#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Reflection Orchestrator

Handles REFLECT phase of RAVL cycle - context gathering and synthesis.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Callable

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
from config_service import ConfigService


class ReflectionOrchestrator:
    """
    Orchestrates reflection phase of RAVL execution

    Responsibilities:
    - Gather context from learnings (this loop, parent, children, siblings)
    - Synthesize domain guidance for ACT phase
    - Check cache skip conditions
    - Coordinate with LoopContextBuilder for discovery
    """

    def __init__(
        self,
        loop_dir: Path,
        learnings_dir: Path,
        context_vars: Dict[str, str],
        llm_provider,
        llm_helper,
        context_builder,
        should_skip_cache_fn: Callable[[], tuple],
        check_has_domain_learnings_fn: Callable[[], bool],
        config_service: ConfigService = None
    ):
        """
        Initialize reflection orchestrator

        Args:
            loop_dir: Path to loop directory
            learnings_dir: Path to learnings directory
            context_vars: Context variables (e.g., {"current_role": "CTO"})
            llm_provider: LLM provider for domain synthesis
            llm_helper: LLMResponseHelper for prompt loading/parsing
            context_builder: LoopContextBuilder for loop discovery
            should_skip_cache_fn: Function to check if cache should be skipped
            check_has_domain_learnings_fn: Function to check for domain learnings
            config_service: ConfigService for accessing configuration (optional)
        """
        self.loop_dir = loop_dir
        self.learnings_dir = learnings_dir
        self.config_service = config_service
        self.context_vars = context_vars
        self.llm = llm_provider
        self.llm_helper = llm_helper
        self.context_builder = context_builder
        self.should_skip_cache_fn = should_skip_cache_fn
        self.check_has_domain_learnings_fn = check_has_domain_learnings_fn

    def reflect(self, read_learnings_fn: Callable[[Path], Dict[str, Any]]) -> Dict[str, Any]:
        """
        REFLECT phase: Automatic context gathering

        Scans all learnings from:
        - This loop's learnings/
        - Parent loop's learnings/ (if exists)
        - Child loops' learnings/ (if exist)
        - Sibling loops' learnings/ (if exist)

        Args:
            read_learnings_fn: Function to read learnings from a directory

        Returns:
            Dict with reflection context including learnings and domain guidance
        """
        log_message("Reflecting...", status='info')

        reflection = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'context_vars': self.context_vars,
            'learnings': {}
        }

        # Check for domain learnings specifically (not execution artifacts)
        has_domain_learnings = self.check_has_domain_learnings_fn()

        # Read this loop's learnings (both execution and domain)
        reflection['learnings']['this_loop'] = read_learnings_fn(self.learnings_dir)

        # Parse answered unknowns from markdown files
        answered_loop_unknowns = self._parse_answered_unknowns(
            self.learnings_dir / 'loop_learning' / 'current_state' / 'known_loop_unknowns.md'
        )
        answered_execution_unknowns = self._parse_answered_unknowns(
            self.learnings_dir / 'execution_learning' / 'current_state' / 'known_execution_unknowns.md'
        )

        # Add answered unknowns to reflection if present
        if answered_loop_unknowns or answered_execution_unknowns:
            reflection['answered_unknowns'] = {
                'domain': answered_loop_unknowns,
                'infrastructure': answered_execution_unknowns
            }
            if answered_loop_unknowns:
                from ravl.common.core.learning.known_knowns_manager import KnownKnownsManager
                knowns_manager = KnownKnownsManager(self.learnings_dir, "domain")
                total_knowns = knowns_manager.count_knowns()
                log_execution(f"Loaded {total_knowns} domain known knowns (accumulated across all runs)", status='info', indent=4)
            if answered_execution_unknowns:
                from ravl.common.core.learning.known_knowns_manager import KnownKnownsManager
                knowns_manager = KnownKnownsManager(self.learnings_dir, "execution")
                total_knowns = knowns_manager.count_knowns()
                log_execution(f"Loaded {total_knowns} execution known knowns (accumulated across all runs)", status='info', indent=4)

        # Report domain learning status to user
        if has_domain_learnings:
            log_execution("Found domain learnings from previous runs", status='info', indent=4)
        else:
            log_execution("No prior domain learnings (fresh start)", status='info', indent=4)

        # Synthesize domain guidance from this loop's learnings
        reflection['domain_guidance'] = self._synthesize_domain_context(
            reflection['learnings']['this_loop']
        )

        # Discover and read related loops
        log_execution("Discovering related loops...", status='debug', indent=4)
        related_loops = self.context_builder.discover_related_loops()

        # Check if parent learning is disabled
        disable_parent = self.config_service.get_learning_config('disable_parent_learning', False) if self.config_service else False

        if related_loops['parent']:
            if disable_parent:
                log_execution("Parent learning disabled by config", status='info', indent=4)
            else:
                parent_learnings_dir = related_loops['parent'] / 'learnings'
                reflection['learnings']['parent_loop'] = read_learnings_fn(parent_learnings_dir)
                log_execution(f"Found parent loop learnings: {related_loops['parent'].name}", status='info', indent=4)
                log_execution(f"  Parent learning path: {parent_learnings_dir}", status='debug', indent=6)

        # Check if child learning is disabled
        disable_children = self.config_service.get_learning_config('disable_child_learning', []) if self.config_service else []
        disable_all_children = disable_children is True

        if related_loops['children']:
            if disable_all_children:
                log_execution("All child learning disabled by config", status='info', indent=4)
            else:
                reflection['learnings']['child_loops'] = {}
                child_names = []
                for child_dir in related_loops['children']:
                    child_name = child_dir.name

                    # Check if this specific child is disabled
                    if isinstance(disable_children, list) and child_name in disable_children:
                        log_execution(f"Child learning disabled for {child_name}", status='info', indent=4)
                        continue

                    child_names.append(child_name)
                    child_learnings_dir = child_dir / 'learnings'
                    reflection['learnings']['child_loops'][child_name] = read_learnings_fn(child_learnings_dir)
                    log_execution(f"  Child: {child_name} at {child_learnings_dir}", status='debug', indent=6)

                if child_names:
                    log_execution(f"Found {len(child_names)} child loop(s): {', '.join(child_names)}", status='info', indent=4)

        # Check if sibling learning is disabled
        disable_siblings = self.config_service.get_learning_config('disable_sibling_learning', []) if self.config_service else []
        disable_all_siblings = disable_siblings is True

        if related_loops['siblings']:
            if disable_all_siblings:
                log_execution("All sibling learning disabled by config", status='info', indent=4)
            else:
                reflection['learnings']['sibling_loops'] = {}
                sibling_names = []
                for sibling_dir in related_loops['siblings']:
                    sibling_name = sibling_dir.name

                    # Check if this specific sibling is disabled
                    if isinstance(disable_siblings, list) and sibling_name in disable_siblings:
                        log_execution(f"Sibling learning disabled for {sibling_name}", status='info', indent=4)
                        continue

                    sibling_names.append(sibling_name)
                    sibling_learnings_dir = sibling_dir / 'learnings'
                    reflection['learnings']['sibling_loops'][sibling_name] = read_learnings_fn(sibling_learnings_dir)
                    log_execution(f"  Sibling: {sibling_name} at {sibling_learnings_dir}", status='debug', indent=6)

                if sibling_names:
                    log_execution(f"Found {len(sibling_names)} sibling loop(s): {', '.join(sibling_names)}", status='info', indent=4)
        else:
            # Check if this is a top-level parent (would explain no siblings)
            from core.learning.learning_access_helper import LearningAccessHelper
            helper = LearningAccessHelper(self.loop_dir, self.learnings_dir)
            if helper.is_top_level_parent():
                log_execution("This is a top-level parent (isolated from other top-level parents)", status='debug', indent=4)

        # Check if code caching should be skipped
        skip_cache, skip_reason = self.should_skip_cache_fn()
        if skip_cache:
            reflection['skip_cache'] = True
            reflection['skip_cache_reason'] = skip_reason
            log_execution(f"Cache will be skipped: {skip_reason}", status='info', indent=4)

        return reflection

    def _synthesize_domain_context(self, learnings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to synthesize domain learnings into actionable context for ACT

        Reads previous run insights, verification suggestions, and metrics to
        create focused guidance for the next ACT phase.

        Args:
            learnings: Raw learnings data from this loop (includes files and subdirs)

        Returns:
            Dict with synthesized domain guidance for ACT
        """
        # Extract loop_learning subdirectory data
        loop_learning_data = learnings.get('subdirs', {}).get('loop_learning', {})
        if not loop_learning_data:
            # No domain learning yet - return empty guidance
            return {
                'priority_focus': [],
                'successful_patterns': [],
                'failed_patterns': [],
                'new_strategies_to_try': [],
                'context_needs': [],
                'verification_notes': {}
            }

        log_execution("Synthesizing domain context for ACT...", status='working')

        # Extract recent run insights from execution_learning/recent_attempts/attempt_N/
        execution_learning_data = learnings.get('subdirs', {}).get('execution_learning', {})
        recent_attempts_data = execution_learning_data.get('subdirs', {}).get('recent_attempts', {})

        run_insights_files = []
        for attempt_name, attempt_data in recent_attempts_data.get('subdirs', {}).items():
            # Each attempt_N folder may contain run_insights_*.json files
            for fname in attempt_data.get('files', {}).keys():
                if fname.startswith('run_insights_'):
                    run_insights_files.append((fname, attempt_data['files'][fname]))

        recent_insights = []
        if run_insights_files:
            # Get most recent insights (sorted by timestamp in filename)
            recent_insight_file, insight_data = sorted(run_insights_files, key=lambda x: x[0])[-1]
            if isinstance(insight_data, dict):
                recent_insights = [insight_data.get('insights', {})]

        # Extract verification suggestions from recent attempts
        verification_suggestions = []
        recent_attempts = loop_learning_data.get('subdirs', {})
        for attempt_name in sorted(recent_attempts.keys(), reverse=True)[:3]:  # Last 3 attempts
            attempt_data = recent_attempts[attempt_name]
            verification_file = attempt_data.get('files', {}).get('domain_verification.json', {})
            if isinstance(verification_file, dict):
                suggestions = verification_file.get('suggestions', [])
                verification_suggestions.extend(suggestions)

        # Extract performance metrics
        metrics_files = [
            fname for fname in loop_learning_data.get('files', {}).keys()
            if fname.startswith('domain_metrics_') or fname == 'latest_metrics.yml'
        ]
        performance_metrics = {}
        if metrics_files:
            latest_metrics_file = sorted(metrics_files)[-1]
            performance_metrics = loop_learning_data['files'].get(latest_metrics_file, {})

        # Extract historical patterns from history subdirectory
        history_data = loop_learning_data.get('subdirs', {}).get('history', {})
        historical_patterns = {
            'failures': history_data.get('files', {}).get('domain_failures.jsonl', ''),
            'successes': history_data.get('files', {}).get('domain_successes.jsonl', ''),
            'evolution': history_data.get('files', {}).get('pattern_evolution.jsonl', '')
        }

        # Load and format prompt
        prompt = self.llm_helper.load_prompt(
            'synthesize_domain_learnings',
            run_insights=json.dumps(recent_insights, indent=2) if recent_insights else 'No previous run insights',
            verification_suggestions=json.dumps(verification_suggestions, indent=2) if verification_suggestions else 'No verification suggestions',
            performance_metrics=json.dumps(performance_metrics, indent=2) if performance_metrics else 'No performance metrics',
            historical_patterns=json.dumps(historical_patterns, indent=2) if historical_patterns else 'No historical patterns'
        )

        llm_response = self.llm.complete(prompt, max_tokens=get_max_tokens('domain_context_synthesis', 4096))

        # Parse JSON response
        try:
            domain_guidance = self.llm_helper.parse_json_response(llm_response)
        except Exception as e:
            log_message(f"Warning: Could not parse domain guidance: {e}", status='error')
            domain_guidance = {
                'priority_focus': [],
                'successful_patterns': [],
                'failed_patterns': [],
                'new_strategies_to_try': [],
                'context_needs': [],
                'verification_notes': {},
                'error': f'Failed to parse guidance: {e}'
            }

        log_execution("Domain context synthesized", status='success')
        return domain_guidance

    def _parse_answered_unknowns(self, md_file: Path) -> Dict[str, str]:
        """
        Parse markdown file to extract answered questions, save to known_knowns.jsonl,
        and return ALL accumulated known knowns (current + historical).

        Args:
            md_file: Path to known_unknowns.md file

        Returns:
            Dict mapping questions to answers (all accumulated knowns)
        """
        from ravl.common.core.learning.known_knowns_manager import KnownKnownsManager

        # Determine category based on file path
        category = "domain" if "loop_learning" in str(md_file) else "execution"

        # Always load existing known knowns first
        knowns_manager = KnownKnownsManager(self.learnings_dir, category)

        # If file doesn't exist, just return existing knowns
        if not md_file.exists():
            return knowns_manager.get_all_knowns()

        # Parse current markdown file for NEW answers
        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception as e:
            log_message(f"Failed to read {md_file.name}: {e}", status='warning')
            return knowns_manager.get_all_knowns()

        # Parse markdown to extract Q&A pairs with "Answered by" metadata
        new_answers = {}  # question -> (answer, answered_by)
        lines = content.split('\n')
        current_question = None
        current_answer = None
        current_answered_by = None

        for line in lines:
            # Question headers: "## Question N"
            if line.startswith('## Question'):
                # Save previous Q&A if complete
                if current_question and current_answer:
                    answered_by = current_answered_by if current_answered_by else "human"
                    new_answers[current_question] = (current_answer, answered_by)

                # Reset for new question
                current_question = None
                current_answer = None
                current_answered_by = None
                continue

            # Question text (non-empty line after "## Question")
            if current_question is None and line.strip() and not line.startswith('**') and not line.startswith('---'):
                current_question = line.strip()
                continue

            # Answer line: "**Answer**: actual answer text"
            if line.startswith('**Answer**:'):
                answer = line.replace('**Answer**:', '').strip()
                # Only include if answer is not placeholder
                if answer and not answer.startswith('_[Fill in'):
                    current_answer = answer
                continue

            # Answered by line: "**Answered by**: name or identifier"
            if line.startswith('**Answered by**:'):
                answered_by_raw = line.replace('**Answered by**:', '').strip()
                # Skip placeholder text
                if not answered_by_raw.startswith('_['):
                    current_answered_by = answered_by_raw
                continue

        # Don't forget last question
        if current_question and current_answer:
            answered_by = current_answered_by if current_answered_by else "human"
            new_answers[current_question] = (current_answer, answered_by)

        # Save NEW answers to known_knowns.jsonl
        if new_answers:
            for question, (answer, answered_by) in new_answers.items():
                knowns_manager.add_known_known(
                    question=question,
                    answer=answer,
                    answered_by=answered_by
                )

        # Return ALL accumulated knowns (historical + current)
        return knowns_manager.get_all_knowns()
