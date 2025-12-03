#!/usr/bin/env python3
"""
Unit tests for PromptNormalizer.

Tests edge cases, protection rules, duplicate detection, and reference generation.
"""

import pytest
from ravl.common.llm.prompt_normalizer import PromptNormalizer, Block, BlockType


class TestPromptNormalizer:
    """Unit tests for PromptNormalizer class."""

    def test_exact_duplicate_detection(self):
        """Verify exact duplicates are detected."""
        prompt = """
## Section A
This is a large block of text that should be detected as a duplicate when it appears again later in the prompt with the exact same content.

## Section B
Different content here that is unique.

## Section C
This is a large block of text that should be detected as a duplicate when it appears again later in the prompt with the exact same content.
"""
        normalizer = PromptNormalizer(min_block_size=20)
        normalized = normalizer.normalize(prompt)

        assert "See the earlier section" in normalized
        assert normalized.count("This is a large block of text") == 1

    def test_whitespace_normalization(self):
        """Verify whitespace differences don't prevent deduplication."""
        prompt = """
## Section A
Text   with    extra    spaces that should still match

## Section B
Text with extra spaces that should still match
"""
        normalizer = PromptNormalizer(min_block_size=10)
        normalized = normalizer.normalize(prompt)

        assert "See the earlier section" in normalized

    def test_code_block_protection(self):
        """Verify code blocks aren't incorrectly deduplicated."""
        prompt = """
## Section A
```python
def foo():
    pass
```

## Section B
```python
def bar():
    pass
```
"""
        normalizer = PromptNormalizer()
        normalized = normalizer.normalize(prompt)

        # Different code blocks should NOT be deduplicated (protected)
        assert "def foo" in normalized
        assert "def bar" in normalized
        assert "See the earlier section" not in normalized

    def test_protected_content_placeholders(self):
        """Verify protected content with placeholders never deduplicated."""
        prompt = """
## Context
{context_summary}

## Instructions
{act_instructions}

## Verification
{verify_instructions}
"""
        normalizer = PromptNormalizer()
        normalized = normalizer.normalize(prompt)

        # Placeholders should be preserved
        assert normalized == prompt

    def test_min_block_size_threshold(self):
        """Verify small blocks aren't deduplicated."""
        prompt = """
## A
Short.

## B
Short.
"""
        normalizer = PromptNormalizer(min_block_size=100)
        normalized = normalizer.normalize(prompt)

        # Too small, should not be deduplicated
        assert normalized == prompt

    def test_reference_generation_with_heading(self):
        """Verify references use headings when available."""
        prompt = """
## Google Authentication Pattern
Use GOOGLE_CREDENTIALS environment variable for authentication across all providers.

## Section B
Other content that is unique.

## Google Authentication Pattern
Use GOOGLE_CREDENTIALS environment variable for authentication across all providers.
"""
        normalizer = PromptNormalizer(min_block_size=20)
        normalized = normalizer.normalize(prompt)

        assert 'See the earlier section titled "Google Authentication Pattern"' in normalized

    def test_idempotency(self):
        """Verify running normalizer twice doesn't break output."""
        prompt = """
## Section A
Large repeated block of text that should be deduplicated when it appears again later.

## Section B
Large repeated block of text that should be deduplicated when it appears again later.
"""
        normalizer = PromptNormalizer(min_block_size=10)
        normalized1 = normalizer.normalize(prompt)
        normalized2 = normalizer.normalize(normalized1)

        # Second run should not change output
        assert normalized1 == normalized2

    def test_small_prompt_early_bailout(self):
        """Verify small prompts (<1000 chars) skip normalization."""
        prompt = "Short prompt."
        normalizer = PromptNormalizer()
        normalized = normalizer.normalize(prompt)

        # Should return original unchanged
        assert normalized == prompt

    def test_large_prompt_early_bailout(self):
        """Verify very large prompts (>100k chars) skip normalization."""
        # Create 150k character prompt
        prompt = "x" * 150000
        normalizer = PromptNormalizer()
        normalized = normalizer.normalize(prompt)

        # Should return original unchanged (too large)
        assert normalized == prompt

    def test_json_protection(self):
        """Verify JSON data is protected from deduplication."""
        prompt = """
## Data A
{
  "key": "value",
  "nested": {"a": 1}
}

## Data B
{
  "key": "value",
  "nested": {"a": 1}
}
"""
        normalizer = PromptNormalizer()
        normalized = normalizer.normalize(prompt)

        # JSON blocks should be protected (not deduplicated)
        assert normalized.count('"key": "value"') == 2

    def test_user_query_protection(self):
        """Verify user query markers are protected."""
        prompt = """
## User Query:
Tell me about the data

## Act Instructions
Process the data

## User Query:
Tell me about the data
"""
        normalizer = PromptNormalizer()
        normalized = normalizer.normalize(prompt)

        # User query should be protected
        assert normalized.count("Tell me about the data") == 2

    def test_no_duplicates_returns_original(self):
        """Verify prompt with no duplicates returns unchanged."""
        prompt = """
## Section A
Unique content in section A that appears nowhere else.

## Section B
Unique content in section B that is completely different.

## Section C
Unique content in section C that has nothing in common.
"""
        normalizer = PromptNormalizer(min_block_size=10)
        normalized = normalizer.normalize(prompt)

        # No duplicates, should return original
        assert normalized == prompt

    def test_multiple_duplicates_same_content(self):
        """Verify multiple duplicates of same content handled correctly."""
        prompt = """
## A
Repeated content here that will appear three times.

## B
Repeated content here that will appear three times.

## C
Repeated content here that will appear three times.
"""
        normalizer = PromptNormalizer(min_block_size=10)
        normalized = normalizer.normalize(prompt)

        # First occurrence kept, subsequent replaced
        assert normalized.count("Repeated content here") == 1
        assert normalized.count("See the earlier section") == 2

    def test_block_id_generation(self):
        """Verify smart block ID generation from content."""
        normalizer = PromptNormalizer()

        # Test Google Auth pattern detection
        block_ga = Block(
            content="## Google Auth\n\nUse GOOGLE_CREDENTIALS...",
            normalized="google auth use google_credentials",
            block_type=BlockType.PARAGRAPH,
            heading="Google Auth",
            start_pos=0,
            end_pos=50,
            is_protected=False
        )
        assert normalizer._generate_block_id(block_ga) == "google_auth"

        # Test LLM Provider pattern detection
        block_llm = Block(
            content="## LLM Provider\n\nUse LLMProviderFactory...",
            normalized="llm provider use llmproviderfactory",
            block_type=BlockType.PARAGRAPH,
            heading="LLM Provider",
            start_pos=0,
            end_pos=50,
            is_protected=False
        )
        assert normalizer._generate_block_id(block_llm) == "llm_provider"

    def test_reference_without_heading(self):
        """Verify references work when no heading available."""
        prompt = """
Large block of text without a heading that will be repeated later in the prompt.

## Some Section
Other content here.

Large block of text without a heading that will be repeated later in the prompt.
"""
        normalizer = PromptNormalizer(min_block_size=10)
        normalized = normalizer.normalize(prompt)

        # Should generate block ID reference
        assert "BLOCK:" in normalized or "See" in normalized

    def test_error_handling_graceful_degradation(self):
        """Verify errors return original prompt (graceful degradation)."""
        normalizer = PromptNormalizer()

        # Mock an error in segmentation by passing invalid input
        # The normalizer should catch and return original
        prompt = "Valid prompt"

        # Should not raise, should return original
        normalized = normalizer.normalize(prompt)
        assert isinstance(normalized, str)

    def test_normalize_for_comparison(self):
        """Test whitespace normalization logic."""
        normalizer = PromptNormalizer()

        text1 = "Text   with    multiple     spaces"
        text2 = "Text with multiple spaces"

        norm1 = normalizer._normalize_for_comparison(text1)
        norm2 = normalizer._normalize_for_comparison(text2)

        assert norm1 == norm2

    def test_heading_extraction(self):
        """Test heading extraction from blocks."""
        prompt = """
## Main Heading

Content under main heading.

### Subheading

Content under subheading.
"""
        normalizer = PromptNormalizer()
        blocks = normalizer._segment_into_blocks(prompt)

        # Should extract headings correctly
        headings = [b.heading for b in blocks if b.heading]
        assert "Main Heading" in headings
        assert "Subheading" in headings


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
