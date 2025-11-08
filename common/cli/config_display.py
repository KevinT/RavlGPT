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

        print(f"\n{'='*80}", file=sys.stderr)
        print(f"{emoji} Configuration Report: {name}", file=sys.stderr)
        print(f"{'='*80}\n", file=sys.stderr)

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

        print(f"\n{'='*80}\n", file=sys.stderr)

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
        print("📍 Configuration Resolution", file=sys.stderr)
        print(f"{'─'*80}", file=sys.stderr)

        # Loop Directory
        print(f"\n  Loop Directory:", file=sys.stderr)
        print(f"    Source:  {loop_dir_source}", file=sys.stderr)
        print(f"    Path:    {loop_dir}", file=sys.stderr)
        print(f"    Status:  {'✅ Exists' if loop_dir.exists() else '❌ Not found'}", file=sys.stderr)

        # Learning Path
        print(f"\n  Learning Path:", file=sys.stderr)
        print(f"    Source:  {learning_path_source}", file=sys.stderr)
        print(f"    Path:    {learning_path}", file=sys.stderr)
        print(f"    Status:  {'✅ Exists' if learning_path.exists() else '⚠️  Will be created'}", file=sys.stderr)

        # Venv Path
        print(f"\n  Virtual Environment:", file=sys.stderr)
        print(f"    Source:  {venv_path_source}", file=sys.stderr)
        print(f"    Path:    {venv_path}", file=sys.stderr)
        print(f"    Status:  {'✅ Exists' if venv_path.exists() else '⚠️  Will be created'}", file=sys.stderr)
        print()

    @staticmethod
    def _show_loop_configuration(loop_dir: Path, loop_config: Dict[str, Any]):
        """Display loop configuration section"""
        print("🔧 Loop Configuration", file=sys.stderr)
        print(f"{'─'*80}", file=sys.stderr)

        # Detect loop type
        is_markdown = (loop_dir / 'ravl_loop.md').exists()
        is_python = (loop_dir / 'ravl_loop.py').exists()
        loop_type = 'Markdown' if is_markdown else ('Python' if is_python else 'Unknown')

        print(f"\n  Name:         {loop_config.get('name', loop_dir.name)}", file=sys.stderr)
        print(f"  Description:  {loop_config.get('description', 'N/A')}", file=sys.stderr)
        print(f"  Emoji:        {loop_config.get('emoji', '➿')}", file=sys.stderr)
        print(f"  Type:         {loop_type}", file=sys.stderr)

        if not is_markdown:
            print(f"  Class:        {loop_config.get('class_name', 'N/A')}", file=sys.stderr)
            print(f"  Module:       {loop_config.get('module', 'ravl_loop')}", file=sys.stderr)

        print()

        # Template variables for markdown loops
        if is_markdown and 'template_variables' in loop_config:
            ConfigDisplay._show_template_variables(loop_config['template_variables'])

    @staticmethod
    def _show_template_variables(template_vars: Dict[str, Any]):
        """Display template variables for markdown loops"""
        print("  Template Variables:", file=sys.stderr)

        if not template_vars:
            print("    (none)", file=sys.stderr)
            return

        for var_name, var_config in template_vars.items():
            required = var_config.get('required', False)
            default = var_config.get('default', None)
            description = var_config.get('description', '')

            req_marker = '(required)' if required else '(optional)'
            default_str = f", default: {default}" if default else ""

            print(f"    • {var_name} {req_marker}{default_str}", file=sys.stderr)
            if description:
                print(f"      {description}", file=sys.stderr)
        print()

    @staticmethod
    def _show_execution_parameters(args: Any):
        """Display execution parameters section"""
        print("⚙️  Execution Parameters", file=sys.stderr)
        print(f"{'─'*80}", file=sys.stderr)
        print(f"\n  Mode:          {args.mode}", file=sys.stderr)
        print(f"  Deep Learning: {'❌ Disabled (--no-deep-learning)' if args.no_deep_learning else '✅ Enabled'}", file=sys.stderr)
        print(f"  Timeout:       {args.timeout} seconds", file=sys.stderr)
        print(f"  Quiet Mode:    {'✅ Enabled' if args.quiet else '❌ Disabled'}", file=sys.stderr)
        print()

    @staticmethod
    def _show_environment_variables():
        """Display RAVL-related environment variables"""
        print("🌍 Environment Variables", file=sys.stderr)
        print(f"{'─'*80}", file=sys.stderr)
        print()

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
                print(f"  ✅ {var_name}", file=sys.stderr)
                print(f"     {display_value}", file=sys.stderr)

        if not found_any:
            print("  (no RAVL environment variables set)", file=sys.stderr)

        print()

    @staticmethod
    def _show_loaded_config_files(project_root: Path, loop_dir: Path):
        """Display which config files were loaded"""
        print("📄 Loaded Configuration Files", file=sys.stderr)
        print(f"{'─'*80}", file=sys.stderr)
        print()

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
                print(f"  ✅ {description}", file=sys.stderr)
                print(f"     {config_path}", file=sys.stderr)
            else:
                print(f"  ⚪ {description} (not found)", file=sys.stderr)

        print()

    @staticmethod
    def _show_dependencies_whitelist(project_root: Path, loop_dir: Path, loop_config: Dict[str, Any]):
        """Display allowed dependencies"""
        print("📦 Dependency Whitelist", file=sys.stderr)
        print(f"{'─'*80}", file=sys.stderr)
        print()

        # Check if whitelist is in loop config
        allowed_deps = loop_config.get('allowed_dependencies', {})

        if allowed_deps:
            print(f"  Found {len(allowed_deps)} approved packages in loop config:", file=sys.stderr)
            for pkg_name, constraints in list(allowed_deps.items())[:5]:  # Show first 5
                if isinstance(constraints, dict):
                    min_ver = constraints.get('min_version', '')
                    max_ver = constraints.get('max_version', '')
                    version_str = f" ({min_ver} - {max_ver})" if min_ver or max_ver else ""
                    print(f"    • {pkg_name}{version_str}", file=sys.stderr)
                else:
                    print(f"    • {pkg_name}", file=sys.stderr)

            if len(allowed_deps) > 5:
                print(f"    ... and {len(allowed_deps) - 5} more", file=sys.stderr)
        else:
            print("  No loop-specific whitelist. Inheriting from project/framework defaults.", file=sys.stderr)

        print()

    @staticmethod
    def _show_suggested_command(args: Any, loop_config: Dict[str, Any]):
        """Display suggested run command"""
        print("🚀 Ready to Run", file=sys.stderr)
        print(f"{'─'*80}", file=sys.stderr)
        print()

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

        print(f"  Command: {' '.join(cmd_parts)}", file=sys.stderr)
        print()
