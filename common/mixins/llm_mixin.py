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


class LLMMixin:
    """
    Mixin providing LLM utilities for RAVL loops

    Methods:
    - detect_llm_provider(): Auto-detect available LLM provider
    - extract_json(): Parse JSON from LLM responses
    """

    def detect_llm_provider(self):
        """
        Auto-detect LLM provider based on available API keys

        Checks for API keys in this order:
        1. ANTHROPIC_API_KEY
        2. OPENAI_API_KEY
        3. GOOGLE_API_KEY
        4. Falls back to local Ollama

        Returns:
            LLMProvider instance
        """
        from llm.llm_providers import LLMProviderFactory

        loop_name = getattr(self, 'loop_name', 'RAVL Loop')

        if os.environ.get("ANTHROPIC_API_KEY"):
            print(f"  ℹ️  {loop_name}: Auto-detected Anthropic API key", file=sys.stderr, flush=True)
            return LLMProviderFactory.create_provider("anthropic")
        elif os.environ.get("OPENAI_API_KEY"):
            print(f"  ℹ️  {loop_name}: Auto-detected OpenAI API key", file=sys.stderr, flush=True)
            return LLMProviderFactory.create_provider("openai")
        elif os.environ.get("GOOGLE_API_KEY"):
            print(f"  ℹ️  {loop_name}: Auto-detected Google API key", file=sys.stderr, flush=True)
            return LLMProviderFactory.create_provider("google")
        else:
            print(f"  ℹ️  {loop_name}: No API keys found, trying local Ollama", file=sys.stderr, flush=True)
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
            print(f"  ⚠️  JSON extraction failed: {e}", file=sys.stderr)
            print(f"  Response text: {response_text[:500]}", file=sys.stderr)
            # Return empty structure based on what's likely in the response
            return {} if '{' in response_text else []
