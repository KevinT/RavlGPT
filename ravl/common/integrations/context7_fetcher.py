#!/usr/bin/env python3
"""
Context7 Documentation Fetcher

Utility for fetching API documentation from Context7.com with caching.
Supports single-API and multi-API configurations.
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None

# Import logging utilities (using lazy import to avoid circular dependencies)
_log_execution = None
_log_message = None


def _get_loggers():
    """Lazy import of logging utilities"""
    global _log_execution, _log_message
    if _log_execution is None:
        try:
            from utils.logging_utils import log_execution, log_message
            _log_execution = log_execution
            _log_message = log_message
        except ImportError:
            # Fallback if logging not available
            _log_execution = lambda msg, **kwargs: print(f"[INFO] {msg}")
            _log_message = lambda msg, **kwargs: print(f"[INFO] {msg}")
    return _log_execution, _log_message


class Context7Fetcher:
    """
    Fetches and caches API documentation from Context7.com

    Supports:
    - Single API or multiple APIs
    - Per-API caching with TTL
    - Configurable cache directory
    """

    DEFAULT_CACHE_TTL_HOURS = 168  # 1 week

    def __init__(self, cache_dir: Path):
        """
        Initialize Context7 fetcher

        Args:
            cache_dir: Directory to store cached documentation
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_execution, self.log_message = _get_loggers()

    def fetch_api_docs(
        self,
        api_name: str,
        context7_path: str,
        cache_ttl_hours: Optional[int] = None
    ) -> str:
        """
        Fetch documentation for a single API

        Args:
            api_name: Name of the API (for cache file naming)
            context7_path: Path or full URL on Context7.com
                          (e.g., /websites/developers_notion or https://context7.com/websites/developers_notion)
            cache_ttl_hours: Cache TTL in hours (defaults to 168 = 1 week)

        Returns:
            Documentation content as string
        """
        if cache_ttl_hours is None:
            cache_ttl_hours = self.DEFAULT_CACHE_TTL_HOURS

        cache_file = self.cache_dir / f'context7_docs_cache_{api_name}.txt'

        # Check cache first
        if cache_file.exists() and self._is_cache_fresh(cache_file, cache_ttl_hours):
            self.log_execution(f"Using cached Context7 docs for {api_name}", status='info')
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read()

        # Fetch from Context7
        self.log_execution(f"Fetching Context7 docs for {api_name}...", status='working')

        if requests is None:
            raise ImportError("requests library not available - cannot fetch Context7 docs")

        try:
            # Handle both full URLs and path-only strings
            parsed = urlparse(context7_path)
            if parsed.scheme:  # Full URL provided
                url = context7_path
            else:  # Path-only, prepend base URL
                url = f"https://context7.com{context7_path}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            docs = response.text

            # Cache for future use
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(docs)

            self.log_execution(
                f"Cached {len(docs)} chars from Context7 for {api_name}",
                status='success'
            )
            return docs

        except Exception as e:
            self.log_message(
                f"Context7 fetch failed for {api_name}: {e}, using empty docs",
                status='error'
            )
            return f"# {api_name} API\n\n(Context7 documentation fetch failed: {e})"

    def fetch_multiple_apis(
        self,
        apis_config: Dict[str, Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Fetch documentation for multiple APIs

        Args:
            apis_config: Dict mapping API name to config dict with:
                - context7_path: Required path on Context7.com
                - context7_cache_ttl_hours: Optional cache TTL override

        Returns:
            Dict mapping API name to documentation content

        Example:
            >>> fetcher = Context7Fetcher(Path('learnings'))
            >>> apis = {
            ...     'notion': {'context7_path': '/websites/developers_notion'},
            ...     'clickup': {'context7_path': '/websites/developer_clickup'}
            ... }
            >>> docs = fetcher.fetch_multiple_apis(apis)
            >>> print(docs['notion'])
        """
        result = {}

        for api_name, api_config in apis_config.items():
            context7_path = api_config.get('context7_path')
            if not context7_path:
                self.log_message(
                    f"API '{api_name}' missing context7_path, skipping",
                    status='warning'
                )
                continue

            cache_ttl = api_config.get('context7_cache_ttl_hours')
            docs = self.fetch_api_docs(api_name, context7_path, cache_ttl)
            result[api_name] = docs

        return result

    def invalidate_cache(self, api_name: Optional[str] = None):
        """
        Invalidate cached documentation

        Args:
            api_name: Optional API name to invalidate (None = invalidate all)
        """
        if api_name:
            cache_file = self.cache_dir / f'context7_docs_cache_{api_name}.txt'
            if cache_file.exists():
                cache_file.unlink()
                self.log_execution(f"Invalidated Context7 cache for {api_name}", status='info')
        else:
            # Invalidate all Context7 caches
            for cache_file in self.cache_dir.glob('context7_docs_cache_*.txt'):
                cache_file.unlink()
            self.log_execution("Invalidated all Context7 caches", status='info')

    def _is_cache_fresh(self, cache_file: Path, ttl_hours: int) -> bool:
        """Check if cache file is still fresh based on TTL"""
        try:
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            age = datetime.now() - mtime
            return age < timedelta(hours=ttl_hours)
        except Exception:
            return False


def fetch_context7_docs_for_loop(
    config: Dict[str, Any],
    cache_dir: Path
) -> Dict[str, str]:
    """
    Convenience function to fetch Context7 docs based on loop config

    Handles both single-API and multi-API configurations.

    Args:
        config: Loop configuration dict
        cache_dir: Directory for caching documentation

    Returns:
        Dict mapping API name to documentation content

    Examples:
        Single-API (legacy):
        >>> config = {'context7_docs_path': '/websites/developers_notion'}
        >>> docs = fetch_context7_docs_for_loop(config, Path('learnings'))
        >>> # Returns: {'default': '...'}

        Multi-API:
        >>> config = {
        ...     'apis': {
        ...         'notion': {'context7_path': '/websites/developers_notion'},
        ...         'clickup': {'context7_path': '/websites/developer_clickup'}
        ...     }
        ... }
        >>> docs = fetch_context7_docs_for_loop(config, Path('learnings'))
        >>> # Returns: {'notion': '...', 'clickup': '...'}
    """
    fetcher = Context7Fetcher(cache_dir)

    # Check for multi-API configuration
    if 'apis' in config:
        return fetcher.fetch_multiple_apis(config['apis'])

    # Legacy single-API configuration
    context7_path = config.get('context7_docs_path')
    if context7_path:
        cache_ttl = config.get('context7_cache_ttl_hours')
        docs = fetcher.fetch_api_docs('default', context7_path, cache_ttl)
        return {'default': docs}

    # No Context7 configuration
    return {}
