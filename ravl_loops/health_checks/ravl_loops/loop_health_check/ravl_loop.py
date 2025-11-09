#!/usr/bin/env python3
"""
Loop Health Check RAVL Loop

CRITICAL: Analyzes PROBLEM SPACE (domain learning) ONLY:
- Domain model evolution, verification quality, learned patterns
- WHAT the loop learns about its domain
- Business logic and domain insights

Uses LLM-powered diagnostics, persistent threads, and cross-loop pattern learning.
"""

import sys
import json
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Bootstrap: Find project root
_current = Path(__file__).resolve().parent
while not (_current / '.ravl').exists() and _current.parent != _current:
    _current = _current.parent
if not (_current / '.ravl').exists():
    _current = Path(__file__).resolve().parent.parent.parent
elif _current.name == '.ravl':
    _current = _current.parent

sys.path.insert(0, str(_current / '.ravl' / 'common'))
from ravl_base import BaseRAVLLoop

# Import sophisticated infrastructure
from domain_llm_analyzer import DomainLLMAnalyzer
from domain_thread_manager import DomainThreadManager
from domain_pattern_repository import DomainPatternRepository
from domain_data_discovery import DomainDataDiscovery


class LoopHealthCheckLoop(BaseRAVLLoop):
    """
    Analyzes loop health with LLM-powered diagnostics

    FOCUS: Problem space only (domain learning)
    """

    def __init__(self, model_path: str, config_path: Optional[str] = None, loop_name: str = ""):
        """Initialize loop health check"""
        super().__init__(Path(model_path), loop_name="Loop Health Check")

        self.loop_dir = Path(__file__).parent
        self.project_root = _current
        self.learning_path = Path(model_path).parent if model_path else self.loop_dir / 'learnings'

        # Initialize model
        self.model = self.load_model_with_timestamp(self._get_default_model)

        # Target loop from parameter
        import os
        self.target_loop_name = loop_name or os.environ.get('HEALTH_CHECK_TARGET_LOOP', '')

        if not self.target_loop_name:
            raise ValueError("No target loop specified. Use: ./ravl --loop-health <loop_name>")

        # Find target loop
        self.target_loop_dir = self._find_target_loop()

        # Load target loop config
        target_config = self._load_target_config()

        # Resolve learning path
        from ravl_runner import RAVLRunner
        target_learning_path = RAVLRunner.resolve_learning_path(
            loop_dir=self.target_loop_dir,
            loop_config=target_config,
            cli_learning_path=None,
            project_root=self.project_root
        )
        self.target_loop_learning = target_learning_path / 'loop_learning'

        # Initialize sophisticated infrastructure
        self.llm_analyzer = DomainLLMAnalyzer(prompts_dir=self.loop_dir / "config")

        # Thread manager for this specific target loop
        thread_dir = self.learning_path / 'threads'
        thread_file = thread_dir / f"domain_{self.target_loop_name}.jsonl"
        self.thread_manager = DomainThreadManager(thread_file)

        # Pattern repository (shared across all loops)
        pattern_file = self.learning_path / 'domain_patterns.jsonl'
        self.pattern_repository = DomainPatternRepository(pattern_file)

        # Data discovery
        self.data_discovery = DomainDataDiscovery(self.target_loop_learning)

    def _get_default_model(self) -> Dict[str, Any]:
        """Get default model"""
        return {
            'learning_iterations': 0,
            'last_learned': None,
            'known_domain_patterns': {},
            'improvement_suggestions': [],
            'loops_diagnosed': []
        }

    def _find_target_loop(self) -> Path:
        """Find target loop using LoopDiscovery"""
        sys.path.insert(0, str(self.project_root / '.ravl' / 'common' / 'cli'))
        from loop_discovery import LoopDiscovery

        discovery = LoopDiscovery(self.project_root)
        try:
            return discovery.find_loop(self.target_loop_name)
        except ValueError as e:
            raise FileNotFoundError(f"Could not find loop: {self.target_loop_name}") from e

    def _load_target_config(self) -> Dict[str, Any]:
        """Load configuration"""
        sys.path.insert(0, str(self.project_root / '.ravl' / 'common' / 'cli'))
        from loop_discovery import LoopDiscovery

        discovery = LoopDiscovery(self.project_root)
        try:
            return discovery.load_config(self.target_loop_dir)
        except Exception:
            return {}

    def reflect(self) -> Dict[str, Any]:
        """REFLECT: Analyze domain learning data"""
        print(f"\n🔍 Analyzing domain learning health: {self.target_loop_name}", file=sys.stderr)

        # Check if learning structure exists
        if not self.target_loop_learning.exists():
            learnings_dir = self.target_loop_dir / 'learnings'
            if not learnings_dir.exists() or not any(learnings_dir.iterdir()):
                return {
                    'status': 'no_data',
                    'loop_state': 'fresh',
                    'message': f"Loop '{self.target_loop_name}' has no domain learning data yet."
                }
            else:
                return {
                    'status': 'old_structure',
                    'message': f"Loop '{self.target_loop_name}' uses old learning structure."
                }

        # Discover all domain learning data
        domain_data = self.data_discovery.discover_all()

        reflection = {
            'target_loop': self.target_loop_name,
            'target_dir': str(self.target_loop_dir),
            'domain_data': domain_data,
            'thread_history': self.thread_manager.format_thread_history(limit=5)
        }

        return reflection

    def act(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        """ACT: Generate diagnostic report with LLM analysis - ALWAYS calls LLM"""
        # Handle no data
        if reflection.get('status') in ['no_data', 'old_structure']:
            return reflection

        print(f"  Generating domain diagnostics...", file=sys.stderr)

        # Always call LLM with full context - no state routing!
        return self._generate_diagnostic_report(reflection)

    def _generate_diagnostic_report(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate diagnostic report by ALWAYS calling LLM with full context.

        Passes raw loop learning files to LLM - let it analyze.
        Implements RAVL Principle 3: "Maximize LLM Intelligence"
        """
        domain_data = reflection['domain_data']

        # Get cross-loop patterns (for few-shot learning)
        patterns = self.pattern_repository.get_patterns_for_loop(reflection['target_loop'])

        # Build simple domain context - just pass raw files to LLM
        domain_context = {
            'loop_name': reflection['target_loop'],
            'loop_dir': str(reflection['target_dir']),
            'files': domain_data.get('files', [])
        }

        # ALWAYS call LLM analyzer with FULL context
        diagnosis = self.llm_analyzer.analyze_domain_health(
            domain_context=domain_context,
            learned_patterns=patterns[:5]
        )

        # Save diagnostic turn for thread continuity
        self.thread_manager.append_turn(
            input_data={'context': domain_context},
            output_data=diagnosis
        )

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'target_loop': reflection['target_loop'],
            'diagnosis': diagnosis
        }

    def verify(self, previous_action: Dict[str, Any], current_reflection: Dict[str, Any]) -> Dict[str, Any]:
        """VERIFY: Check if diagnostic was successful"""
        if not previous_action or previous_action.get('status') in ['no_data', 'old_structure']:
            return {
                'overall_passed': False,
                'message': previous_action.get('message', 'Health check failed') if previous_action else 'Health check failed'
            }

        status = previous_action.get('status', 'unknown')

        return {
            'overall_passed': True,
            'domain_health_status': status,
            'target_loop': previous_action.get('target_loop'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def learn(self, verification: Dict[str, Any], action_result: Dict[str, Any]) -> None:
        """LEARN: Update model and extract patterns"""
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
        print(f"\n🔍 Domain Learning Health Assessment:", file=sys.stderr)
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
        """Extract successful diagnosis as a pattern"""
        diagnosis = action_result.get('diagnosis', {})

        if not diagnosis.get('success') or diagnosis.get('confidence', 0) < 0.7:
            return

        pattern = {
            'id': f"domain_{action_result['target_loop']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'source_loop': action_result['target_loop'],
            'issue_type': 'domain',
            'root_cause': diagnosis.get('root_cause_analysis', ''),
            'solution_steps': diagnosis.get('actionable_steps', []),
            'confidence': diagnosis.get('confidence', 0),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'success_count': 1
        }

        self.pattern_repository.add_pattern(pattern)
        print(f"   📚 Extracted domain pattern: {pattern['id']}", file=sys.stderr)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Domain Learning Health Check')
    parser.add_argument('target_loop', help='Target loop to analyze')
    parser.add_argument('--model', default=None, help='Path to model.yml')

    args = parser.parse_args()

    if args.model:
        model_path = args.model
    else:
        loop_dir = Path(__file__).parent
        model_path = str(loop_dir / 'learnings' / 'model.yml')

    # Create and run loop
    loop = LoopHealthCheckLoop(model_path, loop_name=args.target_loop)

    # Run RAVL cycle
    reflection = loop.reflect()
    action = loop.act(reflection)

    # Print results
    if action.get('status') == 'no_data':
        print(f"\n❌ {action.get('message')}", file=sys.stderr)
        sys.exit(1)

    status = action.get('status', 'unknown')
    if status == 'healthy':
        print(f"\n✅ Domain Learning Health: HEALTHY", file=sys.stderr)
        print(f"   Verification pass rate: {action.get('pass_rate', action['metrics'].get('verification_success_rate', 0))*100:.0f}%", file=sys.stderr)
        if action.get('improvements'):
            print(f"\n💡 Domain Improvement Suggestions:\n{action['improvements']}", file=sys.stderr)
    elif status == 'failing':
        print(f"\n❌ Domain Learning Health: FAILING", file=sys.stderr)
        print(f"   Verification pass rate: {action.get('pass_rate', 0)*100:.0f}%", file=sys.stderr)
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
        print(f"\n🟡 Domain Learning Health: MODERATE", file=sys.stderr)
        for issue in action.get('issues', []):
            print(f"   • {issue['message']}", file=sys.stderr)

    verification = loop.verify(action, reflection)
    loop.learn(verification, action)


if __name__ == '__main__':
    main()
