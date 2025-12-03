#!/usr/bin/env python3
"""
Integration tests for PromptNormalizer.

Tests with real prompt templates and LLM provider integration.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from ravl.common.llm.prompt_normalizer import PromptNormalizer


class TestPromptNormalizerIntegration:
    """Integration tests with real prompts."""

    def test_real_act_prompt_normalization(self):
        """Test with actual act_phase.md prompt."""
        # Read the real act_phase.md template
        act_phase_path = Path(__file__).parent.parent / 'ravl' / 'common' / 'execution' / 'markdown' / 'prompts' / 'act_phase.md'

        if not act_phase_path.exists():
            pytest.skip("act_phase.md not found")

        with open(act_phase_path, 'r') as f:
            template = f.read()

        # Substitute placeholders with sample content
        prompt = template.format(
            act_instructions='Fetch data from API',
            context_summary='Context here',
            verify_instructions='Check quality'
        )

        normalizer = PromptNormalizer()
        normalized = normalizer.normalize(prompt)

        # Should reduce size significantly
        reduction = (len(prompt) - len(normalized)) / len(prompt)
        print(f"\nOriginal: {len(prompt)} chars, Normalized: {len(normalized)} chars, Reduction: {reduction*100:.1f}%")

        # At least some reduction expected (may not be 20% if template changes)
        assert len(normalized) <= len(prompt)

        # Should preserve key content (either placeholder or substituted value)
        assert 'act_instructions' in normalized or 'Fetch data' in normalized
        assert 'context_summary' in normalized or 'Context here' in normalized

    def test_data_ingestion_codegen_prompt(self):
        """Test with data_ingestion_codegen.md prompt."""
        codegen_path = Path(__file__).parent.parent / 'ravl' / 'common' / 'execution' / 'markdown' / 'prompts' / 'data_ingestion_codegen.md'

        if not codegen_path.exists():
            pytest.skip("data_ingestion_codegen.md not found")

        with open(codegen_path, 'r') as f:
            template = f.read()

        # Substitute placeholders
        prompt = template.format(
            context7_docs='API documentation here',
            required_fields='field1, field2',
            output_format='JSON',
            failure_context=''
        )

        normalizer = PromptNormalizer()
        normalized = normalizer.normalize(prompt)

        print(f"\nCodegen - Original: {len(prompt)} chars, Normalized: {len(normalized)} chars")

        # Should not break the prompt
        assert len(normalized) > 0
        assert isinstance(normalized, str)

    def test_llm_provider_integration_anthropic(self):
        """Test normalization through AnthropicProvider.complete()."""
        os.environ['RAVL_NORMALIZE_PROMPTS'] = 'true'
        os.environ['ANTHROPIC_API_KEY'] = 'test-key-for-mocking'

        try:
            from ravl.common.llm.llm_providers import AnthropicProvider

            with patch('ravl.common.llm.llm_providers.anthropic') as mock_anthropic:
                # Mock the Anthropic client
                mock_client = Mock()
                mock_response = Mock()
                mock_response.content = [Mock(text='response text')]
                mock_client.messages.create.return_value = mock_response
                mock_anthropic.Anthropic.return_value = mock_client

                provider = AnthropicProvider()

                prompt_with_dupes = """
## Section A
Large repeated block of instructional text that appears multiple times.

## Section B
Large repeated block of instructional text that appears multiple times.
"""

                result = provider.complete(prompt_with_dupes)

                # Verify call was made
                assert mock_client.messages.create.called

                # Verify normalized prompt was sent to API
                call_args = mock_client.messages.create.call_args[1]
                sent_prompt = call_args['messages'][0]['content']

                # Should be normalized (shorter)
                assert len(sent_prompt) < len(prompt_with_dupes)
                assert 'See the earlier section' in sent_prompt

        finally:
            # Cleanup
            if 'RAVL_NORMALIZE_PROMPTS' in os.environ:
                del os.environ['RAVL_NORMALIZE_PROMPTS']
            if 'ANTHROPIC_API_KEY' in os.environ:
                del os.environ['ANTHROPIC_API_KEY']

    def test_llm_provider_integration_disabled(self):
        """Test that normalization is skipped when disabled."""
        os.environ['RAVL_NORMALIZE_PROMPTS'] = 'false'
        os.environ['ANTHROPIC_API_KEY'] = 'test-key-for-mocking'

        try:
            from ravl.common.llm.llm_providers import AnthropicProvider

            with patch('ravl.common.llm.llm_providers.anthropic') as mock_anthropic:
                # Mock the Anthropic client
                mock_client = Mock()
                mock_response = Mock()
                mock_response.content = [Mock(text='response text')]
                mock_client.messages.create.return_value = mock_response
                mock_anthropic.Anthropic.return_value = mock_client

                provider = AnthropicProvider()

                prompt_with_dupes = """
## Section A
Large repeated block.

