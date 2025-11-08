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
                print(f"  [•] Custom code required - complex operations in loop spec", file=sys.stderr)
            return should_generate
        except Exception as e:
            # If analysis fails, default to False (safer fallback)
            print(f"  [•] Code generation decision analysis failed: {e}", file=sys.stderr)
            return False

    def generate_with_dsl_inference(
        self,
        act_spec: str,
        verify_spec: str,
        reflection: Dict[str, Any],
        load_prompt_fn,
        build_context_fn,
        available_credentials_fn=None
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

        Returns:
            Dictionary with generation result
        """
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')

        # Infer DSL from loop specification
        print(f"  [•] Inferring DSL from specification...", file=sys.stderr)
        dsl = self.dsl_engine.infer(act_spec, verify_spec)

        # Save inferred DSL for reference (pattern must match _get_next_attempt_number lookup)
        dsl_file = self.learnings_dir / f'dsl_iteration_{dsl["attempt_number"]}.json'
        with open(dsl_file, 'w') as f:
            json.dump(dsl, f, indent=2)

        # Build context summary
        context_summary = build_context_fn(reflection)

        # Load prompt template
        prompt = load_prompt_fn(
            'act_phase',
            act_instructions=act_spec,
            context_summary=context_summary,
            verify_instructions=verify_spec
        )

        # Add DSL guidance to prompt
        dsl_guidance = dsl['llm_guidance']

        # Enhance with schema-adaptive instructions if this is a Notion API loop
        if 'notion' in str(act_spec).lower():
            dsl_guidance = enhance_llm_guidance_with_schema_adaptation(dsl_guidance)

            # Add available credential names to guidance
            if available_credentials_fn:
                notion_creds = available_credentials_fn()
                if notion_creds:
                    dsl_guidance += f"\n\n## Available Credentials\n\nUse ONE of these environment variables: {', '.join(notion_creds)}\n"
                    dsl_guidance += f"Example: os.environ.get('{notion_creds[0]}')"

        prompt += f"\n\n## Code Generation DSL\n\n{dsl_guidance}"

        # Generate code
        print(f"  [•] Generating code (attempt {dsl['attempt_number']})...", file=sys.stderr)
        generated_code = self.llm.complete(prompt, max_tokens=get_max_tokens('code_generation', 16384))

        return {
            'timestamp': reflection['timestamp'],
            'generated_code': generated_code,
            'inferred_dsl': dsl,
            'dsl_file': str(dsl_file.name),
        }

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
            print(f"  [•] Caching code strategy for future attempts", file=sys.stderr)
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
            print(f"  [i] Failed to record successful strategy: {str(e)[:100]}", file=sys.stderr)

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
            print(f"  [i] Failed to generate suggestions: {str(e)[:100]}", file=sys.stderr)
            return None
