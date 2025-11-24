#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
LLM Response Helper

Utilities for working with LLM responses and prompts.
"""

import json
from pathlib import Path
from typing import Dict, Any


class LLMResponseHelper:
    """
    Helper for LLM prompt loading and response parsing

    Responsibilities:
    - Load and format prompt templates
    - Parse JSON from LLM responses (handling markdown)
    - Truncate data structures for LLM consumption
    - Build context summaries for prompts
    """

    def __init__(self, prompts_dir: Path):
        """
        Initialize helper

        Args:
            prompts_dir: Directory containing prompt template files
        """
        self.prompts_dir = prompts_dir

    def load_prompt(self, prompt_name: str, **variables) -> str:
        """
        Load a prompt template and substitute variables

        Args:
            prompt_name: Name of prompt file (without .md extension)
            **variables: Variables to substitute in template

        Returns:
            Formatted prompt string
        """
        prompt_file = self.prompts_dir / f'{prompt_name}.md'

        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Substitute variables
        return prompt_template.format(**variables)

    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code blocks

        Args:
            response: LLM response text

        Returns:
            Parsed JSON dict

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        json_text = response.strip()

        # Remove markdown code block markers if present
        if json_text.startswith('```'):
            lines = json_text.split('\n')
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            json_text = '\n'.join(lines)

        return json.loads(json_text)

    def truncate_for_llm(self, data: Any, max_length: int = 2000) -> Any:
        """
        Truncate data structure for LLM consumption

        Recursively truncates strings in nested data structures to prevent
        token limit issues when passing data to LLMs.

        Args:
            data: Data to truncate (dict, list, str, etc.)
            max_length: Maximum string length for any value

        Returns:
            Truncated copy of data
        """
        if isinstance(data, dict):
            return {k: self.truncate_for_llm(v, max_length) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.truncate_for_llm(item, max_length) for item in data]
        elif isinstance(data, str):
            if len(data) > max_length:
                return data[:max_length] + f"... (truncated {len(data) - max_length} chars)"
            return data
        else:
            return data

    def build_context_summary(
        self,
        reflection: Dict[str, Any],
        context_vars: Dict[str, str],
        learnings_dir: Path,
        is_exploratory: bool
    ) -> str:
        """
        Build human-readable context summary from reflection

        Args:
            reflection: Reflection phase output
            context_vars: Context variables (e.g., {"current_role": "CTO"})
            learnings_dir: Path to learnings directory
            is_exploratory: Whether this is an exploratory/discovery loop

        Returns:
            Formatted context summary string
        """
        summary_parts = []

        # EXPLORATORY LOOP DETECTION (CRITICAL for cache invalidation decisions)
        if is_exploratory:
            summary_parts.append("## LOOP TYPE: EXPLORATORY/DISCOVERY")
            summary_parts.append("⚠️  This loop is designed for PROGRESSIVE DISCOVERY - each run should explore something NEW.")
            summary_parts.append("⚠️  Exploratory loops fundamentally conflict with code caching.")
            summary_parts.append("")

        # Execution History (CRITICAL for cache invalidation decisions)
        execution_learning_dir = learnings_dir / 'execution_learning'
        if execution_learning_dir.exists():
            recent_attempts_dir = execution_learning_dir / 'recent_attempts'
            if recent_attempts_dir.exists():
                attempt_count = len([d for d in recent_attempts_dir.iterdir()
                                    if d.is_dir() and d.name.startswith('attempt_')])

                if attempt_count > 0:
                    summary_parts.append("## Execution History")
                    summary_parts.append(f"- Total attempts: {attempt_count}")

                    # Check if using cached code
                    current_state_dir = execution_learning_dir / 'current_state'
                    verified_code_file = current_state_dir / 'verified_code.py'
                    if verified_code_file.exists():
                        summary_parts.append("- Status: Using CACHED CODE (same code across multiple runs)")
                        if is_exploratory:
                            summary_parts.append("  🚨 CRITICAL: Exploratory loop + cached code = repetitive exploration (NOT progressive)")
                        summary_parts.append("  ⚠️  If same error repeats, this indicates a CODE LOGIC issue, not transient failure")
                    else:
                        summary_parts.append("- Status: Generating fresh code each run")

                    # Show recent execution outcomes
                    attempt_dirs = sorted(
                        [d for d in recent_attempts_dir.iterdir() if d.is_dir() and d.name.startswith('attempt_')],
                        key=lambda d: int(d.name.split('_')[1])
                    )

                    if attempt_dirs:
                        summary_parts.append("- Recent execution results:")
                        for attempt_dir in attempt_dirs[-5:]:  # Last 5 attempts
                            attempt_num = attempt_dir.name
                            result_file = attempt_dir / 'execution_result.json'
                            if result_file.exists():
                                try:
                                    with open(result_file, 'r') as f:
                                        result = json.load(f)
                                    passed = result.get('passed', False)
                                    status = "✓" if passed else "✗"
                                    summary_parts.append(f"  {status} {attempt_num}")
                                except (IOError, json.JSONDecodeError):
                                    pass
                    summary_parts.append("")

        # Context vars
        if context_vars:
            summary_parts.append("## Context Variables")
            for key, value in context_vars.items():
                summary_parts.append(f"- {key}: {value}")
            summary_parts.append("")

        # Domain guidance from previous runs (MOST IMPORTANT)
        domain_guidance = reflection.get('domain_guidance', {})
        if domain_guidance and any(domain_guidance.values()):
            summary_parts.append("## Domain Guidance from Previous Runs")
            summary_parts.append("")
            summary_parts.append("Based on analysis of previous RAVL iterations:")
            summary_parts.append("")

            if domain_guidance.get('priority_focus'):
                summary_parts.append("### Priority Focus")
                for item in domain_guidance['priority_focus']:
                    summary_parts.append(f"- {item}")
                summary_parts.append("")

            if domain_guidance.get('successful_patterns'):
                summary_parts.append("### Patterns That Worked Well (Repeat These)")
                for pattern in domain_guidance['successful_patterns']:
                    summary_parts.append(f"- ✓ {pattern}")
                summary_parts.append("")

            if domain_guidance.get('failed_patterns'):
                summary_parts.append("### Patterns That Failed (Avoid These)")
                for pattern in domain_guidance['failed_patterns']:
                    summary_parts.append(f"- ✗ {pattern}")
                summary_parts.append("")

            if domain_guidance.get('new_strategies_to_try'):
                summary_parts.append("### New Strategies to Try")
                for strategy in domain_guidance['new_strategies_to_try']:
                    summary_parts.append(f"- → {strategy}")
                summary_parts.append("")

            if domain_guidance.get('verification_notes', {}).get('recent_failures'):
                summary_parts.append("### Recent Verification Failures")
                for failure in domain_guidance['verification_notes']['recent_failures']:
                    summary_parts.append(f"- {failure}")
                summary_parts.append("")

        # Related loops
        related = reflection.get('related_loops', {})
        if related:
            if related.get('parent'):
                summary_parts.append(f"## Parent Loop: {related['parent'].name}")
            if related.get('children'):
                summary_parts.append(f"## Child Loops: {', '.join(c.name for c in related['children'])}")
            if related.get('siblings'):
                summary_parts.append(f"## Sibling Loops: {', '.join(s.name for s in related['siblings'])}")
            summary_parts.append("")

        # Learning history summary
        learnings = reflection.get('learnings', {})
        if learnings:
            summary_parts.append("## Learning History")
            for filename, content in learnings.items():
                if isinstance(content, dict):
                    summary_parts.append(f"### {filename}")
                    # Summarize key metrics
                    if 'metrics' in content:
                        metrics = content['metrics']
                        summary_parts.append(f"- Total runs: {metrics.get('total_runs', 0)}")
                        summary_parts.append(f"- Success rate: {metrics.get('success_rate', 0):.1%}")
            summary_parts.append("")

        return "\n".join(summary_parts)
