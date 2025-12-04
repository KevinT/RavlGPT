"""
Known Knowns Manager - Persistent storage for answered questions

Manages the transition from "known unknowns" (unanswered questions) to
"known knowns" (answered questions with attribution and metadata).

Key features:
- JSONL storage for append-only history
- Question deduplication by stable ID
- Source tracking (human vs loop vs system)
- Separation by category (domain vs execution)
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple


class KnownKnownsManager:
    """
    Manages persistent storage of answered questions (known knowns).

    Once a question transitions from "unknown" to "known", it's saved here
    with full metadata about who answered it and when.
    """

    def __init__(self, learnings_dir: Path, category: str):
        """
        Initialize Known Knowns Manager.

        Args:
            learnings_dir: Base learnings directory (e.g., ravl_loops/test/learnings)
            category: "domain" or "execution"
        """
        self.learnings_dir = Path(learnings_dir)
        self.category = category

        # Determine JSONL file path based on category
        if category == "domain":
            self.jsonl_file = self.learnings_dir / "loop_learning" / "known_knowns.jsonl"
        elif category == "execution":
            self.jsonl_file = self.learnings_dir / "execution_learning" / "known_knowns.jsonl"
        else:
            raise ValueError(f"Invalid category: {category}. Must be 'domain' or 'execution'")

        # Ensure parent directory exists
        self.jsonl_file.parent.mkdir(parents=True, exist_ok=True)

    def load_known_knowns(self) -> List[Dict]:
        """
        Load all known knowns from JSONL file.

        Returns:
            List of known known dicts, sorted by answered_at timestamp
        """
        if not self.jsonl_file.exists():
            return []

        knowns = []
        with open(self.jsonl_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        knowns.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        # Log and skip malformed lines
                        print(f"Warning: Skipping malformed line in {self.jsonl_file}: {e}")
                        continue

        # Sort by timestamp (oldest first)
        knowns.sort(key=lambda k: k.get('answered_at', ''))
        return knowns

    def get_all_knowns(self) -> Dict[str, str]:
        """
        Get all known knowns as simple dict of question -> answer.

        Returns:
            Dict mapping question text to answer text (strips metadata)
        """
        knowns = self.load_known_knowns()
        return {k['question']: k['answer'] for k in knowns}

    def get_all_knowns_with_metadata(self) -> Dict[str, Dict]:
        """
        Get all known knowns with full metadata.

        Returns:
            Dict mapping question_id -> full metadata dict
        """
        knowns = self.load_known_knowns()
        return {k['question_id']: k for k in knowns}

    def has_question(self, question_id: str) -> bool:
        """
        Check if question has already been answered.

        Args:
            question_id: Unique hash ID for the question

        Returns:
            True if question already exists in known knowns
        """
        knowns_with_meta = self.get_all_knowns_with_metadata()
        return question_id in knowns_with_meta

    def add_known_known(
        self,
        question: str,
        answer: str,
        answered_by: str,
        run_number: Optional[int] = None
    ) -> None:
        """
        Add a newly answered question to known knowns.

        Appends to JSONL file with full metadata.

        Args:
            question: The question text
            answer: The answer provided
            answered_by: Who answered ("human", "loop:name", "Alice", etc.)
            run_number: Optional run/attempt number
        """
        # Generate stable question ID
        question_id = self._generate_question_id(question)

        # Check if already exists (update scenario)
        if self.has_question(question_id):
            # For now, we don't update - JSONL is append-only
            # Future enhancement: mark old answer as superseded
            print(f"Note: Question {question_id} already answered, keeping original")
            return

        # Create known known record
        known = {
            "question": question,
            "answer": answer,
            "answered_by": answered_by,
            "answered_at": datetime.now(timezone.utc).isoformat(),
            "run_number": run_number,
            "category": self.category,
            "question_id": question_id
        }

        # Append to JSONL file
        with open(self.jsonl_file, 'a') as f:
            f.write(json.dumps(known) + '\n')

    def _generate_question_id(self, question: str) -> str:
        """
        Generate stable unique ID for a question.

        Uses SHA256 hash of normalized question text.

        Args:
            question: Question text

        Returns:
            Hex string hash ID (first 16 chars)
        """
        # Normalize question text for consistent hashing
        normalized = question.lower().strip()
        normalized = ' '.join(normalized.split())  # Normalize whitespace

        # Generate hash
        hash_obj = hashlib.sha256(normalized.encode('utf-8'))
        return hash_obj.hexdigest()[:16]  # First 16 chars sufficient

    def get_known_by_question(self, question: str) -> Optional[Dict]:
        """
        Retrieve a known known by question text.

        Args:
            question: The question to look up

        Returns:
            Known known dict or None if not found
        """
        question_id = self._generate_question_id(question)
        knowns_with_meta = self.get_all_knowns_with_metadata()
        return knowns_with_meta.get(question_id)

    def count_knowns(self) -> int:
        """
        Count total number of known knowns.

        Returns:
            Count of answered questions
        """
        return len(self.load_known_knowns())

    def get_knowns_by_source(self, answered_by: str) -> List[Dict]:
        """
        Get all knowns answered by a specific source.

        Args:
            answered_by: Source filter (e.g., "human", "loop:analyzer", "Alice")

        Returns:
            List of known known dicts matching the source
        """
        knowns = self.load_known_knowns()
        return [k for k in knowns if k.get('answered_by') == answered_by]
