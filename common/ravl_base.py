#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Base RAVL Loop Class

Core RAVL framework functionality:
- Model persistence (load/save with timestamps)
- Cross-loop communication (read sibling/parent models)
- Model history tracking

Project-specific functionality has been extracted to mixins.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from utils.file_utils import load_yaml_file, save_yaml_file, find_timestamped_files
from utils.constants import VERSION_INCREMENT, MODEL_PATTERN
from utils.logging_utils import log_execution
from core.learning.learning_access_helper import LearningAccessHelper


class BaseRAVLLoop:
    """
    Base class for RAVL loops with core framework functionality

    Provides:
    - Model persistence with timestamp tracking
    - Cross-loop communication (read-anywhere pattern)
    - Model history queries

    Child classes should:
    - Override RAVL protocol methods (reflect, act, verify, learn)
    - Inherit from mixins for additional functionality
    """

    def __init__(self, model_path: Path, loop_name: str, learning_path: Optional[Path] = None, loop_dir: Optional[Path] = None):
        """
        Initialize base RAVL loop

        Args:
            model_path: Path to model.yml file (relative to learning_path)
            loop_name: Name of the loop (for logging)
            learning_path: Optional override for learning directory. If provided, model_path is resolved relative to this path
            loop_dir: Optional path to loop directory (where config/ravl.yml lives). Required for cross-loop learning access
        """
        # If learning_path is provided, resolve model_path relative to it
        if learning_path is not None:
            self.learning_path = Path(learning_path)
            self.model_path = self.learning_path / model_path.name if isinstance(model_path, Path) else self.learning_path / model_path
        else:
            self.learning_path = Path(model_path).parent
            self.model_path = Path(model_path)

        self.loop_name = loop_name
        self.loop_dir = Path(loop_dir) if loop_dir else None
        self._learning_access_helper = None  # Lazy-initialized

    # ==================== MODEL PERSISTENCE ====================

    def load_model_with_timestamp(self, default_model_factory: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load the learned intelligence model from latest timestamped file

        Args:
            default_model_factory: Function that returns default model structure

        Returns:
            Loaded model or default model if none exists
        """
        model_dir = self.model_path.parent

        # Find all timestamped model files
        model_files = find_timestamped_files(model_dir, MODEL_PATTERN, reverse=True)
        if model_files:
            # Load the most recent timestamped model
            latest_model = model_files[0]
            log_execution(f"{self.loop_name}: Loading model from {latest_model.name}", status='info')
            return load_yaml_file(latest_model)

        # Fall back to non-timestamped model.yml if it exists
        model_data = load_yaml_file(self.model_path)
        if model_data is not None:
            log_execution(f"{self.loop_name}: Loading model from model.yml", status='info')
            return model_data

        # Return default model if no existing model found
        log_execution(f"{self.loop_name}: No existing model found, initializing new model", status='info')
        return default_model_factory()

    def _models_differ(self, model1: Dict[str, Any], model2: Dict[str, Any]) -> bool:
        """
        Compare two models, ignoring timestamp fields

        Args:
            model1: First model to compare
            model2: Second model to compare

        Returns:
            True if models differ (excluding timestamps), False otherwise
        """
        import copy

        # Fields to ignore when comparing (timestamps and version metadata)
        ignore_fields = {'last_updated', 'created_at', 'timestamp', 'version', 'last_learned'}

        def remove_timestamps(obj, parent_key=''):
            """Recursively remove timestamp fields from nested dict"""
            if isinstance(obj, dict):
                return {
                    k: remove_timestamps(v, k)
                    for k, v in obj.items()
                    if k not in ignore_fields
                }
            elif isinstance(obj, list):
                return [remove_timestamps(item, parent_key) for item in obj]
            else:
                return obj

        # Create copies without timestamps
        clean_model1 = remove_timestamps(copy.deepcopy(model1))
        clean_model2 = remove_timestamps(copy.deepcopy(model2))

        # Compare the cleaned models
        return clean_model1 != clean_model2

    def save_model_with_timestamp(self, model: Dict[str, Any]):
        """
        Save the learned intelligence model with timestamp
        Only creates new timestamped file if model has actually changed

        Args:
            model: Model to save
        """
        # Load existing model if it exists
        existing_model = load_yaml_file(self.model_path)

        # Check if model has actually changed (excluding version/timestamps)
        model_changed = existing_model is None or self._models_differ(existing_model, model)

        if model_changed:
            # Increment version only when model actually changed
            if existing_model and 'version' in model:
                try:
                    current_version = float(existing_model.get('version', '1.0'))
                    model['version'] = f"{current_version + VERSION_INCREMENT:.1f}"
                except (ValueError, TypeError):
                    # If version parsing fails, just keep the existing version
                    pass

            # Generate timestamped filename
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M%S')
            timestamped_path = self.model_path.parent / f'model-{timestamp}.yml'

            # Save to timestamped file
            save_yaml_file(timestamped_path, model, create_dirs=True)

            log_execution(f"Model changed - saved to {timestamped_path.name}", status='success')
        else:
            log_execution("Model unchanged - skipping timestamped save", status='info')

        # Always update model.yml with latest timestamps
        save_yaml_file(self.model_path, model, create_dirs=True)

    def get_model_history(self, metrics_extractor: Optional[Callable[[Dict], Dict]] = None) -> List[Dict[str, Any]]:
        """
        Get historical model versions for meta-reflection

        Args:
            metrics_extractor: Optional function to extract specific metrics from model

        Returns:
            List of dicts with timestamp, filename, and extracted metrics
        """
        model_dir = self.model_path.parent
        history = []

        if not model_dir.exists():
            return history

        # Find all timestamped model files
        model_files = sorted(model_dir.glob('model-*.yml'))

        for model_file in model_files:
            try:
                # Extract timestamp from filename (model-YYYY-MM-DD-HHMMSS.yml)
                timestamp_str = model_file.stem.replace('model-', '')

                # Load the model to get metrics
                with open(model_file, 'r') as f:
                    historical_model = yaml.safe_load(f)

                history_entry = {
                    'timestamp': timestamp_str,
                    'filename': model_file.name,
                }

                # Add custom metrics if extractor provided
                if metrics_extractor:
                    history_entry.update(metrics_extractor(historical_model))

                history.append(history_entry)

            except Exception as e:
                log_execution(f"Could not load historical model {model_file.name}: {e}", status='error')
                continue

        return history

    # ==================== CROSS-LOOP COMMUNICATION ====================

    @property
    def learning_access_helper(self) -> Optional[LearningAccessHelper]:
        """
        Get learning access helper (lazy-initialized)

        Returns:
            LearningAccessHelper instance or None if loop_dir not provided
        """
        if self._learning_access_helper is None and self.loop_dir is not None:
            self._learning_access_helper = LearningAccessHelper(
                self.loop_dir,
                self.learning_path,
                debug=False  # Set to True for verbose path resolution logging
            )
        return self._learning_access_helper

    def read_sibling_model(self, sibling_name: str) -> Optional[Dict[str, Any]]:
        """
        Read a sibling loop's model (read-only)

        Implements "read-anywhere" part of "read-anywhere, write-own" pattern.

        Uses LearningAccessHelper for proper path resolution with configurable learning paths.
        Falls back to legacy hardcoded navigation if loop_dir not provided.

        Args:
            sibling_name: Name of sibling loop directory

        Returns:
            Sibling's model or None if not found
        """
        # Use helper if available (proper path resolution)
        if self.learning_access_helper:
            log_execution(f"{self.loop_name}: Reading sibling model: {sibling_name}", status='debug')
            model = self.learning_access_helper.read_sibling_model(sibling_name)
            if model is None:
                log_execution(f"{self.loop_name}: Sibling model not found: {sibling_name}", status='warning')
            return model

        # Legacy fallback (hardcoded parent.parent navigation)
        # DEPRECATED: This doesn't respect configurable learning paths
        log_execution(
            f"{self.loop_name}: Using legacy sibling path resolution (loop_dir not provided). "
            "This may fail with configurable learning paths.",
            status='warning'
        )
        sibling_model_path = self.model_path.parent.parent / sibling_name / 'learnings' / 'model.yml'
        return load_yaml_file(sibling_model_path)

    def read_parent_model(self) -> Optional[Dict[str, Any]]:
        """
        Read parent loop's model (read-only)

        Implements "read-anywhere" part of "read-anywhere, write-own" pattern.

        Uses LearningAccessHelper for proper path resolution with configurable learning paths.
        Falls back to legacy hardcoded navigation if loop_dir not provided.

        Returns:
            Parent's model or None if not found
        """
        # Use helper if available (proper path resolution)
        if self.learning_access_helper:
            log_execution(f"{self.loop_name}: Reading parent model", status='debug')
            model = self.learning_access_helper.read_parent_model()
            if model is None:
                log_execution(f"{self.loop_name}: Parent model not found", status='warning')
            return model

        # Legacy fallback (hardcoded parent.parent.parent navigation)
        # DEPRECATED: This doesn't respect configurable learning paths
        log_execution(
            f"{self.loop_name}: Using legacy parent path resolution (loop_dir not provided). "
            "This may fail with configurable learning paths.",
            status='warning'
        )
        parent_model_path = self.model_path.parent.parent.parent / 'learnings' / 'model.yml'
        return load_yaml_file(parent_model_path)

    # ==================== EXECUTION METADATA ====================

    def initialize_execution_learning(self):
        """
        Initialize execution_learning directory structure.

        Creates:
        - execution_learning/
        - execution_learning/history/
        - execution_learning/current_state/

        Call this during loop initialization to ensure directories exist.
        """
        exec_learning_dir = self.learning_path / 'execution_learning'
        exec_learning_dir.mkdir(parents=True, exist_ok=True)

        history_dir = exec_learning_dir / 'history'
        history_dir.mkdir(exist_ok=True)

        current_state_dir = exec_learning_dir / 'current_state'
        current_state_dir.mkdir(exist_ok=True)

    def write_execution_metadata(self, metadata: Dict[str, Any]):
        """
        Write execution metadata to execution_learning/.

        Writes to:
        - execution_learning/latest_run.json (current run)
        - execution_learning/history/runs.jsonl (appends to history)
        - execution_learning/current_state/execution_metadata.json (aggregated stats)

        Args:
            metadata: Dictionary containing execution metadata (timestamps, errors, performance, etc.)
        """
        import json

        exec_learning_dir = self.learning_path / 'execution_learning'

        # Ensure directories exist
        self.initialize_execution_learning()

        # Write latest run
        latest_run_file = exec_learning_dir / 'latest_run.json'
        with open(latest_run_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, default=str)

        # Append to history
        history_file = exec_learning_dir / 'history' / 'runs.jsonl'
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(metadata, default=str) + '\n')

        # Update aggregated metadata
        self._update_aggregated_execution_metadata(metadata)

    def _update_aggregated_execution_metadata(self, latest_metadata: Dict[str, Any]):
        """
        Update aggregated execution metadata with exponential moving average.

        Args:
            latest_metadata: Latest execution metadata
        """
        import json

        exec_learning_dir = self.learning_path / 'execution_learning'
        current_state_file = exec_learning_dir / 'current_state' / 'execution_metadata.json'

        # Load existing aggregated metadata
        if current_state_file.exists():
            with open(current_state_file, 'r', encoding='utf-8') as f:
                aggregated = json.load(f)
        else:
            aggregated = {
                'total_runs': 0,
                'successful_runs': 0,
                'failed_runs': 0,
                'average_duration_seconds': 0.0,
                'last_updated': None
            }

        # Update counts
        aggregated['total_runs'] += 1
        if latest_metadata.get('success', False):
            aggregated['successful_runs'] += 1
        else:
            aggregated['failed_runs'] += 1

        # Update average duration (exponential moving average: 70% history, 30% current)
        if 'duration_seconds' in latest_metadata:
            if aggregated['average_duration_seconds'] == 0:
                aggregated['average_duration_seconds'] = latest_metadata['duration_seconds']
            else:
                aggregated['average_duration_seconds'] = (
                    0.7 * aggregated['average_duration_seconds'] +
                    0.3 * latest_metadata['duration_seconds']
                )

        aggregated['last_updated'] = latest_metadata.get('timestamp', datetime.now(timezone.utc).isoformat())

        # Write updated aggregated metadata
        with open(current_state_file, 'w', encoding='utf-8') as f:
            json.dump(aggregated, f, indent=2, default=str)
