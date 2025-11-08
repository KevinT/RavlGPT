#!/usr/bin/env python3
"""
Test script for LLM provider abstraction
Tests all available providers based on environment variables
"""

import sys
from pathlib import Path

# Add common directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.llm_providers import LLMProviderFactory


def test_provider(provider_type: str):
    """Test a specific provider"""
    print(f"\n{'='*60}")
    print(f"Testing {provider_type.upper()} provider...")
    print('='*60)

    try:
        provider = LLMProviderFactory.create_provider(provider_type)
        print(f"✓ Provider initialized: {provider.get_provider_name()}")

        # Simple test prompt
        prompt = "Respond with exactly: 'LLM provider working!'"
        print(f"\nSending test prompt...")

        response = provider.complete(prompt, max_tokens=50)
        print(f"Response: {response.strip()}")

        if "working" in response.lower() or "llm" in response.lower():
            print(f"✓ {provider_type.upper()} test PASSED")
            return True
        else:
            print(f"⚠ {provider_type.upper()} responded but unexpected format")
            return True

    except Exception as e:
        print(f"✗ {provider_type.upper()} test FAILED: {e}")
        return False


def main():
    """Test all configured providers"""
    import os

    print("LLM Provider Abstraction Test")
    print("=" * 60)

    # Check which providers are available
    available_providers = []

    if os.environ.get("ANTHROPIC_API_KEY"):
        available_providers.append("anthropic")
    if os.environ.get("OPENAI_API_KEY"):
        available_providers.append("openai")
    if os.environ.get("GOOGLE_API_KEY"):
        available_providers.append("google")

    # Always test Ollama if requested
    if "--test-ollama" in sys.argv or not available_providers:
        available_providers.append("ollama")

    if not available_providers:
        print("\n⚠ No API keys found and --test-ollama not specified")
        print("\nSet one of these environment variables:")
        print("  - ANTHROPIC_API_KEY")
        print("  - OPENAI_API_KEY")
        print("  - GOOGLE_API_KEY")
        print("\nOr run: python test_providers.py --test-ollama")
        return 1

    print(f"\nFound {len(available_providers)} provider(s) to test:")
    for p in available_providers:
        print(f"  - {p}")

    # Test each provider
    results = {}
    for provider_type in available_providers:
        results[provider_type] = test_provider(provider_type)

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)

    for provider_type, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{provider_type:15s} {status}")

    all_passed = all(results.values())
    if all_passed:
        print(f"\n✓ All tests passed!")
        return 0
    else:
        print(f"\n⚠ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())