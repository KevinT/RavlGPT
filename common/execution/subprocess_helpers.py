#!/usr/bin/env python3
"""
Subprocess Helpers

Minimal utilities for calling external commands from generated code.
Handles environment cleanup when generated code runs in venv but needs
to call commands that require framework dependencies.

Following HELPER_PATTERN philosophy:
- Stateless utilities (@staticmethod)
- Parse/extract only, no workflow
- Optional - LLM can implement inline if preferred
"""

import os
import subprocess
from typing import List, Any, Dict


class SubprocessHelper:
    """
    Minimal utility for executing external commands from generated code.

    Use when generated code runs in a venv but needs to call commands that
    require framework dependencies (e.g., ravl script, system Python).
    """

    @staticmethod
    def call_with_clean_env(
        command: List[str],
        **kwargs: Any
    ) -> subprocess.CompletedProcess:
        """
        Execute command with virtual environment removed from environment.

        When generated code runs in a venv, subprocess calls inherit the venv
        environment. This causes issues when calling commands that need framework
        dependencies (like the ravl script which imports pyyaml, etc.).

        This helper removes VIRTUAL_ENV and cleans venv paths from PATH.

        Args:
            command: Command to execute (list format: ["cmd", "arg1", "arg2"])
            **kwargs: Additional arguments passed to subprocess.run()

        Returns:
            CompletedProcess instance with stdout, stderr, returncode

        Example:
            >>> from ravl.common.execution.subprocess_helpers import SubprocessHelper
            >>>
            >>> # Get project root
            >>> project_root = SubprocessHelper.get_project_root()
            >>>
            >>> # Call child ravl loop with clean environment
            >>> result = SubprocessHelper.call_with_clean_env(
            ...     [f"{project_root}/ravl", "child_loop_name"],
            ...     capture_output=True,
            ...     text=True,
            ...     cwd=project_root
            ... )
            >>>
            >>> if result.returncode == 0:
            ...     print("Child loop succeeded")
            ... else:
            ...     print(f"Child loop failed: {result.stderr}")
        """
        # Copy environment and remove venv-specific variables
        env = os.environ.copy()

        # Remove VIRTUAL_ENV variable if present
        if 'VIRTUAL_ENV' in env:
            del env['VIRTUAL_ENV']

        # Clean venv paths from PATH
        if 'PATH' in env:
            paths = env['PATH'].split(os.pathsep)
            # Remove paths containing /venv/ or ending with /venv/bin
            cleaned_paths = [
                p for p in paths
                if '/venv/' not in p and not p.endswith('/venv/bin')
            ]
            env['PATH'] = os.pathsep.join(cleaned_paths)

        # Execute command with cleaned environment
        return subprocess.run(command, env=env, **kwargs)

    @staticmethod
    def get_project_root() -> str:
        """
        Get the project root directory using git.

        Returns:
            Absolute path to project root (where .git directory is)

        Raises:
            subprocess.CalledProcessError: If not in a git repository

        Example:
            >>> from ravl.common.execution.subprocess_helpers import SubprocessHelper
            >>>
            >>> project_root = SubprocessHelper.get_project_root()
            >>> print(f"Project root: {project_root}")
            >>>
            >>> # Use with ravl script
            >>> ravl_script = f"{project_root}/ravl"
            >>> result = SubprocessHelper.call_with_clean_env([ravl_script, "my_loop"])
        """
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
