"""Logging utilities for RAVL framework

Standardizes logging output formats and emoji usage across the framework.
"""

import os
import sys
from typing import Optional

# Standard emoji constants
EMOJI_SUCCESS = "✅"
EMOJI_ERROR = "❌"
EMOJI_WARNING = "⚠️"
EMOJI_INFO = "ℹ️"
EMOJI_LOOP = "➿"
EMOJI_REFLECT = "🔍"
EMOJI_VERIFY = "✅"
EMOJI_LEARN = "📚"
EMOJI_TRASH = "🗑️"
EMOJI_RUNNING = "▶️"
EMOJI_DONE = "✨"
EMOJI_CHECK = "✓"
EMOJI_CROSS = "✗"
EMOJI_BULLET = "•"

# Status symbols for consistent output
STATUS_SYMBOLS = {
    'info': '[i]',
    'success': '[✓]',
    'error': '[✗]',
    'working': '[•]',
}

# Global flag for execution detail visibility
# Controls whether execution learning messages (code generation, DSL, caching) are shown
# Domain learning messages (validation, insights, patterns) are always shown
_show_execution: bool = False


def set_show_execution(enabled: bool):
    """
    Set global flag for execution detail visibility.

    Call this once at runner startup to control whether execution learning
    details (code generation, DSL inference, caching) are shown.

    Args:
        enabled: True to show execution details, False to hide them
    """
    global _show_execution
    _show_execution = enabled


def should_show_execution() -> bool:
    """
    Check if execution details should be shown.

    Checks both the global flag and RAVL_SHOW_EXECUTION environment variable.

    Returns:
        True if execution details should be shown, False otherwise
    """
    global _show_execution
    # Check environment variable as fallback
    if os.environ.get('RAVL_SHOW_EXECUTION', '').lower() in ('1', 'true', 'yes'):
        return True
    return _show_execution


def log_execution(message: str, indent: int = 2, status: str = 'working'):
    """
    Log execution-related message (only shown if show_execution enabled).

    Use for framework plumbing messages like code generation, DSL inference,
    caching, etc. These are hidden by default unless --show-execution flag is used.

    Args:
        message: Message to log
        indent: Number of spaces to indent (default: 2)
        status: Status type ('info', 'success', 'error', 'working')
    """
    if should_show_execution():
        log_message(message, status=status, indent=indent)


def log_domain(message: str, indent: int = 2, status: str = 'info'):
    """
    Log domain-related message (always shown).

    Use for user-facing messages about domain learning progress like
    validation results, insights, patterns, metrics, etc.

    Args:
        message: Message to log
        indent: Number of spaces to indent (default: 2)
        status: Status type ('info', 'success', 'error', 'working')
    """
    log_message(message, status=status, indent=indent)


def log_message(message: str, status: str = 'info', indent: int = 2, file=None, show_symbol: bool = True):
    """
    Log a formatted message with consistent styling.

    Args:
        message: Message to log
        status: Status type ('info', 'success', 'error', 'working')
        indent: Number of spaces to indent
        file: File to write to (default: sys.stderr)
        show_symbol: Whether to show the status symbol prefix (default: True)
    """
    if file is None:
        file = sys.stderr

    # For empty or whitespace-only messages, print blank line without prefix
    if not message or message.isspace():
        print("", file=file, flush=True)
        return

    indent_str = ' ' * indent
    if show_symbol:
        symbol = STATUS_SYMBOLS.get(status, '[i]')
        print(f"{indent_str}{symbol} {message}", file=file, flush=True)
    else:
        print(f"{indent_str}{message}", file=file, flush=True)


def log_verification_error(error_title: str, error_msg: str, max_length: int = 150, file=None):
    """
    Log a verification error in consistent format.

    Args:
        error_title: Short title of the error
        error_msg: Detailed error message (will be truncated if needed)
        max_length: Maximum length of error message to display
        file: File to write to (default: sys.stderr)
    """
    if file is None:
        file = sys.stderr

    truncated_msg = error_msg[:max_length] if len(error_msg) > max_length else error_msg
    log_message(error_title, status='error', file=file)
    log_message(f"Error: {truncated_msg}", indent=6, file=file)


def log_phase_banner(phase_name: str, emoji: str = "🔍", file=None):
    """
    Log a phase transition banner.

    Args:
        phase_name: Name of the phase
        emoji: Emoji to display
        file: File to write to (default: sys.stderr)
    """
    if file is None:
        file = sys.stderr

    print("\n" + "="*80, file=file, flush=True)
    print(f"{emoji} {phase_name}", file=file, flush=True)
    print("="*80, file=file, flush=True)


def truncate_output(content: str, max_length: int) -> str:
    """
    Truncate content to a maximum length, keeping the end of the content.

    Args:
        content: Content to truncate
        max_length: Maximum length

    Returns:
        Truncated content
    """
    if len(content) <= max_length:
        return content
    return content[-max_length:]
