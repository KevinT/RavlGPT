#!/usr/bin/env python3
"""
Code Cache Manager

Manages caching and validation of generated code.
Handles cache invalidation based on error patterns and dependency whitelists.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, List

# Import DependencyValidator for security checks
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.dependency_validator import DependencyValidator


class CodeCacheManager:
    """
    Manages code generation cache

    Responsibilities:
    - Check if verified code exists and is valid
    - Invalidate cache on repeated error patterns
    - Save verified code and DSL to cache
    - Load cached code and metadata
    """

    def __init__(self, learnings_dir: Path, loop_dir: Optional[Path] = None, project_root: Optional[Path] = None):
        """
        Initialize cache manager

        Args:
            learnings_dir: Path to learnings directory
            loop_dir: Path to loop directory (for dependency validation)
            project_root: Path to project root (for dependency validation)
        """
        self.learnings_dir = learnings_dir
        self.verified_code_file = learnings_dir / 'verified_code.py'
        self.verified_dsl_file = learnings_dir / 'verified_dsl.json'
        self.loop_dir = loop_dir
        self.project_root = project_root

    def check_cache(self) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Check if verified code exists in cache and is still valid

        Invalidates cache if:
        - Repeated error patterns detected in failure history
        - ravl_loop.md has been modified since code was cached

        Returns:
            Tuple of (code, dsl) if cache valid, else None
        """
        if not (self.verified_code_file.exists() and self.verified_dsl_file.exists()):
            return None

        # Check for repeated error categories that indicate cache should be invalidated
        if self._should_invalidate_cache():
            self._clear_cache()
            return None

        try:
            with open(self.verified_code_file, 'r') as f:
                code = f.read()

            with open(self.verified_dsl_file, 'r') as f:
                dsl = json.load(f)

            # Check if ravl_loop.md was modified since code was cached
            if self._is_markdown_loop_modified(dsl):
                self._clear_cache()
                print(f"  [i] Cache invalidated: ravl_loop.md was modified", file=sys.stderr)
                return None

            return (code, dsl)

        except (IOError, json.JSONDecodeError):
            return None

    def save_verified_code(self, code: str, dsl: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """
        Save verified code and DSL to cache when verification passes 100%

        Validates dependencies before caching.

        Args:
            code: The generated Python code that passed verification
            dsl: The DSL used to generate this code (optional)

        Returns:
            Tuple of (success, error_message)
            - If successful: (True, None)
            - If validation failed: (False, error_message)
        """
        try:
            # Clean code if needed
            if '```python' in code:
                code = re.sub(r'^```python\n|^```\n|\n```$', '', code, flags=re.MULTILINE).strip()

            # Validate dependencies if we have loop and project context
            if self.loop_dir and self.project_root:
                validator = DependencyValidator(self.loop_dir, self.project_root)
                is_valid, error_msg = validator.validate_generated_code(code)
                if not is_valid:
                    print(f"\n{error_msg}\n", file=sys.stderr)
                    return (False, error_msg)

            # Save code
            with open(self.verified_code_file, 'w') as f:
                f.write(code)

            print(f"  [✓] Cached verified code to {self.verified_code_file.name}", file=sys.stderr)

            # Save DSL if provided
            if dsl:
                # Add ravl_loop.md modification time for cache invalidation
                if self.loop_dir:
                    markdown_file = self.loop_dir / 'ravl_loop.md'
                    if markdown_file.exists():
                        dsl['ravl_loop_mtime'] = markdown_file.stat().st_mtime

                with open(self.verified_dsl_file, 'w') as f:
                    json.dump(dsl, f, indent=2)
                print(f"  [✓] Cached DSL to {self.verified_dsl_file.name}", file=sys.stderr)

            return (True, None)

        except Exception as e:
            error_msg = f"Failed to save verified code: {str(e)[:100]}"
            print(f"  [i] {error_msg}", file=sys.stderr)
            return (False, error_msg)

    def _should_invalidate_cache(self) -> bool:
        """
        Check if cache should be invalidated based on error patterns

        Invalidates if 3+ recent attempts have errors in same category
        """
        # Read from actual attempt directories
        recent_attempts_dir = self.learnings_dir / 'recent_attempts'
        if not recent_attempts_dir.exists():
            return False

        try:
            # Find all attempt_N directories and sort by N
            attempt_dirs = sorted(
                [d for d in recent_attempts_dir.iterdir() if d.is_dir() and d.name.startswith('attempt_')],
                key=lambda d: int(d.name.split('_')[1])
            )

            # Read execution results from last 5 attempts
            error_categories = {}
            for attempt_dir in attempt_dirs[-5:]:
                execution_result_file = attempt_dir / 'execution_result.json'
                if not execution_result_file.exists():
                    continue

                with open(execution_result_file, 'r') as f:
                    result = json.load(f)

                # Check if execution failed
                execution_data = result.get('execution', {})
                if not execution_data.get('passed', True):
                    # Extract error category from error_type or error_message
                    error_type = execution_data.get('error_type', 'unknown')

                    # Categorize common errors
                    error_msg = execution_data.get('error_message', '')
                    if 'ImportError' in error_msg or 'ModuleNotFoundError' in error_msg:
                        error_type = 'import_error'
                    elif 'AttributeError' in error_msg:
                        error_type = 'attribute_error'
                    elif 'TypeError' in error_msg:
                        error_type = 'type_error'

                    error_categories[error_type] = error_categories.get(error_type, 0) + 1

            # Invalidate if same error happened 3+ times
            return any(count >= 3 for count in error_categories.values())

        except (IOError, json.JSONDecodeError, KeyError, ValueError):
            return False

    def _is_markdown_loop_modified(self, cached_dsl: Dict[str, Any]) -> bool:
        """
        Check if ravl_loop.md has been modified since code was cached

        Args:
            cached_dsl: The cached DSL metadata with ravl_loop_mtime

        Returns:
            True if markdown file was modified (cache should be invalidated)
        """
        # Can't check without loop_dir
        if not self.loop_dir:
            return False

        # Check if this is a markdown loop
        markdown_file = self.loop_dir / 'ravl_loop.md'
        if not markdown_file.exists():
            return False  # Not a markdown loop, no need to invalidate

        # Get cached modification time
        cached_mtime = cached_dsl.get('ravl_loop_mtime')
        if cached_mtime is None:
            # Backward compatibility: no mtime stored in cache
            # Conservative approach: invalidate cache to be safe
            return True

        # Compare modification times
        current_mtime = markdown_file.stat().st_mtime
        return current_mtime > cached_mtime

    def _clear_cache(self) -> None:
        """Clear the cache files"""
        import sys

        try:
            if self.verified_code_file.exists():
                self.verified_code_file.unlink()
            if self.verified_dsl_file.exists():
                self.verified_dsl_file.unlink()
            print(f"  [i] Cache invalidated: repeated error patterns detected", file=sys.stderr)
        except Exception as e:
            print(f"  [i] Failed to clear cache: {str(e)[:100]}", file=sys.stderr)
