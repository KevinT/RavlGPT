#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Unit tests for InteractiveUnknownsAsker

Tests interactive prompting for unknown unknowns answers, covering:
- Question parsing from markdown
- Interactive prompting with skip options
- Attribution collection
- Persistence via KnownKnownsManager
- Edge cases (empty files, missing files, etc.)
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import shutil

from ravl.common.core.interactive_unknowns_asker import InteractiveUnknownsAsker


@pytest.fixture
def temp_learnings_dir():
    """Create temporary learnings directory for testing"""
    temp_dir = Path(tempfile.mkdtemp())

    # Create structure for both categories
    (temp_dir / "execution_learning" / "current_state").mkdir(parents=True, exist_ok=True)
    (temp_dir / "loop_learning" / "current_state").mkdir(parents=True, exist_ok=True)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


class TestInteractiveUnknownsAskerInitialization:
    """Test InteractiveUnknownsAsker initialization"""

    def test_init_execution_category(self, temp_learnings_dir):
        """Test initialization with execution category"""
        asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution", "test_user")

        assert asker.category == "execution"
        assert asker.answered_by == "test_user"
        assert "execution_learning" in str(asker.unknowns_file)
        assert asker.category_label == "Execution Unknowns (Infrastructure)"
        assert asker.emoji == "🔧"

    def test_init_domain_category(self, temp_learnings_dir):
        """Test initialization with domain category"""
        asker = InteractiveUnknownsAsker(temp_learnings_dir, "domain", "test_user")

        assert asker.category == "domain"
        assert asker.answered_by == "test_user"
        assert "loop_learning" in str(asker.unknowns_file)
        assert asker.category_label == "Loop Unknowns (Domain)"
        assert asker.emoji == "📋"

    def test_init_invalid_category(self, temp_learnings_dir):
        """Test initialization with invalid category raises error"""
        with pytest.raises(ValueError, match="Invalid category"):
            InteractiveUnknownsAsker(temp_learnings_dir, "invalid", "test_user")


class TestQuestionParsing:
    """Test parsing of questions from markdown files"""

    def test_parse_valid_questions(self, temp_learnings_dir):
        """Test parsing valid markdown with questions"""
        # Create test file
        unknowns_file = temp_learnings_dir / "execution_learning" / "current_state" / "known_execution_unknowns.md"
        unknowns_file.write_text("""# Known Execution Unknowns

## Question 1
What are the API rate limits?

**Answer**: _[Fill in your answer]_

**Answered by**: _[Your name]_

---

## Question 2
What are the memory limits?

**Answer**: _[Fill in your answer]_

**Answered by**: _[Your name]_

---
""")

        asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution")
        questions = asker._parse_unknowns_file(unknowns_file)

        assert len(questions) == 2
        assert questions[0] == "What are the API rate limits?"
        assert questions[1] == "What are the memory limits?"

    def test_parse_multiline_question(self, temp_learnings_dir):
        """Test parsing question that spans multiple lines"""
        unknowns_file = temp_learnings_dir / "execution_learning" / "current_state" / "known_execution_unknowns.md"
        unknowns_file.write_text("""# Known Execution Unknowns

## Question 1
What are the specific API rate limits
or throttling constraints for the service
being called?

**Answer**: _[Fill in your answer]_

**Answered by**: _[Your name]_

---
""")

        asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution")
        questions = asker._parse_unknowns_file(unknowns_file)

        assert len(questions) == 1
        # Multiline question should be normalized to single line
        assert "API rate limits or throttling constraints" in questions[0]

    def test_parse_empty_file(self, temp_learnings_dir):
        """Test parsing empty file returns empty list"""
        unknowns_file = temp_learnings_dir / "execution_learning" / "current_state" / "known_execution_unknowns.md"
        unknowns_file.write_text("")

        asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution")
        questions = asker._parse_unknowns_file(unknowns_file)

        assert questions == []

    def test_parse_no_questions(self, temp_learnings_dir):
        """Test parsing file with headers but no questions"""
        unknowns_file = temp_learnings_dir / "execution_learning" / "current_state" / "known_execution_unknowns.md"
        unknowns_file.write_text("""# Known Execution Unknowns

These are infrastructure questions.

No questions yet.
""")

        asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution")
        questions = asker._parse_unknowns_file(unknowns_file)

        assert questions == []

    def test_parse_nonexistent_file(self, temp_learnings_dir):
        """Test parsing nonexistent file returns empty list"""
        unknowns_file = temp_learnings_dir / "execution_learning" / "current_state" / "nonexistent.md"

        asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution")
        questions = asker._parse_unknowns_file(unknowns_file)

        assert questions == []


