#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Verification Manager

Handles VERIFY phase of RAVL cycle - both execution and domain verification.
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable

# Add utils to path
_utils_dir = Path(__file__).parent.parent.parent / 'utils'
if str(_utils_dir) not in sys.path:
    sys.path.insert(0, str(_utils_dir))

from logging_utils import log_message, log_verification_error, log_execution

# Add config to path
_config_dir = Path(__file__).parent.parent.parent / 'config'
if str(_config_dir) not in sys.path:
    sys.path.insert(0, str(_config_dir))

from config_loader import get_max_tokens


class VerificationManager:
    """
    Manages verification phase of RAVL execution

    Responsibilities:
    - Verify execution (infrastructure): did code run successfully?
    - Verify domain (problem space): did it solve the problem?
    - Extract execution warnings from stderr
    - Handle DSL verification outcomes (cache/failure)
    """

    def __init__(
        self,
        llm_provider,
        llm_helper,
        phases_accessor: Callable[[], Dict[str, str]],
        code_generator,
        should_attempt_code_generation: Callable[[], bool]
    ):
        """
        Initialize verification manager

        Args:
            llm_provider: LLM provider for domain verification
            llm_helper: LLMResponseHelper for prompt loading/parsing
            phases_accessor: Function to access parsed markdown phases (lazy loaded)
            code_generator: CodeGenerator instance for handling verification outcomes
            should_attempt_code_generation: Function that returns whether code gen is enabled
        """
        self.llm = llm_provider
        self.llm_helper = llm_helper
        self.get_phases = phases_accessor
        self.code_gen = code_generator
        self.should_attempt_code_generation = should_attempt_code_generation

    def verify(
        self,
        action_result: Optional[Dict[str, Any]],
        current_reflection: Dict[str, Any],
        save_verified_code_fn: Callable[[str, Optional[Dict[str, Any]]], None]
    ) -> Dict[str, Any]:
        """
        VERIFY phase: Check both execution and domain independently

        Args:
            action_result: Output from ACT phase
            current_reflection: Output from REFLECT phase
            save_verified_code_fn: Function to save verified code to cache

        Returns:
            Dict with 'execution' and 'domain' keys containing separate verification results
        """
        log_message("Verifying...", status='info')

        # EXECUTION VERIFICATION: Did code run successfully?
        execution_verification = self._verify_execution(action_result)

        # DOMAIN VERIFICATION: Did it solve the problem?
        domain_verification = self._verify_domain(action_result, current_reflection)

        # DSL-based learning: cache successful code or save failure analysis
        if self.should_attempt_code_generation() and action_result:
            self._handle_dsl_verification_outcome(
                execution_verification,
                domain_verification,
                action_result,
                save_verified_code_fn
            )

        # Combined result
        return {
            'execution': execution_verification,
            'domain': domain_verification,
            'overall_passed': execution_verification['passed'] and domain_verification.get('overall_passed', True),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def _verify_execution(self, action_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify execution infrastructure: did code run successfully?

        This is SOLUTION LEARNING - checking if infrastructure works.

        Args:
            action_result: Output from ACT phase

        Returns:
            Dict with execution verification results
        """
        if not action_result:
            return {'passed': True, 'message': 'No execution to verify'}

        # Check if code was executed (for any loop type)
        if action_result.get('code_executed'):
            execution_result = action_result.get('execution_result', {})

            # Check credentials (only for data ingress loops that explicitly validate)
            # SimpleCodeExecutor doesn't set this field, so only check if present
            if 'credential_validation_passed' in execution_result:
                if not execution_result.get('credential_validation_passed', False):
                    error_msg = execution_result.get('error', 'Missing credentials')
                    log_verification_error('Credential validation failed', error_msg, max_length=150)
                    return {
                        'passed': False,
                        'error_type': 'credential_validation',
                        'error_message': error_msg,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }

            # Check execution success
            if not execution_result.get('success', False):
                error_msg = execution_result.get('error', 'Execution failed')
                # Extract meaningful error message (show last line if multiline)
                error_preview = error_msg[:200] if error_msg else 'Unknown error'
                if '\n' in error_preview:
                    error_preview = error_preview.split('\n')[-1]  # Show last line of error
                log_verification_error('Code execution failed', error_preview, max_length=200)
                return {
                    'passed': False,
                    'error_type': execution_result.get('error_type', 'execution_error'),
                    'error_message': error_msg,
                    'exit_code': execution_result.get('exit_code'),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }

            # Execution succeeded - check for warnings even on success
            stderr = execution_result.get('stderr', '')
            warnings = self._extract_execution_warnings(stderr)

            return {
                'passed': True,
                'execution_time': execution_result.get('execution_time'),
                'has_warnings': len(warnings) > 0,
                'warnings': warnings,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        # No code execution, consider it passed
        return {'passed': True, 'message': 'No code execution to verify'}

    def _extract_execution_warnings(self, stderr: str) -> list:
        """
        Extract warnings from stderr (deprecations, future warnings, etc.)

        Args:
            stderr: The stderr output from code execution

        Returns:
            List of warning dictionaries with type, message, and api fields
        """
        warnings = []

        if not stderr:
            return warnings

        # Extract DeprecationWarnings
        deprecation_pattern = r'DeprecationWarning: (.+?) is deprecated'
        for match in re.finditer(deprecation_pattern, stderr):
            warnings.append({
                'type': 'deprecation',
                'message': match.group(0),
                'api': match.group(1).strip()
            })

        # Extract FutureWarnings
        future_pattern = r'FutureWarning: (.+?)(?:\n|$)'
        for match in re.finditer(future_pattern, stderr):
            warnings.append({
                'type': 'future',
                'message': match.group(0).strip()
            })

        return warnings

    def _verify_domain(
        self,
        action_result: Optional[Dict[str, Any]],
        current_reflection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify domain criteria: did it solve the problem?

        This is LOOP LEARNING - checking if domain requirements met.

        Args:
            action_result: Output from ACT phase
            current_reflection: Output from REFLECT phase

        Returns:
            Dict with domain verification results
        """
        phases = self.get_phases()
        verify_instructions = phases.get('verify', '')
        if not verify_instructions:
            log_execution("No verification criteria defined, skipping", status='info', indent=4)
            return {
                'overall_passed': True,
                'message': 'No verification criteria defined',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        if not action_result:
            log_execution("No action result to verify", status='info', indent=4)
            return {
                'overall_passed': None,
                'message': 'No action result available for verification',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        # Load and format prompt
        prompt = self.llm_helper.load_prompt(
            'verify_phase',
            verify_instructions=verify_instructions,
            action_result=json.dumps(action_result, indent=2),
            current_context=self.llm_helper.build_context_summary(
                current_reflection,
                {},  # context_vars passed separately
                Path(),  # learnings_dir passed separately
                False  # is_exploratory passed separately
            )
        )

        llm_response = self.llm.complete(prompt, max_tokens=get_max_tokens('verification', 4096))

        # Parse LLM response (handle markdown code blocks)
        json_text = llm_response.strip()

        # Remove markdown code block markers if present
        if json_text.startswith('```'):
            lines = json_text.split('\n')
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            json_text = '\n'.join(lines)

        try:
            verification = json.loads(json_text)
        except json.JSONDecodeError:
            # If still can't parse, try to extract suggestions from raw text
            suggestions = []
            if 'suggestions' in llm_response.lower():
                # Try to extract suggestions list from text
                suggestion_match = re.search(r'"suggestions"\s*:\s*\[(.*?)\]', llm_response, re.DOTALL)
                if suggestion_match:
                    suggestions_text = suggestion_match.group(1)
                    # Extract individual suggestions
                    for match in re.finditer(r'"([^"]+)"', suggestions_text):
                        suggestions.append(match.group(1))

            verification = {
                'overall_passed': False,
                'raw_evaluation': llm_response,
                'error': 'Could not parse verification as JSON',
                'suggestions': suggestions
            }

        verification['timestamp'] = datetime.now(timezone.utc).isoformat()

        log_execution("Verification complete", status='success')
        return verification

    def _handle_dsl_verification_outcome(
        self,
        execution_verification: Dict[str, Any],
        domain_verification: Dict[str, Any],
        action_result: Dict[str, Any],
        save_verified_code_fn: Callable[[str, Optional[Dict[str, Any]]], None]
    ) -> None:
        """
        Handle DSL learning: delegate to CodeGenerator

        CodeGenerator handles caching successful code and failure analysis.
        Only uses execution verification (not domain).

        Args:
            execution_verification: Execution verification results
            domain_verification: Domain verification results (for context)
            action_result: Output from ACT phase
            save_verified_code_fn: Function to save verified code to cache
        """
        self.code_gen.handle_verification_outcome(
            verification=execution_verification,
            act_result=action_result,
            save_verified_code_fn=save_verified_code_fn
        )
