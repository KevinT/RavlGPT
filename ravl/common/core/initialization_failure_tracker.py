#!/usr/bin/env python3
"""
Initialization Failure Tracker

Tracks failures that occur before a RAVL loop can even start executing
(discovery, import, configuration errors). These failures don't go through
the normal RAVL phases, but still need to be recorded for observability.

Philosophy:
- "If it can fail, it should be learned from"
- Capture ALL failures, even pre-initialization ones
- Make failures queryable by ravl-health
- Help users diagnose why a loop won't start
"""

import json
import traceback
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


class InitializationFailureTracker:
    """
    Tracks initialization failures for RAVL loops.

    Writes failure records to loop's learning directory even when the loop
    can't be instantiated. This enables observability for discovery/import/
    config errors.
    """

    @staticmethod
    def record_failure(
        learning_path: Path,
        error: Exception,
        phase: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Record an initialization failure to the loop's learning directory.

        Args:
            learning_path: Path to loop's learning directory
            error: The exception that was raised
            phase: Which initialization phase failed (discovery/import/config)
            context: Additional context about the failure

        Returns:
            Path to the created failure record file

        Example:
            >>> learning_path = Path("/data/learning/my_loop/learnings")
            >>> try:
            ...     import_loop_class()
            ... except ImportError as e:
            ...     InitializationFailureTracker.record_failure(
            ...         learning_path,
            ...         e,
            ...         "import",
            ...         context={"expected_class": "MyLoop", "available": ["OtherLoop"]}
            ...     )
        """
        # Ensure learning directory exists
        learning_path.mkdir(parents=True, exist_ok=True)

        # Create initialization_failures subdirectory
        failures_dir = learning_path / "initialization_failures"
        failures_dir.mkdir(exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M%S')
        failure_file = failures_dir / f"failure_{timestamp}.json"

        # Build failure record
        failure_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "failure_phase": phase,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "context": context or {}
        }

        # Write failure record
        with open(failure_file, 'w') as f:
            json.dump(failure_record, f, indent=2)

        # Keep only last 20 failures (prevent directory bloat)
        InitializationFailureTracker._cleanup_old_failures(failures_dir, keep=20)

        return failure_file

    @staticmethod
    def _cleanup_old_failures(failures_dir: Path, keep: int = 20):
        """
        Remove old failure records, keeping only the most recent.

        Args:
            failures_dir: Directory containing failure records
            keep: Number of most recent failures to keep
        """
        failure_files = sorted(
            failures_dir.glob("failure_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # Most recent first
        )

        # Delete all but the most recent 'keep' failures
        for old_file in failure_files[keep:]:
            try:
                old_file.unlink()
            except Exception:
                pass  # Ignore cleanup failures

    @staticmethod
    def get_recent_failures(learning_path: Path, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent initialization failures for a loop.

        Args:
            learning_path: Path to loop's learning directory
            limit: Maximum number of failures to return

        Returns:
            List of failure records (most recent first)

        Example:
            >>> learning_path = Path("/data/learning/my_loop/learnings")
            >>> failures = InitializationFailureTracker.get_recent_failures(learning_path)
            >>> if failures:
            ...     print(f"Last failure: {failures[0]['error_message']}")
        """
        failures_dir = learning_path / "initialization_failures"

        if not failures_dir.exists():
            return []

        # Get failure files sorted by modification time (most recent first)
        failure_files = sorted(
            failures_dir.glob("failure_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        failures = []
        for failure_file in failure_files[:limit]:
            try:
                with open(failure_file, 'r') as f:
                    failure_data = json.load(f)
                    failure_data['file'] = str(failure_file.name)
                    failures.append(failure_data)
            except Exception:
                continue  # Skip corrupted files

        return failures

    @staticmethod
    def has_recent_failures(learning_path: Path, hours: int = 24) -> bool:
        """
        Check if there are any recent initialization failures.

        Args:
            learning_path: Path to loop's learning directory
            hours: Consider failures within this many hours as "recent"

        Returns:
            True if there are failures within the specified time window
        """
        failures = InitializationFailureTracker.get_recent_failures(learning_path, limit=1)

        if not failures:
            return False

        # Check if most recent failure is within time window
        try:
            failure_time = datetime.fromisoformat(failures[0]['timestamp'])
            now = datetime.now(timezone.utc)
            age_hours = (now - failure_time).total_seconds() / 3600
            return age_hours <= hours
        except Exception:
            return True  # If we can't parse timestamp, consider it recent

    @staticmethod
    def format_failure_summary(failure: Dict[str, Any]) -> str:
        """
        Format a failure record for human-readable display.

        Args:
            failure: Failure record dictionary

        Returns:
            Formatted string suitable for terminal output
        """
        lines = []
        lines.append(f"❌ Initialization Failure ({failure['failure_phase']} phase)")
        lines.append(f"   Time: {failure['timestamp']}")
        lines.append(f"   Error: {failure['error_type']}: {failure['error_message']}")

        context = failure.get('context', {})
        if context:
            lines.append("   Context:")
            for key, value in context.items():
                if isinstance(value, list):
                    lines.append(f"     {key}: {', '.join(str(v) for v in value)}")
                else:
                    lines.append(f"     {key}: {value}")

        return '\n'.join(lines)
