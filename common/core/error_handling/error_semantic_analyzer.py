#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Error Semantic Analyzer

Extracts semantic meaning from execution errors and stderr output.
Works generically across any API to identify error categories and suggest strategies.
"""

import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class ErrorHint:
    """Represents a semantic error hint extracted from output"""
    category: str  # error_type: auth, resource_type, schema, rate_limit, etc.
    message: str  # Original error message
    suggestion: str  # Suggested strategy adjustment
    confidence: float  # How confident we are in this categorization (0.0-1.0)


class ErrorSemanticAnalyzer:
    """Analyzes execution errors to extract semantic meaning and strategy hints"""

    # Patterns for common error categories (API-agnostic)
    PATTERNS = {
        "resource_type": [
            # Notion-specific
            (r"is a page, not a database", "Resource is page, not database. Try page retrieval API."),
            (r"is a database, not a page", "Resource is database, not page. Try database query API."),
            # Generic
            (r"wrong.*type|type.*mismatch|invalid.*resource", "Resource type mismatch. Verify endpoint or resource ID format."),
            (r"not found|404|does not exist", "Resource not found. Verify ID or check if deleted."),
        ],
        "auth": [
            (r"unauthorized|401|forbidden|403", "Authentication or permission denied. Try alternative credentials or scope."),
            (r"invalid.*token|expired.*token|token.*invalid", "Token issue (invalid, expired, or revoked). Try refreshing credentials."),
            (r"permission.*denied|access.*denied|insufficient.*permission", "Insufficient permissions. Check scope or ask for elevated access."),
            (r"unauthenticated|not.*authenticated", "Not authenticated. Provide API key or token."),
        ],
        "schema": [
            (r"field.*not found|property.*not found|unknown.*field|no such column", "Field/property doesn't exist in schema. Use schema discovery API first."),
            (r"invalid.*field|wrong.*field|unexpected.*field", "Field validation error. Check field name or format."),
            (r"cannot.*parse|invalid.*format|malformed", "Data format error. Verify input format matches API requirements."),
            (r"required.*field|missing.*required", "Required field missing from request."),
        ],
        "rate_limit": [
            (r"rate.*limit|quota.*exceeded|too.*many.*request", "Rate limit hit. Implement exponential backoff or reduce request frequency."),
            (r"throttle", "API throttling active. Slow down requests."),
        ],
        "pagination": [
            (r"cursor.*invalid|invalid.*offset|page.*out.*of.*range", "Pagination parameter invalid. Verify cursor/offset format."),
        ],
        "network": [
            (r"connection.*timeout|timeout|timed out", "Connection timeout. Increase timeout or retry with backoff."),
            (r"connection.*refused|connection.*error", "Connection failed. Check endpoint URL and network."),
        ],
        "generic": [
            (r"error|exception|failed", "Execution failed. Review error message for details."),
        ],
    }

    @classmethod
    def analyze_error(cls, stderr: str, stdout: str, error_message: str) -> List[ErrorHint]:
        """
        Analyze execution error and extract semantic hints

        Args:
            stderr: Standard error output from code execution
            stdout: Standard output from code execution
            error_message: Error message from executor

        Returns:
            List of ErrorHint objects, sorted by confidence
        """
        hints = []

        # Combine all error sources
        combined_error = f"{error_message}\n{stderr}\n{stdout}".lower()

        # Try to match patterns in order of specificity
        # Check resource_type first (most specific)
        for category in ["resource_type", "auth", "schema", "rate_limit", "pagination", "network", "generic"]:
            patterns = cls.PATTERNS[category]

            for pattern, suggestion in patterns:
                if re.search(pattern, combined_error, re.IGNORECASE):
                    # Found a match
                    confidence = cls._calculate_confidence(category, combined_error)
                    hints.append(
                        ErrorHint(
                            category=category,
                            message=error_message[:200],  # Truncate for storage
                            suggestion=suggestion,
                            confidence=confidence,
                        )
                    )
                    # Don't break - collect all matching hints, then deduplicate

        # Remove duplicate categories, keeping highest confidence
        hints_by_category = {}
        for hint in hints:
            if hint.category not in hints_by_category or hint.confidence > hints_by_category[hint.category].confidence:
                hints_by_category[hint.category] = hint

        # Sort by confidence
        result = sorted(hints_by_category.values(), key=lambda h: h.confidence, reverse=True)

        # If nothing matched, return generic error hint
        if not result:
            result.append(
                ErrorHint(
                    category="unknown",
                    message=error_message[:200],
                    suggestion="Execution failed. Review error message and verify API documentation.",
                    confidence=0.3,
                )
            )

        return result

    @classmethod
    def _calculate_confidence(cls, category: str, error_text: str) -> float:
        """
        Calculate confidence score for error category match

        Args:
            category: Error category
            error_text: Full error text

        Returns:
            Confidence score 0.0-1.0
        """
        # Higher confidence for specific categories with clear indicators
        if category == "resource_type":
            # Very specific patterns = high confidence
            if "page" in error_text and "database" in error_text:
                return 0.95
            if "not found" in error_text or "404" in error_text:
                return 0.85
            return 0.75

        elif category == "auth":
            # Auth errors are usually very clear
            if "401" in error_text or "403" in error_text:
                return 0.95
            if "unauthorized" in error_text or "forbidden" in error_text:
                return 0.90
            if "token" in error_text or "credential" in error_text:
                return 0.85
            return 0.70

        elif category == "schema":
            # Schema errors are clear when field names are mentioned
            if "field" in error_text or "property" in error_text or "column" in error_text:
                return 0.85
            return 0.65

        elif category == "rate_limit":
            # Rate limit errors are usually very specific
            return 0.90

        elif category == "pagination":
            return 0.75

        elif category == "network":
            return 0.80

        else:  # generic
            return 0.50

    @classmethod
    def extract_stderr_messages(cls, stderr: str) -> List[str]:
        """
        Extract meaningful messages from stderr output

        Args:
            stderr: Raw stderr output

        Returns:
            List of parsed error/debug messages
        """
        messages = []

        # Split by line and extract ERROR, DEBUG, Exception messages
        for line in stderr.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Look for common log patterns
            if re.search(r"ERROR|CRITICAL|EXCEPTION", line, re.IGNORECASE):
                messages.append(line)
            elif re.search(r"is a.*not a", line):  # Specific pattern for resource type errors
                messages.append(line)
            elif "Traceback" in line:
                messages.append(line)

        return messages

    @classmethod
    def build_failure_context(
        cls, stderr: str, stdout: str, error_message: str, attempted_strategy: str = ""
    ) -> Dict[str, Any]:
        """
        Build comprehensive failure context for learning

        Args:
            stderr: Standard error output
            stdout: Standard output
            error_message: Error message from executor
            attempted_strategy: Description of what code approach was attempted

        Returns:
            Dict with failure context suitable for storage in failure_analysis.jsonl
        """
        hints = cls.analyze_error(stderr, stdout, error_message)
        stderr_messages = cls.extract_stderr_messages(stderr)

        return {
            "error_category": hints[0].category if hints else "unknown",
            "error_hints": [
                {
                    "category": hint.category,
                    "suggestion": hint.suggestion,
                    "confidence": hint.confidence,
                }
                for hint in hints[:3]  # Top 3 hints
            ],
            "error_message": error_message[:500],
            "stderr_messages": stderr_messages[:5],  # Top 5 messages
            "attempted_strategy": attempted_strategy,
        }
