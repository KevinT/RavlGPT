"""
Prompt Normalizer - Deterministic prompt deduplication system.

Reduces LLM token consumption by detecting repeated text blocks within a single
prompt, keeping one canonical copy, and replacing duplicates with concise references.

Key principles:
- Deterministic (identical input → identical output)
- Semantic preservation (no meaning changes)
- Locality (all references within same prompt)
- Safety first (protected content never modified)
- Performance (<50ms for typical prompts)
"""

import hashlib
import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class BlockType(Enum):
    """Types of blocks in a prompt."""
    HEADING = "heading"         # ## Section Title
    CODE = "code"              # ```...```
    PARAGRAPH = "paragraph"     # Regular text
    PROTECTED = "protected"     # {placeholders}, JSON, dynamic content


@dataclass
class Block:
    """Represents a segment of the prompt."""
    content: str           # Original text
    normalized: str        # Whitespace-normalized for comparison
    block_type: BlockType  # Type of block
    heading: Optional[str] # Section heading if available
    start_pos: int        # Position in original prompt
    end_pos: int          # End position
    is_protected: bool    # Whether this block should never be deduped

    def hash_key(self) -> str:
        """Generate hash for duplicate detection."""
        return hashlib.sha256(self.normalized.encode()).hexdigest()


class PromptNormalizer:
    """
    Deterministic prompt deduplication system.

    Detects repeated blocks within a single prompt, marks the first
    occurrence as canonical, and replaces subsequent occurrences with
    concise references.
    """

    def __init__(self, min_block_size: int = 200, enable_logging: bool = True):
        """
        Initialize the normalizer.

        Args:
            min_block_size: Minimum character count for deduplication candidates
            enable_logging: Whether to log normalization metrics
        """
        self.min_block_size = min_block_size
        self.enable_logging = enable_logging

    def normalize(self, prompt: str) -> str:
        """
        Main entry point: normalize a prompt by deduplicating repeated blocks.

        Returns the normalized prompt with duplicates replaced by references.
        """
        # 1. Early bailout for small prompts
        if len(prompt) < 1000:
            return prompt

        # 2. Early bailout for very large prompts (performance safety)
        if len(prompt) > 100_000:
            if self.enable_logging:
                logger.warning(f"Prompt too large for normalization ({len(prompt)} chars), skipping")
            return prompt

        try:
            # 3. Segment into blocks
            blocks = self._segment_into_blocks(prompt)

            # 4. Identify duplicates
            canonical_map = self._identify_duplicates(blocks)

            # 5. Replace duplicates with references
            if not canonical_map:
                # No duplicates found, return original
                return prompt

            normalized = self._replace_duplicates(blocks, canonical_map)

            # 6. Log metrics
            if self.enable_logging:
                self._log_metrics(prompt, normalized, len(canonical_map))

            return normalized

        except Exception as e:
            # Graceful degradation: return original prompt on error
            logger.warning(f"Prompt normalization failed: {e}", exc_info=True)
            return prompt

    def _segment_into_blocks(self, prompt: str) -> List[Block]:
        """
        Segment prompt into hierarchical blocks based on markdown structure.

        Block types:
        - Heading blocks (# Section Title)
        - Code blocks (```...```)
        - Paragraph blocks (text between headings)
        - Protected blocks (dynamic placeholders, JSON payloads)
        """
        blocks = []
        lines = prompt.split('\n')
        current_block = []
        current_heading = None
        in_code_block = False
        code_start = None
        pos = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            line_start_pos = pos
            pos += len(line) + 1  # +1 for newline

            # Detect code block boundaries
            if line.strip().startswith('```'):
                if in_code_block:
                    # End of code block
                    current_block.append(line)
                    block_content = '\n'.join(current_block)
                    blocks.append(self._create_block(
                        content=block_content,
                        block_type=BlockType.CODE,
                        heading=None,
                        start_pos=code_start,
                        end_pos=pos
                    ))
                    current_block = []
                    in_code_block = False
                else:
                    # Start of code block - flush any pending paragraph
                    if current_block:
                        block_content = '\n'.join(current_block)
                        blocks.append(self._create_block(
                            content=block_content,
                            block_type=BlockType.PARAGRAPH,
                            heading=current_heading,
                            start_pos=line_start_pos - len(block_content),
                            end_pos=line_start_pos
                        ))
                        current_block = []

                    in_code_block = True
                    code_start = line_start_pos
                    current_block.append(line)
                i += 1
                continue

            # Inside code block - accumulate
            if in_code_block:
                current_block.append(line)
                i += 1
                continue

            # Detect heading
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                # Flush previous block
                if current_block:
                    block_content = '\n'.join(current_block)
                    blocks.append(self._create_block(
                        content=block_content,
                        block_type=BlockType.PARAGRAPH,
                        heading=current_heading,
                        start_pos=line_start_pos - len(block_content),
                        end_pos=line_start_pos
                    ))
                    current_block = []

                # Store heading for subsequent blocks (but don't include it in content)
                current_heading = heading_match.group(2).strip()
                # Start fresh block after heading (don't include heading line in content)
                i += 1
                continue

            # Regular line - accumulate
            current_block.append(line)
            i += 1

        # Flush final block
        if current_block:
            block_content = '\n'.join(current_block)
            blocks.append(self._create_block(
                content=block_content,
                block_type=BlockType.PARAGRAPH if not in_code_block else BlockType.CODE,
                heading=current_heading,
                start_pos=pos - len(block_content),
                end_pos=pos
            ))

        return blocks

    def _create_block(
        self,
        content: str,
        block_type: BlockType,
        heading: Optional[str],
        start_pos: int,
        end_pos: int
    ) -> Block:
        """
        Create a Block object with protection rules applied.
        """
        normalized = self._normalize_for_comparison(content)
        is_protected = self._is_protected_content(content, block_type)

        return Block(
            content=content,
            normalized=normalized,
            block_type=block_type,
            heading=heading,
            start_pos=start_pos,
            end_pos=end_pos,
            is_protected=is_protected
        )

    def _normalize_for_comparison(self, text: str) -> str:
        """
        Normalize text for duplicate detection.

        Normalization rules:
        - Collapse whitespace (multiple spaces → single space)
        - Trim leading/trailing whitespace
        - Keep case sensitivity (meaningful for code)
        - Keep punctuation (meaningful for instructions)
        """
        # Collapse multiple whitespace to single space
        normalized = re.sub(r'\s+', ' ', text)

        # Trim
        normalized = normalized.strip()

        return normalized

    def _is_protected_content(self, content: str, block_type: BlockType) -> bool:
        """
        Check if content should never be deduplicated.

        Protection rules:
        - Size threshold (too small)
        - Dynamic placeholders ({variable})
        - JSON/YAML data structures
        - User query markers
        - Code blocks (always protected for now)
        - Already-normalized content (references)
        """
        # Rule 1: Size threshold
        if len(content) < self.min_block_size:
            return True

        # Rule 2: Code blocks (conservative - protect all code)
        if block_type == BlockType.CODE:
            return True

        # Rule 3: Dynamic placeholders
        if re.search(r'\{[a-z_]+\}', content):
            return True

        # Rule 4: JSON/YAML data
        if content.strip().startswith(('{', '[', '---')):
            return True

        # Rule 5: User query markers
        if any(marker in content.lower() for marker in [
            'user query:',
            'user instructions:',
            '## act instructions',
            '{act_instructions}',
            '{context_summary}',
            '{verify_instructions}'
        ]):
            return True

        # Rule 6: Already-normalized content (idempotency)
        if self._is_already_normalized(content):
            return True

        return False

    def _is_already_normalized(self, content: str) -> bool:
        """Check if block is already a reference."""
        return bool(re.search(r'\(See (the earlier section|canonical block)', content))

    def _identify_duplicates(self, blocks: List[Block]) -> Dict[str, Block]:
        """
        Identify duplicate blocks and map them to canonical instances.

        Uses normalized exact matching (whitespace-normalized, case-sensitive).
        First occurrence becomes canonical.

        Returns: {block_hash: canonical_block} for blocks that have duplicates
        """
        canonical_map = {}  # hash -> first occurrence (canonical)
        duplicates = {}     # hash -> list of duplicate blocks

        for block in blocks:
            # Skip protected blocks
            if block.is_protected:
                continue

            # Skip small blocks
            if len(block.content) < self.min_block_size:
                continue

            # Generate hash
            hash_key = block.hash_key()

            # First occurrence = canonical
            if hash_key not in canonical_map:
                canonical_map[hash_key] = block
                duplicates[hash_key] = []
            else:
                duplicates[hash_key].append(block)

        # Filter: only keep hashes with actual duplicates
        return {k: canonical_map[k] for k in duplicates if len(duplicates[k]) > 0}

    def _replace_duplicates(
        self,
        blocks: List[Block],
        canonical_map: Dict[str, Block]
    ) -> str:
        """
        Replace duplicate blocks with references to canonical blocks.

        Reference style:
        - Preferred: (See the earlier section titled "<heading>" for the full block.)
        - Fallback: (See canonical block [BLOCK:identifier] above.)
        """
        # Build a map of blocks that should be replaced
        replace_map = {}  # block hash -> reference string

        for hash_key, canonical_block in canonical_map.items():
            reference = self._generate_reference(canonical_block)
            replace_map[hash_key] = reference

        # Reconstruct prompt with replacements
        result_parts = []
        seen_hashes = set()

        for block in blocks:
            # Prepare block content with heading if present
            block_with_heading = block.content
            if block.heading and block.block_type != BlockType.CODE:
                # Reconstruct the heading (use ## for consistency)
                block_with_heading = f"## {block.heading}\n{block.content}"

            # Protected blocks always kept as-is
            if block.is_protected:
                result_parts.append(block_with_heading)
                continue

            # Small blocks kept as-is
            if len(block.content) < self.min_block_size:
                result_parts.append(block_with_heading)
                continue

            hash_key = block.hash_key()

            # First occurrence of a duplicate - keep canonical
            if hash_key not in seen_hashes:
                seen_hashes.add(hash_key)
                result_parts.append(block_with_heading)
            else:
                # Subsequent occurrence - replace with reference
                if hash_key in replace_map:
                    # Include heading before reference
                    if block.heading:
                        result_parts.append(f"## {block.heading}\n{replace_map[hash_key]}")
                    else:
                        result_parts.append(replace_map[hash_key])
                else:
                    # Shouldn't happen, but keep original if no reference
                    result_parts.append(block_with_heading)

        return '\n\n'.join(result_parts)

    def _generate_reference(self, canonical_block: Block) -> str:
        """
        Generate a concise reference to the canonical block.

        Preferred format: Use heading if available
        Fallback format: Use block identifier
        """
        # Preferred: Reference by heading
        if canonical_block.heading:
            heading_text = canonical_block.heading.lstrip('#').strip()
            return f'(See the earlier section titled "{heading_text}" for the full block.)'

        # Fallback: Generate block identifier from content
        block_id = self._generate_block_id(canonical_block)
        return f'(See canonical block [BLOCK:{block_id}] above.)'

    def _generate_block_id(self, block: Block) -> str:
        """
        Generate a human-readable identifier for a block.

        Examples:
        - "google_auth" for Google authentication pattern
        - "llm_provider" for LLM provider usage pattern
        - "problem_space" for problem space explanation
        """
        # Extract key phrases from first few words
        first_words = block.content[:100].lower()

        if 'google' in first_words and 'auth' in first_words:
            return 'google_auth'
        elif 'llm' in first_words or 'provider' in first_words:
            return 'llm_provider'
        elif 'problem space' in first_words:
            return 'problem_space'
        elif 'child loop' in first_words:
            return 'child_loop'
        else:
            # Fallback: hash prefix
            return block.hash_key()[:8]

    def _log_metrics(
        self,
        original: str,
        normalized: str,
        duplicate_count: int
    ) -> None:
        """Log normalization metrics."""
        original_len = len(original)
        normalized_len = len(normalized)
        reduction = original_len - normalized_len
        reduction_pct = (reduction / original_len * 100) if original_len > 0 else 0

        logger.info(
            f"Prompt normalized: {original_len} → {normalized_len} chars "
            f"({reduction_pct:.1f}% reduction, {duplicate_count} duplicates found)"
        )
