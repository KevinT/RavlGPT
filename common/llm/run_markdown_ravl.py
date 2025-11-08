#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Generic Markdown RAVL Loop Runner

Runs markdown-based RAVL loops using configuration from config.yml
instead of requiring custom run.py files for each loop.

Usage:
    # Auto-detect config from loop directory
    python3 run_markdown_ravl.py --loop-dir path/to/loop --role "CTO"

    # Specify config explicitly
    python3 run_markdown_ravl.py --config path/to/config.yml --role "CTO"
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add common directory and .ravl root to path
_script_dir = Path(__file__).parent
_common_dir = _script_dir.parent
_ravl_root = _common_dir.parent
sys.path.insert(0, str(_ravl_root))  # Add .ravl root so 'common' module is importable
sys.path.insert(0, str(_common_dir))
sys.path.insert(0, str(_common_dir / 'utils'))
sys.path.insert(0, str(_common_dir / 'config'))

from ravl_runner import RAVLRunner
from execution.markdown.markdown_ravl_executor import MarkdownRAVLExecutor
from constants import DEFAULT_EXECUTION_TIMEOUT
from file_utils import load_yaml_file

# Add CLI directory to path for ConfigDisplay
sys.path.insert(0, str(_script_dir.parent / 'cli'))
from config_display import ConfigDisplay


