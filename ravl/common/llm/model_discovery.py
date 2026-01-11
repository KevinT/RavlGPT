"""
Model Discovery - Fetch available models from LLM provider APIs with metadata

Provides dynamic model discovery with:
- API-based fetching from Anthropic, OpenAI, Google
- TTL-based caching to minimize API calls
- Model metadata (strengths, weaknesses, costs) for dynamic selection
- Fallback mechanisms (API -> stale cache -> data file)
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
from dataclasses import dataclass, asdict


@dataclass
class ModelMetadata:
    """Metadata about an LLM model for dynamic selection"""
    id: str
    display_name: str
    tier: str  # 'fast', 'balanced', 'premium', 'legacy'
    description: str
    strengths: List[str]  # e.g., ["code generation", "analysis"]
    weaknesses: List[str]  # e.g., ["creative writing", "long context"]
    cost_per_million_input_tokens: Optional[float] = None
    cost_per_million_output_tokens: Optional[float] = None
    context_window: Optional[int] = None
    is_default: bool = False

    def to_display_string(self) -> str:
        """Format for display in config wizard"""
        parts = [self.display_name, f"({self.description})"]
        if self.is_default:
            parts.append("[DEFAULT]")
        return " ".join(parts)


class ModelDiscovery:
    """Discovers and caches available models from LLM providers"""

    # Cache file location
    CACHE_FILE = Path.home() / '.ravl' / 'config' / 'model_cache.json'
    DEFAULT_TTL_HOURS = 24

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize model discovery

        Args:
            config_path: Optional path to ravl.toml config file
        """
        self.config = self._load_config(config_path)
        self.cache_file = self.CACHE_FILE
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Load fallback models from data file
        self.fallback_models = self._load_fallback_models()

    def _load_fallback_models(self) -> Dict[str, List[ModelMetadata]]:
        """Load fallback models from config/model_fallbacks.json"""
        from ravl.common.cli.ravl_cli_base import RAVLCLIBase

        framework_root = RAVLCLIBase.find_framework_root()
        fallback_file = framework_root / 'config' / 'model_fallbacks.json'

        if not fallback_file.exists():
            print(f"Warning: Fallback models file not found: {fallback_file}")
            return {}

        try:
            with open(fallback_file, 'r') as f:
                data = json.load(f)

            # Convert JSON data to ModelMetadata objects
            result = {}
            for provider, models in data.items():
                result[provider] = [ModelMetadata(**m) for m in models]

            return result
        except Exception as e:
            print(f"Warning: Failed to load fallback models: {e}")
            return {}

    def _load_config(self, config_path: Optional[Path]) -> Dict:
        """Load configuration from framework_defaults.toml"""
        default_config = {
            'enabled': True,
            'cache_ttl_hours': self.DEFAULT_TTL_HOURS,
            'auto_refresh': True,
            'prompt_on_stale': False
        }

        try:
            # Try to load from framework config using existing loader
            from ravl.common.config.config_loader import load_framework_config
            framework_config = load_framework_config()
            llm_config = framework_config.get('llm', {})
            model_discovery_config = llm_config.get('model_discovery', {})

            # Merge with defaults
            return {**default_config, **model_discovery_config}
        except Exception as e:
            # Fall back to defaults if config loading fails
            return default_config

    def get_models(
        self,
        provider: str,
        api_key: Optional[str] = None
    ) -> List[ModelMetadata]:
        """Get models for provider (from cache, API, or fallback)

        Priority:
        1. Valid cache (within TTL) -> return cached
        2. API available + key provided -> fetch from API, update cache
        3. Stale cache exists -> return stale cache (warn)
        4. Fallback -> return models from data file

        Args:
            provider: 'anthropic', 'openai', or 'google'
            api_key: Optional API key for fetching from provider API

        Returns:
            List of ModelMetadata objects
        """
        # Check if model discovery is disabled
        if not self.config.get('enabled', True):
            return self.fallback_models.get(provider, [])

        # Load cache
        cache = self._load_cache()

        # Check if cache is valid
        if self._is_cache_valid(cache, provider):
            return self._models_from_cache(cache[provider]['models'])

        # Try to fetch from API if key provided and auto_refresh enabled
        if api_key and self.config.get('auto_refresh', True):
            try:
                models = self._fetch_from_api(provider, api_key)
                self._update_cache(cache, provider, models)
                return models
            except Exception as e:
                print(f"Warning: API fetch failed for {provider}: {e}")

        # Use stale cache if available
        if provider in cache and 'models' in cache[provider]:
            if not self.config.get('prompt_on_stale', False):
                print(f"Warning: Using stale cache for {provider} models")
                return self._models_from_cache(cache[provider]['models'])

        # Final fallback to data file
        print(f"Using fallback models for {provider}")
        return self.fallback_models.get(provider, [])

    def get_models_as_tuples(
        self,
        provider: str,
        api_key: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """Get models formatted as (id, display_string) tuples for wizard

        Args:
            provider: 'anthropic', 'openai', or 'google'
            api_key: Optional API key for fetching from provider API

        Returns:
            List of (model_id, display_string) tuples
        """
        models = self.get_models(provider, api_key)
        return [(m.id, m.to_display_string()) for m in models]

    def _fetch_from_api(self, provider: str, api_key: str) -> List[ModelMetadata]:
        """Fetch models from provider API

        Args:
            provider: 'anthropic', 'openai', or 'google'
            api_key: API key for the provider

        Returns:
            List of ModelMetadata objects
        """
        if provider == 'anthropic':
            return self._fetch_anthropic_models(api_key)
        elif provider == 'openai':
            return self._fetch_openai_models(api_key)
        elif provider == 'google':
            return self._fetch_google_models(api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _fetch_anthropic_models(self, api_key: str) -> List[ModelMetadata]:
        """Fetch Anthropic models from API

        Note: Anthropic doesn't have a models.list() endpoint yet.
        We test the API connection and return fallback models.
        When API becomes available, this will fetch real-time data.
        """
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)

            # Test API connection with a minimal request
            client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )

            # If successful, return fallback (in future, parse API response)
            return self.fallback_models.get('anthropic', [])

        except Exception as e:
            raise Exception(f"Failed to fetch Anthropic models: {e}")

    def _fetch_openai_models(self, api_key: str) -> List[ModelMetadata]:
        """Fetch OpenAI models from API"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            # Get available models
            models_response = client.models.list()
            available_model_ids = {m.id for m in models_response.data}

            # Filter fallback models to only those available via API
            fallback_models = self.fallback_models.get('openai', [])
            filtered_models = [
                m for m in fallback_models
                if m.id in available_model_ids
            ]

            # If we found models, return them; otherwise return all fallback
            return filtered_models if filtered_models else fallback_models

        except Exception as e:
            raise Exception(f"Failed to fetch OpenAI models: {e}")

    def _fetch_google_models(self, api_key: str) -> List[ModelMetadata]:
        """Fetch Google models from API"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)

            # Get available models
            models_response = genai.list_models()
            available_model_ids = set()

            for m in models_response:
                # Extract model ID from name (format: "models/gemini-1.5-pro")
                if hasattr(m, 'name') and m.name.startswith('models/'):
                    model_id = m.name.replace('models/', '')
                    available_model_ids.add(model_id)

            # Filter fallback models to only those available via API
            fallback_models = self.fallback_models.get('google', [])
            filtered_models = [
                m for m in fallback_models
                if m.id in available_model_ids
            ]

            # If we found models, return them; otherwise return all fallback
            return filtered_models if filtered_models else fallback_models

        except Exception as e:
            raise Exception(f"Failed to fetch Google models: {e}")

    def _load_cache(self) -> Dict:
        """Load cache from disk"""
        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load cache: {e}")
            return {}

    def _is_cache_valid(self, cache: Dict, provider: str) -> bool:
        """Check if cached models are within TTL"""
        if provider not in cache:
            return False

        if 'fetched_at' not in cache[provider]:
            return False

        try:
            fetched_at = datetime.fromisoformat(cache[provider]['fetched_at'])
            ttl_hours = cache[provider].get('ttl_hours', self.config.get('cache_ttl_hours', self.DEFAULT_TTL_HOURS))
            ttl = timedelta(hours=ttl_hours)

            return datetime.now() - fetched_at < ttl
        except Exception:
            return False

    def _update_cache(self, cache: Dict, provider: str, models: List[ModelMetadata]):
        """Update cache with new models"""
        cache[provider] = {
            'fetched_at': datetime.now().isoformat(),
            'ttl_hours': self.config.get('cache_ttl_hours', self.DEFAULT_TTL_HOURS),
            'models': [asdict(m) for m in models]
        }

        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    def _models_from_cache(self, cached_models: List[Dict]) -> List[ModelMetadata]:
        """Convert cached model dicts to ModelMetadata objects"""
        return [ModelMetadata(**m) for m in cached_models]
