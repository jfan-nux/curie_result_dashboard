"""
Consolidated Coda Table and Row models with Snowflake persistence.

This module consolidates functionality from:
- show_all_project_data.py
- example_crawl_table.py
- fetch_all_columns.py
- get_row_details.py
- inspect_table_columns.py
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
import pandas as pd

from coda_service.coda_client import CodaClient
from utils.snowflake_connection import SnowflakeHook
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CodaRow:
    """
    Represents a single row from a Coda table.
    
    Based on the structure from sample_row_rich.json
    """
    # Row metadata from Coda API
    row_id: str
    row_type: str
    row_href: str
    row_name: str
    row_index: int
    created_at: str
    updated_at: str
    browser_link: str
    
    # Table context
    doc_id: str
    table_id: str
    page_id: Optional[str] = None
    
    # Row values (all columns)
    values: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    fetched_at: str = field(default_factory=lambda: datetime.now().date().isoformat())
    
    @classmethod
    def from_api_response(cls, row_data: Dict[str, Any], doc_id: str, 
                          table_id: str, page_id: Optional[str] = None) -> 'CodaRow':
        """
        Create a CodaRow from Coda API response.
        
        Args:
            row_data: Raw row data from Coda API
            doc_id: Document ID
            table_id: Table ID
            page_id: Page ID (optional)
            
        Returns:
            CodaRow instance
        """
        return cls(
            row_id=row_data.get('id', ''),
            row_type=row_data.get('type', 'row'),
            row_href=row_data.get('href', ''),
            row_name=row_data.get('name', ''),
            row_index=row_data.get('index', 0),
            created_at=row_data.get('createdAt', ''),
            updated_at=row_data.get('updatedAt', ''),
            browser_link=row_data.get('browserLink', ''),
            doc_id=doc_id,
            table_id=table_id,
            page_id=page_id,
            values=cls._process_values(row_data.get('values', {}))
        )
    
    @staticmethod
    def _process_values(values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and flatten values for storage.
        
        Handles:
        - Rich text objects (extract plain text)
        - Link objects (extract URLs)
        - Arrays (convert to JSON strings)
        """
        processed = {}
        
        for key, value in values.items():
            if isinstance(value, dict):
                # Handle link objects
                if '@type' in value and value.get('@type') == 'WebPage':
                    processed[key] = value.get('url', '')
                else:
                    # Store complex objects as JSON
                    processed[key] = json.dumps(value)
            elif isinstance(value, list):
                # Handle arrays - flatten if it's a list of strings
                if value and isinstance(value[0], str):
                    processed[key] = ', '.join(str(v) for v in value)
                else:
                    processed[key] = json.dumps(value)
            else:
                processed[key] = value
        
        return processed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def to_flat_dict(self) -> Dict[str, Any]:
        """
        Convert to flat dictionary suitable for DataFrame/Snowflake.
        
        Combines metadata and values into a single flat dict.
        """
        flat = {
            'row_id': self.row_id,
            'row_type': self.row_type,
            'row_name': self.row_name,
            'row_index': self.row_index,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'doc_id': self.doc_id,
            'table_id': self.table_id,
            'page_id': self.page_id,
            'fetched_at': self.fetched_at,
            'browser_link': self.browser_link,
        }
        
        # Add all values (clean column names for Snowflake)
        for key, value in self.values.items():
            # Clean column names for Snowflake
            clean_key = key.lower().replace(' ', '_').replace('(', '').replace(')', '')
            flat[clean_key] = value
        
        return flat


