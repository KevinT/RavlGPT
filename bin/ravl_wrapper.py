#!/bin/sh
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

# RAVL Command Wrapper
# This script provides a unified interface to all RAVL commands
# Usage: ./ravl [--list|--clean|--clone|--health] [options] or ./ravl <loop-name> [options]

# Find the project root (directory containing this script)
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
RAVL_BIN="$PROJECT_ROOT/.ravl/bin"
VENV_PATH="$PROJECT_ROOT/.ravl/venv"

# Ensure venv exists (create if needed)
if [ ! -d "$VENV_PATH" ]; then
  echo "🔧 Creating RAVL framework venv..." >&2
  "$PROJECT_ROOT/.ravl/bin/ravl-init-venv" || {
    echo "❌ Failed to create venv. Run manually: $PROJECT_ROOT/.ravl/bin/ravl-init-venv" >&2
    exit 1
  }
fi

# Use venv Python for all CLI operations
PYTHON="$VENV_PATH/bin/python"

# Get the first argument to determine which command to run
COMMAND="${1:-list}"

# Map flags to their corresponding ravl bin scripts (run with venv Python)
case "$COMMAND" in
  --list|-l)
    # Remove the flag from arguments and pass the rest through
    shift
    exec "$PYTHON" "$RAVL_BIN/ravl-list" "$@"
    ;;
  --clean|-c)
    shift
    exec "$PYTHON" "$RAVL_BIN/ravl-clean" "$@"
    ;;
  --clone)
    shift
    exec "$PYTHON" "$RAVL_BIN/ravl-clone" "$@"
    ;;
  --new)
    shift
    exec "$PYTHON" "$RAVL_BIN/ravl-new-loop" "$@"
    ;;
  --execution-health)
    shift
    exec "$PYTHON" "$RAVL_BIN/ravl-execution-health" "$@"
    ;;
  --loop-health)
    shift
    exec "$PYTHON" "$RAVL_BIN/ravl-loop-health" "$@"
    ;;
  --help)
    cat << 'EOF'
RAVL - Unified Command Wrapper

Usage:
  ./ravl [COMMAND] [OPTIONS]

Commands:
  <loop-name>         Run a RAVL loop by name or path
  --list, -l          List all available RAVL loops
  --clean, -c         Clean up RAVL learning files
  --clone             Clone a RAVL loop from templates
  --new               Create a new RAVL loop from scratch
  --show-config       Display resolved configuration without executing
  --execution-health  Analyze code generation and DSL (solution space)
                      Use --focus "text" to bias analysis toward specific concerns
  --loop-health       Analyze domain learning and patterns (problem space)
                      Use --focus "text" to bias analysis toward specific concerns
  --help              Show this help message

Running Loops:
  By name:     ./ravl strategic_context_sourcing --mode fast
  By path:     ./ravl frontier_delivery.strategic_context_sourcing

  If multiple loops share the same name, you MUST use the full path.
  Use './ravl --list' to see all loops and detect name collisions.

Loop Options:
  --mode {fast|full}               Analysis mode (default: full)
  --force-code-regeneration        Force fresh code generation, bypassing cache
  --no-deep-learning               Skip verify and learn phases
  --show-config                    Display resolved configuration
  --show-execution                 Show code generation details
  --quiet                          Suppress status messages
  --timeout SECONDS                Execution timeout
  --learning-path PATH             Override learning directory
  --venv-path PATH                 Override venv location
  --loop-dir PATH                  Override loop directory

Examples:
  ./ravl external_drift --mode fast
  ./ravl frontier_delivery.my_loop --mode full
  ./ravl my_loop --force-code-regeneration
  ./ravl --list
  ./ravl --clean
  ./ravl --new my_loop --content "# Reflect\n\n# Act\n\n# Verify\n\n# Learn"
  ./ravl LOOP_NAME --show-config
  ./ravl --execution-health org_context
  ./ravl --execution-health my_loop --focus "Look for dependency conflicts"
  ./ravl --loop-health strategy_coherence
  ./ravl --loop-health my_loop --focus "have a look why there's no data"

For more information, see the README.md file.
EOF
    exit 0
    ;;
  *)
    # Assume it's a loop name and pass everything to the main ravl runner (with venv Python)
    exec "$PYTHON" "$RAVL_BIN/ravl" "$@"
    ;;
esac
