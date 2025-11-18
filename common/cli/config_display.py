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


def _log(message: str, indent: int = 0):
    """Log a message without status symbols for clean config display"""
    log_message(message, status='info', indent=indent, show_symbol=False)


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
        name = loop_config.get('description', loop_dir.name)

        _log(f"\n{'='*80}", indent=0)
        _log(f"Configuration Report: {name}", indent=0)
        _log(f"{'='*80}\n", indent=0)

        # Section 1: Loop Metadata & Execution Parameters
        ConfigDisplay._show_loop_metadata_and_parameters(loop_dir, loop_config, args)

        # Section 2: Configuration Resolution
        ConfigDisplay._show_configuration_resolution(
            loop_dir, learning_path, venv_path,
            loop_dir_source, learning_path_source, venv_path_source
        )

        # Section 3: Environment Variables
        ConfigDisplay._show_environment_variables()

        # Section 4: Loaded Config Files
        ConfigDisplay._show_loaded_config_files(project_root, loop_dir)

        # Section 5: Dependencies Whitelist
        ConfigDisplay._show_dependencies_whitelist(project_root, loop_dir, loop_config)

        # Section 6: Ready to Run
        ConfigDisplay._show_suggested_command(args, loop_config)

        _log(f"\n{'='*80}\n", indent=0)

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
        _log("Configuration Resolution", indent=0)
        _log(f"{'─'*80}", indent=0)

        # Loop Directory
        _log(f"\n  Loop Directory:", indent=0)
        _log(f"    Source:  {loop_dir_source}", indent=0)
        _log(f"    Path:    {loop_dir}", indent=0)
        _log(f"    Status:  {'[exists]' if loop_dir.exists() else '[not found]'}", indent=0)

        # Learning Path
        _log(f"\n  Learning Path:", indent=0)
        _log(f"    Source:  {learning_path_source}", indent=0)
        _log(f"    Path:    {learning_path}", indent=0)
        _log(f"    Status:  {'[exists]' if learning_path.exists() else '[will be created]'}", indent=0)

        # Venv Path
        _log(f"\n  Virtual Environment:", indent=0)
        _log(f"    Source:  {venv_path_source}", indent=0)
        _log(f"    Path:    {venv_path}", indent=0)
        _log(f"    Status:  {'[exists]' if venv_path.exists() else '[will be created]'}", indent=0)
        _log("", indent=0)

    @staticmethod
    def _show_loop_metadata_and_parameters(loop_dir: Path, loop_config: Dict[str, Any], args: Any):
        """Display loop metadata and execution parameters"""
        _log("Loop Metadata & Execution Parameters", indent=0)
        _log(f"{'─'*80}", indent=0)

        # Detect loop type
        is_markdown = (loop_dir / 'ravl_loop.md').exists()
        is_python = (loop_dir / 'ravl_loop.py').exists()
        loop_type = 'Markdown' if is_markdown else ('Python' if is_python else 'Unknown')

        # Loop Metadata
        _log(f"\n  Loop Metadata:", indent=0)
        _log(f"    Name:         {loop_config.get('name', loop_dir.name)}", indent=0)
        _log(f"    Description:  {loop_config.get('description', 'N/A')}", indent=0)
        _log(f"    Type:         {loop_type}", indent=0)

        if not is_markdown:
            _log(f"    Class:        {loop_config.get('class_name', 'N/A')}", indent=0)
            _log(f"    Module:       {loop_config.get('module', 'ravl_loop')}", indent=0)

        # Template variables for markdown loops
        if is_markdown and 'template_variables' in loop_config:
            _log(f"\n    Template Variables:", indent=0)
            template_vars = loop_config['template_variables']
            if not template_vars:
                _log("      (none)", indent=0)
            else:
                for var_name, var_config in template_vars.items():
                    required = var_config.get('required', False)
                    default = var_config.get('default', None)
                    description = var_config.get('description', '')
                    req_marker = '(required)' if required else '(optional)'
                    default_str = f", default: {default}" if default else ""
                    _log(f"      • {var_name} {req_marker}{default_str}", indent=0)
                    if description:
                        _log(f"        {description}", indent=0)

        # Execution Parameters (ALL options)
        _log(f"\n  Execution Parameters:", indent=0)
        _log(f"    Mode:                {args.mode}", indent=0)
        _log(f"    Deep Learning:       {'[disabled]' if args.no_deep_learning else '[enabled]'}", indent=0)
        _log(f"    Timeout:             {args.timeout} seconds", indent=0)
        _log(f"    Quiet Mode:          {'[enabled]' if args.quiet else '[disabled]'}", indent=0)

        # Show execution details flag
        show_exec = getattr(args, 'show_execution', False)
        _log(f"    Show Execution:      {'[enabled]' if show_exec else '[disabled]'}", indent=0)

        # Path overrides (show if set, otherwise "not set, use --flag")
        learning_path_val = getattr(args, 'learning_path', None)
        if learning_path_val:
            _log(f"    Learning Path:       {learning_path_val}", indent=0)
        else:
            _log(f"    Learning Path:       not set, use --learning-path flag", indent=0)

        venv_path_val = getattr(args, 'venv_path', None)
        if venv_path_val:
            _log(f"    Venv Path:           {venv_path_val}", indent=0)
        else:
            _log(f"    Venv Path:           not set, use --venv-path flag", indent=0)

        loop_dir_val = getattr(args, 'loop_dir', None)
        if loop_dir_val:
            _log(f"    Loop Directory:      {loop_dir_val}", indent=0)
        else:
            _log(f"    Loop Directory:      not set, use --loop-dir flag", indent=0)

        _log("", indent=0)

    @staticmethod
    def _show_environment_variables():
        """Display RAVL-related environment variables"""
        _log("Environment Variables", indent=0)
        _log(f"{'─'*80}", indent=0)
        _log("", indent=0)

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
                _log(f"  [set] {var_name}", indent=0)
                _log(f"        {display_value}", indent=0)

        if not found_any:
            _log("  (no RAVL environment variables set)", indent=0)

        _log("", indent=0)

    @staticmethod
    def _show_loaded_config_files(project_root: Path, loop_dir: Path):
        """Display which config files were loaded"""
        _log("Loaded Configuration Files", indent=0)
        _log(f"{'─'*80}", indent=0)
        _log("", indent=0)

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
                _log(f"  [loaded] {description}", indent=0)
                _log(f"           {config_path}", indent=0)
            else:
                _log(f"  [not found] {description}", indent=0)

        _log("", indent=0)

    @staticmethod
    def _show_dependencies_whitelist(project_root: Path, loop_dir: Path, loop_config: Dict[str, Any]):
        """Display allowed dependencies"""
        _log("Dependency Whitelist", indent=0)
        _log(f"{'─'*80}", indent=0)
        _log("", indent=0)

        # Check if whitelist is in loop config
        allowed_deps = loop_config.get('allowed_dependencies', {})

        if allowed_deps:
            _log(f"  Found {len(allowed_deps)} approved packages in loop config:", indent=0)
            for pkg_name, constraints in list(allowed_deps.items())[:5]:  # Show first 5
                if isinstance(constraints, dict):
                    min_ver = constraints.get('min_version', '')
                    max_ver = constraints.get('max_version', '')
                    version_str = f" ({min_ver} - {max_ver})" if min_ver or max_ver else ""
                    _log(f"    • {pkg_name}{version_str}", indent=0)
                else:
                    _log(f"    • {pkg_name}", indent=0)

            if len(allowed_deps) > 5:
                _log(f"    ... and {len(allowed_deps) - 5} more", indent=0)
        else:
            _log("  No loop-specific whitelist. Inheriting from project/framework defaults.", indent=0)

        _log("", indent=0)

    @staticmethod
    def _show_suggested_command(args: Any, loop_config: Dict[str, Any]):
        """Display suggested run command"""
        _log("Ready to Run", indent=0)
        _log(f"{'─'*80}", indent=0)
        _log("", indent=0)

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

        _log(f"  Command: {' '.join(cmd_parts)}", indent=0)
        _log("", indent=0)
