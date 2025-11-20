#!/usr/bin/env python3
"""
Code Generator

Handles LLM-guided code generation for RAVL loops using DSL inference.
Manages code generation strategies, attempt tracking, and DSL learning.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from common.config.config_loader import get_max_tokens

# Add paths for relocated modules
_script_dir = Path(__file__).parent
_common_dir = _script_dir.parent.parent
sys.path.insert(0, str(_script_dir))
sys.path.insert(0, str(_common_dir / 'core' / 'verification'))

from dsl_inference_engine import DSLInferenceEngine
from schema_adapters import enhance_llm_guidance_with_schema_adaptation

# Import logging utilities
from utils.logging_utils import log_execution


class CodeGenerator:
    """
    Orchestrates code generation for RAVL loops

    Responsibilities:
    - Determine if code generation is needed
    - Perform DSL-guided code generation
    - Handle DSL-based verification outcomes
    - Generate diagnostic suggestions
    - Track generation attempts and learning
    """

    def __init__(
        self,
        loop_dir: Path,
        learnings_dir: Path,
        llm_provider=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize code generator

        Args:
            loop_dir: Path to the loop directory
            learnings_dir: Path to learnings directory
            llm_provider: LLM provider instance
            config: Loop configuration
        """
        self.loop_dir = loop_dir
        self.learnings_dir = learnings_dir
        self.llm = llm_provider
        self.config = config or {}

        # Initialize DSL inference engine
        self.dsl_engine = DSLInferenceEngine(loop_dir, learnings_dir)

    def should_attempt_code_generation(
        self,
        act_section: str,
        verify_section: str,
        is_data_ingress_loop: bool
    ) -> bool:
        """
        Intelligently decide if code generation should be attempted

        Returns True if:
        - Loop is a data ingestion loop (existing behavior), OR
        - Loop spec suggests code generation is needed (file I/O, data transform, etc.)
        - Loop has both ACT and VERIFY sections (required for code generation)

        Args:
            act_section: Act phase content
            verify_section: Verify phase content
            is_data_ingress_loop: Whether this is a data ingestion loop

        Returns:
            True if code generation should be attempted
        """
        # Always use code generation for data ingestion loops
        if is_data_ingress_loop:
            return True

        # Check if loop has required sections
        if not act_section or not verify_section:
            return False

        # Use DSL engine to intelligently decide
        try:
            should_generate = self.dsl_engine.should_generate_code(act_section, verify_section)
            if should_generate:
                log_execution("Custom code required - complex operations in loop spec")
            return should_generate
        except Exception as e:
            # If analysis fails, default to False (safer fallback)
            log_execution(f"Code generation decision analysis failed: {e}")
            return False

    def generate_with_dsl_inference(
        self,
        act_spec: str,
        verify_spec: str,
        reflection: Dict[str, Any],
        load_prompt_fn,
        build_context_fn,
        available_credentials_fn=None,
        context7_docs: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate code using DSL inference guidance

        Args:
            act_spec: Act phase content
            verify_spec: Verify phase content
            reflection: Reflection data from RAVL phase
            load_prompt_fn: Function to load prompt templates
            build_context_fn: Function to build context summary
            available_credentials_fn: Optional function to get available credentials
            context7_docs: Optional dict mapping API names to their Context7 documentation

        Returns:
            Dictionary with generation result
        """
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')

        # Infer DSL from loop specification
        log_execution("Inferring DSL from specification...")
        dsl = self.dsl_engine.infer(act_spec, verify_spec)

        # Save inferred DSL for reference (pattern must match _get_next_attempt_number lookup)
        dsl_file = self.learnings_dir / f'dsl_iteration_{dsl["attempt_number"]}.json'
        with open(dsl_file, 'w') as f:
            json.dump(dsl, f, indent=2)

        # Build context summary
        context_summary = build_context_fn(reflection)

        # Check if this is a data ingress loop with Context7 docs
        is_data_ingress = context7_docs and len(context7_docs) > 0

        if is_data_ingress:
            # Format Context7 docs for multiple APIs
            formatted_docs = self._format_context7_docs(context7_docs)

            # Use data ingestion codegen prompt for API integration
            prompt = load_prompt_fn(
                'data_ingestion_codegen',
                context7_docs=formatted_docs,
                required_fields='(See Act section for requirements)',
                output_format='(See Verify section for expected format)',
                failure_context=''  # Can be enhanced with DSL failure history
            )

            # Add act and verify context
            prompt += f"\n\n## Loop Specification\n\n### ACT Section\n{act_spec}\n\n### VERIFY Section\n{verify_spec}"

        else:
            # Use standard act_phase prompt for non-API loops
            prompt = load_prompt_fn(
                'act_phase',
                act_instructions=act_spec,
                context_summary=context_summary,
                verify_instructions=verify_spec
            )

        # Add DSL guidance to prompt
        dsl_guidance = dsl['llm_guidance']

        # Enhance with schema-adaptive instructions if this is a Notion API loop
        detected_apis = dsl.get('act_requirements', {}).get('api_types', [])
        if 'notion' in detected_apis or 'notion' in str(act_spec).lower():
            dsl_guidance = enhance_llm_guidance_with_schema_adaptation(dsl_guidance)

            # Add available credential names to guidance
            if available_credentials_fn:
                notion_creds = available_credentials_fn()
                if notion_creds:
                    dsl_guidance += f"\n\n## Available Credentials\n\nUse ONE of these environment variables: {', '.join(notion_creds)}\n"
                    dsl_guidance += f"Example: os.environ.get('{notion_creds[0]}')"

        prompt += f"\n\n## Code Generation DSL\n\n{dsl_guidance}"

        # Generate code
        log_execution(f"Generating code (attempt {dsl['attempt_number']})...")
        generated_code = self.llm.complete(prompt, max_tokens=get_max_tokens('code_generation', 16384))

        return {
            'timestamp': reflection.get('timestamp', datetime.now(timezone.utc).isoformat()),
            'generated_code': generated_code,
            'inferred_dsl': dsl,
            'dsl_file': str(dsl_file.name),
        }

    def _format_context7_docs(self, context7_docs: Dict[str, str]) -> str:
        """
        Format Context7 documentation for multiple APIs into a single string

        Args:
            context7_docs: Dict mapping API names to their documentation

        Returns:
            Formatted documentation string with clear API sections
        """
        if not context7_docs:
            return "(No API documentation available)"

        # Single API case - just return the docs
        if len(context7_docs) == 1:
            return list(context7_docs.values())[0]

        # Multiple APIs - format with clear section headers
        sections = []
        for api_name, docs in context7_docs.items():
            sections.append(f"## {api_name.upper()} API Documentation\n\n{docs}")

        return "\n\n" + "\n\n---\n\n".join(sections)

    def handle_verification_outcome(
        self,
        verification: Dict[str, Any],
        act_result: Dict[str, Any],
        save_verified_code_fn
    ) -> None:
        """
        Handle DSL-based learning from verification outcome

        Args:
            verification: Verification result dictionary
            act_result: Act phase result with code generation info
            save_verified_code_fn: Function to save verified code to cache
        """
        # Only process if verification passed 100%
        if not verification.get('overall_passed'):
            return

        # Cache the code if it passed verification
        generated_code = act_result.get('output')
        inferred_dsl = act_result.get('inferred_dsl')

        if generated_code and inferred_dsl:
            log_execution("Caching code strategy for future attempts")
            save_verified_code_fn(generated_code, inferred_dsl)

        # Update DSL learning with successful attempt
        try:
            success_file = self.learnings_dir / 'successful_strategies.jsonl'
            with open(success_file, 'a') as f:
                entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'attempt_number': inferred_dsl.get('attempt_number'),
                    'dsl': inferred_dsl,
                    'verification_passed': verification.get('overall_passed'),
                }
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            log_execution(f"Failed to record successful strategy: {str(e)[:100]}", status='info')

    def generate_next_suggestions(
        self,
        current_dsl: Dict[str, Any],
        verification_result: Dict[str, Any],
        act_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate next DSL suggestions based on verification feedback

        Args:
            current_dsl: Current DSL that was tried
            verification_result: Result of verification
            act_result: Result of code execution

        Returns:
            Dictionary with suggested improvements or None
        """
        try:
            # Build debug context from current attempt
            debug_context = {
                'current_dsl': current_dsl,
                'verification_feedback': verification_result.get('suggestions', []),
                'execution_error': act_result.get('execution_error'),
                'attempt_number': current_dsl.get('attempt_number', 0),
            }

            # Analyze patterns to suggest next DSL
            suggestions = self.dsl_engine.suggest_next_attempt(debug_context)

            return suggestions

        except Exception as e:
            log_execution(f"Failed to generate suggestions: {str(e)[:100]}", status='info')
            return None
