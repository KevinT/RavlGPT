#!/usr/bin/env python3
"""
Domain Cross-Loop Pattern Repository

CRITICAL: This stores PROBLEM SPACE patterns ONLY:
- Domain learning fixes that worked across loops
- Verification criteria improvements
- Domain pattern recognition strategies
- Business logic learning patterns

DO NOT store execution/solution space patterns. Use execution_pattern_repository.py instead.
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class DomainPatternRepository:
    """Manages cross-loop domain learning patterns (PROBLEM SPACE)"""

    def __init__(self, repo_path: Path):
        self.path = Path(repo_path)

    def add_pattern(self, pattern: Dict[str, Any]) -> None:
        """Add a new domain learning pattern to the repository"""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Tag pattern as domain type
        pattern["pattern_type"] = "domain"

        with open(self.path, 'a', encoding='utf-8') as f:
            json.dump(pattern, f, ensure_ascii=False)
            f.write('\n')

    def get_all_patterns(self) -> List[Dict[str, Any]]:
        """Get all domain learning patterns"""
        if not self.path.exists():
            return []

        patterns = []
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            pattern = json.loads(line)
                            # Verify it's a domain pattern
                            if pattern.get("pattern_type") == "domain":
                                patterns.append(pattern)
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        return patterns

    def get_patterns_for_loop(self, loop_name: str) -> List[Dict[str, Any]]:
        """Get domain patterns from other loops (cross-loop learning)"""
        all_patterns = self.get_all_patterns()
        return [p for p in all_patterns if p.get('source_loop') != loop_name]

    def get_patterns_by_issue_type(self, issue_type: str) -> List[Dict[str, Any]]:
        """Get domain patterns by issue type (verification/model/pattern)"""
        all_patterns = self.get_all_patterns()
        return [p for p in all_patterns if p.get('issue_type') == issue_type]

    def get_recent_patterns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent domain patterns"""
        all_patterns = self.get_all_patterns()
        return all_patterns[-limit:] if all_patterns else []
