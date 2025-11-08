#!/usr/bin/env python3
"""
Execution Cross-Loop Pattern Repository

CRITICAL: This stores SOLUTION SPACE patterns ONLY:
- Execution fixes that worked across loops
- DSL convergence patterns
- Code generation patterns
- Framework infrastructure fixes

DO NOT store domain/problem space patterns. Use domain_pattern_repository.py instead.

Stores execution healing patterns discovered from all loops, making them available
as few-shot examples for the LLM to reference when diagnosing new execution issues.

Patterns accumulate over time:
- When execution health check successfully diagnoses a loop, it can extract a pattern
- Patterns are shared across all loops for execution reference
- LLM uses patterns to improve future execution diagnoses

Simple file I/O wrapper around JSONL format:
- One JSON object per line
- Each line = one execution healing pattern
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class ExecutionPatternRepository:
    """
    Manages cross-loop execution healing patterns

    FOCUS: Solution space only (execution infrastructure)
    """

    def __init__(self, repo_path: Path):
        """
        Initialize execution pattern repository

        Args:
            repo_path: Path to execution_patterns.jsonl file
        """
        self.path = Path(repo_path)

    def add_pattern(self, pattern: Dict[str, Any]) -> None:
        """
        Add a new execution healing pattern to the repository

        Args:
            pattern: Pattern dict with:
                - id: unique pattern identifier
                - pattern_type: "execution" (always)
                - source_loop: which loop this came from
                - issue_type: type of execution issue (dsl/code_generation/cache/execution_error)
                - root_cause_keywords: keywords to identify similar issues
                - solution: what worked to fix this execution issue
                - confidence: LLM confidence 0-100
                - And other metadata
        """
        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Tag pattern as execution type
        pattern["pattern_type"] = "execution"

        # Append as JSONL (one object per line)
        with open(self.path, 'a', encoding='utf-8') as f:
            json.dump(pattern, f, ensure_ascii=False)
            f.write('\n')

    def get_all_patterns(self) -> List[Dict[str, Any]]:
        """
        Get all execution healing patterns

        Returns:
            List of all execution patterns
        """
        if not self.path.exists():
            return []

        patterns = []
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            pattern = json.loads(line)
                            # Verify it's an execution pattern
                            if pattern.get("pattern_type") == "execution":
                                patterns.append(pattern)
                        except json.JSONDecodeError:
                            # Skip malformed lines
                            continue
        except Exception:
            pass

        return patterns

    def get_patterns_for_loop(self, loop_name: str) -> List[Dict[str, Any]]:
        """
        Get execution patterns relevant to a specific loop (from other loops)

        Args:
            loop_name: Name of the target loop

        Returns:
            List of execution patterns from OTHER loops
        """
        all_patterns = self.get_all_patterns()
        # Return patterns from other loops (cross-loop learning)
        return [p for p in all_patterns if p.get('source_loop') != loop_name]

    def get_patterns_by_issue_type(self, issue_type: str) -> List[Dict[str, Any]]:
        """
        Get execution patterns by issue type

        Args:
            issue_type: Type of execution issue (dsl/code_generation/cache/execution_error)

        Returns:
            List of patterns matching this issue type
        """
        all_patterns = self.get_all_patterns()
        return [p for p in all_patterns if p.get('issue_type') == issue_type]

    def get_recent_patterns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recent execution patterns

        Args:
            limit: Maximum number of patterns to return

        Returns:
            List of up to limit most recent patterns
        """
        all_patterns = self.get_all_patterns()
        return all_patterns[-limit:] if all_patterns else []
