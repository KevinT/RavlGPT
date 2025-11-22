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
        # Find project root (uses CWD as fallback if outside RAVL project)
        self.project_root = self.find_project_root(required=False)

        # Use custom loops_dir if provided, otherwise default to project_root/ravl_loops
        effective_loops_dir = loops_dir if loops_dir else None

        self.discovery = LoopDiscovery(self.project_root, loops_dir=effective_loops_dir)

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
        templates = []

        if show_loops:
            all_loops = self.discovery.find_all_loops()
            # Separate into project and framework loops
            all_project = [l for l in all_loops if l.get('loop_type') == 'project']
            all_framework = [l for l in all_loops if l.get('loop_type') == 'framework']

            # Apply loop type filters
            if only_project_loops:
                project_loops = all_project
                framework_loops = []
            elif only_framework_loops:
                project_loops = []
                framework_loops = all_framework
            else:
                project_loops = all_project
                framework_loops = all_framework

        # Templates and examples are now just regular framework loops
        # For --templates flag, filter to show only templates/examples parent loops and their children
        if show_templates and only_templates:
            # Filter framework loops to only show templates and examples
            templates = [l for l in all_framework
                        if 'templates' in str(l['path']) or 'examples' in str(l['path'])]
            framework_loops = []
            project_loops = []

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

    def _is_template_or_example(self, loop_info: Dict[str, Any]) -> bool:
        """
        Check if a loop is under templates/ or examples/ parent loops

        Args:
            loop_info: Loop information dict

        Returns:
            True if loop is a template or example
        """
        loop_path_str = str(loop_info['path'])
        return 'templates' in loop_path_str or 'examples' in loop_path_str

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
        # Print project loops
        if project_loops:
            self.print_header("[Project Loops]", "")
            print(" │", file=sys.stderr)
            # Build hierarchy
            hierarchy = self._build_hierarchy(project_loops)
            # Print top-level loops with tree structure
            for idx, loop_info in enumerate(hierarchy):
                is_last = (idx == len(hierarchy) - 1)
                self._print_project_loop_tree(loop_info, is_last)

        # Print framework loops (includes templates and examples as regular loops)
        # Combine framework_loops and templates since templates are now just framework loops
        all_framework = framework_loops + templates
        if all_framework:
            self.print_header("[Framework Loops]", "")
            print(" │", file=sys.stderr)
            hierarchy = self._build_hierarchy(all_framework)
            for idx, loop_info in enumerate(hierarchy):
                is_last = (idx == len(hierarchy) - 1)
                self._print_project_loop_tree(loop_info, is_last)

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
        # Combine framework loops and templates (templates are now just framework loops)
        all_framework = framework_loops + templates
        self._print_flat(project_loops, all_framework)

    def _print_json_with_templates(self, project_loops: List[Dict[str, Any]], framework_loops: List[Dict[str, Any]], templates: List[Dict[str, Any]]):
        """Print loops and templates as JSON"""
        output = {
            'project_loops': [],
            'framework_loops': []
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

        # Add framework loops (combines framework_loops and templates)
        all_framework = framework_loops + templates
        for loop_info in all_framework:
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

        print(json.dumps(output, indent=2))


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