class ConfigBasedRAVLRunner:
    """Runs markdown RAVL loops based on config.yml"""

    def __init__(self, config_path: Path):
        """
        Initialize runner from config file

        Args:
            config_path: Path to config.yml file
        """
        self.config_path = config_path

        # Determine loop directory
        # If config is in config/ subdirectory, loop_dir is parent of config/
        # Otherwise loop_dir is parent of config file
        if config_path.parent.name == 'config':
            self.loop_dir = config_path.parent.parent
        else:
            self.loop_dir = config_path.parent

        # Load configuration
        self.config = load_yaml_file(config_path) or {}

        # If we loaded ravl.yml directly, it has everything
        # If we loaded config.yml, merge metadata from ravl.yml
        if config_path.name == 'config.yml' and self.config and ('name' not in self.config or 'description' not in self.config):
            ravl_yml = self.loop_dir / 'config' / 'ravl.yml'
            ravl_config = load_yaml_file(ravl_yml) or {}
            if ravl_config:
                # Merge metadata from ravl.yml
                self.config.setdefault('name', ravl_config.get('name'))
                self.config.setdefault('description', ravl_config.get('description'))
                self.config.setdefault('emoji', ravl_config.get('emoji'))

        # Ensure name is always set (derive from loop folder if not in config)
        if 'name' not in self.config:
            self.config['name'] = self.loop_dir.name

        # Validate required config keys
        self._validate_config()

    def _validate_config(self):
        """Validate required configuration keys"""
        # No truly required keys - all can have sensible defaults
        # Provide defaults for optional keys
        if 'template_variables' not in self.config:
            self.config['template_variables'] = {}

        # Validate template variables structure if they exist
        for var_name, var_config in self.config.get('template_variables', {}).items():
            if 'cli_arg' not in var_config:
                raise ValueError(f"Template variable '{var_name}' missing 'cli_arg'")

    def create_argument_parser(self) -> argparse.ArgumentParser:
        """
        Create argument parser with dynamic arguments from config

        Returns:
            ArgumentParser configured with loop-specific arguments
        """
        description = self.config.get('description', f"{self.config['name']} RAVL Loop")
        parser = RAVLRunner.create_base_parser(description)

        # Add template variable arguments
        for var_name, var_config in self.config['template_variables'].items():
            cli_arg = var_config['cli_arg']
            required = var_config.get('required', False)
            help_text = var_config.get('help', f'Value for template variable: {var_name}')
            var_type = var_config.get('type', 'string')

            # Convert type string to Python type
            type_map = {
                'string': str,
                'int': int,
                'float': float,
                'bool': bool
            }
            python_type = type_map.get(var_type, str)

            parser.add_argument(
                cli_arg,
                required=required,
                help=help_text,
                type=python_type
            )

        return parser

    def extract_template_vars(self, args: argparse.Namespace) -> Dict[str, str]:
        """
        Extract template variables from parsed arguments

        Args:
            args: Parsed command-line arguments

        Returns:
            Dict mapping template variable names to values
        """
        template_vars = {}

        for var_name, var_config in self.config['template_variables'].items():
            cli_arg = var_config['cli_arg'].lstrip('-').replace('-', '_')
            value = getattr(args, cli_arg, None)

            if value is not None:
                template_vars[var_name] = str(value)

        return template_vars

    def run(self, args: argparse.Namespace):
        """
        Execute the RAVL loop

        Args:
            args: Parsed command-line arguments
        """
        # Setup paths
        markdown_file = self.loop_dir / self.config.get('markdown_file', 'ravl_loop.md')

        # Use provided learning_path if available, otherwise default to loop_dir/learnings
        if hasattr(args, 'learning_path') and args.learning_path:
            learnings_dir = Path(args.learning_path)
        else:
            learnings_dir = self.loop_dir / 'learnings'

        logs_dir = learnings_dir / 'logs'

        # Setup logging
        loop_name = self.config['name']
        tee_logger = RAVLRunner.setup_logging(logs_dir, loop_name)

        # Extract template variables
        context_vars = self.extract_template_vars(args)

        # Display startup info
        print(f"➿ {self.config.get('description', loop_name)} starting...", file=sys.stderr)
        for var_name, var_value in context_vars.items():
            print(f"   {var_name}: {var_value}", file=sys.stderr)
        print(f"   Mode: {args.mode}", file=sys.stderr)

        start_time = time.time()

        try:
            # Read markdown file
            if not markdown_file.exists():
                raise FileNotFoundError(f"Markdown file not found: {markdown_file}")

            with open(markdown_file, 'r', encoding='utf-8') as f:
                markdown_text = f.read()

            # Copy original markdown to current_state/ for reference
            current_state_dir = learnings_dir / 'current_state'
            current_state_dir.mkdir(parents=True, exist_ok=True)
            source_copy = current_state_dir / 'ravl_loop.md'
            with open(source_copy, 'w', encoding='utf-8') as f:
                f.write(markdown_text)

            # Perform template substitution
            for var_name, var_value in context_vars.items():
                markdown_text = markdown_text.replace(f"{{{var_name}}}", var_value)

            # Initialize executor
            executor = MarkdownRAVLExecutor(
                markdown_text=markdown_text,
                loop_dir=self.loop_dir,
                learnings_dir=learnings_dir,
                context_vars=context_vars
            )

            # ===== Step 1: REFLECT =====
            RAVLRunner.print_banner("Step 1 of 4: [R]EFLECT", "")
            reflection = executor.reflect()

            # Calculate duration
            duration = time.time() - start_time
            print(f"\n   ✓ Completed at {duration:.1f}s", file=sys.stderr)

            # ===== Step 2: ACT =====
            RAVLRunner.print_banner("Step 2 of 4: [A]CT", "")
            action_result = executor.act(reflection)

            # Calculate duration
            duration = time.time() - start_time
            print(f"\n   ✓ Completed at {duration:.1f}s", file=sys.stderr)

            # ===== Step 3: VERIFY =====
            if not args.no_deep_learning:

                RAVLRunner.print_banner("Phase 3 of 4: [V]ERIFY", "")

                # Load previous action for verification from loop_learning/recent_attempts/
                recent_attempts_dir = learnings_dir / 'loop_learning' / 'recent_attempts'
                previous_action = None

                if recent_attempts_dir.exists():
                    # Find attempt folders and get second-most recent
                    attempt_folders = sorted(
                        [f for f in recent_attempts_dir.iterdir() if f.is_dir() and f.name.startswith('attempt_')],
                        key=lambda f: int(f.name.split('_')[1])
                    )
                    if len(attempt_folders) >= 2:
                        previous_action_file = attempt_folders[-2] / 'domain_action.json'
                        if previous_action_file.exists():
                            with open(previous_action_file, 'r', encoding='utf-8') as f:
                                previous_action = json.load(f)

                verification = executor.verify(previous_action, reflection)

                # Calculate duration
                duration = time.time() - start_time
                print(f"\n   ✓ Completed at {duration:.1f}s", file=sys.stderr)

                RAVLRunner.print_banner("Step 4 of 4: [L]EARN", "")
                executor.learn(verification, action_result)

                # Calculate duration
                duration = time.time() - start_time
                print(f"\n   ✓ Completed at {duration:.1f}s", file=sys.stderr)

            # Show interpretation summary if LLM interpreted the loop
            if executor.used_interpretation:
                RAVLRunner.print_banner("INTERPRETATION APPLIED", "📚")
                print(f"   Your free-form markdown was structured into RAVL phases", file=sys.stderr)
                print(f"", file=sys.stderr)
                print(f"   Review:  cat {learnings_dir.name}/current_state/ravl_loop_enhanced.md", file=sys.stderr)
                print(f"   Learn:   .ravl/docs/free_form_interpretation.md", file=sys.stderr)
                print(f"", file=sys.stderr)
                print(f"   To refine for future runs:", file=sys.stderr)
                print(f"     1. Review the enhanced version", file=sys.stderr)
                print(f"     2. Update ravl_loop.md with any tweaks", file=sys.stderr)
                print(f"     3. Next run will use your updated structure", file=sys.stderr)

            # Check if verification failed and suggest diagnostician
            verification_passed = (
                not args.no_deep_learning
                and verification
                and verification.get("overall_passed", False)
            )

            if not args.no_deep_learning and verification and not verification.get("overall_passed", False):
                RAVLRunner.print_banner("VERIFICATION FAILED", "⚠️")
                print(f"   The loop ran but didn't meet all verification criteria.", file=sys.stderr)

                # Display detailed verification criteria results
                domain_verification = verification.get('domain', {})
                criteria_results = domain_verification.get('criteria_results', [])

                if criteria_results:
                    print(f"", file=sys.stderr)
                    print(f"   📋 Verification Details:", file=sys.stderr)
                    for i, criterion in enumerate(criteria_results, 1):
                        status = "✓" if criterion.get('passed', False) else "✗"
                        criterion_name = criterion.get('criterion', 'Unknown criterion')
                        print(f"      {status} [{i}] {criterion_name}", file=sys.stderr)

                        # Show explanation for failed criteria
                        if not criterion.get('passed', False) and criterion.get('explanation'):
                            explanation = criterion['explanation']
                            # Truncate long explanations for readability
                            if len(explanation) > 100:
                                explanation = explanation[:100] + "..."
                            print(f"          {explanation}", file=sys.stderr)

                print(f"", file=sys.stderr)
                print(f"   Understand config and get diagnostic suggestions:", file=sys.stderr)
                print(f"     ravl {loop_name} --show-config", file=sys.stderr)
                print(f"     ravl --loop-health {loop_name} # loop agentic health", file=sys.stderr)
                print(f"     ravl --execution-health {loop_name} # loop execution health", file=sys.stderr)
                print(f"", file=sys.stderr)

            # Success/completion summary
            completion_status = "completed successfully" if verification_passed else "completed with errors"
            RAVLRunner.print_banner(f"{loop_name} {completion_status}", "🏁")
            print(f"   Duration: {duration:.1f}s", file=sys.stderr)
            for var_name, var_value in context_vars.items():
                print(f"   {var_name}: {var_value}", file=sys.stderr)
            print(f"   Output: {action_result.get('output_file', 'N/A')}", file=sys.stderr)
            print("=" * 80, file=sys.stderr)

            # Close logger
            tee_logger.close()
            sys.exit(0)

        except (KeyboardInterrupt, Exception) as e:
            RAVLRunner.handle_error(e, tee_logger)


