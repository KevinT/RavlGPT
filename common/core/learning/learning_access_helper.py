#!/usr/bin/env python3
"""
Learning Access Helper

Provides canonical methods for accessing learning artifacts across loop hierarchies.
Handles configurable learning paths, parent/child/sibling discovery, and top-level isolation.

USAGE:
  from core.learning.learning_access_helper import LearningAccessHelper

  helper = LearningAccessHelper(loop_dir, learnings_dir)
  parent_path = helper.get_parent_learning_path()
  sibling_path = helper.get_sibling_learning_path('cross_source_synthesizer')
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class LearningAccessHelper:
    """
    Helper for accessing learning artifacts across loop hierarchies

    Handles:
    - Configurable learning paths (respects 6-level priority hierarchy)
    - Parent/child/sibling loop discovery
    - Top-level parent isolation enforcement
    - Path debugging and logging
    """

    def __init__(self, loop_dir: Path, learnings_dir: Path, debug: bool = False):
        """
        Initialize learning access helper

        Args:
            loop_dir: Path to the loop directory (where ravl.yml lives)
            learnings_dir: Path to this loop's learnings directory (resolved via RAVLRunner)
            debug: Enable verbose logging for path resolution
        """
        self.loop_dir = Path(loop_dir).resolve()
        self.learnings_dir = Path(learnings_dir).resolve()
        self.debug = debug

        if self.debug:
            logger.setLevel(logging.DEBUG)

    def is_top_level_parent(self) -> bool:
        """
        Check if this loop is a top-level parent (no parent loop above it)

        Returns:
            True if top-level parent, False otherwise
        """
        # Top-level parents are directly under ravl_loops/
        # Structure: ravl_loops/{top_level_parent}/...
        # NOT: ravl_loops/{parent}/ravl_loops/{child}/...

        parent_dir = self.loop_dir.parent
        if parent_dir.name == 'ravl_loops':
            # Check if there's a parent loop above this
            grandparent_dir = parent_dir.parent
            has_parent_loop = (grandparent_dir / 'config' / 'ravl.yml').exists()
            return not has_parent_loop
        return False

    def get_parent_learning_path(self) -> Optional[Path]:
        """
        Get the learning path for this loop's parent

        Returns:
            Path to parent's learnings directory, or None if no parent
        """
        if self.debug:
            logger.debug(f"Resolving parent learning path for loop: {self.loop_dir}")

        # Check if this is a child loop (parent.name == 'ravl_loops')
        if self.loop_dir.parent.name != 'ravl_loops':
            if self.debug:
                logger.debug("Not a child loop (parent is not 'ravl_loops')")
            return None

        # Parent is the directory above ravl_loops/
        parent_dir = self.loop_dir.parent.parent

        # Verify parent has ravl.yml
        if not (parent_dir / 'config' / 'ravl.yml').exists():
            if self.debug:
                logger.debug(f"No parent loop found at {parent_dir}")
            return None

        # Calculate parent's learning path
        # Strategy: Use loop_dir structure to find parent, then calculate learning path
        # from the relationship between child's loop_dir and learnings_dir

        # Example structures:
        # DEFAULT: child loop_dir = .../parent/ravl_loops/child
        #          child learnings = .../parent/ravl_loops/child/learnings
        #          parent learnings = .../parent/learnings
        # CUSTOM:  child loop_dir = .../parent/ravl_loops/child
        #          child learnings = /data/ravl/parent/child/learnings
        #          parent learnings = /data/ravl/parent/learnings

        # Calculate the relative depth from loop_dir to learnings_dir
        # For DEFAULT: loop_dir -> loop_dir/learnings (depth = 1, learnings at same level)
        # For CUSTOM: complex, learnings_dir structure mirrors loop_dir structure

        # Find common path structure by counting how many levels down child is from parent
        # Parent loop_dir: .../parent
        # Child loop_dir: .../parent/ravl_loops/child (2 levels down)

        # Calculate parent learnings by applying same transformation
        try:
            # Get relative path from loop_dir to learnings_dir
            # If learnings is at loop_dir/learnings, rel_path = 'learnings'
            # If custom, rel_path might be more complex
            rel_learnings = self.learnings_dir.relative_to(self.loop_dir)

            # Parent learnings should be at parent_dir + same relative path
            parent_learning_path = parent_dir / rel_learnings
        except ValueError:
            # learnings_dir is not under loop_dir (custom path)
            # Need to reconstruct path based on loop hierarchy
            # Count levels from child to parent
            child_name = self.loop_dir.name
            parent_name = parent_dir.name

            # Remove child segment from learnings path and add to parent base
            # Convert loop_dir path to learnings_dir path pattern
            # Example: /ravl_loops/parent/ravl_loops/child -> /data/ravl/parent/child
            #          so /data/ravl/parent/child/learnings -> /data/ravl/parent/learnings

            # Find where child_name appears in learnings_dir and remove it
            learnings_str = str(self.learnings_dir)
            loop_str = str(self.loop_dir)

            # Simple heuristic: replace loop_dir with parent_dir in learnings path
            if loop_str in learnings_str:
                parent_learning_path = Path(learnings_str.replace(loop_str, str(parent_dir)))
            else:
                # Fall back to removing last two segments before /learnings
                parent_learning_path = self.learnings_dir.parent.parent / 'learnings'

        if self.debug:
            logger.debug(f"Parent learning path resolved: {parent_learning_path}")

        return parent_learning_path if parent_learning_path.exists() else None

    def get_sibling_learning_path(self, sibling_name: str) -> Optional[Path]:
        """
        Get the learning path for a sibling loop

        Args:
            sibling_name: Name of sibling loop directory

        Returns:
            Path to sibling's learnings directory, or None if not found
        """
        if self.debug:
            logger.debug(f"Resolving sibling learning path for: {sibling_name}")

        # Siblings exist at the same level in the hierarchy
        # Structure: ravl_loops/{parent}/ravl_loops/{sibling_1}/...
        #                                            /{sibling_2}/...

        # Check if this is a child loop
        if self.loop_dir.parent.name != 'ravl_loops':
            if self.debug:
                logger.debug("Not a child loop, cannot have siblings")
            return None

        # Sibling directory
        sibling_dir = self.loop_dir.parent / sibling_name

        # Verify sibling exists and has ravl.yml
        if not (sibling_dir / 'config' / 'ravl.yml').exists():
            if self.debug:
                logger.debug(f"No sibling loop found at {sibling_dir}")
            return None

        # Calculate sibling's learning path
        # Strategy: Replace our loop_dir with sibling_dir, apply same to learnings_dir
        # Similar to parent path calculation but replacing sibling at same level

        try:
            # Get relative path from loop_dir to learnings_dir
            rel_learnings = self.learnings_dir.relative_to(self.loop_dir)

            # Sibling learnings should be at sibling_dir + same relative path
            sibling_learning_path = sibling_dir / rel_learnings
        except ValueError:
            # learnings_dir is not under loop_dir (custom path)
            # Replace loop_dir with sibling_dir in learnings path
            learnings_str = str(self.learnings_dir)
            loop_str = str(self.loop_dir)

            if loop_str in learnings_str:
                sibling_learning_path = Path(learnings_str.replace(loop_str, str(sibling_dir)))
            else:
                # Fall back to simple replacement of loop name
                base_path = self.learnings_dir.parent.parent
                sibling_learning_path = base_path / sibling_name / 'learnings'

        if self.debug:
            logger.debug(f"Sibling learning path resolved: {sibling_learning_path}")

        return sibling_learning_path if sibling_learning_path.exists() else None

    def get_child_learning_path(self, child_name: str) -> Optional[Path]:
        """
        Get the learning path for a child loop

        Args:
            child_name: Name of child loop directory

        Returns:
            Path to child's learnings directory, or None if not found
        """
        if self.debug:
            logger.debug(f"Resolving child learning path for: {child_name}")

        # Children exist under ravl_loops/ subdirectory
        # Structure: {loop_dir}/ravl_loops/{child_name}/...

        child_dir = self.loop_dir / 'ravl_loops' / child_name

        # Verify child exists and has ravl.yml
        if not (child_dir / 'config' / 'ravl.yml').exists():
            if self.debug:
                logger.debug(f"No child loop found at {child_dir}")
            return None

        # Calculate child's learning path
        # Strategy: Append child_dir relative structure to learnings base path

        try:
            # Get relative path from loop_dir to learnings_dir
            rel_learnings = self.learnings_dir.relative_to(self.loop_dir)

            # Child learnings: child_dir + same relative path structure
            child_learning_path = child_dir / rel_learnings
        except ValueError:
            # learnings_dir is not under loop_dir (custom path)
            # Build child path by extending parent learnings path
            # Example: parent learnings = /data/ravl/parent/learnings
            #          child learnings = /data/ravl/parent/child_name/learnings

            # Remove '/learnings' from parent, add child_name, add '/learnings' back
            parent_base = self.learnings_dir.parent
            child_learning_path = parent_base / child_name / 'learnings'

        if self.debug:
            logger.debug(f"Child learning path resolved: {child_learning_path}")

        return child_learning_path if child_learning_path.exists() else None

    def discover_siblings(self, exclude_top_level_parents: bool = True) -> List[str]:
        """
        Discover all sibling loops

        Args:
            exclude_top_level_parents: If True and this loop is a top-level parent,
                                       exclude other top-level parents from results

        Returns:
            List of sibling loop names
        """
        siblings = []

        # Check if this is a child loop
        if self.loop_dir.parent.name != 'ravl_loops':
            return siblings

        # Check if we should exclude top-level parents
        is_top_level = self.is_top_level_parent()

        # Find all siblings in same directory
        siblings_dir = self.loop_dir.parent
        for sibling_dir in siblings_dir.iterdir():
            if not sibling_dir.is_dir() or sibling_dir == self.loop_dir:
                continue

            # Verify sibling has ravl.yml
            if not (sibling_dir / 'config' / 'ravl.yml').exists():
                continue

            # Check if sibling is a top-level parent
            if exclude_top_level_parents and is_top_level:
                # Both this loop and sibling are top-level parents
                # Skip this sibling to enforce isolation
                sibling_helper = LearningAccessHelper(sibling_dir, sibling_dir / 'learnings')
                if sibling_helper.is_top_level_parent():
                    if self.debug:
                        logger.debug(f"Excluding top-level parent sibling: {sibling_dir.name}")
                    continue

            siblings.append(sibling_dir.name)

        return siblings

    def discover_children(self) -> List[str]:
        """
        Discover all child loops

        Returns:
            List of child loop names
        """
        children = []

        children_dir = self.loop_dir / 'ravl_loops'
        if not children_dir.exists():
            return children

        for child_dir in children_dir.iterdir():
            if not child_dir.is_dir():
                continue

            # Verify child has ravl.yml
            if (child_dir / 'config' / 'ravl.yml').exists():
                children.append(child_dir.name)

        return children

    def load_model_from_path(self, learning_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load model.yml from a learning path

        Args:
            learning_path: Path to learnings directory

        Returns:
            Parsed model or None if not found
        """
        model_file = learning_path / 'model.yml'
        if not model_file.exists():
            if self.debug:
                logger.debug(f"No model.yml found at {model_file}")
            return None

        try:
            import yaml
            with open(model_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load model from {model_file}: {e}")
            return None

    def read_sibling_model(self, sibling_name: str) -> Optional[Dict[str, Any]]:
        """
        Read a sibling loop's model (convenience method)

        Args:
            sibling_name: Name of sibling loop

        Returns:
            Sibling's model or None if not found
        """
        sibling_path = self.get_sibling_learning_path(sibling_name)
        if not sibling_path:
            if self.debug:
                logger.debug(f"Could not resolve sibling path for: {sibling_name}")
            return None

        return self.load_model_from_path(sibling_path)

    def read_parent_model(self) -> Optional[Dict[str, Any]]:
        """
        Read parent loop's model (convenience method)

        Returns:
            Parent's model or None if not found
        """
        parent_path = self.get_parent_learning_path()
        if not parent_path:
            if self.debug:
                logger.debug("Could not resolve parent path")
            return None

        return self.load_model_from_path(parent_path)

    def read_child_model(self, child_name: str) -> Optional[Dict[str, Any]]:
        """
        Read a child loop's model (convenience method)

        Args:
            child_name: Name of child loop

        Returns:
            Child's model or None if not found
        """
        child_path = self.get_child_learning_path(child_name)
        if not child_path:
            if self.debug:
                logger.debug(f"Could not resolve child path for: {child_name}")
            return None

        return self.load_model_from_path(child_path)
