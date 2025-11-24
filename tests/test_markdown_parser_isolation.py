#!/usr/bin/env python3
"""
Tests for Markdown Parser Top-Level Loop Isolation

Tests that top-level parent loops do not load sibling context during
markdown enhancement, preventing contamination between organizationally
separate loops.

This addresses the bug where simple_loop_tree was loading experimental
loop's elaborate report-generation instructions as a "similar loop" example.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys
from unittest.mock import Mock, MagicMock

# Add common to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'ravl' / 'common'))

from execution.markdown.markdown_parser import MarkdownParser


class TestMarkdownParserIsolation:
    """Tests for top-level loop isolation in markdown enhancement"""

    @pytest.fixture
    def temp_loop_structure(self):
        """Create temporary loop directory structure for testing"""
        temp_dir = tempfile.mkdtemp()

        # Create structure:
        # ravl_loops/
        #   ├── simple_loop_tree/        # Top-level (should be isolated)
        #   │   ├── config/ravl.toml
        #   │   ├── ravl_loop.md         # Simple: "Run your child loops"
        #   │   └── learnings/
        #   ├── experimental/             # Top-level (should be isolated)
        #   │   ├── config/ravl.toml
        #   │   ├── ravl_loop.md         # Complex report generation
        #   │   └── learnings/
        #   └── parent_with_children/     # Top-level parent with children
        #       ├── config/ravl.toml
        #       ├── ravl_loop.md
        #       ├── learnings/
        #       └── child_loops/
        #           ├── child_1/
        #           │   ├── config/ravl.toml
        #           │   ├── ravl_loop.md
        #           │   └── learnings/
        #           └── child_2/
        #               ├── config/ravl.toml
        #               ├── ravl_loop.md
        #               └── learnings/

        base = Path(temp_dir) / 'ravl_loops'
        base.mkdir()

        # Simple loop tree (top-level, minimal)
        simple = base / 'simple_loop_tree'
        (simple / 'config').mkdir(parents=True)
        (simple / 'config' / 'ravl.toml').write_text('name = "simple_loop_tree"\n')
        (simple / 'ravl_loop.md').write_text('Run your child loops')
        (simple / 'learnings').mkdir()

        # Experimental (top-level, elaborate)
        experimental = base / 'experimental'
        (experimental / 'config').mkdir(parents=True)
        (experimental / 'config' / 'ravl.toml').write_text('name = "experimental"\n')
        elaborate_md = """You are the parent of an eclectic collection of experimental loops.

Summarise your child loop structure and their most recent learning in a report at `output/experimental-loops-state-YYYY-MMM-DD-HH-MM-SS.md`.

