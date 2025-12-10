#!/usr/bin/env python3
"""
Centralized Configuration Service

Provides unified config resolution with hierarchical inheritance:
Priority: CLI → Loop → Parent → Project → Framework → Environment → Default

This eliminates duplication of config loading logic across the codebase.
"""

import os
try:
    import tomllib
except ImportError:
    import tomli as tomllib
try:
    import tomli_w
except ImportError:
    tomli_w = None
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache


class ConfigService:
    """
    Centralized configuration resolution for RAVL framework

    Handles:
    - Hierarchical config resolution (CLI → Loop → Parent → Project → Framework → Env)
    - Config file discovery and loading
    - Value extraction with defaults
    - Caching for performance
    """

    def __init__(self, loop_dir: Path, project_root: Path):
        """
        Initialize config service

        Args:
            loop_dir: Path to current loop directory
            project_root: Path to project root
        """
        self.loop_dir = Path(loop_dir)
        self.project_root = Path(project_root)
        self._config_cache: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None, scope: str = 'all') -> Any:
        """
        Get config value with automatic resolution

        Args:
            key: Config key (supports dot notation, e.g., 'llm_provider.model')
            default: Default value if not found
            scope: 'loop' | 'parent' | 'project' | 'framework' | 'all'

        Returns:
            Resolved config value
        """
        cache_key = f"{scope}:{key}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        # Load configs based on scope
        configs = self._get_config_hierarchy(scope)

        # Resolve value from hierarchy
        for config in configs:
            value = self._extract_nested_key(config, key)
            if value is not None:
                self._config_cache[cache_key] = value
                return value

        return default

    def resolve_learning_path(
        self,
        cli_override: Optional[Path] = None
    ) -> Path:
        """
        Resolve learning path with hierarchy

        Priority:
        1. CLI override (--learning-path)
        2. Loop config/ravl.toml (learning_path)
        3. Default (loop_dir/learnings)

        Child loops inherit parent's learning_path automatically.

        Args:
            cli_override: CLI-specified path

        Returns:
            Resolved learning path
        """
        # Priority 1: CLI override
        if cli_override:
            return Path(cli_override)

        # Priority 2: Loop config
        loop_learning_path = self.get('learning_path', scope='loop')
        if loop_learning_path:
            return self._resolve_path(loop_learning_path, self.loop_dir)

        # Check parent configs for inheritance
        for parent_dir in self._find_all_parent_loops():
            parent_config = self._load_config(parent_dir / 'config' / 'ravl.toml')
            if parent_config and 'learning_path' in parent_config:
                return self._resolve_path(parent_config['learning_path'], parent_dir)

        # Priority 3: Default
        return self.loop_dir / 'learnings'

    def resolve_venv_path(
        self,
        cli_override: Optional[Path] = None,
        env_var: str = 'RAVL_DEFAULT_VENV_DIRECTORY'
    ) -> Path:
        """
        Resolve virtual environment path

        Priority:
        1. CLI override
        2. Loop config
        3. Project config
        4. Environment variable
        5. Default (.ravl/venv)
        """
        # Priority 1: CLI override
        if cli_override:
            return Path(cli_override)

        # Priority 2: Loop config
        loop_venv_path = self.get('venv_path', scope='loop')
        if loop_venv_path:
            return self._resolve_path(loop_venv_path, self.loop_dir)

        # Priority 3: Project config
        project_venv_path = self.get('venv_path', scope='project')
        if project_venv_path:
            return self._resolve_path(project_venv_path, self.project_root)

        # Priority 4: Environment variable
        env_value = os.environ.get(env_var)
        if env_value:
            return Path(env_value)

        # Priority 5: Default
        return self.project_root / '.ravl' / 'venv'

    def resolve_llm_config(self) -> Dict[str, Any]:
        """
        Resolve LLM provider configuration

        Priority:
        1. Loop config (llm_provider section)
        2. Parent config
        3. Project config
        4. Framework config
        5. Default (empty dict)
        """
        return self.get('llm_provider', default={}, scope='all')

    def resolve_allowed_dependencies(self) -> Dict[str, Dict[str, str]]:
        """
        Resolve dependency whitelist with full hierarchy

        Priority:
        1. Loop config (allowed_dependencies)
        2. Parent config
        3. Project config
        4. Framework config
        5. None (if not found)
        """
        return self.get('allowed_dependencies', default=None, scope='all')

    def get_learning_config(self, key: str, default: Any = None) -> Any:
        """
        Get learning configuration value with hierarchy resolution

        Args:
            key: Config key within learning section (e.g., 'disable_parent_learning')
            default: Default value if not found

        Returns:
            Config value from learning.{key} with hierarchy resolution

        Priority:
        1. Loop config (learning.{key})
        2. Parent config
        3. Project config
        4. Framework config
        5. Default value
        """
        learning_config = self.get('learning', {}, scope='all')
        if isinstance(learning_config, dict):
            return learning_config.get(key, default)
        return default

    def find_parent_loop(self) -> Optional[Path]:
        """
        Find parent loop directory

        Returns:
            Path to parent loop or None if top-level
        """
        parents = self._find_all_parent_loops()
        return parents[0] if parents else None

    # Private helper methods

    def _get_config_hierarchy(self, scope: str) -> List[Dict[str, Any]]:
        """Get list of configs to search based on scope"""
        configs = []

        if scope in ('loop', 'all'):
            loop_config = self._load_config(self.loop_dir / 'config' / 'ravl.toml')
            if loop_config:
                configs.append(loop_config)

        if scope in ('parent', 'all'):
            for parent_dir in self._find_all_parent_loops():
                parent_config = self._load_config(parent_dir / 'config' / 'ravl.toml')
                if parent_config:
                    configs.append(parent_config)

        if scope in ('project', 'all'):
            project_config = self._load_config(
                self.project_root / 'ravl_loops' / 'config' / 'ravl.toml'
            )
            if project_config:
                configs.append(project_config)

        if scope in ('framework', 'all'):
            framework_config = self._load_config(
                self.project_root / '.ravl' / 'config' / 'ravl.toml'
            )
            if framework_config:
                configs.append(framework_config)

        return configs

    @lru_cache(maxsize=32)
    def _load_config(self, config_path: Path) -> Optional[Dict[str, Any]]:
        """Load a TOML config file with caching"""
        if not config_path.exists():
            return None

        try:
            with open(config_path, 'rb') as f:
                return tomllib.load(f) or {}
        except Exception:
            return None

    def _find_all_parent_loops(self) -> List[Path]:
        """
        Find all parent loops in hierarchy

        Returns:
            List of parent loop paths, nearest first
        """
        parents = []

        # Count occurrences of 'child_loops' in path
        child_loops_indices = [
            i for i, part in enumerate(self.loop_dir.parts)
            if part == 'child_loops'
        ]

        # For each nesting level, extract parent path
        for idx in reversed(child_loops_indices[:-1] if len(child_loops_indices) > 1 else []):
            parent_path = Path(*self.loop_dir.parts[:idx])
            if parent_path.exists():
                parents.append(parent_path)

        return parents

    def _extract_nested_key(self, config: Dict[str, Any], key: str) -> Any:
        """
        Extract nested key using dot notation

        Example: 'llm_provider.model' extracts config['llm_provider']['model']
        """
        keys = key.split('.')
        value = config

        for k in keys:
            if not isinstance(value, dict) or k not in value:
                return None
            value = value[k]

        return value

    def _resolve_path(self, path_value: Any, base_dir: Path) -> Path:
        """
        Resolve a path value (handle relative vs absolute)

        Args:
            path_value: Path string or Path object
            base_dir: Base directory for relative paths

        Returns:
            Resolved absolute path
        """
        path = Path(path_value)

        if path.is_absolute():
            return path

        # Relative path - resolve against base_dir
        return base_dir / path

    def get_llm_provider(self) -> Optional[str]:
        """
        Get configured LLM provider from config hierarchy

        Priority:
        1. Loop config (llm.default_provider)
        2. Parent config
        3. Project config
        4. Framework config (.ravl/config/llm.toml)
        5. None (not configured)

        Returns:
            Provider name ("anthropic", "google", "openai", "ollama") or None
        """
        # Check loop/parent/project configs first
        llm_config = self.get('llm', {}, scope='all')
        if isinstance(llm_config, dict) and 'default_provider' in llm_config:
            provider = llm_config['default_provider']
            return str(provider).lower() if provider else None

        return None

    def get_llm_model(self) -> Optional[str]:
        """
        Get configured default LLM model from config hierarchy

        Checks llm_provider dict in hierarchy, then framework config.
        Does NOT check loop/parent/project configs (those use llm_provider dict).

        Priority:
        1. Loop config (llm_provider.model if dict)
        2. Parent config (llm_provider.model if dict)
        3. Project config (llm_provider.model if dict)
        4. Framework config (llm.default_model)
        5. None (not configured - provider uses hardcoded default)

        Returns:
            Model name string or None if not configured at framework level
        """
        # Check if llm_provider in hierarchy has a model key
        llm_config = self.get('llm_provider', default={}, scope='all')
        if isinstance(llm_config, dict) and 'model' in llm_config:
            model = llm_config['model']
            return str(model) if model else None

        # Check framework config for default_model
        return get_llm_model_from_framework_config(self.project_root)

    def set_framework_llm_provider(self, provider: str) -> Tuple[bool, Optional[str]]:
        """
        Save LLM provider choice to framework config

        Args:
            provider: Provider name ("anthropic", "google", "openai", "ollama")

        Returns:
            (success, error_message)
        """
        if tomli_w is None:
            return (False, "tomli-w package not installed. Install with: uv pip install tomli-w")

        framework_config_path = self.project_root / '.ravl' / 'config' / 'llm.toml'

        # Load existing framework config
        existing_config = self._load_config(framework_config_path) or {}

        # Update LLM provider
        if 'llm' not in existing_config:
            existing_config['llm'] = {}
        existing_config['llm']['default_provider'] = provider.lower()

        # Write back to file
        try:
            framework_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(framework_config_path, 'wb') as f:
                tomli_w.dump(existing_config, f)

            # Clear cache for this config
            self._load_config.cache_clear()
            self._config_cache.clear()

            return (True, None)
        except Exception as e:
            return (False, f"Failed to save config: {str(e)}")


