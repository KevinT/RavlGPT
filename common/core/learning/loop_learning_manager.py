#!/usr/bin/env python3
"""
Loop Learning Manager for RAVL Loops

Manages learning about the problem domain - WHAT the loop has learned.
This is separate from execution_learning which tracks HOW to make the infrastructure work.

This is THE "L" IN RAVL - the actual domain learning that the loop performs.

Organization:
  learnings/loop_learning/
  ├── current_state/           # Latest domain state
  │   ├── latest_action.json
  │   ├── latest_verification.json
  │   └── latest_metrics.yml
  ├── recent_attempts/         # Last 3 domain attempts
  │   ├── attempt_1/
  │   │   ├── domain_action.json
  │   │   ├── domain_verification.json
  │   │   └── domain_metrics.yml
  │   ├── attempt_2/
  │   └── attempt_3/
  ├── history/                 # Aggregated domain history
  │   ├── domain_failures.jsonl
  │   ├── domain_successes.jsonl
  │   └── pattern_evolution.jsonl
  ├── model.yml                # Current domain model
  └── model-TIMESTAMP.yml      # Historical domain models
"""

import json
try:
    import tomllib
except ImportError:
    import tomli as tomllib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class LoopLearningManager:
    """Manages learning about the problem domain (THE 'L' IN RAVL)"""

    # Default: 0 = keep all attempts indefinitely
    DEFAULT_RECENT_ATTEMPTS_RETENTION = 0

    def __init__(self, loop_learning_dir: Path, config: Optional[Dict[str, Any]] = None):
        """
        Initialize loop learning manager

        Args:
            loop_learning_dir: Path to loop_learning/ directory
            config: Optional loop config dict with 'recent_attempts_retention' setting
        """
        self.learning_dir = loop_learning_dir

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

    def save_domain_attempt(
        self,
        action_result: Dict[str, Any],
        verification: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> None:
        """
        Save a domain learning attempt

        Args:
            action_result: Result from domain action (what the loop did)
            verification: Domain verification results (did it meet criteria?)
            metrics: Domain metrics (quality, completeness, etc.)
        """
        # Save to current_state/
        self._save_current_domain_state(action_result, verification, metrics)

        # Manage retention of recent attempts
        self._manage_recent_attempts()

        # Save to recent_attempts/
        self._save_recent_domain_attempt(action_result, verification, metrics)

        # Aggregate into history
        self._aggregate_domain_history(action_result, verification, metrics)

    def _save_current_domain_state(
        self,
        action_result: Dict[str, Any],
        verification: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> None:
        """Save latest domain state for quick reference"""
        current_dir = self.learning_dir / 'current_state'

        # Save action result
        action_file = current_dir / 'latest_action.json'
        with open(action_file, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'action': action_result
                },
                f,
                indent=2
            )

        # Save verification
        verification_file = current_dir / 'latest_verification.json'
        with open(verification_file, 'w', encoding='utf-8') as f:
            json.dump(verification, f, indent=2)

        # Save metrics
        metrics_file = current_dir / 'latest_metrics.yml'
        with open(metrics_file, 'w', encoding='utf-8') as f:
            yaml.dump(metrics, f, default_flow_style=False)

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

    def _save_recent_domain_attempt(
        self,
        action_result: Dict[str, Any],
        verification: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> None:
        """Save attempt to recent_attempts/attempt_N/ folder"""
        recent_dir = self.learning_dir / 'recent_attempts'
        existing = self._get_recent_attempts_numbers()
        next_num = (max(existing) + 1) if existing else 1

        # Create attempt folder
        attempt_folder = recent_dir / f'attempt_{next_num}'
        attempt_folder.mkdir(parents=True, exist_ok=True)

        # Save domain action
        action_file = attempt_folder / 'domain_action.json'
        with open(action_file, 'w', encoding='utf-8') as f:
            json.dump(action_result, f, indent=2)

        # Save domain verification
        verification_file = attempt_folder / 'domain_verification.json'
        with open(verification_file, 'w', encoding='utf-8') as f:
            json.dump(verification, f, indent=2)

        # Save domain metrics
        metrics_file = attempt_folder / 'domain_metrics.yml'
        with open(metrics_file, 'w', encoding='utf-8') as f:
            yaml.dump(metrics, f, default_flow_style=False)

    def save_run_insights(self, insights: Dict[str, Any], attempt_number: Optional[int] = None) -> None:
        """
        Save synthesized insights from full RAVL run (REFLECT+ACT+VERIFY)

        These insights are created by LEARN phase after analyzing the entire run,
        and will be read by REFLECT in the next iteration to inform ACT.

        Args:
            insights: Synthesized insights dict from LLM analysis
            attempt_number: Optional attempt number to associate insights with execution attempt
        """
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

        insights_with_metadata = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'insights': insights
        }

        # If attempt number provided, save to execution_learning/recent_attempts/attempt_N/
        # Otherwise fall back to loop_learning/ for backward compatibility
        if attempt_number is not None:
            # Navigate from loop_learning/ to execution_learning/recent_attempts/attempt_N/
            execution_learning_dir = self.learning_dir.parent / 'execution_learning'
            attempt_folder = execution_learning_dir / 'recent_attempts' / f'attempt_{attempt_number}'

            if attempt_folder.exists():
                insights_file = attempt_folder / f'run_insights_{timestamp}.json'
            else:
                # Fallback to loop_learning if attempt folder doesn't exist
                insights_file = self.learning_dir / f'run_insights_{timestamp}.json'
        else:
            # Legacy behavior: save to loop_learning/
            insights_file = self.learning_dir / f'run_insights_{timestamp}.json'

        with open(insights_file, 'w', encoding='utf-8') as f:
            json.dump(insights_with_metadata, f, indent=2)

    def _aggregate_domain_history(
        self,
        action_result: Dict[str, Any],
        verification: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> None:
        """Add domain attempt to aggregated history"""
        # Update domain failures if verification failed
        if not verification.get('overall_passed', True):
            self._update_domain_failures(verification, action_result)

        # Update domain successes if verification passed
        if verification.get('overall_passed', False):
            self._update_domain_successes(verification, action_result)

        # Update pattern evolution
        self._update_pattern_evolution(metrics, verification)

    def _update_domain_failures(
        self,
        verification: Dict[str, Any],
        action_result: Dict[str, Any]
    ) -> None:
        """Log domain failures for learning"""
        failures_file = self.learning_dir / 'history' / 'domain_failures.jsonl'

        failed_criteria = [
            c for c in verification.get('criteria_results', [])
            if not c.get('passed', False)
        ]

        failure_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'failed_criteria': failed_criteria,
            'strategy_used': action_result.get('strategy'),
            'suggestions': verification.get('suggestions', [])
        }

        with open(failures_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(failure_entry) + '\n')

    def _update_domain_successes(
        self,
        verification: Dict[str, Any],
        action_result: Dict[str, Any]
    ) -> None:
        """Log domain successes for reinforcement"""
        successes_file = self.learning_dir / 'history' / 'domain_successes.jsonl'

        success_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'strategy_used': action_result.get('strategy'),
            'passed_criteria': len([
                c for c in verification.get('criteria_results', [])
                if c.get('passed', False)
            ]),
            'total_criteria': len(verification.get('criteria_results', []))
        }

        with open(successes_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(success_entry) + '\n')

    def _update_pattern_evolution(
        self,
        metrics: Dict[str, Any],
        verification: Dict[str, Any]
    ) -> None:
        """Track how domain patterns evolve over time"""
        evolution_file = self.learning_dir / 'history' / 'pattern_evolution.jsonl'

        evolution_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'pass_rate': metrics.get('pass_rate', 0.0),
            'total_passed': metrics.get('total_passed', 0),
            'total_failed': metrics.get('total_failed', 0),
            'quality_score': verification.get('quality_score', 0.0)
        }

        with open(evolution_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(evolution_entry) + '\n')

    def get_domain_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent domain failures for context

        Args:
            limit: Maximum number of recent failures to return

        Returns:
            List of recent domain failures
        """
        failures_file = self.learning_dir / 'history' / 'domain_failures.jsonl'
        if not failures_file.exists():
            return []

        failures = []
        with open(failures_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    failures.append(json.loads(line))

        return failures[-limit:]

    def load_model(self) -> Optional[Dict[str, Any]]:
        """
        Load the current domain model

        Returns:
            Domain model dict or None if not exists
        """
        model_file = self.learning_dir / 'model.yml'
        if not model_file.exists():
            return None

        with open(model_file, 'rb') as f:
            return tomllib.load(f)

    def save_model(self, model: Dict[str, Any]) -> None:
        """
        Save the domain model

        Args:
            model: Domain model to save
        """
        model_file = self.learning_dir / 'model.yml'

        # Save current model
        with open(model_file, 'w', encoding='utf-8') as f:
            yaml.dump(model, f, default_flow_style=False)

        # Save timestamped copy
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        historical_file = self.learning_dir / f'model-{timestamp}.yml'
        with open(historical_file, 'w', encoding='utf-8') as f:
            yaml.dump(model, f, default_flow_style=False)

    def get_model_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get historical domain models

        Args:
            limit: Maximum number of historical models to return

        Returns:
            List of historical models
        """
        model_files = sorted(
            self.learning_dir.glob('model-*.yml'),
            reverse=True
        )[:limit]

        models = []
        for model_file in model_files:
            with open(model_file, 'rb') as f:
                model = tomllib.load(f)
                models.append({
                    'timestamp': model_file.stem.replace('model-', ''),
                    'model': model
                })

        return models