class TestAskUnknowns:
    """Test interactive prompting for unknowns"""

    def test_ask_unknowns_no_file(self, temp_learnings_dir):
        """Test ask_unknowns returns (0, False) when file doesn't exist"""
        asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution", "test_user")

        answered, exited = asker.ask_unknowns()

        assert answered == 0
        assert exited == False

    def test_ask_unknowns_empty_file(self, temp_learnings_dir):
        """Test ask_unknowns returns (0, False) when file is empty"""
        unknowns_file = temp_learnings_dir / "execution_learning" / "current_state" / "known_execution_unknowns.md"
        unknowns_file.write_text("")

        asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution", "test_user")

        answered, exited = asker.ask_unknowns()

        assert answered == 0
        assert exited == False

    @patch('builtins.input')
    def test_ask_unknowns_skip_individual(self, mock_input, temp_learnings_dir):
        """Test skipping individual questions with 's'"""
        # Create test file with 2 questions
        unknowns_file = temp_learnings_dir / "execution_learning" / "current_state" / "known_execution_unknowns.md"
        unknowns_file.write_text("""# Known Execution Unknowns

## Question 1
What are the API rate limits?

**Answer**: _[Fill in your answer]_

---

## Question 2
What are the memory limits?

**Answer**: _[Fill in your answer]_

---
""")

        # Mock user input: skip first, skip second (no attribution prompt)
        mock_input.side_effect = ['s', 's']

        asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution", "test_user")
        answered, exited = asker.ask_unknowns()

        assert answered == 0  # No questions answered
        assert exited == False

    @patch('builtins.input')
    def test_ask_unknowns_skip_all(self, mock_input, temp_learnings_dir):
        """Test skipping all remaining questions with 'skip-all'"""
        # Create test file with 3 questions
        unknowns_file = temp_learnings_dir / "execution_learning" / "current_state" / "known_execution_unknowns.md"
        unknowns_file.write_text("""# Known Execution Unknowns

## Question 1
Question one?

**Answer**: _[Fill in]_

---

## Question 2
Question two?

**Answer**: _[Fill in]_

---

## Question 3
Question three?

**Answer**: _[Fill in]_

---
""")

        # Mock user input: skip-all on first question
        mock_input.side_effect = ['skip-all']

        asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution", "test_user")
        answered, exited = asker.ask_unknowns()

        assert answered == 0  # No questions answered
        assert exited == False

    @patch('builtins.input')
    def test_ask_unknowns_exit_command(self, mock_input, temp_learnings_dir):
        """Test exiting with 'exit' command"""
        # Create test file with 2 questions
        unknowns_file = temp_learnings_dir / "execution_learning" / "current_state" / "known_execution_unknowns.md"
        unknowns_file.write_text("""# Known Execution Unknowns

## Question 1
What are the API rate limits?

**Answer**: _[Fill in]_

---

## Question 2
What are the memory limits?

**Answer**: _[Fill in]_

---
""")

        # Mock user input: exit on first question
        mock_input.side_effect = ['exit']

        asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution", "test_user")
        answered, exited = asker.ask_unknowns()

        assert answered == 0  # No questions answered
        assert exited == True  # Exit was requested

    @patch('builtins.input')
    def test_ask_unknowns_valid_answers(self, mock_input, temp_learnings_dir):
        """Test answering questions with valid responses"""
        # Create test file with 2 questions
        unknowns_file = temp_learnings_dir / "execution_learning" / "current_state" / "known_execution_unknowns.md"
        unknowns_file.write_text("""# Known Execution Unknowns

## Question 1
What are the API rate limits?

**Answer**: _[Fill in]_

---

## Question 2
What are the memory limits?

**Answer**: _[Fill in]_

---
""")

        # Mock user input: Q1: answer, Q2: skip
        mock_input.side_effect = [
            'No rate limits, file-based processing',  # Answer to Q1
            's'  # Skip Q2
        ]

        asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution", "Kevin")
        answered, exited = asker.ask_unknowns()

        assert answered == 1  # One question answered
        assert exited == False

        # Verify known known was persisted
        knowns_file = temp_learnings_dir / "execution_learning" / "known_knowns.jsonl"
        assert knowns_file.exists()


class TestCategorySeparation:
    """Test that execution and domain categories remain separate"""

    @patch('builtins.input')
    def test_execution_and_domain_separate_files(self, mock_input, temp_learnings_dir):
        """Test execution and domain use separate files"""
        # Create both unknowns files
        exec_file = temp_learnings_dir / "execution_learning" / "current_state" / "known_execution_unknowns.md"
        exec_file.write_text("""# Execution Unknowns

## Question 1
Execution question?

**Answer**: _[Fill in]_

---
""")

        domain_file = temp_learnings_dir / "loop_learning" / "current_state" / "known_loop_unknowns.md"
        domain_file.write_text("""# Loop Unknowns

## Question 1
Domain question?

**Answer**: _[Fill in]_

---
""")

        # Mock input for both: answer for each (attribution passed to constructor)
        mock_input.side_effect = [
            'Execution answer',  # Execution Q1
            'Domain answer'  # Domain Q1
        ]

        # Create both askers with same attribution
        exec_asker = InteractiveUnknownsAsker(temp_learnings_dir, "execution", "test_user")
        domain_asker = InteractiveUnknownsAsker(temp_learnings_dir, "domain", "test_user")

        # Answer both
        exec_answered, exec_exited = exec_asker.ask_unknowns()
        domain_answered, domain_exited = domain_asker.ask_unknowns()

        assert exec_answered == 1
        assert exec_exited == False
        assert domain_answered == 1
        assert domain_exited == False

        # Verify separate JSONL files
        exec_knowns = temp_learnings_dir / "execution_learning" / "known_knowns.jsonl"
        domain_knowns = temp_learnings_dir / "loop_learning" / "known_knowns.jsonl"

        assert exec_knowns.exists()
        assert domain_knowns.exists()
        assert exec_knowns != domain_knowns  # Different files
