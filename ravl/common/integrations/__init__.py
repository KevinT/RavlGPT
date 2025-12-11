"""
External System Integrations

Provides integrations with external systems and utilities:
- Google Workspace APIs
- Credential validation
- Context7 API documentation fetching
- Learning file migration
"""

import sys
from pathlib import Path

# Add current directory to path for imports
_script_dir = Path(__file__).parent
sys.path.insert(0, str(_script_dir))

from credential_validator import CredentialValidator
from context7_fetcher import Context7Fetcher, fetch_context7_docs_for_loop
from google_apis_mixin import GoogleAPIsMixin
from google_docs_exporter import GoogleDocsExporter
from google_docs_revision_tracker import GoogleDocsRevisionTracker
from google_workspace_user_fetcher import GoogleWorkspaceUserFetcher
from google_slides_exporter import GoogleSlidesExporter
from google_sheets_analyzer import GoogleSheetsAnalyzer
from google_sheets_revision_tracker import GoogleSheetsRevisionTracker

__all__ = [
    'CredentialValidator',
    'Context7Fetcher',
    'fetch_context7_docs_for_loop',
    'GoogleAPIsMixin',
    'GoogleDocsExporter',
    'GoogleDocsRevisionTracker',
    'GoogleWorkspaceUserFetcher',
    'GoogleSlidesExporter',
    'GoogleSheetsAnalyzer',
    'GoogleSheetsRevisionTracker',
]
