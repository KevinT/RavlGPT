#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Generic Markdown RAVL Loop Runner

Runs markdown-based RAVL loops using configuration from config.toml
instead of requiring custom run.py files for each loop.

Usage:
    # Auto-detect config from loop directory
    python3 run_markdown_ravl.py --loop-dir path/to/loop --role "CTO"

    # Specify config explicitly
    python3 run_markdown_ravl.py --config path/to/config.toml --role "CTO"
"""

import sys
import json
import time
import argparse
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Bootstrap: Add framework to path
# __file__ is .ravl/ravl/common/llm/run_markdown_ravl.py
# parent.parent.parent.parent gives .ravl/
_ravl_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_ravl_root))

from ravl.common.ravl_runner import RAVLRunner
from ravl.common.execution.markdown.markdown_ravl_executor import MarkdownRAVLExecutor
from ravl.common.execution.venv_manager import VenvManager
from ravl.common.utils.constants import DEFAULT_EXECUTION_TIMEOUT
from ravl.common.utils.file_utils import load_toml_file
from ravl.common.utils.logging_utils import log_message, log_execution
from ravl.common.cli.config_display import ConfigDisplay
from ravl.common.cli.ravl_cli_base import RAVLCLIBase


class ConfigBasedRAVLRunner:
    """Runs markdown RAVL loops based on config.toml"""

    def __init__(self, config_path: Path, loop_dir: Optional[Path] = None):
        """
        Initialize runner from config file

        Args:
            config_path: Path to config.toml file
            loop_dir: Optional explicit loop directory (for delegation with external config)
        """
        self.config_path = config_path

        # Use explicit loop_dir if provided (e.g., from delegation)
        # Otherwise determine from config path
        if loop_dir is not None:
            self.loop_dir = loop_dir
        elif config_path.parent.name == 'config':
            self.loop_dir = config_path.parent.parent
        else:
            self.loop_dir = config_path.parent

        # Load configuration
        self.config = load_toml_file(config_path) or {}

        # If we loaded ravl.toml directly, it has everything
        # If we loaded config.toml, merge metadata from ravl.toml
        if config_path.name == 'config.toml' and self.config and 'description' not in self.config:
            ravl_toml = self.loop_dir / 'config' / 'ravl.toml'
            ravl_config = load_toml_file(ravl_toml) or {}
            if ravl_config:
                # Merge metadata from ravl.toml (except name which comes from folder)
                self.config.setdefault('description', ravl_config.get('description'))
                self.config.setdefault('emoji', ravl_config.get('emoji'))

        # Always use folder name as loop name (ignore any name field in config)
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
        Extract template variables from config and CLI arguments

        Sources (lower priority first, later overrides):
        1. Top-level string config keys (for config_overrides from delegation)
        2. Explicit template_variables mapped from CLI args

        Args:
            args: Parsed command-line arguments

        Returns:
            Dict mapping template variable names to values
        """
        template_vars = {}

        # First, add all top-level string values from config
        # (These come from config_overrides in delegation)
        for key, value in self.config.items():
            if isinstance(value, str):
                template_vars[key] = value

        # Then, override with explicit template_variables from CLI args
        for var_name, var_config in self.config['template_variables'].items():
            cli_arg = var_config['cli_arg'].lstrip('-').replace('-', '_')
            value = getattr(args, cli_arg, None)

            if value is not None:
                template_vars[var_name] = str(value)

        return template_vars

    def _check_consecutive_failures(self, learnings_dir: Path) -> tuple[bool, int]:
        """
        Check if there have been 3+ consecutive failures

        Returns:
            (should_show_config: bool, failure_count: int)
        """
        recent_attempts_dir = learnings_dir / "execution_learning" / "recent_attempts"

        if not recent_attempts_dir.exists():
            return False, 0

        # Get last 3 attempts
        attempts = []
        for i in range(1, 4):
            attempt_dir = recent_attempts_dir / f"attempt_{i}"
            result_file = attempt_dir / "execution_result.json"
            if result_file.exists():
                try:
                    import json
                    with open(result_file) as f:
                        result = json.load(f)
                        passed = result.get("execution", {}).get("passed", True)
                        attempts.append(not passed)  # True if failed
                except:
                    pass

        # Count consecutive failures from end
        consecutive = 0
        for failed in reversed(attempts):
            if failed:
                consecutive += 1
            else:
                break

        return consecutive >= 3, consecutive

    def _count_unanswered_unknowns(self, md_file: Path) -> int:
        """
        Count unanswered questions in an unknowns markdown file.

        Args:
            md_file: Path to known_unknowns.md file

        Returns:
            Count of questions with placeholder answers
        """
        if not md_file.exists():
            return 0

        try:
            content = md_file.read_text(encoding='utf-8')
        except Exception:
            return 0

        # Count questions with placeholder answers
        unanswered = 0
        lines = content.split('\n')
        in_question = False

        for line in lines:
            if line.startswith('## Question'):
                in_question = True
            elif line.startswith('**Answer**:') and in_question:
                answer = line.replace('**Answer**:', '').strip()
                # Check if placeholder
                if answer.startswith('_[Fill in'):
                    unanswered += 1
                in_question = False

        return unanswered

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

        # Check for persistent diagnostic state
        diagnostic_state_file = learnings_dir / "execution_learning" / "auto_diagnostic_mode.json"
        if diagnostic_state_file.exists():
            try:
                import json
                with open(diagnostic_state_file) as f:
                    state = json.load(f)
                    if state.get("enabled", False):
                        log_message("ℹ️  Auto-diagnostic mode active (persisted from previous failures)", status='info')
                        from ravl.common.utils.logging_utils import set_show_execution
                        set_show_execution(True)
            except Exception:
                pass  # Ignore errors reading state

        # Check for consecutive failures and auto-enable debug mode
        should_show_config, failure_count = self._check_consecutive_failures(learnings_dir)
        if should_show_config:
            log_message(f"⚠️  Detected {failure_count} consecutive failures - enabling auto-diagnostic mode", status='info')

            # Persist diagnostic state
            diagnostic_state_file.parent.mkdir(parents=True, exist_ok=True)
            import json
            from datetime import datetime
            with open(diagnostic_state_file, 'w') as f:
                json.dump({
                    "enabled": True,
                    "triggered_at": datetime.now().isoformat(),
                    "failure_count": failure_count
                }, f, indent=2)

            # Enable execution logging for this run
            from ravl.common.utils.logging_utils import set_show_execution
            set_show_execution(True)

            # Display configuration
            from cli.config_display import ConfigDisplay
            from cli.ravl_cli_base import RAVLCLIBase

            project_root = RAVLCLIBase.find_project_root(required=False)
            learning_path = RAVLRunner.resolve_learning_path(
                loop_dir=self.loop_dir,
                loop_config=self.config,
                cli_learning_path=Path(args.learning_path) if hasattr(args, 'learning_path') and args.learning_path else None,
                project_root=project_root
            )
            venv_path = RAVLRunner.resolve_venv_path(
                loop_dir=self.loop_dir,
                loop_config=self.config,
                cli_venv_path=None,
                project_root=project_root
            )

            ConfigDisplay.show(
                loop_dir=self.loop_dir,
                learning_path=learning_path,
                venv_path=venv_path,
                loop_config=self.config,
                args=args,
                project_root=project_root,
                learning_path_source="Auto-debug",
                venv_path_source="Auto-debug",
                loop_dir_source="Auto-debug"
            )
            log_message("Continuing with loop execution...", status='info')

        logs_dir = learnings_dir / 'logs'

        # Setup logging
        loop_name = self.config['name']
        tee_logger = RAVLRunner.setup_logging(logs_dir, loop_name)

        # Extract template variables
        context_vars = self.extract_template_vars(args)

        # Display startup info
        log_message(f"➿ {self.config.get('description', loop_name)} starting...", status='info', indent=0)
        for var_name, var_value in context_vars.items():
            log_message(f"   {var_name}: {var_value}", status='info', indent=0)
        log_message(f"   Mode: {args.mode}", status='info', indent=0)

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

            # Extract force_code_regeneration flag from args
            force_code_regeneration = getattr(args, 'force_code_regeneration', False)

            # ===== Venv Setup =====
            # Ensure venv exists before creating executor (needed for code generation/execution)
            from cli.ravl_cli_base import RAVLCLIBase as _RAVLCLIBase

            project_root = _RAVLCLIBase.find_project_root(required=False)
            venv_path = RAVLRunner.resolve_venv_path(
                loop_dir=self.loop_dir,
                loop_config=self.config,
                cli_venv_path=Path(args.venv_path) if hasattr(args, 'venv_path') and args.venv_path else None,
                project_root=project_root
            )

            # Initialize venv manager and ensure venv exists
            venv_manager = VenvManager(venv_path)
            success, error = venv_manager.detect_or_create()
            if not success:
                raise RuntimeError(f"Failed to initialize virtual environment: {error}")

            log_message(f"Using venv: {venv_path}", status='info', indent=3)

            # Initialize executor (with initialization failure handling)
            executor = None
            initialization_error = None
            try:
                executor = MarkdownRAVLExecutor(
                    markdown_text=markdown_text,
                    loop_dir=self.loop_dir,
                    learnings_dir=learnings_dir,
                    context_vars=context_vars,
                    force_code_regeneration=force_code_regeneration
                )
            except Exception as init_error:
                # Executor initialization failed (e.g., missing API key, invalid config)
                # We still want to run LEARN phase to record this failure in the model
                initialization_error = init_error
                log_message(f"Executor initialization failed: {init_error}", status='error', indent=3)
                log_message(f"Will attempt to record failure in LEARN phase", status='info', indent=3)

                # Create minimal executor stub that can at least run learn()
                class MinimalExecutor:
                    def __init__(self, learnings_dir, loop_dir, context_vars):
                        self.learnings_dir = learnings_dir
                        self.loop_dir = loop_dir
                        self.context_vars = context_vars
                        self.used_interpretation = False

                    def learn(self, verification, action_result):
                        """Write minimal learning artifact for initialization failure"""
                        from pathlib import Path
                        import json
                        from datetime import datetime, timezone

                        # Write to execution_learning (same structure as normal learning)
                        execution_learning_dir = self.learnings_dir / 'execution_learning'
                        execution_learning_dir.mkdir(parents=True, exist_ok=True)

                        # Current state
                        failure_state = {
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'phase': 'initialization',
                            'success': False,
                            'error': str(initialization_error),
                            'error_type': type(initialization_error).__name__,
                            'verification': verification,
                            'action_result': action_result
                        }

                        current_state_file = execution_learning_dir / 'current_state' / 'initialization_failure.json'
                        current_state_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(current_state_file, 'w', encoding='utf-8') as f:
                            json.dump(failure_state, f, indent=2)

                        # Append to history
                        history_file = execution_learning_dir / 'history' / 'initialization_failures.jsonl'
                        history_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(history_file, 'a', encoding='utf-8') as f:
                            f.write(json.dumps(failure_state) + '\n')

                executor = MinimalExecutor(learnings_dir, self.loop_dir, context_vars)

            # If initialization failed, create stub responses and jump to LEARN
            if initialization_error:
                # Create stub responses that indicate initialization failure
                reflection = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'error': f"Executor initialization failed: {initialization_error}",
                    'error_type': type(initialization_error).__name__,
                    'phase': 'initialization',
                    'success': False
                }
                action_result = {
                    'timestamp': reflection.get('timestamp', datetime.now(timezone.utc).isoformat()),
                    'context_vars': context_vars,
                    'error': str(initialization_error),
                    'error_type': type(initialization_error).__name__,
                    'phase': 'initialization',
                    'success': False,
                    'output_file': None
                }
                verification = {
                    'timestamp': reflection.get('timestamp', datetime.now(timezone.utc).isoformat()),
                    'error': str(initialization_error),
                    'error_type': type(initialization_error).__name__,
                    'phase': 'initialization',
                    'success': False,
                    'verification_passed': False,
                    'overall_passed': False
                }

                # Skip to LEARN phase
                RAVLRunner.print_banner("Step 4 of 4: [L]EARN", "")
                executor.learn(verification, action_result)

                # Show error and exit
                RAVLRunner.print_banner(f"{loop_name} failed during initialization", "❌")
                log_message(f"   Error: {initialization_error}", status='error', indent=0)
                log_message(f"   Learning artifacts written to: {learnings_dir}/execution_learning/", status='info', indent=0)
                tee_logger.close()
                sys.exit(1)

            # Determine which phases to run based on mode
            mode = args.mode
            run_reflect = mode in ['full', 'fast']  # Execute mode skips REFLECT
            run_verify = mode in ['full', 'fast']    # Execute mode skips VERIFY
            run_learn = mode == 'full'               # Only full mode runs LEARN

            # ===== Step 1: REFLECT =====
            if run_reflect:
                RAVLRunner.print_banner("Step 1 of 4: [R]EFLECT", "")
                try:
                    reflection = executor.reflect()
                    # Calculate duration
                    duration = time.time() - start_time
                    log_message(f"Completed at {duration:.1f}s", status='success', indent=3)
                except Exception as reflect_error:
                    # REFLECT failed, but record the failure so loop can learn from it
                    log_message(f"REFLECT phase failed: {reflect_error}", status='error', indent=3)
                    reflection = {
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'error': str(reflect_error),
                        'error_type': type(reflect_error).__name__,
                        'phase': 'reflect',
                        'success': False
                    }
                    # Continue to ACT phase with error information
            else:
                # Execute mode: skip REFLECT, use minimal reflection context
                log_execution("Execute mode: skipping REFLECT phase", status='info')
                reflection = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'context_vars': context_vars,
                    'learnings': {},
                    'skip_cache': False
                }

            # ===== Step 2: ACT =====
            RAVLRunner.print_banner("Step 2 of 4: [A]CT", "")
            try:
                action_result = executor.act(reflection, mode=mode)
                # Calculate duration
                duration = time.time() - start_time
                log_message(f"Completed at {duration:.1f}s", status='success', indent=3)
            except Exception as act_error:
                # ACT failed, but record the failure so loop can learn from it
                log_message(f"ACT phase failed: {act_error}", status='error', indent=3)
                action_result = {
                    'timestamp': reflection.get('timestamp', datetime.now(timezone.utc).isoformat()),
                    'context_vars': context_vars,
                    'error': str(act_error),
                    'error_type': type(act_error).__name__,
                    'phase': 'act',
                    'code_executed': False,
                    'success': False
                }
                # Continue to VERIFY and LEARN phases to record the failure (if running)

            # ===== Step 3: VERIFY =====
            if run_verify and not args.no_deep_learning:

                RAVLRunner.print_banner("Phase 3 of 4: [V]ERIFY", "")

                # Verify the current action result against verification criteria
                try:
                    verification = executor.verify(action_result, reflection)
                    # Calculate duration
                    duration = time.time() - start_time
                    log_message(f"Completed at {duration:.1f}s", status='success', indent=3)
                except Exception as verify_error:
                    # VERIFY failed, but record the failure so loop can learn from it
                    log_message(f"VERIFY phase failed: {verify_error}", status='error', indent=3)
                    verification = {
                        'timestamp': action_result.get('timestamp', datetime.now(timezone.utc).isoformat()),
                        'error': str(verify_error),
                        'error_type': type(verify_error).__name__,
                        'phase': 'verify',
                        'success': False,
                        'verification_passed': False
                    }
                    # Continue to LEARN phase to record the failure (if running)

                # ===== Step 4: LEARN =====
                if run_learn:
                    RAVLRunner.print_banner("Step 4 of 4: [L]EARN", "")
                    try:
                        executor.learn(verification, action_result)

                        # Calculate duration
                        duration = time.time() - start_time
                        log_message(f"Completed at {duration:.1f}s", status='success', indent=3)
                    except Exception as learn_error:
                        duration = time.time() - start_time
                        log_message(f"Error during LEARN phase: {learn_error}", status='error', indent=3)
                        log_message(f"Completed at {duration:.1f}s (with LEARN error)", status='warning', indent=3)

                        # Save error artifacts for debugging
                        error_file = learnings_dir / 'current_state' / 'learn_phase_error.json'
                        error_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(error_file, 'w', encoding='utf-8') as f:
                            json.dump({
                                'error': str(learn_error),
                                'error_type': type(learn_error).__name__,
                                'timestamp': datetime.now().isoformat(),
                            'phase': 'learn',
                            'verification': verification,
                            'action_result': action_result
                        }, f, indent=2)
                        log_message(f"Error details saved to: {error_file.relative_to(Path.cwd())}", status='info', indent=3)
            else:
                # Execute mode: skip VERIFY and LEARN
                log_execution("Execute mode: skipping VERIFY and LEARN phases", status='info')
                verification = None

            # Show interpretation summary if LLM interpreted the loop
            if executor.used_interpretation:
                RAVLRunner.print_banner("INTERPRETATION APPLIED", "📚")
                log_message(f"   Your free-form markdown was structured into RAVL phases", status='info', indent=0)
                log_message(f"", status='info', indent=0)
                log_message(f"   Review:  cat {learnings_dir.name}/current_state/ravl_loop_enhanced.md", status='info', indent=0)
                log_message(f"   Learn:   .ravl/docs/free_form_interpretation.md", status='info', indent=0)
                log_message(f"", status='info', indent=0)
                log_message(f"   To refine for future runs:", status='info', indent=0)
                log_message(f"     1. Review the enhanced version", status='info', indent=0)
                log_message(f"     2. Update ravl_loop.md with any tweaks", status='info', indent=0)
                log_message(f"     3. Next run will use your updated structure", status='info', indent=0)

            # Check if verification failed and suggest diagnostician
            verification_passed = (
                not args.no_deep_learning
                and verification
                and verification.get("overall_passed", False)
            )

            if not args.no_deep_learning and verification and not verification.get("overall_passed", False):
                RAVLRunner.print_banner("VERIFICATION FAILED", "⚠️")
                log_message(f"   The loop ran but didn't meet all verification criteria.", status='error', indent=0)

                # Display detailed verification criteria results
                domain_verification = verification.get('domain', {})
                criteria_results = domain_verification.get('criteria_results', [])

                if criteria_results:
                    log_message(f"", status='info', indent=0)
                    log_message(f"   📋 Verification Details:", status='info', indent=0)
                    for i, criterion in enumerate(criteria_results, 1):
                        status = "✓" if criterion.get('passed', False) else "✗"
                        criterion_name = criterion.get('criterion', 'Unknown criterion')
                        log_message(f"      {status} [{i}] {criterion_name}", status='info', indent=0)

                        # Show explanation for failed criteria
                        if not criterion.get('passed', False) and criterion.get('explanation'):
                            explanation = criterion['explanation']
                            # Truncate long explanations for readability
                            if len(explanation) > 100:
                                explanation = explanation[:100] + "..."
                            log_message(f"          {explanation}", status='error', indent=0)

                log_message(f"", status='info', indent=0)
                log_message(f"   Understand config and get diagnostic suggestions:", status='info', indent=0)
                log_message(f"     ravl {loop_name} --show-config # shows settings", status='info', indent=0)
                log_message(f"     ravl {loop_name} --verbose # shows execution steps in bright", status='info', indent=0)
                log_message(f"     ravl --loop-health {loop_name} # inspect loop agentic health", status='info', indent=0)
                log_message(f"     ravl --execution-health {loop_name} # inspect loop execution health", status='info', indent=0)
                log_message(f"", status='info', indent=0)

            # Clear auto-diagnostic state on success
            if verification_passed and diagnostic_state_file.exists():
                diagnostic_state_file.unlink()
                log_message("✓ Loop succeeded - cleared auto-diagnostic mode", status='success')

            # Success/completion summary
            completion_status = "completed successfully" if verification_passed else "completed with errors"
            RAVLRunner.print_banner(f"{loop_name} {completion_status}", "🏁")
            final_duration = time.time() - start_time
            log_message(f"   Total Duration: {final_duration:.1f}s", status='info', indent=0)
            # Filter out 'name' since it's already shown in banner
            for var_name, var_value in context_vars.items():
                if var_name != 'name':
                    log_message(f"   {var_name}: {var_value}", status='info', indent=0)

            # Count unanswered questions to guide user improvements
            domain_unknowns_file = learnings_dir / 'loop_learning' / 'current_state' / 'known_loop_unknowns.md'
            execution_unknowns_file = learnings_dir / 'execution_learning' / 'current_state' / 'known_execution_unknowns.md'

            domain_count = self._count_unanswered_unknowns(domain_unknowns_file)
            execution_count = self._count_unanswered_unknowns(execution_unknowns_file)

            # Only show tip if there are unanswered questions
            if domain_count > 0 or execution_count > 0:
                log_message("💡 Tip: Answer questions to improve future runs:", status='info', indent=0)
                if domain_count > 0:
                    log_message(f"   • {domain_count} domain question(s): learnings/loop_learning/current_state/known_loop_unknowns.md",
                               status='info', indent=0)
                if execution_count > 0:
                    log_message(f"   • {execution_count} execution question(s): learnings/execution_learning/current_state/known_execution_unknowns.md",
                               status='info', indent=0)
            log_message("=" * 80, status='info', indent=0)

            # Close logger
            tee_logger.close()
            sys.exit(0)

        except (KeyboardInterrupt, Exception) as e:
            RAVLRunner.handle_error(e, tee_logger)


