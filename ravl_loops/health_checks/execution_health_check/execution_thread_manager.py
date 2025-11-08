#!/usr/bin/env python3
"""
Execution Persistent Thread Manager

CRITICAL: This manages conversation threads for SOLUTION SPACE diagnostics ONLY:
- Tracks execution failure diagnoses over time
- Accumulates execution context (DSL, code cache, execution errors)
- Improves execution diagnosis quality over time

DO NOT use for domain/problem space issues. Use domain_thread_manager.py instead.

Manages conversation threads for loop execution health diagnostics.
Each loop gets its own thread that grows over time, storing the complete
execution diagnostic history for that loop.

Simple file I/O wrapper around JSONL format:
- One JSON object per line
- Each line = one execution diagnostic turn (input + output)
- LLM analyzes all turns to improve execution diagnosis over time
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any


class ExecutionThreadManager:
    """
    Manages execution diagnostic conversation history for a single loop

    FOCUS: Solution space only (execution infrastructure)
    """

    def __init__(self, thread_path: Path):
        """
        Initialize execution thread manager

        Args:
            thread_path: Path to execution_thread_{loop_name}.jsonl file
        """
        self.path = Path(thread_path)

    def append_turn(self, input_data: Dict[str, Any], output_data: Dict[str, Any]) -> None:
        """
        Append an execution diagnostic turn to the thread

        Args:
            input_data: Input context for this execution diagnosis
            output_data: LLM diagnostic output for execution
        """
        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Create turn object with metadata
        turn = {
            "turn_number": self._get_next_turn_number(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "diagnostic_type": "execution",  # Tag as execution diagnostic
            "input": input_data,
            "output": output_data,
        }

        # Append as JSONL (one object per line)
        with open(self.path, 'a', encoding='utf-8') as f:
            json.dump(turn, f, ensure_ascii=False)
            f.write('\n')

    def get_all_turns(self) -> List[Dict[str, Any]]:
        """
        Get all execution diagnostic turns from this thread

        Returns:
            List of all execution turns, in chronological order
        """
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
                            # Skip malformed lines
                            continue
        except Exception:
            pass

        return turns

    def get_recent_turns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent execution diagnostic turns

        Args:
            limit: Maximum number of recent turns to return

        Returns:
            List of up to limit most recent execution turns
        """
        all_turns = self.get_all_turns()
        return all_turns[-limit:] if all_turns else []

    def format_thread_history(self, limit: int = 5) -> str:
        """
        Format recent thread history for LLM context

        Args:
            limit: Number of recent turns to format

        Returns:
            Markdown formatted history
        """
        recent = self.get_recent_turns(limit)
        if not recent:
            return "No previous execution diagnostics"

        formatted = ["## Previous Execution Diagnostics:\n"]

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
        # Get the highest turn_number and add 1
        max_turn = max(t.get('turn_number', 0) for t in all_turns)
        return max_turn + 1
