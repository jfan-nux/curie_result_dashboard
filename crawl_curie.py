#!/usr/bin/env python3
"""
Daily Curie Results Crawler

Fetches Curie experiment results for active experiments and persists to Snowflake.

This crawler should run AFTER crawl_coda.py to ensure coda_experiments_daily is populated.

Usage:
    python crawl_curie.py
"""

import sys
from dotenv import load_dotenv
from curie_service import CurieCrawler
from utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

# Configuration
SOURCE_TABLE = "proddb.fionafan.coda_experiments_daily"  # Input: Coda data
SNOWFLAKE_DATABASE = "proddb"
SNOWFLAKE_SCHEMA = "fionafan"
SNOWFLAKE_TABLE = "nux_curie_result_daily"  # Output: Curie results


def main():
    """Main entry point for Curie results crawler."""
    
    logger.info("=" * 80)
    logger.info("🧪 NUX Curie Results Daily Crawler")
    logger.info("=" * 80)
    logger.info("Note: Reads from coda_experiments_daily table")
    logger.info("      Run crawl_coda.py first!")
    
    try:
        # Initialize crawler
        crawler = CurieCrawler(
            source_table=SOURCE_TABLE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            table_name=SNOWFLAKE_TABLE
        )
        
        # Run the crawl
        success = crawler.run()
        
        if success:
            logger.info("\n🎉 Curie crawl completed successfully!")
            sys.exit(0)
        else:
            logger.error("\n💥 Curie crawl failed!")
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

