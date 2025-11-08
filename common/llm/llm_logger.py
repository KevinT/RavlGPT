"""
LLM Call Logger
Logs all LLM interactions to markdown files for inspection and debugging
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict


class LLMLogger:
    """Logs LLM calls and responses to markdown files"""

    def __init__(self, log_dir: str = None):
        if log_dir is None:
            # Default to centralized LLM logs directory (.ravl/logs/llm/)
            self.log_dir = Path(__file__).parent.parent.parent / 'logs' / 'llm'
        else:
            self.log_dir = Path(log_dir)

        # Create logs directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create markdown log file for this session
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.md_file = self.log_dir / f'llm_calls_{timestamp}.md'

        # Write header to markdown log
        with open(self.md_file, 'w', encoding='utf-8') as f:
            f.write(f"# LLM Call Log\n\n")
            f.write(f"**Session Started:** {datetime.now().isoformat()}\n\n")
            f.write("---\n\n")

    def log_call(self, provider: str, prompt: str, response: str,
                 max_tokens: int, error: Optional[str] = None):
        """
        Log an LLM call with prompt and response to markdown file

        Args:
            provider: Name of the LLM provider (e.g., "Anthropic Claude")
            prompt: The prompt sent to the LLM
            response: The response received from the LLM
            max_tokens: Maximum tokens requested
            error: Optional error message if call failed
        """
        timestamp = datetime.now().isoformat()

        # Write to markdown log
        status = "❌ ERROR" if error else "✅ SUCCESS"
        with open(self.md_file, 'a', encoding='utf-8') as f:
            f.write(f"## LLM Call - {timestamp}\n\n")
            f.write(f"**Status:** {status}  \n")
            f.write(f"**Provider:** {provider}  \n")
            f.write(f"**Max Tokens:** {max_tokens}  \n")
            f.write(f"**Prompt Length:** {len(prompt)} chars  \n")
            f.write(f"**Response Length:** {len(response)} chars  \n")

            if error:
                f.write(f"**Error:** {error}  \n")

            f.write(f"\n### Prompt\n\n")
            f.write(f"```\n{prompt}\n```\n\n")

            f.write(f"### Response\n\n")
            f.write(f"```\n{response}\n```\n\n")

            f.write("---\n\n")

    def get_log_path(self) -> str:
        """Return the path to the current markdown log file"""
        return str(self.md_file)


# Global logger instances (one per log directory)
_logger_instances: Dict[str, LLMLogger] = {}


def get_logger(log_dir: str = None) -> LLMLogger:
    """
    Get or create a logger instance for the specified log directory

    Args:
        log_dir: Optional directory path for log files. If None, uses default .ravl/logs/llm/

    Returns:
        LLMLogger instance for the specified directory
    """
    # Normalize log_dir to use as dict key
    if log_dir is None:
        key = "__default__"
    else:
        key = str(Path(log_dir).resolve())

    # Create logger if it doesn't exist for this directory
    if key not in _logger_instances:
        _logger_instances[key] = LLMLogger(log_dir=log_dir)

    return _logger_instances[key]


def log_llm_call(provider: str, prompt: str, response: str,
                 max_tokens: int, error: Optional[str] = None,
                 log_dir: str = None):
    """
    Convenience function to log an LLM call

    Args:
        provider: Name of the LLM provider (e.g., "Anthropic Claude")
        prompt: The prompt sent to the LLM
        response: The response received from the LLM
        max_tokens: Maximum tokens requested
        error: Optional error message if call failed
        log_dir: Optional directory path for log files. If None, uses default .ravl/logs/llm/
    """
    logger = get_logger(log_dir=log_dir)
    logger.log_call(provider, prompt, response, max_tokens, error)