# Standalone helper functions for easy importing

def get_llm_provider_from_framework_config(project_root: Optional[Path] = None) -> Optional[str]:
    """
    Get LLM provider from framework config only (not hierarchy)

    Args:
        project_root: Project root path (auto-detected if not provided)

    Returns:
        Provider name or None
    """
    if project_root is None:
        from ravl.common.cli.ravl_cli_base import RAVLCLIBase
        project_root = RAVLCLIBase.find_project_root(required=False)
        if project_root is None:
            return None

    framework_config_path = project_root / '.ravl' / 'config' / 'llm.toml'

    if not framework_config_path.exists():
        return None

    try:
        with open(framework_config_path, 'rb') as f:
            config = tomllib.load(f)

        if 'llm' in config and 'default_provider' in config['llm']:
            provider = config['llm']['default_provider']
            return str(provider).lower() if provider else None

    except Exception:
        pass

    return None


def get_llm_model_from_framework_config(project_root: Optional[Path] = None) -> Optional[str]:
    """
    Get default LLM model from framework config only (not hierarchy)

    Reads llm.default_model from .ravl/config/llm.toml

    Args:
        project_root: Project root path (auto-detected if not provided)

    Returns:
        Model name string or None if not configured
    """
    if project_root is None:
        from ravl.common.cli.ravl_cli_base import RAVLCLIBase
        project_root = RAVLCLIBase.find_project_root(required=False)
        if project_root is None:
            return None

    framework_config_path = project_root / '.ravl' / 'config' / 'llm.toml'

    if not framework_config_path.exists():
        return None

    try:
        with open(framework_config_path, 'rb') as f:
            config = tomllib.load(f)

        if 'llm' in config and 'default_model' in config['llm']:
            model = config['llm']['default_model']
            return str(model) if model else None

    except Exception:
        pass

    return None


def save_framework_llm_provider(provider: str, project_root: Optional[Path] = None) -> Tuple[bool, Optional[str]]:
    """
    Save LLM provider to framework config (standalone function)

    Args:
        provider: Provider name
        project_root: Project root (auto-detected if not provided)

    Returns:
        (success, error_message)
    """
    if tomli_w is None:
        return (False, "tomli-w not installed")

    if project_root is None:
        from ravl.common.cli.ravl_cli_base import RAVLCLIBase
        project_root = RAVLCLIBase.find_project_root(required=False)
        if project_root is None:
            return (False, "Could not find project root")

    framework_config_path = project_root / '.ravl' / 'config' / 'llm.toml'

    # Load existing config
    config = {}
    if framework_config_path.exists():
        try:
            with open(framework_config_path, 'rb') as f:
                config = tomllib.load(f)
        except Exception:
            pass

    # Update provider
    if 'llm' not in config:
        config['llm'] = {}
    config['llm']['default_provider'] = provider.lower()

    # Save
    try:
        framework_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(framework_config_path, 'wb') as f:
            tomli_w.dump(config, f)
        return (True, None)
    except Exception as e:
        return (False, str(e))
