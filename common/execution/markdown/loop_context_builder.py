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

    def discover_related_loops(self) -> Dict[str, List[Path]]:
        """
        Discover parent, child, and sibling loops based on directory structure

        Returns dict with 'parent', 'children', 'siblings' keys
        """
        result = {
            'parent': None,
            'children': [],
            'siblings': []
        }

        # Determine loop type based on directory structure
        is_child_loop = self.loop_dir.parent.name == 'ravl_loops'

        # Find parent
        if is_child_loop:
            parent_dir = self.loop_dir.parent.parent
            if (parent_dir / 'config' / 'ravl.yml').exists():
                result['parent'] = parent_dir

        # Find children
        children_dir = self.loop_dir / 'ravl_loops'
        if children_dir.exists():
            for child in children_dir.iterdir():
                if child.is_dir() and (child / 'config' / 'ravl.yml').exists():
                    result['children'].append(child)

        # Find siblings
        if is_child_loop:
            siblings_dir = self.loop_dir.parent
            for sibling in siblings_dir.iterdir():
                if (sibling.is_dir() and
                    sibling != self.loop_dir and
                    (sibling / 'config' / 'ravl.yml').exists()):
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
                import yaml
                with open(model_file, 'r') as f:
                    learnings['model'] = yaml.safe_load(f)

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
            context_parts.append(f"Execution Timestamp: {reflection['timestamp']}")

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

        return '\n'.join(context_parts)
