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
import logging
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from llm.llm_logger import log_llm_call

logger = logging.getLogger(__name__)

# Import config_loader with path-based import (works whether framework is installed or not)
_config_path = Path(__file__).parent.parent / 'config'
if str(_config_path) not in sys.path:
    sys.path.insert(0, str(_config_path))
from config_loader import get_max_tokens, get_prompt_normalization_config

# Module-level normalizer singleton (lazy-loaded)
_normalizer = None

def get_normalizer():
    """Get or create the prompt normalizer singleton."""
    global _normalizer
    if _normalizer is None:
        try:
            from llm.prompt_normalizer import PromptNormalizer
            config = get_prompt_normalization_config()
            _normalizer = PromptNormalizer(
                min_block_size=config['min_block_size'],
                enable_logging=config['enable_logging']
            )
        except Exception as e:
            logger.warning(f"Failed to initialize prompt normalizer: {e}")
            _normalizer = None
    return _normalizer


def _get_install_instructions(package_name: str) -> str:
    """
    Generate context-aware install instructions for missing packages.

    Args:
        package_name: Name of the package that's missing

    Returns:
        Helpful error message with working install instructions
    """
    # Try to find the framework venv
    venv_path = os.environ.get('RAVL_VENV_PATH')
    if not venv_path:
        # Try to detect framework venv relative to this file
        framework_root = Path(__file__).parent.parent.parent.parent
        venv_path = framework_root / 'venv'

    if Path(venv_path).exists():
        return (
            f"{package_name} package not installed.\n\n"
            f"Install it with:\n"
            f"  {venv_path}/bin/pip install {package_name}\n\n"
            f"Or activate the framework venv first:\n"
            f"  source {venv_path}/bin/activate\n"
            f"  pip install {package_name}"
        )
    else:
        return (
            f"{package_name} package not installed.\n\n"
            f"The framework venv hasn't been created yet.\n"
            f"This should have been done automatically on first run.\n\n"
            f"Try running your loop again - the venv will be created automatically.\n"
            f"If the problem persists, you may need to manually create the venv."
        )


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

    @staticmethod
    def _format_api_error(exception: Exception, provider_name: str) -> str:
        """Format API error with helpful message for common issues"""
        error_str = str(exception)

        # Detect credit/quota errors
        if provider_name == "anthropic":
            if "credit_balance_exceeded" in error_str or "429" in error_str:
                return "❌ Anthropic API credit balance exhausted. Add credits at https://console.anthropic.com/settings/billing"
        elif provider_name == "openai":
            if "insufficient_quota" in error_str or "rate_limit_exceeded" in error_str:
                return "❌ OpenAI API quota exceeded. Check usage at https://platform.openai.com/usage"
        elif provider_name == "google":
            if "quota" in error_str.lower():
                return "❌ Google API quota exceeded. Check quota at https://console.cloud.google.com/apis/dashboard"

        return f"❌ {provider_name} API error: {error_str}"


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None
    ):
        try:
            import anthropic
        except ImportError:
            raise ImportError(_get_install_instructions('anthropic'))

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.model = model
        self.temperature = temperature
        self.default_max_tokens = max_tokens
        self.top_p = top_p
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def complete(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        # Use method param, then instance default, then framework default
        if max_tokens is None:
            max_tokens = self.default_max_tokens or get_max_tokens('default')

        # Apply prompt normalization if enabled in config
        normalized_prompt = prompt
        original_length = len(prompt)
        config = get_prompt_normalization_config()
        if config['enabled']:
            try:
                normalizer = get_normalizer()
                if normalizer:
                    normalized_prompt = normalizer.normalize(prompt)
            except Exception as e:
                # Graceful degradation: use original prompt on error
                logger.warning(f"Prompt normalization failed: {e}")
                normalized_prompt = prompt

        # Build API params
        api_params = {
            'model': self.model,
            'max_tokens': max_tokens,
            'messages': [{"role": "user", "content": normalized_prompt}]
        }

        # Add optional parameters if configured
        if self.temperature is not None:
            api_params['temperature'] = self.temperature
        if self.top_p is not None:
            api_params['top_p'] = self.top_p

        try:
            response = self.client.messages.create(**api_params)
            response_text = response.content[0].text
            log_llm_call(self.get_provider_name(), prompt, response_text, max_tokens)
            return response_text
        except Exception as e:
            formatted_error = self._format_api_error(e, self.get_provider_name())
            log_llm_call(self.get_provider_name(), prompt, "", max_tokens, error=formatted_error)
            print(formatted_error)  # Show to user immediately
            raise

    def get_provider_name(self) -> str:
        return f"Anthropic ({self.model})"


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None
    ):
        try:
            import openai
        except ImportError:
            raise ImportError(_get_install_instructions('openai'))

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        self.model = model
        self.temperature = temperature
        self.default_max_tokens = max_tokens
        self.top_p = top_p
        self.client = openai.OpenAI(api_key=self.api_key)

    def _is_reasoning_model(self) -> bool:
        """
        Check if model is a reasoning model (GPT-5, o1, o3 series).
        These models use max_completion_tokens instead of max_tokens.
        """
        model_lower = self.model.lower()
        reasoning_prefixes = ['gpt-5', 'o1-', 'o3-']
        return any(model_lower.startswith(prefix) for prefix in reasoning_prefixes)

    def complete(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        # Use method param, then instance default, then framework default
        if max_tokens is None:
            max_tokens = self.default_max_tokens or get_max_tokens('default')

        # Apply prompt normalization if enabled in config
        normalized_prompt = prompt
        original_length = len(prompt)
        config = get_prompt_normalization_config()
        if config['enabled']:
            try:
                normalizer = get_normalizer()
                if normalizer:
                    normalized_prompt = normalizer.normalize(prompt)
            except Exception as e:
                # Graceful degradation: use original prompt on error
                logger.warning(f"Prompt normalization failed: {e}")
                normalized_prompt = prompt

        # Reasoning models (GPT-5, o1, o3) require max_completion_tokens
        # Regular models (GPT-4, GPT-3.5) use max_tokens
        is_reasoning = self._is_reasoning_model()
        token_param = 'max_completion_tokens' if is_reasoning else 'max_tokens'

        # Build API params
        api_params = {
            'model': self.model,
            token_param: max_tokens,
            'messages': [{"role": "user", "content": normalized_prompt}]
        }

        # Add optional parameters if configured
        if self.temperature is not None:
            api_params['temperature'] = self.temperature
        if self.top_p is not None:
            api_params['top_p'] = self.top_p

        try:
            response = self.client.chat.completions.create(**api_params)
            response_text = response.choices[0].message.content
            log_llm_call(self.get_provider_name(), prompt, response_text, max_tokens)
            return response_text
        except Exception as e:
            formatted_error = self._format_api_error(e, self.get_provider_name())
            log_llm_call(self.get_provider_name(), prompt, "", max_tokens, error=formatted_error)
            print(formatted_error)  # Show to user immediately
            raise

    def get_provider_name(self) -> str:
        return f"OpenAI ({self.model})"


class GoogleProvider(LLMProvider):
    """Google Gemini provider"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash-exp",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None
    ):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(_get_install_instructions('google-generativeai'))

        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")

        self.model = model
        self.temperature = temperature
        self.default_max_tokens = max_tokens
        self.top_p = top_p
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(model)

    def complete(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        # Use method param, then instance default, then framework default
        if max_tokens is None:
            max_tokens = self.default_max_tokens or get_max_tokens('default')

        # Apply prompt normalization if enabled in config
        normalized_prompt = prompt
        original_length = len(prompt)
        config = get_prompt_normalization_config()
        if config['enabled']:
            try:
                normalizer = get_normalizer()
                if normalizer:
                    normalized_prompt = normalizer.normalize(prompt)
            except Exception as e:
                # Graceful degradation: use original prompt on error
                logger.warning(f"Prompt normalization failed: {e}")
                normalized_prompt = prompt

        # Build generation config
        gen_config = {"max_output_tokens": max_tokens}
        if self.temperature is not None:
            gen_config['temperature'] = self.temperature
        if self.top_p is not None:
            gen_config['top_p'] = self.top_p

        try:
            response = self.client.generate_content(
                normalized_prompt,
                generation_config=gen_config
            )
            response_text = response.text
            log_llm_call(self.get_provider_name(), prompt, response_text, max_tokens)
            return response_text
        except Exception as e:
            formatted_error = self._format_api_error(e, self.get_provider_name())
            log_llm_call(self.get_provider_name(), prompt, "", max_tokens, error=formatted_error)
            print(formatted_error)  # Show to user immediately
            raise

    def get_provider_name(self) -> str:
        return f"Google ({self.model})"


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""

    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None
    ):
        try:
            import requests
        except ImportError:
            raise ImportError(_get_install_instructions('requests'))

        self.model = model
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/generate"
        self.temperature = temperature
        self.default_max_tokens = max_tokens
        self.top_p = top_p

    def complete(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        # Use method param, then instance default, then framework default
        if max_tokens is None:
            max_tokens = self.default_max_tokens or get_max_tokens('default')

        # Apply prompt normalization if enabled in config
        normalized_prompt = prompt
        original_length = len(prompt)
        config = get_prompt_normalization_config()
        if config['enabled']:
            try:
                normalizer = get_normalizer()
                if normalizer:
                    normalized_prompt = normalizer.normalize(prompt)
            except Exception as e:
                # Graceful degradation: use original prompt on error
                logger.warning(f"Prompt normalization failed: {e}")
                normalized_prompt = prompt

        import requests

        # Build options dict
        options = {"num_predict": max_tokens}
        if self.temperature is not None:
            options['temperature'] = self.temperature
        if self.top_p is not None:
            options['top_p'] = self.top_p

        payload = {
            "model": self.model,
            "prompt": normalized_prompt,
            "stream": False,
            "options": options
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
    def validate_provider_credentials(provider_type: str) -> tuple[bool, Optional[str]]:
        """
        Validate that required credentials exist for the provider.

        Args:
            provider_type: Provider name (anthropic, openai, google, ollama)

        Returns:
            Tuple of (is_valid, error_message)
        """
        provider_type = provider_type.lower()

        if provider_type == "anthropic":
            if not os.environ.get('ANTHROPIC_API_KEY'):
                return (False, "ANTHROPIC_API_KEY environment variable not found")
            return (True, None)

        elif provider_type == "openai":
            if not os.environ.get('OPENAI_API_KEY'):
                return (False, "OPENAI_API_KEY environment variable not found")
            return (True, None)

        elif provider_type == "google":
            if not os.environ.get('GOOGLE_API_KEY'):
                return (False, "GOOGLE_API_KEY environment variable not found")
            return (True, None)

        elif provider_type == "ollama":
            # Ollama doesn't require API key, just endpoint
            return (True, None)

        else:
            return (False, f"Unknown provider: {provider_type}")

    @staticmethod
    def create_provider(
        provider_type: str = "anthropic",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs
    ) -> LLMProvider:
        """
        Create an LLM provider

        Args:
            provider_type: One of: anthropic, openai, google, ollama
            api_key: Optional API key (will use env var if not provided)
            model: Optional model name (uses provider default if not provided)
            temperature: Optional temperature (0.0-1.0) for response randomness
            max_tokens: Optional max tokens for response
            top_p: Optional top_p (0.0-1.0) for nucleus sampling
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMProvider instance
        """
        provider_type = provider_type.lower()

        # Validate credentials before creating provider (skip if api_key is explicitly provided)
        if not api_key:
            is_valid, error_msg = LLMProviderFactory.validate_provider_credentials(provider_type)
            if not is_valid:
                raise ValueError(
                    f"Cannot use provider '{provider_type}': {error_msg}\n\n"
                    f"To fix:\n"
                    f"  1. Set the required API key environment variable\n"
                    f"  2. Or choose a different provider with: ravl --config\n"
                    f"  3. Or check available providers with: ravl --config"
                )

        if provider_type == "anthropic":
            return AnthropicProvider(
                api_key=api_key,
                model=model or "claude-sonnet-4-5-20250929",
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p
            )
        elif provider_type == "openai":
            return OpenAIProvider(
                api_key=api_key,
                model=model or "gpt-4o",
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p
            )
        elif provider_type == "google":
            return GoogleProvider(
                api_key=api_key,
                model=model or "gemini-2.0-flash-exp",
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p
            )
        elif provider_type == "ollama":
            return OllamaProvider(
                model=model or "llama3.1",
                base_url=kwargs.get("base_url", "http://localhost:11434"),
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p
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
        from logging_utils import log_message
        log_message(f"Error: {e}", status='error', indent=0)
        sys.exit(1)