def create_minimal_config(loop_dir: Path) -> bool:
    """
    Offer to create a minimal config file for a loop

    Args:
        loop_dir: Path to the loop directory

    Returns:
        True if config was created, False if user declined
    """
    # Determine loop name from folder
    loop_name = loop_dir.name

    log_message(f"\n⚠️  No config file found for loop '{loop_name}'", status='error', indent=0)
    log_message("", status='info', indent=0)

    # Interactive prompt
    try:
        response = input("Would you like to create a minimal config? (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        log_message("\n❌ Config creation cancelled", status='error', indent=0)
        return False

    if response != 'y':
        log_message("\nℹ️  To create a config manually, create config/ravl.toml with:", status='info', indent=0)
        log_message("    description: Your loop description", status='info', indent=0)
        log_message("    loop_type: markdown  # or python", status='info', indent=0)
        return False

    # Prompt for description
    log_message("", status='info', indent=0)
    try:
        description = input("Enter a description (or press Enter for default): ").strip()
    except (EOFError, KeyboardInterrupt):
        log_message("\n❌ Config creation cancelled", status='error', indent=0)
        return False

    if not description:
        description = "RAVL loop"

    # Detect loop type
    loop_type = "markdown" if (loop_dir / "ravl_loop.md").exists() else "python"

    # Create config directory
    config_dir = loop_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Generate config content (TOML format)
    config_content = f"""# RAVL loop configuration
# Note: Loop name is always derived from the folder name: {loop_name}
description = "{description}"
loop_type = "{loop_type}"

# Optional: Override execution timeout (default: 300 seconds)
# execution_timeout = 120

# Optional: Specify Python packages for generated code (markdown loops)
# [allowed_dependencies.requests]
# min_version = "2.31.0"
# max_version = "3.0.0"

# Optional: Custom learning directory (default: ./learnings)
# learning_path = "/path/to/custom/learnings"

# Optional: Custom virtual environment (default: .ravl/venv)
# venv_path = "/path/to/custom/venv"

# Optional: Template variables for parameterized loops
# [template_variables.variable_name]
# cli_arg = "--variable"
# required = true
# type = "string"
# help = "Description of variable"

# Optional: Metadata for categorization
# [metadata]
# author = "Your Name"
# tags = ["tag1", "tag2"]
"""

    # Write config file
    config_path = config_dir / "ravl.toml"
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
    except Exception as e:
        log_message(f"\n❌ Failed to create config: {e}", status='error', indent=0)
        return False

    log_message(f"\n✅ Created {config_path.relative_to(loop_dir.parent)} with minimal settings", status='success', indent=0)
    log_message(f"   Loop name '{loop_name}' is derived from folder name", status='info', indent=0)
    log_message("   You can customize other settings by editing the config.", status='info', indent=0)
    log_message("\nContinuing with loop execution...\n", status='info', indent=0)

    return True


def main():
    """Main entry point"""
    # Initial parser for --config and --loop-dir
    initial_parser = argparse.ArgumentParser(add_help=False)
    initial_parser.add_argument(
        '--config',
        type=Path,
        help='Path to config.toml file'
    )
    initial_parser.add_argument(
        '--loop-dir',
        type=Path,
        help='Path to loop directory (will look for config.toml inside)'
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
    initial_parser.add_argument(
        '--show-execution',
        action='store_true',
        help='Show execution learning details (code generation, DSL, caching). '
             'Default: only show domain learning progress.'
    )

    # Parse just these arguments first
    initial_args, remaining_argv = initial_parser.parse_known_args()

    # Determine config path
    config_path = None

    if initial_args.config:
        config_path = initial_args.config
    elif initial_args.loop_dir:
        # Try config locations in order:
        # 1. config/ravl.toml (standard location)
        # 2. config/config.toml (old markdown loops with separate config)
        config_path = initial_args.loop_dir / 'config' / 'ravl.toml'
        if not config_path.exists():
            config_path = initial_args.loop_dir / 'config' / 'config.toml'
    else:
        log_message("Error: Must specify either --config or --loop-dir", status='error', indent=0)
        log_message("", status='info', indent=0)
        log_message("Usage:", status='info', indent=0)
        log_message("  python3 run_markdown_ravl.py --loop-dir path/to/loop [options]", status='info', indent=0)
        log_message("  python3 run_markdown_ravl.py --config path/to/config.toml [options]", status='info', indent=0)
        sys.exit(1)

    if not config_path.exists():
        # Try to create config if we have a loop directory
        if initial_args.loop_dir:
            if create_minimal_config(initial_args.loop_dir):
                # Config was created, check if it exists now
                if not config_path.exists():
                    # Try the standard location we just created
                    config_path = initial_args.loop_dir / 'config' / 'ravl.toml'
                    if not config_path.exists():
                        log_message(f"Error: Config creation succeeded but file not found: {config_path}", status='error', indent=0)
                        sys.exit(1)
            else:
                # User declined to create config
                log_message(f"\nError: Config file required but not found: {config_path}", status='error', indent=0)
                sys.exit(1)
        else:
            # No loop directory, can't offer to create config
            log_message(f"Error: Config file not found: {config_path}", status='error', indent=0)
            sys.exit(1)

    # Create runner and parse full arguments
    try:
        # Pass explicit loop_dir if provided (for delegation with external config)
        runner = ConfigBasedRAVLRunner(config_path, loop_dir=initial_args.loop_dir)
        parser = runner.create_argument_parser()

        # Re-parse with full argument list
        sys.argv = [sys.argv[0]] + remaining_argv
        args = parser.parse_args()

        # Pass learning path to runner if provided (from CLI or config)
        if initial_args.learning_path:
            args.learning_path = initial_args.learning_path
        elif 'learning_path' in runner.config:
            args.learning_path = runner.config['learning_path']

        # Handle --show-config: Display configuration and exit
        if initial_args.show_config:
            # Find project root
            from cli.ravl_cli_base import RAVLCLIBase
            project_root = RAVLCLIBase.find_project_root(required=False)

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
        log_message(f"Error: {e}", status='error', indent=0)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