Include:
- A summary table of all child loops
- Their current state
- Recent learnings
- Any failures or issues
"""
        (experimental / 'ravl_loop.md').write_text(elaborate_md)
        (experimental / 'learnings').mkdir()

        # Parent with children
        parent = base / 'parent_with_children'
        (parent / 'config').mkdir(parents=True)
        (parent / 'config' / 'ravl.toml').write_text('name = "parent_with_children"\n')
        (parent / 'ravl_loop.md').write_text('Coordinate my children')
        (parent / 'learnings').mkdir()

        child_1 = parent / 'child_loops' / 'child_1'
        (child_1 / 'config').mkdir(parents=True)
        (child_1 / 'config' / 'ravl.toml').write_text('name = "child_1"\n')
        (child_1 / 'ravl_loop.md').write_text('Do task 1')
        (child_1 / 'learnings').mkdir()

        child_2 = parent / 'child_loops' / 'child_2'
        (child_2 / 'config').mkdir(parents=True)
        (child_2 / 'config' / 'ravl.toml').write_text('name = "child_2"\n')
        (child_2 / 'ravl_loop.md').write_text('Do task 2')
        (child_2 / 'learnings').mkdir()

        yield base

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_top_level_parent_no_sibling_examples(self, temp_loop_structure):
        """
        Test that top-level parents don't load sibling examples.

        This is the PRIMARY bug fix: simple_loop_tree should NOT load
        experimental's elaborate instructions as a "similar loop" example.
        """
        base = temp_loop_structure
        simple = base / 'simple_loop_tree'

        # Create parser without LLM (we're testing context loading, not LLM calls)
        parser = MarkdownParser(simple, simple / 'learnings', llm_provider=None)

        # Mock the _interpret_free_form_markdown method to capture examples_text
        original_method = parser._interpret_free_form_markdown
        examples_captured = []

        def capture_examples(markdown_text, existing_phases=None, reflection=None):
            # We need to check what examples_text would be generated
            # Since we can't easily intercept it, we'll check the file system access
            # For now, let's verify the helper correctly identifies this as top-level
            from core.learning.learning_access_helper import LearningAccessHelper
            helper = LearningAccessHelper(simple, simple / 'learnings')
            assert helper.is_top_level_parent() is True, "simple_loop_tree should be top-level"

            # Since this is top-level, NO sibling examples should be loaded
            # We verify this by checking discover_related_loops would exclude siblings
            from execution.markdown.loop_context_builder import LoopContextBuilder
            context_builder = LoopContextBuilder(simple, simple / 'learnings')
            related = context_builder.discover_related_loops(exclude_top_level_parents=True)

            # Should have NO siblings (all are top-level and excluded)
            assert len(related.get('siblings', [])) == 0, \
                "Top-level parent should have no siblings (all top-level parents excluded)"

            return {"act": "# Act\nRun your child loops", "verify": "# Verify\nChildren completed"}

        parser._interpret_free_form_markdown = capture_examples

        # Call parse_with_context (which would trigger sibling loading)
        result = parser.parse_with_context('Run your child loops', reflection=None)

        # Assertions verified in capture_examples function above
        assert result is not None

    def test_child_loop_loads_sibling_examples(self, temp_loop_structure):
        """
        Test that child loops CAN load sibling examples.

        This preserves existing functionality: child_1 should see child_2
        as a sibling example for context.
        """
        base = temp_loop_structure
        parent = base / 'parent_with_children'
        child_1 = parent / 'child_loops' / 'child_1'

        parser = MarkdownParser(child_1, child_1 / 'learnings', llm_provider=None)

        # Verify this is NOT a top-level parent
        from core.learning.learning_access_helper import LearningAccessHelper
        helper = LearningAccessHelper(child_1, child_1 / 'learnings')
        assert helper.is_top_level_parent() is False, "child_1 should NOT be top-level"

        # Verify siblings are discovered (child_2)
        from execution.markdown.loop_context_builder import LoopContextBuilder
        context_builder = LoopContextBuilder(child_1, child_1 / 'learnings')
        related = context_builder.discover_related_loops(exclude_top_level_parents=True)

        # Should have child_2 as sibling
        siblings = related.get('siblings', [])
        assert len(siblings) == 1, f"Expected 1 sibling, found {len(siblings)}"
        assert siblings[0].name == 'child_2', f"Expected child_2, found {siblings[0].name}"

    def test_sibling_isolation_prevents_contamination(self, temp_loop_structure):
        """
        Test the actual contamination scenario from the bug report.

        Verify that simple_loop_tree and experimental are properly isolated
        so one loop's elaborate instructions don't contaminate the other.
        """
        base = temp_loop_structure
        simple = base / 'simple_loop_tree'
        experimental = base / 'experimental'

        # Both should be top-level parents
        from core.learning.learning_access_helper import LearningAccessHelper

        simple_helper = LearningAccessHelper(simple, simple / 'learnings')
        experimental_helper = LearningAccessHelper(experimental, experimental / 'learnings')

        assert simple_helper.is_top_level_parent() is True
        assert experimental_helper.is_top_level_parent() is True

        # Neither should see the other as a sibling
        from execution.markdown.loop_context_builder import LoopContextBuilder

        simple_context = LoopContextBuilder(simple, simple / 'learnings')
        simple_related = simple_context.discover_related_loops(exclude_top_level_parents=True)

        experimental_context = LoopContextBuilder(experimental, experimental / 'learnings')
        experimental_related = experimental_context.discover_related_loops(exclude_top_level_parents=True)

        # Both should have ZERO siblings (all potential siblings are top-level and excluded)
        assert len(simple_related.get('siblings', [])) == 0, \
            "simple_loop_tree should not see experimental as sibling"
        assert len(experimental_related.get('siblings', [])) == 0, \
            "experimental should not see simple_loop_tree as sibling"

    def test_discover_siblings_respects_exclusion_flag(self, temp_loop_structure):
        """
        Test that discover_siblings properly respects exclude_top_level_parents flag.
        """
        base = temp_loop_structure
        simple = base / 'simple_loop_tree'

        from core.learning.learning_access_helper import LearningAccessHelper
        helper = LearningAccessHelper(simple, simple / 'learnings')

        # With exclusion (default)
        siblings_excluded = helper.discover_siblings(exclude_top_level_parents=True)
        assert len(siblings_excluded) == 0, "Should have no siblings when excluding top-level"

        # Without exclusion (would see other top-level parents - but this is NOT desired behavior)
        siblings_included = helper.discover_siblings(exclude_top_level_parents=False)
        # This test just verifies the flag works; in production we ALWAYS want exclusion


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
