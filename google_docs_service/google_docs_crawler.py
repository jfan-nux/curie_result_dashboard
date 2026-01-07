#!/usr/bin/env python3
"""
Google Docs Crawler

Crawls Google Docs to extract:
- Text content
- Images with LLM-based descriptions

Authentication Methods:
1. Service Account (recommended for Databricks/server environments)
   - Set GOOGLE_SERVICE_ACCOUNT_JSON env var with the JSON key content
   - Or set GOOGLE_SERVICE_ACCOUNT_FILE env var with path to JSON key file
   
2. OAuth (for local development with interactive sign-in)
   - Set GOOGLE_OAUTH_CREDENTIALS_FILE env var with path to credentials.json
   - Token will be saved to GOOGLE_OAUTH_TOKEN_FILE (default: token.json)

Note on Databricks:
-------------------
OAuth requires interactive sign-in which won't work on Databricks.
Use Service Account authentication instead:
1. Create a Service Account in Google Cloud Console
2. Enable Google Docs API and Google Drive API
3. Download the JSON key
4. Store in Databricks Secrets: dbutils.secrets.put(scope="google", key="service_account_json")
5. In your code: os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'] = dbutils.secrets.get("google", "service_account_json")
"""

import os
import re
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv
from utils.logger import get_logger
from utils.portkey_llm import get_portkey_llm

# Load environment variables from .env file
load_dotenv()

try:
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


# Scopes required for reading docs and downloading images
SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]


@dataclass
class GoogleDocContent:
    """Container for crawled Google Doc content."""
    doc_id: str
    title: str = ""
    text_content: str = ""
    images: List[Dict[str, Any]] = field(default_factory=list)
    image_descriptions: List[str] = field(default_factory=list)
    combined_summary: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'doc_id': self.doc_id,
            'title': self.title,
            'text_content': self.text_content,
            'image_count': len(self.images),
            'image_descriptions': self.image_descriptions,
            'combined_summary': self.combined_summary,
            'error': self.error
        }


