"""
LLM Logging Utility for Generated Code

This module provides a simple function that generated code can import to log
LLM calls. All logs go to .ravl/logs/llm/ in both text and JSONL formats.

Usage in generated code:
```python
from llm.generated_code_llm_logger import log_llm_call

# Make LLM call
response = anthropic_client.complete(prompt)

# Log it
log_llm_call(
    prompt=prompt,
    response=response,
    provider="Anthropic",
    max_tokens=1024
)
```
"""

from .llm_logger import get_logger


def log_llm_call(prompt: str, response: str, provider: str = "Anthropic",
                 max_tokens: int = 1024, error: str = None):
    """
    Log an LLM call from generated code

    Args:
        prompt: The prompt sent to the LLM
        response: The response received from the LLM
        provider: Name of the LLM provider (default: "Anthropic")
        max_tokens: Maximum tokens requested (default: 1024)
        error: Optional error message if call failed

    Logs are written to:
    - .ravl/logs/llm/llm_calls_TIMESTAMP.md (markdown format)
    """
    logger = get_logger()
    logger.log_call(
        provider=provider,
        prompt=prompt,
        response=response,
        max_tokens=max_tokens,
        error=error
    )
