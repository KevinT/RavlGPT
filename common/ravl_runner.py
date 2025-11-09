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
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, TextIO, Callable, List

from utils.constants import DEFAULT_EXECUTION_TIMEOUT, MODEL_PATTERN


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
                print(f"  ⚠️  Warning: Could not load .env file: {e}", file=sys.stderr)

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
        # Filter out intermediate "ravl_loops" directories (they separate parent/child boundaries)
        hierarchy = []
        for part in parts[first_ravl_loops_idx + 1:]:
            if part != 'ravl_loops':
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
        2. Loop config (learning_path in ravl.yml)
        3. Parent config (parent's config/ravl.yml learning_path)
        4. Project config (ravl_loops/config/ravl.yml learning_path)
        5. Project .env file (RAVL_DEFAULT_LEARNING_DIRECTORY)
        6. Default (loop_dir/learnings) - lowest priority

        Relative paths are resolved relative to the directory containing the config:
        - Loop config: relative to loop_dir
        - Parent config: relative to parent_dir
        - Project config: relative to project_root

        .env RAVL_DEFAULT_LEARNING_DIRECTORY only applies if NO config specifies learning_path.

        Child loops automatically inherit parent path structure:
        - If running child loop directly: /data/ravl-learning/parent/child/learnings
        - If running parent loop: /data/ravl-learning/parent/learnings

        Args:
            loop_dir: Path to the loop directory
            loop_config: Parsed loop configuration (from ravl.yml)
            cli_learning_path: CLI-provided learning path
            project_root: Project root for loading .env

        Returns:
            Resolved learning path
        """
        # Track if we found a path in config (priorities 2-4)
        # This ensures .env only applies when NO config specifies learning_path
        config_path_found = False

        # Priority 1: CLI flag (highest)
        if cli_learning_path:
            return Path(cli_learning_path).expanduser().resolve()

        # Priority 2: Loop config
        # FIXED: Relative paths now resolved relative to loop directory
        if loop_config and 'learning_path' in loop_config:
            config_path_found = True
            return RAVLRunner._resolve_path_relative_to(
                loop_config['learning_path'],
                loop_dir
            )

        # Priority 3: Parent configs (walk full parent chain from immediate to root)
        all_parents = RAVLRunner._find_all_parent_loops(loop_dir)
        for parent_dir in all_parents:
            parent_config_file = parent_dir / 'config' / 'ravl.yml'
            if parent_config_file.exists():
                try:
                    import yaml
                    with open(parent_config_file, 'r') as f:
                        parent_config = yaml.safe_load(f) or {}
                        if 'learning_path' in parent_config:
                            config_path_found = True
                            parent_learning_path = Path(parent_config['learning_path']).expanduser()
                            # If relative, resolve relative to parent directory
                            if not parent_learning_path.is_absolute():
                                parent_learning_path = (parent_dir / parent_learning_path).resolve()

                            # Build child path: collect all intermediate loop names between parent and child
                            # Example: parent=frontier_engineering, child=context_ingestion
                            # Intermediate: context_management
                            # Result: parent_path/context_management/context_ingestion/learnings
                            child_segments = []
                            current = loop_dir
                            while current != parent_dir and current != current.parent:
                                # Skip 'ravl_loops' directories - they're structural, not semantic
                                if current.name != 'ravl_loops':
                                    child_segments.insert(0, current.name)
                                current = current.parent

                            # Build final path
                            final_path = parent_learning_path
                            for segment in child_segments:
                                final_path = final_path / segment
                            return (final_path / 'learnings').resolve()
                except Exception:
                    pass  # If parent config is malformed, try next parent

        # Priority 4: Project config (ravl_loops/config/ravl.yml)
        if project_root:
            project_config_file = project_root / 'ravl_loops' / 'config' / 'ravl.yml'
            if project_config_file.exists():
                try:
                    import yaml
                    with open(project_config_file, 'r') as f:
                        project_config = yaml.safe_load(f) or {}
                        if 'learning_path' in project_config:
                            config_path_found = True
                            project_learning_path = Path(project_config['learning_path']).expanduser()
                            # If relative, resolve relative to project root
                            if not project_learning_path.is_absolute():
                                project_learning_path = (project_root / project_learning_path).resolve()
                            # Build path structure for this loop
                            child_path = RAVLRunner._detect_child_loop_path(loop_dir)
                            if child_path:
                                return (project_learning_path / child_path / 'learnings').resolve()
                            else:
                                return (project_learning_path / loop_dir.name / 'learnings').resolve()
                except Exception:
                    pass  # If project config is malformed, fall through to next priority

        # Priority 5: Project .env file (ONLY if no config specified learning_path)
        if not config_path_found and project_root:
            env_vars = RAVLRunner.load_env_file(project_root)
            if 'RAVL_DEFAULT_LEARNING_DIRECTORY' in env_vars:
                base_path = Path(env_vars['RAVL_DEFAULT_LEARNING_DIRECTORY']).expanduser()

                # Check if this is a child loop and build appropriate path structure
                child_path = RAVLRunner._detect_child_loop_path(loop_dir)
                if child_path:
                    # Child loop: {base}/{parent}/{child}/learnings
                    return (base_path / child_path / 'learnings').resolve()
                else:
                    # Parent loop: {base}/{loop_name}/learnings
                    return (base_path / loop_dir.name / 'learnings').resolve()

        # Priority 6: Default (lowest)
        return (loop_dir / 'learnings').resolve()

    @staticmethod
    def _find_parent_loop(loop_dir: Path) -> Optional[Path]:
        """
        Find parent loop if this is a nested loop.
        Uses the same algorithm as DependencyValidator for consistency.

        Returns:
            Path to parent loop or None if top-level
        """
        # Count 'ravl_loops' in path
        ravl_loops_indices = [
            i for i, part in enumerate(loop_dir.parts)
            if part == 'ravl_loops'
        ]

        if len(ravl_loops_indices) >= 2:
            # Nested loop: parent is everything before the last 'ravl_loops'
            last_ravl_loops_idx = ravl_loops_indices[-1]
            parent_path = Path(*loop_dir.parts[:last_ravl_loops_idx])
            return parent_path

        return None

    @staticmethod
    def _find_all_parent_loops(loop_dir: Path) -> List[Path]:
        """
        Find all parent loops in the hierarchy, from immediate to root.

        Returns:
            List of parent paths, ordered from nearest (immediate parent) to farthest (root)

        Example:
            loop: ravl_loops/grandparent/ravl_loops/parent/ravl_loops/child
            returns: [parent, grandparent]
        """
        parents = []
        ravl_loops_indices = [
            i for i, part in enumerate(loop_dir.parts)
            if part == 'ravl_loops'
        ]

        # Walk from innermost to outermost parent
        # Start from second-to-last ravl_loops (immediate parent) and work backwards
        for i in range(len(ravl_loops_indices) - 1, 0, -1):
            parent_idx = ravl_loops_indices[i]
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
        2. Loop config (venv_path in ravl.yml)
        3. Project config (venv_path in ravl_loops/config/ravl.yml)
        4. Project .env file (RAVL_DEFAULT_VENV_DIRECTORY)
        5. Default (.ravl/venv) - lowest priority

        All loops in a project can share the same venv, or each loop can have its own.

        Args:
            loop_dir: Path to the loop directory
            loop_config: Parsed loop configuration (from ravl.yml)
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

        # Priority 3: Project-level config (ravl_loops/config/ravl.yml)
        if project_root:
            project_loops_config = project_root / 'ravl_loops' / 'config' / 'ravl.yml'
            if project_loops_config.exists():
                try:
                    import yaml
                    with open(project_loops_config, 'r') as f:
                        project_config = yaml.safe_load(f) or {}
                        if 'venv_path' in project_config:
                            return Path(project_config['venv_path']).expanduser().resolve()
                except Exception:
                    pass

        # Priority 4: Project .env file
        if project_root:
            env_vars = RAVLRunner.load_env_file(project_root)
            if 'RAVL_DEFAULT_VENV_DIRECTORY' in env_vars:
                return Path(env_vars['RAVL_DEFAULT_VENV_DIRECTORY']).expanduser().resolve()

        # Priority 5: Default (.ravl/venv)
        if project_root:
            return (project_root / '.ravl' / 'venv').resolve()
        else:
            return (loop_dir.parent.parent / '.ravl' / 'venv').resolve()

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
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')
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
        parser.add_argument('--mode', choices=['fast', 'full'], default='full',
                           help='Analysis mode (fast=quick check, full=deep analysis)')
        parser.add_argument('--no-deep-learning', action='store_true',
                           help='Skip verify and learn phases')
        parser.add_argument('--timeout', type=int, default=300,
                           help='Timeout in seconds (default: 300)')
        parser.add_argument('--show-execution', action='store_true',
                           help='Show execution learning details (code generation, DSL, caching). '
                                'Default: only show domain learning progress.')
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
        print("\n" + "="*80, file=sys.stderr)
        print(f"{emoji} {message}", file=sys.stderr)
        print("="*80, file=sys.stderr)

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
        print(f"   Duration: {duration:.1f}s", file=sys.stderr)

        # Print loop-specific counts
        if 'summary' in findings:
            summary = findings['summary']
            print(f"   Total issues: {summary.get('total_issues', 0)}", file=sys.stderr)
            print(f"   Coherence score: {summary.get('overall_coherence_score', 'N/A')}", file=sys.stderr)
        elif 'gaps_found' in findings:
            print(f"   Gaps found: {len(findings['gaps_found'])}", file=sys.stderr)
        elif 'drift_findings' in findings:
            print(f"   Drift findings: {len(findings['drift_findings'])}", file=sys.stderr)
        elif 'gaps' in findings:
            print(f"   Gaps found: {len(findings['gaps'])}", file=sys.stderr)

        if log_file:
            print(f"   Log file: {log_file.name}", file=sys.stderr)

        print("="*80, file=sys.stderr)

    @staticmethod
    def handle_error(exception: Exception, tee_logger: Optional[TeeLogger] = None):
        """
        Handle and report errors

        Args:
            exception: The exception that occurred
            tee_logger: Optional TeeLogger to close
        """
        if isinstance(exception, KeyboardInterrupt):
            print("\n\n⚠️  Interrupted by user", file=sys.stderr)
            exit_code = 1
        else:
            print(f"\n\n❌ ERROR: {exception}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            exit_code = 1

        if tee_logger:
            tee_logger.close()

        sys.exit(exit_code)
