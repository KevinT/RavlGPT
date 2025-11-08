#!/usr/bin/env python3
"""
Execution Learning Data Discovery

CRITICAL: This discovers data from SOLUTION SPACE (execution_learning/) ONLY:
- DSL iterations
- Code cache (verified_code.py, verified_dsl.json)
- Execution logs
- Recent execution attempts
- Execution failure analysis

DO NOT read from loop_learning/. Use domain_data_discovery.py for that.

Discovers and loads all execution learning artifacts for comprehensive health analysis.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class ExecutionDataDiscovery:
    """
    Discovers and loads execution learning data for health analysis

    FOCUS: Solution space only (execution_learning/)
    """

    def __init__(self, execution_learning_dir: Path):
        """
        Initialize execution data discovery

        Args:
            execution_learning_dir: Path to execution_learning/ directory
        """
        self.execution_dir = Path(execution_learning_dir)

    def discover_all(self) -> Dict[str, Any]:
        """
        Discover all execution learning data - reads ALL files in directory tree

        Returns:
            Dict with raw file contents
        """
        return {
            "files": self.read_all_execution_learning()
        }

    def read_all_execution_learning(self) -> List[Dict[str, Any]]:
        """
        Read all files in execution_learning directory tree.

        For recent_attempts/, only includes last 3 attempt subdirectories to limit tokens.
        For everything else, includes all files.

        Returns:
            List of dicts with 'path' (relative) and 'contents' (file text)
        """
        if not self.execution_dir.exists():
            return []

        files_data = []

        # Get list of recent_attempts subdirs to limit
        recent_attempts_dir = self.execution_dir / "recent_attempts"
        recent_attempts_to_include = set()
        if recent_attempts_dir.exists():
            attempt_dirs = sorted([d for d in recent_attempts_dir.iterdir() if d.is_dir()])
            recent_attempts_to_include = set([d.name for d in attempt_dirs[-3:]])  # Last 3 only

        # Walk entire directory tree
        for file_path in self.execution_dir.rglob('*'):
            # Skip directories
            if file_path.is_dir():
                continue

            # Get relative path
            rel_path = file_path.relative_to(self.execution_dir)

            # Check if in recent_attempts and should be skipped
            if len(rel_path.parts) >= 2 and rel_path.parts[0] == "recent_attempts":
                attempt_name = rel_path.parts[1]
                if attempt_name not in recent_attempts_to_include:
                    continue  # Skip attempts beyond last 3

            # Read file contents
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    contents = f.read()
                    files_data.append({
                        "path": str(rel_path),
                        "contents": contents
                    })
            except Exception as e:
                # Skip binary files or unreadable files
                files_data.append({
                    "path": str(rel_path),
                    "contents": f"[Could not read file: {str(e)}]"
                })

        return files_data

    def discover_dsl_iterations(self) -> Dict[str, Any]:
        """
        Discover DSL iteration files (dsl_iteration_N.json)

        Returns:
            Dict with DSL iteration data
        """
        if not self.execution_dir.exists():
            return {"found": False, "iterations": []}

        dsl_files = sorted(self.execution_dir.glob("dsl_iteration_*.json"))

        iterations = []
        for dsl_file in dsl_files:
            try:
                with open(dsl_file, 'r') as f:
                    data = json.load(f)
                    iterations.append({
                        "file": dsl_file.name,
                        "iteration": int(dsl_file.stem.split('_')[-1]),
                        "data": data
                    })
            except Exception:
                continue

        return {
            "found": len(iterations) > 0,
            "count": len(iterations),
            "iterations": iterations,
            "status": self._assess_dsl_stability(iterations)
        }

    def discover_code_cache(self) -> Dict[str, Any]:
        """
        Discover code cache (verified_code.py, verified_dsl.json)

        Returns:
            Dict with code cache status
        """
        cache_code = self.execution_dir / "verified_code.py"
        cache_dsl = self.execution_dir / "verified_dsl.json"

        result = {
            "verified_code_exists": cache_code.exists(),
            "verified_dsl_exists": cache_dsl.exists(),
        }

        if cache_code.exists():
            result["code_cache_age_days"] = self._get_file_age_days(cache_code)
            result["code_cache_size"] = cache_code.stat().st_size

        if cache_dsl.exists():
            result["dsl_cache_age_days"] = self._get_file_age_days(cache_dsl)

        result["cache_status"] = "healthy" if result["verified_code_exists"] else "missing"

        return result

    def discover_execution_logs(self) -> Dict[str, Any]:
        """
        Discover execution logs

        Returns:
            Dict with log data
        """
        logs_dir = self.execution_dir / "logs"

        if not logs_dir.exists():
            return {"found": False, "logs": []}

        log_files = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)

        logs = []
        for log_file in log_files[:5]:  # Get 5 most recent
            logs.append({
                "file": log_file.name,
                "size": log_file.stat().st_size,
                "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            })

        return {
            "found": len(logs) > 0,
            "count": len(logs),
            "logs": logs
        }

    def discover_recent_attempts(self) -> Dict[str, Any]:
        """
        Discover recent execution attempts (recent_attempts/ directory)

        Returns:
            Dict with recent attempt data
        """
        recent_dir = self.execution_dir / "recent_attempts"

        if not recent_dir.exists():
            return {"found": False, "attempts": []}

        attempt_dirs = sorted([d for d in recent_dir.iterdir() if d.is_dir()])

        attempts = []
        for attempt_dir in attempt_dirs[-10:]:  # Get 10 most recent
            result_file = attempt_dir / "execution_result.json"
            if result_file.exists():
                try:
                    with open(result_file, 'r') as f:
                        data = json.load(f)
                        attempts.append({
                            "attempt_dir": attempt_dir.name,
                            "success": data.get("passed", True),
                            "data": data
                        })
                except Exception:
                    continue

        success_count = sum(1 for a in attempts if a["success"])

        return {
            "found": len(attempts) > 0,
            "count": len(attempts),
            "success_count": success_count,
            "success_rate": success_count / len(attempts) if attempts else 0,
            "attempts": attempts
        }

    def discover_failure_analysis(self) -> Dict[str, Any]:
        """
        Discover failure analysis history (history/failure_analysis.jsonl)

        Returns:
            Dict with failure analysis data
        """
        failure_file = self.execution_dir / "history" / "failure_analysis.jsonl"

        if not failure_file.exists():
            return {"found": False, "failures": []}

        failures = []
        try:
            with open(failure_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            failures.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        return {
            "found": len(failures) > 0,
            "count": len(failures),
            "failures": failures
        }

    def discover_initialization_failures(self) -> Dict[str, Any]:
        """
        Discover initialization failures (import errors, class not found)

        Returns:
            Dict with initialization failure data
        """
        init_failure_file = self.execution_dir / "initialization_failures.jsonl"

        if not init_failure_file.exists():
            return {"found": False, "failures": []}

        failures = []
        try:
            with open(init_failure_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            failures.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        return {
            "found": len(failures) > 0,
            "count": len(failures),
            "failures": failures[-10:]  # Get 10 most recent
        }

    def _assess_dsl_stability(self, iterations: List[Dict[str, Any]]) -> str:
        """Assess DSL stability based on iteration convergence"""
        if not iterations:
            return "no_data"

        # Single iteration means DSL converged immediately (stable from start)
        if len(iterations) == 1:
            return "stable"

        # Check if recent iterations are converging
        recent = iterations[-3:] if len(iterations) > 3 else iterations

        # Simple heuristic: if we have many iterations, DSL may be unstable
        if len(iterations) > 10:
            return "unstable"
        elif len(iterations) > 5:
            return "converging"
        else:
            return "stable"

    def _get_file_age_days(self, file_path: Path) -> float:
        """Get file age in days"""
        if not file_path.exists():
            return -1

        mtime = file_path.stat().st_mtime
        age_seconds = datetime.now().timestamp() - mtime
        return age_seconds / (60 * 60 * 24)  # Convert to days
