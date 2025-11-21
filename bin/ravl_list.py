#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
RAVL-LIST - List all RAVL loops and templates

Discover and display all RAVL loops in the project and available templates.

Usage:
    ravl-list [options]

Options:
    --json              Output as JSON
    --flat              Show flat list (default: tree view)
    --project-loops     Show only project loops
    --framework-loops   Show only framework loops
    --templates         Show only available templates
"""

import sys
import json
import yaml
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# Bootstrap: Find .ravl framework
_current = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_current / 'common'))
sys.path.insert(0, str(_current / 'common' / 'cli'))

from ravl_cli_base import RAVLCLIBase
from loop_discovery import LoopDiscovery


class RAVLListCommand(RAVLCLIBase):
    """List all RAVL loops with status"""

    def __init__(self, loops_dir: Optional[Path] = None):
        """Initialize list command

        Args:
            loops_dir: Optional custom path for project loops
        """
        self.project_root = self.find_project_root()
        self.discovery = LoopDiscovery(self.project_root, loops_dir=loops_dir)

    def run(self, args: argparse.Namespace):
        """
        Execute list command

        Args:
            args: Parsed command-line arguments
        """
        # Determine what to show
        only_templates = getattr(args, 'templates', False)
        only_project_loops = getattr(args, 'project_loops', False)
        only_framework_loops = getattr(args, 'framework_loops', False)
        only_namespaces = getattr(args, 'namespaces_only', False)

        # Capture filter text early (used for all output formats)
        filter_text = getattr(args, 'namespace_filter', None)

        # Auto-enable namespaces-only mode when search criteria provided
        # (provides better UX for search: simple list instead of tree)
        if filter_text and not only_namespaces:
            # Check if user explicitly requested a different output format
            user_requested_format = args.json or args.flat

            if not user_requested_format:
                # Auto-enable namespaces-only for cleaner search results
                only_namespaces = True

        show_loops = not only_templates
        show_templates = not (only_project_loops or only_framework_loops)

        # Find all loops
        all_loops = []
        project_loops = []
        framework_loops = []

        if show_loops:
            all_loops = self.discovery.find_all_loops()
            # Separate into project and framework loops
            all_project = [l for l in all_loops if l.get('loop_type') == 'project']
            all_framework = [l for l in all_loops if l.get('loop_type') == 'framework']

            # Further filter framework loops to only those in .ravl/ravl_loops/
            # (exclude those in .ravl/examples/ and .ravl/templates/)
            framework_loops_only = []
            for loop in all_framework:
                loop_path_str = str(loop['path'])
                # Check if this is in the actual ravl_loops directory, not examples or templates
                if '/.ravl/ravl_loops/' in loop_path_str:
                    framework_loops_only.append(loop)
                elif '/.ravl/examples/' not in loop_path_str and '/.ravl/templates/' not in loop_path_str:
                    # Also include framework loops that aren't in examples/templates subdirs
                    # but are still in .ravl/ (for backward compatibility)
                    if '/.ravl/' in loop_path_str:
                        framework_loops_only.append(loop)

            # Apply loop type filters
            if only_project_loops:
                project_loops = all_project
                framework_loops = []
            elif only_framework_loops:
                project_loops = []
                framework_loops = framework_loops_only
            else:
                project_loops = all_project
                framework_loops = framework_loops_only

        # Find all templates
        templates = []
        if show_templates:
            templates = self._discover_templates()

        # Apply filter to all lists if provided (works for all output formats)
        if filter_text:
            project_loops = self._filter_loops_by_text(project_loops, filter_text)
            framework_loops = self._filter_loops_by_text(framework_loops, filter_text)
            templates = self._filter_loops_by_text(templates, filter_text)

        # Check if we have anything to show
        if not project_loops and not framework_loops and not templates:
            self.print_warning("No RAVL loops or templates found")
            sys.exit(1)

        # Handle namespaces-only output (takes precedence over other formats)
        if only_namespaces:
            self._print_namespaces_only(
                project_loops, framework_loops, templates,
                as_json=args.json,
                filter_text=filter_text
            )
            return

        # Output format
        if args.json:
            self._print_json_with_templates(project_loops, framework_loops, templates)
        else:
            if args.flat:
                self._print_flat_with_templates(project_loops, framework_loops, templates)
            else:
                self._print_tree_with_templates(project_loops, framework_loops, templates)

    def _discover_templates(self) -> List[Dict[str, Any]]:
        """
        Discover available templates and examples

        Returns:
            List of template information dicts
        """
        templates = []

        # Scan both templates and examples directories
        source_dirs = [
            (self.project_root / '.ravl' / 'templates', 'template'),
            (self.project_root / '.ravl' / 'examples', 'example'),
        ]

        for source_dir, source_type in source_dirs:
            if not source_dir.exists():
                continue

            # Scan directories
            for item_dir in sorted(source_dir.iterdir()):
                if not item_dir.is_dir():
                    continue

                # Check for required files
                config_file = item_dir / 'config' / 'ravl.yml'
                loop_file_md = item_dir / 'ravl_loop.md'
                loop_file_py = item_dir / 'ravl_loop.py'

                has_config = config_file.exists()
                has_loop = loop_file_md.exists() or loop_file_py.exists()

                if has_config and has_loop:
                    try:
                        with open(config_file, 'r') as f:
                            config = yaml.safe_load(f) or {}

                        # Determine type based on file presence
                        if loop_file_py.exists():
                            type_label = 'Python'
                        else:
                            type_label = 'Markdown'

                        templates.append({
                            'name': item_dir.name,
                            'config': config,
                            'path': item_dir,
                            'source_type': source_type,
                            'loop_type': type_label,
                            'description': config.get('description', f'{type_label} loop'),
                            'emoji': config.get('emoji', '📋')
                        })
                    except Exception as e:
                        # Skip items with invalid config
                        continue

        return templates

    def _print_tree(self, project_loops: List[Dict[str, Any]], framework_loops: List[Dict[str, Any]]):
        """Print loops in tree view, separated by type"""
        if project_loops:
            self.print_header("[Project Loops]", "")
            print(" │", file=sys.stderr)
            # Build hierarchy
            hierarchy = self._build_hierarchy(project_loops)
            # Print top-level loops with tree structure
            for idx, loop_info in enumerate(hierarchy):
                is_last = (idx == len(hierarchy) - 1)
                self._print_project_loop_tree(loop_info, is_last)

        if framework_loops:
            self.print_header("[Framework Loops (built-in)]", "")
            print(" │", file=sys.stderr)
            # Build hierarchy
            hierarchy = self._build_hierarchy(framework_loops)
            # Print top-level loops with tree structure
            for idx, loop_info in enumerate(hierarchy):
                is_last = (idx == len(hierarchy) - 1)
                self._print_project_loop_tree(loop_info, is_last)

    def _print_flat(self, project_loops: List[Dict[str, Any]], framework_loops: List[Dict[str, Any]]):
        """Print loops in flat list, separated by type"""
        if project_loops:
            self.print_header("[Project Loops]", "")
            for loop_info in sorted(project_loops, key=lambda x: str(x['path'])):
                config = loop_info['config']
                emoji = config.get('emoji', '➰')
                loop_name = loop_info['path'].name
                display_name = self._format_loop_name(loop_name)
                last_run = loop_info.get('last_run') or 'Never'

                # Show full path
                rel_path = loop_info['path'].relative_to(self.project_root)
                print(f"{emoji} {loop_name} - {display_name} - Last run: {last_run} ({rel_path})", file=sys.stderr)

        if framework_loops:
            self.print_header("[Framework Loops (built-in)]", "")
            for loop_info in sorted(framework_loops, key=lambda x: str(x['path'])):
                config = loop_info['config']
                emoji = config.get('emoji', '➰')
                loop_name = loop_info['path'].name
                display_name = self._format_loop_name(loop_name)
                last_run = loop_info.get('last_run') or 'Never'

                # Show full path
                rel_path = loop_info['path'].relative_to(self.project_root)
                print(f"{emoji} {loop_name} - {display_name} - Last run: {last_run} ({rel_path})", file=sys.stderr)

    def _print_json(self, project_loops: List[Dict[str, Any]], framework_loops: List[Dict[str, Any]]):
        """Print loops as JSON"""
        output_project = []
        for loop_info in project_loops:
            loop_name = loop_info['path'].name
            output_project.append({
                'name': loop_name,
                'description': loop_info['config'].get('description', ''),
                'emoji': loop_info['config'].get('emoji', '➰'),
                'path': str(loop_info['path'].relative_to(self.project_root)),
                'last_run': loop_info.get('last_run'),
                'parent': str(loop_info['parent'].relative_to(self.project_root)) if loop_info['parent'] else None,
                'run_command': f"./ravl {loop_name}"
            })

        output_framework = []
        for loop_info in framework_loops:
            loop_name = loop_info['path'].name
            output_framework.append({
                'name': loop_name,
                'description': loop_info['config'].get('description', ''),
                'emoji': loop_info['config'].get('emoji', '➰'),
                'path': str(loop_info['path'].relative_to(self.project_root)),
                'last_run': loop_info.get('last_run'),
                'parent': str(loop_info['parent'].relative_to(self.project_root)) if loop_info['parent'] else None,
                'run_command': f"./ravl {loop_name}"
            })

        output = {
            'project_loops': output_project,
            'framework_loops': output_framework
        }

        print(json.dumps(output, indent=2))

    def _build_hierarchy(self, loops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build hierarchical structure from flat loop list

        Returns:
            List of top-level loops with children nested
        """
        # Create lookup by path
        loops_by_path = {loop['path']: loop for loop in loops}

        # Add children arrays
        for loop in loops:
            loop['children'] = []

        # Build parent-child relationships
        for loop in loops:
            if loop['parent'] and loop['parent'] in loops_by_path:
                parent = loops_by_path[loop['parent']]
                parent['children'].append(loop)

        # Return only top-level (no parent) loops
        top_level = [loop for loop in loops if not loop['parent']]

        # Sort children recursively
        def sort_children(loop):
            loop['children'].sort(key=lambda x: x['path'].name)
            for child in loop['children']:
                sort_children(child)

        for loop in top_level:
            sort_children(loop)

        return sorted(top_level, key=lambda x: x['path'].name)

    def _print_loop_tree(self, loop_info: Dict[str, Any], indent: int = 0):
        """
        Recursively print loop and its children in tree format

        Args:
            loop_info: Loop information dict
            indent: Indentation level
        """
        config = loop_info['config']
        emoji = config.get('emoji', '➰')
        loop_name = loop_info['path'].name
        display_name = self._format_loop_name(loop_name)
        last_run = loop_info.get('last_run') or 'Never'

        indent_str = "  " * indent

        if indent == 0:
            # Top-level loop
            print(f"\n{emoji} {loop_name} - {display_name} - Last run: {last_run}", file=sys.stderr)
        else:
            # Nested loop
            print(f"{indent_str}├─ {emoji} {loop_name} - {display_name} - Last run: {last_run}", file=sys.stderr)

        # Print children
        children = loop_info.get('children', [])
        for idx, child in enumerate(children):
            # Use └─ for last child, ├─ for others
            is_last = (idx == len(children) - 1)
            self._print_loop_tree_child(child, "  ", is_last)

    def _print_loop_tree_child(self, loop_info: Dict[str, Any], prefix: str, is_last: bool):
        """
        Print a child loop with correct tree characters

        Args:
            loop_info: Loop information dict
            prefix: Prefix string built from ancestor tree structure
            is_last: Whether this is the last child in the parent's list
        """
        config = loop_info['config']
        emoji = config.get('emoji', '➰')
        display_name = self._format_loop_name(config['name'])
        loop_name = config['name']
        last_run = loop_info.get('last_run') or 'Never'

        branch = "└─" if is_last else "├─"

        print(f"{prefix}{branch} {emoji} {loop_name} - {display_name} - Last run: {last_run}", file=sys.stderr)

        # Print grandchildren with proper prefix continuation
        # If current node is NOT the last, add vertical line │ to prefix
        # If current node IS the last, add spaces to prefix
        child_prefix = prefix + ("  " if is_last else "│ ")

        children = loop_info.get('children', [])
        for idx, child in enumerate(children):
            is_child_last = (idx == len(children) - 1)
            self._print_loop_tree_child(child, child_prefix, is_child_last)

    def _print_tree_with_templates(self, project_loops: List[Dict[str, Any]], framework_loops: List[Dict[str, Any]], templates: List[Dict[str, Any]]):
        """Print loops and templates in tree view"""
        # Print project loops only
        if project_loops:
            self.print_header("[Project Loops]", "")
            print(" │", file=sys.stderr)
            # Build hierarchy
            hierarchy = self._build_hierarchy(project_loops)
            # Print top-level loops with tree structure
            for idx, loop_info in enumerate(hierarchy):
                is_last = (idx == len(hierarchy) - 1)
                self._print_project_loop_tree(loop_info, is_last)

        # Print framework resources (framework loops, templates, examples) together
        if framework_loops or templates:
            self._print_framework_resources(framework_loops, templates)

    def _build_loop_namespace(self, loop_path: Path) -> str:
        """
        Build dot-separated namespace from loop path.

        Converts hierarchical loop paths to namespaces for easy copy-paste.
        Example: ravl_loops/parent/ravl_loops/child -> parent.child

        Args:
            loop_path: Path to loop directory

        Returns:
            Dot-separated namespace string
        """
        # Get path relative to project root
        try:
            rel_path = loop_path.relative_to(self.project_root)
        except ValueError:
            # If not relative to project root, try framework root
            rel_path = loop_path.relative_to(self.project_root / '.ravl')

        # Filter out 'ravl_loops' and 'child_loops' structural directories and build namespace
        parts = [p for p in rel_path.parts if p not in ('ravl_loops', 'child_loops')]

        # Return dot-separated namespace
        return '.'.join(parts)

    def _filter_loops_by_text(self, loops: List[Dict[str, Any]], filter_text: str) -> List[Dict[str, Any]]:
        """
        Filter loops by partial text matching in namespace.

        When filtering for tree view, also includes parent loops so the hierarchy can be built.

        Args:
            loops: List of loop info dicts
            filter_text: Text to search for (case-insensitive)

        Returns:
            Filtered list of loops (including necessary parents for tree structure)
        """
        if not filter_text:
            return loops

        filter_lower = filter_text.lower()

        # Create lookup by path
        loops_by_path = {loop['path']: loop for loop in loops}

        # Find directly matching loops
        matching_loops = set()
        for loop_info in loops:
            namespace = self._build_loop_namespace(loop_info['path'])
            if filter_lower in namespace.lower():
                matching_loops.add(loop_info['path'])

        # Include all parent loops for tree structure
        loops_to_include = set(matching_loops)
        for loop_path in matching_loops:
            # Walk up parent chain (only for loops that have parents, not templates)
            current = loops_by_path.get(loop_path)
            while current and current.get('parent'):
                loops_to_include.add(current['parent'])
                current = loops_by_path.get(current['parent'])

        # Return loops in original order
        return [loop for loop in loops if loop['path'] in loops_to_include]

    def _print_namespaces_only(self, project_loops: List[Dict[str, Any]], framework_loops: List[Dict[str, Any]], templates: List[Dict[str, Any]], as_json: bool = False, filter_text: Optional[str] = None):
        """
        Print only loop namespaces in simple list format.

        Output is one namespace per line for easy copy-paste.

        Args:
            project_loops: List of project loop info dicts
            framework_loops: List of framework loop info dicts
            templates: List of template info dicts
            as_json: If True, output as JSON array instead of line-by-line
            filter_text: Optional filter string for partial matching (case-insensitive)
        """
        namespaces = []

        # Collect all namespaces
        for loop_info in project_loops:
            namespace = self._build_loop_namespace(loop_info['path'])
            namespaces.append(namespace)

        for loop_info in framework_loops:
            namespace = self._build_loop_namespace(loop_info['path'])
            namespaces.append(namespace)

        for template_info in templates:
            namespace = self._build_loop_namespace(template_info['path'])
            namespaces.append(namespace)

        # Sort alphabetically for easier browsing
        namespaces.sort()

        # Apply filter if provided
        if filter_text:
            filter_lower = filter_text.lower()
            namespaces = [ns for ns in namespaces if filter_lower in ns.lower()]

        # Output
        if as_json:
            # Build filtered output for JSON
            if filter_text:
                filter_lower = filter_text.lower()
                output = {
                    'project_loops': [
                        self._build_loop_namespace(l['path'])
                        for l in project_loops
                        if filter_lower in self._build_loop_namespace(l['path']).lower()
                    ],
                    'framework_loops': [
                        self._build_loop_namespace(l['path'])
                        for l in framework_loops
                        if filter_lower in self._build_loop_namespace(l['path']).lower()
                    ],
                    'templates': [
                        self._build_loop_namespace(t['path'])
                        for t in templates
                        if filter_lower in self._build_loop_namespace(t['path']).lower()
                    ]
                }
            else:
                output = {
                    'project_loops': [self._build_loop_namespace(l['path']) for l in project_loops],
                    'framework_loops': [self._build_loop_namespace(l['path']) for l in framework_loops],
                    'templates': [self._build_loop_namespace(t['path']) for t in templates]
                }
            print(json.dumps(output, indent=2))
        else:
            # Simple line-by-line output
            for namespace in namespaces:
                print(namespace)

    def _print_flat_with_templates(self, project_loops: List[Dict[str, Any]], framework_loops: List[Dict[str, Any]], templates: List[Dict[str, Any]]):
        """Print loops and templates in flat view"""
        self._print_flat(project_loops, framework_loops)
        if templates:
            self._print_templates(templates)

    def _print_json_with_templates(self, project_loops: List[Dict[str, Any]], framework_loops: List[Dict[str, Any]], templates: List[Dict[str, Any]]):
        """Print loops and templates as JSON"""
        output = {
            'project_loops': [],
            'framework_loops': [],
            'templates': []
        }

        # Add project loops
        for loop_info in project_loops:
            loop_name = loop_info['config']['name']
            namespace = self._build_loop_namespace(loop_info['path'])
            output['project_loops'].append({
                'name': loop_name,
                'namespace': namespace,
                'description': loop_info['config'].get('description', ''),
                'emoji': loop_info['config'].get('emoji', '➰'),
                'path': str(loop_info['path'].relative_to(self.project_root)),
                'last_run': loop_info.get('last_run'),
                'parent': str(loop_info['parent'].relative_to(self.project_root)) if loop_info['parent'] else None,
                'run_command': f"./ravl {namespace}"
            })

        # Add framework loops
        for loop_info in framework_loops:
            loop_name = loop_info['config']['name']
            namespace = self._build_loop_namespace(loop_info['path'])
            output['framework_loops'].append({
                'name': loop_name,
                'namespace': namespace,
                'description': loop_info['config'].get('description', ''),
                'emoji': loop_info['config'].get('emoji', '➰'),
                'path': str(loop_info['path'].relative_to(self.project_root)),
                'last_run': loop_info.get('last_run'),
                'parent': str(loop_info['parent'].relative_to(self.project_root)) if loop_info['parent'] else None,
                'run_command': f"./ravl {namespace}"
            })

        # Add templates
        for template_info in templates:
            output['templates'].append({
                'name': template_info['name'],
                'description': template_info.get('description', ''),
                'emoji': template_info.get('emoji', '📋'),
                'path': str(template_info['path'].relative_to(self.project_root)),
                'clone_command': f"./ravl --clone {template_info['name']} <loop_name>"
            })

        print(json.dumps(output, indent=2))

    def _print_templates(self, templates: List[Dict[str, Any]]):
        """Print available templates and examples"""
        # This method is kept for backward compatibility but delegates to new method
        self._print_framework_resources([], templates)

    def _print_framework_resources(self, framework_loops: List[Dict[str, Any]], templates: List[Dict[str, Any]]):
        """Print framework resources: loops, templates, and examples"""
        self.print_header("[Framework Resources]", "")

        # Group templates by source type
        examples = [t for t in templates if t.get('source_type') == 'example']
        templates_only = [t for t in templates if t.get('source_type') == 'template']

        # Print tree structure
        print(" │", file=sys.stderr)

        # Framework Loops subsection
        if framework_loops:
            print(" ├── Framework Loops (built-in loops)", file=sys.stderr)
            # Build hierarchy for framework loops to show nesting
            hierarchy = self._build_hierarchy(framework_loops)
            # Print top-level framework loops with tree structure
            for idx, loop_info in enumerate(hierarchy):
                is_last = (idx == len(hierarchy) - 1)
                self._print_framework_loop_tree(loop_info, " │    ", is_last)
            print(" │", file=sys.stderr)

        # Templates subsection
        if templates_only:
            print(" ├── Templates (useful starting points to clone):", file=sys.stderr)
            if templates_only:
                print(" │    Clone with: ./ravl-clone <name> <new_name>", file=sys.stderr)
            for idx, template in enumerate(sorted(templates_only, key=lambda x: x['name'])):
                emoji = template.get('emoji', '📋')
                template_name = template['name']
                description = template.get('description', 'Template loop')
                # Truncate description to fit on one line
                if len(description) > 50:
                    description = description[:47] + "..."

                is_last = (idx == len(templates_only) - 1)
                branch = " │    └──" if is_last else " │    ├──"
                print(f"{branch} {emoji} {template_name} - {description}", file=sys.stderr)
            print(" │", file=sys.stderr)

        # Examples subsection
        if examples:
            print(" └── Examples (working examples to clone):", file=sys.stderr)
            if examples:
                print("      Clone with: ./ravl-clone <name> <new_name>", file=sys.stderr)
            for idx, example in enumerate(sorted(examples, key=lambda x: x['name'])):
                emoji = example.get('emoji', '📋')
                example_name = example['name']
                description = example.get('description', 'Example loop')
                # Truncate description to fit on one line
                if len(description) > 50:
                    description = description[:47] + "..."

                is_last = (idx == len(examples) - 1)
                branch = "      └──" if is_last else "      ├──"
                print(f"{branch} {emoji} {example_name} - {description}", file=sys.stderr)

    def _print_project_loop_tree(self, loop_info: Dict[str, Any], is_last: bool):
        """
        Print a project loop with tree structure

        Args:
            loop_info: Loop information dict
            is_last: Whether this is the last loop in the list
        """
        config = loop_info['config']
        emoji = config.get('emoji', '➿')
        loop_name = loop_info['path'].name
        display_name = self._format_loop_name(loop_name)
        last_run = loop_info.get('last_run') or 'Never'

        # Use appropriate tree character
        branch = " └──" if is_last else " ├──"
        print(f"{branch} {emoji} {loop_name} - {display_name} - Last run: {last_run}", file=sys.stderr)

        # Print children with proper indentation
        children = loop_info.get('children', [])
        for idx, child in enumerate(children):
            is_child_last = (idx == len(children) - 1)
            child_prefix = " │   " if not is_last else "     "
            self._print_project_loop_child(child, child_prefix, is_child_last)

        # Add separator line after each top-level loop (except the last)
        if not is_last:
            print(" │", file=sys.stderr)

    def _print_project_loop_child(self, loop_info: Dict[str, Any], prefix: str, is_last: bool):
        """
        Print a child project loop with correct tree characters

        Args:
            loop_info: Loop information dict
            prefix: Prefix string for tree structure
            is_last: Whether this is the last child in the parent's list
        """
        config = loop_info['config']
        emoji = config.get('emoji', '➿')
        loop_name = config['name']
        display_name = self._format_loop_name(loop_name)
        last_run = loop_info.get('last_run') or 'Never'

        branch = "└──" if is_last else "├──"
        print(f"{prefix}{branch} {emoji} {loop_name} - {display_name} - Last run: {last_run}", file=sys.stderr)

        # Print grandchildren with proper prefix continuation
        child_prefix = prefix + ("    " if is_last else "│   ")
        children = loop_info.get('children', [])
        for idx, child in enumerate(children):
            is_child_last = (idx == len(children) - 1)
            self._print_project_loop_child(child, child_prefix, is_child_last)

    def _print_framework_loop_tree(self, loop_info: Dict[str, Any], prefix: str, is_last: bool):
        """
        Print a framework loop with tree structure and truncated description

        Args:
            loop_info: Loop information dict
            prefix: Prefix string for indentation (e.g., " │    ")
            is_last: Whether this is the last loop in the list
        """
        config = loop_info['config']
        emoji = config.get('emoji', '➿')
        loop_name = loop_info['path'].name
        description = config.get('description', '')

        # Truncate description to fit on one line
        if len(description) > 50:
            description = description[:47] + "..."

        branch = "└──" if is_last else "├──"
        print(f"{prefix}{branch} {emoji} {loop_name} - {description}", file=sys.stderr)

        # Print children with proper indentation
        children = loop_info.get('children', [])
        child_prefix = prefix + ("    " if is_last else "│   ")
        for idx, child in enumerate(children):
            is_child_last = (idx == len(children) - 1)
            self._print_framework_loop_tree(child, child_prefix, is_child_last)

    def _format_loop_name(self, name: str) -> str:
        """Format loop name for display (snake_case to Title Case)"""
        return ' '.join(word.capitalize() for word in name.split('_'))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='List all RAVL loops and templates in the project',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )
    parser.add_argument(
        '--flat',
        action='store_true',
        help='Show flat list instead of tree view'
    )
    parser.add_argument(
        '--project-loops',
        action='store_true',
        help='Show only project loops'
    )
    parser.add_argument(
        '--framework-loops',
        action='store_true',
        help='Show only framework loops'
    )
    parser.add_argument(
        '--templates',
        action='store_true',
        help='Show only available templates'
    )
    parser.add_argument(
        '--namespaces-only',
        action='store_true',
        help='Show only loop namespaces (dot-separated paths) for easy copy-paste'
    )
    parser.add_argument(
        '--loop-dir',
        type=str,
        default=None,
        help='Override loop directory path (highest priority: CLI > .env > default)'
    )
    parser.add_argument(
        'namespace_filter',
        nargs='?',
        default=None,
        help='Optional filter: show only namespaces containing this text (case-insensitive)'
    )

    args = parser.parse_args()

    # Resolve loop directory if provided
    resolved_loops_dir = None
    if args.loop_dir:
        resolved_loops_dir = Path(args.loop_dir).expanduser().resolve()

    lister = RAVLListCommand(loops_dir=resolved_loops_dir)
    lister.run(args)


if __name__ == '__main__':
    main()
