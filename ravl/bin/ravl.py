#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
RAVL - Universal RAVL Loop Runner

Execute any RAVL loop by name or path.

Usage:
    ravl <loop-name-or-path> [options]

Examples:
    ravl external_drift --mode fast
    ravl ravl_loops/strategy_guardian --mode full
    ravl . --mode fast  # From within loop directory

Standard Options:
    --mode {fast|full}      Analysis mode (default: full)
    --no-deep-learning      Skip verify and learn phases
    --timeout SECONDS       Timeout in seconds (default: 300)

Run 'ravl-list' to see available loops.
"""

import sys
import argparse
import time
import json
import inspect
import os
import yaml
import tomli_w
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Bootstrap: Add framework to path
# Works for both UV installation and .ravl submodule
# __file__ is .ravl/ravl/bin/ravl.py, so parent.parent.parent gives .ravl/
_current = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_current))

# Use absolute imports that work both from source and installed package
from ravl.common.cli.ravl_cli_base import RAVLCLIBase
from ravl.common.cli.loop_discovery import LoopDiscovery
from ravl.common.ravl_runner import RAVLRunner
from ravl.common.cli.config_display import ConfigDisplay
from ravl.common.utils.constants import DEFAULT_EXECUTION_TIMEOUT
from ravl.common.core.initialization_failure_tracker import InitializationFailureTracker

# Show helpful message if called directly (not via wrapper)
def _show_wrapper_hint():
    """Show helpful message once per session if called directly"""
    hint_env = 'RAVL_WRAPPER_HINT_SHOWN'

    # Only show once per shell session
    if os.environ.get(hint_env):
        return

    os.environ[hint_env] = '1'

    project_root = Path(__file__).resolve().parent.parent.parent
    script_name = Path(sys.argv[0]).name

    # Only show if called as .ravl/bin/ravl (direct call, not via wrapper)
#    if '.ravl/bin' in str(Path(sys.argv[0]).resolve()):
#        print(
#            "\n💡 Tip: You can use './ravl' instead of './.ravl/bin/ravl'!",
#            file=sys.stderr
#        )
#        print(
#            "   Try: ravl --list    (list all loops)",
#            file=sys.stderr
#        )
#        print(
#            "        ravl --help    (show all options)",
#            file=sys.stderr
#        )
#        print(
#            "   See README.md for setup options.",
#            file=sys.stderr
#        )
#        print(file=sys.stderr)

# Show the helpful message on first direct call
_show_wrapper_hint()


class RAVLUniversalRunner(RAVLCLIBase):
    """Universal runner for any RAVL loop"""

    def __init__(self, loops_dir: Optional[Path] = None):
        """Initialize universal runner

        Args:
            loops_dir: Optional custom path for project loops
        """
        # Find project root (uses CWD as fallback if outside RAVL project)
        self.project_root = self.find_project_root(required=False)

        # Load .env file and set all variables in environment
        env_vars = RAVLRunner.load_env_file(self.project_root)
        for key, value in env_vars.items():
            # Only set if not already in environment (don't override existing)
            if key not in os.environ:
                os.environ[key] = value

        self.discovery = LoopDiscovery(self.project_root, loops_dir=loops_dir)

    def _determine_learning_path_source(
        self,
        loop_dir: Path,
        config: Dict[str, Any],
        cli_path: Optional[Path]
    ) -> str:
        """Determine which source provided the learning path"""
        if cli_path:
            return "CLI (--learning-path)"
        if config and 'learning_path' in config:
            return "Loop config (config/ravl.toml)"

        # Check parent configs (walk full parent chain)
        all_parents = RAVLRunner._find_all_parent_loops(loop_dir)
        for parent_dir in all_parents:
            parent_config_file = parent_dir / 'config' / 'ravl.toml'
            if parent_config_file.exists():
                try:
                    import tomllib
                    with open(parent_config_file, 'rb') as f:
                        parent_config = tomllib.load(f) or {}
                        if 'learning_path' in parent_config:
                            return f"Parent config ({parent_dir.name}/config/ravl.toml)"
                except Exception:
                    pass

        return "Default (loop_dir/learnings)"

    def _determine_venv_path_source(
        self,
        loop_dir: Path,
        config: Dict[str, Any],
        cli_path: Optional[Path]
    ) -> str:
        """Determine which source provided the venv path"""
        if cli_path:
            return "CLI (--venv-path)"
        if config and 'venv_path' in config:
            return "Loop config (config/ravl.toml)"

        # Check project config
        project_config_file = self.project_root / 'ravl_loops' / 'config' / 'ravl.toml'
        if project_config_file.exists():
            try:
                import toml
                with open(project_config_file, 'rb') as f:
                    project_config = tomllib.load(f) or {}
                    if 'venv_path' in project_config:
                        return "Project config (ravl_loops/config/ravl.toml)"
            except Exception:
                pass

        # Check .env
        env_vars = RAVLRunner.load_env_file(self.project_root)
        if 'RAVL_DEFAULT_VENV_DIRECTORY' in env_vars:
            return "Environment (.env RAVL_DEFAULT_VENV_DIRECTORY)"

        return "Default (.ravl/venv)"

    def _determine_loop_dir_source(self, cli_dir: Optional[Path]) -> str:
        """Determine which source provided the loop directory"""
        if cli_dir:
            return "CLI (--loop-dir)"

        # Check .env
        env_vars = RAVLRunner.load_env_file(self.project_root)
        if 'RAVL_DEFAULT_LOOP_DIRECTORY' in env_vars:
            return "Environment (.env RAVL_DEFAULT_LOOP_DIRECTORY)"

        return "Default (project_root/ravl_loops)"

    def run(self, args: argparse.Namespace):
        """
        Execute a RAVL loop

        Args:
            args: Parsed command-line arguments
        """
        # Find loop directory
        try:
            loop_dir = self.discovery.find_loop(args.loop)
        except ValueError as e:
            self.print_error(str(e))
            sys.exit(1)

        # Check if this is an example loop
        if self.discovery.is_example_loop(loop_dir):
            loop_name = loop_dir.name

            # Strip example_n_ prefix for target name
            import re
            match = re.match(r'^example_\d+_(.+)$', loop_name)
            if match:
                target_name = match.group(1)
            else:
                target_name = loop_name

            target_path = self.project_root / 'ravl_loops' / target_name

            # Check if already cloned
            if target_path.exists():
                print(f"\nℹ️  Example '{loop_name}' already cloned to ravl_loops/{target_name}/", file=sys.stderr)
                print(f"   Running from: {target_path.relative_to(self.project_root)}\n", file=sys.stderr)
                loop_dir = target_path
            else:
                # Prompt user to clone
                print(f"\n📚 '{loop_name}' is an example loop.", file=sys.stderr)
                print(f"   Examples should be cloned to ravl_loops/ before running.\n", file=sys.stderr)

                response = input(f"Clone to ravl_loops/{target_name}? (y/n): ").strip().lower()

                if response in ['y', 'yes']:
                    # Clone the example (ravl_clone.py will auto-strip the prefix)
                    import subprocess
                    clone_cmd = [
                        sys.executable,
                        str(self.find_framework_root() / 'ravl' / 'bin' / 'ravl_clone.py'),
                        loop_name
                        # No target name - let ravl_clone.py auto-strip the prefix
                    ]
                    result = subprocess.run(clone_cmd, capture_output=False)

                    if result.returncode != 0:
                        self.print_error(f"Failed to clone example: {loop_name}")
                        sys.exit(1)

                    # Update loop_dir to cloned location
                    loop_dir = target_path
                    print(f"\n✅ Example cloned successfully\n", file=sys.stderr)
                else:
                    print(f"\n❌ Clone declined. Use 'ravl --clone {loop_name} <name>' to clone manually.\n", file=sys.stderr)
                    sys.exit(0)

        # Load configuration
        try:
            config = self.discovery.load_config(loop_dir)
        except Exception as e:
            self.print_error(f"Failed to load configuration: {e}")
            sys.exit(1)

        # Initialize execution logging visibility
        # This must be set before any loop execution to control message visibility
        from ravl.common.utils.logging_utils import set_show_execution
        if hasattr(args, 'show_execution') and args.show_execution:
            set_show_execution(True)
            os.environ['RAVL_SHOW_EXECUTION'] = '1'  # For subprocess consistency

        # Detect loop type and route accordingly
        is_markdown_loop = (loop_dir / 'ravl_loop.md').exists()
        is_python_loop = (loop_dir / 'ravl_loop.py').exists()

        if not is_markdown_loop and not is_python_loop:
            self.print_error(
                f"No loop implementation found in {loop_dir}\n"
                f"  Expected either: ravl_loop.py or ravl_loop.md"
            )
            sys.exit(1)

        # Handle --show-config: Display configuration and exit
        if args.show_config:
            # Resolve all paths
            learning_path = RAVLRunner.resolve_learning_path(
                loop_dir=loop_dir,
                loop_config=config,
                cli_learning_path=Path(args.learning_path) if args.learning_path else None,
                project_root=self.project_root
            )
            venv_path = RAVLRunner.resolve_venv_path(
                loop_dir=loop_dir,
                loop_config=config,
                cli_venv_path=Path(args.venv_path) if hasattr(args, 'venv_path') and args.venv_path else None,
                project_root=self.project_root
            )

            # Determine sources
            learning_path_source = self._determine_learning_path_source(
                loop_dir, config, Path(args.learning_path) if args.learning_path else None
            )
            venv_path_source = self._determine_venv_path_source(
                loop_dir, config, Path(args.venv_path) if hasattr(args, 'venv_path') and args.venv_path else None
            )
            loop_dir_source = self._determine_loop_dir_source(
                Path(args.loop_dir) if args.loop_dir else None
            )

            # Display configuration
            ConfigDisplay.show(
                loop_dir=loop_dir,
                learning_path=learning_path,
                venv_path=venv_path,
                loop_config=config,
                args=args,
                project_root=self.project_root,
                learning_path_source=learning_path_source,
                venv_path_source=venv_path_source,
                loop_dir_source=loop_dir_source
            )
            sys.exit(0)

        # Check for delegation - resolve chain and execute delegated loop
        delegation = self.discovery.detect_delegation(config)
        if delegation:
            self._run_delegated_loop(loop_dir, config, args)
            return

        # Check if this is a markdown loop - delegate to markdown runner
        if is_markdown_loop:
            self._run_markdown_loop(loop_dir, config, args)
            return

        # Display startup info (unless in quiet mode)
        emoji = config.get('emoji', '➿')
        name = config.get('description', loop_dir.name)

        if not args.quiet:
            print(f"\n{emoji} {name}", file=sys.stderr)
            print(f"   Mode: {args.mode}", file=sys.stderr)
            print(f"   Timeout: {args.timeout}s", file=sys.stderr)
            print(f"   Deep learning: {not args.no_deep_learning}", file=sys.stderr)

        start_time = time.time()

        # Set RAVL_QUIET environment variable if quiet mode enabled
        if args.quiet:
            os.environ['RAVL_QUIET'] = '1'

        # Resolve learning path BEFORE importing loop class
        # (ensures we can write failure records even if import fails)
        learning_path = RAVLRunner.resolve_learning_path(
            loop_dir=loop_dir,
            loop_config=config,
            cli_learning_path=Path(args.learning_path) if args.learning_path else None,
            project_root=self.project_root
        )

        try:
            # Import loop class - catch import/discovery failures
            try:
                LoopClass = self.discovery.import_loop_class(loop_dir, config)
            except ImportError as e:
                # Record initialization failure
                context = {
                    "loop_dir": str(loop_dir),
                    "loop_file": str(loop_dir / config.get('python_file', 'ravl_loop.py')),
                    "expected_class": config.get('name', loop_dir.name) + "Loop" if 'class_name' not in config else config['class_name']
                }

                # Try to extract available classes from error message
                error_msg = str(e)
                if "Available:" in error_msg:
                    available_str = error_msg.split("Available:")[1].strip()
                    context["available_classes"] = available_str

                InitializationFailureTracker.record_failure(
                    learning_path,
                    e,
                    "import",
                    context=context
                )

                # Re-raise to trigger outer exception handler
                raise

            # Initialize loop with resolved learning path
            loop_instance = self._initialize_loop(LoopClass, loop_dir, config, learning_path)

            # Load previous findings for learning
            previous_findings = self._load_previous_findings(loop_dir)

            # Run RAVL phases
            action_results = RAVLRunner.run_ravl_phases(
                loop_instance,
                previous_findings=previous_findings,
                deep_learning=not args.no_deep_learning,
                quiet=args.quiet
            )

            # Save results
            self._save_results(learning_path, action_results, args.mode, time.time() - start_time)

            # Print summary (unless in quiet mode)
            duration = time.time() - start_time
            if not args.quiet:
                RAVLRunner.print_summary(action_results, duration, name)

            sys.exit(0)

        except KeyboardInterrupt:
            self.print_error("Interrupted by user")
            sys.exit(1)
        except Exception as e:
            # Record all other initialization/execution failures
            if not isinstance(e, ImportError):  # ImportError already recorded above
                context = {
                    "loop_dir": str(loop_dir),
                    "phase": "initialization or execution"
                }

                # Determine failure phase
                if "initialize" in str(e).lower():
                    phase = "initialization"
                elif "config" in str(e).lower():
                    phase = "configuration"
                else:
                    phase = "execution"

                InitializationFailureTracker.record_failure(
                    learning_path,
                    e,
                    phase,
                    context=context
                )

            self.print_error(f"Execution failed: {e}")
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)

    def _run_delegated_loop(self, wrapper_loop_dir: Path, wrapper_config: Dict[str, Any], args: argparse.Namespace):
        """
        Run a loop that delegates to another loop (framework or project)

        Args:
            wrapper_loop_dir: Wrapper loop directory (caller)
            wrapper_config: Wrapper loop configuration with delegate_to
            args: Parsed arguments from universal runner
        """
        # Resolve delegation chain
        try:
            final_loop_dir, chain, merged_config = self.discovery.resolve_delegation_chain(
                wrapper_loop_dir,
                wrapper_config
            )
        except ValueError as e:
            self.print_error(f"Delegation error: {e}")
            sys.exit(1)

        # Display delegation info (unless quiet)
        if not args.quiet:
            emoji = wrapper_config.get('emoji', '➿')
            name = wrapper_config.get('description', wrapper_loop_dir.name)
            chain_names = [Path(p).name for p in chain]
            chain_str = ' → '.join(chain_names)

            print(f"\n{emoji} {name}", file=sys.stderr)
            print(f"   Delegation: {chain_str}", file=sys.stderr)
            print(f"   Mode: {args.mode}", file=sys.stderr)
            print(f"   Timeout: {args.timeout}s", file=sys.stderr)

        # Resolve learning path for WRAPPER loop (not delegate)
        # This ensures learning artifacts go to the wrapper's directory
        learning_path = RAVLRunner.resolve_learning_path(
            loop_dir=wrapper_loop_dir,
            loop_config=wrapper_config,
            cli_learning_path=Path(args.learning_path) if args.learning_path else None,
            project_root=self.project_root
        )

        # Check if final loop is markdown or Python
        is_markdown_loop = (final_loop_dir / 'ravl_loop.md').exists()

        if is_markdown_loop:
            # Delegate to markdown runner with merged config
            # Save merged config temporarily to learning directory
            temp_config_file = learning_path / '_merged_config.toml'
            temp_config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_config_file, 'wb') as f:
                tomli_w.dump(merged_config, f)

            # Run markdown loop with final loop dir but wrapper learning path
            import subprocess
            markdown_runner_path = self.find_framework_root() / 'ravl' / 'common' / 'llm' / 'run_markdown_ravl.py'
            cmd = [
                sys.executable,
                str(markdown_runner_path),
                '--loop-dir', str(final_loop_dir),
                '--mode', args.mode,
                '--learning-path', str(learning_path)
            ]

            if args.no_deep_learning:
                cmd.append('--no-deep-learning')
            if args.timeout != DEFAULT_EXECUTION_TIMEOUT:
                cmd.extend(['--timeout', str(args.timeout)])

            result = subprocess.run(cmd)

            # Cleanup temp config
            if temp_config_file.exists():
                temp_config_file.unlink()

            sys.exit(result.returncode)
        else:
            # Python loop - import and execute with merged config
            try:
                LoopClass = self.discovery.import_loop_class(final_loop_dir, merged_config)
            except ImportError as e:
                # Record initialization failure to wrapper's learning path
                context = {
                    "loop_dir": str(final_loop_dir),
                    "wrapper_loop_dir": str(wrapper_loop_dir),
                    "delegation_chain": [Path(p).name for p in chain] + [final_loop_dir.name]
                }
                InitializationFailureTracker.record_failure(
                    learning_path,
                    e,
                    "import_delegated",
                    context=context
                )
                raise

            # Write merged config to temporary file for loops that read from config_path
            temp_config_file = learning_path / '_merged_config.toml'
            temp_config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_config_file, 'wb') as f:
                tomli_w.dump(merged_config, f)

            try:
                # Initialize loop with wrapper's learning path and merged config
                loop_instance = self._initialize_loop_with_merged_config(
                    LoopClass, final_loop_dir, merged_config, learning_path, temp_config_file
                )
            finally:
                # Clean up temporary config file
                if temp_config_file.exists():
                    temp_config_file.unlink()

            # Execute RAVL phases with execution metadata tracking
            previous_findings = self._load_previous_findings(wrapper_loop_dir)

            # Initialize execution_learning directory
            if hasattr(loop_instance, 'initialize_execution_learning'):
                loop_instance.initialize_execution_learning()

            # Track execution metadata
            from datetime import datetime, timezone
            import time
            import traceback

            execution_metadata = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'loop_name': wrapper_config.get('description', wrapper_loop_dir.name),
                'phases': {},
                'success': False,
                'error': None
            }

            start_time = time.time()

            try:
                # REFLECT phase
                phase_start = time.time()
                reflection = loop_instance.reflect()
                execution_metadata['phases']['reflect'] = {
                    'duration_seconds': time.time() - phase_start,
                    'success': True
                }

                # ACT phase
                phase_start = time.time()
                action_result = loop_instance.act(reflection)
                execution_metadata['phases']['act'] = {
                    'duration_seconds': time.time() - phase_start,
                    'success': True
                }

                # VERIFY phase
                phase_start = time.time()
                verification_result = loop_instance.verify(action_result, reflection)
                execution_metadata['phases']['verify'] = {
                    'duration_seconds': time.time() - phase_start,
                    'success': True
                }

                # LEARN phase
                phase_start = time.time()
                loop_instance.learn(verification_result, action_result)
                execution_metadata['phases']['learn'] = {
                    'duration_seconds': time.time() - phase_start,
                    'success': True
                }

                execution_metadata['success'] = True

            except Exception as e:
                execution_metadata['success'] = False
                execution_metadata['error'] = {
                    'type': type(e).__name__,
                    'message': str(e),
                    'traceback': traceback.format_exc()
                }
                raise  # Re-raise after recording

            finally:
                # Record total duration
                execution_metadata['duration_seconds'] = time.time() - start_time

                # Write execution metadata if loop supports it
                if hasattr(loop_instance, 'write_execution_metadata'):
                    try:
                        loop_instance.write_execution_metadata(execution_metadata)
                    except Exception as meta_error:
                        # Don't fail the loop if metadata writing fails
                        if not args.quiet:
                            print(f"Warning: Could not write execution metadata: {meta_error}", file=sys.stderr)

            # Display completion message
            if not args.quiet:
                print(f"\n✅ {wrapper_config.get('description', wrapper_loop_dir.name)} completed successfully", file=sys.stderr)

    def _run_markdown_loop(self, loop_dir: Path, config: Dict[str, Any], args: argparse.Namespace):
        """
        Run a markdown-based RAVL loop by delegating to markdown runner

        Args:
            loop_dir: Path to loop directory
            config: Loop configuration
            args: Parsed arguments from universal runner
        """
        # Import markdown runner
        markdown_runner_path = self.find_framework_root() / 'ravl' / 'common' / 'llm' / 'run_markdown_ravl.py'

        if not markdown_runner_path.exists():
            self.print_error(
                "Markdown runner not found. Markdown loops are not yet supported.\n"
                f"  Expected: {markdown_runner_path}"
            )
            sys.exit(1)

        # Resolve learning path with proper precedence
        learning_path = RAVLRunner.resolve_learning_path(
            loop_dir=loop_dir,
            loop_config=config,
            cli_learning_path=Path(args.learning_path) if args.learning_path else None,
            project_root=self.project_root
        )

        # Build command for markdown runner
        cmd = [
            sys.executable,
            str(markdown_runner_path),
            '--loop-dir', str(loop_dir),
            '--mode', args.mode,
            '--learning-path', str(learning_path)
        ]

        if args.no_deep_learning:
            cmd.append('--no-deep-learning')

        if args.timeout != DEFAULT_EXECUTION_TIMEOUT:  # Only add if non-default
            cmd.extend(['--timeout', str(args.timeout)])

        if args.show_config:
            cmd.append('--show-config')

        if hasattr(args, 'show_execution') and args.show_execution:
            cmd.append('--show-execution')

        if hasattr(args, 'venv_path') and args.venv_path:
            cmd.extend(['--venv-path', str(args.venv_path)])

        # Add any loop-specific arguments that were passed (e.g., --role for role_ambitions)
        if hasattr(args, 'unknown_args'):
            cmd.extend(args.unknown_args)

        # Execute markdown runner
        import subprocess
        result = subprocess.run(cmd)
        sys.exit(result.returncode)

    def _initialize_loop_with_merged_config(
        self,
        LoopClass,
        loop_dir: Path,
        config: Dict[str, Any],
        learning_path: Optional[Path],
        merged_config_file: Path
    ):
        """
        Initialize loop with merged config from delegation

        Args:
            LoopClass: Loop class to initialize
            loop_dir: Path to loop directory
            config: Merged configuration
            learning_path: Resolved learning path
            merged_config_file: Path to temporary merged config file

        Returns:
            Initialized loop instance
        """
        # Get constructor signature
        sig = inspect.signature(LoopClass.__init__)
        params = {}

        # Auto-resolve parameters, using merged_config_file for config_path
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            # Special handling for config_path - use merged config file
            if param_name == 'config_path':
                params[param_name] = str(merged_config_file)
            else:
                # Try to resolve parameter normally
                resolved = self._resolve_parameter(param_name, loop_dir, config, learning_path)

                if resolved is not None:
                    params[param_name] = resolved
                elif param.default == inspect.Parameter.empty:
                    # Required parameter without default
                    self.print_warning(
                        f"Could not resolve required parameter: {param_name}\n"
                        f"  Add to ravl.toml under 'init_params' or implement auto-resolution"
                    )

        # Add parameters from config
        config_params = config.get('init_params', {})
        for key, value in config_params.items():
            if key not in params:
                # Resolve special values
                if value == 'auto' and key == 'handbook_root':
                    params[key] = str(self.project_root)
                elif isinstance(value, str) and not Path(value).is_absolute():
                    # Resolve relative paths
                    params[key] = str(loop_dir / value)
                else:
                    params[key] = value

        try:
            return LoopClass(**params)
        except TypeError as e:
            self.print_error(f"Failed to initialize {LoopClass.__name__}: {e}")
            self.print_info(f"Resolved parameters: {list(params.keys())}")
            raise

    def _initialize_loop(self, LoopClass, loop_dir: Path, config: Dict[str, Any], learning_path: Optional[Path] = None):
        """
        Initialize loop with smart parameter resolution

        Args:
            LoopClass: Loop class to initialize
            loop_dir: Path to loop directory
            config: Loop configuration
            learning_path: Optional resolved learning path

        Returns:
            Initialized loop instance
        """
        # Get constructor signature
        sig = inspect.signature(LoopClass.__init__)
        params = {}

        # Auto-resolve common parameters based on conventions
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            # Try to resolve parameter
            resolved = self._resolve_parameter(param_name, loop_dir, config, learning_path)

            if resolved is not None:
                params[param_name] = resolved
            elif param.default == inspect.Parameter.empty:
                # Required parameter without default
                self.print_warning(
                    f"Could not resolve required parameter: {param_name}\n"
                    f"  Add to ravl.toml under 'init_params' or implement auto-resolution"
                )

        # Add parameters from config
        config_params = config.get('init_params', {})
        for key, value in config_params.items():
            if key not in params:
                # Resolve special values
                if value == 'auto' and key == 'handbook_root':
                    params[key] = str(self.project_root)
                elif isinstance(value, str) and not Path(value).is_absolute():
                    # Resolve relative paths
                    params[key] = str(loop_dir / value)
                else:
                    params[key] = value

        try:
            return LoopClass(**params)
        except TypeError as e:
            self.print_error(f"Failed to initialize {LoopClass.__name__}: {e}")
            self.print_info(f"Resolved parameters: {list(params.keys())}")
            raise

    def _resolve_parameter(self, param_name: str, loop_dir: Path, config: Dict[str, Any], learning_path: Optional[Path] = None) -> Optional[Any]:
        """
        Auto-resolve common parameter patterns

        Args:
            param_name: Parameter name
            loop_dir: Loop directory
            config: Loop configuration
            learning_path: Optional resolved learning path

        Returns:
            Resolved value or None
        """
        # Common parameter conventions
        if param_name == 'model_path':
            # Use resolved learning path if provided, otherwise default
            if learning_path:
                model_file = learning_path / 'model.yml'
            else:
                model_file = loop_dir / 'learnings' / 'model.yml'
            return str(model_file)

        elif param_name == 'learnings_dir':
            # Use resolved learning path if provided, otherwise default
            if learning_path:
                learnings_dir = learning_path
            else:
                learnings_dir = loop_dir / 'learnings'
            return str(learnings_dir)

        elif param_name == 'config_path':
            # Find first config file in config directory
            config_dir = loop_dir / 'config'
            if config_dir.exists():
                configs = list(config_dir.glob('*.yml'))
                if configs:
                    return str(configs[0])

        elif param_name == 'sources_config_path':
            # Specific to loops that fetch external sources
            sources_file = loop_dir / 'config' / 'strategic_sources.yml'
            if sources_file.exists():
                return str(sources_file)

        elif param_name == 'handbook_root':
            return str(self.project_root)

        elif param_name.endswith('_path') and '_config' in param_name:
            # Try to find config file matching pattern
            config_name = param_name.replace('_path', '.yml').replace('_config', '_config')
            config_file = loop_dir / 'config' / config_name
            if config_file.exists():
                return str(config_file)

        elif param_name.endswith('_loop'):
            # Auto-resolve nested loop parameters (e.g., workspace_loop, hibob_loop)
            # Extract loop name from parameter (workspace_loop -> workspace)
            loop_name = param_name.replace('_loop', '')

            # Check for nested loop in ravl_loops subdirectory
            nested_loop_dir = loop_dir / 'ravl_loops' / loop_name
            if nested_loop_dir.exists():
                # Recursively initialize the nested loop
                try:
                    nested_config = self.discovery.load_config(nested_loop_dir)
                    nested_class = self.discovery.import_loop_class(nested_loop_dir, nested_config)

                    # Resolve learning path for the nested loop
                    # Child loops inherit parent's learning path + their name + /learnings
                    if learning_path:
                        nested_learning_path = learning_path / loop_name / 'learnings'
                    else:
                        nested_learning_path = nested_loop_dir / 'learnings'

                    # Initialize nested loop with resolved learning path
                    return self._initialize_loop(nested_class, nested_loop_dir, nested_config, nested_learning_path)
                except Exception as e:
                    print(f"  ⚠️  Warning: Could not auto-resolve {param_name}: {e}", file=sys.stderr)
                    return None

        return None

    def _load_previous_findings(self, loop_dir: Path) -> Optional[Dict[str, Any]]:
        """Load previous findings for learning"""
        findings_file = loop_dir / 'learnings' / 'latest_run.json'
        if findings_file.exists():
            try:
                with open(findings_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return None

    def _save_results(self, learning_path: Path, action_results: Dict[str, Any], mode: str, duration: float):
        """Save action results to latest_run.json in the resolved learning path"""
        findings_file = learning_path / 'latest_run.json'
        findings_file.parent.mkdir(parents=True, exist_ok=True)

        findings = {
            **action_results,
            'metadata': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'duration_seconds': round(duration, 1),
                'run_type': mode,
                'standalone': True
            }
        }

        with open(findings_file, 'w') as f:
            json.dump(findings, f, indent=2, ensure_ascii=False)

    def show_loop_help(self, loop_identifier: str):
        """
        Show help for a specific loop including loop-specific parameters

        Args:
            loop_identifier: Loop name or path
        """
        try:
            # Find and load loop
            loop_dir = self.discovery.find_loop(loop_identifier)
            config = self.discovery.load_config(loop_dir)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Get loop info
        emoji = config.get('emoji', '➿')
        name = config['name']
        description = config.get('description', '')

        # Print header
        print(f"\n{emoji} RAVL Loop: {name}", file=sys.stderr)
        if description:
            print(f"{description}\n", file=sys.stderr)

        print(f"usage: ravl {name} [options]\n", file=sys.stderr)

        # Universal options
        print("Universal options:", file=sys.stderr)
        print("  --mode {{fast,full}}      Analysis mode (default: full)", file=sys.stderr)
        print("  --no-deep-learning      Skip verify and learn phases", file=sys.stderr)
        print("  --timeout SECONDS       Timeout in seconds (default: 300)", file=sys.stderr)

        # Get loop-specific parameters
        params = self.discovery.get_loop_parameters(loop_dir, config)

        # Separate required, optional, and auto-resolved
        auto_resolved_params = [p for p in params if p.get('auto_resolved')]
        required_params = [p for p in params if p.get('required') and not p.get('auto_resolved')]
        optional_params = [p for p in params if not p.get('required') and not p.get('auto_resolved')]

        if params:
            print("\nLoop-specific parameters:", file=sys.stderr)

            if required_params:
                print("\n  Required:", file=sys.stderr)
                for param in required_params:
                    cli_arg = param.get('cli_arg', f"--{param['name']}")
                    param_type = param.get('type', 'str')
                    help_text = param.get('help', '')
                    print(f"    {cli_arg} {param_type.upper()}", file=sys.stderr)
                    if help_text:
                        # Wrap help text
                        import textwrap
                        wrapped = textwrap.fill(help_text, width=70, initial_indent='      ', subsequent_indent='      ')
                        print(wrapped, file=sys.stderr)

            if optional_params:
                print("\n  Optional:", file=sys.stderr)
                for param in optional_params:
                    cli_arg = param.get('cli_arg', f"--{param['name']}")
                    param_type = param.get('type', 'str')
                    default = param.get('default')
                    help_text = param.get('help', '')

                    default_str = f" (default: {default})" if default else ""
                    print(f"    {cli_arg} {param_type.upper()}{default_str}", file=sys.stderr)
                    if help_text:
                        import textwrap
                        wrapped = textwrap.fill(help_text, width=70, initial_indent='      ', subsequent_indent='      ')
                        print(wrapped, file=sys.stderr)

            if auto_resolved_params:
                print("\n  Auto-resolved (no CLI arg needed):", file=sys.stderr)
                for param in auto_resolved_params:
                    print(f"    {param['name']}: {param.get('type', 'str')}", file=sys.stderr)

        # Examples
        print("\nExamples:", file=sys.stderr)
        if required_params:
            # Show example with required params
            example_args = []
            for param in required_params[:2]:  # Show max 2 required params in example
                cli_arg = param.get('cli_arg', f"--{param['name']}")
                param_type = param.get('type', 'str')
                if param_type == 'string' or param_type == 'str':
                    example_args.append(f'{cli_arg} "example"')
                else:
                    example_args.append(f'{cli_arg} value')

            print(f"  ravl {name} {' '.join(example_args)}", file=sys.stderr)
            print(f"  ravl {name} {' '.join(example_args)} --mode full", file=sys.stderr)
        else:
            print(f"  ravl {name} --mode fast", file=sys.stderr)
            print(f"  ravl {name} --mode full --timeout 600", file=sys.stderr)

        print("", file=sys.stderr)


def main():
    """Main entry point with command routing"""

    # Capture execution context for child loops to inherit
    # Child loops will use the same Python interpreter and ravl script as parent
    # This ensures they run in the same venv/context
    framework_root = Path(__file__).resolve().parent.parent.parent  # .ravl directory
    ravl_py_path = framework_root / 'ravl' / 'bin' / 'ravl.py'

    os.environ['RAVL_COMMAND'] = sys.executable  # Python interpreter (respects venv)
    os.environ['RAVL_SCRIPT'] = str(ravl_py_path)  # Path to ravl.py script
    os.environ['RAVL_CWD'] = os.getcwd()  # Working directory

    # Route subcommands before argument parsing
    # This allows --list, --clean, etc. to work identically in local and UV-installed versions
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd in ['--list', '-l']:
            from ravl.bin.ravl_list import main as list_main
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            return list_main()

        elif cmd in ['--clean', '-c']:
            from ravl.bin.ravl_clean import main as clean_main
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            return clean_main()

        elif cmd == '--clone':
            from ravl.bin.ravl_clone import main as clone_main
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            return clone_main()

        elif cmd == '--new':
            from ravl.bin.ravl_new_loop import main as new_main
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            return new_main()

        elif cmd == '--health':
            from ravl.bin.ravl_health import main as health_main
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            return health_main()

        elif cmd == '--execution-health':
            from ravl.bin.ravl_execution_health import main as exec_health_main
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            return exec_health_main()

        elif cmd == '--loop-health':
            from ravl.bin.ravl_loop_health import main as loop_health_main
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            return loop_health_main()

    # Stage 1: Parse loop name and check for --help
    initial_parser = argparse.ArgumentParser(add_help=False)
    initial_parser.add_argument('loop', nargs='?')
    initial_parser.add_argument('--loop-dir', type=str, default=None)
    initial_args, remaining_argv = initial_parser.parse_known_args()

    # Check if --help was requested
    if '--help' in remaining_argv or '-h' in remaining_argv:
        if initial_args.loop:
            # Show loop-specific help
            resolved_loops_dir = None
            if initial_args.loop_dir:
                resolved_loops_dir = Path(initial_args.loop_dir).expanduser().resolve()
            runner = RAVLUniversalRunner(loops_dir=resolved_loops_dir)
            runner.show_loop_help(initial_args.loop)
            sys.exit(0)
        # Fall through to show general help

    # Stage 2: Parse full arguments
    parser = argparse.ArgumentParser(
        description='RAVL - Universal RAVL Loop Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'loop',
        help='Loop name or path (e.g., "external_drift" or "ravl_loops/strategy_guardian")'
    )
    parser.add_argument(
        '--mode',
        choices=['full', 'fast', 'execute'],
        default='full',
        help='Execution mode: full=complete RAVL cycle (REFLECT-ACT-VERIFY-LEARN), fast=use cached code with verification (REFLECT-ACT-VERIFY), execute=run cached code only (ACT)'
    )
    parser.add_argument(
        '--no-deep-learning',
        action='store_true',
        help='Skip verify and learn phases'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_EXECUTION_TIMEOUT,
        help=f'Timeout in seconds (default: {DEFAULT_EXECUTION_TIMEOUT})'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress framework status messages and phase banners'
    )
    parser.add_argument(
        '--show-execution',
        action='store_true',
        help='Show execution learning details (code generation, DSL, caching). '
             'Default: only show domain learning progress.'
    )
    parser.add_argument(
        '--learning-path',
        type=str,
        default=None,
        help='Override learning directory path (highest priority: CLI > loop config > .env > default)'
    )
    parser.add_argument(
        '--venv-path',
        type=str,
        default=None,
        help='Override virtual environment path (highest priority: CLI > loop config > .env > default)'
    )
    parser.add_argument(
        '--loop-dir',
        type=str,
        default=None,
        help='Override loop directory path (highest priority: CLI > .env > default)'
    )
    parser.add_argument(
        '--show-config',
        action='store_true',
        help='Display resolved configuration without executing the loop'
    )

    # Use parse_known_args to allow loop-specific parameters through
    args, unknown = parser.parse_known_args()

    # Store unknown args for potential markdown loop delegation
    args.unknown_args = unknown

    # Resolve loop directory if provided
    project_root = Path(__file__).resolve().parent.parent.parent
    resolved_loops_dir = None
    if args.loop_dir:
        resolved_loops_dir = Path(args.loop_dir).expanduser().resolve()

    runner = RAVLUniversalRunner(loops_dir=resolved_loops_dir)
    runner.run(args)


if __name__ == '__main__':
    main()
