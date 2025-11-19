#!/usr/bin/env python3
"""
Execution LLM Diagnostic Analyzer

CRITICAL: This analyzer focuses ONLY on SOLUTION SPACE issues:
- HOW to make the RAVL framework execute properly
- Code generation failures
- DSL convergence problems
- Execution errors
- Framework infrastructure issues

DO NOT use this for domain/problem space issues. Use domain_llm_analyzer.py instead.

Uses an LLM to intelligently analyze execution failures and generate context-aware
diagnostic recommendations based on error messages, DSL iterations, code cache,
and learned execution patterns from previous fixes.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

# Add common directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'common'))

from llm.llm_providers import LLMProviderFactory
from config.config_loader import get_max_tokens


class ExecutionLLMAnalyzer:
    """
    Analyzes execution failures using an LLM for intelligent diagnostics

    FOCUS: Solution space only (execution infrastructure)
    """

    def __init__(self, api_key: Optional[str] = None, prompts_dir: Optional[Path] = None):
        """
        Initialize execution LLM diagnostic analyzer

        Args:
            api_key: Anthropic API key (uses env var if not provided)
            prompts_dir: Directory containing prompt files (defaults to ./config/)
        """
        # Use framework LLM provider (automatically logs to .ravl/logs/llm/)
        self.llm = LLMProviderFactory.create_provider(provider_name="anthropic", api_key=api_key)

        # Set prompts directory
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent / "config"
        self.prompts_dir = Path(prompts_dir)

        # Load unified execution health diagnostic prompt
        self.prompt_execution_diagnostic = self._load_prompt("execution_health_diagnosis.md")

    def analyze_execution_health(
        self,
        execution_context: Dict[str, Any],
        learned_patterns: Optional[List[Dict[str, Any]]] = None,
        focus_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze execution health using LLM - ALWAYS calls LLM with full context.

        Implements RAVL Principle 1: "Imperative Intent Over Declarative Configuration"
        No pre-assessment of state - LLM decides health, issues, and recommendations.

        Args:
            execution_context: Full execution context (DSL, code cache, attempts, failures, logs)
            learned_patterns: Previous successful diagnostics (few-shot learning)
            focus_area: Optional custom focus area to bias analysis (e.g., "Look for dependency conflicts")

        Returns:
            Diagnostic results with assessment, root cause, steps, and confidence
        """
        # Format comprehensive execution information for LLM
        execution_info = self._format_execution_info(execution_context)
        examples = self._format_learned_patterns(learned_patterns or [])

        # Build prompt with FULL context (not just failures!)
        prompt = self._build_diagnostic_prompt(
            execution_info=execution_info,
            learned_patterns_examples=examples,
            focus_area=focus_area
        )

        # Call LLM for comprehensive execution health analysis
        # (automatically logs to .ravl/logs/llm/ via provider)
        try:
            diagnosis_text = self.llm.complete(
                prompt=prompt,
                max_tokens=get_max_tokens('health_check_execution_analysis', 4096)
            )

            # Parse LLM response
            diagnosis = self._parse_diagnosis_response(diagnosis_text)

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "root_cause_analysis": diagnosis.get("root_cause"),
                "actionable_steps": diagnosis.get("steps", []),
                "confidence": diagnosis.get("confidence", 0.75),
                "full_analysis": diagnosis_text,
                "success": True,
            }

        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "success": False,
                "confidence": 0,
            }

    def _format_execution_info(self, execution_context: Dict[str, Any]) -> str:
        """
        Format raw execution learning files for LLM context.

        Simply dumps all files in directory structure - LLM analyzes.
        """
        parts = []

        # Basic context
        if "loop_name" in execution_context:
            parts.append(f"**Loop Name:** {execution_context['loop_name']}")

        if "loop_dir" in execution_context:
            parts.append(f"**Loop Directory:** {execution_context['loop_dir']}")

        # Raw file contents - let LLM analyze structure and content
        files = execution_context.get("files", [])
        if files:
            parts.append(f"\n**Execution Learning Files:** ({len(files)} files found)")
            parts.append("\nThe following files were found in execution_learning/. Analyze their contents to assess execution health:\n")

            for file_data in files:
                file_path = file_data.get("path", "unknown")
                contents = file_data.get("contents", "")

                parts.append(f"\n{'='*60}")
                parts.append(f"FILE: {file_path}")
                parts.append(f"{'='*60}")
                parts.append(contents)
        else:
            parts.append("\n**No execution learning files found.** Loop may not have run yet.")

        return "\n".join(parts)

    def _format_learned_patterns(self, patterns: List[Dict[str, Any]]) -> str:
        """Format previous successful execution fixes as few-shot examples"""
        if not patterns:
            return "No previous execution patterns available"

        formatted = ["## Previously Successful Execution Fixes:\n"]

        for pattern in patterns[:3]:  # Show top 3 examples
            formatted.append(f"**Pattern:** {pattern.get('id', 'unknown')}")
            formatted.append(f"- Execution Error: {pattern.get('error_summary', 'N/A')}")
            formatted.append(f"- Root Cause: {pattern.get('root_cause', 'N/A')}")
            if pattern.get("solution_steps"):
                steps = pattern["solution_steps"]
                formatted.append("- Solution Steps:")
                for step in steps[:3]:
                    formatted.append(f"  - {step}")
            formatted.append(f"- Success Rate: {pattern.get('success_count', 1)} time(s)")
            formatted.append("")

        return "\n".join(formatted)

    def _load_prompt(self, filename: str) -> str:
        """Load prompt from file"""
        prompt_file = self.prompts_dir / filename
        if not prompt_file.exists():
            raise FileNotFoundError(f"Execution prompt file not found: {prompt_file}")

        with open(prompt_file, 'r') as f:
            return f.read()

    def _build_diagnostic_prompt(
        self, execution_info: str, learned_patterns_examples: str, focus_area: Optional[str] = None
    ) -> str:
        """Build comprehensive execution health diagnostic prompt with optional focus"""
        # Build focus instruction if user provided focus area
        if focus_area:
            focus_instruction = f"""
**USER'S SPECIFIC DIAGNOSTIC CONCERN:**

The user has requested focused analysis on: "{focus_area}"

Interpret this as a diagnostic concern about the loop being analyzed. Bias your health
check to specifically investigate this area. If you find issues related to this concern,
ensure they are prominently addressed in your ROOT_CAUSE and STEPS sections.

"""
        else:
            focus_instruction = ""

        return self.prompt_execution_diagnostic.format(
            focus_instruction=focus_instruction,
            execution_info=execution_info,
            learned_patterns_examples=learned_patterns_examples
        )

    def _parse_diagnosis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse structured diagnosis response"""
        import re

        diagnosis = {
            "root_cause": None,
            "steps": [],
            "confidence": 0.5,
            "explanation": "",
        }

        # Extract sections using regex
        root_cause_match = re.search(r'ROOT_CAUSE:\s*(.+?)(?=\n(?:STEPS|CONFIDENCE|EXPLANATION):|$)', response_text, re.DOTALL)
        steps_match = re.search(r'STEPS:\s*(.+?)(?=\n(?:CONFIDENCE|EXPLANATION):|$)', response_text, re.DOTALL)
        confidence_match = re.search(r'CONFIDENCE:\s*(\d+)', response_text)
        explanation_match = re.search(r'EXPLANATION:\s*(.+?)$', response_text, re.DOTALL)

        if root_cause_match:
            diagnosis["root_cause"] = root_cause_match.group(1).strip()

        if steps_match:
            steps_text = steps_match.group(1).strip()
            diagnosis["steps"] = self._parse_steps([steps_text])

        if confidence_match:
            try:
                diagnosis["confidence"] = int(confidence_match.group(1)) / 100.0
            except ValueError:
                diagnosis["confidence"] = 0.5

        if explanation_match:
            diagnosis["explanation"] = explanation_match.group(1).strip()

        return diagnosis

    def _parse_steps(self, lines: List[str]) -> List[str]:
        """Parse numbered steps from response"""
        steps = []

        # Join all lines and split by numbered steps
        text = " ".join(line.strip() for line in lines).strip()

        # Split on numbered patterns like "1. " "2. " etc
        import re
        matches = re.split(r'\s+\d+\.\s+', text)

        for match in matches:
            if match.strip():
                steps.append(match.strip())

        return steps
