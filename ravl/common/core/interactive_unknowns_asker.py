#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Interactive Unknown Unknowns Asker

Prompts users interactively for answers to unknown unknowns when running
loops with --interactive flag. Supports both execution and loop (domain)
categories, maintaining RAVL's learning separation principle.

Key features:
- Category-aware (execution vs domain)
- Interactive prompting with skip options
- Attribution collection ("answered_by")
- Persistence via KnownKnownsManager
- Graceful handling of missing/empty files
"""

import re
from pathlib import Path
from typing import List

from ravl.common.core.learning.known_knowns_manager import KnownKnownsManager


class InteractiveUnknownsAsker:
    """
    Prompts user interactively for answers to unknown unknowns.

    Handles both execution unknowns (infrastructure) and loop unknowns (domain),
    maintaining strict separation between the two learning spaces.
    """

    def __init__(self, learning_path: Path, category: str, answered_by: str = "human"):
        """
        Initialize asker for specific category.

        Args:
            learning_path: Base learnings directory (e.g., ravl_loops/test/learnings)
            category: "execution" or "domain"
            answered_by: Attribution for all answers (default: "human")

        Raises:
            ValueError: If category is not "execution" or "domain"
        """
        self.learning_path = Path(learning_path)
        self.category = category
        self.answered_by = answered_by

        # Determine file paths and labels based on category
        if category == "execution":
            self.unknowns_file = (
                self.learning_path /
                "execution_learning" /
                "current_state" /
                "known_execution_unknowns.md"
            )
            self.category_label = "Execution Unknowns (Infrastructure)"
            self.emoji = "🔧"
        elif category == "domain":
            self.unknowns_file = (
                self.learning_path /
                "loop_learning" /
                "current_state" /
                "known_loop_unknowns.md"
            )
            self.category_label = "Loop Unknowns (Domain)"
            self.emoji = "📋"
        else:
            raise ValueError(
                f"Invalid category: {category}. Must be 'execution' or 'domain'"
            )

        # Initialize known knowns manager with category
        self.known_knowns_mgr = KnownKnownsManager(self.learning_path, category)

    def ask_unknowns(self) -> tuple[int, bool]:
        """
        Ask user for answers to unknown unknowns interactively.

        Returns:
            Tuple of (number of questions answered, exit_requested flag)
        """
        # Check if unknowns file exists
        if not self.unknowns_file.exists():
            return 0, False  # No unknowns to ask about

        # Parse questions from markdown file
        questions = self._parse_unknowns_file(self.unknowns_file)

        if not questions:
            return 0, False  # File exists but has no questions

        # Display header
        print("\n" + "=" * 80)
        print(f"{self.emoji} {self.category_label}")
        print("=" * 80)
        print(f"Found {len(questions)} questions.\n")

        answered_count = 0
        exit_requested = False

        # Prompt for each question
        for idx, question in enumerate(questions, 1):
            print(f"\n[Question {idx}/{len(questions)}]")
            print(f"❓ {question}\n")

            # Get answer
            answer = input("Your answer: ").strip()

            # Handle exit commands
            if answer.lower() in ['exit', 'quit', 'q']:
                print("\n🚪 Exiting interactive prompting...")
                exit_requested = True
                break

            # Handle skip-all
            if answer.lower() == 'skip-all':
                remaining = len(questions) - idx + 1
                print(f"\n⏭️  Skipping all {remaining} remaining questions.")
                break

            # Handle individual skip
            if answer.lower() == 's' or answer == '':
                print("⏭️  Skipped.")
                continue

            # Valid answer - persist it
            self.known_knowns_mgr.add_known_known(
                question=question,
                answer=answer,
                answered_by=self.answered_by
            )
            answered_count += 1
            print("✅ Answer recorded.")

        # Display summary (unless user exited)
        if not exit_requested:
            print("\n" + "=" * 80)
            print(f"📝 Answered {answered_count} out of {len(questions)} questions.")
            print("=" * 80 + "\n")

        return answered_count, exit_requested

    def _parse_unknowns_file(self, file_path: Path) -> List[str]:
        """
        Parse unknowns markdown file to extract questions.

        Format:
            ## Question 1
            What are the specific API rate limits...

            **Answer**: _[Fill in your answer here]_

            **Answered by**: _[Your name]_

            ---

            ## Question 2
            ...

        Args:
            file_path: Path to unknowns markdown file

        Returns:
            List of question strings (extracted from question sections)
        """
        try:
            content = file_path.read_text()
        except Exception:
            # If file can't be read, return empty list
            return []

        questions = []

        # Split by ## Question headers
        sections = re.split(r'^## Question \d+$', content, flags=re.MULTILINE)

        # Skip first section (file header) and process rest
        for section in sections[1:]:
            # Extract question text (everything before **Answer**)
            match = re.search(r'^(.*?)\*\*Answer\*\*:', section, re.DOTALL)
            if match:
                question = match.group(1).strip()
                # Remove trailing newlines and normalize whitespace
                question = ' '.join(question.split())
                if question:
                    questions.append(question)

        return questions
