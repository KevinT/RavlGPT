#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
RAVL Health Checks - Choose between Execution or Domain Learning analysis

IMPORTANT: The old unified health check has been replaced with TWO separate checks:

1. EXECUTION HEALTH CHECK (Solution Space)
   - Analyzes HOW the framework infrastructure works
   - Diagnoses: code generation, DSL stability, execution errors, dependencies
   - Use when: Loop crashes, won't start, execution failures
   - Command: ravl-execution-health <loop-name>

2. LOOP HEALTH CHECK (Problem Space)
   - Analyzes WHAT the loop learns about its domain
   - Diagnoses: verification failures, model stagnation, domain patterns
   - Use when: Loop runs but verification fails, poor quality output
   - Command: ravl-loop-health <loop-name>

Usage:
    ravl-health <loop-name>                    # Run BOTH checks
    ravl-health <loop-name> --execution-only   # Execution check only
    ravl-health <loop-name> --loop-only        # Domain learning check only

Examples:
    ravl-health org_context                # Run both checks
    ravl-health strategy_coherence --execution-only
    ravl-health breadcrumb_importer --loop-only

Documentation: See .ravl/docs/health_checks.md for detailed guide
"""

import sys
import subprocess
from pathlib import Path

if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
    print(__doc__)
    sys.exit(0 if len(sys.argv) > 1 else 1)

# Find framework directory
_current = Path(__file__).resolve().parent.parent
_framework_dir = _current  # .ravl directory
project_root = _framework_dir.parent

loop_name = sys.argv[1]

# Check flags
execution_only = '--execution-only' in sys.argv
loop_only = '--loop-only' in sys.argv

if execution_only and loop_only:
    print("❌ Error: Cannot specify both --execution-only and --loop-only", file=sys.stderr)
    sys.exit(1)

# Determine which checks to run
run_execution = not loop_only
run_loop = not execution_only

print(f"\n🏥 Running Health Checks for: {loop_name}\n", file=sys.stderr)

if run_execution and run_loop:
    print("Running BOTH checks (execution + domain learning)", file=sys.stderr)
    print("Use --execution-only or --loop-only to run just one\n", file=sys.stderr)

exit_code = 0

# Run execution health check
if run_execution:
    print("=" * 60, file=sys.stderr)
    print("EXECUTION HEALTH CHECK (Solution Space)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    cmd = [str(_framework_dir / "bin" / "ravl-execution-health"), loop_name]
    result = subprocess.run(cmd, cwd=str(project_root))

    if result.returncode != 0:
        exit_code = result.returncode

# Run loop health check
if run_loop:
    if run_execution:
        print("\n", file=sys.stderr)

    print("=" * 60, file=sys.stderr)
    print("LOOP HEALTH CHECK (Problem Space)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    cmd = [str(_framework_dir / "bin" / "ravl-loop-health"), loop_name]
    result = subprocess.run(cmd, cwd=str(project_root))

    if result.returncode != 0:
        exit_code = result.returncode

print("\n" + "=" * 60, file=sys.stderr)
print("Health Check Complete", file=sys.stderr)
print("=" * 60, file=sys.stderr)

if exit_code != 0:
    print("\n⚠️  Some checks indicated issues. Review diagnostics above.", file=sys.stderr)
else:
    print("\n✅ All checks passed!", file=sys.stderr)

print("\n💡 For detailed documentation: .ravl/docs/health_checks.md\n", file=sys.stderr)

sys.exit(exit_code)
