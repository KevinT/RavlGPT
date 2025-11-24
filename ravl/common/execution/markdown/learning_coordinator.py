#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Learning Coordinator

Handles LEARN phase of RAVL cycle - both execution and domain learning.
"""

import json
import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable

# Add utils to path
_utils_dir = Path(__file__).parent.parent.parent / 'utils'
if str(_utils_dir) not in sys.path:
    sys.path.insert(0, str(_utils_dir))

from logging_utils import log_message, log_execution

# Add config to path
_config_dir = Path(__file__).parent.parent.parent / 'config'
if str(_config_dir) not in sys.path:
    sys.path.insert(0, str(_config_dir))

from config_loader import get_max_tokens


class LearningCoordinator:
    """
    Coordinates learning phase of RAVL execution

    Responsibilities:
    - Coordinate execution learning (code generation)
    - Coordinate domain learning (problem space)
    - Calculate domain metrics
    - Analyze code regeneration needs
    - Synthesize run insights
    - Update performance metrics
    """

    def __init__(
        self,
        learnings_dir: Path,
        execution_learning_mgr,
        loop_learning_mgr,
        llm_provider,
        llm_helper,
        phases_accessor: Callable[[], Dict[str, str]],
        cache_manager,
        should_attempt_code_generation: Callable[[], bool]
    ):
        """
        Initialize learning coordinator

        Args:
            learnings_dir: Path to learnings directory
            execution_learning_mgr: ExecutionLearningManager instance
            loop_learning_mgr: LoopLearningManager instance
            llm_provider: LLM provider for insight synthesis
            llm_helper: LLMResponseHelper for prompt loading/parsing
            phases_accessor: Function to access parsed markdown phases (lazy loaded)
            cache_manager: CodeCacheManager instance
            should_attempt_code_generation: Function that returns whether code gen is enabled
        """
        self.learnings_dir = learnings_dir
        self.execution_learning_mgr = execution_learning_mgr
        self.loop_learning_mgr = loop_learning_mgr
        self.llm = llm_provider
        self.llm_helper = llm_helper
        self.get_phases = phases_accessor
        self.cache_manager = cache_manager
        self.should_attempt_code_generation = should_attempt_code_generation

        # Track current attempt number for cross-manager coordination
        self._current_attempt_number = None

    def learn(
        self,
        verification: Dict[str, Any],
        action_result: Dict[str, Any],
        last_reflection: Dict[str, Any],
        last_generated_code: Optional[str],
        save_verified_code_fn: Callable[[str, Optional[Dict[str, Any]]], None]
    ) -> None:
        """
        LEARN phase: Automatic learning from verification outcomes

        Splits learning into execution (infrastructure) and domain (problem space).

        Args:
            verification: Combined verification results (execution + domain)
            action_result: Output from ACT phase
            last_reflection: Output from REFLECT phase (for insight synthesis)
            last_generated_code: The generated code from ACT phase
            save_verified_code_fn: Function to save verified code to cache
        """
        log_message("Learning...", status='info')

        # EXECUTION LEARNING: How to make code work
        if 'execution' in verification:
            # Pass domain verification too, so execution learning can check regeneration recommendation
            domain_verification = verification.get('domain', {})
            self._learn_execution(
                verification['execution'],
                action_result,
                domain_verification,
                last_generated_code,
                save_verified_code_fn
            )

        # DOMAIN LEARNING: What the loop learned about its problem (THE "L" IN RAVL)
        if 'domain' in verification:
            self._learn_domain(verification['domain'], action_result)

        # REGENERATION ANALYSIS: Should code be regenerated next run?
        # Only analyze if we're generating code (not for pure markdown loops)
        if (self.should_attempt_code_generation() and last_reflection and
            'execution' in verification and 'domain' in verification):
            log_execution("Analyzing code regeneration need...", status='working')
            regeneration_analysis = self._analyze_regeneration_need(
                reflection=last_reflection,
                action_result=action_result,
                execution_verification=verification['execution'],
                domain_verification=verification['domain']
            )

            # Save recommendation for next REFLECT to read
            execution_learning_dir = self.learnings_dir / 'execution_learning'
            current_state_dir = execution_learning_dir / 'current_state'
            current_state_dir.mkdir(parents=True, exist_ok=True)

            recommendation_file = current_state_dir / 'regeneration_recommendation.json'
            with open(recommendation_file, 'w', encoding='utf-8') as f:
                json.dump(regeneration_analysis, f, indent=2)

            if regeneration_analysis.get('recommend_regeneration', False):
                rationale = regeneration_analysis.get('rationale', 'See regeneration_recommendation.json')
                log_execution(f"💡 Regeneration recommended: {rationale[:80]}", status='info')
            else:
                log_execution("✓ Code is working well - will reuse if successful", status='success')

        log_execution("Learning saved to execution_learning/ and loop_learning/", status='success')

    def _learn_execution(
        self,
        execution_verification: Dict[str, Any],
        action_result: Dict[str, Any],
        domain_verification: Optional[Dict[str, Any]],
        last_generated_code: Optional[str],
        save_verified_code_fn: Callable[[str, Optional[Dict[str, Any]]], None]
    ) -> None:
        """
        Learn from execution outcomes (code generation, infrastructure)

        This is SOLUTION LEARNING - improving code generation and execution.

        Args:
            execution_verification: Execution verification results
            action_result: Output from ACT phase
            domain_verification: Domain verification (for regeneration recommendations)
            last_generated_code: The generated code from ACT phase
            save_verified_code_fn: Function to save verified code to cache
        """
        # Save execution attempt and track attempt number
        self._current_attempt_number = self.execution_learning_mgr.save_execution_attempt(
            execution_result=execution_verification,
            generated_code=last_generated_code,
            dsl=action_result.get('inferred_dsl')
        )

        # Check if LLM recommends code regeneration based on domain verification
        if domain_verification:
            recommend_regeneration = domain_verification.get('recommend_code_regeneration', False)
            regeneration_rationale = domain_verification.get('regeneration_rationale', '')

            if recommend_regeneration:
                log_execution(f"🔄 Domain verification recommends code regeneration: {regeneration_rationale}", status='info')
                # Explicitly invalidate cache to force regeneration on next run
                if self.cache_manager:
                    self.cache_manager._clear_cache()
                    log_execution("✓ Cache cleared - code will be regenerated on next run", status='success')
                return

        # Cache code only if execution succeeded AND has no warnings
        # If code has warnings, force regeneration with warning guidance
        if (execution_verification.get('passed', False) and
            not execution_verification.get('has_warnings', False) and
            last_generated_code):
            save_verified_code_fn(last_generated_code, action_result.get('inferred_dsl'))
        elif execution_verification.get('has_warnings', False):
            # Invalidate cache to force regeneration with warning fixes
            log_execution("Code has warnings - invalidating cache to improve quality", status='info')

    def _learn_domain(
        self,
        domain_verification: Dict[str, Any],
        action_result: Dict[str, Any],
        last_reflection: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Learn from domain outcomes (problem space learning)

        This is LOOP LEARNING - THE ACTUAL "L" IN RAVL.

        Args:
            domain_verification: Domain verification results
            action_result: Output from ACT phase
            last_reflection: Output from REFLECT phase (for insight synthesis)
        """
        # Calculate domain metrics
        metrics = self._calculate_domain_metrics(domain_verification)

        # Save domain attempt
        self.loop_learning_mgr.save_domain_attempt(
            action_result=action_result,
            verification=domain_verification,
            metrics=metrics
        )

        # Synthesize insights from full RAVL run (REFLECT → ACT → VERIFY)
        if last_reflection:
            run_insights = self._synthesize_run_insights(
                reflection=last_reflection,
                action_result=action_result,
                verification=domain_verification
            )
            # Persist insights for next REFLECT to use, associated with the execution attempt
            self.loop_learning_mgr.save_run_insights(run_insights, attempt_number=self._current_attempt_number)

        # Update performance metrics
        self._update_performance_metrics(domain_verification)

    def _calculate_domain_metrics(self, verification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate domain metrics from verification results

        Args:
            verification: Domain verification results

        Returns:
            Dict with calculated metrics
        """
        criteria_results = verification.get('criteria_results', [])

        passed_count = 0
        total_count = len(criteria_results)

        for criterion in criteria_results:
            if isinstance(criterion, dict) and criterion.get('passed', False):
                passed_count += 1

        failed_count = total_count - passed_count

        return {
            'total_criteria': total_count,
            'total_passed': passed_count,
            'total_failed': failed_count,
            'pass_rate': passed_count / total_count if total_count > 0 else 0.0,
            'overall_passed': verification.get('overall_passed', False)
        }

    def _analyze_regeneration_need(
        self,
        reflection: Dict[str, Any],
        action_result: Dict[str, Any],
        execution_verification: Dict[str, Any],
        domain_verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze whether code should be regenerated on next run

        Analyzes loop definition, current run outcomes, and execution history
        to determine if fresh code generation would improve results.

        Args:
            reflection: Output from REFLECT phase
            action_result: Output from ACT phase
            execution_verification: Execution verification results
            domain_verification: Domain verification results

        Returns:
            Dict with regeneration recommendation and rationale
        """
        # Get act and verify sections from loop definition
        phases = self.get_phases()
        act_instructions = phases.get('act', '')
        verify_instructions = phases.get('verify', '')

        # Build execution history summary
        execution_learning_dir = self.learnings_dir / 'execution_learning'
        recent_attempts_dir = execution_learning_dir / 'recent_attempts'

        history_parts = []
        if recent_attempts_dir.exists():
            attempt_dirs = sorted(
                [d for d in recent_attempts_dir.iterdir() if d.is_dir() and d.name.startswith('attempt_')],
                key=lambda d: int(d.name.split('_')[1])
            )

            history_parts.append(f"Total attempts: {len(attempt_dirs)}")

            # Summarize last 5 attempts
            for attempt_dir in attempt_dirs[-5:]:
                attempt_num = attempt_dir.name
                result_file = attempt_dir / 'execution_result.json'
                if result_file.exists():
                    try:
                        with open(result_file, 'r', encoding='utf-8') as f:
                            result = json.load(f)
                        passed = result.get('passed', False)
                        status = "✓ PASSED" if passed else "✗ FAILED"
                        history_parts.append(f"{attempt_num}: {status}")
                    except (IOError, json.JSONDecodeError):
                        history_parts.append(f"{attempt_num}: Unknown")

            # Check if using cached code
            current_state_dir = execution_learning_dir / 'current_state'
            verified_code_file = current_state_dir / 'verified_code.py'
            if verified_code_file.exists():
                history_parts.append("\n⚠️  Currently using CACHED CODE (same code across runs)")

        execution_history = "\n".join(history_parts) if history_parts else "No execution history available"

        # Truncate summaries for LLM
        reflection_summary = self.llm_helper.truncate_for_llm(reflection, max_length=1000)
        action_summary = self.llm_helper.truncate_for_llm(action_result, max_length=1000)
        verification_summary = {
            'execution': execution_verification,
            'domain': domain_verification
        }
        verification_summary = self.llm_helper.truncate_for_llm(verification_summary, max_length=1000)

        # Load and format prompt
        prompt = self.llm_helper.load_prompt(
            'learn_regeneration_analysis',
            act_instructions=act_instructions,
            verify_instructions=verify_instructions,
            reflection_summary=json.dumps(reflection_summary, indent=2),
            action_summary=json.dumps(action_summary, indent=2),
            verification_summary=json.dumps(verification_summary, indent=2),
            execution_history=execution_history
        )

        llm_response = self.llm.complete(prompt, max_tokens=get_max_tokens('regeneration_analysis', 2048))

        # Parse JSON response
        try:
            analysis = self.llm_helper.parse_json_response(llm_response)
        except Exception as e:
            log_message(f"Warning: Could not parse regeneration analysis: {e}", status='error')
            analysis = {
                'recommend_regeneration': False,
                'rationale': f'Failed to parse analysis: {e}',
                'error': str(e)
            }

        # Add timestamp
        analysis['timestamp'] = datetime.now(timezone.utc).isoformat()

        return analysis

    def _synthesize_run_insights(
        self,
        reflection: Dict[str, Any],
        action_result: Dict[str, Any],
        verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze the entire RAVL run and extract domain insights

        This looks across REFLECT, ACT, and VERIFY to identify what worked,
        what didn't, and what patterns emerged in the problem domain.

        Args:
            reflection: Output from REFLECT phase
            action_result: Output from ACT phase
            verification: Output from VERIFY phase (domain verification)

        Returns:
            Dict with synthesized insights about domain effectiveness
        """
        log_execution("Synthesizing insights from full run...", status='working')

        # Truncate large outputs for LLM consumption
        reflection_summary = self.llm_helper.truncate_for_llm(reflection, max_length=2000)
        action_summary = self.llm_helper.truncate_for_llm(action_result, max_length=2000)
        verification_summary = self.llm_helper.truncate_for_llm(verification, max_length=2000)

        # Load and format prompt
        prompt = self.llm_helper.load_prompt(
            'synthesize_run',
            reflection=json.dumps(reflection_summary, indent=2),
            action_result=json.dumps(action_summary, indent=2),
            verification=json.dumps(verification_summary, indent=2)
        )

        llm_response = self.llm.complete(prompt, max_tokens=get_max_tokens('learn_insights', 4096))

        # Parse JSON response
        try:
            insights = self.llm_helper.parse_json_response(llm_response)
        except Exception as e:
            log_message(f"Warning: Could not parse run insights: {e}", status='error')
            insights = {
                'error': 'Failed to parse insights',
                'raw_response': llm_response[:500]
            }

        log_execution("Run insights synthesized", status='success')
        return insights

    def _update_performance_metrics(self, current_verification: Optional[Dict[str, Any]] = None):
        """
        Calculate performance metrics from learning history

        Args:
            current_verification: Current verification results (for display)
        """
        history_file = self.learnings_dir / 'learning_history.jsonl'

        if not history_file.exists():
            return

        # Read all learning entries
        entries = []
        with open(history_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        if not entries:
            return

        # Calculate metrics
        total_runs = len(entries)
        passed_runs = sum(1 for e in entries if e.get('verification', {}).get('passed') is True)
        success_rate = passed_runs / total_runs if total_runs > 0 else 0.0

        # Collect recent suggestions
        recent_suggestions = []
        for entry in entries[-10:]:  # Last 10 runs
            suggestions = entry.get('verification', {}).get('suggestions', [])
            recent_suggestions.extend(suggestions)

        # Create metrics file (timestamped, append-only)
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        metrics_file = self.learnings_dir / f'metrics_{timestamp}.yml'

        metrics = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_runs': total_runs,
            'passed_runs': passed_runs,
            'success_rate': success_rate,
            'recent_suggestions': recent_suggestions[-5:]  # Last 5 suggestions
        }

        with open(metrics_file, 'w', encoding='utf-8') as f:
            yaml.dump(metrics, f, default_flow_style=False, sort_keys=False)

        log_execution(f"Metrics: {passed_runs}/{total_runs} passed ({success_rate:.1%})", status='success')

        # Display current verification details if provided and failed
        if current_verification and not current_verification.get('overall_passed', False):
            criteria_results = current_verification.get('criteria_results', [])
            if criteria_results:
                log_message("\n📋 Current Verification Details:", status='info')
                for i, criterion in enumerate(criteria_results, 1):
                    status = "✓" if criterion.get('passed', False) else "✗"
                    log_message(f"  {status} [{i}] {criterion.get('criterion', 'Unknown criterion')}", status='info', indent=4)
                    if not criterion.get('passed', False) and criterion.get('explanation'):
                        # Truncate long explanations for console readability
                        explanation = criterion['explanation']
                        if len(explanation) > 100:
                            explanation = explanation[:100] + "..."
                        log_message(explanation, status='info', indent=8)
