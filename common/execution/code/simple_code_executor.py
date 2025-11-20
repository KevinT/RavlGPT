#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Simple Code Executor

General-purpose code executor for RAVL loops that don't require structured JSON output.
Executes Python code in isolated venvs with automatic dependency management.
"""

import sys
import re
import tempfile
import subprocess
import time
import hashlib
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# Add utils to path
_script_dir = Path(__file__).parent
_utils_dir = _script_dir.parent.parent / 'utils'
if str(_utils_dir) not in sys.path:
    sys.path.insert(0, str(_utils_dir))

from logging_utils import log_execution
from venv_manager import VenvManager
from requirements_generator import RequirementsGenerator


class SimpleCodeExecutor:
    """
    Simple code executor for general-purpose code generation (non-data-ingestion loops)

    Unlike DataIngressExecutor which expects JSON output, this executor:
    - Runs code without parsing output
    - Checks for execution errors (non-zero exit code)
    - Success = code ran without errors
    - Suitable for file I/O, data transforms, and other general operations

    Features:
    - Automatic virtual environment detection/creation
    - Automatic requirements.txt generation from imports
    - Automatic dependency installation
    - Runs code with venv Python executable
    """

    def __init__(self, loop_dir: Path, project_root: Optional[Path] = None):
        """
        Initialize the simple executor

        Args:
            loop_dir: Path to the loop directory
            project_root: Path to project root (for venv/learning path resolution)
        """
        self.loop_dir = loop_dir
        self.project_root = project_root or self._find_project_root()

        # Resolve learnings directory for generated_requirements.txt
        from ravl_runner import RAVLRunner
        self.learnings_dir = RAVLRunner.resolve_learning_path(
            loop_dir=loop_dir,
            project_root=self.project_root
        )

    def _find_project_root(self) -> Path:
        """Find project root by looking for .git directory"""
        current = self.loop_dir.resolve()
        while current.parent != current:
            if (current / '.git').exists():
                return current
            current = current.parent
        return self.loop_dir.parent

    def execute_code(self, code: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Execute generated Python code with venv support

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds

        Returns:
            Dict with keys: success (bool), error (str), execution_time (float),
                           stdout (str), stderr (str), code_hash (str)
        """
        # Clean markdown code fences if present
        code_clean = self._clean_markdown_fences(code)

        try:
            # Resolve venv path using RAVLRunner resolution logic
            from ravl_runner import RAVLRunner

            config = self._load_config()
            venv_path = RAVLRunner.resolve_venv_path(
                loop_dir=self.loop_dir,
                loop_config=config,
                project_root=self.project_root
            )

            # Validate existing venv or create new one
            venv_manager = VenvManager(venv_path)

            # Check if existing venv has correct Python version
            is_valid, issue = venv_manager.validate_venv()
            if not is_valid and venv_manager.exists():
                # Venv exists but has wrong Python version - recreate it
                log_execution(f"Venv needs recreation: {issue}", status='info')
                delete_success, delete_error = venv_manager.delete()
                if not delete_success:
                    return {
                        'success': False,
                        'error': f'Failed to delete incompatible venv: {delete_error}',
                        'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                    }
                log_execution("Deleted incompatible venv, will recreate with correct Python", status='info')

            # Create venv if needed (with correct Python version)
            success, error = venv_manager.detect_or_create()
            if not success:
                return {
                    'success': False,
                    'error': f'Failed to create venv: {error}',
                    'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                }

            # Generate requirements.txt from code imports
            execution_learning_dir = self.learnings_dir / 'execution_learning'
            execution_learning_dir.mkdir(parents=True, exist_ok=True)
            requirements_path = execution_learning_dir / 'generated_requirements.txt'
            RequirementsGenerator.save_requirements(code_clean, requirements_path)

            # Install requirements into venv
            success, error = venv_manager.install_requirements(requirements_path, quiet=True)
            if not success:
                return {
                    'success': False,
                    'error': f'Failed to install requirements: {error}',
                    'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                }

            # Write code to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                temp_file = Path(f.name)
                f.write(code_clean)

            try:
                start_time = time.time()

                # Get environment with venv activated
                env = venv_manager.get_environment_vars()
                env['PYTHONUNBUFFERED'] = '1'

                # Provide loop directories to generated code
                # Resolve learnings directory using same logic as main executor
                from ravl_runner import RAVLRunner
                learnings_dir = RAVLRunner.resolve_learning_path(
                    loop_dir=self.loop_dir,
                    loop_config=config,
                    cli_learning_path=None,
                    project_root=self.project_root
                )
                env['RAVL_LEARNINGS_DIR'] = str(learnings_dir)
                env['RAVL_LOOP_DIR'] = str(self.loop_dir)

                # Load .env file from project root and add to environment
                project_root = self.project_root
                env_vars = RAVLRunner.load_env_file(project_root)
                env.update(env_vars)

                # Execute code in subprocess with venv Python using Popen for real-time output
                import threading

                process = subprocess.Popen(
                    [venv_manager.get_python_executable(), str(temp_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    bufsize=1  # Line buffered
                )

                # Capture output while displaying in real-time
                stdout_lines = []
                stderr_lines = []

                def read_stream(stream, output_list, display_stream):
                    """Read from stream, append to list, and display in real-time"""
                    for line in iter(stream.readline, ''):
                        if line:
                            output_list.append(line)
                            print(line, end='', file=display_stream, flush=True)
                    stream.close()

                # Start threads to read stdout and stderr concurrently
                stdout_thread = threading.Thread(
                    target=read_stream,
                    args=(process.stdout, stdout_lines, sys.stdout)
                )
                stderr_thread = threading.Thread(
                    target=read_stream,
                    args=(process.stderr, stderr_lines, sys.stderr)
                )

                stdout_thread.daemon = True
                stderr_thread.daemon = True
                stdout_thread.start()
                stderr_thread.start()

                # Wait for process to complete with timeout
                try:
                    returncode = process.wait(timeout=timeout)

                    # Wait for output threads to finish reading
                    stdout_thread.join(timeout=2)
                    stderr_thread.join(timeout=2)

                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout_thread.join(timeout=2)
                    stderr_thread.join(timeout=2)

                    error_msg = f'Code execution timeout after {timeout}s'
                    return {
                        'success': False,
                        'error': error_msg,
                        'execution_time': timeout,
                        'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                    }

                execution_time = time.time() - start_time

                # Join output into strings
                stdout_text = ''.join(stdout_lines)
                stderr_text = ''.join(stderr_lines)

                # Success = code ran without errors (exit code 0)
                if returncode == 0:
                    return {
                        'success': True,
                        'stdout': stdout_text,
                        'stderr': stderr_text,
                        'execution_time': execution_time,
                        'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                    }
                else:
                    error_msg = stderr_text or stdout_text or f'Exit code: {returncode}'
                    return {
                        'success': False,
                        'error': error_msg,
                        'stdout': stdout_text,
                        'stderr': stderr_text,
                        'execution_time': execution_time,
                        'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                    }

            except subprocess.TimeoutExpired:
                # Fallback timeout handler (shouldn't reach here with new code)
                error_msg = f'Code execution timeout after {timeout}s'
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': timeout,
                    'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                }

            finally:
                # Clean up temp file
                try:
                    temp_file.unlink()
                except Exception:
                    pass

        except Exception as e:
            error_msg = f'Execution error: {str(e)}'
            return {
                'success': False,
                'error': error_msg,
                'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
            }

    def _load_config(self) -> Dict[str, Any]:
        """Load loop configuration from config/ravl.yml if it exists"""
        config_file = self.loop_dir / 'config' / 'ravl.yml'
        if not config_file.exists():
            return {}

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _clean_markdown_fences(self, code: str) -> str:
        """
        Remove code block delimiters if present.

        Handles both custom delimiters (===RAVL_CODE_START/END===) and
        markdown code blocks (```python / ```).
        """
        # First try custom delimiters (preferred)
        if '===RAVL_CODE_START===' in code and '===RAVL_CODE_END===' in code:
            start_marker = '===RAVL_CODE_START==='
            end_marker = '===RAVL_CODE_END==='
            start_idx = code.find(start_marker) + len(start_marker)
            end_idx = code.find(end_marker)
            return code[start_idx:end_idx].strip()

        # Fallback: Remove markdown code block fences
        # Remove ```python or ```bash or similar
        code = re.sub(r'^```[\w]*\n', '', code)
        # Remove trailing ```
        code = re.sub(r'\n```$', '', code)
        return code.strip()
