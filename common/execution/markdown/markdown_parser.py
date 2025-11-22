#!/usr/bin/env python3
"""
Markdown RAVL Loop Parser

Handles parsing, normalization, and interpretation of markdown-defined RAVL loops.
Converts markdown into structured RAVL phases (Reflect, Act, Verify, Learn).
"""

import re
import sys
from pathlib import Path
from typing import Dict, Optional, Any

# Add utils to path for logging
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'utils'))
from logging_utils import log_execution

# Add cli to path for project root discovery
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'cli'))
from ravl_cli_base import RAVLCLIBase


class MarkdownParser:
    """
    Parses markdown into RAVL phases

    Responsibilities:
    - Parse markdown into phase sections (Act, Verify, etc.)
    - Normalize phase names (Verification → verify, Acceptance Criteria → verify)
    - Interpret free-form markdown into structured RAVL format
    - Handle loading related loop examples for context
    """

    def __init__(self, loop_dir: Path, learnings_dir: Path, llm_provider=None):
        """
        Initialize parser

        Args:
            loop_dir: Path to the loop directory
            learnings_dir: Path to learnings directory
            llm_provider: Optional LLM provider for interpreting free-form markdown
        """
        self.loop_dir = loop_dir
        self.learnings_dir = learnings_dir
        self.llm = llm_provider

    def parse_markdown(self, markdown_text: str) -> Dict[str, str]:
        """
        Parse markdown into phase sections (legacy method - no reflection context).

        Note: This method is kept for backwards compatibility but won't have access
        to fresh domain_guidance. Use parse_with_context() instead.

        Now accepts H1, H2, and H3 headings but warns on non-H1.
        """
        phases = {}
        current_phase = None
        current_content = []

        for line in markdown_text.split('\n'):
            # Check if line is a heading
            heading_info = self._extract_heading(line)
            if heading_info:
                level, heading_text = heading_info

                # Save previous phase
                if current_phase:
                    phases[current_phase] = '\n'.join(current_content).strip()

                # Warn if not H1
                if level != 1:
                    log_execution(
                        f"⚠️  Found H{level} heading '{heading_text}' (expected H1). "
                        f"Use '# {heading_text}' instead of '{'#' * level} {heading_text}'",
                        status='warning'
                    )

                # Start new phase - normalize the name
                current_phase = self._normalize_phase_name(heading_text)
                current_content = []
            else:
                current_content.append(line)

        # Save final phase
        if current_phase:
            phases[current_phase] = '\n'.join(current_content).strip()

        # Always trigger interpretation for markdown loops
        # This allows the LLM to validate, improve, and fill in missing sections
        # Well-defined loops will have minimal changes; incomplete loops will be enhanced
        if markdown_text.strip():
            if self.llm:
                try:
                    interpreted = self._interpret_free_form_markdown(markdown_text, phases)
                    # Re-parse the interpreted markdown which should now have explicit phases
                    return self._parse_markdown_internal(interpreted)
                except Exception as e:
                    log_execution(
                        f"⚠️  LLM enhancement failed: {e}. Using original markdown.",
                        status='warning'
                    )
                    # Fallback to original phases if enhancement fails
                    return phases

        return phases

    def parse_with_context(
        self,
        markdown_text: str,
        reflection: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Parse markdown into phases, enhancing with reflection context.

        If reflection provided, uses fresh domain_guidance to inform enhancement.
        Otherwise falls back to disk-based run_insights.

        Now accepts H1, H2, and H3 headings but warns on non-H1.

        Args:
            markdown_text: Raw markdown content
            reflection: Optional reflection dict with domain_guidance

        Returns:
            Dict of phase names to phase content
        """
        # First pass parse to extract existing phases
        phases = {}
        current_phase = None
        current_content = []

        for line in markdown_text.split('\n'):
            # Check if line is a heading
            heading_info = self._extract_heading(line)
            if heading_info:
                level, heading_text = heading_info

                if current_phase:
                    phases[current_phase] = '\n'.join(current_content).strip()

                # Warn if not H1
                if level != 1:
                    log_execution(
                        f"⚠️  Found H{level} heading '{heading_text}' (expected H1). "
                        f"Use '# {heading_text}' instead of '{'#' * level} {heading_text}'",
                        status='warning'
                    )

                current_phase = self._normalize_phase_name(heading_text)
                current_content = []
            else:
                current_content.append(line)

        if current_phase:
            phases[current_phase] = '\n'.join(current_content).strip()

        # Enhance with reflection context (includes fresh domain_guidance)
        if markdown_text.strip() and self.llm:
            try:
                interpreted = self._interpret_free_form_markdown(
                    markdown_text,
                    phases,
                    reflection=reflection  # Pass reflection context
                )
                # Re-parse the interpreted markdown
                return self._parse_markdown_internal(interpreted)
            except Exception as e:
                log_execution(
                    f"⚠️  LLM enhancement failed: {e}. Using original markdown.",
                    status='warning'
                )
                # Fallback to original phases if enhancement fails
                return phases

        return phases

    def _extract_heading(self, line: str) -> Optional[tuple[int, str]]:
        """
        Extract heading level and text from a markdown line.

        Handles common heading variations:
        - # Act (H1) → (1, "Act")
        - ## Act (H2) → (2, "Act")
        - ### # Act (malformed H3+H1) → (3, "Act")
        - ### Act (H3) → (3, "Act")

        Returns:
            Tuple of (level, heading_text) or None if not a heading
        """
        stripped = line.strip()
        if not stripped.startswith('#'):
            return None

        # Count leading # characters
        level = 0
        for char in stripped:
            if char == '#':
                level += 1
            elif char == ' ':
                break
            else:
                # Not a valid heading
                return None

        if level == 0:
            return None

        # Extract heading text (strip all # and spaces)
        text = stripped.lstrip('#').strip()

        return (level, text)

    def _normalize_phase_name(self, heading: str) -> str:
        """
        Normalize phase heading to canonical name

        Supports alternative names:
        - "Acceptance Criteria" → "verify"
        - "Verification" → "verify"
        """
        normalized = heading.lower().strip()

        # Map alternative names to canonical phase names
        phase_mappings = {
            'acceptance criteria': 'verify',
            'verification': 'verify',
        }

        return phase_mappings.get(normalized, normalized)

    def _parse_markdown_internal(self, markdown_text: str) -> Dict[str, str]:
        """
        Internal parse that doesn't trigger interpretation (to avoid recursion)

        Now accepts H1, H2, and H3 headings but warns on non-H1.
        """
        phases = {}
        current_phase = None
        current_content = []

        for line in markdown_text.split('\n'):
            # Check if line is a heading
            heading_info = self._extract_heading(line)
            if heading_info:
                level, heading_text = heading_info

                # Save previous phase
                if current_phase:
                    phases[current_phase] = '\n'.join(current_content).strip()

                # Warn if not H1
                if level != 1:
                    log_execution(
                        f"⚠️  Found H{level} heading '{heading_text}' (expected H1). "
                        f"Use '# {heading_text}' instead of '{'#' * level} {heading_text}'",
                        status='warning'
                    )

                # Start new phase - normalize the name
                current_phase = self._normalize_phase_name(heading_text)
                current_content = []
            else:
                current_content.append(line)

        # Save final phase
        if current_phase:
            phases[current_phase] = '\n'.join(current_content).strip()

        # Validate required phases
        self._validate_phases(phases, markdown_text)

        return phases

    def _validate_phases(self, phases: Dict[str, str], markdown_text: str) -> None:
        """
        Validate that required phases are present and provide helpful errors.

        Args:
            phases: Parsed phases dict
            markdown_text: Original markdown text for debugging
        """
        required_phases = {'act', 'verify'}
        found_phases = set(phases.keys())
        missing_phases = required_phases - found_phases

        if missing_phases:
            log_execution(
                f"⚠️  Missing required phases: {', '.join(missing_phases)}",
                status='warning'
            )

            # Check if there are headings in the markdown that weren't parsed
            has_headings = any(line.strip().startswith('#') for line in markdown_text.split('\n'))

            if has_headings and not found_phases:
                log_execution(
                    "Headings found but no phases parsed. Common issues:",
                    status='warning'
                )
                log_execution(
                    "  1. Headings must use H1 format: '# Act' not '## Act'",
                    status='warning'
                )
                log_execution(
                    "  2. Must have space after #: '# Act' not '#Act'",
                    status='warning'
                )
                log_execution(
                    "  3. Phase names must match: 'Act', 'Verify', 'Reflect', 'Learn'",
                    status='warning'
                )
            elif not has_headings:
                log_execution(
                    "No headings found in markdown. Required format:",
                    status='warning'
                )
                log_execution(
                    "  # Act",
                    status='warning'
                )
                log_execution(
                    "  [instructions]",
                    status='warning'
                )
                log_execution(
                    "  # Verify",
                    status='warning'
                )
                log_execution(
                    "  [criteria]",
                    status='warning'
                )

    def _interpret_free_form_markdown(
        self,
        raw_markdown: str,
        existing_phases: dict = None,
        reflection: dict = None
    ) -> str:
        """
        Use LLM to interpret/enhance markdown into structured RAVL phases

        Provides context from:
        - RAVL protocol documentation
        - Related loops (parent/child/sibling) as examples
        - Loop configuration
        - Existing phase sections (if any) to preserve or enhance
        - Fresh domain guidance from reflection (if available)

        Args:
            raw_markdown: The original markdown content
            existing_phases: Dict of already-parsed phase sections (e.g., {'act': '...'})
            reflection: Optional reflection dict with fresh domain_guidance
        """
        # Lazy import to avoid circular dependency issues
        from common.config.config_loader import get_max_tokens

        if not self.llm:
            raise ValueError("LLM provider required for markdown interpretation")

        import os

        # Load RAVL protocol (from framework, not project)
        framework_root = RAVLCLIBase.find_framework_root()
        protocol_file = framework_root / 'docs' / 'RAVL_PROTOCOL.md'
        protocol_text = ""
        if protocol_file.exists():
            with open(protocol_file, 'r', encoding='utf-8') as f:
                protocol_text = f.read()[:3000]  # First 3000 chars to keep context reasonable

        # Load related loop examples
        examples_text = ""

        # Check if this is a top-level parent (should be isolated from other top-level parents)
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from core.learning.learning_access_helper import LearningAccessHelper

        helper = LearningAccessHelper(self.loop_dir, self.learnings_dir)
        is_top_level = helper.is_top_level_parent()

        # Only child loops should load parent/sibling examples
        # Top-level parents must remain isolated from each other
        if not is_top_level:
            # Load parent loop example
            parent_loop = self.loop_dir.parent.parent if self.loop_dir.parent.name == 'ravl_loops' else None
            if parent_loop and (parent_loop / 'ravl_loop.md').exists():
                with open(parent_loop / 'ravl_loop.md', 'r', encoding='utf-8') as f:
                    parent_content = f.read()[:1500]
                    examples_text += f"## Parent Loop Example:\n{parent_content}\n\n"

            # Load sibling examples using proper isolation
            from execution.markdown.loop_context_builder import LoopContextBuilder
            context_builder = LoopContextBuilder(self.loop_dir, self.learnings_dir)
            related = context_builder.discover_related_loops(exclude_top_level_parents=True)

            for sibling_dir in related.get('siblings', [])[:2]:
                if (sibling_dir / 'ravl_loop.md').exists():
                    with open(sibling_dir / 'ravl_loop.md', 'r', encoding='utf-8') as f:
                        sibling_content = f.read()[:1000]
                        examples_text += f"## Similar Loop ({sibling_dir.name}):\n{sibling_content}\n\n"
        # else: Top-level parents get NO sibling examples (proper isolation)

        # Build and load prompt from template file
        prompts_dir = Path(__file__).parent / 'prompts'
        prompt_file = prompts_dir / 'interpret_freeform_markdown.md'

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        loop_name = self.loop_dir.name

        # Format existing phases for prompt context
        existing_phases_text = ""
        if existing_phases:
            existing_phases_text = "\n\n## Existing Phase Sections:\n"
            for phase_name, phase_content in existing_phases.items():
                existing_phases_text += f"\n### {phase_name.capitalize()}\n{phase_content}\n"

        # Load recent run insights from execution_learning/recent_attempts/
        run_insights_text = ""
        execution_learning_dir = self.learnings_dir / 'execution_learning'
        recent_attempts_dir = execution_learning_dir / 'recent_attempts'

        if recent_attempts_dir.exists():
            # Find all run_insights files across all attempts
            all_insights = []
            for attempt_dir in recent_attempts_dir.iterdir():
                if attempt_dir.is_dir() and attempt_dir.name.startswith('attempt_'):
                    for insights_file in attempt_dir.glob('run_insights_*.json'):
                        try:
                            import json
                            with open(insights_file, 'r', encoding='utf-8') as f:
                                insights_data = json.load(f)
                                all_insights.append((insights_file.name, insights_data))
                        except Exception:
                            pass  # Skip files that can't be read

            if all_insights:
                # Get most recent insights (sorted by timestamp in filename)
                recent_insights_file, recent_insights_data = sorted(all_insights, key=lambda x: x[0])[-1]
                insights = recent_insights_data.get('insights', {})

                # Format insights for prompt
                run_insights_text = "\n\n## Previous Run Insights\n\n"
                run_insights_text += "The following insights were learned from previous runs:\n\n"

                if insights.get('priority_focus'):
                    run_insights_text += "**Priority Focus:**\n"
                    for item in insights['priority_focus']:
                        run_insights_text += f"- {item}\n"
                    run_insights_text += "\n"

                if insights.get('successful_patterns'):
                    run_insights_text += "**Successful Patterns:**\n"
                    for item in insights['successful_patterns']:
                        run_insights_text += f"- {item}\n"
                    run_insights_text += "\n"

                if insights.get('failed_patterns'):
                    run_insights_text += "**Failed Patterns to Avoid:**\n"
                    for item in insights['failed_patterns']:
                        run_insights_text += f"- {item}\n"
                    run_insights_text += "\n"

        # Build FRESH domain guidance from reflection (if available)
        # This takes priority over disk-based run_insights
        domain_guidance_text = ""
        if reflection:
            domain_guidance = reflection.get('domain_guidance', {})

            if domain_guidance:
                domain_guidance_text = "\n\n## Fresh Domain Guidance from REFLECT Phase\n\n"
                domain_guidance_text += "Just synthesized from this REFLECT phase:\n\n"

                # Priority focus
                if domain_guidance.get('priority_focus'):
                    domain_guidance_text += "**Current Priorities:**\n"
                    for item in domain_guidance['priority_focus']:
                        domain_guidance_text += f"- {item}\n"
                    domain_guidance_text += "\n"

                # Successful patterns (to reinforce)
                if domain_guidance.get('successful_patterns'):
                    domain_guidance_text += "**Patterns That Work (use these):**\n"
                    for pattern in domain_guidance['successful_patterns']:
                        domain_guidance_text += f"- ✓ {pattern}\n"
                    domain_guidance_text += "\n"

                # Failed patterns (to avoid)
                if domain_guidance.get('failed_patterns'):
                    domain_guidance_text += "**Patterns That Failed (avoid these):**\n"
                    for pattern in domain_guidance['failed_patterns']:
                        domain_guidance_text += f"- ✗ {pattern}\n"
                    domain_guidance_text += "\n"

                # Verification issues
                verification_notes = domain_guidance.get('verification_notes', {})
                if verification_notes.get('recent_failures'):
                    domain_guidance_text += "**Recent Verification Failures:**\n"
                    for failure in verification_notes['recent_failures']:
                        domain_guidance_text += f"- ⚠️ {failure}\n"
                    domain_guidance_text += "\n"

        prompt = prompt_template.format(
            protocol_text=protocol_text,
            examples_text=examples_text,
            loop_name=loop_name,
            raw_markdown=raw_markdown,
            existing_phases=existing_phases_text,
            run_insights=run_insights_text,
            domain_guidance=domain_guidance_text  # NEW: Pass fresh domain guidance
        )

        # Call LLM
        response = self.llm.complete(prompt, max_tokens=get_max_tokens('markdown_enhancement', 4096))

        # Save enhanced version to current_state/
        current_state_dir = self.learnings_dir / 'current_state'
        current_state_dir.mkdir(parents=True, exist_ok=True)
        enhanced_file = current_state_dir / 'ravl_loop_enhanced.md'
        with open(enhanced_file, 'w', encoding='utf-8') as f:
            f.write(response)

        log_execution("Enhanced markdown saved to learnings/current_state/ravl_loop_enhanced.md")

        return response
