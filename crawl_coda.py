#!/usr/bin/env python3
"""
Daily Coda Data Crawler

Production script to crawl Coda tables and persist to Snowflake.
Designed to run daily with idempotent behavior:
- Creates table if it doesn't exist
- Deletes today's data before appending (prevents duplicates)
- Appends new data

Usage:
    python crawl_coda.py
"""

import sys
from datetime import datetime
from dotenv import load_dotenv

from coda_service.coda_table import CodaTable
from utils.snowflake_connection import SnowflakeHook
from utils.logger import get_logger

# Load environment variables
load_dotenv()

# Setup logging
logger = get_logger(__name__)

# Configuration
CODA_URL = "https://coda.io/d/_dn6rnftKCGZ/Everything_suVyKToC#Q3-2025-Roadmap-overview_tuWR35uZ"
SNOWFLAKE_DATABASE = "proddb"
SNOWFLAKE_SCHEMA = "fionafan"
SNOWFLAKE_TABLE = "coda_experiments_daily"
FETCH_LIMIT = None  # None = fetch all rows, or set a number like 100


def crawl_and_persist():
    """
    Main function to crawl Coda data and persist to Snowflake.
    
    Returns:
        bool: True if successful, False otherwise
    """
    today = datetime.now().date().isoformat()
    
    logger.info("=" * 80)
    logger.info("🚀 Starting Coda Daily Crawl")
    logger.info("=" * 80)
    logger.info(f"Date: {today}")
    logger.info(f"Source: {CODA_URL}")
    logger.info(f"Target: {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}")
    
    try:
        # Step 1: Fetch data from Coda
        logger.info("\n" + "=" * 80)
        logger.info("Step 1: Fetching data from Coda")
        logger.info("=" * 80)
        
        table = CodaTable(CODA_URL)
        
        # Fetch all rows (or limited by FETCH_LIMIT)
        if FETCH_LIMIT:
            logger.info(f"Fetching up to {FETCH_LIMIT} rows...")
            table.fetch_rows(limit=FETCH_LIMIT)
        else:
            logger.info("Fetching all rows...")
            # Fetch in batches to handle large tables
            table.fetch_rows(limit=500)  # Adjust based on your table size
        
        if not table.rows:
            logger.error("❌ No rows fetched from Coda")
            return False
        
        logger.info(f"✅ Fetched {len(table.rows)} rows")
        logger.info(f"   Table: {table.table_name}")
        logger.info(f"   Columns: {len(table.get_column_names())}")
        
        # Step 2: Convert to DataFrame
        logger.info("\n" + "=" * 80)
        logger.info("Step 2: Converting to DataFrame")
        logger.info("=" * 80)
        
        df = table.to_dataframe()
        logger.info(f"✅ DataFrame created: {df.shape[0]} rows x {df.shape[1]} columns")
        
        # Step 3: Persist to Snowflake
        logger.info("\n" + "=" * 80)
        logger.info("Step 3: Persisting to Snowflake")
        logger.info("=" * 80)
        
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
                # Case 1: Table doesn't exist - create it
                logger.info("📋 Table doesn't exist. Creating new table...")
                success = hook.create_and_populate_table(
                    df=df,
                    table_name=SNOWFLAKE_TABLE,
                    schema=SNOWFLAKE_SCHEMA,
                    database=SNOWFLAKE_DATABASE,
                    method='pandas'
                )
                
                if success:
                    logger.info(f"✅ Table created successfully")
                    logger.info(f"   Inserted {len(df)} rows")
                else:
                    logger.error("❌ Failed to create table")
                    return False
                    
            else:
                # Case 2: Table exists - check for today's data
                logger.info("📋 Table exists. Checking for existing data...")
                
                # Check if today's data exists
                check_today_query = f"""
                SELECT COUNT(*) as cnt
                FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}
                WHERE DATE(fetched_at) = '{today}'
                """
                
                result = hook.query_snowflake(check_today_query, method='pandas')
                today_count = result.iloc[0]['cnt']
                
                if today_count > 0:
                    # Case 2a: Today's data exists - delete it first
                    logger.info(f"   Found {today_count} existing rows for {today}")
                    logger.info(f"   Deleting existing data for {today}...")
                    
                    delete_query = f"""
                    DELETE FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}
                    WHERE DATE(fetched_at) = '{today}'
                    """
                    
                    hook.query_without_result(delete_query)
                    logger.info(f"   ✅ Deleted {today_count} rows")
                else:
                    # Case 2b: No data for today
                    logger.info(f"   No existing data for {today}")
                
                # Append new data
                logger.info(f"   Appending {len(df)} new rows...")
                success = hook.write_to_snowflake(
                    df=df,
                    table_name=SNOWFLAKE_TABLE,
                    mode='append',
                    method='pandas'
                )
                
                if success:
                    logger.info(f"✅ Data appended successfully")
                else:
                    logger.error("❌ Failed to append data")
                    return False
        
        # Step 4: Verify
        logger.info("\n" + "=" * 80)
        logger.info("Step 4: Verification")
        logger.info("=" * 80)
        
        with SnowflakeHook(
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA
        ) as hook:
            verify_query = f"""
            SELECT 
                DATE(fetched_at) as fetch_date,
                COUNT(*) as row_count,
                MAX(updated_at) as latest_update
            FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}
            WHERE DATE(fetched_at) = '{today}'
            GROUP BY DATE(fetched_at)
            """
            
            result = hook.query_snowflake(verify_query, method='pandas')
            
            if not result.empty:
                row = result.iloc[0]
                logger.info(f"✅ Verification successful:")
                logger.info(f"   Date: {row['fetch_date']}")
                logger.info(f"   Rows: {row['row_count']}")
                logger.info(f"   Latest update: {row['latest_update']}")
            else:
                logger.warning("⚠️  Could not verify data")
        
        # Success summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ CRAWL COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Target: {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}")
        logger.info(f"Rows: {len(df)}")
        logger.info(f"Date: {today}")
        logger.info("Permissions: read_only_users (SELECT), sysadmin (ALL), public (ALL)")
        
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
        success = crawl_and_persist()
        
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