def main():
    """Main entry point"""
    # Initial parser for --config and --loop-dir
    initial_parser = argparse.ArgumentParser(add_help=False)
    initial_parser.add_argument(
        '--config',
        type=Path,
        help='Path to config.yml file'
    )
    initial_parser.add_argument(
        '--loop-dir',
        type=Path,
        help='Path to loop directory (will look for config.yml inside)'
    )
    initial_parser.add_argument(
        '--learning-path',
        type=str,
        default=None,
        help='Override learning directory path'
    )
    initial_parser.add_argument(
        '--venv-path',
        type=str,
        default=None,
        help='Override virtual environment path'
    )
    initial_parser.add_argument(
        '--show-config',
        action='store_true',
        help='Display resolved configuration without executing the loop'
    )

    # Parse just these arguments first
    initial_args, remaining_argv = initial_parser.parse_known_args()

    # Determine config path
    config_path = None

    if initial_args.config:
        config_path = initial_args.config
    elif initial_args.loop_dir:
        # Try config locations in order:
        # 1. config/config.yml (old markdown loops with separate config)
        # 2. config/ravl.yml (new: everything in ravl.yml)
        # 3. config.yml (legacy: root level)
        config_path = initial_args.loop_dir / 'config' / 'config.yml'
        if not config_path.exists():
            config_path = initial_args.loop_dir / 'config' / 'ravl.yml'
        if not config_path.exists():
            config_path = initial_args.loop_dir / 'config.yml'
    else:
        print("Error: Must specify either --config or --loop-dir", file=sys.stderr)
        print("", file=sys.stderr)
        print("Usage:", file=sys.stderr)
        print("  python3 run_markdown_ravl.py --loop-dir path/to/loop [options]", file=sys.stderr)
        print("  python3 run_markdown_ravl.py --config path/to/config.yml [options]", file=sys.stderr)
        sys.exit(1)

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    # Create runner and parse full arguments
    try:
        runner = ConfigBasedRAVLRunner(config_path)
        parser = runner.create_argument_parser()

        # Re-parse with full argument list
        sys.argv = [sys.argv[0]] + remaining_argv
        args = parser.parse_args()

        # Pass learning path to runner if provided
        if initial_args.learning_path:
            args.learning_path = initial_args.learning_path

        # Handle --show-config: Display configuration and exit
        if initial_args.show_config:
            # Find project root
            from cli.ravl_cli_base import RAVLCLIBase
            project_root = RAVLCLIBase.find_project_root()

            # Resolve all paths
            learning_path = RAVLRunner.resolve_learning_path(
                loop_dir=runner.loop_dir,
                loop_config=runner.config,
                cli_learning_path=Path(initial_args.learning_path) if initial_args.learning_path else None,
                project_root=project_root
            )
            venv_path = RAVLRunner.resolve_venv_path(
                loop_dir=runner.loop_dir,
                loop_config=runner.config,
                cli_venv_path=Path(initial_args.venv_path) if initial_args.venv_path else None,
                project_root=project_root
            )

            # Determine sources (simplified for markdown loops)
            learning_path_source = "CLI (--learning-path)" if initial_args.learning_path else "Default"
            venv_path_source = "CLI (--venv-path)" if initial_args.venv_path else "Default"
            loop_dir_source = "CLI (--loop-dir)" if initial_args.loop_dir else "Default"

            # Create args object with necessary attributes for ConfigDisplay
            class ShowConfigArgs:
                def __init__(self):
                    self.loop = str(runner.loop_dir.name)
                    self.mode = getattr(args, 'mode', 'full')
                    self.no_deep_learning = getattr(args, 'no_deep_learning', False)
                    self.timeout = getattr(args, 'timeout', DEFAULT_EXECUTION_TIMEOUT)
                    self.quiet = False
                    self.learning_path = initial_args.learning_path
                    self.venv_path = initial_args.venv_path
                    self.loop_dir = str(initial_args.loop_dir) if initial_args.loop_dir else None

            show_args = ShowConfigArgs()

            # Display configuration
            ConfigDisplay.show(
                loop_dir=runner.loop_dir,
                learning_path=learning_path,
                venv_path=venv_path,
                loop_config=runner.config,
                args=show_args,
                project_root=project_root,
                learning_path_source=learning_path_source,
                venv_path_source=venv_path_source,
                loop_dir_source=loop_dir_source
            )
            sys.exit(0)

        # Run the loop
        runner.run(args)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
