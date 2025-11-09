#!/usr/bin/env python3
"""
Google Docs Exporter Workflow

Handles extraction of content from Google Docs and conversion to markdown format.

Inherits from GoogleAPIsMixin to access Google Docs service.
"""

import re
import sys
from datetime import datetime, timezone
from typing import Dict, Any


class GoogleDocsExporter:
    """
    Exports content from Google Docs to markdown format.

    Usage:
        exporter = GoogleDocsExporter(loop)  # loop must inherit GoogleAPIsMixin
        doc = exporter.fetch(url)
        markdown = exporter.export_as_markdown(url)
    """

    def __init__(self, loop_with_mixin):
        """
        Initialize with a loop that has GoogleAPIsMixin.

        Args:
            loop_with_mixin: A RAVL loop instance that inherits GoogleAPIsMixin
        """
        self.loop = loop_with_mixin

    def fetch(self, url: str) -> Dict[str, Any]:
        """
        Fetch content from Google Docs using Drive API markdown export.

        Uses Google Drive API's native export endpoint with mimeType=text/markdown
        to get the same markdown that Google Docs' "Download as Markdown" produces.

        Args:
            url: Google Docs URL

        Returns:
            Dict with:
            - 'text': Full markdown text content (from Drive API export)
            - 'title': Document title
            - 'last_modified': ISO timestamp of last modification
            - 'doc_id': Extracted document ID from URL

        Raises:
            ValueError: If URL is invalid
            Exception: If API request fails
        """
        if not self.loop.google_docs_service or not self.loop.google_drive_service:
            self.loop.init_google_services()

        # Extract document ID from URL
        doc_id_match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url)
        if not doc_id_match:
            raise ValueError(f"Invalid Google Docs URL: {url}")

        doc_id = doc_id_match.group(1)

        # Get document metadata from Docs API
        document = self.loop.google_docs_service.documents().get(documentId=doc_id).execute()

        # Export as markdown from Drive API
        try:
            markdown_content = self.loop.google_drive_service.files().export(
                fileId=doc_id,
                mimeType='text/markdown'
            ).execute().decode('utf-8')
        except Exception as e:
            raise Exception(f"Failed to export document as markdown: {e}")

        return {
            'text': markdown_content,
            'title': document.get('title', ''),
            'last_modified': document.get('modifiedTime', datetime.now(timezone.utc).isoformat() + '+00:00'),
            'doc_id': doc_id
        }

    def export_as_markdown(self, url: str) -> str:
        """
        Fetch document and return as markdown string.

        Args:
            url: Google Docs URL

        Returns:
            Markdown formatted string

        Raises:
            ValueError: If URL is invalid
            Exception: If API request fails
        """
        doc = self.fetch(url)
        return doc['text']
