"""
Coda API Client

A client wrapper for interacting with Coda's REST API.
Handles authentication, request formatting, and URL parsing.
"""

import re
import requests
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs
from utils.logger import logger


class CodaClient:
    """Client for interacting with Coda API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Coda API client.
        
        Args:
            api_key: Coda API key. If not provided, will load from config.
        """
        if api_key:
            self.api_key = api_key
        else:
            from config.api_keys import CODA_API_KEY
            self.api_key = CODA_API_KEY
            
        if not self.api_key:
            raise ValueError("CODA_API_KEY not found. Please set it in your .env file.")
            
        self.base_url = 'https://coda.io/apis/v1'
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'curie-dashboard/1.0'
        })
    
    def parse_coda_url(self, url: str) -> Dict[str, str]:
        """
        Parse a Coda URL to extract document ID, page ID, and table fragment.
        
        Per Coda API docs: https://coda.io/developers/apis/v1#section/Using-the-API/Doc-IDs
        
        NOTE: Fragment IDs (like 'tudJtJVH') are NOT the actual table IDs!
        You must use resolveBrowserLink() to get the actual table ID (like 'table-U0LudJtJVH').
        
        Examples:
            https://coda.io/d/_dn6rnftKCGZ/Everything_suVyKToC
            → doc_id: "n6rnftKCGZ", page_id: "suVyKToC"
            
            https://coda.io/d/_dn6rnftKCGZ/Everything_suVyKToC#ALL-PROJECTS_tudJtJVH
            → doc_id: "n6rnftKCGZ", page_id: "suVyKToC", table_fragment: "tudJtJVH"
            → Use resolveBrowserLink to get actual table_id: "table-U0LudJtJVH"
        
        Args:
            url: Full Coda URL
            
        Returns:
            Dictionary with 'doc_id', 'page_id', 'table_fragment' (if present)
        """
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')
        
        result = {'original_url': url}
        
        # Extract doc_id (format: /d/{doc_id})
        # Doc IDs may have prefix like "_dn6rnftKCGZ" or "name_dn6rnftKCGZ"
        if len(path_parts) >= 3 and path_parts[1] == 'd':
            doc_id_raw = path_parts[2]
            # Handle different URL formats:
            # "_dn6rnftKCGZ" -> strip "_d" prefix -> "n6rnftKCGZ"
            # "nux-product_dn6rnftKCGZ" -> take after last underscore -> "dn6rnftKCGZ"
            if doc_id_raw.startswith('_d'):
                # Strip the "_d" prefix (e.g., "_dn6rnftKCGZ" -> "n6rnftKCGZ")
                doc_id = doc_id_raw[2:]
            elif doc_id_raw.startswith('_'):
                # Strip single underscore (e.g., "_abc123" -> "abc123")
                doc_id = doc_id_raw[1:]
            elif '_' in doc_id_raw:
                # Format like "nux-product_dn6rnftKCGZ" -> "dn6rnftKCGZ"
                doc_id = doc_id_raw.split('_')[-1]
            else:
                doc_id = doc_id_raw
            result['doc_id'] = doc_id
        
        # Extract page_id from the path (format: /PageName_pageId)
        if len(path_parts) >= 4:
            page_part = path_parts[3]
            result['full_page_part'] = page_part  # Keep the full part
            # Extract ID after last underscore (e.g., "Everything_suVyKToC" -> "suVyKToC")
            if '_' in page_part:
                result['page_id'] = page_part.split('_')[-1]
            else:
                result['page_id'] = page_part
        
        # Extract table fragment from URL fragment (after #)
        # IMPORTANT: This is NOT the actual table ID!
        if parsed.fragment:
            result['fragment_raw'] = parsed.fragment
            # Format: #ALL-PROJECTS_tudJtJVH or #View-Name_viewId
            if '_' in parsed.fragment:
                fragment_id = parsed.fragment.split('_')[-1]
                result['table_fragment'] = fragment_id  # e.g., "tudJtJVH"
                result['table_name'] = parsed.fragment.split('_')[0]  # e.g., "ALL-PROJECTS"
            else:
                result['table_fragment'] = parsed.fragment
        
        # Print parsed results
        print(f"\n📝 Parsed URL Components:")
        print(f"   Doc ID: {result.get('doc_id', 'N/A')}")
        print(f"   Page ID: {result.get('page_id', 'N/A')}")
        if 'table_fragment' in result:
            print(f"   Table Fragment: {result.get('table_fragment')} (from URL)")
            print(f"   Table Name: {result.get('table_name', 'N/A')}")
            print(f"   ⚠️  Note: Fragment is NOT the actual table ID!")
        print()
        
        logger.debug(f"Parsed URL: {url} -> {result}")
        logger.debug("Note: Use resolve_browser_link() to get the actual table ID")
        return result
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the Coda API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/docs' or '/docs/{doc_id}/tables')
            params: Query parameters
            json_data: JSON body for POST/PUT requests
            
        Returns:
            Response JSON data
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=30
            )
            
            # Log the request details
            logger.debug(f"{method} {url} - Status: {response.status_code}")
            
            # Handle different status codes
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise Exception(f"Unauthorized: Invalid API key or expired token")
            elif response.status_code == 403:
                raise Exception(f"Forbidden: API key does not have access to this resource")
            elif response.status_code == 404:
                raise Exception(f"Not Found: Resource does not exist - {url}")
            elif response.status_code == 429:
                raise Exception(f"Rate limit exceeded. Please try again later.")
            else:
                raise Exception(f"API error {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def get_doc_info(self, doc_id: str) -> Dict[str, Any]:
        """
        Get information about a Coda document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document information
        """
        logger.info(f"Fetching doc info for: {doc_id}")
        return self._make_request('GET', f'/docs/{doc_id}')
    
    def list_tables(self, doc_id: str) -> Dict[str, Any]:
        """
        List all tables in a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            List of tables
        """
        logger.info(f"Listing tables for doc: {doc_id}")
        return self._make_request('GET', f'/docs/{doc_id}/tables')
    
    def get_table_info(self, doc_id: str, table_id: str) -> Dict[str, Any]:
        """
        Get information about a specific table.
        
        Args:
            doc_id: Document ID
            table_id: Table ID
            
        Returns:
            Table information
        """
        logger.info(f"Fetching table info: {doc_id}/{table_id}")
        return self._make_request('GET', f'/docs/{doc_id}/tables/{table_id}')
    
    def get_table_rows(
        self, 
        doc_id: str, 
        table_id: str, 
        limit: int = 100,
        use_column_names: bool = True,
        value_format: str = 'simple'
    ) -> Dict[str, Any]:
        """
        Get rows from a table.
        
        Args:
            doc_id: Document ID
            table_id: Table ID or name
            limit: Maximum number of rows to return
            use_column_names: Return column names instead of IDs
            value_format: 'simple', 'simpleWithArrays', or 'rich'
            
        Returns:
            Table rows data
        """
        print(f"\n📥 Fetching Table Rows:")
        print(f"   Doc ID: {doc_id}")
        print(f"   Table ID: {table_id}")
        print(f"   Limit: {limit} rows")
        print(f"   Column Names: {use_column_names}")
        print()
        
        logger.info(f"Fetching rows from table: {doc_id}/{table_id}")
        
        params = {
            'limit': limit,
            'useColumnNames': use_column_names,
            'valueFormat': value_format
        }
        
        response = self._make_request('GET', f'/docs/{doc_id}/tables/{table_id}/rows', params=params)
        
        # Print summary of results
        items = response.get('items', [])
        print(f"✅ Retrieved {len(items)} rows")
        if items and len(items) > 0:
            columns = list(items[0].get('values', {}).keys())
            print(f"   Columns: {len(columns)} total")
        print()
        
        return response
    
    def resolve_browser_link(self, url: str) -> Dict[str, Any]:
        """
        Resolve a browser link to get the underlying resource.
        
        Args:
            url: Full Coda URL
            
        Returns:
            Resource information with actual table/page IDs
        """
        logger.info(f"Resolving browser link: {url}")
        
        response = self._make_request('GET', '/resolveBrowserLink', params={'url': url})
        
        # Print resolved resource information
        resource = response.get('resource', {})
        print(f"\n🔍 Resolved Resource:")
        print(f"   Type: {resource.get('type', 'N/A')}")
        print(f"   Name: {resource.get('name', 'N/A')}")
        print(f"   Actual ID: {resource.get('id', 'N/A')}")
        print(f"   API href: {resource.get('href', 'N/A')}")
        
        # Show parent info if available
        if 'parent' in resource:
            parent = resource['parent']
            print(f"\n   Parent Page:")
            print(f"     Name: {parent.get('name', 'N/A')}")
            print(f"     ID: {parent.get('id', 'N/A')}")
        print()
        
        return response
    
    def get_row_comments(self, doc_id: str, table_id: str, row_id: str) -> Dict[str, Any]:
        """
        Get comments/discussions on a specific row (if available).
        
        Note: This feature may require additional permissions and is not always available.
        
        Args:
            doc_id: Document ID
            table_id: Table ID
            row_id: Row ID
            
        Returns:
            Comments data if available
        """
        logger.info(f"Fetching comments for row: {row_id}")
        
        try:
            # Try to get row details with expanded fields
            response = self._make_request(
                'GET',
                f'/docs/{doc_id}/tables/{table_id}/rows/{row_id}'
            )
            return response
        except Exception as e:
            logger.warning(f"Could not fetch row comments: {e}")
            return {}
    
    def test_connection(self) -> bool:
        """
        Test if the API connection is working.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = self._make_request('GET', '/whoami')
            logger.info(f"✅ Connected to Coda API as: {response.get('name', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Coda API: {e}")
            return False


# Example usage
if __name__ == "__main__":
    try:
        client = CodaClient()
        
        # Test connection
        if client.test_connection():
            print("✅ Successfully connected to Coda API")
        else:
            print("❌ Failed to connect to Coda API")
            
    except Exception as e:
        print(f"❌ Error: {e}")

