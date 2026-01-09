#!/usr/bin/env python3
"""
Crawl Specific Coda Experiment Views

Crawls only the key experiment tracking views:
- Live Experiments
- Upcoming xps
- Pre-dev
- Concluded xps

Daily Update Behavior:
----------------------
When run daily, this script will:
1. Check if today's data exists in Snowflake
2. DELETE today's data if it exists (prevents duplicates)
3. INSERT fresh data from Coda

This ensures:
- Each day has only ONE snapshot of data
- Historical data from previous days is preserved
- Re-running on the same day updates (not duplicates) the data

Example queries after daily runs:
---------------------------------
-- Get today's snapshot
SELECT * FROM proddb.fionafan.coda_experiments_focused
WHERE DATE(fetched_at) = CURRENT_DATE;

-- Get yesterday's snapshot
SELECT * FROM proddb.fionafan.coda_experiments_focused
WHERE DATE(fetched_at) = CURRENT_DATE - 1;

-- Track changes over time
SELECT 
    DATE(fetched_at) as snapshot_date,
    view_name,
    COUNT(*) as experiment_count
FROM proddb.fionafan.coda_experiments_focused
GROUP BY DATE(fetched_at), view_name
ORDER BY snapshot_date DESC, view_name;

Usage:
    python crawl_coda_experiments.py
"""

import sys
import re
from datetime import datetime
from typing import List, Dict, Any, Set, Optional
import pandas as pd
from dotenv import load_dotenv

from coda_service.coda_client import CodaClient
from utils.snowflake_connection import SnowflakeHook
from utils.logger import get_logger
from google_docs_service.google_docs_crawler import get_google_docs_crawler, GoogleDocContent

# Load environment variables
load_dotenv()

# Setup logging
logger = get_logger(__name__)

# Configuration
CODA_DOC_URL = "https://coda.io/d/_dn6rnftKCGZ/Experiments_su6XeoP4"
SNOWFLAKE_DATABASE = "proddb"
SNOWFLAKE_SCHEMA = "fionafan"
SNOWFLAKE_TABLE = "coda_experiments_focused"
FETCH_LIMIT = 500  # Rows per table

# Only crawl these specific views
TARGET_VIEWS = [
    "Live Experiments",
    "Upcoming xps",
    "Pre-dev",
    "Concluded xps"
]

# Column names that may contain Google Doc links
BRIEF_COLUMN_NAMES = ['brief', 'brief_link', 'brief_url', 'design_doc', 'prd']


def extract_google_doc_url(value: Any) -> Optional[str]:
    """
    Extract Google Doc URL from a cell value.
    
    Handles various formats:
    - Direct URLs
    - Markdown links [text](url)
    - URLs embedded in text
    
    Args:
        value: Cell value from Coda
        
    Returns:
        Google Doc URL or None
    """
    if not value or not isinstance(value, str):
        return None
    
    value = value.strip()
    
    # Pattern for Google Doc URLs
    gdoc_pattern = r'https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+'
    
    # Try to find Google Doc URL in the value
    match = re.search(gdoc_pattern, value)
    if match:
        return match.group(0)
    
    # Check for markdown link format [text](url)
    markdown_pattern = r'\[.*?\]\((https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+[^)]*)\)'
    match = re.search(markdown_pattern, value)
    if match:
        return match.group(1)
    
    return None


