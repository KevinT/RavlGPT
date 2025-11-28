#!/usr/bin/env python3
"""
Execution Health Check RAVL Loop

CRITICAL: Analyzes SOLUTION SPACE (execution infrastructure) ONLY:
- Code generation, DSL stability, dependencies
- HOW to make the RAVL framework execute properly
- Framework infrastructure issues

Uses LLM-powered diagnostics, persistent threads, and cross-loop pattern learning.
"""

import sys
import json
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from collections import Counter

# Bootstrap: Add framework common/ to path
# This file is at: ravl_loops/framework/child_loops/health_checks/child_loops/execution_health_check/ravl_loop.py
# Framework root is 6 levels up
_framework_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(_framework_root / 'ravl' / 'common'))
from ravl_base import BaseRAVLLoop

# Import sophisticated infrastructure
from execution_llm_analyzer import ExecutionLLMAnalyzer
from execution_thread_manager import ExecutionThreadManager
from execution_pattern_repository import ExecutionPatternRepository
from execution_data_discovery import ExecutionDataDiscovery


class ExecutionHealthCheckLoop(BaseRAVLLoop):
    """
    Analyzes execution health with LLM-powered diagnostics

    FOCUS: Solution space only (execution infrastructure)
    """

    def __init__(self, model_path: str, config_path: Optional[str] = None, loop_name: str = ""):
        """Initialize execution health check"""
        super().__init__(Path(model_path), loop_name="Execution Health Check")

        self.loop_dir = Path(__file__).parent

        # Find project root using framework utility
        from ravl.common.cli.ravl_cli_base import RAVLCLIBase
        self.project_root = RAVLCLIBase.find_project_root(required=False)

        self.learning_path = Path(model_path).parent if model_path else self.loop_dir / 'learnings'

        # Initialize model
        self.model = self.load_model_with_timestamp(self._get_default_model)

        # Target loop from parameter
        import os
        self.target_loop_name = loop_name or os.environ.get('HEALTH_CHECK_TARGET_LOOP', '')

        if not self.target_loop_name:
            raise ValueError("No target loop specified. Use: ./ravl --execution-health <loop_name>")

        # Optional focus area for biasing analysis
        self.focus_area = os.environ.get('HEALTH_CHECK_FOCUS', None)

        # Find target loop
        self.target_loop_dir = self._find_target_loop()

        # Load target loop config
        target_config = self._load_target_config()

        # Resolve learning path using framework's existing logic
        from ravl_runner import RAVLRunner
        target_learning_path = RAVLRunner.resolve_learning_path(
            loop_dir=self.target_loop_dir,
            loop_config=target_config,
            cli_learning_path=None,
            project_root=self.project_root
        )
        self.target_execution_learning = target_learning_path / 'execution_learning'

        # Initialize sophisticated infrastructure
        self.llm_analyzer = ExecutionLLMAnalyzer(prompts_dir=self.loop_dir / "config")

        # Thread manager for this specific target loop
        thread_dir = self.learning_path / 'threads'
        thread_file = thread_dir / f"execution_{self.target_loop_name}.jsonl"
        self.thread_manager = ExecutionThreadManager(thread_file)

        # Pattern repository (shared across all loops)
        pattern_file = self.learning_path / 'execution_patterns.jsonl'
        self.pattern_repository = ExecutionPatternRepository(pattern_file)

        # Data discovery for comprehensive analysis
        self.data_discovery = ExecutionDataDiscovery(self.target_execution_learning)

    def _get_default_model(self) -> Dict[str, Any]:
        """Get default model for execution health tracking"""
        return {
            'learning_iterations': 0,
            'last_learned': None,
            'known_failure_patterns': {},
            'successful_strategies': [],
            'loops_diagnosed': []
        }

    def _find_target_loop(self) -> Path:
        """Find target loop directory using LoopDiscovery"""
        # Find framework root (where common/cli lives)
        # This file is at: ravl_loops/framework/child_loops/health_checks/child_loops/execution_health_check/ravl_loop.py
        # Framework root is 6 levels up
        framework_root = Path(__file__).resolve().parents[5]
        sys.path.insert(0, str(framework_root / 'ravl' / 'common' / 'cli'))
        from loop_discovery import LoopDiscovery

        discovery = LoopDiscovery(self.project_root)
        try:
            return discovery.find_loop(self.target_loop_name)
        except ValueError as e:
            raise FileNotFoundError(f"Could not find loop: {self.target_loop_name}") from e

    def _load_target_config(self) -> Dict[str, Any]:
        """Load configuration for target loop"""
        # Find framework root (where common/cli lives)
        framework_root = Path(__file__).resolve().parents[5]
        sys.path.insert(0, str(framework_root / 'ravl' / 'common' / 'cli'))
        from loop_discovery import LoopDiscovery

        discovery = LoopDiscovery(self.project_root)
        try:
            return discovery.load_config(self.target_loop_dir)
        except Exception:
            return {}

    def reflect(self) -> Dict[str, Any]:
        """
        REFLECT: Analyze execution learning data with comprehensive discovery

        Returns:
            Dict with execution analysis
        """
        print(f"\n🔍 Analyzing execution health: {self.target_loop_name}", file=sys.stderr)

        # Check if learning structure exists
        if not self.target_execution_learning.exists():
            # Check if this is a fresh loop vs old structure
            learnings_dir = self.target_loop_dir / 'learnings'
            if not learnings_dir.exists() or not any(learnings_dir.iterdir()):
                return {
                    'status': 'no_data',
                    'loop_state': 'fresh',
                    'message': f"Loop '{self.target_loop_name}' has no learning data yet. Run the loop first."
                }
            else:
                return {
                    'status': 'old_structure',
                    'message': f"Loop '{self.target_loop_name}' uses old learning structure. Delete learnings/ and re-run."
                }

        # Discover all execution learning data
        execution_data = self.data_discovery.discover_all()

        # Check if loop has been modified since last run
        loop_modified = self._check_loop_modification()

        # Check venv health for Python version mismatches
        venv_health = self._check_venv_health()

        reflection = {
            'target_loop': self.target_loop_name,
            'target_dir': str(self.target_loop_dir),
            'loop_modified': loop_modified,
            'execution_data': execution_data,
            'thread_history': self.thread_manager.format_thread_history(limit=5),
            'venv_health': venv_health
        }

        return reflection

    def _check_loop_modification(self) -> bool:
        """Check if loop was modified since last execution"""
        loop_file = self.target_loop_dir / 'ravl_loop.py'
        if not loop_file.exists():
            loop_file = self.target_loop_dir / 'ravl_loop.md'

        if not loop_file.exists():
            return False

        # Check latest execution timestamp
        recent_dir = self.target_execution_learning / 'recent_attempts'
        if not recent_dir.exists():
            return False

        attempt_dirs = sorted([d for d in recent_dir.iterdir() if d.is_dir()])
        if not attempt_dirs:
            return False

        latest_attempt = attempt_dirs[-1]
        attempt_time = latest_attempt.stat().st_mtime
        loop_mtime = loop_file.stat().st_mtime

        return loop_mtime > attempt_time

    def _check_venv_health(self) -> Dict[str, Any]:
        """
        Check framework venv health for Python version mismatches

        Returns dict with venv health status including version mismatch detection.
        This helps diagnose issues caused by Python upgrades (e.g., 3.12 → 3.14)
        where binary wheels become incompatible.
        """
        # Find framework venv (check both project and framework locations)
        framework_venv = _framework_root / 'venv'

        result = {
            'has_venv': framework_venv.exists(),
            'venv_path': str(framework_venv),
            'system_python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'venv_python_version': None,
            'version_mismatch': False,
            'recommendation': None
        }

        if not result['has_venv']:
            result['recommendation'] = "venv will be auto-created on next loop run"
            return result

        # Read venv's Python version from pyvenv.cfg
        pyvenv_cfg = framework_venv / 'pyvenv.cfg'
        if not pyvenv_cfg.exists():
            result['recommendation'] = "venv missing pyvenv.cfg - delete and recreate"
            return result

        try:
            with open(pyvenv_cfg, 'r') as f:
                for line in f:
                    if line.startswith('version ='):
                        venv_version = line.split('=')[1].strip()
                        result['venv_python_version'] = venv_version
                        break
        except Exception as e:
            result['recommendation'] = f"Could not read pyvenv.cfg: {e}"
            return result

        if not result['venv_python_version']:
            result['recommendation'] = "venv pyvenv.cfg missing version - delete and recreate"
            return result

        # Compare major.minor versions
        system_major_minor = f"{sys.version_info.major}.{sys.version_info.minor}"
        venv_major_minor = '.'.join(result['venv_python_version'].split('.')[:2])

        if system_major_minor != venv_major_minor:
            result['version_mismatch'] = True
            result['recommendation'] = (
                f"venv Python {venv_major_minor} incompatible with system Python {system_major_minor}. "
                f"Binary wheels (like pydantic_core) won't load. "
                f"Delete venv: rm -rf {framework_venv}"
            )

        return result

    def act(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        """ACT: Generate diagnostic report with LLM analysis - ALWAYS calls LLM"""
        # Handle no data or old structure
        if reflection.get('status') in ['no_data', 'old_structure']:
            return reflection

        # Check for critical venv issues first
        venv_health = reflection.get('venv_health', {})
        if venv_health.get('version_mismatch'):
            print(f"  ⚠️  venv Python version mismatch detected!", file=sys.stderr)
            print(f"  {venv_health['recommendation']}", file=sys.stderr)
            return {
                **reflection,
                'critical_issue': 'venv_version_mismatch',
                'status': 'critical_venv_issue',
                'message': venv_health['recommendation']
            }

        print(f"  Generating execution diagnostics...", file=sys.stderr)

        # Always call LLM with full context - no state routing!
        return self._generate_diagnostic_report(reflection)

    def _generate_diagnostic_report(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate diagnostic report by ALWAYS calling LLM with full context.

        Passes raw execution learning files to LLM - let it analyze.
        Implements RAVL Principle 3: "Maximize LLM Intelligence"
        """
        execution_data = reflection['execution_data']

        # Get cross-loop patterns (for few-shot learning)
        patterns = self.pattern_repository.get_patterns_for_loop(reflection['target_loop'])

        # Build simple execution context - just pass raw files to LLM
        execution_context = {
            'loop_name': reflection['target_loop'],
            'loop_dir': str(reflection['target_dir']),
            'files': execution_data.get('files', [])
        }

        # ALWAYS call LLM analyzer with FULL context
        diagnosis = self.llm_analyzer.analyze_execution_health(
            execution_context=execution_context,
            learned_patterns=patterns[:5],
            focus_area=self.focus_area
        )

        # Save diagnostic turn for thread continuity
        self.thread_manager.append_turn(
            input_data={'context': execution_context},
            output_data=diagnosis
        )

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'target_loop': reflection['target_loop'],
            'diagnosis': diagnosis
        }

    def verify(self, previous_action: Dict[str, Any], current_reflection: Dict[str, Any]) -> Dict[str, Any]:
        """
        VERIFY: Check if diagnostic was successful

        Args:
            previous_action: Previous diagnostic
            current_reflection: Current reflection

        Returns:
            Verification result
        """
        if not previous_action or previous_action.get('status') in ['no_data', 'old_structure']:
            return {
                'overall_passed': False,
                'message': previous_action.get('message', 'Health check failed') if previous_action else 'Health check failed'
            }

        # Diagnostic is successful if we generated a report
        status = previous_action.get('status', 'unknown')

        return {
            'overall_passed': True,
            'execution_health_status': status,
            'target_loop': previous_action.get('target_loop'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def learn(self, verification: Dict[str, Any], action_result: Dict[str, Any]) -> None:
        """
        LEARN: Update model and extract patterns

        Args:
            verification: Verification result
            action_result: Action result
        """
        # Print diagnostics regardless of verification status
        self._print_diagnostics(action_result)

        if not verification.get('overall_passed'):
            return

        # Track loops diagnosed
        target_loop = action_result.get('target_loop')
        if target_loop and target_loop not in self.model.get('loops_diagnosed', []):
            if 'loops_diagnosed' not in self.model:
                self.model['loops_diagnosed'] = []
            self.model['loops_diagnosed'].append(target_loop)

        # UNIVERSAL PATTERN LEARNING: Extract patterns from ALL diagnostics (not just failures)
        # If LLM provided high-confidence recommendations, save as pattern
        diagnosis = action_result.get('diagnosis', {})
        if diagnosis.get('success') and diagnosis.get('confidence', 0) >= 0.7:
            self._extract_pattern(action_result)

        # Update learning iterations
        self.model['learning_iterations'] += 1
        self.model['last_learned'] = datetime.now(timezone.utc).isoformat()

        # Save model
        self.save_model_with_timestamp(self.model)

    def _print_diagnostics(self, action: Dict[str, Any]) -> None:
        """Print diagnostic results to user"""
        # Handle no data case
        if action.get('status') == 'no_data':
            print(f"\n❌ {action.get('message')}", file=sys.stderr)
            return

        # Get LLM diagnosis
        diagnosis = action.get('diagnosis', {})

        if not diagnosis or not diagnosis.get('success'):
            print(f"\n⚠️  Diagnostic generation failed: {diagnosis.get('error', 'Unknown error')}", file=sys.stderr)
            return

        # Print health assessment from LLM
        print(f"\n🔍 Execution Health Assessment:", file=sys.stderr)
        print(f"   {diagnosis.get('full_analysis', 'No analysis provided')}", file=sys.stderr)

        # Print root cause if provided
        if diagnosis.get('root_cause_analysis'):
            print(f"\n💡 Root Cause:", file=sys.stderr)
            print(f"   {diagnosis['root_cause_analysis']}", file=sys.stderr)

        # Print actionable steps
        if diagnosis.get('actionable_steps'):
            print(f"\n✅ Recommended Actions:", file=sys.stderr)
            for i, step in enumerate(diagnosis['actionable_steps'], 1):
                print(f"   {i}. {step}", file=sys.stderr)

        # Print confidence
        if 'confidence' in diagnosis:
            confidence_pct = int(diagnosis['confidence'] * 100)
            print(f"\n📊 Confidence: {confidence_pct}%", file=sys.stderr)

    def _extract_pattern(self, action_result: Dict[str, Any]) -> None:
        """Extract successful diagnosis as a pattern for future use"""
        diagnosis = action_result.get('diagnosis', {})

        if not diagnosis.get('success') or diagnosis.get('confidence', 0) < 0.7:
            return  # Only extract high-confidence diagnoses

        pattern = {
            'id': f"execution_{action_result['target_loop']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'source_loop': action_result['target_loop'],
            'issue_type': 'execution',
            'root_cause': diagnosis.get('root_cause_analysis', ''),
            'solution_steps': diagnosis.get('actionable_steps', []),
            'confidence': diagnosis.get('confidence', 0),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'success_count': 1
        }

        self.pattern_repository.add_pattern(pattern)
        print(f"   📚 Extracted execution pattern: {pattern['id']}", file=sys.stderr)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Execution Health Check')
    parser.add_argument('target_loop', help='Target loop to analyze')
    parser.add_argument('--model', default=None, help='Path to model.yml')

    args = parser.parse_args()

    # Set model path
    if args.model:
        model_path = args.model
    else:
        loop_dir = Path(__file__).parent
        model_path = str(loop_dir / 'learnings' / 'model.yml')

    # Create and run loop
    loop = ExecutionHealthCheckLoop(model_path, loop_name=args.target_loop)

    # Run RAVL cycle
    reflection = loop.reflect()
    action = loop.act(reflection)

    # Print results
    if action.get('status') == 'no_data':
        print(f"\n❌ {action.get('message')}", file=sys.stderr)
        sys.exit(1)

    status = action.get('status', 'unknown')
    if status == 'healthy':
        print(f"\n✅ Execution Health: HEALTHY", file=sys.stderr)
        print(f"   Success rate: {action.get('success_rate', action['metrics']['success_rate'])*100:.0f}%", file=sys.stderr)
        if action.get('improvements'):
            print(f"\n💡 Improvement Suggestions:\n{action['improvements']}", file=sys.stderr)
    elif status == 'failing':
        print(f"\n❌ Execution Health: FAILING", file=sys.stderr)
        print(f"   Success rate: {action.get('success_rate', 0)*100:.0f}%", file=sys.stderr)
        diagnosis = action.get('diagnosis', {})
        if diagnosis.get('root_cause_analysis'):
            print(f"\n🔍 Root Cause: {diagnosis['root_cause_analysis']}", file=sys.stderr)
        if diagnosis.get('actionable_steps'):
            print(f"\n💡 Recommended Steps:", file=sys.stderr)
            for i, step in enumerate(diagnosis['actionable_steps'], 1):
                print(f"   {i}. {step}", file=sys.stderr)
    elif status == 'stale':
        print(f"\n⚠️  {action.get('message')}", file=sys.stderr)
    else:
        print(f"\n🟡 Execution Health: MODERATE", file=sys.stderr)
        for issue in action.get('issues', []):
            print(f"   • {issue['message']}", file=sys.stderr)

    verification = loop.verify(action, reflection)
    loop.learn(verification, action)


if __name__ == '__main__':
    main()
