#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Learning Manager Factory for RAVL Loops

Creates separate learning managers for execution and loop learning.

CRITICAL SEPARATION:
- ExecutionLearningManager: HOW to make the RAVL infrastructure work
- LoopLearningManager: WHAT the loop learns about its domain (THE "L" IN RAVL)

These two learning contexts must never mix.

Directory Structure:
  learnings/
  ├── execution_learning/     # Code generation, execution errors, DSL
  └── loop_learning/          # Domain patterns, model evolution, insights
"""

from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from .execution_learning_manager import ExecutionLearningManager
from .loop_learning_manager import LoopLearningManager


def create_learning_managers(
    learning_path: Path,
    config: Optional[Dict[str, Any]] = None
) -> Tuple[ExecutionLearningManager, LoopLearningManager]:
    """
    Create both learning managers with proper subdirectory separation.

    Args:
        learning_path: Base learning directory (e.g., loop_dir/learnings)
        config: Optional loop config dict with 'recent_attempts_retention' setting

    Returns:
        Tuple of (ExecutionLearningManager, LoopLearningManager)

    The function automatically creates:
    - {learning_path}/execution_learning/
    - {learning_path}/loop_learning/
    """
    # Ensure subdirectories exist
    execution_dir = learning_path / 'execution_learning'
    loop_dir = learning_path / 'loop_learning'

    execution_dir.mkdir(parents=True, exist_ok=True)
    loop_dir.mkdir(parents=True, exist_ok=True)

    # Create managers with config
    execution_mgr = ExecutionLearningManager(execution_dir, config=config)
    loop_mgr = LoopLearningManager(loop_dir, config=config)

    return execution_mgr, loop_mgr
