# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
RAVL Loop Protocol

This module defines the Protocol (interface) that all RAVL loops must implement.
Using Python's Protocol for structural typing (duck typing) rather than ABC
inheritance, so loops naturally implementing these methods are compatible.

This supports:
- Python classes implementing the protocol directly
- Future markdown-based loops via an executor wrapper
- Any object with the right method signatures

See ../docs/RAVL_PROTOCOL.md for full specification.
"""

from typing import Protocol, Dict, Any, Optional


class RAVLLoop(Protocol):
    """
    Protocol defining the RAVL (Reflect-Act-Verify-Learn) loop interface.

    All RAVL loops must implement these four phases:
    1. reflect() - Pure observation and data gathering
    2. act() - Decision making and actions based on reflection
    3. verify() - Outcome verification against previous actions
    4. learn() - Model updates based on verification

    This is a Protocol, not an ABC, so classes don't need to explicitly
    inherit from it - any class with these methods is compatible.
    """

    def reflect(self) -> Dict[str, Any]:
        """
        REFLECT Phase: Pure observation and data gathering

        Responsibilities:
        - Gather raw data about current state
        - Compute state signatures/hashes for change detection
        - Load learned context from previous runs
        - Prepare observations for Act phase

        Anti-patterns:
        - Making decisions or selecting strategies
        - Analyzing or interpreting data
        - Modifying state

        Returns:
            Dict containing observations about current state

        Example:
            {
                "timestamp": "2025-10-04T12:00:00+00:00",
                "state_hash": "abc123...",
                "files_found": 64,
                "learned_context": {...}
            }
        """
        ...

    def act(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        """
        ACT Phase: Make decisions and take actions based on reflection

        Responsibilities:
        - Select strategies/approaches using learned intelligence
        - Perform analysis (LLM calls, comparisons, etc.)
        - Generate findings/gaps/recommendations
        - Return structured results

        Anti-patterns:
        - Re-gathering data (use reflection)
        - Learning/updating models (save for Learn phase)
        - Verification (save for Verify phase)

        Args:
            reflection: Output from reflect() phase

        Returns:
            Dict containing actions taken and results

        Example:
            {
                "strategy_used": {"name": "broad_survey", "reasoning": "..."},
                "gaps_found": [...],
                "metadata": {"llm_calls": 3, "tokens_used": 12000}
            }
        """
        ...

    def verify(
        self,
        previous_action: Optional[Dict[str, Any]],
        current_reflection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        VERIFY Phase: Check if previous actions achieved intended outcomes

        Responsibilities:
        - Compare previous issues with current state
        - Detect which issues were fixed (disappeared)
        - Detect which issues were ignored (still present)
        - Identify false positives (flagged but not real)
        - Calculate verification metrics

        Important: Reuses reflection from Act phase - does NOT re-reflect!

        Anti-patterns:
        - Updating models (save for Learn phase)
        - Re-running reflection
        - Taking new actions

        Args:
            previous_action: Results from previous run's act() phase (or None for first run)
            current_reflection: Current reflection (reused from act() phase)

        Returns:
            Dict containing verification results

        Example:
            {
                "outcomes": {
                    "fixed": ["GAP-001"],
                    "ignored": ["GAP-002"],
                    "false_positives": ["GAP-003"]
                },
                "fix_rate": 0.5,
                "precision": 0.75
            }
        """
        ...

    def learn(
        self,
        verification: Dict[str, Any],
        action_result: Dict[str, Any]
    ) -> None:
        """
        LEARN Phase: Update model based on verification outcomes

        Responsibilities:
        - Update learned weights based on what worked
        - Adjust strategy selection based on outcomes
        - Identify and record false positive patterns
        - Update performance metrics
        - Persist updated model

        Anti-patterns:
        - Taking new actions
        - Re-analyzing data
        - Writing to other loops' models

        Args:
            verification: Output from verify() phase
            action_result: Output from act() phase

        Returns:
            None (updates self.model in place and persists to disk)
        """
        ...


# Type alias for optional RAVL loops (used in parent coordination)
OptionalRAVLLoop = Optional[RAVLLoop]


def is_ravl_loop(obj: Any) -> bool:
    """
    Check if an object implements the RAVL loop protocol.

    Useful for runtime validation when coordinating loops.

    Args:
        obj: Object to check

    Returns:
        True if object has all required RAVL methods
    """
    required_methods = ['reflect', 'act', 'verify', 'learn']
    return all(
        hasattr(obj, method) and callable(getattr(obj, method))
        for method in required_methods
    )


def validate_ravl_loop(obj: Any, loop_name: str = "loop") -> None:
    """
    Validate that an object implements the RAVL loop protocol.

    Raises TypeError if object doesn't implement required methods.

    Args:
        obj: Object to validate
        loop_name: Name for error messages

    Raises:
        TypeError: If object doesn't implement RAVL protocol
    """
    if not is_ravl_loop(obj):
        missing = [
            method for method in ['reflect', 'act', 'verify', 'learn']
            if not (hasattr(obj, method) and callable(getattr(obj, method)))
        ]
        raise TypeError(
            f"{loop_name} must implement RAVLLoop protocol. "
            f"Missing methods: {', '.join(missing)}"
        )
