#!/usr/bin/env python3
"""
Domain Learning Data Discovery

CRITICAL: This discovers data from PROBLEM SPACE (loop_learning/) ONLY:
- Domain models (model.yml, model-*.yml)
- Verification results
- Domain metrics
- Learned domain patterns
- Domain attempt history

DO NOT read from execution_learning/. Use execution_data_discovery.py for that.
"""

import json
import toml
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class DomainDataDiscovery:
    """Discovers and loads domain learning data for health analysis (PROBLEM SPACE)"""

    def __init__(self, loop_learning_dir: Path):
        self.loop_learning_dir = Path(loop_learning_dir)

    def discover_all(self) -> Dict[str, Any]:
        """
        Discover all domain learning data - reads ALL files in directory tree

        Returns:
            Dict with raw file contents
        """
        return {
            "files": self.read_all_loop_learning()
        }

    def read_all_loop_learning(self) -> List[Dict[str, Any]]:
        """
        Read all files in loop_learning directory tree.

        For recent_attempts/, only includes last 3 attempt subdirectories to limit tokens.
        For everything else, includes all files.

        Returns:
            List of dicts with 'path' (relative) and 'contents' (file text)
        """
        if not self.loop_learning_dir.exists():
            return []

        files_data = []

        # Get list of recent_attempts subdirs to limit
        recent_attempts_dir = self.loop_learning_dir / "recent_attempts"
        recent_attempts_to_include = set()
        if recent_attempts_dir.exists():
            attempt_dirs = sorted([d for d in recent_attempts_dir.iterdir() if d.is_dir()])
            recent_attempts_to_include = set([d.name for d in attempt_dirs[-3:]])  # Last 3 only

        # Walk entire directory tree
        for file_path in self.loop_learning_dir.rglob('*'):
            # Skip directories
            if file_path.is_dir():
                continue

            # Get relative path
            rel_path = file_path.relative_to(self.loop_learning_dir)

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

    def discover_domain_models(self) -> Dict[str, Any]:
        """Discover domain model files (model.yml, model-*.yml)"""
        if not self.loop_learning_dir.exists():
            return {"found": False, "models": []}

        # Current model
        current_model_file = self.loop_learning_dir / "model.yml"

        # Historical models
        model_files = sorted(self.loop_learning_dir.glob("model-*.yml"))

        models = []
        current_model = None

        if current_model_file.exists():
            try:
                with open(current_model_file, 'r') as f:
                    current_model = toml.load(f)
            except Exception:
                pass

        for model_file in model_files:
            try:
                with open(model_file, 'r') as f:
                    data = toml.load(f)
                    models.append({
                        "file": model_file.name,
                        "timestamp": model_file.stem.split('-', 1)[1] if '-' in model_file.stem else "unknown",
                        "data": data
                    })
            except Exception:
                continue

        return {
            "found": current_model is not None or len(models) > 0,
            "current_model": current_model,
            "historical_count": len(models),
            "models": models,
            "evolution_status": self._assess_model_evolution(current_model, models)
        }

    def discover_verification_results(self) -> Dict[str, Any]:
        """Discover verification result files"""
        if not self.loop_learning_dir.exists():
            return {"found": False, "results": []}

        verification_files = sorted(self.loop_learning_dir.glob("verification_*.yml"), key=lambda p: p.stat().st_mtime, reverse=True)

        results = []
        for verification_file in verification_files[:10]:  # Get 10 most recent
            try:
                with open(verification_file, 'r') as f:
                    data = toml.load(f)
                    results.append({
                        "file": verification_file.name,
                        "passed": data.get("overall_passed", False),
                        "data": data
                    })
            except Exception:
                continue

        pass_count = sum(1 for r in results if r["passed"])

        return {
            "found": len(results) > 0,
            "count": len(results),
            "pass_count": pass_count,
            "pass_rate": pass_count / len(results) if results else 0,
            "results": results
        }

    def discover_domain_metrics(self) -> Dict[str, Any]:
        """Discover domain metrics from history/"""
        metrics_file = self.loop_learning_dir / "history" / "domain_metrics.jsonl"

        if not metrics_file.exists():
            return {"found": False, "metrics": []}

        metrics = []
        try:
            with open(metrics_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            metrics.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        return {
            "found": len(metrics) > 0,
            "count": len(metrics),
            "metrics": metrics[-20:]  # Get 20 most recent
        }

    def discover_learned_patterns(self) -> Dict[str, Any]:
        """Discover learned domain patterns"""
        patterns_file = self.loop_learning_dir / "learned_patterns.jsonl"

        if not patterns_file.exists():
            return {"found": False, "patterns": []}

        patterns = []
        try:
            with open(patterns_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            patterns.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        return {
            "found": len(patterns) > 0,
            "count": len(patterns),
            "patterns": patterns
        }

    def discover_recent_attempts(self) -> Dict[str, Any]:
        """Discover recent domain learning attempts"""
        recent_dir = self.loop_learning_dir / "recent_attempts"

        if not recent_dir.exists():
            return {"found": False, "attempts": []}

        attempt_dirs = sorted([d for d in recent_dir.iterdir() if d.is_dir()])

        attempts = []
        for attempt_dir in attempt_dirs[-10:]:  # Get 10 most recent
            verification_file = attempt_dir / "domain_verification.json"
            if verification_file.exists():
                try:
                    with open(verification_file, 'r') as f:
                        data = json.load(f)
                        attempts.append({
                            "attempt_dir": attempt_dir.name,
                            "passed": data.get("overall_passed", False),
                            "data": data
                        })
                except Exception:
                    continue

        pass_count = sum(1 for a in attempts if a["passed"])

        return {
            "found": len(attempts) > 0,
            "count": len(attempts),
            "pass_count": pass_count,
            "pass_rate": pass_count / len(attempts) if attempts else 0,
            "attempts": attempts
        }

    def _assess_model_evolution(self, current_model: Optional[Dict[str, Any]], historical_models: List[Dict[str, Any]]) -> str:
        """Assess model evolution based on version history"""
        if not current_model and not historical_models:
            return "no_data"

        if not historical_models or len(historical_models) < 2:
            return "insufficient_history"

        # Check if model is growing (evolving) or stagnant
        if len(historical_models) > 10:
            return "actively_evolving"
        elif len(historical_models) > 3:
            return "evolving"
        else:
            return "stagnant"
