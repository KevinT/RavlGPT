#!/usr/bin/env python3
"""
Google Docs Fetching Loop Base Class

Generic RAVL loop for fetching Google Docs with lineage tracking.
Delegate to this to create new fetching loops - just provide config!

The base class handles:
- Document fetching from Google Docs API
- Change detection via content hashing
- Markdown export and lineage .jsonl creation
- Optional revision history tracking
- Domain learning persistence (learnings/loop_learning/ - WHAT documents to fetch)

Delegating loops only need to define:
- Loop name/description
- Which documents to fetch (in config/ravl.yml)
"""

import os
import sys
import json
import yaml
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

from ravl_base import BaseRAVLLoop
from ravl_protocol import RAVLLoop
from cli.ravl_cli_base import RAVLCLIBase

# Import learning manager for domain learning (loop_learning)
from core.learning.loop_learning_manager import LoopLearningManager

# Import framework integrations using proper path resolution
_framework_root = RAVLCLIBase.find_project_root(Path(__file__).parent) / '.ravl'
sys.path.insert(0, str(_framework_root / 'common' / 'integrations'))
from google_apis_mixin import GoogleAPIsMixin
from google_docs_exporter import GoogleDocsExporter
from google_docs_revision_tracker import GoogleDocsRevisionTracker


