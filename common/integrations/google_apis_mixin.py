#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Google APIs Mixin for RAVL Loops

Provides integration with Google services:
- Google Docs, Slides, Sheets (reading content)
- Google Workspace Admin SDK (user directory)

Used by agents that need to fetch data from Google services.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Try to import Google API libraries
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False


class GoogleAPIsMixin:
    """
    Mixin providing low-level Google API service initialization for RAVL loops.

    Initializes and provides lazy-loaded Google API services:
    - Google Docs, Slides, Sheets (via init_google_services)
    - Google Workspace Admin SDK (via init_google_workspace_service)

    For workflow-specific operations, use the specialized workflow classes:
    - GoogleDocsExporter - Extract content from Google Docs
    - GoogleDocsRevisionTracker - Track document revision history
    - GoogleWorkspaceUserFetcher - Fetch users from Workspace Directory
    - GoogleSlidesExporter - Extract content from Google Slides
    - GoogleSheetsAnalyzer - Analyze Google Sheets

    Usage:
        from ravl.common.integrations import GoogleAPIsMixin, GoogleDocsExporter

        class MyLoop(BaseRAVLLoop, GoogleAPIsMixin):
            def act(self, reflection):
                self.init_google_services()
                exporter = GoogleDocsExporter(self)
                doc = exporter.fetch(url)

    Note: Service properties are lazy-initialized on first use
    """

    @property
    def google_docs_service(self):
        """Lazy-init Google Docs service"""
        if not hasattr(self, '_google_docs_service'):
            self._google_docs_service = None
        return self._google_docs_service

    @google_docs_service.setter
    def google_docs_service(self, value):
        self._google_docs_service = value

    @property
    def google_slides_service(self):
        """Lazy-init Google Slides service"""
        if not hasattr(self, '_google_slides_service'):
            self._google_slides_service = None
        return self._google_slides_service

    @google_slides_service.setter
    def google_slides_service(self, value):
        self._google_slides_service = value

    @property
    def google_sheets_service(self):
        """Lazy-init Google Sheets service"""
        if not hasattr(self, '_google_sheets_service'):
            self._google_sheets_service = None
        return self._google_sheets_service

    @google_sheets_service.setter
    def google_sheets_service(self, value):
        self._google_sheets_service = value

    @property
    def google_workspace_service(self):
        """Lazy-init Google Workspace service"""
        if not hasattr(self, '_google_workspace_service'):
            self._google_workspace_service = None
        return self._google_workspace_service

    @google_workspace_service.setter
    def google_workspace_service(self, value):
        self._google_workspace_service = value

    @property
    def google_drive_service(self):
        """Lazy-init Google Drive service"""
        if not hasattr(self, '_google_drive_service'):
            self._google_drive_service = None
        return self._google_drive_service

    @google_drive_service.setter
    def google_drive_service(self, value):
        self._google_drive_service = value

    # ==================== GOOGLE DOCS/SLIDES/SHEETS ====================

    def init_google_services(self, handbook_root: Optional[Path] = None):
        """
        Initialize Google Docs, Slides, and Sheets API services

        Uses service account credentials from GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_FILE environment variable.

        Args:
            handbook_root: Optional handbook root path (for backward compatibility)

        Raises:
            Exception: If Google APIs not available or credentials not found
        """
        if not GOOGLE_APIS_AVAILABLE:
            raise Exception("Google APIs not available - install google-api-python-client and google-auth")

        scopes = [
            'https://www.googleapis.com/auth/documents.readonly',
            'https://www.googleapis.com/auth/presentations.readonly',
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]

        # Get service account credentials file path
        cred_file = os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_FILE')

        if not cred_file or not os.path.exists(cred_file):
            raise Exception(
                f"Service account credentials file not found: {cred_file or 'GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_FILE not set'}\n"
                f"  Set GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_FILE environment variable to the path of your service account JSON file."
            )

        try:
            credentials = service_account.Credentials.from_service_account_file(
                cred_file,
                scopes=scopes
            )
            print(f"  🔐  Using service account credentials from {cred_file}", file=sys.stderr)
        except Exception as e:
            raise Exception(f"Error loading service account credentials from {cred_file}: {e}")

        self.google_docs_service = build('docs', 'v1', credentials=credentials)
        self.google_slides_service = build('slides', 'v1', credentials=credentials)
        self.google_sheets_service = build('sheets', 'v4', credentials=credentials)
        self.google_drive_service = build('drive', 'v3', credentials=credentials)

    # ==================== GOOGLE WORKSPACE ADMIN SDK ====================

    def init_google_workspace_service(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Workspace Admin SDK Directory API service

        Supports four authentication methods (checked in order):
        1. credentials_path parameter (explicit path to JSON key file)
        2. GOOGLE_APPLICATION_CREDENTIALS env var (path to JSON key file)
        3. GOOGLE_SERVICE_ACCOUNT_KEY env var (JSON key content as string)
        4. ~/.config/gcloud/application_default_credentials.json (gcloud default)

        Args:
            credentials_path: Optional path to service account credentials JSON file

        Raises:
            Exception: If Google APIs not available or credentials not found
        """
        if not GOOGLE_APIS_AVAILABLE:
            raise Exception("Google APIs not available - install google-api-python-client and google-auth")

        credentials = None

        # Option 1: Explicit path parameter
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/admin.directory.user.readonly']
            )
            print(f"  🔐  Using explicit credentials path", file=sys.stderr)

        # Option 2: GOOGLE_APPLICATION_CREDENTIALS (file path)
        elif os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            key_path = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
            if os.path.exists(key_path):
                credentials = service_account.Credentials.from_service_account_file(
                    key_path,
                    scopes=['https://www.googleapis.com/auth/admin.directory.user.readonly']
                )
                print(f"  🔐  Using GOOGLE_APPLICATION_CREDENTIALS", file=sys.stderr)

        # Option 3: GOOGLE_SERVICE_ACCOUNT_KEY (JSON content as string)
        elif os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY'):
            import json
            key_json = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_KEY'])
            credentials = service_account.Credentials.from_service_account_info(
                key_json,
                scopes=['https://www.googleapis.com/auth/admin.directory.user.readonly']
            )
            print(f"  🔐  Using GOOGLE_SERVICE_ACCOUNT_KEY", file=sys.stderr)

        # Option 4: gcloud application default credentials
        else:
            gcloud_default = os.path.expanduser('~/.config/gcloud/application_default_credentials.json')
            if os.path.exists(gcloud_default):
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        gcloud_default,
                        scopes=['https://www.googleapis.com/auth/admin.directory.user.readonly']
                    )
                    print(f"  🔐  Using gcloud application default credentials", file=sys.stderr)
                except Exception:
                    # File exists but is not a service account key (likely user credentials)
                    # This is fine - we'll fall through to the error below
                    pass

        if not credentials:
            raise Exception(
                "Google Workspace credentials not found. "
                "Need service account credentials with domain-wide delegation. "
                "Set GOOGLE_APPLICATION_CREDENTIALS (file path to service account key) or "
                "GOOGLE_SERVICE_ACCOUNT_KEY (JSON key content as string)"
            )

        # Enable domain-wide delegation if needed
        # The service account must be configured in Google Workspace admin console
        # with domain-wide delegation enabled

        self.google_workspace_service = build('admin', 'directory_v1', credentials=credentials)

        print(f"  ✓ Initialized Google Workspace Admin SDK", file=sys.stderr)
