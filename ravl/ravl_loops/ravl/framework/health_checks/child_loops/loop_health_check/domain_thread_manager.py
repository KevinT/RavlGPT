#!/usr/bin/env python3
"""
Domain Persistent Thread Manager

CRITICAL: This manages conversation threads for PROBLEM SPACE diagnostics ONLY:
- Tracks domain learning failure diagnoses over time
- Accumulates domain context (models, patterns, verification results)
- Improves domain diagnosis quality over time

DO NOT use for execution/solution space issues. Use execution_thread_manager.py instead.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any


class DomainThreadManager:
    """Manages domain diagnostic conversation history for a single loop (PROBLEM SPACE)"""

    def __init__(self, thread_path: Path):
        self.path = Path(thread_path)

    def append_turn(self, input_data: Dict[str, Any], output_data: Dict[str, Any]) -> None:
        """Append a domain diagnostic turn to the thread"""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        turn = {
            "turn_number": self._get_next_turn_number(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "diagnostic_type": "domain",  # Tag as domain diagnostic
            "input": input_data,
            "output": output_data,
        }

        with open(self.path, 'a', encoding='utf-8') as f:
            json.dump(turn, f, ensure_ascii=False)
            f.write('\n')

    def get_all_turns(self) -> List[Dict[str, Any]]:
        """Get all domain diagnostic turns from this thread"""
        if not self.path.exists():
            return []

        turns = []
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            turns.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        return turns

    def get_recent_turns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent domain diagnostic turns"""
        all_turns = self.get_all_turns()
        return all_turns[-limit:] if all_turns else []

    def format_thread_history(self, limit: int = 5) -> str:
        """Format recent thread history for LLM context"""
        recent = self.get_recent_turns(limit)
        if not recent:
            return "No previous domain diagnostics"

        formatted = ["## Previous Domain Learning Diagnostics:\n"]

        for turn in recent:
            turn_num = turn.get("turn_number", "?")
            timestamp = turn.get("timestamp", "unknown")
            root_cause = turn.get("output", {}).get("root_cause_analysis", "N/A")

            formatted.append(f"**Turn {turn_num}** ({timestamp}):")
            formatted.append(f"- Root Cause: {root_cause}")
            formatted.append("")

        return "\n".join(formatted)

    def _get_next_turn_number(self) -> int:
        """Get the next turn number for sequencing"""
        all_turns = self.get_all_turns()
        if not all_turns:
            return 1
        max_turn = max(t.get('turn_number', 0) for t in all_turns)
        return max_turn + 1