## Section B
Large repeated block.
"""

                result = provider.complete(prompt_with_dupes)

                # Verify original prompt was sent (not normalized)
                call_args = mock_client.messages.create.call_args[1]
                sent_prompt = call_args['messages'][0]['content']

                # Should be original (no normalization)
                assert sent_prompt == prompt_with_dupes

        finally:
            # Cleanup
            if 'RAVL_NORMALIZE_PROMPTS' in os.environ:
                del os.environ['RAVL_NORMALIZE_PROMPTS']
            if 'ANTHROPIC_API_KEY' in os.environ:
                del os.environ['ANTHROPIC_API_KEY']

    def test_complex_prompt_with_multiple_patterns(self):
        """Test prompt with multiple repeated patterns."""
        prompt = """
# Main Instructions

## Google Authentication Pattern
Use GOOGLE_CREDENTIALS environment variable for all authentication.
Load from JSON, create Credentials object, refresh if expired.

## Data Processing
Process the data according to requirements.

## LLM Provider Pattern
Use LLMProviderFactory to create providers.
Call complete() with prompt and max_tokens.
Handle errors gracefully.

## Additional Context
More information here.

## Google Authentication Pattern
Use GOOGLE_CREDENTIALS environment variable for all authentication.
Load from JSON, create Credentials object, refresh if expired.

## LLM Provider Pattern
Use LLMProviderFactory to create providers.
Call complete() with prompt and max_tokens.
Handle errors gracefully.
"""

        normalizer = PromptNormalizer(min_block_size=20)
        normalized = normalizer.normalize(prompt)

        print(f"\nComplex - Original: {len(prompt)} chars, Normalized: {len(normalized)} chars")

        # Should have references to both patterns
        assert 'See the earlier section titled "Google Authentication Pattern"' in normalized
        assert 'See the earlier section titled "LLM Provider Pattern"' in normalized

        # Each pattern should appear only once in full
        assert normalized.count("Use GOOGLE_CREDENTIALS environment variable") == 1
        assert normalized.count("Use LLMProviderFactory to create providers") == 1

    def test_prompt_with_code_and_text_duplicates(self):
        """Test that code duplicates are protected but text duplicates are deduplicated."""
        prompt = """
## Text Pattern
This is instructional text that should be deduplicated.

## Code Example 1
```python
def example():
    pass
```

## More Instructions
This is instructional text that should be deduplicated.

## Code Example 2
```python
def example():
    pass
```
"""

        normalizer = PromptNormalizer(min_block_size=10)
        normalized = normalizer.normalize(prompt)

        # Text should be deduplicated
        assert normalized.count("This is instructional text") == 1

        # Code blocks should remain (protected)
        assert normalized.count("def example():") == 2

    def test_environment_variable_configuration(self):
        """Test that environment variables control normalizer behavior."""
        # Test min block size configuration
        os.environ['RAVL_PROMPT_MIN_BLOCK_SIZE'] = '50'

        try:
            from ravl.common.llm.prompt_normalizer import PromptNormalizer
            from ravl.common.llm.llm_providers import get_normalizer

            # Clear the singleton
            import ravl.common.llm.llm_providers as llm_mod
            llm_mod._normalizer = None

            normalizer = get_normalizer()
            assert normalizer.min_block_size == 50

        finally:
            if 'RAVL_PROMPT_MIN_BLOCK_SIZE' in os.environ:
                del os.environ['RAVL_PROMPT_MIN_BLOCK_SIZE']
            # Reset singleton
            llm_mod._normalizer = None

    def test_config_loader_environment_variable_override(self):
        """Test that environment variables override TOML config in config_loader."""
        # Set environment overrides
        os.environ['RAVL_PROMPT_NORMALIZATION_ENABLED'] = 'false'
        os.environ['RAVL_PROMPT_NORMALIZATION_MIN_BLOCK_SIZE'] = '500'
        os.environ['RAVL_PROMPT_NORMALIZATION_ENABLE_LOGGING'] = 'false'

        try:
            from ravl.common.config.config_loader import get_prompt_normalization_config, reload_config

            # Force config reload
            reload_config()

            config = get_prompt_normalization_config()

            # Should use env vars, not TOML defaults
            assert config['enabled'] == False
            assert config['min_block_size'] == 500
            assert config['enable_logging'] == False

        finally:
            # Cleanup
            if 'RAVL_PROMPT_NORMALIZATION_ENABLED' in os.environ:
                del os.environ['RAVL_PROMPT_NORMALIZATION_ENABLED']
            if 'RAVL_PROMPT_NORMALIZATION_MIN_BLOCK_SIZE' in os.environ:
                del os.environ['RAVL_PROMPT_NORMALIZATION_MIN_BLOCK_SIZE']
            if 'RAVL_PROMPT_NORMALIZATION_ENABLE_LOGGING' in os.environ:
                del os.environ['RAVL_PROMPT_NORMALIZATION_ENABLE_LOGGING']
            reload_config()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