def get_previous_day_brief_data() -> Dict[str, Dict[str, Any]]:
    """
    Fetch the previous day's brief data from Snowflake.
    
    Returns:
        Dictionary mapping row_id to {brief_url, brief_content, brief_images_description, brief_summary}
    """
    from datetime import timedelta
    
    try:
        with SnowflakeHook(
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            create_local_spark=False
        ) as hook:
            # Get the most recent date before today
            query = f"""
            SELECT 
                row_id,
                brief,
                brief_content,
                brief_images_description,
                brief_summary
            FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}
            WHERE DATE(fetched_at) = (
                SELECT MAX(DATE(fetched_at)) 
                FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}
                WHERE DATE(fetched_at) < CURRENT_DATE
            )
            """
            
            result = hook.query_snowflake(query, method='pandas')
            
            if result.empty:
                logger.info("   No previous day's data found in Snowflake")
                return {}
            
            # Build lookup dictionary
            prev_data = {}
            for _, row in result.iterrows():
                row_id = row.get('row_id') or row.get('ROW_ID')
                if row_id:
                    prev_data[row_id] = {
                        'brief': row.get('brief') or row.get('BRIEF'),
                        'brief_content': row.get('brief_content') or row.get('BRIEF_CONTENT'),
                        'brief_images_description': row.get('brief_images_description') or row.get('BRIEF_IMAGES_DESCRIPTION'),
                        'brief_summary': row.get('brief_summary') or row.get('BRIEF_SUMMARY'),
                    }
            
            logger.info(f"   Loaded {len(prev_data)} rows from previous day")
            return prev_data
            
    except Exception as e:
        logger.warning(f"   Could not fetch previous day's data: {e}")
        return {}


def crawl_google_docs_for_briefs(df: pd.DataFrame, limit: int = None) -> pd.DataFrame:
    """
    Crawl Google Doc links from brief columns and add content to DataFrame.
    
    Optimization: Only crawls briefs that have changed since the previous day.
    If brief URL is unchanged or previous brief_content was null, reuses cached content.
    
    Args:
        df: DataFrame with experiment data
        limit: Optional limit on number of docs to crawl (for testing)
        
    Returns:
        DataFrame with additional columns for brief content
    """
    logger.info("\n" + "=" * 80)
    logger.info("📄 Crawling Google Doc briefs")
    logger.info("=" * 80)
    
    # Initialize crawler
    crawler = get_google_docs_crawler()
    
    if not crawler.is_available():
        logger.warning("⚠️  Google Docs crawler not available - skipping brief crawl")
        logger.warning("   To enable: Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_OAUTH_CREDENTIALS_FILE")
        df['brief_content'] = None
        df['brief_images_description'] = None
        df['brief_summary'] = None
        return df
    
    # Find the brief column
    brief_col = None
    for col_name in BRIEF_COLUMN_NAMES:
        if col_name in df.columns:
            brief_col = col_name
            break
    
    if not brief_col:
        logger.info("   No brief column found in data")
        df['brief_content'] = None
        df['brief_images_description'] = None
        df['brief_summary'] = None
        return df
    
    logger.info(f"   Found brief column: '{brief_col}'")
    
    # Fetch previous day's data for caching
    logger.info("   Checking previous day's data for unchanged briefs...")
    prev_day_data = get_previous_day_brief_data()
    
    # Extract Google Doc URLs from brief column
    df['_gdoc_url'] = df[brief_col].apply(extract_google_doc_url)
    
    # Determine which URLs need crawling vs can be cached
    urls_to_crawl = set()
    cached_results: Dict[str, Dict[str, Any]] = {}  # url -> {content, images_desc, summary}
    
    for _, row in df.iterrows():
        row_id = row.get('row_id')
        current_url = row.get('_gdoc_url')
        
        if not current_url:
            continue
        
        # Check if we have previous data for this row
        prev_row = prev_day_data.get(row_id, {})
        prev_brief = prev_row.get('brief')
        prev_content = prev_row.get('brief_content')
        
        # Extract URL from previous brief for comparison
        prev_url = extract_google_doc_url(prev_brief) if prev_brief else None
        
        # Decide whether to crawl or use cache
        if prev_url == current_url and prev_content and prev_content not in [None, 'None', '']:
            # Same URL and we have content - use cached
            if current_url not in cached_results:
                cached_results[current_url] = {
                    'content': prev_content,
                    'images_desc': prev_row.get('brief_images_description'),
                    'summary': prev_row.get('brief_summary'),
                }
        else:
            # URL changed or no previous content - need to crawl
            urls_to_crawl.add(current_url)
    
    # Remove cached URLs that also need crawling (in case of conflicts)
    for url in urls_to_crawl:
        cached_results.pop(url, None)
    
    urls_to_crawl = list(urls_to_crawl)
    
    if limit:
        urls_to_crawl = urls_to_crawl[:limit]
    
    logger.info(f"   Found {len(urls_to_crawl)} URLs to crawl (new/changed)")
    logger.info(f"   Found {len(cached_results)} URLs with cached content (unchanged)")
    
    if not urls_to_crawl and not cached_results:
        df['brief_content'] = None
        df['brief_images_description'] = None
        df['brief_summary'] = None
        df.drop(columns=['_gdoc_url'], inplace=True)
        return df
    
    # Crawl new/changed documents
    doc_results: Dict[str, GoogleDocContent] = {}
    
    for i, url in enumerate(urls_to_crawl, 1):
        logger.info(f"\n   [{i}/{len(urls_to_crawl)}] Crawling: {url[:60]}...")
        try:
            result = crawler.crawl_document(
                doc_url_or_id=url,
                analyze_images=True,
                is_experiment_doc=True
            )
            doc_results[url] = result
            
            if result.error:
                logger.warning(f"      ⚠️  {result.error}")
            else:
                logger.info(f"      ✅ {result.title}")
                logger.info(f"         Text: {len(result.text_content)} chars, Images: {len(result.images)}")
                
        except Exception as e:
            logger.error(f"      ❌ Error: {e}")
            doc_results[url] = GoogleDocContent(
                doc_id=url,
                error=str(e)
            )
    
    # Clean up temporary files
    if urls_to_crawl:
        logger.info("\n🧹 Cleaning up temporary files...")
        crawler.cleanup()
    
    # Map results back to DataFrame - check both crawled and cached results
    def get_content(url):
        if pd.isna(url):
            return None
        # Check newly crawled results first
        if url in doc_results:
            return doc_results[url].text_content
        # Then check cached results
        if url in cached_results:
            return cached_results[url].get('content')
        return None
    
    def get_images_desc(url):
        if pd.isna(url):
            return None
        # Check newly crawled results first
        if url in doc_results:
            descs = doc_results[url].image_descriptions
            if descs:
                return '\n\n---\n\n'.join(descs)
            return None
        # Then check cached results
        if url in cached_results:
            return cached_results[url].get('images_desc')
        return None
    
    def get_summary(url):
        if pd.isna(url):
            return None
        # Check newly crawled results first
        if url in doc_results:
            return doc_results[url].combined_summary
        # Then check cached results
        if url in cached_results:
            return cached_results[url].get('summary')
        return None
    
    df['brief_content'] = df['_gdoc_url'].apply(get_content)
    df['brief_images_description'] = df['_gdoc_url'].apply(get_images_desc)
    df['brief_summary'] = df['_gdoc_url'].apply(get_summary)
    
    # Drop temporary column
    df.drop(columns=['_gdoc_url'], inplace=True)
    
    # Stats
    crawled_count = len(doc_results)
    cached_count = len(cached_results)
    total_with_content = df['brief_content'].notna().sum()
    logger.info(f"\n✅ Brief crawl complete:")
    logger.info(f"   - Newly crawled: {crawled_count} documents")
    logger.info(f"   - From cache (unchanged): {cached_count} documents")
    logger.info(f"   - Total with content: {total_with_content} documents")
    
    return df


