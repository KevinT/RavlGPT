"""
Learning system for RAVL loops

Manages the Learn phase with separate execution and domain learning:
- ExecutionLearningManager: Solution space (HOW infrastructure works)
- LoopLearningManager: Problem space (WHAT loop learns about domain)
- Factory function to create both managers with proper separation
"""

from .learning_manager import create_learning_managers
from .execution_learning_manager import ExecutionLearningManager
from .loop_learning_manager import LoopLearningManager

__all__ = ['create_learning_managers', 'ExecutionLearningManager', 'LoopLearningManager']