class GoogleDocsCrawler:
    """
    Crawler for Google Docs with image extraction and LLM analysis.
    
    Supports:
    - Service Account auth (for Databricks/servers)
    - OAuth auth (for local development)
    - Text content extraction
    - Image download and analysis
    - Treatment vs Control comparison detection
    """
    
    def __init__(self):
        """Initialize the Google Docs crawler."""
        self.logger = get_logger(__name__)
        self.credentials = None
        self.docs_service = None
        self.drive_service = None
        self.temp_dir = None
        self.llm = get_portkey_llm()
        
        if not GOOGLE_API_AVAILABLE:
            self.logger.warning("Google API libraries not available. Install with: pip install google-api-python-client google-auth-oauthlib")
        else:
            self._initialize_credentials()
    
    def _initialize_credentials(self):
        """Initialize Google API credentials."""
        # Try Service Account first (preferred for Databricks)
        if self._try_service_account_auth():
            return
        
        # Fall back to OAuth (for local development)
        if self._try_oauth_auth():
            return
        
        self.logger.warning("No Google authentication configured. Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_OAUTH_CREDENTIALS_FILE")
    
    def _try_service_account_auth(self) -> bool:
        """Try to authenticate using a service account."""
        # Check for JSON content in env var
        sa_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        if sa_json:
            try:
                sa_info = json.loads(sa_json)
                
                # Debug: Check what the private key looks like
                pk = sa_info.get('private_key', '')

                # Fix private key: dotenv loads \n as literal backslash-n, 
                # but the private key needs actual newlines
                if 'private_key' in sa_info and '\\n' in sa_info['private_key']:
                    sa_info['private_key'] = sa_info['private_key'].replace('\\n', '\n')
                self.credentials = service_account.Credentials.from_service_account_info(
                    sa_info, scopes=SCOPES
                )
                self._build_services()
                self.logger.info("✅ Authenticated with Service Account (from env JSON)")
                return True
            except Exception as e:
                self.logger.error(f"Failed to load service account from JSON: {e}")
                import traceback
                traceback.print_exc()
        
        # Check for JSON file path
        sa_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
        if sa_file and Path(sa_file).exists():
            try:
                self.credentials = service_account.Credentials.from_service_account_file(
                    sa_file, scopes=SCOPES
                )
                self._build_services()
                self.logger.info(f"✅ Authenticated with Service Account (from file: {sa_file})")
                return True
            except Exception as e:
                self.logger.error(f"Failed to load service account from file: {e}")
        
        return False
    
    def _try_oauth_auth(self) -> bool:
        """Try to authenticate using OAuth (interactive sign-in)."""
        creds = None
        token_file = os.getenv('GOOGLE_OAUTH_TOKEN_FILE', 'token.json')
        credentials_file = os.getenv('GOOGLE_OAUTH_CREDENTIALS_FILE')
        
        # Check for existing token
        if Path(token_file).exists():
            try:
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            except Exception:
                pass
        
        # Refresh or get new credentials
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        
        if not creds or not creds.valid:
            if not credentials_file or not Path(credentials_file).exists():
                return False
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save token for future use
                with open(token_file, 'w') as f:
                    f.write(creds.to_json())
            except Exception as e:
                self.logger.error(f"OAuth authentication failed: {e}")
                return False
        
        self.credentials = creds
        self._build_services()
        self.logger.info("✅ Authenticated with OAuth")
        return True
    
    def _build_services(self):
        """Build Google API service clients."""
        self.docs_service = build('docs', 'v1', credentials=self.credentials)
        self.drive_service = build('drive', 'v3', credentials=self.credentials)
    
    def is_available(self) -> bool:
        """Check if the crawler is properly configured."""
        return GOOGLE_API_AVAILABLE and self.credentials is not None
    
    def extract_doc_id(self, url: str) -> Optional[str]:
        """
        Extract Google Doc ID from various URL formats.
        
        Supported formats:
        - https://docs.google.com/document/d/{doc_id}/edit
        - https://docs.google.com/document/d/{doc_id}/view
        - https://docs.google.com/document/d/{doc_id}
        - Just the doc_id itself
        
        Args:
            url: Google Doc URL or ID
            
        Returns:
            Document ID or None if not parseable
        """
        if not url:
            return None
        
        url = url.strip()
        
        # If it's already just an ID (no slashes or dots suggesting URL)
        if '/' not in url and '.' not in url and len(url) > 20:
            return url
        
        # Parse URL formats
        patterns = [
            r'docs\.google\.com/document/d/([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _create_temp_dir(self):
        """Create a temporary directory for storing images."""
        if self.temp_dir is None:
            self.temp_dir = tempfile.mkdtemp(prefix='gdocs_crawl_')
            self.logger.info(f"Created temp directory: {self.temp_dir}")
    
    def cleanup(self):
        """Clean up temporary files and directories."""
        if self.temp_dir and Path(self.temp_dir).exists():
            try:
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"🧹 Cleaned up temp directory: {self.temp_dir}")
                self.temp_dir = None
            except Exception as e:
                self.logger.error(f"Failed to cleanup temp directory: {e}")
    
    def _extract_text_from_content(self, content: List[Dict]) -> str:
        """
        Extract plain text from Google Docs content structure.
        
        Args:
            content: The 'content' array from Google Docs API response
            
        Returns:
            Extracted text content
        """
        text_parts = []
        
        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                for elem in paragraph.get('elements', []):
                    if 'textRun' in elem:
                        text_parts.append(elem['textRun'].get('content', ''))
            elif 'table' in element:
                # Extract text from tables
                table = element['table']
                for row in table.get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        cell_text = self._extract_text_from_content(cell.get('content', []))
                        if cell_text.strip():
                            text_parts.append(cell_text)
        
        return ''.join(text_parts)
    
    def _extract_images_from_content(self, content: List[Dict], doc_id: str) -> List[Dict[str, Any]]:
        """
        Extract image metadata from Google Docs content.
        
        Args:
            content: The 'content' array from Google Docs API response
            doc_id: Document ID for context
            
        Returns:
            List of image metadata dictionaries
        """
        images = []
        
        for idx, element in enumerate(content):
            if 'paragraph' in element:
                paragraph = element['paragraph']
                for elem in paragraph.get('elements', []):
                    if 'inlineObjectElement' in elem:
                        inline_obj = elem['inlineObjectElement']
                        obj_id = inline_obj.get('inlineObjectId')
                        if obj_id:
                            images.append({
                                'object_id': obj_id,
                                'index': idx,
                                'doc_id': doc_id
                            })
        
        return images
    
    def _download_image(self, image_uri: str, image_id: str) -> Optional[str]:
        """
        Download an image from Google Docs.
        
        Args:
            image_uri: The image content URI
            image_id: Identifier for the image
            
        Returns:
            Path to downloaded image or None if failed
        """
        self._create_temp_dir()
        
        try:
            import requests
            
            # Download image
            response = requests.get(image_uri, timeout=30)
            if response.status_code != 200:
                self.logger.warning(f"Failed to download image {image_id}: HTTP {response.status_code}")
                return None
            
            # Determine file extension from content type
            content_type = response.headers.get('Content-Type', 'image/png')
            ext = '.png'
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'gif' in content_type:
                ext = '.gif'
            elif 'webp' in content_type:
                ext = '.webp'
            
            # Save to temp file
            image_path = Path(self.temp_dir) / f"{image_id}{ext}"
            with open(image_path, 'wb') as f:
                f.write(response.content)
            
            self.logger.info(f"📥 Downloaded image: {image_path.name}")
            return str(image_path)
            
        except Exception as e:
            self.logger.error(f"Error downloading image {image_id}: {e}")
            return None
    
    def _analyze_images_with_llm(
        self, 
        image_paths: List[str], 
        text_context: str,
        is_experiment_doc: bool = True
    ) -> List[str]:
        """
        Analyze images using LLM with context from the document text.
        
        Args:
            image_paths: List of paths to image files
            text_context: Text content from the document for context
            is_experiment_doc: Whether this is an experiment/brief document
            
        Returns:
            List of image descriptions
        """
        if not self.llm.is_available():
            self.logger.warning("LLM not available for image analysis")
            return ["[LLM not available for image analysis]" for _ in image_paths]
        
        descriptions = []
        
        # Prepare context prompt based on document type
        if is_experiment_doc:
            base_prompt = f"""You are analyzing images from an experiment brief/design document. 

Document context:
{text_context[:3000]}  # Limit context length

For each image, provide a detailed description including:
1. What type of image/chart/screenshot this is
2. Key information visible (data, text, UI elements)
3. If this appears to be Treatment vs Control comparison:
   - Clearly identify which is Treatment and which is Control
   - List the specific DIFFERENCES between Treatment and Control
   - Note any visual changes, text changes, or functional differences
4. Any metrics, numbers, or key data points visible

Be specific and detailed. If you see UI mockups, describe the user experience changes."""
        else:
            base_prompt = f"""Analyze this image from a document. Describe what you see in detail.

Document context:
{text_context[:2000]}

Provide:
1. Type of image (chart, diagram, screenshot, etc.)
2. Key information visible
3. Any text, numbers, or data shown"""
        
        for i, image_path in enumerate(image_paths):
            try:
                prompt = f"""{base_prompt}

This is image {i+1} of {len(image_paths)} in the document.
Describe this image thoroughly."""
                
                description = self.llm.analyze_image(
                    image_path=image_path,
                    prompt=prompt,
                    model="gpt-4o",  # Use vision-capable model
                    max_tokens=1500,
                    temperature=0.2
                )
                
                if description:
                    descriptions.append(description)
                else:
                    descriptions.append("[Failed to analyze image]")
                    
            except Exception as e:
                self.logger.error(f"Error analyzing image {i+1}: {e}")
                descriptions.append(f"[Error analyzing image: {str(e)}]")
        
        return descriptions
    
    def crawl_document(
        self, 
        doc_url_or_id: str,
        analyze_images: bool = True,
        is_experiment_doc: bool = True
    ) -> GoogleDocContent:
        """
        Crawl a Google Doc to extract text and image content.
        
        Args:
            doc_url_or_id: Google Doc URL or document ID
            analyze_images: Whether to analyze images with LLM
            is_experiment_doc: Whether this is an experiment document (affects image analysis prompts)
            
        Returns:
            GoogleDocContent object with extracted content
        """
        doc_id = self.extract_doc_id(doc_url_or_id)
        
        if not doc_id:
            return GoogleDocContent(
                doc_id="",
                error=f"Could not extract document ID from: {doc_url_or_id}"
            )
        
        if not self.is_available():
            return GoogleDocContent(
                doc_id=doc_id,
                error="Google Docs crawler not properly configured. Check authentication."
            )
        
        result = GoogleDocContent(doc_id=doc_id)
        
        try:
            # Fetch document content
            self.logger.info(f"📄 Fetching Google Doc: {doc_id}")
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            
            result.title = doc.get('title', 'Untitled')
            self.logger.info(f"   Title: {result.title}")
            
            # Extract text content
            content = doc.get('body', {}).get('content', [])
            result.text_content = self._extract_text_from_content(content)
            self.logger.info(f"   Text length: {len(result.text_content)} chars")
            
            # Extract and process images
            inline_objects = doc.get('inlineObjects', {})
            image_paths = []
            
            if inline_objects:
                self.logger.info(f"   Found {len(inline_objects)} images")
                
                for obj_id, obj_data in inline_objects.items():
                    embedded = obj_data.get('inlineObjectProperties', {}).get('embeddedObject', {})
                    
                    # Get image URI
                    image_props = embedded.get('imageProperties', {})
                    content_uri = image_props.get('contentUri')
                    
                    if content_uri:
                        result.images.append({
                            'object_id': obj_id,
                            'uri': content_uri,
                            'title': embedded.get('title', ''),
                            'description': embedded.get('description', '')
                        })
                        
                        # Download image
                        image_path = self._download_image(content_uri, obj_id)
                        if image_path:
                            image_paths.append(image_path)
            
            # Analyze images with LLM
            if analyze_images and image_paths:
                self.logger.info(f"🔍 Analyzing {len(image_paths)} images with LLM...")
                result.image_descriptions = self._analyze_images_with_llm(
                    image_paths=image_paths,
                    text_context=result.text_content,
                    is_experiment_doc=is_experiment_doc
                )
            
            # Create combined summary
            result.combined_summary = self._create_combined_summary(result)
            
            self.logger.info(f"✅ Successfully crawled: {result.title}")
            
        except Exception as e:
            error_msg = str(e)
            if 'HttpError 404' in error_msg:
                result.error = f"Document not found or not accessible: {doc_id}"
            elif 'HttpError 403' in error_msg:
                result.error = f"Permission denied. Ensure the document is shared with the service account or accessible."
            else:
                result.error = f"Error crawling document: {error_msg}"
            self.logger.error(result.error)
        
        return result
    
    def _create_combined_summary(self, content: GoogleDocContent) -> str:
        """
        Create a combined summary of document content and image descriptions.
        
        Args:
            content: Crawled document content
            
        Returns:
            Combined summary string
        """
        parts = []
        
        # Add title
        if content.title:
            parts.append(f"# {content.title}\n")
        
        # Add text content (truncated if too long)
        if content.text_content:
            text = content.text_content.strip()
            if len(text) > 5000:
                text = text[:5000] + "...[truncated]"
            parts.append(f"## Document Content\n{text}\n")
        
        # Add image descriptions
        if content.image_descriptions:
            parts.append(f"\n## Image Analysis ({len(content.image_descriptions)} images)\n")
            for i, desc in enumerate(content.image_descriptions, 1):
                parts.append(f"\n### Image {i}\n{desc}\n")
        
        return '\n'.join(parts)
    
    def crawl_multiple_documents(
        self, 
        doc_urls: List[str],
        analyze_images: bool = True
    ) -> Dict[str, GoogleDocContent]:
        """
        Crawl multiple Google Docs.
        
        Args:
            doc_urls: List of Google Doc URLs or IDs
            analyze_images: Whether to analyze images with LLM
            
        Returns:
            Dictionary mapping doc URLs to their content
        """
        results = {}
        
        for url in doc_urls:
            if url and url.strip():
                results[url] = self.crawl_document(
                    doc_url_or_id=url,
                    analyze_images=analyze_images
                )
        
        # Cleanup all temp files after processing
        self.cleanup()
        
        return results


# Singleton instance
_crawler_instance = None


def get_google_docs_crawler() -> GoogleDocsCrawler:
    """
    Get shared GoogleDocsCrawler instance (singleton pattern).
    
    Returns:
        GoogleDocsCrawler instance
    """
    global _crawler_instance
    if _crawler_instance is None:
        _crawler_instance = GoogleDocsCrawler()
    return _crawler_instance