def extract_doc_id_from_url(url: str, client: CodaClient) -> str:
    """Extract document ID from Coda URL."""
    parsed = client.parse_coda_url(url)
    return parsed.get('doc_id')


def fetch_specific_tables(doc_id: str, client: CodaClient, target_views: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch only specific tables (views) from a Coda document.
    
    Args:
        doc_id: Document ID
        client: CodaClient instance
        target_views: List of view names to fetch
        
    Returns:
        List of table metadata dictionaries (only matching views)
    """
    logger.info(f"Fetching tables for document: {doc_id}")
    
    response = client.list_tables(doc_id)
    all_tables = response.get('items', [])
    
    # Filter to only target views
    filtered_tables = [
        table for table in all_tables 
        if table.get('name') in target_views
    ]
    
    logger.info(f"✅ Found {len(all_tables)} total tables, filtered to {len(filtered_tables)} target views:")
    for i, table in enumerate(filtered_tables, 1):
        logger.info(f"   {i}. {table.get('name')} (ID: {table.get('id')})")
    
    if len(filtered_tables) < len(target_views):
        missing = set(target_views) - {t.get('name') for t in filtered_tables}
        logger.warning(f"⚠️  Missing views: {missing}")
    
    return filtered_tables


def fetch_table_data(doc_id: str, table_id: str, table_name: str, 
                     client: CodaClient, limit: int = 500) -> pd.DataFrame:
    """
    Fetch all data from a single table/view.
    
    Args:
        doc_id: Document ID
        table_id: Table ID
        table_name: Table name (for logging)
        client: CodaClient instance
        limit: Maximum rows to fetch
        
    Returns:
        DataFrame with table data
    """
    logger.info(f"\n📥 Fetching data from: {table_name}")
    
    try:
        rows_response = client.get_table_rows(
            doc_id=doc_id,
            table_id=table_id,
            limit=limit,
            use_column_names=True,
            value_format='simple'
        )
        
        items = rows_response.get('items', [])
        logger.info(f"   Retrieved {len(items)} rows")
        
        if not items:
            logger.warning(f"   ⚠️  No rows found in {table_name}")
            return pd.DataFrame()
        
        # Convert to flat records
        records = []
        for row in items:
            record = {
                'view_name': table_name,
                'view_id': table_id,
                'row_id': row.get('id', ''),
                'row_name': row.get('name', ''),
                'row_index': row.get('index', 0),
                'created_at': row.get('createdAt', ''),
                'updated_at': row.get('updatedAt', ''),
                'fetched_at': datetime.now().date().isoformat(),
            }
            
            # Add all column values
            values = row.get('values', {})
            for col_name, col_value in values.items():
                # Clean column names for Snowflake
                clean_col = col_name.lower()\
                    .replace(' ', '_')\
                    .replace('(', '')\
                    .replace(')', '')\
                    .replace('%', 'pct')\
                    .replace('~', '')\
                    .replace('/', '_')\
                    .replace('-', '_')\
                    .replace('.', '_')\
                    .strip('_')
                
                # Prefix with 'col_' if starts with a number
                if clean_col and clean_col[0].isdigit():
                    clean_col = f"col_{clean_col}"
                
                record[clean_col] = col_value
            
            records.append(record)
        
        df = pd.DataFrame(records)
        logger.info(f"   ✅ Created DataFrame: {len(df)} rows × {len(df.columns)} columns")
        
        return df
        
    except Exception as e:
        logger.error(f"   ❌ Error fetching {table_name}: {str(e)}")
        return pd.DataFrame()


def combine_dataframes(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Combine multiple DataFrames with different schemas into one unified DataFrame.
    
    For columns that exist in some DataFrames but not others, fills with None.
    
    Args:
        dfs: List of DataFrames to combine
        
    Returns:
        Combined DataFrame with unified schema
    """
    if not dfs:
        logger.error("No DataFrames to combine")
        return pd.DataFrame()
    
    logger.info("\n📊 Combining all views into unified schema...")
    
    # Collect all unique columns across all DataFrames
    all_columns: Set[str] = set()
    for df in dfs:
        all_columns.update(df.columns)
    
    all_columns_sorted = sorted(list(all_columns))
    logger.info(f"   Total unique columns across all views: {len(all_columns_sorted)}")
    
    # Ensure each DataFrame has all columns (fill missing with None)
    normalized_dfs = []
    for df in dfs:
        # Add missing columns with None values
        for col in all_columns_sorted:
            if col not in df.columns:
                df[col] = None
        
        # Reorder columns to match unified schema
        df = df[all_columns_sorted]
        normalized_dfs.append(df)
    
    # Concatenate all DataFrames
    combined_df = pd.concat(normalized_dfs, ignore_index=True)
    
    # Convert columns with mixed types to strings to avoid Arrow conversion errors
    logger.info(f"   Converting mixed-type columns to strings...")
    for col in combined_df.columns:
        # Check if column has mixed types
        if combined_df[col].dtype == 'object':
            # Convert to string, handling None values
            combined_df[col] = combined_df[col].astype(str).replace('nan', None).replace('None', None)
    
    logger.info(f"   ✅ Combined DataFrame: {len(combined_df)} rows × {len(combined_df.columns)} columns")
    
    return combined_df


def crawl_experiments_and_persist():
    """
    Main function to crawl focused Coda experiment views and persist to Snowflake.
    
    Daily Update Behavior:
    ----------------------
    1. Checks for existing data from today
    2. Deletes today's data if it exists
    3. Inserts fresh data
    
    This ensures:
    - Each day = one snapshot
    - Re-running same day = update, not duplicate
    - Historical data preserved
    
    Returns:
        bool: True if successful, False otherwise
    """
    today = datetime.now().date().isoformat()
    
    logger.info("=" * 80)
    logger.info("🚀 Starting Coda Experiments Focused Crawl")
    logger.info("=" * 80)
    logger.info(f"Date: {today}")
    logger.info(f"Source: {CODA_DOC_URL}")
    logger.info(f"Target Views: {', '.join(TARGET_VIEWS)}")
    logger.info(f"Destination: {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}")
    
    try:
        # Step 1: Initialize Coda client
        logger.info("\n" + "=" * 80)
        logger.info("Step 1: Connecting to Coda API")
        logger.info("=" * 80)
        
        client = CodaClient()
        if not client.test_connection():
            logger.error("❌ Failed to connect to Coda API")
            return False
        
        # Step 2: Get document ID and list target tables
        logger.info("\n" + "=" * 80)
        logger.info("Step 2: Fetching target views")
        logger.info("=" * 80)
        
        doc_id = extract_doc_id_from_url(CODA_DOC_URL, client)
        logger.info(f"Document ID: {doc_id}")
        
        tables = fetch_specific_tables(doc_id, client, TARGET_VIEWS)
        
        if not tables:
            logger.error("❌ No target tables found in document")
            return False
        
        # Step 3: Fetch data from each table/view
        logger.info("\n" + "=" * 80)
        logger.info("Step 3: Fetching data from target views")
        logger.info("=" * 80)
        
        all_dfs = []
        for table in tables:
            table_id = table.get('id')
            table_name = table.get('name')
            
            df = fetch_table_data(
                doc_id=doc_id,
                table_id=table_id,
                table_name=table_name,
                client=client,
                limit=FETCH_LIMIT
            )
            
            if not df.empty:
                all_dfs.append(df)
        
        if not all_dfs:
            logger.error("❌ No data fetched from any tables")
            return False
        
        # Step 4: Combine all DataFrames with unified schema
        logger.info("\n" + "=" * 80)
        logger.info("Step 4: Creating unified schema")
        logger.info("=" * 80)
        
        combined_df = combine_dataframes(all_dfs)
        
        logger.info(f"\n📊 Combined Dataset (before brief crawl):")
        logger.info(f"   Total rows: {len(combined_df)}")
        logger.info(f"   Total columns: {len(combined_df.columns)}")
        logger.info(f"   Views included: {combined_df['view_name'].nunique()}")
        
        # Show breakdown by view
        logger.info(f"\n   Rows per view:")
        for view in TARGET_VIEWS:
            count = len(combined_df[combined_df['view_name'] == view])
            logger.info(f"      {view}: {count} rows")
        
        # Step 5: Crawl Google Doc briefs
        logger.info("\n" + "=" * 80)
        logger.info("Step 5: Crawling Google Doc briefs")
        logger.info("=" * 80)
        
        combined_df = crawl_google_docs_for_briefs(combined_df)
        
        logger.info(f"\n📊 Final Combined Dataset (after brief crawl):")
        logger.info(f"   Total rows: {len(combined_df)}")
        logger.info(f"   Total columns: {len(combined_df.columns)}")
        
        # Step 6: Persist to Snowflake
        logger.info("\n" + "=" * 80)
        logger.info("Step 6: Persisting to Snowflake")
        logger.info("=" * 80)
        logger.info("Daily Update Strategy:")
        logger.info("  1. Check for today's data")
        logger.info("  2. Delete if exists (prevents duplicates)")
        logger.info("  3. Insert fresh data")
        logger.info("  → Result: One snapshot per day, historical data preserved")
        
        with SnowflakeHook(
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            create_local_spark=False
        ) as hook:
            
            # Check if table exists
            check_query = f"""
            SELECT COUNT(*) as cnt 
            FROM information_schema.tables 
            WHERE table_schema = '{SNOWFLAKE_SCHEMA.upper()}' 
            AND table_name = '{SNOWFLAKE_TABLE.upper()}'
            AND table_catalog = '{SNOWFLAKE_DATABASE.upper()}'
            """
            
            result = hook.query_snowflake(check_query, method='pandas')
            table_exists = result.iloc[0]['cnt'] > 0
            
            if not table_exists:
                # Create new table
                logger.info("📋 Table doesn't exist. Creating new table...")
                success = hook.create_and_populate_table(
                    df=combined_df,
                    table_name=SNOWFLAKE_TABLE,
                    schema=SNOWFLAKE_SCHEMA,
                    database=SNOWFLAKE_DATABASE,
                    method='pandas'
                )
                
                if success:
                    logger.info(f"✅ Table created successfully")
                else:
                    logger.error("❌ Failed to create table")
                    return False
                    
            else:
                # Table exists - delete today's data and append
                logger.info("📋 Table exists. Checking for existing data...")
                
                check_today_query = f"""
                SELECT COUNT(*) as cnt
                FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}
                WHERE DATE(fetched_at) = '{today}'
                """
                
                result = hook.query_snowflake(check_today_query, method='pandas')
                today_count = result.iloc[0]['cnt']
                
                if today_count > 0:
                    logger.info(f"   Found {today_count} existing rows for {today}")
                    logger.info(f"   🗑️  Deleting existing data for {today}...")
                    
                    delete_query = f"""
                    DELETE FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}
                    WHERE DATE(fetched_at) = '{today}'
                    """
                    
                    hook.query_without_result(delete_query)
                    logger.info(f"   ✅ Deleted {today_count} rows")
                else:
                    logger.info(f"   No existing data for {today}")
                
                # Append new data
                logger.info(f"   📝 Appending {len(combined_df)} new rows...")
                success = hook.write_to_snowflake(
                    df=combined_df,
                    table_name=SNOWFLAKE_TABLE,
                    mode='append',
                    method='pandas'
                )
                
                if success:
                    logger.info(f"✅ Data appended successfully")
                else:
                    logger.error("❌ Failed to append data")
                    return False
        
        # Step 7: Verify
        logger.info("\n" + "=" * 80)
        logger.info("Step 7: Verification")
        logger.info("=" * 80)
        
        with SnowflakeHook(
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            create_local_spark=False
        ) as hook:
            verify_query = f"""
            SELECT 
                DATE(fetched_at) as fetch_date,
                view_name,
                COUNT(*) as row_count
            FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}
            WHERE DATE(fetched_at) = '{today}'
            GROUP BY DATE(fetched_at), view_name
            ORDER BY view_name
            """
            
            result = hook.query_snowflake(verify_query, method='pandas')
            
            if not result.empty:
                logger.info(f"✅ Verification successful for {today}:")
                logger.info(f"\n   Rows per view:")
                for _, row in result.iterrows():
                    logger.info(f"      {row['view_name']}: {row['row_count']} rows")
            else:
                logger.warning("⚠️  Could not verify data")
        
        # Success summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ CRAWL COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Destination: {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}")
        logger.info(f"Total rows: {len(combined_df)}")
        logger.info(f"Views: {', '.join(TARGET_VIEWS)}")
        logger.info(f"Date: {today}")
        logger.info("\nDaily Update Behavior:")
        logger.info("  ✓ Each day creates ONE snapshot")
        logger.info("  ✓ Re-running same day updates (not duplicates)")
        logger.info("  ✓ Historical data from previous days preserved")
        
        return True
        
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("❌ CRAWL FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.exception("Full traceback:")
        return False


def main():
    """Main entry point."""
    try:
        success = crawl_experiments_and_persist()
        
        if success:
            logger.info("\n🎉 All done!")
            sys.exit(0)
        else:
            logger.error("\n💥 Crawl failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n💥 Unexpected error: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()

