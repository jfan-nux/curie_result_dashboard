#!/usr/bin/env python3
"""
Curie Results Crawler

Fetches experiment results from Curie for active experiments in Coda
and persists to Snowflake.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd

# No longer need CodaTable - reading from Snowflake instead
from utils.snowflake_connection import SnowflakeHook
from utils.logger import get_logger

logger = get_logger(__name__)


class CurieCrawler:
    """
    Crawler for fetching Curie experiment results and persisting to Snowflake.
    
    Workflow:
    1. Fetch active experiments from Snowflake (coda_experiments_daily table)
    2. Parse Curie iOS links to extract analysis_id
    3. Query Curie results for each experiment
    4. Combine results with Coda metadata
    5. Persist to Snowflake with daily upsert logic
    
    Note: This crawler should run AFTER crawl_coda.py has populated coda_experiments_daily
    """
    
    def __init__(self, 
                 source_table: str = 'proddb.fionafan.coda_experiments_daily',
                 database: str = 'proddb',
                 schema: str = 'fionafan',
                 table_name: str = 'nux_curie_result_daily'):
        """
        Initialize Curie crawler.
        
        Args:
            source_table: Snowflake table with Coda experiment data
            database: Snowflake database for output
            schema: Snowflake schema for output
            table_name: Target table name
        """
        self.source_table = source_table
        self.database = database
        self.schema = schema
        self.table_name = table_name
        
        # Load SQL template
        sql_template_path = Path(__file__).parent / 'combined_curie_results_unified.sql'
        with open(sql_template_path, 'r') as f:
            self.sql_template = f.read()
        
        logger.info(f"✅ Initialized CurieCrawler")
        logger.info(f"   Source: {source_table}")
        logger.info(f"   Target: {database}.{schema}.{table_name}")
    
    def parse_curie_link(self, curie_link: str) -> Optional[str]:
        """
        Extract analysis_id from Curie iOS link.
        
        Example: https://ops.doordash.team/decision-systems/experiments/xxx?analysisId=yyy
        Returns: yyy
        
        Args:
            curie_link: Full Curie URL
            
        Returns:
            analysis_id or None if not found
        """
        if not curie_link or curie_link == '':
            return None
        
        # Try to extract analysisId parameter
        match = re.search(r'analysisId=([a-f0-9\-]+)', curie_link, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Try alternative format
        match = re.search(r'/analysis/([a-f0-9\-]+)', curie_link)
        if match:
            return match.group(1)
        
        logger.warning(f"Could not parse analysis_id from: {curie_link}")
        return None
    
    def fetch_active_experiments(self) -> pd.DataFrame:
        """
        Fetch active experiments from Snowflake (coda_experiments_daily table).
        
        Returns:
            DataFrame with active experiments and metadata
        """
        logger.info(f"Fetching active experiments from {self.source_table}...")
        
        # Query to get active experiments from Snowflake
        query = f"""
        SELECT * 
        FROM {self.source_table}
        WHERE fetched_at = (SELECT MAX(fetched_at) FROM {self.source_table})
        AND project_status IN ('8. In experiment', '8. Ramping')
        AND curie_ios IS NOT NULL 
        AND curie_ios != ''
        """
        
        # Fetch from Snowflake
        with SnowflakeHook(database=self.database, schema=self.schema) as hook:
            df_active = hook.query_snowflake(query, method='pandas')
        
        logger.info(f"✅ Found {len(df_active)} active experiments with Curie links")
        
        return df_active
    
    def fetch_curie_results(self, analysis_id: str) -> pd.DataFrame:
        """
        Fetch Curie experiment results for a specific analysis_id.
        
        Args:
            analysis_id: Curie analysis ID
            
        Returns:
            DataFrame with experiment results
        """
        logger.info(f"Fetching Curie results for analysis_id: {analysis_id}")
        
        # Replace {analysis_id} in SQL template
        query = self.sql_template.replace('{analysis_id}', analysis_id)
        
        # Execute query
        with SnowflakeHook(database=self.database, schema=self.schema) as hook:
            results_df = hook.query_snowflake(query, method='pandas')
        
        logger.info(f"✅ Fetched {len(results_df)} result rows")
        
        return results_df
    
    def crawl_all_experiments(self) -> pd.DataFrame:
        """
        Crawl results for all active experiments.
        
        Returns:
            Combined DataFrame with all results and metadata
        """
        today = datetime.now().date().isoformat()
        
        logger.info("=" * 80)
        logger.info("Starting Curie Results Crawl")
        logger.info("=" * 80)
        
        # Step 1: Get active experiments from Coda
        experiments_df = self.fetch_active_experiments()
        
        if experiments_df.empty:
            logger.warning("No active experiments found")
            return pd.DataFrame()
        
        # Step 2: Process each experiment
        all_results = []
        
        for idx, exp_row in experiments_df.iterrows():
            project_name = exp_row.get('row_name', 'Unknown')
            curie_link = exp_row.get('curie_ios', '')
            
            logger.info(f"\n--- Processing: {project_name} ---")
            
            # Parse analysis_id
            analysis_id = self.parse_curie_link(curie_link)
            
            if not analysis_id:
                logger.warning(f"   ⚠️  No analysis_id found, skipping")
                continue
            
            logger.info(f"   Analysis ID: {analysis_id}")
            
            try:
                # Fetch Curie results
                results_df = self.fetch_curie_results(analysis_id)
                
                if results_df.empty:
                    logger.warning(f"   ⚠️  No results found")
                    continue
                
                # Add metadata from Coda
                results_df['coda_row_id'] = exp_row.get('row_id', '')
                results_df['coda_browser_link'] = exp_row.get('browser_link', '')
                results_df['project_name'] = project_name
                results_df['project_status'] = exp_row.get('project_status', '')
                results_df['curie_ios_link'] = curie_link
                results_df['dv_link'] = exp_row.get('dv', '')
                results_df['fetched_at'] = today
                
                all_results.append(results_df)
                logger.info(f"   ✅ Added {len(results_df)} results")
                
            except Exception as e:
                logger.error(f"   ❌ Error fetching results: {e}")
                continue
        
        # Step 3: Combine all results
        if not all_results:
            logger.warning("No results fetched from any experiment")
            return pd.DataFrame()
        
        combined_df = pd.concat(all_results, ignore_index=True)
        logger.info(f"\n✅ Total results collected: {len(combined_df)} rows")
        logger.info(f"   From {len(all_results)} experiments")
        
        return combined_df
    
    def save_to_snowflake(self, df: pd.DataFrame) -> bool:
        """
        Save results to Snowflake with daily upsert logic.
        
        Args:
            df: DataFrame with results to save
            
        Returns:
            True if successful
        """
        if df.empty:
            logger.error("No data to save")
            return False
        
        today = datetime.now().date().isoformat()
        
        logger.info("\n" + "=" * 80)
        logger.info("Saving to Snowflake")
        logger.info("=" * 80)
        logger.info(f"Target: {self.database}.{self.schema}.{self.table_name}")
        logger.info(f"Rows: {len(df)}")
        
        with SnowflakeHook(
            database=self.database,
            schema=self.schema,
            create_local_spark=False
        ) as hook:
            
            # Check if table exists
            check_query = f"""
            SELECT COUNT(*) as cnt 
            FROM information_schema.tables 
            WHERE table_schema = '{self.schema.upper()}' 
            AND table_name = '{self.table_name.upper()}'
            AND table_catalog = '{self.database.upper()}'
            """
            
            result = hook.query_snowflake(check_query, method='pandas')
            table_exists = result.iloc[0]['cnt'] > 0
            
            if not table_exists:
                # Create table
                logger.info("📋 Creating new table...")
                success = hook.create_and_populate_table(
                    df=df,
                    table_name=self.table_name,
                    schema=self.schema,
                    database=self.database,
                    method='pandas'
                )
                
                if success:
                    logger.info(f"✅ Table created with {len(df)} rows")
                return success
            else:
                # Delete today's data if exists
                logger.info("📋 Table exists. Checking for today's data...")
                
                check_today_query = f"""
                SELECT COUNT(*) as cnt
                FROM {self.database}.{self.schema}.{self.table_name}
                WHERE fetched_at = '{today}'
                """
                
                result = hook.query_snowflake(check_today_query, method='pandas')
                today_count = result.iloc[0]['cnt']
                
                if today_count > 0:
                    logger.info(f"   Found {today_count} existing rows for {today}")
                    logger.info(f"   Deleting...")
                    
                    delete_query = f"""
                    DELETE FROM {self.database}.{self.schema}.{self.table_name}
                    WHERE fetched_at = '{today}'
                    """
                    
                    hook.query_without_result(delete_query)
                    logger.info(f"   ✅ Deleted {today_count} rows")
                
                # Append new data
                logger.info(f"   Appending {len(df)} new rows...")
                success = hook.write_to_snowflake(
                    df=df,
                    table_name=self.table_name,
                    mode='append',
                    method='pandas'
                )
                
                if success:
                    logger.info(f"✅ Data appended successfully")
                
                return success
    
    def run(self) -> bool:
        """
        Run the complete crawl pipeline.
        
        Returns:
            True if successful
        """
        try:
            # Crawl all experiments
            results_df = self.crawl_all_experiments()
            
            if results_df.empty:
                logger.warning("No results to save")
                return False
            
            # Save to Snowflake
            success = self.save_to_snowflake(results_df)
            
            if success:
                logger.info("\n" + "=" * 80)
                logger.info("✅ CURIE CRAWL COMPLETED SUCCESSFULLY")
                logger.info("=" * 80)
                logger.info(f"Table: {self.database}.{self.schema}.{self.table_name}")
                logger.info(f"Rows: {len(results_df)}")
                logger.info(f"Date: {datetime.now().date().isoformat()}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Curie crawl failed: {e}")
            logger.exception("Full traceback:")
            return False


# Standalone execution
if __name__ == "__main__":
    from dotenv import load_dotenv
    import sys
    
    load_dotenv()
    
    # Run crawler (reads from proddb.fionafan.coda_experiments_daily)
    crawler = CurieCrawler(
        source_table='proddb.fionafan.coda_experiments_daily',
        database='proddb',
        schema='fionafan',
        table_name='nux_curie_result_daily'
    )
    
    success = crawler.run()
    
    sys.exit(0 if success else 1)

