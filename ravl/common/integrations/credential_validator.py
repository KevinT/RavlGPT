#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Credential Validator for RAVL Data Ingestion

Detects which APIs/services the generated code uses and validates
that required credentials are available before execution.

Supports:
- Notion (NOTION_API_KEY)
- HiBob (HIBOB_API_TOKEN, HIBOB_SERVICE_USER_ID)
- Generic APIs (API_KEY, ACCESS_TOKEN, etc.)
"""

import os
import re
from typing import List, Tuple, Dict, Optional


class CredentialValidator:
    """Validates credentials for API integration code"""

    # Mapping of Python packages/imports to required environment variables
    CREDENTIAL_MAP = {
        'notion_client': {
            'env_vars': ['NOTION_API_KEY'],
            'display_name': 'Notion API',
            'setup_url': 'https://www.notion.com/my-integrations'
        },
        'hibob': {
            'env_vars': ['HIBOB_API_TOKEN', 'HIBOB_SERVICE_USER_ID'],
            'display_name': 'HiBob API',
            'setup_url': 'https://apidocs.hibob.com'
        },
        'google': {
            'env_vars': ['GOOGLE_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS'],
            'display_name': 'Google APIs',
            'setup_url': 'https://developers.google.com/workspace/guides/create-credentials'
        },
        'openai': {
            'env_vars': ['OPENAI_API_KEY'],
            'display_name': 'OpenAI API',
            'setup_url': 'https://platform.openai.com/api-keys'
        },
        'anthropic': {
            'env_vars': ['ANTHROPIC_API_KEY'],
            'display_name': 'Anthropic Claude API',
            'setup_url': 'https://console.anthropic.com/account/keys'
        },
        'notion': {
            'env_vars': ['NOTION_API_KEY', 'NOTION_API_TOKEN', 'NOTION_TOKEN'],  # Accept any of these
            'display_name': 'Notion API',
            'setup_url': 'https://www.notion.com/my-integrations'
        }
    }

    @staticmethod
    def detect_required_credentials(code: str) -> Dict[str, List[str]]:
        """
        Analyze generated code and detect which APIs it uses

        Args:
            code: Python code string to analyze

        Returns:
            Dict mapping API name to required env vars
            Example: {'notion_client': ['NOTION_API_KEY'], 'hibob': ['HIBOB_API_TOKEN']}
        """
        required = {}

        # Check for imports
        for api, config in CredentialValidator.CREDENTIAL_MAP.items():
            # Look for import statements
            if re.search(rf'import {api}|from {api}', code, re.IGNORECASE):
                required[api] = config['env_vars']

        # Also check for common string patterns that indicate API usage
        patterns = {
            'notion': [r'NOTION_TOKEN', r'notion\.com', r'api\.notion\.com', r'databases.*query', r'Client\(auth=.*NOTION', r'database_id'],
            'hibob': [r'hibob', r'HIBOB_API_TOKEN', r'HIBOB_SERVICE_USER_ID', r'api\.hibob\.com'],
            'google': [r'google\.', r'Google', r'GOOGLE_API', r'googleapis\.com'],
        }

        for api, patterns_list in patterns.items():
            if api not in required:
                for pattern in patterns_list:
                    if re.search(pattern, code, re.IGNORECASE):
                        if api in CredentialValidator.CREDENTIAL_MAP:
                            required[api] = CredentialValidator.CREDENTIAL_MAP[api]['env_vars']
                        break

        # Consolidate: if we have notion_client, use its credentials for notion patterns too
        if 'notion_client' in required and 'notion' in required:
            # Merge notion's env_vars into notion_client and remove notion
            required['notion_client'].extend([v for v in required['notion'] if v not in required['notion_client']])
            del required['notion']

        return required

    @staticmethod
    def validate_credentials(required_creds: Dict[str, List[str]]) -> Tuple[bool, str, List[str]]:
        """
        Check if required credentials are available in environment

        For APIs with multiple credential options (e.g., NOTION_API_KEY or NOTION_TOKEN),
        at least ONE must be present.

        Args:
            required_creds: Dict of API to required env vars (from detect_required_credentials)

        Returns:
            Tuple of (all_present: bool, message: str, missing_vars: List[str])
        """
        missing_vars = []
        details = []

        for api, env_vars in required_creds.items():
            api_config = CredentialValidator.CREDENTIAL_MAP.get(api, {})
            api_display = api_config.get('display_name', api)

            # Check which credentials are present
            present_vars = [var for var in env_vars if os.environ.get(var)]
            missing_api_vars = [var for var in env_vars if not os.environ.get(var)]

            # For Notion (and similar): need at least ONE of the credential options
            if len(env_vars) > 1:  # Multiple options available
                if present_vars:
                    details.append(f"  ✓ {api_display}: Ready (using {present_vars[0]})")
                else:
                    missing_vars.extend(env_vars)
                    details.append(f"  ❌ {api_display}: Missing at least one of {', '.join(env_vars)}")
            else:  # Single required credential
                if missing_api_vars:
                    missing_vars.extend(missing_api_vars)
                    details.append(f"  ❌ {api_display}: Missing {', '.join(missing_api_vars)}")
                else:
                    details.append(f"  ✓ {api_display}: Ready")

        if missing_vars:
            message = "Missing required credentials:\n" + "\n".join(details)
            return False, message, missing_vars

        message = "All credentials available:\n" + "\n".join(details)
        return True, message, []

    @staticmethod
    def get_setup_instructions(api_name: str) -> str:
        """
        Get setup instructions for a specific API

        Args:
            api_name: API name (e.g., 'notion', 'hibob')

        Returns:
            Setup instructions string
        """
        config = CredentialValidator.CREDENTIAL_MAP.get(api_name, {})

        if not config:
            return f"Unknown API: {api_name}"

        display = config.get('display_name', api_name)
        url = config.get('setup_url', '')
        env_vars = config.get('env_vars', [])

        instructions = f"""
{display} Setup Instructions
{'=' * 50}

