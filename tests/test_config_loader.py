#!/usr/bin/env python3
"""
Tests for config_loader.py

Validates environment variable override behavior for LLM configuration.
"""

import os
import pytest


class TestConfigLoaderMaxTokens:
    """Test max_tokens environment variable overrides."""

    def test_max_tokens_environment_variable_override(self):
        """Test that environment variables override TOML config for max_tokens."""
        # Set environment override
        os.environ['RAVL_MAX_TOKENS_CODE_GENERATION'] = '32768'

        try:
            from ravl.common.config.config_loader import get_max_tokens, reload_config

            # Force config reload
            reload_config()

            # Should use env var, not TOML default (16384)
            max_tokens = get_max_tokens('code_generation')
            assert max_tokens == 32768

        finally:
            # Cleanup
            if 'RAVL_MAX_TOKENS_CODE_GENERATION' in os.environ:
                del os.environ['RAVL_MAX_TOKENS_CODE_GENERATION']
            reload_config()

    def test_max_tokens_multiple_environment_variables(self):
        """Test multiple max_tokens environment variables work independently."""
        # Set multiple overrides
        os.environ['RAVL_MAX_TOKENS_VERIFICATION'] = '8192'
        os.environ['RAVL_MAX_TOKENS_DEFAULT'] = '16384'

        try:
            from ravl.common.config.config_loader import get_max_tokens, reload_config

            # Force config reload
            reload_config()

            # Should use env vars, not TOML defaults
            verification_tokens = get_max_tokens('verification')
            default_tokens = get_max_tokens('default')

            assert verification_tokens == 8192  # Override from env var
            assert default_tokens == 16384  # Override from env var

        finally:
            # Cleanup
            if 'RAVL_MAX_TOKENS_VERIFICATION' in os.environ:
                del os.environ['RAVL_MAX_TOKENS_VERIFICATION']
            if 'RAVL_MAX_TOKENS_DEFAULT' in os.environ:
                del os.environ['RAVL_MAX_TOKENS_DEFAULT']
            reload_config()

    def test_max_tokens_fallback_to_toml_when_env_not_set(self):
        """Test that TOML config is used when environment variable is not set."""
        from ravl.common.config.config_loader import get_max_tokens, reload_config

        # Make sure env var is not set
        if 'RAVL_MAX_TOKENS_CODE_GENERATION' in os.environ:
            del os.environ['RAVL_MAX_TOKENS_CODE_GENERATION']

        reload_config()

        # Should use TOML default (16384)
        max_tokens = get_max_tokens('code_generation')
        assert max_tokens == 16384  # TOML default

    def test_max_tokens_invalid_env_value_falls_back_to_toml(self):
        """Test that invalid env var value falls back to TOML config."""
        # Set invalid environment override
        os.environ['RAVL_MAX_TOKENS_CODE_GENERATION'] = 'invalid'

        try:
            from ravl.common.config.config_loader import get_max_tokens, reload_config

            # Force config reload
            reload_config()

            # Should fall back to TOML default (16384)
            max_tokens = get_max_tokens('code_generation')
            assert max_tokens == 16384

        finally:
            # Cleanup
            if 'RAVL_MAX_TOKENS_CODE_GENERATION' in os.environ:
                del os.environ['RAVL_MAX_TOKENS_CODE_GENERATION']
            reload_config()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
