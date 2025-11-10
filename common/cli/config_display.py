#!/usr/bin/env python3
"""
Configuration Display Module

Displays comprehensive configuration information without executing the loop.
Shows resolved paths, sources, loop metadata, and runtime parameters.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

from utils.logging_utils import log_message


class ConfigDisplay:
    """Display comprehensive configuration information for RAVL loops"""

    # RAVL-related environment variables to check
    RAVL_ENV_VARS = [
        'ANTHROPIC_API_KEY',
        'GOOGLE_CREDENTIALS',
        'RAVL_DEFAULT_LEARNING_DIRECTORY',
        'RAVL_DEFAULT_VENV_DIRECTORY',
        'RAVL_DEFAULT_LOOP_DIRECTORY',
        'RAVL_QUIET',
    ]

    @staticmethod
    def show(
        loop_dir: Path,
        learning_path: Path,
        venv_path: Path,
        loop_config: Dict[str, Any],
        args: Any,
        project_root: Path,
        learning_path_source: str,
        venv_path_source: str,
        loop_dir_source: str
    ):
        """
        Display comprehensive configuration information

        Args:
            loop_dir: Resolved loop directory
            learning_path: Resolved learning path
            venv_path: Resolved venv path
            loop_config: Loaded loop configuration
            args: Parsed CLI arguments
            project_root: Project root directory
            learning_path_source: Source of learning path (CLI/Config/Env/Default)
            venv_path_source: Source of venv path (CLI/Config/Env/Default)
            loop_dir_source: Source of loop directory (CLI/Env/Default)
        """
        emoji = loop_config.get('emoji', '➿')
        name = loop_config.get('description', loop_dir.name)

        log_message(f"\n{'='*80}", status='info', indent=0)
        log_message(f"{emoji} Configuration Report: {name}", status='info', indent=0)
        log_message(f"{'='*80}\n", status='info', indent=0)

        # Section 1: Configuration Resolution
        ConfigDisplay._show_configuration_resolution(
            loop_dir, learning_path, venv_path,
            loop_dir_source, learning_path_source, venv_path_source
        )

        # Section 2: Loop Configuration
        ConfigDisplay._show_loop_configuration(loop_dir, loop_config)

        # Section 3: Execution Parameters
        ConfigDisplay._show_execution_parameters(args)

        # Section 4: Environment Variables
        ConfigDisplay._show_environment_variables()

        # Section 5: Loaded Config Files
        ConfigDisplay._show_loaded_config_files(project_root, loop_dir)

        # Section 6: Dependencies Whitelist
        ConfigDisplay._show_dependencies_whitelist(project_root, loop_dir, loop_config)

        # Section 7: Suggested Run Command
        ConfigDisplay._show_suggested_command(args, loop_config)

        log_message(f"\n{'='*80}\n", status='info', indent=0)

    @staticmethod
    def _show_configuration_resolution(
        loop_dir: Path,
        learning_path: Path,
        venv_path: Path,
        loop_dir_source: str,
        learning_path_source: str,
        venv_path_source: str
    ):
        """Display configuration resolution section"""
        log_message("📍 Configuration Resolution", status='info', indent=0)
        log_message(f"{'─'*80}", status='info', indent=0)

        # Loop Directory
        log_message(f"\n  Loop Directory:", status='info', indent=0)
        log_message(f"    Source:  {loop_dir_source}", status='info', indent=0)
        log_message(f"    Path:    {loop_dir}", status='info', indent=0)
        log_message(f"    Status:  {'✅ Exists' if loop_dir.exists() else '❌ Not found'}", status='info', indent=0)

        # Learning Path
        log_message(f"\n  Learning Path:", status='info', indent=0)
        log_message(f"    Source:  {learning_path_source}", status='info', indent=0)
        log_message(f"    Path:    {learning_path}", status='info', indent=0)
        log_message(f"    Status:  {'✅ Exists' if learning_path.exists() else '⚠️  Will be created'}", status='info', indent=0)

        # Venv Path
        log_message(f"\n  Virtual Environment:", status='info', indent=0)
        log_message(f"    Source:  {venv_path_source}", status='info', indent=0)
        log_message(f"    Path:    {venv_path}", status='info', indent=0)
        log_message(f"    Status:  {'✅ Exists' if venv_path.exists() else '⚠️  Will be created'}", status='info', indent=0)
        log_message("", status='info', indent=0)

    @staticmethod
    def _show_loop_configuration(loop_dir: Path, loop_config: Dict[str, Any]):
        """Display loop configuration section"""
        log_message("🔧 Loop Configuration", status='info', indent=0)
        log_message(f"{'─'*80}", status='info', indent=0)

        # Detect loop type
        is_markdown = (loop_dir / 'ravl_loop.md').exists()
        is_python = (loop_dir / 'ravl_loop.py').exists()
        loop_type = 'Markdown' if is_markdown else ('Python' if is_python else 'Unknown')

        log_message(f"\n  Name:         {loop_config.get('name', loop_dir.name)}", status='info', indent=0)
        log_message(f"  Description:  {loop_config.get('description', 'N/A')}", status='info', indent=0)
        log_message(f"  Emoji:        {loop_config.get('emoji', '➿')}", status='info', indent=0)
        log_message(f"  Type:         {loop_type}", status='info', indent=0)

        if not is_markdown:
            log_message(f"  Class:        {loop_config.get('class_name', 'N/A')}", status='info', indent=0)
            log_message(f"  Module:       {loop_config.get('module', 'ravl_loop')}", status='info', indent=0)

        log_message("", status='info', indent=0)

        # Template variables for markdown loops
        if is_markdown and 'template_variables' in loop_config:
            ConfigDisplay._show_template_variables(loop_config['template_variables'])

    @staticmethod
    def _show_template_variables(template_vars: Dict[str, Any]):
        """Display template variables for markdown loops"""
        log_message("  Template Variables:", status='info', indent=0)

        if not template_vars:
            log_message("    (none)", status='info', indent=0)
            return

        for var_name, var_config in template_vars.items():
            required = var_config.get('required', False)
            default = var_config.get('default', None)
            description = var_config.get('description', '')

            req_marker = '(required)' if required else '(optional)'
            default_str = f", default: {default}" if default else ""

            log_message(f"    • {var_name} {req_marker}{default_str}", status='info', indent=0)
            if description:
                log_message(f"      {description}", status='info', indent=0)
        log_message("", status='info', indent=0)

    @staticmethod
    def _show_execution_parameters(args: Any):
        """Display execution parameters section"""
        log_message("⚙️  Execution Parameters", status='info', indent=0)
        log_message(f"{'─'*80}", status='info', indent=0)
        log_message(f"\n  Mode:          {args.mode}", status='info', indent=0)
        log_message(f"  Deep Learning: {'❌ Disabled (--no-deep-learning)' if args.no_deep_learning else '✅ Enabled'}", status='info', indent=0)
        log_message(f"  Timeout:       {args.timeout} seconds", status='info', indent=0)
        log_message(f"  Quiet Mode:    {'✅ Enabled' if args.quiet else '❌ Disabled'}", status='info', indent=0)
        log_message("", status='info', indent=0)

    @staticmethod
    def _show_environment_variables():
        """Display RAVL-related environment variables"""
        log_message("🌍 Environment Variables", status='info', indent=0)
        log_message(f"{'─'*80}", status='info', indent=0)
        log_message("", status='info', indent=0)

        found_any = False
        for var_name in ConfigDisplay.RAVL_ENV_VARS:
            value = os.environ.get(var_name)
            if value:
                found_any = True
                # Truncate sensitive values
                if var_name in ['ANTHROPIC_API_KEY', 'GOOGLE_CREDENTIALS']:
                    display_value = f"{value[:20]}... (truncated)"
                else:
                    display_value = value
                log_message(f"  ✅ {var_name}", status='info', indent=0)
                log_message(f"     {display_value}", status='info', indent=0)

        if not found_any:
            log_message("  (no RAVL environment variables set)", status='info', indent=0)

        log_message("", status='info', indent=0)

    @staticmethod
    def _show_loaded_config_files(project_root: Path, loop_dir: Path):
        """Display which config files were loaded"""
        log_message("📄 Loaded Configuration Files", status='info', indent=0)
        log_message(f"{'─'*80}", status='info', indent=0)
        log_message("", status='info', indent=0)

        config_files = [
            (project_root / '.ravl' / 'config' / 'ravl.yml', 'Framework defaults'),
            (project_root / 'ravl_loops' / 'config' / 'ravl.yml', 'Project config'),
            (loop_dir / 'config' / 'ravl.yml', 'Loop config'),
        ]

        # Check for parent config
        parent_dir = loop_dir.parent
        if parent_dir.name != 'ravl_loops':
            parent_config_file = parent_dir / 'config' / 'ravl.yml'
            config_files.insert(2, (parent_config_file, 'Parent loop config'))

        for config_path, description in config_files:
            if config_path.exists():
                log_message(f"  ✅ {description}", status='info', indent=0)
                log_message(f"     {config_path}", status='info', indent=0)
            else:
                log_message(f"  ⚪ {description} (not found)", status='info', indent=0)

        log_message("", status='info', indent=0)

    @staticmethod
    def _show_dependencies_whitelist(project_root: Path, loop_dir: Path, loop_config: Dict[str, Any]):
        """Display allowed dependencies"""
        log_message("📦 Dependency Whitelist", status='info', indent=0)
        log_message(f"{'─'*80}", status='info', indent=0)
        log_message("", status='info', indent=0)

        # Check if whitelist is in loop config
        allowed_deps = loop_config.get('allowed_dependencies', {})

        if allowed_deps:
            log_message(f"  Found {len(allowed_deps)} approved packages in loop config:", status='info', indent=0)
            for pkg_name, constraints in list(allowed_deps.items())[:5]:  # Show first 5
                if isinstance(constraints, dict):
                    min_ver = constraints.get('min_version', '')
                    max_ver = constraints.get('max_version', '')
                    version_str = f" ({min_ver} - {max_ver})" if min_ver or max_ver else ""
                    log_message(f"    • {pkg_name}{version_str}", status='info', indent=0)
                else:
                    log_message(f"    • {pkg_name}", status='info', indent=0)

            if len(allowed_deps) > 5:
                log_message(f"    ... and {len(allowed_deps) - 5} more", status='info', indent=0)
        else:
            log_message("  No loop-specific whitelist. Inheriting from project/framework defaults.", status='info', indent=0)

        log_message("", status='info', indent=0)

    @staticmethod
    def _show_suggested_command(args: Any, loop_config: Dict[str, Any]):
        """Display suggested run command"""
        log_message("🚀 Ready to Run", status='info', indent=0)
        log_message(f"{'─'*80}", status='info', indent=0)
        log_message("", status='info', indent=0)

        # Build command
        cmd_parts = ['./ravl', args.loop]

        if args.mode != 'full':
            cmd_parts.append(f'--mode {args.mode}')

        if args.no_deep_learning:
            cmd_parts.append('--no-deep-learning')

        if args.timeout != 300:  # Non-default timeout
            cmd_parts.append(f'--timeout {args.timeout}')

        if args.quiet:
            cmd_parts.append('--quiet')

        if args.learning_path:
            cmd_parts.append(f'--learning-path {args.learning_path}')

        if hasattr(args, 'loop_dir') and args.loop_dir:
            cmd_parts.append(f'--loop-dir {args.loop_dir}')

        log_message(f"  Command: {' '.join(cmd_parts)}", status='info', indent=0)
        log_message("", status='info', indent=0)
