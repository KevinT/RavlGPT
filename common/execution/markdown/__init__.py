"""
Markdown-based RAVL Loop Execution

Provides framework for interpreting and executing RAVL loops defined in markdown format.

Components:
- MarkdownParser: Parses markdown RAVL loop definitions
- MarkdownRAVLExecutor: Main executor for markdown loops
- LoopContextBuilder: Builds execution context
- ChildLoopExecutor: Handles child loop coordination
"""

import sys
from pathlib import Path

# Add current directory and common directory to path for imports
_script_dir = Path(__file__).parent
_common_dir = _script_dir.parent.parent
sys.path.insert(0, str(_script_dir))
sys.path.insert(0, str(_common_dir))

from markdown_parser import MarkdownParser
from markdown_ravl_executor import MarkdownRAVLExecutor
from loop_context_builder import LoopContextBuilder
from child_loop_executor import ChildLoopExecutor

__all__ = [
    'MarkdownParser',
    'MarkdownRAVLExecutor',
    'LoopContextBuilder',
    'ChildLoopExecutor',
]
