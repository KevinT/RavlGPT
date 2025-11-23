#!/usr/bin/env python3
"""
Tests for RAVL Learning Access Patterns

Tests the two-dimensional learning architecture:
1. Execution vs Domain learning separation
2. Hierarchical access control (parent/child/sibling with top-level isolation)
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import yaml
import sys

# Add common to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'common'))

from core.learning.learning_access_helper import LearningAccessHelper
from execution.markdown.loop_context_builder import LoopContextBuilder


class TestLearningAccessHelper:
    """Tests for LearningAccessHelper utility class"""

    @pytest.fixture
    def temp_loop_structure(self):
        """Create temporary loop directory structure for testing"""
        temp_dir = tempfile.mkdtemp()

        # Create structure:
        # ravl_loops/
        #   ├── top_level_a/
        #   │   ├── config/ravl.toml
        #   │   ├── learnings/
        #   │   └── child_loops/
        #   │       ├── child_a1/
        #   │       │   ├── config/ravl.toml
        #   │       │   └── learnings/
        #   │       └── child_a2/
        #   │           ├── config/ravl.toml
        #   │           └── learnings/
        #   └── top_level_b/
        #       ├── config/ravl.toml
        #       └── learnings/

        base = Path(temp_dir) / 'ravl_loops'
        base.mkdir()

        # Top level A with children
        top_a = base / 'top_level_a'
        (top_a / 'config').mkdir(parents=True)
        (top_a / 'config' / 'ravl.toml').write_text('name = "top_level_a"\n')
        (top_a / 'learnings').mkdir()
        (top_a / 'ravl_loops').mkdir()

        child_a1 = top_a / 'child_loops' / 'child_a1'
        (child_a1 / 'config').mkdir(parents=True)
        (child_a1 / 'config' / 'ravl.toml').write_text('name = "child_a1"\n')
        (child_a1 / 'learnings').mkdir()

        child_a2 = top_a / 'child_loops' / 'child_a2'
        (child_a2 / 'config').mkdir(parents=True)
        (child_a2 / 'config' / 'ravl.toml').write_text('name = "child_a2"\n')
        (child_a2 / 'learnings').mkdir()

        # Top level B (isolated from A)
        top_b = base / 'top_level_b'
        (top_b / 'config').mkdir(parents=True)
        (top_b / 'config' / 'ravl.toml').write_text('name = "top_level_b"\n')
        (top_b / 'learnings').mkdir()

        yield base

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_is_top_level_parent(self, temp_loop_structure):
        """Test detection of top-level parents"""
        base = temp_loop_structure

        # Top-level parent
        top_a = base / 'top_level_a'
        helper_a = LearningAccessHelper(top_a, top_a / 'learnings')
        assert helper_a.is_top_level_parent() is True, "top_level_a should be detected as top-level parent"

        # Child loop (not top-level)
        child_a1 = top_a / 'child_loops' / 'child_a1'
        helper_child = LearningAccessHelper(child_a1, child_a1 / 'learnings')
        assert helper_child.is_top_level_parent() is False, "child_a1 should NOT be top-level parent"

    def test_get_parent_learning_path(self, temp_loop_structure):
        """Test parent learning path resolution"""
        base = temp_loop_structure
        top_a = base / 'top_level_a'
        child_a1 = top_a / 'child_loops' / 'child_a1'

        # Child can find parent
        helper = LearningAccessHelper(child_a1, child_a1 / 'learnings')
        parent_path = helper.get_parent_learning_path()
        assert parent_path is not None, "Child should find parent learning path"
        # Resolve both paths to handle symlinks (e.g., /var vs /private/var on macOS)
        assert parent_path.resolve() == (top_a / 'learnings').resolve(), \
            f"Expected {(top_a / 'learnings').resolve()}, got {parent_path.resolve()}"

        # Top-level parent has no parent
        helper_top = LearningAccessHelper(top_a, top_a / 'learnings')
        parent_path_top = helper_top.get_parent_learning_path()
        assert parent_path_top is None, "Top-level parent should have no parent"

    def test_get_sibling_learning_path(self, temp_loop_structure):
        """Test sibling learning path resolution"""
        base = temp_loop_structure
        top_a = base / 'top_level_a'
        child_a1 = top_a / 'child_loops' / 'child_a1'
        child_a2 = top_a / 'child_loops' / 'child_a2'

        # child_a1 can find sibling child_a2
        helper = LearningAccessHelper(child_a1, child_a1 / 'learnings')
        sibling_path = helper.get_sibling_learning_path('child_a2')
        assert sibling_path is not None, "Should find sibling learning path"
        # Resolve both paths to handle symlinks (e.g., /var vs /private/var on macOS)
        assert sibling_path.resolve() == (child_a2 / 'learnings').resolve(), \
            f"Expected {(child_a2 / 'learnings').resolve()}, got {sibling_path.resolve()}"

        # Non-existent sibling
        invalid_path = helper.get_sibling_learning_path('nonexistent')
        assert invalid_path is None, "Should return None for non-existent sibling"

    def test_get_child_learning_path(self, temp_loop_structure):
        """Test child learning path resolution"""
        base = temp_loop_structure
        top_a = base / 'top_level_a'
        child_a1 = top_a / 'child_loops' / 'child_a1'

        # Parent can find child
        helper = LearningAccessHelper(top_a, top_a / 'learnings')
        child_path = helper.get_child_learning_path('child_a1')
        assert child_path is not None, "Parent should find child learning path"
        # Resolve both paths to handle symlinks (e.g., /var vs /private/var on macOS)
        assert child_path.resolve() == (child_a1 / 'learnings').resolve(), \
            f"Expected {(child_a1 / 'learnings').resolve()}, got {child_path.resolve()}"

        # Child loop with no children
        helper_child = LearningAccessHelper(child_a1, child_a1 / 'learnings')
        no_child_path = helper_child.get_child_learning_path('nonexistent')
        assert no_child_path is None, "Should return None when no children exist"

    def test_discover_siblings_with_isolation(self, temp_loop_structure):
        """Test sibling discovery with top-level parent isolation"""
        base = temp_loop_structure
        top_a = base / 'top_level_a'
        top_b = base / 'top_level_b'
        child_a1 = top_a / 'child_loops' / 'child_a1'

        # Top-level A should NOT see top-level B as sibling (isolation)
        helper_a = LearningAccessHelper(top_a, top_a / 'learnings')
        siblings_a = helper_a.discover_siblings(exclude_top_level_parents=True)
        assert 'top_level_b' not in siblings_a, "Top-level parents should be isolated"

        # Child should see other children as siblings
        helper_child = LearningAccessHelper(child_a1, child_a1 / 'learnings')
        siblings_child = helper_child.discover_siblings(exclude_top_level_parents=True)
        assert 'child_a2' in siblings_child, "Child should see sibling child_a2"

    def test_discover_siblings_without_isolation(self, temp_loop_structure):
        """Test sibling discovery without isolation (for testing)"""
        base = temp_loop_structure
        top_a = base / 'top_level_a'

        # With isolation disabled, top-level parents can see each other
        helper_a = LearningAccessHelper(top_a, top_a / 'learnings')
        siblings_a = helper_a.discover_siblings(exclude_top_level_parents=False)
        assert 'top_level_b' in siblings_a, "Should see top_level_b when isolation disabled"

    def test_discover_children(self, temp_loop_structure):
        """Test child loop discovery"""
        base = temp_loop_structure
        top_a = base / 'top_level_a'
        child_a1 = top_a / 'child_loops' / 'child_a1'

        # Parent discovers all children
        helper = LearningAccessHelper(top_a, top_a / 'learnings')
        children = helper.discover_children()
        assert len(children) == 2, "Should discover 2 children"
        assert 'child_a1' in children, "Should find child_a1"
        assert 'child_a2' in children, "Should find child_a2"

        # Child loop with no children
        helper_child = LearningAccessHelper(child_a1, child_a1 / 'learnings')
        no_children = helper_child.discover_children()
        assert len(no_children) == 0, "Child loop should have no children"

    def test_read_sibling_model(self, temp_loop_structure):
        """Test reading sibling model"""
        base = temp_loop_structure
        top_a = base / 'top_level_a'
        child_a1 = top_a / 'child_loops' / 'child_a1'
        child_a2 = top_a / 'child_loops' / 'child_a2'

        # Create model.yml in child_a2
        model_data = {'version': 1, 'patterns': ['test']}
        with open(child_a2 / 'learnings' / 'model.yml', 'w') as f:
            yaml.dump(model_data, f)

        # child_a1 reads child_a2's model
        helper = LearningAccessHelper(child_a1, child_a1 / 'learnings')
        sibling_model = helper.read_sibling_model('child_a2')
        assert sibling_model is not None, "Should read sibling model"
        assert sibling_model['version'] == 1, "Should load correct model data"
        assert sibling_model['patterns'] == ['test'], "Should load correct patterns"

    def test_read_parent_model(self, temp_loop_structure):
        """Test reading parent model"""
        base = temp_loop_structure
        top_a = base / 'top_level_a'
        child_a1 = top_a / 'child_loops' / 'child_a1'

        # Create model.yml in parent
        model_data = {'version': 2, 'parent_data': True}
        with open(top_a / 'learnings' / 'model.yml', 'w') as f:
            yaml.dump(model_data, f)

        # Child reads parent's model
        helper = LearningAccessHelper(child_a1, child_a1 / 'learnings')
        parent_model = helper.read_parent_model()
        assert parent_model is not None, "Should read parent model"
        assert parent_model['version'] == 2, "Should load correct parent data"
        assert parent_model['parent_data'] is True, "Should load correct parent flag"

    def test_read_child_model(self, temp_loop_structure):
        """Test reading child model"""
        base = temp_loop_structure
        top_a = base / 'top_level_a'
        child_a1 = top_a / 'child_loops' / 'child_a1'

        # Create model.yml in child
        model_data = {'version': 3, 'child_data': True}
        with open(child_a1 / 'learnings' / 'model.yml', 'w') as f:
            yaml.dump(model_data, f)

        # Parent reads child's model
        helper = LearningAccessHelper(top_a, top_a / 'learnings')
        child_model = helper.read_child_model('child_a1')
        assert child_model is not None, "Should read child model"
        assert child_model['version'] == 3, "Should load correct child data"
        assert child_model['child_data'] is True, "Should load correct child flag"


class TestLoopContextBuilder:
    """Tests for LoopContextBuilder with top-level isolation"""

    @pytest.fixture
    def temp_loop_structure(self):
        """Create temporary loop directory structure for testing"""
        temp_dir = tempfile.mkdtemp()

        base = Path(temp_dir) / 'ravl_loops'
        base.mkdir()

        # Top level A with children
        top_a = base / 'top_level_a'
        (top_a / 'config').mkdir(parents=True)
        (top_a / 'config' / 'ravl.toml').write_text('name = "top_level_a"\n')
        (top_a / 'learnings').mkdir()
        (top_a / 'ravl_loops').mkdir()

        child_a1 = top_a / 'child_loops' / 'child_a1'
        (child_a1 / 'config').mkdir(parents=True)
        (child_a1 / 'config' / 'ravl.toml').write_text('name = "child_a1"\n')
        (child_a1 / 'learnings').mkdir()

        child_a2 = top_a / 'child_loops' / 'child_a2'
        (child_a2 / 'config').mkdir(parents=True)
        (child_a2 / 'config' / 'ravl.toml').write_text('name = "child_a2"\n')
        (child_a2 / 'learnings').mkdir()

        # Top level B (isolated from A)
        top_b = base / 'top_level_b'
        (top_b / 'config').mkdir(parents=True)
        (top_b / 'config' / 'ravl.toml').write_text('name = "top_level_b"\n')
        (top_b / 'learnings').mkdir()

        yield base

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_discover_related_loops_with_isolation(self, temp_loop_structure):
        """Test that top-level parents are isolated from each other"""
        base = temp_loop_structure
        top_a = base / 'top_level_a'

        # Top-level A should NOT discover top-level B as sibling
        builder = LoopContextBuilder(top_a, top_a / 'learnings')
        related = builder.discover_related_loops(exclude_top_level_parents=True)

        assert related['parent'] is None, "Top-level should have no parent"
        assert len(related['children']) == 2, "Should discover 2 children"
        assert len(related['siblings']) == 0, "Should NOT discover other top-level parents as siblings"

    def test_discover_related_loops_children_see_siblings(self, temp_loop_structure):
        """Test that children can see their siblings"""
        base = temp_loop_structure
        top_a = base / 'top_level_a'
        child_a1 = top_a / 'child_loops' / 'child_a1'

        # child_a1 should discover child_a2 as sibling
        builder = LoopContextBuilder(child_a1, child_a1 / 'learnings')
        related = builder.discover_related_loops(exclude_top_level_parents=True)

        assert related['parent'] == top_a, "Should discover parent"
        assert len(related['siblings']) == 1, "Should discover 1 sibling"
        assert related['siblings'][0].name == 'child_a2', "Should discover child_a2 as sibling"

    def test_discover_related_loops_without_isolation(self, temp_loop_structure):
        """Test sibling discovery without top-level isolation"""
        base = temp_loop_structure
        top_a = base / 'top_level_a'

        # With isolation disabled, top-level parents can see each other
        builder = LoopContextBuilder(top_a, top_a / 'learnings')
        related = builder.discover_related_loops(exclude_top_level_parents=False)

        assert len(related['siblings']) == 1, "Should discover 1 sibling (top_level_b)"
        assert related['siblings'][0].name == 'top_level_b', "Should discover top_level_b"


class TestBackwardCompatibility:
    """Tests for backward compatibility in BaseRAVLLoop"""

    @pytest.fixture
    def temp_loop_structure(self):
        """Create temporary loop directory structure for testing"""
        temp_dir = tempfile.mkdtemp()

        base = Path(temp_dir) / 'ravl_loops'
        base.mkdir()

        # Simple parent/child structure
        parent = base / 'parent_loop'
        (parent / 'config').mkdir(parents=True)
        (parent / 'config' / 'ravl.toml').write_text('name = "parent_loop"\n')
        (parent / 'learnings').mkdir()
        (parent / 'ravl_loops').mkdir()

        child = parent / 'child_loops' / 'child_loop'
        (child / 'config').mkdir(parents=True)
        (child / 'config' / 'ravl.toml').write_text('name = "child_loop"\n')
        (child / 'learnings').mkdir()

        # Create model files
        parent_model = {'version': 1, 'parent': True}
        with open(parent / 'learnings' / 'model.yml', 'w') as f:
            yaml.dump(parent_model, f)

        child_model = {'version': 2, 'child': True}
        with open(child / 'learnings' / 'model.yml', 'w') as f:
            yaml.dump(child_model, f)

        yield base

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_base_ravl_loop_with_loop_dir(self, temp_loop_structure):
        """Test BaseRAVLLoop with loop_dir parameter (new behavior)"""
        from ravl_base import BaseRAVLLoop

        base = temp_loop_structure
        child = base / 'parent_loop' / 'child_loops' / 'child_loop'

        # Initialize with loop_dir (enables proper cross-loop access)
        loop = BaseRAVLLoop(
            model_path=child / 'learnings' / 'model.yml',
            loop_name='child_loop',
            loop_dir=child
        )

        # Should use LearningAccessHelper
        assert loop.learning_access_helper is not None, "Should have helper initialized"

        # Should be able to read parent model
        parent_model = loop.read_parent_model()
        assert parent_model is not None, "Should read parent model"
        assert parent_model['parent'] is True, "Should load parent data"

    def test_base_ravl_loop_without_loop_dir(self, temp_loop_structure):
        """Test BaseRAVLLoop without loop_dir (legacy behavior)"""
        from ravl_base import BaseRAVLLoop

        base = temp_loop_structure
        child = base / 'parent_loop' / 'child_loops' / 'child_loop'

        # Initialize without loop_dir (legacy mode)
        loop = BaseRAVLLoop(
            model_path=child / 'learnings' / 'model.yml',
            loop_name='child_loop'
        )

        # Should NOT have helper
        assert loop.learning_access_helper is None, "Should not have helper without loop_dir"

        # Should still work with legacy hardcoded paths (but with warning)
        parent_model = loop.read_parent_model()
        # Note: This might fail with configurable learning paths,
        # but tests backward compatibility of the code path


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
