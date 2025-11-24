#!/usr/bin/env python3
"""
Execution Learning Manager for RAVL Loops

Manages learning about code execution - HOW to make the RAVL infrastructure work.
This is separate from loop_learning which tracks WHAT the loop learns about its domain.

Organization:
  learnings/execution_learning/
  ├── current_state/           # Latest execution state
  │   ├── generated_code.py
  │   ├── ravl_loop_enhanced.md
  │   ├── latest_dsl.json
  │   └── execution_result.json
  ├── recent_attempts/         # Last 3 execution attempts
  │   ├── attempt_1/
  │   │   ├── generated_code.py
  │   │   ├── execution_result.json
  │   │   ├── dsl_used.json
  │   │   └── spec_hash.txt
  │   ├── attempt_2/
  │   └── attempt_3/
  ├── history/                 # Aggregated execution history
  │   ├── execution_failures.jsonl
  │   ├── execution_warnings.jsonl
  │   ├── dsl_iterations.jsonl
  │   └── code_strategies.jsonl
  ├── verified_code.py         # Cached working code
  ├── verified_dsl.json        # DSL that generated working code
  └── metrics.yml              # Execution metrics
"""

import json
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class ExecutionLearningManager:
    """Manages learning about code execution and generation"""

    # Default: 0 = keep all attempts indefinitely
    DEFAULT_RECENT_ATTEMPTS_RETENTION = 0

    def __init__(self, execution_learning_dir: Path, config: Optional[Dict[str, Any]] = None):
        """
        Initialize execution learning manager

        Args:
            execution_learning_dir: Path to execution_learning/ directory
            config: Optional loop config dict with 'recent_attempts_retention' setting
        """
        self.learning_dir = execution_learning_dir

        # Get retention setting from config or use default (0 = unlimited)
        self.recent_attempts_retention = 0
        if config and 'recent_attempts_retention' in config:
            self.recent_attempts_retention = config['recent_attempts_retention']
        else:
            self.recent_attempts_retention = self.DEFAULT_RECENT_ATTEMPTS_RETENTION

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create required subdirectories"""
        for subdir in ['current_state', 'recent_attempts', 'history']:
            (self.learning_dir / subdir).mkdir(parents=True, exist_ok=True)

    def save_execution_attempt(
        self,
        execution_result: Dict[str, Any],
        generated_code: Optional[str] = None,
        dsl: Optional[Dict[str, Any]] = None,
        spec_hash: Optional[str] = None
    ) -> int:
        """
        Save an execution attempt

        Args:
            execution_result: Result of code execution (success, errors, etc.)
            generated_code: Generated Python code
            dsl: DSL used to generate the code
            spec_hash: Hash of spec files for change detection

        Returns:
            Attempt number for this execution
        """
        # Save to current_state/
        self._save_current_execution_state(execution_result, generated_code, dsl)

        # Manage retention of recent attempts
        self._manage_recent_attempts()

        # Save to recent_attempts/
        attempt_num = self._save_recent_execution_attempt(execution_result, generated_code, dsl, spec_hash)

        # Aggregate into history
        self._aggregate_execution_history(execution_result, dsl)

        return attempt_num

    def _save_current_execution_state(
        self,
        execution_result: Dict[str, Any],
        generated_code: Optional[str],
        dsl: Optional[Dict[str, Any]]
    ) -> None:
        """Save latest execution state for quick reference"""
        current_dir = self.learning_dir / 'current_state'

        # Save execution result
        result_file = current_dir / 'execution_result.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'execution': execution_result
                },
                f,
                indent=2
            )

        # Save generated code
        if generated_code:
            code_file = current_dir / 'generated_code.py'
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(generated_code)

        # Save DSL
        if dsl:
            dsl_file = current_dir / 'latest_dsl.json'
            with open(dsl_file, 'w', encoding='utf-8') as f:
                json.dump(dsl, f, indent=2)

    def _manage_recent_attempts(self) -> None:
        """
        Manage recent attempts numbering.
        Keep only recent_attempts_retention of them (0 = unlimited).
        """
        # Skip pruning if retention is 0 (unlimited)
        if self.recent_attempts_retention == 0:
            return

        recent_dir = self.learning_dir / 'recent_attempts'
        existing_attempts = self._get_recent_attempts_numbers()

        if len(existing_attempts) >= self.recent_attempts_retention:
            # Remove oldest attempt
            oldest = min(existing_attempts)
            oldest_folder = recent_dir / f'attempt_{oldest}'
            if oldest_folder.exists():
                import shutil
                shutil.rmtree(oldest_folder)

            # Renumber remaining attempts
            remaining = sorted([n for n in existing_attempts if n != oldest])
            for old_num, new_num in zip(remaining, range(1, len(remaining) + 1)):
                if old_num != new_num:
                    self._rename_attempt(old_num, new_num)

    def _get_recent_attempts_numbers(self) -> List[int]:
        """Get list of attempt numbers in recent_attempts/"""
        recent_dir = self.learning_dir / 'recent_attempts'
        if not recent_dir.exists():
            return []

        attempts = set()
        for folder in recent_dir.iterdir():
            if folder.is_dir() and folder.name.startswith('attempt_'):
                try:
                    num = int(folder.name.split('_')[1])
                    attempts.add(num)
                except (ValueError, IndexError):
                    continue

        return sorted(list(attempts))

    def _rename_attempt(self, old_num: int, new_num: int) -> None:
        """Rename attempt folder"""
        recent_dir = self.learning_dir / 'recent_attempts'
        old_folder = recent_dir / f'attempt_{old_num}'
        new_folder = recent_dir / f'attempt_{new_num}'
        if old_folder.exists():
            old_folder.rename(new_folder)

    def _save_recent_execution_attempt(
        self,
        execution_result: Dict[str, Any],
        generated_code: Optional[str],
        dsl: Optional[Dict[str, Any]],
        spec_hash: Optional[str]
    ) -> int:
        """
        Save attempt to recent_attempts/attempt_N/ folder

        Returns:
            Attempt number
        """
        recent_dir = self.learning_dir / 'recent_attempts'
        existing = self._get_recent_attempts_numbers()
        next_num = (max(existing) + 1) if existing else 1

        # Create attempt folder
        attempt_folder = recent_dir / f'attempt_{next_num}'
        attempt_folder.mkdir(parents=True, exist_ok=True)

        # Save execution result
        result_file = attempt_folder / 'execution_result.json'
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(execution_result, f, indent=2)

        # Save generated code
        if generated_code:
            code_file = attempt_folder / 'generated_code.py'
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(generated_code)

        # Save DSL
        if dsl:
            dsl_file = attempt_folder / 'dsl_used.json'
            with open(dsl_file, 'w', encoding='utf-8') as f:
                json.dump(dsl, f, indent=2)

        # Save spec hash
        if spec_hash:
            hash_file = attempt_folder / 'spec_hash.txt'
            with open(hash_file, 'w', encoding='utf-8') as f:
                f.write(spec_hash)

        return next_num

    def _aggregate_execution_history(
        self,
        execution_result: Dict[str, Any],
        dsl: Optional[Dict[str, Any]]
    ) -> None:
        """Add execution attempt to aggregated history"""
        # Update execution failures if failed
        if not execution_result.get('success', True):
            self._update_execution_failures(execution_result)

        # Save warnings if present (warnings are pre-extracted by verify phase)
        if execution_result.get('has_warnings', False):
            warnings = execution_result.get('warnings', [])
            if warnings:
                self._save_execution_warnings(warnings)

        # Update DSL iterations
        if dsl:
            self._update_dsl_iterations(dsl)

        # Update code strategies if succeeded
        if execution_result.get('success', True):
            self._update_code_strategies(execution_result, dsl)

    def _update_execution_failures(self, execution_result: Dict[str, Any]) -> None:
        """Log execution failures for learning"""
        failures_file = self.learning_dir / 'history' / 'execution_failures.jsonl'

        failure_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error_type': execution_result.get('error_type'),
            'error_message': execution_result.get('error_message'),
            'exit_code': execution_result.get('exit_code'),
            'stderr': execution_result.get('stderr', '')[:500],  # Truncate
        }

        with open(failures_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(failure_entry) + '\n')

    def _update_dsl_iterations(self, dsl: Dict[str, Any]) -> None:
        """Log DSL iterations for tracking evolution"""
        dsl_file = self.learning_dir / 'history' / 'dsl_iterations.jsonl'

        dsl_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'dsl': dsl
        }

        with open(dsl_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(dsl_entry) + '\n')

    def _update_code_strategies(
        self,
        execution_result: Dict[str, Any],
        dsl: Optional[Dict[str, Any]]
    ) -> None:
        """Log successful code strategies"""
        strategies_file = self.learning_dir / 'history' / 'code_strategies.jsonl'

        strategy_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'dsl_summary': {
                'transformation_strategy': dsl.get('transformation_strategy') if dsl else None,
                'data_structure': dsl.get('data_structure') if dsl else None,
            },
            'execution_time': execution_result.get('execution_time'),
        }

        with open(strategies_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(strategy_entry) + '\n')

    def _extract_execution_warnings(self, stderr: str) -> List[Dict[str, Any]]:
        """
        Extract warnings from stderr (deprecations, future warnings, etc.)

        Args:
            stderr: Standard error output from code execution

        Returns:
            List of warning dictionaries with type, message, and api fields
        """
        warnings = []
        if not stderr:
            return warnings

        import re

        # Extract DeprecationWarnings
        deprecation_pattern = r'DeprecationWarning: (.+?) is deprecated'
        for match in re.finditer(deprecation_pattern, stderr):
            warnings.append({
                'type': 'deprecation',
                'message': match.group(0),
                'api': match.group(1).strip()
            })

        # Extract FutureWarnings
        future_pattern = r'FutureWarning: (.+?)(?:\n|$)'
        for match in re.finditer(future_pattern, stderr):
            warnings.append({
                'type': 'future',
                'message': match.group(0).strip()
            })

        return warnings

    def _save_execution_warnings(self, warnings: List[Dict[str, Any]]) -> None:
        """
        Save execution warnings to history for learning

        Args:
            warnings: List of warning dictionaries from _extract_execution_warnings()
        """
        if not warnings:
            return

        warnings_file = self.learning_dir / 'history' / 'execution_warnings.jsonl'

        for warning in warnings:
            warning_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'type': warning.get('type'),
                'message': warning.get('message'),
                'api': warning.get('api')  # May be None for non-deprecation warnings
            }

            with open(warnings_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(warning_entry) + '\n')

    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent execution failures for context

        Args:
            limit: Maximum number of recent failures to return

        Returns:
            List of recent execution failures
        """
        failures_file = self.learning_dir / 'history' / 'execution_failures.jsonl'
        if not failures_file.exists():
            return []

        failures = []
        with open(failures_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    failures.append(json.loads(line))

        return failures[-limit:]

    def get_warning_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent execution warnings for learning

        Args:
            limit: Maximum number of recent warnings to return

        Returns:
            List of recent execution warnings
        """
        warnings_file = self.learning_dir / 'history' / 'execution_warnings.jsonl'
        if not warnings_file.exists():
            return []

        warnings = []
        with open(warnings_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    warnings.append(json.loads(line))

        return warnings[-limit:]

    def get_recent_attempts(self) -> List[Dict[str, Any]]:
        """Get data from recent execution attempts"""
        recent_dir = self.learning_dir / 'recent_attempts'
        if not recent_dir.exists():
            return []

        attempts = []
        for attempt_num in sorted(self._get_recent_attempts_numbers()):
            attempt_folder = recent_dir / f'attempt_{attempt_num}'
            result_file = attempt_folder / 'execution_result.json'

            if result_file.exists():
                with open(result_file, 'r', encoding='utf-8') as f:
                    attempts.append({
                        'attempt_number': attempt_num,
                        'execution_result': json.load(f)
                    })

        return attempts
