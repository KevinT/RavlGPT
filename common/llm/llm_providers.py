#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
LLM Provider Abstraction Layer
Supports multiple LLM providers: Anthropic, OpenAI, Google, etc.
"""

import os
import sys
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from llm.llm_logger import log_llm_call

# Import config_loader with path-based import (works whether framework is installed or not)
_config_path = Path(__file__).parent.parent / 'config'
if str(_config_path) not in sys.path:
    sys.path.insert(0, str(_config_path))
from config_loader import get_max_tokens


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def complete(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        Generate a completion from the LLM

        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens in response (defaults to config value)

        Returns:
            The LLM's response text
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider"""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-5-20250929"):
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def complete(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        if max_tokens is None:
            max_tokens = get_max_tokens('default', 8192)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = response.content[0].text
            log_llm_call(self.get_provider_name(), prompt, response_text, max_tokens)
            return response_text
        except Exception as e:
            log_llm_call(self.get_provider_name(), prompt, "", max_tokens, error=str(e))
            raise

    def get_provider_name(self) -> str:
        return f"Anthropic ({self.model})"


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        try:
            import openai
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)

    def complete(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        if max_tokens is None:
            max_tokens = get_max_tokens('default', 8192)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = response.choices[0].message.content
            log_llm_call(self.get_provider_name(), prompt, response_text, max_tokens)
            return response_text
        except Exception as e:
            log_llm_call(self.get_provider_name(), prompt, "", max_tokens, error=str(e))
            raise

    def get_provider_name(self) -> str:
        return f"OpenAI ({self.model})"


class GoogleProvider(LLMProvider):
    """Google Gemini provider"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-exp"):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")

        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")

        self.model = model
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(model)

    def complete(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        if max_tokens is None:
            max_tokens = get_max_tokens('default', 8192)

        try:
            response = self.client.generate_content(
                prompt,
                generation_config={"max_output_tokens": max_tokens}
            )
            response_text = response.text
            log_llm_call(self.get_provider_name(), prompt, response_text, max_tokens)
            return response_text
        except Exception as e:
            log_llm_call(self.get_provider_name(), prompt, "", max_tokens, error=str(e))
            raise

    def get_provider_name(self) -> str:
        return f"Google ({self.model})"


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""

    def __init__(self, model: str = "llama3.1", base_url: str = "http://localhost:11434"):
        try:
            import requests
        except ImportError:
            raise ImportError("requests package not installed. Run: pip install requests")

        self.model = model
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/generate"

    def complete(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        if max_tokens is None:
            max_tokens = get_max_tokens('default', 8192)

        import requests

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens
            }
        }

        try:
            response = requests.post(self.endpoint, json=payload)
            response.raise_for_status()

            response_text = response.json()["response"]
            log_llm_call(self.get_provider_name(), prompt, response_text, max_tokens)
            return response_text
        except Exception as e:
            log_llm_call(self.get_provider_name(), prompt, "", max_tokens, error=str(e))
            raise

    def get_provider_name(self) -> str:
        return f"Ollama ({self.model})"


class LLMProviderFactory:
    """Factory for creating LLM providers"""

    @staticmethod
    def create_provider(
        provider_type: str = "anthropic",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMProvider:
        """
        Create an LLM provider

        Args:
            provider_type: One of: anthropic, openai, google, ollama
            api_key: Optional API key (will use env var if not provided)
            model: Optional model name (uses provider default if not provided)
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMProvider instance
        """
        provider_type = provider_type.lower()

        if provider_type == "anthropic":
            return AnthropicProvider(
                api_key=api_key,
                model=model or "claude-sonnet-4-5-20250929"
            )
        elif provider_type == "openai":
            return OpenAIProvider(
                api_key=api_key,
                model=model or "gpt-4o"
            )
        elif provider_type == "google":
            return GoogleProvider(
                api_key=api_key,
                model=model or "gemini-2.0-flash-exp"
            )
        elif provider_type == "ollama":
            return OllamaProvider(
                model=model or "llama3.1",
                base_url=kwargs.get("base_url", "http://localhost:11434")
            )
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    @staticmethod
    def from_config(config: Dict[str, Any]) -> LLMProvider:
        """
        Create provider from configuration dict

        Example config:
        {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "api_key": "optional-override"
        }
        """
        provider_type = config.get("provider", "anthropic")
        api_key = config.get("api_key")
        model = config.get("model")

        # Pass remaining config items as kwargs
        kwargs = {k: v for k, v in config.items() if k not in ["provider", "api_key", "model"]}

        return LLMProviderFactory.create_provider(
            provider_type=provider_type,
            api_key=api_key,
            model=model,
            **kwargs
        )


def test_provider(provider: LLMProvider):
    """Test a provider with a simple prompt"""
    print(f"Testing {provider.get_provider_name()}...")

    prompt = "Say 'Hello from the LLM!' and nothing else."
    response = provider.complete(prompt, max_tokens=100)

    print(f"Response: {response}")
    print("✓ Provider working!")


if __name__ == '__main__':
    import sys

    # Test the provider specified in command line or default to anthropic
    provider_type = sys.argv[1] if len(sys.argv) > 1 else "anthropic"

    try:
        provider = LLMProviderFactory.create_provider(provider_type)
        test_provider(provider)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)