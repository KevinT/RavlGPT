#!/usr/bin/env python3
"""
Loop Context Builder

Builds context for RAVL loop execution.
Discovers related loops, loads learning history, and builds execution context.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from core.learning.learning_access_helper import LearningAccessHelper


class LoopContextBuilder:
    """
    Builds execution context for RAVL loops

    Responsibilities:
    - Discover parent, child, and sibling loops
    - Load learning artifacts from history
    - Build context summary for prompts
    - Aggregate related loop information
    """

    def __init__(self, loop_dir: Path, learnings_dir: Path):
        """
        Initialize context builder

        Args:
            loop_dir: Path to the loop directory
            learnings_dir: Path to learnings directory
        """
        self.loop_dir = loop_dir
        self.learnings_dir = learnings_dir

    def discover_related_loops(self, exclude_top_level_parents: bool = True) -> Dict[str, List[Path]]:
        """
        Discover parent, child, and sibling loops based on directory structure

        Args:
            exclude_top_level_parents: If True, top-level parents won't see other top-level parents as siblings

        Returns dict with 'parent', 'children', 'siblings' keys
        """
        result = {
            'parent': None,
            'children': [],
            'siblings': []
        }

        # Create helper for top-level detection
        helper = LearningAccessHelper(self.loop_dir, self.learnings_dir)
        is_top_level_parent = helper.is_top_level_parent()

        # Determine loop type based on directory structure
        is_child_loop = self.loop_dir.parent.name in ('ravl_loops', 'child_loops')

        # Find parent
        if is_child_loop:
            parent_dir = self.loop_dir.parent.parent
            if (parent_dir / 'config' / 'ravl.toml').exists():
                result['parent'] = parent_dir

        # Find children
        children_dir = self.loop_dir / 'child_loops'
        if children_dir.exists():
            for child in children_dir.iterdir():
                if child.is_dir() and (child / 'config' / 'ravl.toml').exists():
                    result['children'].append(child)

        # Find siblings
        if is_child_loop:
            siblings_dir = self.loop_dir.parent
            for sibling in siblings_dir.iterdir():
                if (sibling.is_dir() and
                    sibling != self.loop_dir and
                    (sibling / 'config' / 'ravl.toml').exists()):

                    # Check if we should exclude top-level parent siblings
                    if exclude_top_level_parents and is_top_level_parent:
                        # Check if sibling is also a top-level parent
                        sibling_helper = LearningAccessHelper(sibling, sibling / 'learnings')
                        if sibling_helper.is_top_level_parent():
                            # Both are top-level parents - enforce isolation
                            continue

                    result['siblings'].append(sibling)

        return result

    def read_learnings_files(self, learnings_dir: Path) -> Dict[str, Any]:
        """
        Read and aggregate learning artifacts

        Returns dictionary with learning history, metrics, and models
        """
        learnings = {
            'model': None,
            'metrics': {},
            'recent_attempts': [],
            'history': {}
        }

        try:
            # Read current model
            model_file = learnings_dir / 'model.yml'
            if model_file.exists():
                import toml
                with open(model_file, 'r') as f:
                    learnings['model'] = tomllib.load(f)

            # Read metrics from history
            metrics_file = learnings_dir / 'learnings' / 'history' / 'metrics.jsonl'
            if metrics_file.exists():
                try:
                    with open(metrics_file, 'r') as f:
                        for line in f:
                            try:
                                entry = json.loads(line)
                                timestamp = entry.get('timestamp', 'unknown')
                                learnings['metrics'][timestamp] = entry
                            except json.JSONDecodeError:
                                continue
                except IOError:
                    pass

            # Read recent attempts
            recent_file = learnings_dir / 'learnings' / 'history' / 'recent_attempts.json'
            if recent_file.exists():
                try:
                    with open(recent_file, 'r') as f:
                        data = json.load(f)
                        learnings['recent_attempts'] = data.get('recent_attempts', [])
                except (IOError, json.JSONDecodeError):
                    pass

            # Read history summary
            history_file = learnings_dir / 'learnings' / 'history' / 'history.json'
            if history_file.exists():
                try:
                    with open(history_file, 'r') as f:
                        learnings['history'] = json.load(f)
                except (IOError, json.JSONDecodeError):
                    pass

        except Exception as e:
            from pathlib import Path
            _utils_dir = Path(__file__).parent.parent.parent / 'utils'
            import sys
            if str(_utils_dir) not in sys.path:
                sys.path.insert(0, str(_utils_dir))
            from logging_utils import log_execution
            log_execution(f"Error reading learnings: {str(e)[:100]}", status='error')

        return learnings

    def build_child_loop_metadata(self) -> Dict[str, Dict[str, str]]:
        """
        Build metadata for child loops (names and learning paths)

        Returns:
            Dict mapping child loop directory name to metadata:
            {
                'child1': {
                    'qualified_name': 'parent.child1',  # Full dotted name for ravl command
                    'learning_path': '/path/to/learnings',
                    'execution_history_file': '/path/to/learnings/execution_learning/latest_run.json'
                }
            }
        """
        related = self.discover_related_loops()
        child_metadata = {}

        # Import LoopDiscovery to build qualified names
        _cli_dir = Path(__file__).parent.parent.parent / 'cli'
        if str(_cli_dir) not in sys.path:
            sys.path.insert(0, str(_cli_dir))
        from loop_discovery import LoopDiscovery

        # Create discovery instance to build namespace
        discovery = LoopDiscovery(project_root=self.loop_dir.parent.parent)

        for child_loop_dir in related['children']:
            # Get child loop directory name
            child_dir_name = child_loop_dir.name

            # Build full qualified name (e.g., "parent.child" or "grandparent.parent.child")
            qualified_name = discovery._build_namespace_from_path(child_loop_dir)

            # Calculate learning path (follows RAVL hierarchy)
            child_learning_path = self.learnings_dir / 'child_learnings' / child_dir_name / 'learnings'

            child_metadata[child_dir_name] = {
                'qualified_name': qualified_name,
                'learning_path': str(child_learning_path),
                'execution_history_file': str(child_learning_path / 'execution_learning' / 'latest_run.json')
            }

        return child_metadata

    def build_context_summary(self, reflection: Dict[str, Any]) -> str:
        """
        Build context summary from reflection and loop discovery

        Args:
            reflection: Reflection data from RAVL reflect phase

        Returns:
            Context summary string for use in prompts
        """
        context_parts = []

        # Add reflection timestamp
        if reflection.get('timestamp'):
            context_parts.append(f"Execution Timestamp: {reflection.get('timestamp')}")

        # Add loop metadata
        context_parts.append(f"\nLoop: {self.loop_dir.name}")

        # Add related loops info
        related = self.discover_related_loops()
        if related['parent']:
            context_parts.append(f"Parent Loop: {related['parent'].name}")
        if related['children']:
            context_parts.append(f"Child Loops: {', '.join(c.name for c in related['children'])}")
        if related['siblings']:
            context_parts.append(f"Sibling Loops: {', '.join(s.name for s in related['siblings'][:3])}")

        # Add learning context
        learnings = self.read_learnings_files(self.learnings_dir)
        if learnings['model']:
            model = learnings['model']
            if model.get('learning_iterations'):
                context_parts.append(f"\nExecution Attempts: {model['learning_iterations']}")
            if model.get('last_learned'):
                context_parts.append(f"Last Update: {model['last_learned']}")

        # Add recent performance if available
        if learnings['metrics']:
            latest_metric = list(learnings['metrics'].values())[-1]
            if latest_metric.get('success_rate'):
                context_parts.append(f"Recent Success Rate: {latest_metric['success_rate']:.1%}")

        # Add reflection data
        if reflection.get('learnings'):
            context_parts.append(f"\n## Previous Learnings\n{reflection['learnings']}")

        # Add child loop metadata for orchestrator loops
        child_metadata = self.build_child_loop_metadata()
        if child_metadata:
            # Get ravl.py path (known since we're executing via it right now)
            # Import here to avoid circular dependencies
            _cli_dir = Path(__file__).parent.parent.parent / 'cli'
            if str(_cli_dir) not in sys.path:
                sys.path.insert(0, str(_cli_dir))
            from ravl_cli_base import RAVLCLIBase

            framework_root = RAVLCLIBase.find_framework_root()
            ravl_py_path = framework_root / 'ravl' / 'bin' / 'ravl.py'

            context_parts.append("\n## Child Loop Configuration")
            context_parts.append("```python")
            context_parts.append("# Child loop metadata (generated at code generation time)")
            context_parts.append(f"RAVL_PY_PATH = Path('{ravl_py_path}')")
            context_parts.append("")
            context_parts.append("CHILD_LOOPS = {")
            for child_dir_name, metadata in child_metadata.items():
                context_parts.append(f"    '{child_dir_name}': {{")
                context_parts.append(f"        'qualified_name': '{metadata['qualified_name']}',")
                context_parts.append(f"        'learning_path': Path('{metadata['learning_path']}'),")
                context_parts.append(f"        'execution_history': Path('{metadata['execution_history_file']}')")
                context_parts.append("    },")
            context_parts.append("}")
            context_parts.append("```")

        return '\n'.join(context_parts)
