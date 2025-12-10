#!/usr/bin/env python3
"""
RAVL Execution Health Check - Analyze code generation, DSL stability, and dependencies

Focuses on SOLUTION SPACE: How to make the infrastructure work.

Usage:
    ravl-execution-health <loop-name> [--focus TEXT]

Examples:
    ravl-execution-health org_context
    ravl-execution-health strategy_coherence --focus "Look for dependency conflicts"
    ravl-execution-health my_loop --focus "something's wrong with code generation"

Analyzes:
- DSL iteration stability (converging vs unstable)
- Execution failure patterns
- Code cache effectiveness
- Recent execution success rates

The --focus parameter biases the analysis toward specific concerns (formal or casual phrasing).

Runs: ./.ravl/bin/ravl ravl.framework.health_checks.execution_health_check --loop <loop-name>
"""

import sys
import subprocess
from pathlib import Path
import difflib
import argparse

# Parse arguments
parser = argparse.ArgumentParser(
    description='RAVL Execution Health Check - Analyze code generation and DSL stability',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  ravl-execution-health org_context
  ravl-execution-health my_loop --focus "Look for dependency conflicts"
  ravl-execution-health my_loop --focus "something's wrong with code generation"
"""
)
parser.add_argument('loop_name', help='Target loop to analyze')
parser.add_argument('--focus', type=str, default=None,
                    help='Custom focus area for health analysis (e.g., "Look for dependency conflicts")')

args = parser.parse_args()

# Bootstrap: Add framework to path so we can import utilities
# The framework is installed/available via normal Python imports
try:
    from ravl.common.cli.ravl_cli_base import RAVLCLIBase
    from ravl.common.cli.loop_discovery import LoopDiscovery
except ImportError:
    # If ravl isn't installed, we're running from source - add to path
    _framework_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(_framework_root))
    from ravl.common.cli.ravl_cli_base import RAVLCLIBase
    from ravl.common.cli.loop_discovery import LoopDiscovery

# Find project root using framework utilities
project_root = RAVLCLIBase.find_project_root(required=False)

loop_name = args.loop_name

# Validate that the loop exists before running health check
try:

    discovery = LoopDiscovery(project_root)

    # Try to find the loop
    try:
        target_loop = discovery.find_loop(loop_name)
    except ValueError:
        # Loop not found - provide helpful suggestions
        all_loops = discovery.find_all_loops()
        loop_names = [loop['path'].name for loop in all_loops]

        print(f"❌ Loop not found: {loop_name}", file=sys.stderr)
        print(file=sys.stderr)

        # Find close matches using fuzzy matching
        close_matches = difflib.get_close_matches(loop_name, loop_names, n=3, cutoff=0.6)

        if close_matches:
            print("💡 Did you mean:", file=sys.stderr)
            for match in close_matches:
                print(f"   • {match}", file=sys.stderr)
            print(file=sys.stderr)

        if loop_names:
            print("📋 Available loops:", file=sys.stderr)
            for name in sorted(loop_names)[:10]:  # Show first 10
                print(f"   • {name}", file=sys.stderr)
            if len(loop_names) > 10:
                print(f"   ... and {len(loop_names) - 10} more", file=sys.stderr)

        print(file=sys.stderr)
        print("Use './ravl-list' to see all available loops", file=sys.stderr)
        sys.exit(1)

except Exception as e:
    print(f"Error validating loop: {str(e)}", file=sys.stderr)
    sys.exit(1)

# Build ravl command - use Python module invocation (works for both local and UV installations)
ravl_cmd = [
    sys.executable,
    "-m", "ravl.bin.ravl",
    "ravl.framework.health_checks.execution_health_check",
    "--hide-execution"  # Suppress framework banners, show only health diagnostics
]

# Run the health check through RAVL runner with target loop and focus in environment
import os
env = os.environ.copy()
env["HEALTH_CHECK_TARGET_LOOP"] = loop_name

# Pass focus parameter via environment variable if provided
if args.focus:
    env["HEALTH_CHECK_FOCUS"] = args.focus
    print(f"🔦 Focussing on: {args.focus}")

try:
    result = subprocess.run(ravl_cmd, cwd=str(project_root), env=env)
    sys.exit(result.returncode)
except Exception as e:
    print(f"Error: {str(e)}", file=sys.stderr)
    sys.exit(1)