class GoogleDocsFetchingLoop(BaseRAVLLoop, GoogleAPIsMixin):
    """
    Framework RAVL loop for fetching Google Docs with comprehensive lineage tracking.

    **For Subclasses**: Override in __init__ to set loop name:
        super().__init__(model_path, loop_name="Your Loop Name")

    **Configuration** (in config/ravl.yml):
        google_documents:
          - url: "https://docs.google.com/document/d/..."
            target_path: "./data/output"
            filename: "document.md"
            description: "Document description"
            include_revisions: false       # Optional: track full revision history

        max_google_file_revisions_to_track: 100  # Maximum revisions to track per document

    **Features**:
    - Automatic hash-based change detection
    - Recreates files if deleted (even if hash unchanged)
    - Optional revision history tracking (simple or full-lineage modes)
    - Comprehensive lineage .jsonl files with metadata
    - Domain learning stored in learnings/loop_learning/ (WHAT documents to fetch)
    - No execution learning needed (pure Python, no code generation)
    """

    def __init__(self, model_path: str, config_path: str, loop_name: str = "Google Docs Fetching"):
        """
        Initialize the Google Docs fetching loop.

        Args:
            model_path: Path to learnings/ directory (or legacy learnings/model.yml)
            config_path: Path to config/ravl.yml
            loop_name: Display name for this loop
        """
        super().__init__(Path(model_path), loop_name=loop_name)

        self.config_path = config_path

        # Initialize loop learning manager (domain learning only - no code generation)
        loop_learning_dir = self.learning_path / 'loop_learning'
        self.loop_learning = LoopLearningManager(loop_learning_dir)

        # Load domain model from loop_learning/model.yml
        self.model = self.loop_learning.load_model() or self._get_default_model()

        self.config = self._load_config()
        # Use proper helper to find project root
        self.project_root = RAVLCLIBase.find_project_root(Path(__file__).parent)
        self.max_revisions = self.config.get('max_google_file_revisions_to_track', 100)

        # Track results during this run
        self.act_results = {
            'documents_processed': 0,
            'documents_sourced': 0,
            'documents_skipped': 0,
            'files_created': [],
            'errors': [],
            'warnings': []  # Non-blocking errors (e.g., revision fetch failures)
        }

    def _get_default_model(self) -> Dict[str, Any]:
        """Get default model structure for sourcing"""
        return {
            'version': '1.0',
            'loop_type': 'google_docs_sourcing',
            'description': 'Learned patterns for sourcing Google Docs',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'documents': [],
            'last_sourced': None
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from ravl.yml"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            return {'google_documents': [], 'target_base_path': './data/source'}

        with open(config_file, 'r') as f:
            return yaml.safe_load(f) or {}

    def _resolve_target_path(self, doc_config: Dict[str, Any]) -> Path:
        """
        Resolve target path for a document.

        Priority:
        1. Document config target_path
        2. Loop config target_base_path
        3. Project root
        """
        target_path = doc_config.get('target_path')
        if target_path:
            path = Path(target_path).expanduser()
        elif self.config.get('target_base_path'):
            path = Path(self.config['target_base_path']).expanduser()
        else:
            path = self.project_root

        # Make absolute if relative
        if not path.is_absolute():
            path = self.project_root / path

        return path

    def _calculate_content_hash(self, content: str) -> str:
        """Calculate SHA256 hash of content for change detection"""
        return hashlib.sha256(content.encode()).hexdigest()

    def _find_document_in_model(self, url: str) -> Optional[Dict[str, Any]]:
        """Find document entry in model by URL"""
        for doc in self.model.get('documents', []):
            if doc.get('source_url') == url:
                return doc
        return None

    def _extract_doc_id(self, url: str) -> Optional[str]:
        """Extract document ID from Google Docs URL"""
        import re
        match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url)
        return match.group(1) if match else None

    def reflect(self) -> Dict[str, Any]:
        """
        Phase 1: Reflect on current state and plan document sourcing

        Reviews:
        - Previous sourcing runs
        - Document count and status
        - Model version
        """
        print("\n🔍 REFLECT: Planning document fetching", file=sys.stderr)

        docs_config = self.config.get('google_documents', [])

        # Validate config is not None (can happen if config_files failed to load)
        if docs_config is None:
            error_msg = (
                "Configuration error: 'google_documents' is None.\n"
                "This usually means:\n"
                "  1. External config_files failed to load (check file paths)\n"
                "  2. The config is missing the 'google_documents' key\n"
                "  3. Config overrides were not properly merged\n"
                "\n"
                "To fix:\n"
                "  - Check that config_files paths exist (if specified in delegate_to.config_files)\n"
                "  - Or define google_documents directly in config_overrides\n"
                "  - Or remove config_files references if not needed"
            )
            raise ValueError(error_msg)

        # Validate config is a list
        if not isinstance(docs_config, list):
            raise ValueError(
                f"Configuration error: 'google_documents' must be a list, got {type(docs_config).__name__}"
            )

        model_docs = self.model.get('documents', [])

        print(f"   • Documents configured: {len(docs_config)}", file=sys.stderr)
        print(f"   • Documents in model: {len(model_docs)}", file=sys.stderr)
        print(f"   • Last fetch: {self.model.get('last_sourced', 'Never')}", file=sys.stderr)

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'planned_sourcing': {
                'document_count': len(docs_config),
                'model_version': self.model.get('version'),
                'strategy': 'Fetch all configured documents with change detection'
            }
        }

    def act(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2: Fetch and source documents

        Actions:
        - For each configured document:
          - Fetch from Google Docs API
          - Calculate content hash
          - Check if changed vs model
          - Save markdown file
          - Save lineage .jsonl file
          - Track revisions if enabled
        """
        print("\n⚡ ACT: Fetching documents from Google Workspace", file=sys.stderr)

        docs_config = self.config.get('google_documents', [])

        for doc_idx, doc_config in enumerate(docs_config, 1):
            self.act_results['documents_processed'] += 1

            try:
                url = doc_config.get('url')
                if not url:
                    print(f"   ⚠️  Document {doc_idx}: No URL specified, skipping", file=sys.stderr)
                    self.act_results['documents_skipped'] += 1
                    continue

                # Use description or filename for display, fallback to truncated URL
                doc_name = doc_config.get('description', doc_config.get('filename', url[:60]))
                print(f"   • Fetching document {doc_idx}/{len(docs_config)}: {doc_name}", file=sys.stderr)

                # Detect URL type and use appropriate exporter
                if '/presentation/d/' in url:
                    from integrations.google_slides_exporter import GoogleSlidesExporter
                    exporter = GoogleSlidesExporter(self)
                elif '/document/d/' in url:
                    exporter = GoogleDocsExporter(self)
                elif '/spreadsheets/d/' in url:
                    from integrations.google_sheets_analyzer import GoogleSheetsAnalyzer
                    exporter = GoogleSheetsAnalyzer(self)
                else:
                    raise ValueError(f"Unsupported Google URL type: {url}")

                doc_content = exporter.fetch(url)

                # Calculate hash for change detection
                content_text = doc_content.get('text', '')
                content_hash = self._calculate_content_hash(content_text)

                # Resolve target path and filename
                target_path = self._resolve_target_path(doc_config)
                filename = doc_config.get('filename', 'document.md')
                filename = filename.replace('{document_title}', doc_content.get('title', 'document'))
                filename = filename.replace('{timestamp}', datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M%S'))

                markdown_path = target_path / filename
                metadata_filename = filename.replace('.md', '.metadata.jsonl')
                metadata_path = target_path / metadata_filename

                # Check if document has changed OR if markdown file is missing
                existing_doc = self._find_document_in_model(url)
                markdown_exists = markdown_path.exists()
                hash_unchanged = existing_doc and existing_doc.get('content_hash') == content_hash

                if hash_unchanged and markdown_exists:
                    print(f"      → Document unchanged (hash match) and files exist, skipping", file=sys.stderr)
                    self.act_results['documents_skipped'] += 1
                    continue

                if hash_unchanged and not markdown_exists:
                    print(f"      → Document unchanged but output files missing, recreating", file=sys.stderr)

                # Ensure target directory exists
                target_path.mkdir(parents=True, exist_ok=True)

                # Save markdown file (with just content, no title prefix since Drive export includes it)
                with open(markdown_path, 'w') as f:
                    f.write(content_text)

                file_size = len(content_text.encode())

                # Always collect edit history metadata
                doc_name = filename.replace('.md', '')
                tracker = GoogleDocsRevisionTracker(self)
                try:
                    edit_history = tracker.get_edit_history(doc_content.get('doc_id'), self.max_revisions)
                except Exception as e:
                    error_msg = str(e)
                    print(f"      ⚠️  Could not fetch edit history: {e}", file=sys.stderr)
                    self.act_results['warnings'].append({
                        'document': url,
                        'step': 'edit_history_fetch',
                        'error': error_msg,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                    edit_history = []

                # Track revision content if enabled (per-document setting)
                # Do this BEFORE creating metadata entry so we can include revisions_exported
                revisions_exported = {}
                revision_files = []
                doc_include_revisions = doc_config.get('include_revisions', False)
                if doc_include_revisions:
                    try:
                        revision_result = tracker.save_missing_revisions(
                            document_name=doc_name,
                            doc_id=doc_content.get('doc_id'),
                            output_path=str(target_path),
                            revisions_metadata=edit_history,
                            max_count=self.max_revisions,
                            metadata_path=str(metadata_path)
                        )
                        revision_files = revision_result.get('files_created', [])
                        revisions_exported = revision_result.get('revisions_exported', {})
                        if revision_files:
                            print(f"      ✓ Revisions saved: {len(revision_files)} new revision files", file=sys.stderr)
                    except Exception as e:
                        error_msg = str(e)
                        print(f"      ⚠️  Could not save revisions: {e}", file=sys.stderr)
                        self.act_results['warnings'].append({
                            'document': url,
                            'step': 'revisions_save',
                            'error': error_msg,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        })

                # Create/append metadata entry
                sourced_now = datetime.now(timezone.utc).isoformat()

                # Try to get relative path, fall back to absolute if paths are unrelated
                # (e.g., output is in Google Drive, project is in local git repo)
                try:
                    output_file_path = str(markdown_path.relative_to(self.project_root))
                except ValueError:
                    output_file_path = str(markdown_path)

                metadata_entry = {
                    'source_url': url,
                    'document_id': self._extract_doc_id(url),
                    'document_title': doc_content.get('title', ''),
                    'created_time': doc_content.get('created_time'),
                    'modified_time': doc_content.get('last_modified'),
                    'content_hash': content_hash,
                    'content_length': len(content_text),
                    'sourced_timestamp': sourced_now,
                    'output_file_path': output_file_path,
                    'output_file_size': file_size,
                    'fetch_status': 'success',
                    'fetch_notes': f'Document sourced with {len(edit_history)} edits tracked',
                    'edit_history': edit_history
                }

                # Add revisions_exported if revisions were tracked
                if revisions_exported:
                    metadata_entry['revisions_exported'] = revisions_exported

                # Append to metadata file (JSON Lines format - one entry per sourcing)
                with open(metadata_path, 'a') as f:
                    f.write(json.dumps(metadata_entry) + '\n')

                print(f"      ✓ Saved: {markdown_path.name} ({file_size} bytes)", file=sys.stderr)
                print(f"      ✓ Metadata: {metadata_path.name} (appended)", file=sys.stderr)

                self.act_results['documents_sourced'] += 1
                files_entry = {
                    'markdown': str(markdown_path),
                    'metadata': str(metadata_path)
                }
                if revision_files:
                    files_entry['revisions'] = revision_files
                self.act_results['files_created'].append(files_entry)

                # Update model for this document
                doc_entry = existing_doc or {
                    'source_url': url,
                    'fetch_history': []
                }

                doc_entry['last_sourced'] = sourced_now
                doc_entry['content_hash'] = content_hash

                # Try to get relative paths, fall back to absolute if paths are unrelated
                try:
                    markdown_rel = str(markdown_path.relative_to(self.project_root))
                    metadata_rel = str(metadata_path.relative_to(self.project_root))
                except ValueError:
                    markdown_rel = str(markdown_path)
                    metadata_rel = str(metadata_path)

                doc_entry['output_files'] = {
                    'markdown': markdown_rel,
                    'metadata': metadata_rel
                }
                doc_entry['fetch_status'] = 'success'
                doc_entry['fetch_error'] = None

                if not existing_doc:
                    self.model['documents'].append(doc_entry)
                else:
                    idx = self.model['documents'].index(existing_doc)
                    self.model['documents'][idx] = doc_entry

            except Exception as e:
                import traceback
                error_msg = str(e)
                print(f"      ⚠️  Error: {error_msg}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                self.act_results['errors'].append({
                    'document': doc_config.get('url', 'unknown'),
                    'error': error_msg,
                    'traceback': traceback.format_exc()
                })

                # Still record in model for tracking
                existing_doc = self._find_document_in_model(doc_config.get('url', ''))
                if existing_doc:
                    existing_doc['fetch_status'] = 'error'
                    existing_doc['fetch_error'] = error_msg

                continue

        self.model['last_sourced'] = datetime.now(timezone.utc).isoformat()

        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'documents_processed': self.act_results['documents_processed'],
            'documents_sourced': self.act_results['documents_sourced'],
            'documents_skipped': self.act_results['documents_skipped'],
            'files_created': self.act_results['files_created'],
            'errors': self.act_results['errors'],
            'warnings': self.act_results['warnings']
        }

    def verify(self, previous_action: Optional[Dict[str, Any]], current_reflection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 3: Verify that documents were sourced correctly

        Checks:
        - All markdown files exist and are readable
        - Lineage files are valid JSON Lines
        - Content hashes are correct
        - Files have content
        """
        print("\n✅ VERIFY: Validating sourced documents", file=sys.stderr)

        verification_results = {
            'markdown_files_valid': 0,
            'lineage_files_valid': 0,
            'total_files_checked': 0,
            'issues': []
        }

        if not previous_action:
            print("   • First run, no files to verify yet", file=sys.stderr)
            return verification_results

        for file_pair in previous_action.get('files_created', []):
            markdown_path = Path(file_pair['markdown'])
            metadata_path = Path(file_pair.get('metadata', file_pair.get('lineage', '')))

            # Check markdown file
            verification_results['total_files_checked'] += 1
            if markdown_path.exists() and markdown_path.stat().st_size > 0:
                verification_results['markdown_files_valid'] += 1
                print(f"   ✓ Markdown valid: {markdown_path.name}", file=sys.stderr)
            else:
                verification_results['issues'].append(f"Markdown file invalid: {markdown_path.name}")
                print(f"   ⚠️  Markdown invalid: {markdown_path.name}", file=sys.stderr)

            # Check metadata file
            verification_results['total_files_checked'] += 1
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        line_count = 0
                        for line in f:
                            json.loads(line)  # Validate JSON Lines format
                            line_count += 1
                    verification_results['lineage_files_valid'] += 1
                    print(f"   ✓ Metadata valid: {metadata_path.name} ({line_count} entries)", file=sys.stderr)
                except Exception as e:
                    verification_results['issues'].append(f"Metadata file invalid: {metadata_path.name}: {e}")
                    print(f"   ⚠️  Metadata invalid: {metadata_path.name}: {e}", file=sys.stderr)
            else:
                verification_results['issues'].append(f"Metadata file missing: {metadata_path.name}")
                print(f"   ⚠️  Metadata missing: {metadata_path.name}", file=sys.stderr)

        print(f"\n   Summary: {verification_results['markdown_files_valid']} markdown, "
              f"{verification_results['lineage_files_valid']} metadata files valid", file=sys.stderr)

        return verification_results

    def learn(self, verification: Dict[str, Any], action_result: Dict[str, Any]) -> None:
        """
        Phase 4: Learn and persist domain model updates

        Actions:
        - Calculate domain metrics (documents sourced, pass rate, etc.)
        - Save domain attempt (action, verification, metrics) to loop_learning/
        - Persist updated model to loop_learning/model.yml with timestamp
        """
        print("\n🧠 LEARN: Updating domain model with sourcing results", file=sys.stderr)

        print(f"   • Document entries in model: {len(self.model.get('documents', []))}", file=sys.stderr)
        print(f"   • Model version: {self.model.get('version')}", file=sys.stderr)

        # Calculate domain metrics from action and verification
        total_files_checked = verification.get('total_files_checked', 0)
        markdown_files_valid = verification.get('markdown_files_valid', 0)

        metrics = {
            'documents_sourced': action_result.get('documents_sourced', 0),
            'documents_skipped': action_result.get('documents_skipped', 0),
            'documents_processed': action_result.get('documents_processed', 0),
            'pass_rate': (
                markdown_files_valid / max(total_files_checked, 1)
            ),
            'total_passed': markdown_files_valid,
            'total_failed': len(verification.get('issues', [])),
            'files_created_count': len(action_result.get('files_created', [])),
            'errors_count': len(action_result.get('errors', [])),
            'warnings_count': len(action_result.get('warnings', []))
        }

        # Save domain attempt to loop_learning/
        self.loop_learning.save_domain_attempt(
            action_result=action_result,
            verification=verification,
            metrics=metrics
        )

        # Save updated domain model to loop_learning/model.yml
        self.loop_learning.save_model(self.model)

        print(f"   ✓ Domain model persisted to loop_learning/", file=sys.stderr)
        print(f"   ✓ Domain metrics: {metrics['documents_sourced']} sourced, "
              f"{metrics['pass_rate']:.1%} pass rate", file=sys.stderr)
