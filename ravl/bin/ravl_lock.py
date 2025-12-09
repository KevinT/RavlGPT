#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
RAVL-LOCK - Lock a RAVL loop to use specific generated code

Locks a loop to a specific code generation attempt, preventing
further LLM code generation and using the locked code directly.

Usage:
    ravl-lock <loop-name> [options]

Options:
    --attempt N        Lock to specific attempt number (default: latest successful)
    --force            Force lock even if attempt failed verification
    --learning-path PATH  Override learning path
    --help            Show this help message

Examples:
    # Lock to latest successful code
    ravl-lock test

    # Lock to specific attempt
    ravl-lock test --attempt 5

    # Force lock to failed attempt (for debugging)
    ravl-lock test --attempt 3 --force
"""

import sys
import argparse
from pathlib import Path

# Bootstrap: Add framework to path
_current = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_current))

from ravl.common.core.loop_lock_manager import LoopLockManager
from ravl.common.cli.loop_discovery import LoopDiscovery
from ravl.common.ravl_runner import RAVLRunner


def main():
    """Main entry point for ravl-lock"""
    parser = argparse.ArgumentParser(
        description='Lock a RAVL loop to specific generated code',
        add_help=False
    )

    parser.add_argument(
        'loop_name',
        nargs='?',
        help='Name or path of the RAVL loop to lock'
    )

    parser.add_argument(
        '--attempt',
        type=int,
        default=None,
        help='Lock to specific attempt number (default: latest successful)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force lock even if attempt failed verification'
    )

    parser.add_argument(
        '--learning-path',
        type=str,
        default=None,
        help='Override learning path'
    )

    parser.add_argument(
        '--help',
        '-h',
        action='store_true',
        help='Show this help message'
    )

    args = parser.parse_args()

    # Handle help
    if args.help or not args.loop_name:
        print(__doc__)
        sys.exit(0 if args.help else 1)

    # Find project root and discover loop
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    discovery = LoopDiscovery(project_root)

    try:
        # Find loop and load config
        loop_dir = discovery.find_loop(args.loop_name)
        config = discovery.load_config(loop_dir)

        # Resolve learning path
        learning_path = RAVLRunner.resolve_learning_path(
            loop_dir=loop_dir,
            loop_config=config,
            cli_learning_path=args.learning_path,
            project_root=project_root
        )

        # Lock the loop
        lock_mgr = LoopLockManager(loop_dir, learning_path, config)
        success, message = lock_mgr.lock_loop(args.attempt, args.force)

        if success:
            print(f"✅ {message}", file=sys.stderr)
            sys.exit(0)
        else:
            print(f"❌ {message}", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
