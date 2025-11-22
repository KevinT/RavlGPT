#!/usr/bin/env python3
"""
RAVL Loop Discovery

Utilities for finding, loading, and importing RAVL loops.
"""

import sys
import yaml
import inspect
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional, List, Type, Tuple
from datetime import datetime
import os

# Import RAVLRunner for learning path resolution
sys.path.insert(0, str(Path(__file__).parent.parent))
from ravl_runner import RAVLRunner


class LoopDiscovery:
    """Utilities for discovering and loading RAVL loops"""

    def __init__(self, project_root: Path, loops_dir: Optional[Path] = None):
        """
        Initialize loop discovery

        Args:
            project_root: Path to project root (containing .ravl/ subdirectory or ravl_loops/ if installed flat)
            loops_dir: Optional custom path for project loops (defaults to project_root/ravl_loops)
        """
        self.project_root = project_root

        # Set loops directory (project loops)
        self.loops_dir = loops_dir if loops_dir else (project_root / 'ravl_loops')

        # Detect if .ravl/ subdirectory exists (source/project) or flat structure (installed package)
        # Framework loops are always in ravl_loops/ - either .ravl/ravl_loops/ or just ravl_loops/
        has_ravl_subdir = (project_root / '.ravl').exists()
        self.framework_loops_dir = (project_root / '.ravl' / 'ravl_loops') if has_ravl_subdir else (project_root / 'ravl_loops')

    def _build_namespace_from_path(self, loop_path: Path) -> str:
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
            # If not relative to project root, use as-is
            rel_path = loop_path

        # Filter out 'ravl_loops' and 'child_loops' structural directories and build namespace
        parts = [p for p in rel_path.parts if p not in ('ravl_loops', 'child_loops')]

        # Return dot-separated namespace
        return '.'.join(parts)

    def find_loop(self, identifier: str) -> Path:
        """
        Find loop directory by name, hierarchical path, or full path

        Supports multiple addressing patterns:
        - Absolute path: /absolute/path/to/loop
        - Relative path: ./relative/path/to/loop
        - Project-relative: ravl_loops/parent/ravl_loops/child
        - Hierarchical path: parent.child or grandparent.parent.child
        - Loop name only: my_loop (with collision detection)

        Args:
            identifier: Loop name, hierarchical path, or full path

        Returns:
            Path to loop directory

        Raises:
            ValueError: If loop not found or ambiguous (multiple matches)

        Examples:
            find_loop('my_loop')  # Name only
            find_loop('context_ingestion.fetch_fe_content')  # Hierarchical
            find_loop('frontier_delivery.context_ingestion.fetch_fe_content')  # More specific
        """
        # Check if it's a direct path
        path = Path(identifier)
        if path.is_absolute() and path.exists():
            return path

        # Try relative to current directory
        if path.exists() and self._is_loop_dir(path):
            return path.resolve()

        # Try relative to project root
        project_relative = self.project_root / identifier
        if project_relative.exists() and self._is_loop_dir(project_relative):
            return project_relative

        # Try hierarchical path matching (e.g., parent.child or grandparent.parent.child)
        if '.' in identifier:
            segments = identifier.split('.')
            hierarchical_matches = self._find_loops_by_hierarchical_path(segments)

            if len(hierarchical_matches) == 1:
                return hierarchical_matches[0]
            elif len(hierarchical_matches) > 1:
                # Ambiguous hierarchical path
                matches_str = "\n".join([
                    f"  {i+1}. {self._build_namespace_from_path(match)}"
                    for i, match in enumerate(hierarchical_matches)
                ])
                examples = "\n".join([
                    f"  ./ravl {self._build_namespace_from_path(match)}"
                    for match in hierarchical_matches
                ])
                raise ValueError(
                    f"Ambiguous loop path: '{identifier}'\n\n"
                    f"Multiple loops match this hierarchical path:\n{matches_str}\n\n"
                    f"Use a more specific namespace to disambiguate:\n{examples}\n"
                )
            # If no hierarchical matches, fall through to name-based search

        # Search by name in both project and framework ravl_loops/
        # Collect ALL matches (not just first one)
        matches = []
        for loop_dir in self._find_all_loop_dirs():
            if loop_dir.name == identifier:
                matches.append(loop_dir)

        # If multiple matches, filter out examples if there are non-example matches
        # This allows cloned examples to shadow the originals
        if len(matches) > 1:
            non_example_matches = [m for m in matches if not self.is_example_loop(m)]
            if non_example_matches:
                matches = non_example_matches

        # Handle results
        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            # COLLISION DETECTED - show all matches with helpful error
            matches_str = "\n".join([
                f"  {i+1}. {self._build_namespace_from_path(match)}"
                for i, match in enumerate(matches)
            ])
            examples = "\n".join([
                f"  ./ravl {self._build_namespace_from_path(match)}"
                for match in matches
            ])
            raise ValueError(
                f"Ambiguous loop name: '{identifier}'\n\n"
                f"Multiple loops found with this name:\n{matches_str}\n\n"
                f"Please use the namespace to specify which one:\n{examples}\n"
            )

        # Build list of searched locations
        searched = []
        if self.loops_dir.exists():
            searched.append(str(self.loops_dir))
        if self.framework_loops_dir.exists():
            searched.append(str(self.framework_loops_dir))

        raise ValueError(
            f"Loop not found: {identifier}\n"
            f"  Searched in: {', '.join(searched) if searched else 'ravl_loops/'}\n"
            f"  Try: ./ravl --list to see available loops"
        )

    def load_config(self, loop_dir: Path) -> Dict[str, Any]:
        """
        Load ravl.yml configuration with smart defaults

        Args:
            loop_dir: Path to loop directory

        Returns:
            Configuration dictionary with defaults applied
        """
        # Try config/ravl.yml first (new convention), then ravl.yml (backward compat)
        config_file = loop_dir / 'config' / 'ravl.yml'
        if not config_file.exists():
            config_file = loop_dir / 'ravl.yml'

        # Load from file if exists
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                error_msg = f"YAML syntax error in loop config: {config_file}\n  Loop: {loop_dir.name}\n"
                if hasattr(e, 'problem_mark'):
                    error_msg += f"  Error at line {e.problem_mark.line + 1}, column {e.problem_mark.column + 1}\n"
                    if hasattr(e, 'problem'):
                        error_msg += f"  Problem: {e.problem}\n"
                error_msg += "  Check the file for YAML syntax errors (indentation, colons, etc.)"
                raise ValueError(error_msg)
            except Exception as e:
                raise ValueError(f"Cannot read config file {config_file}: {str(e)}")
        else:
            config = {}

        # Always use folder name as loop name (ignore any name field in config)
        config['name'] = loop_dir.name

        if 'class' not in config:
            # Convention: SnakeCase -> CamelCase + "Loop"
            name_parts = config['name'].split('_')
            config['class'] = ''.join(p.capitalize() for p in name_parts) + 'Loop'

        if 'module' not in config:
            config['module'] = 'ravl_loop'

        if 'emoji' not in config:
            config['emoji'] = '➿'

        return config

    def detect_delegation(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if loop configuration contains delegation directive

        Args:
            config: Loop configuration dictionary

        Returns:
            Delegation config dict if present, None otherwise
        """
        return config.get('delegate_to')

    def resolve_delegation_chain(
        self,
        loop_dir: Path,
        config: Dict[str, Any],
        visited: Optional[List[str]] = None
    ) -> Tuple[Path, List[str], Dict[str, Any]]:
        """
        Resolve delegation chain with circular detection

        Args:
            loop_dir: Current loop directory
            config: Current loop configuration
            visited: List of visited loop paths (for circular detection)

        Returns:
            Tuple of (final_loop_dir, delegation_chain, merged_config)

        Raises:
            ValueError: If circular delegation or chain too deep
        """
        if visited is None:
            visited = []

        # Track this loop
        loop_id = str(loop_dir.resolve())
        if loop_id in visited:
            chain_str = ' → '.join([Path(p).name for p in visited] + [loop_dir.name])
            raise ValueError(
                f"Circular delegation detected:\n  {chain_str}\n\n"
                f"Fix: Remove circular reference in config/ravl.yml"
            )

        if len(visited) >= 3:
            chain_str = ' → '.join([Path(p).name for p in visited] + [loop_dir.name])
            raise ValueError(
                f"Delegation chain exceeds maximum depth (3 levels):\n  {chain_str}\n\n"
                f"Fix: Flatten chain or delegate directly to implementation"
            )

        visited.append(loop_id)

        # Check for delegation
        delegation = self.detect_delegation(config)
        if not delegation:
            # End of chain - this is the implementation
            return loop_dir, visited, config

        # Resolve target loop
        target_loop_name = delegation.get('loop')
        if not target_loop_name:
            raise ValueError(
                f"Invalid delegation in {loop_dir.name}: 'loop' field required\n"
                f"Example:\n"
                f"  delegate_to:\n"
                f"    loop: sourcing/google_docs_sourcing"
            )

        # Find target loop with search order
        target_dir = self.find_loop_with_search_order(target_loop_name, loop_dir)

        # Load target config
        target_config = self.load_config(target_dir)

        # Merge configs: delegate defaults + wrapper overrides
        # Pass loop_dir (wrapper) so config_files can be resolved relative to wrapper
        merged_config = self._merge_configs(target_config, delegation, loop_dir)

        # Recurse to resolve further delegation
        return self.resolve_delegation_chain(target_dir, merged_config, visited)

    def find_loop_with_search_order(self, loop_name: str, parent_dir: Path) -> Path:
        """
        Find loop using search order: framework → project → sibling → relative

        Args:
            loop_name: Loop identifier (name or path)
            parent_dir: Parent loop directory (for relative/sibling resolution)

        Returns:
            Path to loop directory

        Raises:
            ValueError: If loop not found or ambiguous
        """
        candidates = []

        # 1. Framework loops (.ravl/ravl_loops/)
        framework_path = self.framework_loops_dir / loop_name
        if framework_path.exists() and self._is_loop_dir(framework_path):
            candidates.append(('framework', framework_path))

        # 2. Project root (ravl_loops/)
        project_path = self.loops_dir / loop_name
        if project_path.exists() and self._is_loop_dir(project_path):
            candidates.append(('project', project_path))

        # 3. Sibling to parent (parent_dir/child_loops/loop_name or parent_dir/loop_name if at top)
        if parent_dir.name in ('ravl_loops', 'child_loops'):
            # Parent is at top level or is a child_loops dir, so siblings are direct children
            sibling_path = parent_dir / loop_name
        else:
            # Parent is a loop, so siblings are in child_loops
            sibling_path = parent_dir.parent / 'child_loops' / loop_name
        if sibling_path.exists() and self._is_loop_dir(sibling_path):
            candidates.append(('sibling', sibling_path))

        # 4. Relative path (parent_dir/loop_name or ../loop_name)
        relative_path = parent_dir / loop_name
        if relative_path.exists() and self._is_loop_dir(relative_path):
            candidates.append(('relative', relative_path))

        # Handle results
        if len(candidates) == 0:
            raise ValueError(
                f"Loop not found: '{loop_name}'\n\n"
                f"Searched in:\n"
                f"  1. Framework loops: {self.framework_loops_dir / loop_name}\n"
                f"  2. Project loops: {self.loops_dir / loop_name}\n"
                f"  3. Sibling loops: {parent_dir / 'ravl_loops' / loop_name}\n"
                f"  4. Relative: {parent_dir / loop_name}\n\n"
                f"Fix: Ensure loop exists or check loop name spelling"
            )

        if len(candidates) == 1:
            return candidates[0][1]

        # Multiple matches - ambiguous
        matches_str = "\n".join([
            f"  {i+1}. {scope}: {self._build_namespace_from_path(path)}"
            for i, (scope, path) in enumerate(candidates)
        ])
        examples = "\n".join([
            f"  {self._build_namespace_from_path(path)}"
            for scope, path in candidates
        ])
        raise ValueError(
            f"Ambiguous loop name: '{loop_name}'\n\n"
            f"Multiple loops found:\n{matches_str}\n\n"
            f"Fix: Use namespace to disambiguate:\n"
            f"  delegate_to:\n"
            f"    loop: {self._build_namespace_from_path(candidates[0][1])}\n\n"
            f"Or use one of these:\n{examples}"
        )

    def _merge_configs(self, base_config: Dict[str, Any], delegation: Dict[str, Any], wrapper_dir: Path) -> Dict[str, Any]:
        """
        Merge base config with delegation overrides

        Args:
            base_config: Target loop's default configuration
            delegation: Delegation directive with overrides
            wrapper_dir: Wrapper loop directory (for resolving config_files paths)

        Returns:
            Merged configuration
        """
        merged = base_config.copy()

        # Load and merge external config files first
        config_files = delegation.get('config_files', [])
        for config_file_path in config_files:
            # Expand ~ for home directory, then resolve path
            config_file = Path(config_file_path).expanduser()

            # If not absolute after expansion, resolve relative to wrapper loop directory
            if not config_file.is_absolute():
                config_file = wrapper_dir / config_file

            # Set up utils path for logging (needed in both success and error paths)
            _utils_dir = Path(__file__).parent.parent / 'utils'
            if str(_utils_dir) not in sys.path:
                sys.path.insert(0, str(_utils_dir))

            if not config_file.exists():
                from logging_utils import log_message
                log_message(f"Config file not found: {config_file}", status='error')
                log_message(f"Specified in: {wrapper_dir.name}/config/ravl.yml", status='error')
                continue

            # Load and merge config file
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    external_config = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                from logging_utils import log_message
                log_message(f"YAML syntax error in config file: {config_file}", status='error')
                if hasattr(e, 'problem_mark'):
                    log_message(f"Error at line {e.problem_mark.line + 1}, column {e.problem_mark.column + 1}", status='error', indent=4)
                    if hasattr(e, 'problem'):
                        log_message(f"Problem: {e.problem}", status='error', indent=4)
                log_message(f"Specified in delegation from loop: {wrapper_dir.name}", status='error')
                log_message(f"Fix: Check YAML syntax in the config file", status='error')
                raise ValueError(
                    f"Invalid YAML syntax in config file: {config_file}\n"
                    f"  Specified in delegation from: {wrapper_dir.name}/config/ravl.yml\n"
                    f"  Check the file for YAML syntax errors (indentation, colons, etc.)"
                )
            except Exception as e:
                from logging_utils import log_message
                log_message(f"Failed to read config file: {config_file}", status='error')
                log_message(f"Error: {str(e)}", status='error', indent=4)
                raise

            # Deep merge external config into merged
            for key, value in external_config.items():
                    if isinstance(value, dict) and isinstance(merged.get(key), dict):
                        # Deep merge for dicts
                        merged[key] = {**merged[key], **value}
                    elif isinstance(value, list) and isinstance(merged.get(key), list):
                        # Extend lists (combine items from both configs)
                        # This allows multiple config files to contribute documents/items
                        merged[key] = merged[key] + value
                    else:
                        # Direct replacement for other types
                        merged[key] = value

        # Apply config_overrides from delegation (highest priority)
        overrides = delegation.get('config_overrides', {})
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                # Deep merge for dict values
                merged[key] = {**merged.get(key, {}), **value}
            else:
                # Direct override
                merged[key] = value

        return merged

    def import_loop_class(self, loop_dir: Path, config: Dict[str, Any]) -> Type:
        """
        Dynamically import loop class

        Args:
            loop_dir: Path to loop directory
            config: Loop configuration

        Returns:
            Loop class

        Raises:
            ImportError: If class cannot be imported
        """
        module_name = config['module']
        class_name = config['class']
        module_path = loop_dir / f"{module_name}.py"

        if not module_path.exists():
            raise ImportError(
                f"Module not found: {module_path}\n"
                f"  Expected: {loop_dir}/{module_name}.py"
            )

        # Add loop directory to path for relative imports
        sys.path.insert(0, str(loop_dir))

        try:
            # Dynamic import
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module spec for {module_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Get class
            if not hasattr(module, class_name):
                raise ImportError(
                    f"Class '{class_name}' not found in {module_path}\n"
                    f"  Available: {[n for n in dir(module) if not n.startswith('_')]}"
                )

            return getattr(module, class_name)

        finally:
            # Clean up path
            if str(loop_dir) in sys.path:
                sys.path.remove(str(loop_dir))

    def find_all_loops(self) -> List[Dict[str, Any]]:
        """
        Recursively find all loops in project

        Returns:
            List of loop info dicts with keys:
            - path: Path to loop directory
            - config: Loop configuration
            - parent: Parent loop path (if nested)
            - last_run: Last run timestamp (if available)
            - loop_type: 'framework' or 'project'
        """
        loops = []

        for loop_dir in self._find_all_loop_dirs():
            config = self._try_load_config(loop_dir)
            if not config:
                continue

            # Determine if this is a framework or project loop
            # Framework loops are under .ravl/ravl_loops/ (or ravl_loops/ if flat installed)
            # Simple check: if path contains '.ravl' it's framework, or if loops_dir == framework_loops_dir (flat install)
            is_framework = '.ravl' in loop_dir.parts or (self.loops_dir == self.framework_loops_dir)

            # Get parent loop if nested
            parent_path = None
            # Check if this is a child loop (contains 'child_loops' in path)
            if 'child_loops' in loop_dir.parts:
                # Find the last index of 'child_loops' (for deeply nested loops)
                child_loops_indices = [i for i, part in enumerate(loop_dir.parts) if part == 'child_loops']
                last_child_loops_idx = child_loops_indices[-1]
                # Parent is everything before the last 'child_loops'
                parent_path = Path(*loop_dir.parts[:last_child_loops_idx])
            # If no 'child_loops' in path, it's a top-level loop (parent = None)

            # Get last run date (pass config for custom learning path resolution)
            last_run = self._get_last_run_date(loop_dir, config)

            loops.append({
                'path': loop_dir,
                'config': config,
                'parent': parent_path,
                'last_run': last_run,
                'loop_type': 'framework' if is_framework else 'project'
            })

        return loops

    def _matches_hierarchical_path(self, loop_path: Path, segments: List[str]) -> bool:
        """
        Check if loop path matches the given hierarchical segments.

        Args:
            loop_path: Full path to loop directory
            segments: Path segments to match (e.g., ['context_ingestion', 'fetch_fe_content'])

        Returns:
            True if all segments appear in order in the loop path

        Example:
            loop_path: /project/ravl_loops/frontier_delivery/child_loops/context_ingestion/fetch_fe_content/
            segments: ['context_ingestion', 'fetch_fe_content']
            Returns: True (both segments appear in order)
        """
        # Last segment MUST match loop directory name
        if loop_path.name != segments[-1]:
            return False

        # Get path components, excluding structural 'ravl_loops' and 'child_loops' directories
        path_parts = [p for p in loop_path.parts if p not in ('ravl_loops', 'child_loops')]

        # Check if all segments appear in order in the path
        segment_idx = 0
        for part in path_parts:
            if segment_idx < len(segments) and part == segments[segment_idx]:
                segment_idx += 1

        return segment_idx == len(segments)

    def _find_loops_by_hierarchical_path(self, segments: List[str]) -> List[Path]:
        """
        Find all loops matching a hierarchical path.

        Args:
            segments: Path segments like ['context_ingestion', 'fetch_fe_content']

        Returns:
            List of matching loop directories

        Example:
            segments: ['context_ingestion', 'fetch_fe_content']
            Returns: [/path/to/ravl_loops/.../context_ingestion/fetch_fe_content/]
        """
        all_loops = self._find_all_loop_dirs()
        matches = []

        for loop_dir in all_loops:
            if self._matches_hierarchical_path(loop_dir, segments):
                matches.append(loop_dir)

        return matches

    def _is_loop_dir(self, path: Path) -> bool:
        """Check if directory contains a RAVL loop implementation"""
        # Check if directory has a loop file
        has_loop_file = (path / 'ravl_loop.py').exists() or (path / 'ravl_loop.md').exists()

        if not has_loop_file:
            return False

        # Exclude learnings subdirectories (contain artifacts, not actual loops)
        # e.g., loop/learnings/current_state/ravl_loop.md is an artifact
        # e.g., loop/ravl_learning/donnas_loop/current_state/ravl_loop.md is an artifact
        for i, part in enumerate(path.parts):
            if part in ('learnings', 'ravl_learning') and i < len(path.parts) - 1:
                # This path is inside a learnings directory
                return False

        return True

    def is_example_loop(self, loop_path: Path) -> bool:
        """
        Check if loop is in examples parent loop

        Args:
            loop_path: Path to loop directory

        Returns:
            True if loop is under examples parent loop
        """
        # Examples are now under framework_loops_dir/examples/
        examples_dir = self.framework_loops_dir / 'examples'
        try:
            loop_path.relative_to(examples_dir)
            return True
        except ValueError:
            return False

    def _find_all_loop_dirs(self) -> List[Path]:
        """Find all directories containing ravl_loop.py or ravl_loop.md in project and framework"""
        loop_dirs = []

        # Search project and framework locations (framework includes templates and examples)
        search_dirs = []
        if self.loops_dir.exists():
            search_dirs.append(self.loops_dir)
        if self.framework_loops_dir.exists() and self.framework_loops_dir not in search_dirs:
            search_dirs.append(self.framework_loops_dir)

        # Recursively find all ravl_loop.py and ravl_loop.md files
        for search_dir in search_dirs:
            for ravl_loop_file in search_dir.rglob('ravl_loop.py'):
                parent_dir = ravl_loop_file.parent
                if self._is_loop_dir(parent_dir):
                    loop_dirs.append(parent_dir)
            for ravl_loop_file in search_dir.rglob('ravl_loop.md'):
                parent_dir = ravl_loop_file.parent
                if parent_dir not in loop_dirs and self._is_loop_dir(parent_dir):
                    loop_dirs.append(parent_dir)

        return sorted(loop_dirs)

    def _try_load_config(self, loop_dir: Path) -> Optional[Dict[str, Any]]:
        """Try to load config, return None if fails"""
        try:
            return self.load_config(loop_dir)
        except Exception:
            return None

    def _get_last_run_date(self, loop_dir: Path, loop_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get last run date from learnings directory (respects custom learning paths)"""
        if loop_config is None:
            loop_config = {}

        # Use RAVLRunner to resolve the actual learning path (could be custom location)
        learnings_dir = RAVLRunner.resolve_learning_path(
            loop_dir,
            loop_config=loop_config,
            project_root=self.project_root
        )

        if not learnings_dir.exists():
            return None

        latest_mtime = None

        try:
            for root, dirs, files in os.walk(learnings_dir):
                for file in files:
                    if file.startswith('.'):
                        continue
                    file_path = Path(root) / file
                    try:
                        mtime = file_path.stat().st_mtime
                        if latest_mtime is None or mtime > latest_mtime:
                            latest_mtime = mtime
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            return None

        if latest_mtime is None:
            return None

        dt = datetime.fromtimestamp(latest_mtime)
        return dt.strftime("%B %d, %Y")

    def get_loop_parameters(self, loop_dir: Path, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract parameters for a loop (works for both Python and Markdown loops)

        Args:
            loop_dir: Path to loop directory
            config: Loop configuration

        Returns:
            List of parameter dicts with keys: name, type, required, help, default
        """
        loop_type = config.get('type', 'python')

        if loop_type == 'markdown':
            return self._get_markdown_parameters(loop_dir, config)
        else:
            return self._get_python_parameters(loop_dir, config)

    def _get_python_parameters(self, loop_dir: Path, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract parameters from Python loop __init__ signature"""
        try:
            # Import the loop class
            LoopClass = self.import_loop_class(loop_dir, config)

            # Extract parameter descriptions from docstring
            param_descriptions = self._extract_param_descriptions_from_docstring(LoopClass.__init__)

            # Get __init__ signature
            sig = inspect.signature(LoopClass.__init__)
            params = []

            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                # Determine if required
                required = param.default == inspect.Parameter.empty

                # Get type hint if available
                param_type = 'str'
                if param.annotation != inspect.Parameter.empty:
                    param_type = getattr(param.annotation, '__name__', str(param.annotation))

                # Check if auto-resolvable
                auto_resolved = param_name in [
                    'model_path', 'learnings_dir', 'config_path',
                    'handbook_root', 'sources_config_path'
                ]

                # Get description from docstring or use generic
                help_text = param_descriptions.get(param_name)
                if not help_text:
                    help_text = f'Parameter for {config["name"]} loop'

                params.append({
                    'name': param_name,
                    'type': param_type,
                    'required': required and not auto_resolved,
                    'auto_resolved': auto_resolved,
                    'default': None if param.default == inspect.Parameter.empty else param.default,
                    'help': help_text
                })

            return params

        except Exception:
            # If we can't inspect, return empty list
            return []

    def _extract_param_descriptions_from_docstring(self, func) -> Dict[str, str]:
        """Extract parameter descriptions from function docstring"""
        param_descriptions = {}

        if not func.__doc__:
            return param_descriptions

        docstring = func.__doc__
        lines = docstring.split('\n')

        # Find Args or Parameters section
        in_args_section = False
        for i, line in enumerate(lines):
            stripped = line.strip()

            # Look for Args: or Parameters: header
            if stripped in ('Args:', 'Parameters:'):
                in_args_section = True
                continue

            # Stop if we hit another section
            if in_args_section and stripped and not line.startswith(' ') and ':' in stripped:
                break

            # Parse parameter lines (e.g., "  param_name: description")
            if in_args_section and stripped and ':' in stripped:
                parts = stripped.split(':', 1)
                if len(parts) == 2:
                    param_name = parts[0].strip()
                    description = parts[1].strip()
                    if description:
                        param_descriptions[param_name] = description

        return param_descriptions

    def _get_markdown_parameters(self, loop_dir: Path, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract parameters from Markdown loop config"""
        # Try multiple locations:
        # 1. template_variables might be in ravl.yml (new: consolidated)
        # 2. template_variables might be in config/config.yml (old: separate)
        template_vars = config.get('template_variables', {})

        # If not in config (ravl.yml), check config.yml
        if not template_vars:
            markdown_config_file = loop_dir / 'config' / 'config.yml'
            if markdown_config_file.exists():
                try:
                    with open(markdown_config_file, 'r', encoding='utf-8') as f:
                        markdown_config = yaml.safe_load(f) or {}
                        template_vars = markdown_config.get('template_variables', {})
                except yaml.YAMLError as e:
                    # YAML syntax error in markdown config - log but continue with empty config
                    _utils_dir = self.ravl_dir / 'common' / 'utils'
                    if _utils_dir not in sys.path:
                        sys.path.insert(0, str(_utils_dir))
                    from logging_utils import log_execution
                    log_execution(f"YAML syntax error in markdown config: {markdown_config_file}", status='error')
                    if hasattr(e, 'problem_mark'):
                        log_execution(f"Error at line {e.problem_mark.line + 1}, column {e.problem_mark.column + 1}", status='error')
                    template_vars = {}  # Continue with empty config
                except FileNotFoundError:
                    template_vars = {}  # Config file doesn't exist, use defaults
                except Exception as e:
                    # Other errors - log but continue
                    _utils_dir = self.ravl_dir / 'common' / 'utils'
                    if _utils_dir not in sys.path:
                        sys.path.insert(0, str(_utils_dir))
                    from logging_utils import log_execution
                    log_execution(f"Cannot read markdown config {markdown_config_file}: {str(e)}", status='error')
                    template_vars = {}

        if not template_vars:
            return []

        try:
            params = []

            for var_name, var_config in template_vars.items():
                cli_arg = var_config.get('cli_arg', f'--{var_name.replace(" ", "-")}')
                # Remove leading dashes for param name
                param_name = cli_arg.lstrip('-').replace('-', '_')

                params.append({
                    'name': param_name,
                    'cli_arg': cli_arg,
                    'type': var_config.get('type', 'string'),
                    'required': var_config.get('required', False),
                    'auto_resolved': False,
                    'default': var_config.get('default'),
                    'help': var_config.get('help', f'Template variable: {var_name}')
                })

            return params

        except Exception:
            return []
