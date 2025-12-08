#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Loop Lock Manager

Manages locking and unlocking of RAVL loops to specific verified code.
When a loop is locked, it bypasses the full RAVL cycle and executes the locked code directly.

Security: Locked code paths must be within the loop's learnings directory.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Add parent directories to path
_current_dir = Path(__file__).parent
sys.path.insert(0, str(_current_dir.parent))
sys.path.insert(0, str(_current_dir.parent / 'utils'))

from utils.file_utils import load_toml_file
from utils.logging_utils import log_message


class LoopLockManager:
    """
    Manages loop locking and unlocking

    Responsibilities:
    - Lock loops to specific verified code
    - Unlock loops to resume normal RAVL execution
    - Validate locked code paths (security)
    - Execute locked code
    """

    def __init__(self, loop_dir: Path, learnings_dir: Path, config: Dict[str, Any]):
        """
        Initialize lock manager

        Args:
            loop_dir: Path to loop directory
            learnings_dir: Path to learnings directory
            config: Loop configuration dict
        """
        self.loop_dir = loop_dir
        self.learnings_dir = learnings_dir
        self.config = config
        self.config_file = loop_dir / 'config' / 'ravl.toml'

    def lock_loop(self, attempt: Optional[int] = None, force: bool = False) -> Tuple[bool, str]:
        """
        Lock loop to specific verified code

        Args:
            attempt: Specific attempt number to lock (None = most recent)
            force: Force lock even if verification failed

        Returns:
            (success, message/error)
        """
        # Determine which attempt to lock to
        if attempt is None:
            # Lock to most recent attempt (whatever it is)
            code_path, attempt_num, passed = self._get_most_recent_attempt()
            if code_path is None:
                return (False, "No execution attempts found")
        else:
            # Lock to specific attempt
            code_path, attempt_num, passed = self._get_specific_attempt(attempt)
            if code_path is None:
                return (False, f"Attempt {attempt} not found")

        # Check if attempt passed verification
        if not passed and not force:
            return (False,
                    f"Attempt {attempt_num} did not pass verification.\n"
                    f"  Use --force to lock anyway, or run the loop until it succeeds.")

        message = f"attempt {attempt_num} ({'passed verification' if passed else 'failed verification'})"

        if code_path is None:
            return (False, message)

        # Validate path is within learnings directory (SECURITY)
        valid, error_msg = self._validate_locked_path(code_path)
        if not valid:
            return (False, error_msg)

        # Convert to relative path from loop_dir for storage
        try:
            # Try to make relative from loop_dir
            relative_path = code_path.relative_to(self.loop_dir)
            lock_path_str = f"./{relative_path}"
        except ValueError:
            # If not relative to loop_dir, store as absolute
            lock_path_str = str(code_path)

        # Update config
        try:
            import tomli_w

            # Read current config
            if self.config_file.exists():
                with open(self.config_file, 'rb') as f:
                    try:
                        import tomllib
                    except ImportError:
                        import tomli as tomllib
                    config_data = tomllib.load(f) or {}
            else:
                config_data = {}

            # Add lock field
            config_data['loop_locked'] = lock_path_str

            # Write back
            with open(self.config_file, 'wb') as f:
                tomli_w.dump(config_data, f)

            return (True, f"Loop locked to {message}\n  Path: {lock_path_str}\n  See config/ravl.toml for details")

        except Exception as e:
            return (False, f"Failed to update config: {str(e)}")

    def unlock_loop(self) -> Tuple[bool, str]:
        """
        Unlock loop to resume normal RAVL execution

        Returns:
            (success, message)
        """
        # Check if locked
        if 'loop_locked' not in self.config:
            return (True, "Loop is not locked (already unlocked)")

        # Update config
        try:
            import tomli_w

            # Read current config
            if self.config_file.exists():
                with open(self.config_file, 'rb') as f:
                    try:
                        import tomllib
                    except ImportError:
                        import tomli as tomllib
                    config_data = tomllib.load(f) or {}
            else:
                return (False, "Config file not found")

            # Remove lock field
            if 'loop_locked' in config_data:
                del config_data['loop_locked']

            # Write back
            with open(self.config_file, 'wb') as f:
                tomli_w.dump(config_data, f)

            return (True, "Loop unlocked (normal RAVL execution will resume)")

        except Exception as e:
            return (False, f"Failed to update config: {str(e)}")

    def is_locked(self) -> Tuple[bool, Optional[Path]]:
        """
        Check if loop is locked

        Returns:
            (locked, code_path)
        """
        if 'loop_locked' not in self.config:
            return (False, None)

        lock_path_str = self.config['loop_locked']

        # Resolve path (handle relative paths from loop_dir)
        if lock_path_str.startswith('./'):
            code_path = (self.loop_dir / lock_path_str[2:]).resolve()
        else:
            code_path = Path(lock_path_str).resolve()

        # Validate path is within learnings directory (SECURITY)
        valid, error_msg = self._validate_locked_path(code_path)
        if not valid:
            log_message(error_msg, status='error')
            return (False, None)

        # Check if file exists
        if not code_path.exists():
            log_message(
                f"Locked code file not found: {code_path}\n"
                f"  Run 'ravl --unlock {self.loop_dir.name}' to unlock",
                status='error'
            )
            return (False, None)

        return (True, code_path)

    def execute_locked_code(self, venv_path: Path) -> Dict[str, Any]:
        """
        Execute locked code in venv

        Args:
            venv_path: Path to virtual environment

        Returns:
            Execution result dict
        """
        is_locked, code_path = self.is_locked()
        if not is_locked or code_path is None:
            return {
                'success': False,
                'error': 'Loop is not locked or locked code is invalid'
            }

        # Final security validation before execution
        valid, error_msg = self._validate_locked_path(code_path)
        if not valid:
            return {
                'success': False,
                'error': error_msg
            }

        # Execute code
        try:
            from execution.code.simple_code_executor import SimpleCodeExecutor

            executor = SimpleCodeExecutor(
                venv_path=venv_path,
                execution_timeout=300  # 5 minutes default
            )

            with open(code_path, 'r') as f:
                code = f.read()

            result = executor.execute(code)

            return {
                'success': result.get('success', False),
                'output': result.get('output', ''),
                'error': result.get('error', ''),
                'execution_time': result.get('execution_time', 0)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to execute locked code: {str(e)}"
            }

    def get_lockable_attempts(self) -> List[Dict[str, Any]]:
        """
        Get list of lockable attempts (successful executions)

        Returns:
            List of dicts with attempt info: [{"attempt": 1, "timestamp": "...", "passed": true}]
        """
        attempts = []
        recent_attempts_dir = self.learnings_dir / 'execution_learning' / 'recent_attempts'

        if not recent_attempts_dir.exists():
            return attempts

        # Scan for attempt directories
        for attempt_dir in sorted(recent_attempts_dir.iterdir()):
            if not attempt_dir.is_dir() or not attempt_dir.name.startswith('attempt_'):
                continue

            try:
                attempt_num = int(attempt_dir.name.replace('attempt_', ''))
                result_file = attempt_dir / 'execution_result.json'

                if not result_file.exists():
                    continue

                with open(result_file, 'r') as f:
                    result = json.load(f)

                passed = result.get('passed', False)
                timestamp = result.get('timestamp', 'unknown')

                attempts.append({
                    'attempt': attempt_num,
                    'timestamp': timestamp,
                    'passed': passed,
                    'code_path': attempt_dir / 'generated_code.py'
                })

            except (ValueError, json.JSONDecodeError):
                continue

        return attempts

    def validate_attempt(self, attempt_num: int, force: bool = False) -> Tuple[bool, str]:
        """
        Validate that an attempt exists and passed verification

        Args:
            attempt_num: Attempt number to validate
            force: Skip verification pass check

        Returns:
            (valid, error_message)
        """
        attempt_dir = self.learnings_dir / 'execution_learning' / 'recent_attempts' / f'attempt_{attempt_num}'

        if not attempt_dir.exists():
            return (False, f"Attempt {attempt_num} not found")

        result_file = attempt_dir / 'execution_result.json'
        if not result_file.exists():
            return (False, f"Attempt {attempt_num} has no execution result")

        code_file = attempt_dir / 'generated_code.py'
        if not code_file.exists():
            return (False, f"Attempt {attempt_num} has no generated code")

        # Check if verification passed (unless force)
        if not force:
            try:
                with open(result_file, 'r') as f:
                    result = json.load(f)

                passed = result.get('passed', False)
                if not passed:
                    return (False,
                            f"Attempt {attempt_num} did not pass verification.\n"
                            f"  Use --force to lock anyway (not recommended).")

            except (json.JSONDecodeError, KeyError) as e:
                return (False, f"Failed to read verification status: {str(e)}")

        return (True, "")

    def _get_most_recent_attempt(self) -> Tuple[Optional[Path], Optional[int], bool]:
        """
        Get the most recent execution attempt (regardless of success)

        Returns:
            (code_path, attempt_num, passed)
        """
        attempts = self.get_lockable_attempts()

        if not attempts:
            return (None, None, False)

        # Get most recent (highest attempt number)
        most_recent = max(attempts, key=lambda a: a['attempt'])

        return (most_recent['code_path'], most_recent['attempt'], most_recent['passed'])

    def _get_specific_attempt(self, attempt_num: int) -> Tuple[Optional[Path], Optional[int], bool]:
        """
        Get code path for specific attempt

        Args:
            attempt_num: Attempt number

        Returns:
            (code_path, attempt_num, passed)
        """
        attempts = self.get_lockable_attempts()

        # Find the specific attempt
        for attempt in attempts:
            if attempt['attempt'] == attempt_num:
                return (attempt['code_path'], attempt['attempt'], attempt['passed'])

        # Attempt not found
        return (None, None, False)

    def _validate_locked_path(self, locked_path: Path) -> Tuple[bool, str]:
        """
        Validate that locked code path is within the loop's learnings directory

        SECURITY: Prevents users from manually editing ravl.toml to point to
        arbitrary code elsewhere on the filesystem.

        Args:
            locked_path: Path to validate

        Returns:
            (valid, error_message)
        """
        # Resolve both paths to absolute, normalized paths
        try:
            resolved_code = locked_path.resolve()
            resolved_learnings = self.learnings_dir.resolve()

            # Check if code path is within learnings directory
            resolved_code.relative_to(resolved_learnings)
            return (True, "")

        except ValueError:
            return (False,
                    f"SECURITY ERROR: Locked code must be within loop learnings directory.\n"
                    f"  Locked path: {resolved_code}\n"
                    f"  Learnings dir: {resolved_learnings}\n"
                    f"  The locked path is outside the learnings directory tree.\n"
                    f"  This prevents execution of arbitrary code for security reasons.")
        except Exception as e:
            return (False, f"Failed to validate path: {str(e)}")