class CodaTable:
    """
    Represents a Coda table with methods to fetch, inspect, and persist data.
    
    Consolidates functionality from multiple scripts into a single class.
    """
    
    def __init__(self, url: str, api_key: Optional[str] = None):
        """
        Initialize a Coda table from a URL.
        
        Args:
            url: Full Coda URL (with or without fragment)
                 e.g., https://coda.io/d/_dn6rnftKCGZ/Everything_suVyKToC#ALL-PROJECTS_tudJtJVH
            api_key: Coda API key (optional, will use env var if not provided)
        """
        self.url = url
        self.client = CodaClient(api_key=api_key)
        
        # Parse URL to get IDs
        logger.info(f"Parsing Coda URL: {url}")
        self.url_parts = self.client.parse_coda_url(url)
        self.doc_id = self.url_parts.get('doc_id')
        self.page_id = self.url_parts.get('page_id')
        self.table_fragment = self.url_parts.get('table_fragment')
        
        # Resolve browser link to get actual table ID
        logger.info("Resolving browser link to get actual table ID...")
        self.resolved = self.client.resolve_browser_link(url)
        self.resource = self.resolved.get('resource', {})
        
        self.table_id = self.resource.get('id')
        self.table_name = self.resource.get('name')
        self.table_type = self.resource.get('type')
        
        # Storage for fetched data
        self.rows: List[CodaRow] = []
        self.columns: List[Dict[str, Any]] = []
        self.last_fetched: Optional[str] = None
        
        logger.info(f"✅ Initialized CodaTable: {self.table_name} (ID: {self.table_id})")
    
    def fetch_columns(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch column definitions from the table.
        
        Args:
            limit: Maximum number of columns to fetch
            
        Returns:
            List of column definitions
        """
        logger.info(f"Fetching columns for table: {self.table_name}")
        
        columns_response = self.client._make_request(
            'GET',
            f'/docs/{self.doc_id}/tables/{self.table_id}/columns',
            params={'limit': limit}
        )
        
        self.columns = columns_response.get('items', [])
        logger.info(f"✅ Fetched {len(self.columns)} columns")
        
        return self.columns
    
    def get_column_names(self) -> List[str]:
        """Get list of column names."""
        if not self.columns:
            self.fetch_columns()
        return [col.get('name') for col in self.columns]
    
    def fetch_rows(self, limit: int = 100, use_column_names: bool = True,
                   value_format: str = 'simple') -> List[CodaRow]:
        """
        Fetch rows from the table.
        
        Args:
            limit: Maximum number of rows to fetch
            use_column_names: Return column names instead of IDs
            value_format: 'simple', 'simpleWithArrays', or 'rich'
            
        Returns:
            List of CodaRow objects
        """
        logger.info(f"Fetching up to {limit} rows from table: {self.table_name}")
        
        rows_response = self.client.get_table_rows(
            doc_id=self.doc_id,
            table_id=self.table_id,
            limit=limit,
            use_column_names=use_column_names,
            value_format=value_format
        )
        
        # Convert to CodaRow objects
        self.rows = [
            CodaRow.from_api_response(
                row_data=row,
                doc_id=self.doc_id,
                table_id=self.table_id,
                page_id=self.page_id
            )
            for row in rows_response.get('items', [])
        ]
        
        self.last_fetched = datetime.now().date().isoformat()
        logger.info(f"✅ Fetched {len(self.rows)} rows")
        
        return self.rows
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert fetched rows to a pandas DataFrame.
        
        Returns:
            DataFrame with all row data
        """
        if not self.rows:
            logger.warning("No rows fetched. Call fetch_rows() first.")
            return pd.DataFrame()
        
        # Convert rows to flat dictionaries
        flat_rows = [row.to_flat_dict() for row in self.rows]
        
        df = pd.DataFrame(flat_rows)
        logger.info(f"✅ Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
        
        return df
    
    def save_to_snowflake(self, table_name: str, 
                         database: str = 'proddb',
                         schema: str = 'fionafan',
                         mode: str = 'append',
                         method: str = 'pandas') -> bool:
        """
        Persist table data to Snowflake.
        
        Automatically grants permissions:
        - SELECT to read_only_users
        - ALL to sysadmin
        - ALL to public
        
        Args:
            table_name: Target table name in Snowflake
            database: Snowflake database (default: proddb)
            schema: Snowflake schema (default: fionafan)
            mode: Write mode - 'append', 'overwrite', 'error', 'ignore'
            method: Write method - 'pandas' or 'spark'
            
        Returns:
            True if successful
        """
        if not self.rows:
            logger.error("No rows to save. Call fetch_rows() first.")
            return False
        
        logger.info(f"Saving {len(self.rows)} rows to Snowflake: {database}.{schema}.{table_name}")
        
        # Convert to DataFrame
        df = self.to_dataframe()
        
        # Connect to Snowflake and write
        try:
            with SnowflakeHook(database=database, schema=schema, 
                              create_local_spark=False) as hook:
                
                # Create table if it doesn't exist (for first write)
                if mode == 'overwrite' or mode == 'append':
                    full_table_name = f"{database}.{schema}.{table_name}"
                    
                    # Check if table exists
                    check_query = f"""
                    SELECT COUNT(*) as cnt 
                    FROM information_schema.tables 
                    WHERE table_schema = '{schema.upper()}' 
                    AND table_name = '{table_name.upper()}'
                    AND table_catalog = '{database.upper()}'
                    """
                    
                    result = hook.query_snowflake(check_query, method='pandas')
                    table_exists = result.iloc[0]['cnt'] > 0
                    
                    if not table_exists:
                        logger.info(f"Table doesn't exist. Creating: {full_table_name}")
                        success = hook.create_and_populate_table(
                            df=df,
                            table_name=table_name,
                            schema=schema,
                            database=database,
                            method=method
                        )
                    else:
                        logger.info(f"Table exists. Writing with mode={mode}")
                        success = hook.write_to_snowflake(
                            df=df,
                            table_name=table_name,
                            mode=mode,
                            method=method
                        )
                else:
                    success = hook.write_to_snowflake(
                        df=df,
                        table_name=table_name,
                        mode=mode,
                        method=method
                    )
                
                if success:
                    logger.info(f"✅ Successfully saved {len(df)} rows to Snowflake")
                    logger.info(f"   Table: {database}.{schema}.{table_name}")
                    logger.info(f"   Columns: {len(df.columns)}")
                
                return success
                
        except Exception as e:
            logger.error(f"❌ Error saving to Snowflake: {e}")
            raise
    
    def inspect(self) -> Dict[str, Any]:
        """
        Get a complete inspection of the table.
        
        Returns:
            Dictionary with table metadata, columns, and sample data
        """
        # Fetch columns if not already fetched
        if not self.columns:
            self.fetch_columns()
        
        # Fetch sample rows if not already fetched
        if not self.rows:
            self.fetch_rows(limit=5)
        
        inspection = {
            'url': self.url,
            'doc_id': self.doc_id,
            'table_id': self.table_id,
            'table_name': self.table_name,
            'table_type': self.table_type,
            'page_id': self.page_id,
            'column_count': len(self.columns),
            'columns': [col.get('name') for col in self.columns],
            'row_count': len(self.rows),
            'sample_rows': [row.to_dict() for row in self.rows[:3]],
            'last_fetched': self.last_fetched
        }
        
        return inspection
    
    def print_summary(self):
        """Print a formatted summary of the table."""
        print("=" * 80)
        print(f"📊 Coda Table: {self.table_name}")
        print("=" * 80)
        print(f"\n📍 Location:")
        print(f"   Doc ID: {self.doc_id}")
        print(f"   Table ID: {self.table_id}")
        print(f"   Page ID: {self.page_id}")
        print(f"   URL: {self.url}")
        
        if self.columns:
            print(f"\n📋 Columns ({len(self.columns)} total):")
            for i, col in enumerate(self.columns[:10], 1):
                print(f"   {i}. {col.get('name')}")
            if len(self.columns) > 10:
                print(f"   ... and {len(self.columns) - 10} more")
        
        if self.rows:
            print(f"\n📊 Rows: {len(self.rows)} fetched")
            print(f"   Last fetched: {self.last_fetched}")
            
            # Show sample row
            if self.rows:
                print(f"\n📝 Sample Row:")
                sample = self.rows[0]
                print(f"   Name: {sample.row_name}")
                print(f"   ID: {sample.row_id}")
                print(f"   Updated: {sample.updated_at}")
                print(f"   Values: {len(sample.values)} columns")
        
        print("\n" + "=" * 80)
    
    def export_to_json(self, filename: str):
        """Export table data to JSON file."""
        data = {
            'metadata': {
                'doc_id': self.doc_id,
                'table_id': self.table_id,
                'table_name': self.table_name,
                'fetched_at': self.last_fetched,
                'row_count': len(self.rows)
            },
            'columns': self.columns,
            'rows': [row.to_dict() for row in self.rows]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"✅ Exported to {filename}")


## Example usage
# if __name__ == "__main__":
#     from dotenv import load_dotenv
#     load_dotenv()
    
#     # Example: Fetch Q3 2025 Roadmap with Status Notes
#     url = "https://coda.io/d/_dn6rnftKCGZ/Everything_suVyKToC#Q3-2025-Roadmap-overview_tuWR35uZ"
    
#     # Initialize table
#     table = CodaTable(url)
    
#     # Inspect table
#     table.print_summary()
    
#     # Fetch all data
#     table.fetch_columns()
#     table.fetch_rows(limit=20)
    
#     # Show summary
#     print(f"\n✅ Fetched {len(table.rows)} rows")
    
#     # Save to Snowflake
#     try:
#         success = table.save_to_snowflake(
#             table_name='coda_q3_roadmap',
#             database='proddb',
#             schema='fionafan',
#             mode='overwrite'
#         )
        
#         if success:
#             print("\n✅ Data saved to Snowflake: proddb.fionafan.coda_q3_roadmap")
#     except Exception as e:
#         print(f"\n❌ Error saving to Snowflake: {e}")
#         print("   Make sure your Snowflake credentials are configured")

