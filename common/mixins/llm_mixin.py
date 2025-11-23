#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
LLM Mixin for RAVL Loops

Provides LLM provider detection and JSON extraction utilities.
Used by agents that need to interact with LLM APIs.
"""

import os
import sys
import json
from typing import Any
from pathlib import Path

# Add utils to path for logging
_utils_dir = Path(__file__).parent.parent / 'utils'
if str(_utils_dir) not in sys.path:
    sys.path.insert(0, str(_utils_dir))
from logging_utils import log_execution


class LLMMixin:
    """
    Mixin providing LLM utilities for RAVL loops

    Methods:
    - detect_llm_provider(): Auto-detect available LLM provider
    - extract_json(): Parse JSON from LLM responses
    """

    def detect_llm_provider(self):
        """
        Resolve LLM provider using hierarchical configuration

        Checks in priority order:
        1. Loop config (llm_provider in ravl.toml)
        2. Parent configs (parent's config/ravl.toml)
        3. Project config (ravl_loops/config/ravl.toml)
        4. .env file (RAVL_DEFAULT_LLM_PROVIDER)
        5. Auto-detect from API keys (ANTHROPIC > OPENAI > GOOGLE > OLLAMA)

        Falls back to auto-detection if loop context is not available.

        Returns:
            LLMProvider instance
        """
        from llm.llm_providers import LLMProviderFactory

        loop_name = getattr(self, 'loop_name', 'RAVL Loop')

        # Get loop directory if available
        loop_dir = getattr(self, 'loop_dir', None)
        loop_config = getattr(self, 'config', None)
        project_root = getattr(self, 'project_root', None)

        if loop_dir:
            # Use hierarchical resolution
            from ravl_runner import RAVLRunner
            llm_config = RAVLRunner.resolve_llm_config(
                loop_dir=loop_dir,
                loop_config=loop_config,
                project_root=project_root
            )
            provider_name = llm_config.get('provider', 'anthropic')
            log_execution(f"{loop_name}: Using LLM provider from config: {provider_name}", status='info')

            return LLMProviderFactory.create_provider(
                provider_name,
                model=llm_config.get('model'),
                temperature=llm_config.get('temperature'),
                max_tokens=llm_config.get('max_tokens'),
                top_p=llm_config.get('top_p')
            )
        else:
            # Fallback: auto-detect from API keys
            if os.environ.get("ANTHROPIC_API_KEY"):
                log_execution(f"{loop_name}: Auto-detected Anthropic API key", status='info')
                return LLMProviderFactory.create_provider("anthropic")
            elif os.environ.get("OPENAI_API_KEY"):
                log_execution(f"{loop_name}: Auto-detected OpenAI API key", status='info')
                return LLMProviderFactory.create_provider("openai")
            elif os.environ.get("GOOGLE_API_KEY"):
                log_execution(f"{loop_name}: Auto-detected Google API key", status='info')
                return LLMProviderFactory.create_provider("google")
            else:
                log_execution(f"{loop_name}: No API keys found, trying local Ollama", status='info')
                return LLMProviderFactory.create_provider("ollama")

    def extract_json(self, response_text: str) -> Any:
        """
        Extract JSON from LLM response

        Handles responses with or without code blocks.
        Looks for ```json or ``` markers and extracts content.

        Args:
            response_text: Raw LLM response text

        Returns:
            Parsed JSON (dict or list)
            Returns empty dict/list if parsing fails
        """
        try:
            # Try to find JSON in code blocks
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()

            return json.loads(response_text)

        except Exception as e:
            log_execution(f"JSON extraction failed: {e}", status='error')
            log_execution(f"Response text: {response_text[:500]}", status='error')
            # Return empty structure based on what's likely in the response
            return {} if '{' in response_text else []
