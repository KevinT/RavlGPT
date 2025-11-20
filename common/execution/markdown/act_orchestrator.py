#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Act Orchestrator

Handles ACT phase of RAVL cycle - code generation and execution.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Callable

# Add utils to path
_utils_dir = Path(__file__).parent.parent.parent / 'utils'
if str(_utils_dir) not in sys.path:
    sys.path.insert(0, str(_utils_dir))

from logging_utils import log_message, log_execution

# Add config to path
_config_dir = Path(__file__).parent.parent.parent / 'config'
if str(_config_dir) not in sys.path:
    sys.path.insert(0, str(_config_dir))

from config_loader import get_max_tokens

# Lazy import to avoid circular dependencies
DataIngressExecutor = None


class ActOrchestrator:
    """
    Orchestrates action phase of RAVL execution

    Responsibilities:
    - Check code cache before generation
    - Execute with DSL inference for code generation loops
    - Execute generated code (data ingress or general)
    - Save generated code artifacts
    - Process child loop directives
    """

    def __init__(
        self,
        loop_dir: Path,
        learnings_dir: Path,
        project_root: Path,
        context_vars: Dict[str, str],
        config: Dict[str, Any],
        llm_provider,
        llm_helper,
        phases_accessor: Callable[[], Dict[str, str]],
        code_generator,
        cache_manager,
        child_executor,
        simple_code_executor,
        should_attempt_code_generation_fn: Callable[[], bool],
        is_data_ingress_loop_fn: Callable[[bool], bool],
        get_available_credentials_fn: Callable[[], list]
    ):
        """
        Initialize act orchestrator

        Args:
            loop_dir: Path to loop directory
            learnings_dir: Path to learnings directory
            project_root: Path to project root
            context_vars: Context variables
            config: Loop configuration
            llm_provider: LLM provider for code generation
            llm_helper: LLMResponseHelper for prompt loading/parsing
            phases_accessor: Function to access parsed phases (lazy loaded)
            code_generator: CodeGenerator instance
            cache_manager: CodeCacheManager instance
            child_executor: ChildLoopExecutor instance
            simple_code_executor: SimpleCodeExecutor instance
            should_attempt_code_generation_fn: Function to check if code gen enabled
            is_data_ingress_loop_fn: Function to check if data ingress loop
            get_available_credentials_fn: Function to get available Notion credentials
        """
        self.loop_dir = loop_dir
        self.learnings_dir = learnings_dir
        self.project_root = project_root
        self.context_vars = context_vars
        self.config = config
        self.llm = llm_provider
        self.llm_helper = llm_helper
        self.get_phases = phases_accessor
        self.code_gen = code_generator
        self.cache_manager = cache_manager
        self.child_executor = child_executor
        self.simple_code_executor = simple_code_executor
        self.should_attempt_code_generation = should_attempt_code_generation_fn
        self.is_data_ingress_loop = is_data_ingress_loop_fn
        self.get_available_credentials = get_available_credentials_fn

        # Track generated code for learning
        self.last_generated_code = None

    def act(
        self,
        reflection: Dict[str, Any],
        build_context_fn: Callable[[Dict[str, Any]], str]
    ) -> Dict[str, Any]:
        """
        ACT phase: Execute instructions from markdown

        For data ingestion loops: infers DSL, checks cache, and generates code accordingly

        Args:
            reflection: Output from REFLECT phase
            build_context_fn: Function to build context summary

        Returns:
            Dict with action results including generated/executed code
        """
        log_message("Acting...", status='info')

        # Check cache FIRST, before any phase access (which triggers enhancement LLM call)
        skip_cache = reflection.get('skip_cache', False)

        if not skip_cache:
            cache_result = self.cache_manager.check_cache()
            if cache_result:
                # Cache hit - return immediately without accessing phases
                cached_code, cached_dsl = cache_result
                log_execution("Using cached verified code - executing...")

                timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
                action_result = {
                    'timestamp': reflection['timestamp'],
                    'context_vars': self.context_vars,
                    'output': cached_code,
                    'code_executed': False,
                    'execution_result': None,
                    'using_cached_code': True,
                    'cached_dsl': cached_dsl,
                }

                # Execute the cached code
                action_result = self._execute_generated_code(cached_code, action_result)

                # Save human-readable companion files for cached code
                if action_result.get('output'):
                    self._save_generated_code_artifacts(action_result['output'], timestamp)

                log_execution("Cached code executed", status='success')
                return action_result

        # Cache miss or cache skipped - proceed with phase parsing
        # (This triggers enhancement LLM call via lazy-loaded phases)
        phases = self.get_phases()
        act_instructions = phases.get('act', '')
        if not act_instructions:
            raise ValueError("Markdown must define an 'Act' section")

        verify_instructions = phases.get('verify', 'No verification criteria defined')

        # For loops that need code generation: use DSL-guided code generation
        if self.should_attempt_code_generation():
            return self._act_with_dsl_inference(
                act_instructions, verify_instructions, reflection, build_context_fn
            )

        # Standard act phase for non-data-ingestion loops
        # Process run_child directives first
        act_instructions, child_results = self.child_executor.process_run_child_directives(act_instructions)

        # Build context summary
        context_summary = build_context_fn(reflection)

        # Add child results to context if any were executed
        if child_results:
            context_summary += "\n\n## Child Loop Execution Results\n"
            for child_name, result in child_results.items():
                context_summary += f"\n### {child_name}\n"
                context_summary += f"```json\n{json.dumps(result, indent=2)}\n```\n"

        # Load and format prompt
        prompt = self.llm_helper.load_prompt(
            'act_phase',
            act_instructions=act_instructions,
            context_summary=context_summary,
            verify_instructions=verify_instructions
        )

        llm_response = self.llm.complete(prompt, max_tokens=get_max_tokens('act_phase_code_generation', 16384))

        # Build action result
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')

        action_result = {
            'timestamp': reflection['timestamp'],
            'context_vars': self.context_vars,
            'output': llm_response,
            'code_executed': False,
            'execution_result': None
        }

        # For loops with code generation: execute the generated code
        if self.should_attempt_code_generation():
            log_execution("Code generation detected - executing generated code...")
            action_result = self._execute_generated_code(llm_response, action_result)

        # Save human-readable companion files for generated code
        if action_result.get('output'):
            self._save_generated_code_artifacts(action_result['output'], timestamp)

        log_execution("Action phase completed", status='success')

        # Check if verification criteria specifies additional file outputs
        additional_files = self.child_executor.create_additional_outputs(
            llm_response,
            verify_instructions,
            timestamp
        )
        if additional_files:
            action_result['additional_output_files'] = additional_files

        return action_result

    def _act_with_dsl_inference(
        self,
        act_instructions: str,
        verify_instructions: str,
        reflection: Dict[str, Any],
        build_context_fn: Callable[[Dict[str, Any]], str]
    ) -> Dict[str, Any]:
        """
        ACT phase with DSL inference for code generation loops

        Delegates core logic to CodeGenerator while handling code generation,
        execution, and result persistence.

        Args:
            act_instructions: Act phase instructions from markdown
            verify_instructions: Verify phase instructions from markdown
            reflection: Output from REFLECT phase
            build_context_fn: Function to build context summary

        Returns:
            Dict with action results
        """
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')

        # Fetch Context7 docs if this is a data ingress loop
        context7_docs = None
        if self.is_data_ingress_loop(skip_phase_check=False):
            try:
                from context7_fetcher import fetch_context7_docs_for_loop
                context7_docs = fetch_context7_docs_for_loop(self.config, self.learnings_dir)
                if context7_docs:
                    log_execution(f"Fetched Context7 docs for {len(context7_docs)} API(s)", status='success')
            except Exception as e:
                log_execution(f"Failed to fetch Context7 docs: {e}", status='warning')
                context7_docs = None

        # Delegate DSL inference and code generation to CodeGenerator
        gen_result = self.code_gen.generate_with_dsl_inference(
            act_spec=act_instructions,
            verify_spec=verify_instructions,
            reflection=reflection,
            load_prompt_fn=self.llm_helper.load_prompt,
            build_context_fn=build_context_fn,
            available_credentials_fn=self.get_available_credentials,
            context7_docs=context7_docs
        )

        action_result = {
            'timestamp': reflection['timestamp'],
            'context_vars': self.context_vars,
            'output': gen_result['generated_code'],
            'code_executed': False,
            'execution_result': None,
            'inferred_dsl': gen_result['inferred_dsl'],
        }

        # Execute the generated code
        if self.should_attempt_code_generation():
            log_execution("Generated code detected - executing...")
            action_result = self._execute_generated_code(gen_result['generated_code'], action_result)

        # Save human-readable companion files for generated code
        if action_result.get('output'):
            self._save_generated_code_artifacts(action_result['output'], timestamp)

        log_execution("Code generated and executed", status='success')

        # Check if verification criteria specifies additional file outputs
        additional_files = self.child_executor.create_additional_outputs(
            gen_result['generated_code'],
            verify_instructions,
            timestamp
        )
        if additional_files:
            action_result['additional_output_files'] = additional_files

        return action_result

    def _execute_generated_code(self, generated_code: str, act_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute generated code using the appropriate executor

        For data ingestion loops: uses DataIngressExecutor (expects JSON output)
        For general loops: uses SimpleCodeExecutor (any output is fine)

        Args:
            generated_code: Generated code from LLM
            act_result: Current act result dict to update

        Returns:
            Updated act_result with execution results
        """
        try:
            # Choose appropriate executor based on loop type
            # If using cached code, skip phase check to avoid enhancement LLM call
            using_cache = act_result.get('using_cached_code', False)
            if self.is_data_ingress_loop(skip_phase_check=using_cache):
                # Data ingestion loops need JSON output
                global DataIngressExecutor
                if DataIngressExecutor is None:
                    from data_ingress_executor import DataIngressExecutor

                executor = DataIngressExecutor(self.loop_dir, self.llm)
                execution_result = executor.execute_code(generated_code, timeout=self.config.get('execution_timeout', 300))

                act_result['code_executed'] = True
                act_result['execution_result'] = execution_result
                act_result['credentials_used'] = execution_result.get('credentials_used', [])
                act_result['credential_validation_passed'] = execution_result.get('credential_validation_passed', False)

                if execution_result.get('success'):
                    log_execution("Code executed successfully - data fetched", status='success')
                    act_result['data_fetched'] = execution_result.get('data', {})
                else:
                    log_execution(f"Code execution failed: {execution_result.get('error', 'Unknown error')[:100]}", status='error')
                    act_result['execution_error'] = execution_result.get('error', 'Unknown error')
            else:
                # General loops use simple executor (file I/O, data transforms, etc.)
                execution_result = self.simple_code_executor.execute_code(generated_code, timeout=self.config.get('execution_timeout', 300))

                act_result['code_executed'] = True
                act_result['execution_result'] = execution_result

                if execution_result.get('success'):
                    log_execution("Code executed successfully", status='success')
                    if execution_result.get('stdout'):
                        log_execution(f"Output: {execution_result.get('stdout')[:200]}")
                else:
                    log_execution(f"Code execution failed: {execution_result.get('error', 'Unknown error')[:100]}", status='error')
                    act_result['execution_error'] = execution_result.get('error', 'Unknown error')

        except Exception as e:
            log_execution(f"Error executing code: {str(e)[:100]}", status='error')
            act_result['code_executed'] = False
            act_result['execution_error'] = str(e)

        return act_result

    def _save_generated_code_artifacts(self, code_content: str, timestamp: str) -> None:
        """
        Save generated code to current_state/generated_code.py

        Args:
            code_content: The generated code (may contain markdown code blocks)
            timestamp: Timestamp string (unused now, kept for compatibility)
        """
        # Extract Python code using custom delimiters (preferred) or fallback to markdown
        if '===RAVL_CODE_START===' in code_content and '===RAVL_CODE_END===' in code_content:
            # Use custom delimiters (safe from truncation)
            start_marker = '===RAVL_CODE_START==='
            end_marker = '===RAVL_CODE_END==='
            start_idx = code_content.find(start_marker) + len(start_marker)
            end_idx = code_content.find(end_marker)
            code_content = code_content[start_idx:end_idx].strip()
        elif '```python' in code_content:
            # Fallback: Extract from markdown code blocks (legacy support)
            # Split on ```python and take the part after it
            parts = code_content.split('```python')
            if len(parts) > 1:
                # Take the first code block and split on closing ```
                code_content = parts[1].split('```')[0].strip()
        elif '```' in code_content:
            # Generic code block without language specifier
            parts = code_content.split('```')
            if len(parts) > 2:
                code_content = parts[1].strip()

        # Save to current_state/ (always latest)
        current_state_dir = self.learnings_dir / 'current_state'
        current_state_dir.mkdir(parents=True, exist_ok=True)
        latest_file = current_state_dir / 'generated_code.py'
        with open(latest_file, 'w', encoding='utf-8') as f:
            f.write(code_content)

        # Store for passing to LearningManager
        self.last_generated_code = code_content