1. Get your credentials at: {url}

2. Set environment variables locally:
"""

        for var in env_vars:
            instructions += f"   export {var}=\"your-key-here\"\n"

        if api_name == 'notion':
            instructions += """
   Or on macOS with Homebrew:
   echo 'export NOTION_API_KEY="your-key"' >> ~/.zshrc
   source ~/.zshrc

3. Test the connection:
   python3 -c "from notion_client import Client; Client(auth=os.environ['NOTION_API_KEY'])"
"""
        elif api_name == 'hibob':
            instructions += """
   Or on macOS with Homebrew:
   echo 'export HIBOB_API_TOKEN="your-token"' >> ~/.zshrc
   echo 'export HIBOB_SERVICE_USER_ID="your-id"' >> ~/.zshrc
   source ~/.zshrc
"""

        instructions += f"""
4. For GitHub Actions, add these as repository secrets:
   Settings → Secrets and variables → Actions → New repository secret
"""

        return instructions

    @staticmethod
    def get_missing_credentials_error(missing_vars: List[str], api_usage: Dict[str, List[str]]) -> str:
        """
        Generate detailed error message about missing credentials

        Args:
            missing_vars: List of missing environment variables
            api_usage: Dict of which APIs need which variables

        Returns:
            Formatted error message with setup guidance
        """
        error = """
❌ CREDENTIAL ERROR: Code requires credentials that are not set

The generated code needs the following to run:
"""
        for api, env_vars in api_usage.items():
            missing = [var for var in env_vars if var in missing_vars]
            if missing:
                api_config = CredentialValidator.CREDENTIAL_MAP.get(api, {})
                display = api_config.get('display_name', api)
                error += f"\n  {display}:\n"
                for var in missing:
                    error += f"    - {var}\n"

        error += """
To set up credentials:

Option 1: Set as environment variables (local development)
"""
        for var in missing_vars:
            error += f"  export {var}=\"your-value\"\n"

        error += """
Option 2: Add to GitHub Actions secrets (for CI/CD)
  Go to: Settings → Secrets and variables → Actions
  Add each missing variable as a new repository secret

Option 3: Get full setup instructions
  Run: python3 -c "from .ravl.common.llm.credential_validator import CredentialValidator; print(CredentialValidator.get_setup_instructions('notion'))"
"""
        return error

    @staticmethod
    def summarize_credentials(code: str) -> str:
        """
        Analyze code and provide a summary of credential requirements

        Args:
            code: Python code to analyze

        Returns:
            Human-readable summary
        """
        required = CredentialValidator.detect_required_credentials(code)

        if not required:
            return "✓ No external credentials required"

        summary = "📋 Credentials required by generated code:\n"
        for api, env_vars in required.items():
            config = CredentialValidator.CREDENTIAL_MAP.get(api, {})
            display = config.get('display_name', api)
            summary += f"\n  {display}:\n"
            for var in env_vars:
                status = "✓" if os.environ.get(var) else "❌"
                summary += f"    {status} {var}\n"

        return summary
