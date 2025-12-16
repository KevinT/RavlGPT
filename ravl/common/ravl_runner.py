#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
RAVL Runner - Base utilities for all RAVL loop runners

Provides shared functionality for running RAVL loops (both parent and child):
- File I/O (load/save findings)
- Logging utilities (TeeLogger for file + stdout)
- Path resolution (find project root)
- RAVL phase execution (reflect → act → verify → learn)
- Error handling and reporting
"""

import argparse
import json
import sys
import time
import os
import tomllib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, TextIO, Callable, List

from utils.constants import DEFAULT_EXECUTION_TIMEOUT, MODEL_PATTERN
from utils.logging_utils import log_message
from cli.ravl_cli_base import RAVLCLIBase


class TeeLogger:
    """Write to both a file and the original stream"""

    def __init__(self, file_path: Path, original_stream: TextIO):
        self.file = open(file_path, 'w', buffering=1)  # Line buffered
        self.original_stream = original_stream

    def write(self, message: str):
        self.file.write(message)
        self.file.flush()
        self.original_stream.write(message)
        self.original_stream.flush()

    def flush(self):
        self.file.flush()
        self.original_stream.flush()

    def isatty(self):
        """Delegate isatty() to original stream for color detection"""
        return hasattr(self.original_stream, 'isatty') and self.original_stream.isatty()

    def close(self):
        self.file.close()


class RAVLRunner:
    """
    Base class for running RAVL loops

    Provides common utilities and execution flow for all RAVL loop runners.
    """

    @staticmethod
    def load_env_file(project_root: Path) -> Dict[str, str]:
        """
        Load environment variables from project root .env file

        Args:
            project_root: Path to project root

        Returns:
            Dictionary of environment variables from .env file
        """
        env_vars = {}
        env_file = project_root / '.env'

        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if not line or line.startswith('#'):
                            continue
                        # Parse KEY=VALUE
                        if '=' in line:
                            key, value = line.split('=', 1)
                            value = value.strip()
                            # Strip shell-style quotes (single or double)
                            if (value.startswith('"') and value.endswith('"')) or \
                               (value.startswith("'") and value.endswith("'")):
                                value = value[1:-1]
                            env_vars[key.strip()] = value
            except Exception as e:
                log_message(f"Warning: Could not load .env file: {e}", status='error')

        return env_vars

    @staticmethod
    def _detect_child_loop_path(loop_dir: Path) -> Optional[str]:
        """
        Detect if loop_dir is nested in a parent-child-...-child loop structure and return the full hierarchy path.

        For arbitrary nesting depth, captures the complete hierarchy of loop names.

        Examples:
        - Input: /project/ravl_loops/org_context/learnings
          Returns: "org_context"
        - Input: /project/ravl_loops/org_context/ravl_loops/knowledge_commons/learnings
          Returns: "org_context/knowledge_commons"
        - Input: /project/ravl_loops/org_context/ravl_loops/knowledge_commons/ravl_loops/analysis/learnings
          Returns: "org_context/knowledge_commons/analysis"

        Returns:
            Hierarchy path like "parent/child/grandchild" or None if not a child loop
        """
        current = loop_dir.resolve()
        parts = current.parts

        # Find the FIRST "ravl_loops" in the path
        first_ravl_loops_idx = None
        for i, part in enumerate(parts):
            if part == 'ravl_loops':
                first_ravl_loops_idx = i
                break

        if first_ravl_loops_idx is None or first_ravl_loops_idx >= len(parts) - 1:
            # No ravl_loops found, or nothing after it
            return None

        # Capture everything after the first "ravl_loops" as the hierarchy
        # Filter out "ravl_loops" and "child_loops" directories (they separate parent/child boundaries)
        hierarchy = []
        for part in parts[first_ravl_loops_idx + 1:]:
            if part not in ('ravl_loops', 'child_loops'):
                hierarchy.append(part)

        if hierarchy:
            return '/'.join(hierarchy)

        return None

    @staticmethod
    def resolve_loop_directory(
        cli_loop_dir: Optional[Path] = None,
        project_root: Optional[Path] = None
    ) -> Path:
        """
        Resolve the loop directory with precedence:
        1. CLI flag (--loop-dir) - highest priority
        2. Project .env file (RAVL_DEFAULT_LOOP_DIRECTORY)
        3. Default (project_root/ravl_loops) - lowest priority

        Args:
            cli_loop_dir: CLI-provided loop directory
            project_root: Project root for loading .env and computing default

        Returns:
            Resolved loop directory path
        """
        # Priority 1: CLI flag (highest)
        if cli_loop_dir:
            return Path(cli_loop_dir).expanduser().resolve()

        # Priority 2: Project .env file
        if project_root:
            env_vars = RAVLRunner.load_env_file(project_root)
            if 'RAVL_DEFAULT_LOOP_DIRECTORY' in env_vars:
                loop_dir = Path(env_vars['RAVL_DEFAULT_LOOP_DIRECTORY'])
                return loop_dir.expanduser().resolve()

        # Priority 3: Default (lowest)
        if project_root:
            return (project_root / 'ravl_loops').resolve()

        # Fallback if no project root
        return Path('ravl_loops').resolve()

    @staticmethod
    def _resolve_path_relative_to(path_str: str, base_dir: Path) -> Path:
        """
        Resolve path relative to base directory if not absolute.

        Args:
            path_str: Path string (may be absolute or relative)
            base_dir: Base directory for relative path resolution

        Returns:
            Resolved absolute path
        """
        path = Path(path_str).expanduser()
        if not path.is_absolute():
            return (base_dir / path).resolve()
        return path.resolve()

    def resolve_learning_path(
        loop_dir: Path,
        loop_config: Optional[Dict[str, Any]] = None,
        cli_learning_path: Optional[Path] = None,
        project_root: Optional[Path] = None
    ) -> Path:
        """
        Resolve the learning path with precedence:
        1. CLI flag (--learning-path) - highest priority
        2. Loop config (learning_path in config/ravl.toml)
        3. Default (loop_dir/learnings) - lowest priority

        Relative paths are resolved relative to the directory containing the config:
        - Loop config: relative to loop_dir

        Child loops automatically inherit parent's learning_path from parent config:
        - Parent has learning_path="/data/ravl" → child gets "/data/ravl/child_learnings/child_name/learnings"
        - Parent has no learning_path → child uses default "child_dir/learnings"

        Args:
            loop_dir: Path to the loop directory
            loop_config: Parsed loop configuration (from ravl.toml)
            cli_learning_path: CLI-provided learning path
            project_root: Project root (unused but kept for compatibility)

        Returns:
            Resolved learning path
        """
        # Priority 1: CLI flag (highest)
        if cli_learning_path:
            return Path(cli_learning_path).expanduser().resolve()

        # Priority 2: Loop config
        # Relative paths resolved relative to loop directory
        if loop_config and 'learning_path' in loop_config:
            return RAVLRunner._resolve_path_relative_to(
                loop_config['learning_path'],
                loop_dir
            )

        # Child loops check parent configs for inheritance
        all_parents = RAVLRunner._find_all_parent_loops(loop_dir)
        for parent_dir in all_parents:
            parent_config_file = parent_dir / 'config' / 'ravl.toml'
            if parent_config_file.exists():
                try:
                    with open(parent_config_file, 'rb') as f:
                        parent_config = tomllib.load(f) or {}
                        if 'learning_path' in parent_config:
                            parent_learning_path = Path(parent_config['learning_path']).expanduser()
                            # If relative, resolve relative to parent directory
                            if not parent_learning_path.is_absolute():
                                parent_learning_path = (parent_dir / parent_learning_path).resolve()

                            # Build child path: collect all intermediate loop names between parent and child
                            child_segments = []
                            current = loop_dir
                            while current != parent_dir and current != current.parent:
                                if current.name != 'ravl_loops':
                                    child_segments.insert(0, current.name)
                                current = current.parent

                            # Build final path with child_learnings separator between each level
                            final_path = parent_learning_path
                            for segment in child_segments:
                                if segment not in ['child_loops', 'ravl_loops']:
                                    final_path = final_path / 'child_learnings' / segment
                            return (final_path / 'learnings').resolve()
                except Exception:
                    pass  # If parent config is malformed, try next parent

        # Priority 3 (Default): loop_dir/learnings
        return (loop_dir / 'learnings').resolve()

    @staticmethod
    def _find_parent_loop(loop_dir: Path) -> Optional[Path]:
        """
        Find parent loop if this is a nested loop.
        Uses child_loops directories to detect nesting.

        Returns:
            Path to parent loop or None if top-level
        """
        # Count 'child_loops' in path
        child_loops_indices = [
            i for i, part in enumerate(loop_dir.parts)
            if part == 'child_loops'
        ]

        if len(child_loops_indices) >= 1:
            # Nested loop: parent is everything before the last 'child_loops'
            last_child_loops_idx = child_loops_indices[-1]
            parent_path = Path(*loop_dir.parts[:last_child_loops_idx])
            return parent_path

        return None

    @staticmethod
    def _find_all_parent_loops(loop_dir: Path) -> List[Path]:
        """
        Find all parent loops in the hierarchy, from immediate to root.

        Returns:
            List of parent paths, ordered from nearest (immediate parent) to farthest (root)

        Example:
            loop: ravl_loops/grandparent/child_loops/parent/child_loops/child
            returns: [parent, grandparent]
        """
        parents = []
        child_loops_indices = [
            i for i, part in enumerate(loop_dir.parts)
            if part == 'child_loops'
        ]

        # Walk from innermost to outermost parent
        # Start from last child_loops (immediate parent) and work backwards
        for i in range(len(child_loops_indices) - 1, -1, -1):
            parent_idx = child_loops_indices[i]
            parent_path = Path(*loop_dir.parts[:parent_idx])
            parents.append(parent_path)

        return parents

    @staticmethod
    def resolve_venv_path(
        loop_dir: Path,
        loop_config: Optional[Dict[str, Any]] = None,
        cli_venv_path: Optional[Path] = None,
        project_root: Optional[Path] = None
    ) -> Path:
        """
        Resolve the venv path with precedence:
        1. CLI flag (--venv-path) - highest priority
        2. Loop config (venv_path in ravl.toml)
        3. Project config (venv_path in ravl_loops/config/ravl.toml)
        4. Project .env file (RAVL_DEFAULT_VENV_DIRECTORY)
        5. Default (.ravl/venv) - lowest priority

        All loops in a project can share the same venv, or each loop can have its own.

        Args:
            loop_dir: Path to the loop directory
            loop_config: Parsed loop configuration (from ravl.toml)
            cli_venv_path: CLI-provided venv path
            project_root: Project root for loading .env and project config

        Returns:
            Resolved venv path
        """
        # Priority 1: CLI flag (highest)
        if cli_venv_path:
            return Path(cli_venv_path).expanduser().resolve()

        # Priority 2: Loop config
        if loop_config and 'venv_path' in loop_config:
            return Path(loop_config['venv_path']).expanduser().resolve()

        # Priority 3: Project-level config (ravl_loops/config/ravl.toml)
        if project_root:
            project_loops_config = project_root / 'ravl_loops' / 'config' / 'ravl.toml'
            if project_loops_config.exists():
                try:
                    import toml
                    with open(project_loops_config, 'rb') as f:
                        project_config = tomllib.load(f) or {}
                        if 'venv_path' in project_config:
                            return Path(project_config['venv_path']).expanduser().resolve()
                except Exception:
                    pass

        # Priority 4: Project .env file
        if project_root:
            env_vars = RAVLRunner.load_env_file(project_root)
            if 'RAVL_DEFAULT_VENV_DIRECTORY' in env_vars:
                return Path(env_vars['RAVL_DEFAULT_VENV_DIRECTORY']).expanduser().resolve()

        # Priority 5: Default (installation-aware)
        if not project_root:
            # Find project root from loop_dir when project_root not provided
            # Uses loop_dir as fallback if outside RAVL project
            project_root = RAVLCLIBase.find_project_root(loop_dir, required=False)

        installation_type = RAVLCLIBase.get_installation_type()

        if installation_type == 'submodule':
            # Submodule: use .ravl/venv (backward compatible)
            return (project_root / '.ravl' / 'venv').resolve()
        else:
            # UV/package: use canonical .venv at project root
            return (project_root / '.venv').resolve()

    @staticmethod
    def resolve_llm_config(
        loop_dir: Path,
        loop_config: Optional[Dict[str, Any]] = None,
        project_root: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Resolve the LLM provider and model configuration with precedence:

        Provider precedence:
        1. Loop config (llm_provider in ravl.toml)
        2. Parent config (parent's config/ravl.toml llm_provider)
        3. Project config (ravl_loops/config/ravl.toml llm_provider)
        4. Framework config (.ravl/config/llm.toml llm.default_provider)
        5. Project .env file (RAVL_DEFAULT_LLM_PROVIDER)
        6. Auto-detect from API keys (anthropic > openai > google > ollama)

        Model precedence (if not in provider config above):
        4. Framework config (.ravl/config/llm.toml llm.default_model)
        5. Project .env file (RAVL_DEFAULT_MODEL)
        6. Provider hardcoded defaults (claude-sonnet-4-5, gpt-4o, gemini-3-pro-preview, llama3.1)

        Configuration formats supported:
        - Simple string: llm_provider: anthropic
        - Full dict: llm_provider: {provider: anthropic, model: claude-sonnet-4-5, temperature: 0.7}

        Args:
            loop_dir: Path to the loop directory
            loop_config: Parsed loop configuration (from ravl.toml)
            project_root: Project root for loading .env and project config

        Returns:
            Dict with keys: provider (str), model (Optional[str]), and optional parameters
            like temperature, max_tokens, top_p, etc.
        """
        # Priority 1: Loop config
        if loop_config and 'llm_provider' in loop_config:
            config = RAVLRunner._normalize_llm_config(loop_config['llm_provider'])
            config['_source'] = 'loop config'
            return config

        # Priority 2: Parent configs (walk full parent chain from immediate to root)
        all_parents = RAVLRunner._find_all_parent_loops(loop_dir)
        for parent_dir in all_parents:
            parent_config_file = parent_dir / 'config' / 'ravl.toml'
            if parent_config_file.exists():
                try:
                    import toml
                    with open(parent_config_file, 'rb') as f:
                        parent_config = tomllib.load(f) or {}
                        if 'llm_provider' in parent_config:
                            config = RAVLRunner._normalize_llm_config(parent_config['llm_provider'])
                            config['_source'] = 'parent config'
                            return config
                except Exception:
                    pass  # If parent config is malformed, try next parent

        # Priority 3: Project config (ravl_loops/config/ravl.toml)
        if project_root:
            project_config_file = project_root / 'ravl_loops' / 'config' / 'ravl.toml'
            if project_config_file.exists():
                try:
                    import toml
                    with open(project_config_file, 'rb') as f:
                        project_config = tomllib.load(f) or {}
                        if 'llm_provider' in project_config:
                            config = RAVLRunner._normalize_llm_config(project_config['llm_provider'])
                            config['_source'] = 'project config'
                            return config
                except Exception:
                    pass  # If project config is malformed, fall through to next priority

        # Priority 4: Framework config (.ravl/config/llm.toml)
        from ravl.common.config.config_service import get_llm_provider_from_framework_config, get_llm_model_from_framework_config
        framework_provider = get_llm_provider_from_framework_config(project_root)
        framework_model = get_llm_model_from_framework_config(project_root)

        if framework_provider:
            config = RAVLRunner._normalize_llm_config(framework_provider)
            # Add framework model if present and not already set
            if framework_model and 'model' not in config:
                config['model'] = framework_model
            config['_source'] = 'framework config'
            return config

        # Priority 5: Project .env file
        if project_root:
            env_vars = RAVLRunner.load_env_file(project_root)
            env_provider = env_vars.get('RAVL_DEFAULT_LLM_PROVIDER')
            env_model = env_vars.get('RAVL_DEFAULT_MODEL')

            if env_provider:
                # Try to parse as JSON first (for dict format in .env)
                try:
                    import json
                    parsed = json.loads(env_provider)
                    if isinstance(parsed, dict):
                        config = RAVLRunner._normalize_llm_config(parsed)
                        # Add env model if present and not already set
                        if env_model and 'model' not in config:
                            config['model'] = env_model
                        config['_source'] = '.env file'
                        return config
                except (json.JSONDecodeError, ValueError):
                    pass
                # Otherwise treat as simple string
                config = RAVLRunner._normalize_llm_config(env_provider)
                # Add env model if present
                if env_model:
                    config['model'] = env_model
                config['_source'] = '.env file'
                return config

            # If only model in .env but no provider, use it as a default for auto-detect
            if env_model:
                config = RAVLRunner._autodetect_llm_provider(project_root)
                config['model'] = env_model
                config['_source'] = '.env file (model only)'
                return config

        # Priority 6: Auto-detect from API keys (lowest)
        # Check if framework model should be applied to auto-detected provider
        config = RAVLRunner._autodetect_llm_provider(project_root)
        if framework_model and 'model' not in config:
            config['model'] = framework_model
            config['_source'] = f"{config.get('_source', 'auto-detected')} + framework model"
        return config

    @staticmethod
    def _normalize_llm_config(config: Any) -> Dict[str, Any]:
        """
        Normalize LLM config from various formats to standard dict

        Supports:
        - String: "anthropic" -> {provider: "anthropic"}
        - Dict: {provider: "anthropic", model: "...", temperature: 0.7, ...}

        Args:
            config: String or dict config value

        Returns:
            Normalized dict with at least 'provider' key
        """
        if isinstance(config, str):
            return {'provider': config}
        elif isinstance(config, dict):
            # Ensure 'provider' key exists
            if 'provider' not in config:
                raise ValueError("llm_provider dict must have 'provider' key")
            return config
        else:
            raise ValueError(f"Invalid llm_provider format: {type(config).__name__}. Must be string or dict.")

    @staticmethod
    def _autodetect_llm_provider(project_root: Optional[Path] = None) -> Dict[str, Any]:
        """
        Auto-detect LLM provider from available API keys

        First checks framework config, then falls back to API key priority order.

        Checks in priority order:
        1. Framework config default (if credentials exist for that provider)
        2. ANTHROPIC_API_KEY
        3. OPENAI_API_KEY
        4. GOOGLE_API_KEY
        5. Falls back to ollama (local, no key needed)

        Args:
            project_root: Project root for reading framework config

        Returns:
            Dict with 'provider' key
        """
        import os

        # Check framework config first - if it specifies a default and has credentials, use it
        if project_root:
            from ravl.common.config.config_service import get_llm_provider_from_framework_config
            framework_provider = get_llm_provider_from_framework_config(project_root)

            if framework_provider:
                # Framework specifies a default - use it if credentials exist
                if framework_provider == 'anthropic' and os.environ.get("ANTHROPIC_API_KEY"):
                    return {'provider': 'anthropic', '_source': 'framework config + auto-detect'}
                elif framework_provider == 'openai' and os.environ.get("OPENAI_API_KEY"):
                    return {'provider': 'openai', '_source': 'framework config + auto-detect'}
                elif framework_provider == 'google' and os.environ.get("GOOGLE_API_KEY"):
                    return {'provider': 'google', '_source': 'framework config + auto-detect'}
                elif framework_provider == 'ollama':
                    return {'provider': 'ollama', '_source': 'framework config'}
                # Fall through to auto-detect if framework provider has no credentials

        # Auto-detect from API keys (only if framework config doesn't specify or lacks credentials)
        if os.environ.get("ANTHROPIC_API_KEY"):
            return {'provider': 'anthropic', '_source': 'auto-detected'}
        elif os.environ.get("OPENAI_API_KEY"):
            return {'provider': 'openai', '_source': 'auto-detected'}
        elif os.environ.get("GOOGLE_API_KEY"):
            return {'provider': 'google', '_source': 'auto-detected'}
        else:
            return {'provider': 'ollama', '_source': 'auto-detected'}

    @staticmethod
    def find_project_root(start_path: Path) -> Path:
        """
        Find the project root by looking for .git directory

        Args:
            start_path: Starting path to search from

        Returns:
            Path to project root (directory containing .git)
        """
        current = start_path.resolve()
        while current.parent != current:  # Stop at filesystem root
            if (current / '.git').exists():
                return current
            current = current.parent
        # If no .git found, return the original path's parent directory
        return start_path.parent

    @staticmethod
    def load_previous_findings(findings_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load previous findings from JSON file

        Args:
            findings_path: Path to findings file

        Returns:
            Previous findings dict or None if not found
        """
        if not findings_path.exists():
            return None

        try:
            with open(findings_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    @staticmethod
    def load_previous_findings_jsonl(jsonl_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load previous findings from JSONL history (last line)

        Args:
            jsonl_path: Path to JSONL history file

        Returns:
            Last entry from JSONL file or None
        """
        if not jsonl_path.exists() or jsonl_path.stat().st_size == 0:
            return None

        try:
            with open(jsonl_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    # Return last line (most recent entry)
                    return json.loads(lines[-1])
        except (json.JSONDecodeError, IndexError):
            return None

        return None

    @staticmethod
    def save_findings(findings: Dict[str, Any], findings_path: Path):
        """
        Save findings to JSON file

        Args:
            findings: Findings dict to save
            findings_path: Path to save to
        """
        findings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(findings_path, 'w') as f:
            json.dump(findings, f, indent=2, ensure_ascii=False)

    @staticmethod
    def append_to_jsonl(findings: Dict[str, Any], jsonl_path: Path):
        """
        Append findings to JSONL history file

        Args:
            findings: Findings dict to append
            jsonl_path: Path to JSONL file
        """
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with open(jsonl_path, 'a') as f:
            f.write(json.dumps(findings, ensure_ascii=False) + '\n')

    @staticmethod
    def setup_logging(log_dir: Path, loop_name: str) -> TeeLogger:
        """
        Setup file logging that writes to both file and stderr

        Args:
            log_dir: Directory to write log files to
            loop_name: Name of loop (for log filename)

        Returns:
            TeeLogger instance
        """
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S')
        log_file = log_dir / f'{timestamp}_{loop_name}_run.log'

        tee_logger = TeeLogger(log_file, sys.stderr)
        sys.stderr = tee_logger

        return tee_logger

    @staticmethod
    def create_base_parser(description: str) -> argparse.ArgumentParser:
        """
        Create base argument parser with common RAVL options

        Args:
            description: Description for the parser

        Returns:
            ArgumentParser with common options
        """
        parser = argparse.ArgumentParser(description=description)
        parser.add_argument('--mode', choices=['full', 'fast', 'execute'], default='full',
                           help='Execution mode: full=complete RAVL cycle (REFLECT-ACT-VERIFY-LEARN), fast=use cached code with verification (REFLECT-ACT-VERIFY), execute=run cached code only (ACT)')
        parser.add_argument('--no-deep-learning', action='store_true',
                           help='Skip verify and learn phases')
        parser.add_argument('--timeout', type=int, default=300,
                           help='Timeout in seconds (default: 300)')
        parser.add_argument('--show-execution', action='store_true',
                           help='Show execution learning details (code generation, DSL, caching). '
                                'Default: only show domain learning progress.')
        parser.add_argument('--force-code-regeneration', action='store_true',
                           help='Force fresh code generation, bypassing cache for this run')
        return parser

    @staticmethod
    def run_ravl_phases(
        loop,
        previous_findings: Optional[Dict[str, Any]] = None,
        deep_learning: bool = True,
        fetch_external: Optional[bool] = None,
        quiet: bool = False
    ) -> Dict[str, Any]:
        """
        Run standard RAVL phases: Reflect → Act → (Verify → Learn if deep_learning)

        Args:
            loop: RAVL loop instance
            previous_findings: Previous run's findings (for learning)
            deep_learning: Whether to run verify & learn phases
            fetch_external: For parent loops, whether to fetch external sources
            quiet: Whether to suppress phase banners and status output

        Returns:
            Findings from act phase
        """
        if not quiet:
            RAVLRunner.print_banner("Step 1 of 4: [R]EFLECT", "")

        # Reflect
        reflection = loop.reflect()

        # Act (with optional fetch_external for parent loops)
        if not quiet:
            RAVLRunner.print_banner("Step 2 of 4: [A]CT", "")
            
        if fetch_external is not None:
            action_results = loop.act(reflection, fetch_external=fetch_external)
        else:
            action_results = loop.act(reflection)

        # Verify & Learn (if enabled)
        if deep_learning:
            if not quiet:
                RAVLRunner.print_banner("Step 3 of 4: [V]ERIFY", "")

            verification = loop.verify(action_results, reflection)

            if not quiet:
                RAVLRunner.print_banner("Step 4 of 4: [L]EARN", "")

            loop.learn(verification, action_results)

        return action_results

    @staticmethod
    def print_banner(message: str, emoji: str = "✅"):
        """Print a formatted banner message"""
        # Print blank line
        log_message("", status='info', indent=0)
        # Print top separator directly without [i] prefix
        print("="*80, file=sys.stderr, flush=True)
        # Print message with [i] prefix
        log_message(f"{emoji} {message}", status='info', indent=0)
        # Print bottom separator directly without [i] prefix
        print("="*80, file=sys.stderr, flush=True)

    @staticmethod
    def print_summary(findings: Dict[str, Any], duration: float, loop_name: str, log_file: Optional[Path] = None):
        """
        Print run summary

        Args:
            findings: Findings dict with results
            duration: Run duration in seconds
            loop_name: Name of the loop
            log_file: Optional log file path
        """
        RAVLRunner.print_banner(f"{loop_name} completed successfully")
        log_message(f"Duration: {duration:.1f}s", status='info', indent=3)

        # Print loop-specific counts
        if 'summary' in findings:
            summary = findings['summary']
            log_message(f"Total issues: {summary.get('total_issues', 0)}", status='info', indent=3)
            log_message(f"Coherence score: {summary.get('overall_coherence_score', 'N/A')}", status='info', indent=3)
        elif 'gaps_found' in findings:
            log_message(f"Gaps found: {len(findings['gaps_found'])}", status='info', indent=3)
        elif 'drift_findings' in findings:
            log_message(f"Drift findings: {len(findings['drift_findings'])}", status='info', indent=3)
        elif 'gaps' in findings:
            log_message(f"Gaps found: {len(findings['gaps'])}", status='info', indent=3)

        if log_file:
            log_message(f"Log file: {log_file.name}", status='info', indent=3)

        log_message("="*80, status='info', indent=0)

    @staticmethod
    def handle_error(exception: Exception, tee_logger: Optional[TeeLogger] = None):
        """
        Handle and report errors

        Args:
            exception: The exception that occurred
            tee_logger: Optional TeeLogger to close
        """
        if isinstance(exception, KeyboardInterrupt):
            log_message("\n\n⚠️  Interrupted by user", status='error', indent=0)
            exit_code = 1
        else:
            log_message(f"\n\n❌ ERROR: {exception}", status='error', indent=0)
            import traceback
            traceback.print_exc(file=sys.stderr)
            exit_code = 1

        if tee_logger:
            tee_logger.close()

        sys.exit(exit_code)
