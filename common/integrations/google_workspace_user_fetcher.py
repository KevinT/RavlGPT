#!/usr/bin/env python3
"""
Google Workspace User Fetcher Workflow

Handles fetching user directories from Google Workspace Admin SDK.

Inherits from GoogleAPIsMixin to access Google Workspace service.
"""

import sys
from typing import Dict, Any, Optional


class GoogleWorkspaceUserFetcher:
    """
    Fetches users from Google Workspace Directory API.

    Usage:
        fetcher = GoogleWorkspaceUserFetcher(loop)  # loop must inherit GoogleAPIsMixin
        result = fetcher.fetch_users(customer_id='my_customer')
        users = result['users']
    """

    def __init__(self, loop_with_mixin):
        """
        Initialize with a loop that has GoogleAPIsMixin.

        Args:
            loop_with_mixin: A RAVL loop instance that inherits GoogleAPIsMixin
        """
        self.loop = loop_with_mixin

    def fetch_users(
        self,
        customer_id: str = 'my_customer',
        max_results: int = 500,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch users from Google Workspace Directory API.

        Args:
            customer_id: Workspace customer ID (default: 'my_customer' for current domain)
            max_results: Maximum results per page (1-500, default 500)
            query: Optional query string to filter users (e.g., "orgName=Engineering")

        Returns:
            Dict with:
            - 'users': List of user objects with full details
            - 'total_count': Total number of users fetched
            - 'pages_fetched': Number of pages retrieved
            - 'query_used': The query string used
            - 'customer_id': The customer ID used

        Raises:
            Exception: If API request fails

        Example:
            result = fetcher.fetch_users()
            for user in result['users']:
                print(f"{user['name']} - {user['primaryEmail']}")
        """
        if not self.loop.google_workspace_service:
            self.loop.init_google_workspace_service()

        all_users = []
        page_token = None
        page_count = 0

        try:
            while True:
                # Build request parameters
                request_params = {
                    'customer': customer_id,
                    'maxResults': min(max_results, 500),  # API limit is 500
                    'projection': 'full',  # Get all user fields
                    'orderBy': 'email'
                }

                if query:
                    request_params['query'] = query

                if page_token:
                    request_params['pageToken'] = page_token

                # Execute request
                response = self.loop.google_workspace_service.users().list(**request_params).execute()

                # Extract users from response
                users = response.get('users', [])
                all_users.extend(users)
                page_count += 1

                from pathlib import Path
                _utils_dir = Path(__file__).parent.parent / 'utils'
                import sys
                if str(_utils_dir) not in sys.path:
                    sys.path.insert(0, str(_utils_dir))
                from logging_utils import log_execution
                log_execution(f"Fetched page {page_count}: {len(users)} users", status='info')

                # Check if there are more pages
                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            log_execution(f"Total users fetched: {len(all_users)}", status='success')

            return {
                'users': all_users,
                'total_count': len(all_users),
                'pages_fetched': page_count,
                'query_used': query,
                'customer_id': customer_id
            }

        except Exception as e:
            log_execution(f"Google Workspace API request failed: {e}", status='error')
            raise
