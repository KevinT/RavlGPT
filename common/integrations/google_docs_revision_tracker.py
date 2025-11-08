#!/usr/bin/env python3
"""
Google Docs Revision Tracker Workflow

Handles tracking and exporting revision history from Google Docs with two modes:
- Simple mode: All revisions metadata in single .jsonl file
- Full-lineage mode: Each revision as separate .md file with .jsonl index

Inherits from GoogleAPIsMixin to access Google Docs and Drive services.
"""

import os
import re
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class GoogleDocsRevisionTracker:
    """
    Tracks revision history of Google Docs with configurable export modes.

    Usage:
        tracker = GoogleDocsRevisionTracker(loop)  # loop must inherit GoogleAPIsMixin
        revisions = tracker.fetch_revisions(doc_id, max_count=100)
        tracker.organize_revisions(
            document_name="my-doc",
            doc_id="abc123",
            output_path="/data/output/",
            max_count=100,
            full_lineage=False
        )

    Modes:
        simple (default): All revision metadata in single .jsonl file
        full-lineage: Separate .md file per revision + .jsonl index
    """

    def __init__(self, loop_with_mixin):
        """
        Initialize with a loop that has GoogleAPIsMixin.

        Args:
            loop_with_mixin: A RAVL loop instance that inherits GoogleAPIsMixin
        """
        self.loop = loop_with_mixin
        self.drive_service = None

    def _init_drive_service(self):
        """Initialize Google Drive service for revision access."""
        if not self.drive_service:
            # Reuse credentials from existing Google Docs service
            if not self.loop.google_docs_service:
                self.loop.init_google_services()

            # Get credentials from the docs service
            from googleapiclient.discovery import build
            credentials = self.loop.google_docs_service._http.request.__self__

            # Build Drive service with same credentials
            self.drive_service = build('drive', 'v3', http=self.loop.google_docs_service._http)

    def get_edit_history(self, doc_id: str, max_count: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch edit history metadata without exporting revision content.

        Used for metadata collection. Returns author, timestamp, and change info.

        Args:
            doc_id: Google Docs document ID
            max_count: Maximum number of revisions to fetch

        Returns:
            List of edit history entries with:
            - timestamp: ISO timestamp of edit
            - author: Display name of editor
            - email: Email address of editor
            - revision_id: Internal Google revision ID

        Raises:
            Exception: If API request fails
        """
        revisions = self.fetch_revisions(doc_id, max_count)

        # Extract just the metadata we need for audit trail
        edit_history = []
        for rev in revisions:
            edit_history.append({
                'timestamp': rev.get('modifiedTime'),
                'author': rev.get('lastModifyingUser', {}).get('displayName', 'Unknown'),
                'email': rev.get('lastModifyingUser', {}).get('emailAddress', 'unknown@example.com'),
                'revision_id': rev.get('id')
            })

        return edit_history

    def fetch_revisions(self, doc_id: str, max_count: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch revision history from Google Drive API.

        Args:
            doc_id: Google Docs document ID
            max_count: Maximum number of revisions to fetch

        Returns:
            List of revision objects with metadata:
            - id: Revision ID
            - mimeType: MIME type
            - modifiedTime: ISO timestamp
            - lastModifyingUser: User info (displayName, emailAddress)
            - size: File size in bytes
            - keepForever: Whether revision is kept indefinitely

        Raises:
            Exception: If API request fails
        """
        if not self.drive_service:
            self._init_drive_service()

        try:
            results = self.drive_service.revisions().list(
                fileId=doc_id,
                pageSize=max_count,
                fields='revisions(id, mimeType, modifiedTime, lastModifyingUser, size, keepForever)'
            ).execute()

            revisions = results.get('revisions', [])
            print(f"  • Fetched {len(revisions)} revisions for document {doc_id}", file=sys.stderr)
            return revisions

        except Exception as e:
            print(f"  ⚠️  Error fetching revisions: {e}", file=sys.stderr)
            raise

    def export_revision(self, doc_id: str, revision_id: str, max_retries: int = 3) -> str:
        """
        Export a specific revision as markdown with retry logic for rate limiting.

        Args:
            doc_id: Google Docs document ID
            revision_id: Revision ID to export
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            Markdown content of the revision

        Raises:
            Exception: If API request fails after all retries
        """
        import requests
        import time

        if not self.drive_service:
            self._init_drive_service()

        last_error = None
        for attempt in range(max_retries):
            try:
                # Get revision metadata including exportLinks
                revision = self.drive_service.revisions().get(
                    fileId=doc_id,
                    revisionId=revision_id,
                    fields='exportLinks'
                ).execute()

                # Get markdown export link
                export_links = revision.get('exportLinks', {})
                markdown_url = export_links.get('text/markdown')

                if not markdown_url:
                    raise ValueError(f"No markdown export link available for revision {revision_id}")

                # Download the markdown content using the credentials
                response = self.drive_service._http.request(markdown_url)

                # Check if response is HTML (error page) vs actual content
                content = response[1]
                if isinstance(content, bytes):
                    content_str = content.decode('utf-8')
                else:
                    content_str = content

                # Detect error responses (HTML error pages)
                if content_str.startswith('<!DOCTYPE') or content_str.startswith('<html'):
                    # This is an error page, likely rate limiting
                    if 'Too Many Requests' in content_str or '429' in content_str:
                        error_msg = "Rate limited (429 Too Many Requests)"
                    elif 'unavailable' in content_str.lower():
                        error_msg = "Service unavailable"
                    else:
                        error_msg = f"HTML error response (not markdown content)"

                    if attempt < max_retries - 1:
                        # Exponential backoff: 1s, 8s, 16s
                        wait_time = 4 ** attempt
                        print(f"  ⚠️  {error_msg}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                        time.sleep(wait_time)
                        continue
                    else:
                        raise ValueError(f"Failed after {max_retries} retries: {error_msg}")

                # Success - return the markdown content
                return content_str

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Exponential backoff for general errors too
                    wait_time = 4 ** attempt
                    print(f"  ⚠️  Error exporting revision {revision_id}: {e}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                    time.sleep(wait_time)
                else:
                    print(f"  ⚠️  Error exporting revision {revision_id}: {e}", file=sys.stderr)

        # All retries exhausted
        raise last_error if last_error else Exception(f"Failed to export revision {revision_id}")

    def _get_existing_revisions(self, revisions_dir: Path) -> Dict[str, str]:
        """
        Get map of existing revision files in the revisions folder.

        Returns dict mapping revision_id -> filename for quick lookup.

        Args:
            revisions_dir: Path to the revisions folder

        Returns:
            Dict mapping revision_id to filename
        """
        existing = {}
        if revisions_dir.exists():
            for md_file in revisions_dir.glob('*.md'):
                # filename format: {timestamp}-{seq}.md
                # We need to track the revision_id separately
                # For now, just count existing files
                pass
        return existing

    def _load_saved_revision_ids_from_metadata(self, metadata_path: Path) -> set:
        """
        Load all Google revision IDs that have been previously saved from metadata.jsonl.

        Reads all entries in the metadata.jsonl file and extracts revision_ids from
        their edit_history to determine which revisions are already exported.

        Args:
            metadata_path: Path to the .metadata.jsonl file

        Returns:
            Set of Google revision_id strings that have been previously saved
        """
        saved_revision_ids = set()

        if not metadata_path.exists():
            return saved_revision_ids

        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        # Extract revision_ids from edit_history
                        edit_history = entry.get('edit_history', [])
                        for edit in edit_history:
                            revision_id = edit.get('revision_id')
                            if revision_id:
                                saved_revision_ids.add(revision_id)

                        # Also check for revisions_exported from previous saves
                        # This handles the case where revisions were already exported
                        revisions_exported = entry.get('revisions_exported', {})
                        revision_mappings = revisions_exported.get('revision_mappings', [])
                        for mapping in revision_mappings:
                            revision_id = mapping.get('google_revision_id')
                            if revision_id:
                                saved_revision_ids.add(revision_id)
                    except json.JSONDecodeError:
                        print(f"  ⚠️  Could not parse metadata line: {line[:100]}", file=sys.stderr)
                        continue

        except Exception as e:
            print(f"  ⚠️  Could not read metadata file: {e}", file=sys.stderr)

        return saved_revision_ids

    def _get_next_sequence_number(self, metadata_path: Path) -> int:
        """
        Get the next sequence number to use for revision files.

        Reads revision_mappings from metadata.jsonl (source of truth) and returns
        the highest sequence number + 1. If metadata doesn't exist, starts from 1.

        Args:
            metadata_path: Path to the .metadata.jsonl file

        Returns:
            Next sequence number to use (1-based)
        """
        if not metadata_path.exists():
            return 1

        max_seq = 0
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        # Extract sequence numbers from revisions_exported
                        revisions_exported = entry.get('revisions_exported', {})
                        revision_mappings = revisions_exported.get('revision_mappings', [])
                        for mapping in revision_mappings:
                            seq_str = mapping.get('sequence')
                            if seq_str:
                                try:
                                    seq_num = int(seq_str)
                                    max_seq = max(max_seq, seq_num)
                                except ValueError:
                                    pass
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

        return max_seq + 1

    def save_missing_revisions(
        self,
        document_name: str,
        doc_id: str,
        output_path: str,
        revisions_metadata: List[Dict[str, Any]],
        max_count: int = 100,
        metadata_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save only missing revisions (ones not already in the folder).

        Uses metadata.jsonl as the source of truth for tracking which Google
        revision_ids have already been exported. On restart, reads the metadata
        file to rebuild the saved set and continue sequence numbering from where
        it left off.

        Args:
            document_name: Document name for folder naming
            doc_id: Google Docs document ID
            output_path: Path where to save revisions
            revisions_metadata: List of revision metadata from get_edit_history
            max_count: Maximum revisions to save
            metadata_path: Path to the .metadata.jsonl file for state persistence

        Returns:
            Dict with:
            - files_created: List of newly created file paths
            - revisions_exported: Dict with first/last sequence and revision mappings (for metadata)
        """
        output_path = Path(output_path)
        revisions_dir = output_path / f"{document_name}.revisions"
        revisions_dir.mkdir(parents=True, exist_ok=True)

        # Load saved revision IDs from metadata.jsonl (source of truth)
        metadata_file = Path(metadata_path) if metadata_path else output_path / f"{document_name}.metadata.jsonl"
        saved_revision_ids = self._load_saved_revision_ids_from_metadata(metadata_file)
        print(f"  • Previously saved revisions from metadata: {len(saved_revision_ids)}", file=sys.stderr)

        # Get next sequence number from metadata.jsonl (source of truth)
        # If metadata doesn't exist, starts from 1 (ensures consistent numbering on fresh start)
        next_seq = self._get_next_sequence_number(metadata_file)

        files_created = []
        revision_mappings = []
        first_sequence = None
        import time

        for i, rev_metadata in enumerate(revisions_metadata):
            # Handle both 'revision_id' (from get_edit_history) and 'id' (from organize_revisions) keys
            revision_id = rev_metadata.get('revision_id') or rev_metadata.get('id')

            # Skip if this revision_id has already been saved
            if revision_id in saved_revision_ids:
                print(f"  ✓ Revision {revision_id} already saved", file=sys.stderr)
                continue

            # Format: {timestamp}-{seq}.md
            timestamp = rev_metadata.get('timestamp', '')
            # Parse ISO timestamp and extract date/time
            if timestamp:
                # Convert ISO 8601 to simple format: 2025-10-28-143200
                dt = datetime.fromisoformat(timestamp.replace('+00:00', ''))
                timestamp_str = dt.strftime('%Y-%m-%d-%H%M%S')
            else:
                timestamp_str = 'unknown'

            seq_str = f"{next_seq:03d}"
            rev_file = revisions_dir / f"{timestamp_str}-{seq_str}.md"

            try:
                content = self.export_revision(doc_id, revision_id)
                rev_file.write_text(content, encoding='utf-8')
                files_created.append(str(rev_file))

                # Track this revision mapping for metadata
                file_size = len(content.encode())
                content_hash = hashlib.sha256(content.encode()).hexdigest()

                mapping = {
                    'sequence': seq_str,
                    'google_revision_id': revision_id,
                    'exported_filename': rev_file.name,
                    'file_size_bytes': file_size,
                    'content_hash': f"sha256:{content_hash}"
                }
                revision_mappings.append(mapping)

                if first_sequence is None:
                    first_sequence = seq_str
                last_sequence = seq_str

                saved_revision_ids.add(revision_id)
                next_seq += 1
                print(f"  ✓ Saved revision {seq_str}: {rev_file.name}", file=sys.stderr)

                # Add delay between requests to avoid rate limiting (except for last revision)
                if i < len(revisions_metadata) - 1:
                    time.sleep(0.5)  # 500ms delay between revisions
            except Exception as e:
                print(f"  ⚠️  Failed to save revision {seq_str}: {e}", file=sys.stderr)

        # Build the revisions_exported structure for metadata
        revisions_exported = {}
        if revision_mappings:
            revisions_exported = {
                'first_sequence': first_sequence,
                'last_sequence': last_sequence,
                'revision_mappings': revision_mappings
            }
            print(f"  • Exported {len(revision_mappings)} new revisions (seq {first_sequence}-{last_sequence})", file=sys.stderr)
        else:
            print(f"  • No new revisions to export", file=sys.stderr)

        return {
            'files_created': files_created,
            'revisions_exported': revisions_exported
        }

    def organize_revisions(
        self,
        document_name: str,
        doc_id: str,
        output_path: str,
        max_count: int = 100,
        full_lineage: bool = False
    ) -> Dict[str, Any]:
        """
        Fetch and organize revisions based on mode.

        Args:
            document_name: Document name for file naming (e.g., "fde-operating-strategy")
            doc_id: Google Docs document ID
            output_path: Path where to save files
            max_count: Maximum revisions to track
            full_lineage: If True, create separate .md files per revision.
                         If False, store revisions metadata in single .jsonl

        Returns:
            Dict with organization result:
            - mode: "simple" or "full_lineage"
            - revision_count: Number of revisions tracked
            - files_created: List of created files/folders
            - revisions_metadata: List of revision metadata

        Raises:
            Exception: If fetch or export fails
        """
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        # Fetch revisions
        revisions = self.fetch_revisions(doc_id, max_count)

        if not revisions:
            print(f"  ⚠️  No revisions found for document", file=sys.stderr)
            return {
                'mode': 'simple' if not full_lineage else 'full_lineage',
                'revision_count': 0,
                'files_created': [],
                'revisions_metadata': []
            }

        # Extract metadata for all revisions
        revisions_metadata = []
        for rev in revisions:
            revisions_metadata.append({
                'id': rev.get('id'),
                'author': rev.get('lastModifyingUser', {}).get('displayName', 'Unknown'),
                'email': rev.get('lastModifyingUser', {}).get('emailAddress', 'unknown@example.com'),
                'timestamp': rev.get('modifiedTime'),
                'size': rev.get('size', 0),
                'keep_forever': rev.get('keepForever', False)
            })

        files_created = []

        if full_lineage:
            # Full-lineage mode: separate .md files per revision
            revisions_dir = output_path / f"{document_name}.revisions"
            revisions_dir.mkdir(parents=True, exist_ok=True)
            files_created.append(str(revisions_dir))

            # Export each revision to separate file
            for i, rev_metadata in enumerate(revisions_metadata, 1):
                rev_number = f"{i:03d}"
                rev_file = revisions_dir / f"{document_name}-rev-{rev_number}.md"

                try:
                    content = self.export_revision(doc_id, rev_metadata['id'])
                    rev_file.write_text(content, encoding='utf-8')
                    files_created.append(str(rev_file))
                    print(f"  ✓ Exported revision {rev_number} to {rev_file.name}", file=sys.stderr)
                except Exception as e:
                    print(f"  ⚠️  Failed to export revision {rev_number}: {e}", file=sys.stderr)

            # Create .jsonl index file
            index_file = output_path / f"{document_name}.revisions.jsonl"
            index_content = {
                'document_name': document_name,
                'doc_id': doc_id,
                'mode': 'full_lineage',
                'revision_count': len(revisions_metadata),
                'tracked_at': datetime.utcnow().isoformat() + '+00:00',
                'revisions_folder': f"{document_name}.revisions",
                'revisions': [
                    {
                        'number': f"{i:03d}",
                        'id': rev['id'],
                        'author': rev['author'],
                        'timestamp': rev['timestamp'],
                        'file': f"{document_name}-rev-{i:03d}.md"
                    }
                    for i, rev in enumerate(revisions_metadata, 1)
                ]
            }
            index_file.write_text(json.dumps(index_content) + '\n', encoding='utf-8')
            files_created.append(str(index_file))
            print(f"  ✓ Created revision index: {index_file.name}", file=sys.stderr)

        else:
            # Simple mode: all metadata in single .jsonl
            lineage_file = output_path / f"{document_name}.jsonl"
            lineage_content = {
                'document_name': document_name,
                'doc_id': doc_id,
                'mode': 'simple',
                'revision_count': len(revisions_metadata),
                'tracked_at': datetime.utcnow().isoformat() + '+00:00',
                'revisions': revisions_metadata
            }
            lineage_file.write_text(json.dumps(lineage_content) + '\n', encoding='utf-8')
            files_created.append(str(lineage_file))
            print(f"  ✓ Created revision tracking: {lineage_file.name}", file=sys.stderr)

        return {
            'mode': 'simple' if not full_lineage else 'full_lineage',
            'revision_count': len(revisions_metadata),
            'files_created': files_created,
            'revisions_metadata': revisions_metadata
        }
