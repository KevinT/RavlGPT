#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Markdown RAVL Loop Executor

Generic executor for RAVL loops defined in markdown format.
"""

import os
import sys
import json
import re
import tempfile
import subprocess
import time
import hashlib
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

# Add common module to path
_script_dir = Path(__file__).parent
_common_dir = _script_dir.parent.parent
sys.path.insert(0, str(_common_dir))
sys.path.insert(0, str(_common_dir / 'utils'))
sys.path.insert(0, str(_common_dir / 'llm'))
sys.path.insert(0, str(_common_dir / 'core' / 'learning'))
sys.path.insert(0, str(_common_dir / 'core' / 'verification'))
sys.path.insert(0, str(_common_dir / 'core' / 'error_handling'))
sys.path.insert(0, str(_common_dir / 'execution' / 'code'))
sys.path.insert(0, str(_common_dir / 'integrations'))

from common.config.config_loader import get_max_tokens
from llm_providers import LLMProviderFactory, LLMProvider
from credential_validator import CredentialValidator
from dsl_inference_engine import DSLInferenceEngine
from schema_adapters import enhance_llm_guidance_with_schema_adaptation
from markdown_parser import MarkdownParser
from code_cache_manager import CodeCacheManager
from code_generator import CodeGenerator
from loop_context_builder import LoopContextBuilder
from child_loop_executor import ChildLoopExecutor

# Import utilities
from file_utils import load_json_file, save_json_file, append_to_jsonl, load_yaml_file
from logging_utils import (
    log_message, log_verification_error, log_phase_banner,
    truncate_output, EMOJI_SUCCESS, EMOJI_ERROR, EMOJI_CHECK, EMOJI_CROSS, EMOJI_BULLET,
    log_execution
)
from constants import (
    DEFAULT_EXECUTION_TIMEOUT, CODE_EXECUTION_TIMEOUT,
    MAX_FILE_CONTENT_LENGTH, PREVIEW_OUTPUT_LENGTH,
    CONTEXT_DOCUMENTATION_CACHE_TTL, LEARNINGS_FILES
)
from venv_manager import VenvManager
from requirements_generator import RequirementsGenerator

# Lazy import to avoid circular dependencies
DataIngressExecutor = None


class SimpleCodeExecutor:
    """
    Simple code executor for general-purpose code generation (non-data-ingestion loops)

    Unlike DataIngressExecutor which expects JSON output, this executor:
    - Runs code without parsing output
    - Checks for execution errors (non-zero exit code)
    - Success = code ran without errors
    - Suitable for file I/O, data transforms, and other general operations

    Features:
    - Automatic virtual environment detection/creation
    - Automatic requirements.txt generation from imports
    - Automatic dependency installation
    - Runs code with venv Python executable
    """

    def __init__(self, loop_dir: Path, project_root: Optional[Path] = None):
        """
        Initialize the simple executor

        Args:
            loop_dir: Path to the loop directory
            project_root: Path to project root (for venv/learning path resolution)
        """
        self.loop_dir = loop_dir
        self.project_root = project_root or self._find_project_root()

    def _find_project_root(self) -> Path:
        """Find project root by looking for .git directory"""
        current = self.loop_dir.resolve()
        while current.parent != current:
            if (current / '.git').exists():
                return current
            current = current.parent
        return self.loop_dir.parent

    def execute_code(self, code: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Execute generated Python code with venv support

        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds

        Returns:
            Dict with keys: success (bool), error (str), execution_time (float),
                           stdout (str), stderr (str), code_hash (str)
        """
        # Clean markdown code fences if present
        code_clean = self._clean_markdown_fences(code)

        try:
            # Resolve venv path using RAVLRunner resolution logic
            from ravl_runner import RAVLRunner

            config = self._load_config()
            venv_path = RAVLRunner.resolve_venv_path(
                loop_dir=self.loop_dir,
                loop_config=config,
                project_root=self.project_root
            )

            # Validate existing venv or create new one
            venv_manager = VenvManager(venv_path)

            # Check if existing venv has correct Python version
            is_valid, issue = venv_manager.validate_venv()
            if not is_valid and venv_manager.exists():
                # Venv exists but has wrong Python version - recreate it
                log_execution(f"Venv needs recreation: {issue}", status='info')
                delete_success, delete_error = venv_manager.delete()
                if not delete_success:
                    return {
                        'success': False,
                        'error': f'Failed to delete incompatible venv: {delete_error}',
                        'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                    }
                log_execution("Deleted incompatible venv, will recreate with correct Python", status='info')

            # Create venv if needed (with correct Python version)
            success, error = venv_manager.detect_or_create()
            if not success:
                return {
                    'success': False,
                    'error': f'Failed to create venv: {error}',
                    'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                }

            # Generate requirements.txt from code imports
            requirements_path = self.loop_dir / 'generated_requirements.txt'
            RequirementsGenerator.save_requirements(code_clean, requirements_path)

            # Install requirements into venv
            success, error = venv_manager.install_requirements(requirements_path, quiet=True)
            if not success:
                return {
                    'success': False,
                    'error': f'Failed to install requirements: {error}',
                    'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                }

            # Write code to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                temp_file = Path(f.name)
                f.write(code_clean)

            try:
                start_time = time.time()

                # Get environment with venv activated
                env = venv_manager.get_environment_vars()
                env['PYTHONUNBUFFERED'] = '1'

                # Provide loop directories to generated code
                # Resolve learnings directory using same logic as main executor
                from ravl_runner import RAVLRunner
                learnings_dir = RAVLRunner.resolve_learning_path(
                    loop_dir=self.loop_dir,
                    loop_config=config,
                    cli_learning_path=None,
                    project_root=self.project_root
                )
                env['RAVL_LEARNINGS_DIR'] = str(learnings_dir)
                env['RAVL_LOOP_DIR'] = str(self.loop_dir)

                # Load .env file from project root and add to environment
                project_root = self.project_root
                env_vars = RAVLRunner.load_env_file(project_root)
                env.update(env_vars)

                # Execute code in subprocess with venv Python using Popen for real-time output
                import threading

                process = subprocess.Popen(
                    [venv_manager.get_python_executable(), str(temp_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    bufsize=1  # Line buffered
                )

                # Capture output while displaying in real-time
                stdout_lines = []
                stderr_lines = []

                def read_stream(stream, output_list, display_stream):
                    """Read from stream, append to list, and display in real-time"""
                    for line in iter(stream.readline, ''):
                        if line:
                            output_list.append(line)
                            print(line, end='', file=display_stream, flush=True)
                    stream.close()

                # Start threads to read stdout and stderr concurrently
                stdout_thread = threading.Thread(
                    target=read_stream,
                    args=(process.stdout, stdout_lines, sys.stdout)
                )
                stderr_thread = threading.Thread(
                    target=read_stream,
                    args=(process.stderr, stderr_lines, sys.stderr)
                )

                stdout_thread.daemon = True
                stderr_thread.daemon = True
                stdout_thread.start()
                stderr_thread.start()

                # Wait for process to complete with timeout
                try:
                    returncode = process.wait(timeout=timeout)

                    # Wait for output threads to finish reading
                    stdout_thread.join(timeout=2)
                    stderr_thread.join(timeout=2)

                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout_thread.join(timeout=2)
                    stderr_thread.join(timeout=2)

                    error_msg = f'Code execution timeout after {timeout}s'
                    return {
                        'success': False,
                        'error': error_msg,
                        'execution_time': timeout,
                        'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                    }

                execution_time = time.time() - start_time

                # Join output into strings
                stdout_text = ''.join(stdout_lines)
                stderr_text = ''.join(stderr_lines)

                # Success = code ran without errors (exit code 0)
                if returncode == 0:
                    return {
                        'success': True,
                        'stdout': stdout_text,
                        'stderr': stderr_text,
                        'execution_time': execution_time,
                        'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                    }
                else:
                    error_msg = stderr_text or stdout_text or f'Exit code: {returncode}'
                    return {
                        'success': False,
                        'error': error_msg,
                        'stdout': stdout_text,
                        'stderr': stderr_text,
                        'execution_time': execution_time,
                        'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                    }

            except subprocess.TimeoutExpired:
                # Fallback timeout handler (shouldn't reach here with new code)
                error_msg = f'Code execution timeout after {timeout}s'
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': timeout,
                    'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                }

            finally:
                # Clean up temp file
                try:
                    temp_file.unlink()
                except Exception:
                    pass

        except Exception as e:
            error_msg = f'Execution error: {str(e)}'
            return {
                'success': False,
                'error': error_msg,
                'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
            }

    def _load_config(self) -> Dict[str, Any]:
        """Load loop configuration from config/ravl.yml if it exists"""
        config_file = self.loop_dir / 'config' / 'ravl.yml'
        if not config_file.exists():
            return {}

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _clean_markdown_fences(self, code: str) -> str:
        """
        Remove code block delimiters if present.

        Handles both custom delimiters (===RAVL_CODE_START/END===) and
        markdown code blocks (```python / ```).
        """
        # First try custom delimiters (preferred)
        if '===RAVL_CODE_START===' in code and '===RAVL_CODE_END===' in code:
            start_marker = '===RAVL_CODE_START==='
            end_marker = '===RAVL_CODE_END==='
            start_idx = code.find(start_marker) + len(start_marker)
            end_idx = code.find(end_marker)
            return code[start_idx:end_idx].strip()

        # Fallback: Remove markdown code block fences
        # Remove ```python or ```bash or similar
        code = re.sub(r'^```[\w]*\n', '', code)
        # Remove trailing ```
        code = re.sub(r'\n```$', '', code)
        return code.strip()


class MarkdownRAVLExecutor:
    """
    Executes RAVL loops defined in markdown format

    The markdown should contain:
        # Act
        <instructions for what to do>

        # Verify
        <criteria for verification>

    Reflect and Learn phases are handled automatically by scanning learnings.
    """

    def __init__(
        self,
        markdown_text: str,
        loop_dir: Path,
        learnings_dir: Path,
        context_vars: Optional[Dict[str, str]] = None,
        llm_provider: Optional[LLMProvider] = None,
        force_code_regeneration: bool = False
    ):
        """
        Initialize executor

        Args:
            markdown_text: Pre-substituted markdown content (template vars already replaced)
            loop_dir: Path to this loop's directory (for discovering parent/child/sibling)
            learnings_dir: Path to this loop's learnings directory
            context_vars: Context variables (e.g., {"current role": "CTO"})
            llm_provider: LLM provider to use (defaults to Anthropic)
            force_code_regeneration: Force fresh code generation, bypassing cache for this run
        """
        self.markdown_text = markdown_text
        self.loop_dir = loop_dir
        self.learnings_dir = learnings_dir
        self.context_vars = context_vars or {}
        self.force_code_regeneration = force_code_regeneration
        self.used_interpretation = False  # Track if LLM interpretation was used

        # Find project root for venv/dependency resolution
        self.project_root = self._find_project_root()

        # Ensure learnings directory exists
        self.learnings_dir.mkdir(parents=True, exist_ok=True)

        # Setup LLM provider
        self.llm = llm_provider or LLMProviderFactory.create_provider("anthropic")

        # Load loop configuration (for data ingress detection)
        self.config = self._load_config()

        # Initialize markdown parser (needed for _parse_markdown)
        self.markdown_parser = MarkdownParser(self.loop_dir, self.learnings_dir, llm_provider=self.llm)

        # Don't parse phases yet - wait until after reflect() to get fresh domain_guidance
        self._phases_cache = None

        # Initialize learning managers (SEPARATED: execution vs domain)
        from core.learning import create_learning_managers
        self.execution_learning_mgr, self.loop_learning_mgr = create_learning_managers(
            self.learnings_dir,
            config=self.config
        )

        # Initialize DSL inference engine (uses execution_learning)
        execution_learning_dir = self.learnings_dir / 'execution_learning'
        self.dsl_engine = DSLInferenceEngine(self.loop_dir, execution_learning_dir)

        # Initialize code cache manager (uses execution_learning)
        self.cache_manager = CodeCacheManager(execution_learning_dir, loop_dir=self.loop_dir, project_root=self.project_root)

        # Initialize code generator (uses execution_learning)
        self.code_gen = CodeGenerator(
            self.loop_dir,
            execution_learning_dir,
            llm_provider=self.llm,
            config=self.config
        )

        # Initialize loop context builder
        self.context_builder = LoopContextBuilder(self.loop_dir, self.learnings_dir)

        # Initialize child loop executor
        self.child_executor = ChildLoopExecutor(self.loop_dir, self.learnings_dir)

        # Track last generated code for passing to LearningManager
        self._last_generated_code = None

        # Track last reflection for LEARN phase synthesis (also used for lazy phase parsing)
        self._last_reflection = None

        # Prompts directory
        self.prompts_dir = _script_dir / 'prompts'

    @property
    def phases(self) -> Dict[str, Any]:
        """
        Lazy-load phases - parses markdown AFTER reflection if available.
        This ensures enhancement uses fresh domain_guidance from REFLECT phase.
        """
        if self._phases_cache is None:
            # Parse with reflection context if available
            self._phases_cache = self.markdown_parser.parse_with_context(
                self.markdown_text,
                reflection=self._last_reflection
            )
        return self._phases_cache

    def _find_project_root(self) -> Path:
        """Find project root by looking for .git directory"""
        current = self.loop_dir.resolve()
        while current.parent != current:
            if (current / '.git').exists():
                return current
            current = current.parent
        return self.loop_dir.parent

    def _load_config(self) -> Dict[str, Any]:
        """Load loop configuration from config/ravl.yml if it exists"""
        config_file = self.loop_dir / 'config' / 'ravl.yml'
        if not config_file.exists():
            return {}

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _detect_exploratory_loop(self) -> bool:
        """
        Detect if this loop is exploratory/discovery-based

        Exploratory loops are designed to discover NEW things each run,
        which fundamentally conflicts with code caching.

        Detection patterns:
        - Keywords: "discover new", "explore next", "each run", "progressive",
                    "incremental", "adds to knowledge", "map unknown territory"
        - Config metadata: learning_type: discovery or exploration
        - Run-based progression instructions (e.g., "runs 1-3 do X, runs 4+ do Y")

        Returns:
            True if loop shows exploratory patterns
        """
        # Check config metadata
        metadata = self.config.get('metadata', {})
        learning_type = metadata.get('learning_type', '').lower()
        if learning_type in ['discovery', 'exploration', 'exploratory']:
            return True

        # Check for exploratory concepts in metadata
        concepts = metadata.get('concepts', [])
        exploratory_concepts = {'exploration', 'discovery', 'knowledge_building', 'progressive_learning'}
        if any(concept in exploratory_concepts for concept in concepts):
            return True

        # Check markdown text for exploratory keywords
        text_lower = self.markdown_text.lower()
        exploratory_keywords = [
            'discover new', 'explore next', 'each run', 'progressive',
            'incremental', 'adds to knowledge', 'map unknown territory',
            'explore different', 'learn something new', 'new discoveries',
            'expand knowledge', 'avoid repetition', 'build on previous'
        ]

        # Count keyword matches (need at least 2 for confidence)
        keyword_matches = sum(1 for keyword in exploratory_keywords if keyword in text_lower)
        if keyword_matches >= 2:
            return True

        # Check for run-based progression patterns (e.g., "runs 1-3", "runs 4+")
        run_progression_pattern = r'runs?\s+\d+[-+]'
        if re.search(run_progression_pattern, text_lower):
            return True

        return False

    def _should_skip_cache(self) -> Tuple[bool, str]:
        """
        Determine if code caching should be skipped

        Checks three sources (in order of priority):
        1. Config flag: code_generation.cache_code = false
        2. LEARN recommendation: regeneration_recommendation.json
        3. Domain verification: Recent verifications recommend regeneration

        Returns:
            Tuple of (skip_cache: bool, reason: str)
        """
        # Check 1: Force regeneration flag (CLI override)
        if self.force_code_regeneration:
            return (True, "Force regeneration flag enabled (--force-code-regeneration)")

        # Check 2: Config flag (explicit control)
        code_gen_config = self.config.get('code_generation', {})
        cache_enabled = code_gen_config.get('cache_code', True)

        if not cache_enabled:
            reason = code_gen_config.get('cache_reason', 'Config disables code caching')
            return (True, reason)

        # Check 3: LEARN's regeneration recommendation
        execution_learning_dir = self.learnings_dir / 'execution_learning'
        recommendation_file = execution_learning_dir / 'current_state' / 'regeneration_recommendation.json'

        if recommendation_file.exists():
            try:
                with open(recommendation_file, 'r', encoding='utf-8') as f:
                    recommendation = json.load(f)

                if recommendation.get('recommend_regeneration', False):
                    reason = recommendation.get('rationale', 'LEARN phase recommends code regeneration')
                    return (True, f"LEARN recommends regeneration: {reason[:80]}")
            except (IOError, json.JSONDecodeError):
                pass

        # Check 4: Domain verification pattern (fallback - same as cache_manager logic)
        loop_learning_dir = self.learnings_dir / 'loop_learning'
        if loop_learning_dir.exists():
            recent_attempts_dir = loop_learning_dir / 'recent_attempts'
            if recent_attempts_dir.exists():
                domain_attempt_dirs = sorted(
                    [d for d in recent_attempts_dir.iterdir() if d.is_dir() and d.name.startswith('attempt_')],
                    key=lambda d: int(d.name.split('_')[1])
                )

                # Check last 3 domain verifications
                regeneration_recommendations = 0
                for attempt_dir in domain_attempt_dirs[-3:]:
                    domain_verification_file = attempt_dir / 'domain_verification.json'
                    if domain_verification_file.exists():
                        try:
                            with open(domain_verification_file, 'r', encoding='utf-8') as f:
                                verification = json.load(f)

                            if verification.get('recommend_code_regeneration', False):
                                regeneration_recommendations += 1
                        except (IOError, json.JSONDecodeError):
                            continue

                # If 2+ recent verifications recommend regeneration
                if regeneration_recommendations >= 2:
                    return (True, f"Domain verification pattern: {regeneration_recommendations}/3 recent runs recommend regeneration")

        # Default: don't skip cache
        return (False, "")

    def _get_available_notion_credentials(self) -> List[str]:
        """Get list of available Notion credential environment variable names"""
        import os
        candidates = ['NOTION_API_TOKEN', 'NOTION_TOKEN', 'NOTION_API_KEY']
        available = [name for name in candidates if os.environ.get(name)]
        return available or candidates  # Return what's available, or suggest all options

    def _is_data_ingress_loop(self, skip_phase_check: bool = False) -> bool:
        """
        Detect if this loop is for data ingestion (API data fetching)

        Args:
            skip_phase_check: If True, only check config (used when we know phases are valid,
                            e.g., when using cached code). Avoids expensive phase parsing.

        Returns True if:
        - Config has apis section (multi-API configuration), OR
        - Config has api_endpoint field (legacy single-API), OR
        - Config has context7_docs_path field (legacy Context7 docs), AND
        - Has both ACT and VERIFY sections in markdown (unless skip_phase_check=True)
        """
        has_api_config = (
            'apis' in self.config or
            'api_endpoint' in self.config or
            'context7_docs_path' in self.config
        )

        if skip_phase_check:
            # When using cached code, we know phases were valid when code was generated
            # Just check config to avoid triggering enhancement LLM call
            return has_api_config

        has_act_verify = 'act' in self.phases and 'verify' in self.phases
        return has_api_config and has_act_verify

    def _should_attempt_code_generation(self) -> bool:
        """
        Intelligently decide if code generation should be attempted for this loop.

        Delegates to CodeGenerator for intelligent decision-making.
        """
        act_section = self.phases.get('act', '')
        verify_section = self.phases.get('verify', '')
        return self.code_gen.should_attempt_code_generation(
            act_section,
            verify_section,
            self._is_data_ingress_loop()
        )

    def _check_code_cache(self) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Check if verified code exists in cache and is still valid

        Delegates to CodeCacheManager for actual cache checking logic
        """
        result = self.cache_manager.check_cache()
        if result:
            log_execution("Using cached verified code")
        return result

    def _load_prompt(self, prompt_name: str, **variables) -> str:
        """Load a prompt template and substitute variables"""
        prompt_file = self.prompts_dir / f'{prompt_name}.md'

        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Substitute variables
        return prompt_template.format(**variables)

    def _parse_markdown(self) -> Dict[str, str]:
        """
        Parse markdown into phase sections

        Delegates to MarkdownParser for actual parsing logic
        """
        return self.markdown_parser.parse_markdown(self.markdown_text)

    def _discover_related_loops(self) -> Dict[str, List[Path]]:
        """
        Discover parent, child, and sibling loops

        Delegates to LoopContextBuilder for discovery logic
        """
        return self.context_builder.discover_related_loops()

    def _read_learnings_files(self, learnings_dir: Path) -> Dict[str, Any]:
        """
        Read all files from a learnings directory, including subdirectories

        Returns dict with 'files' (top-level files) and 'subdirs' (nested directories)
        """
        # Compute relative path, handling case where learnings_dir is outside loop hierarchy
        try:
            relative_dir = str(learnings_dir.relative_to(self.loop_dir.parent.parent.parent))
        except ValueError:
            # Learning path is outside the loop directory hierarchy (custom learning path)
            # Use just the loop name instead
            relative_dir = self.loop_dir.name

        learnings = {
            'directory': relative_dir,
            'files': {},
            'subdirs': {}
        }

        if not learnings_dir.exists():
            return learnings

        # Read all items in learnings directory
        for item_path in sorted(learnings_dir.iterdir()):
            if item_path.name.startswith('.'):
                continue

            # Handle subdirectories recursively
            if item_path.is_dir():
                subdir_data = {'files': {}}
                for file_path in sorted(item_path.iterdir()):
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        try:
                            # Try to read as YAML
                            if file_path.suffix in ['.yml', '.yaml']:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    subdir_data['files'][file_path.name] = yaml.safe_load(f)
                            # Try to read as JSON
                            elif file_path.suffix == '.json':
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    subdir_data['files'][file_path.name] = json.load(f)
                            # Read as text for JSONL, logs, or other formats
                            else:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # Truncate very large files (e.g., logs)
                                    content = truncate_output(content, MAX_FILE_CONTENT_LENGTH)
                                    subdir_data['files'][file_path.name] = content
                        except Exception as e:
                            subdir_data['files'][file_path.name] = f"<error reading file: {e}>"

                if subdir_data['files']:
                    learnings['subdirs'][item_path.name] = subdir_data

            # Handle top-level files
            elif item_path.is_file():
                try:
                    # Try to read as YAML
                    if item_path.suffix in ['.yml', '.yaml']:
                        with open(item_path, 'r', encoding='utf-8') as f:
                            learnings['files'][item_path.name] = yaml.safe_load(f)
                    # Try to read as JSON
                    elif item_path.suffix == '.json':
                        with open(item_path, 'r', encoding='utf-8') as f:
                            learnings['files'][item_path.name] = json.load(f)
                    # Read as text for JSONL or other formats
                    else:
                        with open(item_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Truncate very large files
                            content = truncate_output(content, MAX_FILE_CONTENT_LENGTH)
                            learnings['files'][item_path.name] = content
                except Exception as e:
                    learnings['files'][item_path.name] = f"<error reading file: {e}>"

        return learnings

    def _check_has_domain_learnings(self) -> bool:
        """
        Check if loop_learning/ has meaningful DOMAIN data.
        (Ignores execution_learning/ - that's framework plumbing)
        """
        loop_learning_dir = self.learnings_dir / 'loop_learning'
        if not loop_learning_dir.exists():
            return False

        # Check for domain artifacts in key subdirectories
        for subdir in ['history', 'current_state', 'recent_attempts']:
            subdir_path = loop_learning_dir / subdir
            if subdir_path.exists() and any(subdir_path.iterdir()):
                return True

        return False

    def reflect(self) -> Dict[str, Any]:
        """
        REFLECT phase: Automatic context gathering

        Scans all learnings from:
        - This loop's learnings/
        - Parent loop's learnings/ (if exists)
        - Child loops' learnings/ (if exist)
        - Sibling loops' learnings/ (if exist)
        """
        log_message("Reflecting...", status='info')

        reflection = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'context_vars': self.context_vars,
            'learnings': {}
        }

        # Check for domain learnings specifically (not execution artifacts)
        has_domain_learnings = self._check_has_domain_learnings()

        # Read this loop's learnings (both execution and domain)
        reflection['learnings']['this_loop'] = self._read_learnings_files(self.learnings_dir)

        # Report domain learning status to user
        if has_domain_learnings:
            log_execution("Found domain learnings from previous runs", status='info', indent=4)
        else:
            log_execution("No prior domain learnings (fresh start)", status='info', indent=4)
        
        # Synthesize domain guidance from this loop's learnings
        reflection['domain_guidance'] = self._synthesize_domain_context(
            reflection['learnings']['this_loop']
        )

        # Discover and read related loops
        log_execution("Discovering related loops...", status='debug', indent=4)
        related_loops = self._discover_related_loops()

        if related_loops['parent']:
            parent_learnings_dir = related_loops['parent'] / 'learnings'
            reflection['learnings']['parent_loop'] = self._read_learnings_files(parent_learnings_dir)
            log_execution(f"Found parent loop learnings: {related_loops['parent'].name}", status='info', indent=4)
            log_execution(f"  Parent learning path: {parent_learnings_dir}", status='debug', indent=6)

        if related_loops['children']:
            reflection['learnings']['child_loops'] = {}
            child_names = []
            for child_dir in related_loops['children']:
                child_name = child_dir.name
                child_names.append(child_name)
                child_learnings_dir = child_dir / 'learnings'
                reflection['learnings']['child_loops'][child_name] = self._read_learnings_files(child_learnings_dir)
                log_execution(f"  Child: {child_name} at {child_learnings_dir}", status='debug', indent=6)
            log_execution(f"Found {len(related_loops['children'])} child loop(s): {', '.join(child_names)}", status='info', indent=4)

        if related_loops['siblings']:
            reflection['learnings']['sibling_loops'] = {}
            sibling_names = []
            for sibling_dir in related_loops['siblings']:
                sibling_name = sibling_dir.name
                sibling_names.append(sibling_name)
                sibling_learnings_dir = sibling_dir / 'learnings'
                reflection['learnings']['sibling_loops'][sibling_name] = self._read_learnings_files(sibling_learnings_dir)
                log_execution(f"  Sibling: {sibling_name} at {sibling_learnings_dir}", status='debug', indent=6)
            log_execution(f"Found {len(related_loops['siblings'])} sibling loop(s): {', '.join(sibling_names)}", status='info', indent=4)
        else:
            # Check if this is a top-level parent (would explain no siblings)
            from core.learning.learning_access_helper import LearningAccessHelper
            helper = LearningAccessHelper(self.loop_dir, self.learnings_dir)
            if helper.is_top_level_parent():
                log_execution("This is a top-level parent (isolated from other top-level parents)", status='debug', indent=4)

        # Check if code caching should be skipped
        skip_cache, skip_reason = self._should_skip_cache()
        if skip_cache:
            reflection['skip_cache'] = True
            reflection['skip_cache_reason'] = skip_reason
            log_execution(f"Cache will be skipped: {skip_reason}", status='info', indent=4)

        # Store reflection for lazy phase parsing (enhancement will use fresh domain_guidance)
        self._last_reflection = reflection

        return reflection

    def _synthesize_domain_context(self, learnings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to synthesize domain learnings into actionable context for ACT

        Reads previous run insights, verification suggestions, and metrics to
        create focused guidance for the next ACT phase.

        Args:
            learnings: Raw learnings data from this loop (includes files and subdirs)

        Returns:
            Dict with synthesized domain guidance for ACT
        """
        # Extract loop_learning subdirectory data
        loop_learning_data = learnings.get('subdirs', {}).get('loop_learning', {})
        if not loop_learning_data:
            # No domain learning yet - return empty guidance
            return {
                'priority_focus': [],
                'successful_patterns': [],
                'failed_patterns': [],
                'new_strategies_to_try': [],
                'context_needs': [],
                'verification_notes': {}
            }

        log_execution("Synthesizing domain context for ACT...", status='working')

        # Extract recent run insights from execution_learning/recent_attempts/attempt_N/
        execution_learning_data = learnings.get('subdirs', {}).get('execution_learning', {})
        recent_attempts_data = execution_learning_data.get('subdirs', {}).get('recent_attempts', {})

        run_insights_files = []
        for attempt_name, attempt_data in recent_attempts_data.get('subdirs', {}).items():
            # Each attempt_N folder may contain run_insights_*.json files
            for fname in attempt_data.get('files', {}).keys():
                if fname.startswith('run_insights_'):
                    run_insights_files.append((fname, attempt_data['files'][fname]))

        recent_insights = []
        if run_insights_files:
            # Get most recent insights (sorted by timestamp in filename)
            recent_insight_file, insight_data = sorted(run_insights_files, key=lambda x: x[0])[-1]
            if isinstance(insight_data, dict):
                recent_insights = [insight_data.get('insights', {})]

        # Extract verification suggestions from recent attempts
        verification_suggestions = []
        recent_attempts = loop_learning_data.get('subdirs', {})
        for attempt_name in sorted(recent_attempts.keys(), reverse=True)[:3]:  # Last 3 attempts
            attempt_data = recent_attempts[attempt_name]
            verification_file = attempt_data.get('files', {}).get('domain_verification.json', {})
            if isinstance(verification_file, dict):
                suggestions = verification_file.get('suggestions', [])
                verification_suggestions.extend(suggestions)

        # Extract performance metrics
        metrics_files = [
            fname for fname in loop_learning_data.get('files', {}).keys()
            if fname.startswith('domain_metrics_') or fname == 'latest_metrics.yml'
        ]
        performance_metrics = {}
        if metrics_files:
            latest_metrics_file = sorted(metrics_files)[-1]
            performance_metrics = loop_learning_data['files'].get(latest_metrics_file, {})

        # Extract historical patterns from history subdirectory
        history_data = loop_learning_data.get('subdirs', {}).get('history', {})
        historical_patterns = {
            'failures': history_data.get('files', {}).get('domain_failures.jsonl', ''),
            'successes': history_data.get('files', {}).get('domain_successes.jsonl', ''),
            'evolution': history_data.get('files', {}).get('pattern_evolution.jsonl', '')
        }

        # Load and format prompt
        prompt = self._load_prompt(
            'synthesize_domain_learnings',
            run_insights=json.dumps(recent_insights, indent=2) if recent_insights else 'No previous run insights',
            verification_suggestions=json.dumps(verification_suggestions, indent=2) if verification_suggestions else 'No verification suggestions',
            performance_metrics=json.dumps(performance_metrics, indent=2) if performance_metrics else 'No performance metrics',
            historical_patterns=json.dumps(historical_patterns, indent=2) if historical_patterns else 'No historical patterns'
        )

        llm_response = self.llm.complete(prompt, max_tokens=get_max_tokens('domain_context_synthesis', 4096))

        # Parse JSON response
        try:
            domain_guidance = self._parse_json_response(llm_response)
        except Exception as e:
            log_message(f"Warning: Could not parse domain guidance: {e}", status='error')
            domain_guidance = {
                'priority_focus': [],
                'successful_patterns': [],
                'failed_patterns': [],
                'new_strategies_to_try': [],
                'context_needs': [],
                'verification_notes': {},
                'error': f'Failed to parse guidance: {e}'
            }

        log_execution("Domain context synthesized", status='success')
        return domain_guidance

    def act(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        """
        ACT phase: Execute instructions from markdown

        For data ingestion loops: infers DSL, checks cache, and generates code accordingly
        """
        log_message("Acting...", status='info')

        # Store reflection for LEARN phase synthesis
        self._last_reflection = reflection

        # Check cache FIRST, before any phase access (which triggers enhancement LLM call)
        # We check cache before even determining if this is a code generation loop,
        # because if there's cached code, we don't need to access phases at all
        skip_cache = reflection.get('skip_cache', False)

        if not skip_cache:
            cache_result = self._check_code_cache()
            if cache_result:
                # Cache hit - return immediately without accessing phases
                cached_code, cached_dsl = cache_result
                log_execution("Using cached verified code - executing...")

                timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
                action_result = {
                    'timestamp': reflection['timestamp'],
                    'context_vars': self.context_vars,
                    'output': cached_code,
                    'code_executed': False,
                    'execution_result': None,
                    'using_cached_code': True,
                    'cached_dsl': cached_dsl,
                }

                # Execute the cached code
                action_result = self._execute_generated_code(cached_code, action_result)

                # Save human-readable companion files for cached code
                if action_result.get('output'):
                    self._save_generated_code_artifacts(action_result['output'], timestamp)

                log_execution("Cached code executed", status='success')
                return action_result

        # Cache miss or cache skipped - proceed with phase parsing
        # (This triggers enhancement LLM call via lazy-loaded @property phases)
        act_instructions = self.phases.get('act', '')
        if not act_instructions:
            raise ValueError("Markdown must define an 'Act' section")

        verify_instructions = self.phases.get('verify', 'No verification criteria defined')

        # For loops that need code generation: use DSL-guided code generation
        if self._should_attempt_code_generation():
            return self._act_with_dsl_inference(
                act_instructions, verify_instructions, reflection
            )

        # Standard act phase for non-data-ingestion loops
        # Process run_child directives first
        act_instructions, child_results = self._process_run_child_directives(act_instructions)

        # Build context summary
        context_summary = self._build_context_summary(reflection)

        # Add child results to context if any were executed
        if child_results:
            context_summary += "\n\n## Child Loop Execution Results\n"
            for child_name, result in child_results.items():
                context_summary += f"\n### {child_name}\n"
                context_summary += f"```json\n{json.dumps(result, indent=2)}\n```\n"

        # Load and format prompt
        prompt = self._load_prompt(
            'act_phase',
            act_instructions=act_instructions,
            context_summary=context_summary,
            verify_instructions=verify_instructions
        )

        llm_response = self.llm.complete(prompt, max_tokens=get_max_tokens('act_phase_code_generation', 16384))

        # Build action result (saved by LearningManager, not here)
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')

        action_result = {
            'timestamp': reflection['timestamp'],
            'context_vars': self.context_vars,
            'output': llm_response,
            'code_executed': False,
            'execution_result': None
        }

        # For loops with code generation: execute the generated code
        if self._should_attempt_code_generation():
            log_execution("Code generation detected - executing generated code...")
            action_result = self._execute_generated_code(llm_response, action_result)

        # Save human-readable companion files for generated code
        if action_result.get('output'):
            self._save_generated_code_artifacts(action_result['output'], timestamp)

        log_execution("Action phase completed", status='success')

        # Check if verification criteria specifies additional file outputs
        additional_files = self._create_additional_outputs(
            llm_response,
            verify_instructions,
            timestamp
        )
        if additional_files:
            action_result['additional_output_files'] = additional_files

        return action_result

    def _act_with_dsl_inference(
        self,
        act_instructions: str,
        verify_instructions: str,
        reflection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ACT phase with DSL inference for code generation loops

        Delegates core logic to CodeGenerator while handling code generation,
        execution, and result persistence.

        Note: Cache checking is now done in act() before calling this method,
        so this method only runs when cache misses or is skipped.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')

        # Fetch Context7 docs if this is a data ingress loop
        context7_docs = None
        if self._is_data_ingress_loop():
            try:
                from context7_fetcher import fetch_context7_docs_for_loop
                context7_docs = fetch_context7_docs_for_loop(self.config, self.learnings_dir)
                if context7_docs:
                    log_execution(f"Fetched Context7 docs for {len(context7_docs)} API(s)", status='success')
            except Exception as e:
                log_execution(f"Failed to fetch Context7 docs: {e}", status='warning')
                context7_docs = None

        # Delegate DSL inference and code generation to CodeGenerator
        gen_result = self.code_gen.generate_with_dsl_inference(
            act_spec=act_instructions,
            verify_spec=verify_instructions,
            reflection=reflection,
            load_prompt_fn=self._load_prompt,
            build_context_fn=self._build_context_summary,
            available_credentials_fn=self._get_available_notion_credentials,
            context7_docs=context7_docs
        )

        action_result = {
            'timestamp': reflection['timestamp'],
            'context_vars': self.context_vars,
            'output': gen_result['generated_code'],
            'code_executed': False,
            'execution_result': None,
            'inferred_dsl': gen_result['inferred_dsl'],
        }

        # Execute the generated code
        if self._should_attempt_code_generation():
            log_execution("Generated code detected - executing...")
            action_result = self._execute_generated_code(gen_result['generated_code'], action_result)

        # Save human-readable companion files for generated code
        if action_result.get('output'):
            self._save_generated_code_artifacts(action_result['output'], timestamp)

        log_execution("Code generated and executed", status='success')

        # Check if verification criteria specifies additional file outputs
        additional_files = self._create_additional_outputs(
            gen_result['generated_code'],
            verify_instructions,
            timestamp
        )
        if additional_files:
            action_result['additional_output_files'] = additional_files

        return action_result

    def _execute_generated_code(self, generated_code: str, act_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute generated code using the appropriate executor

        For data ingestion loops: uses DataIngressExecutor (expects JSON output)
        For general loops: uses SimpleCodeExecutor (any output is fine)

        Args:
            generated_code: Generated code from LLM
            act_result: Current act result dict to update

        Returns:
            Updated act_result with execution results
        """
        try:
            # Choose appropriate executor based on loop type
            # If using cached code, skip phase check to avoid enhancement LLM call
            using_cache = act_result.get('using_cached_code', False)
            if self._is_data_ingress_loop(skip_phase_check=using_cache):
                # Data ingestion loops need JSON output
                global DataIngressExecutor
                if DataIngressExecutor is None:
                    from data_ingress_executor import DataIngressExecutor

                executor = DataIngressExecutor(self.loop_dir, self.llm)
                execution_result = executor.execute_code(generated_code, timeout=self.config.get('execution_timeout', 300))

                act_result['code_executed'] = True
                act_result['execution_result'] = execution_result
                act_result['credentials_used'] = execution_result.get('credentials_used', [])
                act_result['credential_validation_passed'] = execution_result.get('credential_validation_passed', False)

                if execution_result.get('success'):
                    log_execution("Code executed successfully - data fetched", status='success')
                    act_result['data_fetched'] = execution_result.get('data', {})
                else:
                    log_execution(f"Code execution failed: {execution_result.get('error', 'Unknown error')[:100]}", status='error')
                    act_result['execution_error'] = execution_result.get('error', 'Unknown error')
            else:
                # General loops use simple executor (file I/O, data transforms, etc.)
                executor = SimpleCodeExecutor(self.loop_dir, self.project_root)
                execution_result = executor.execute_code(generated_code, timeout=self.config.get('execution_timeout', 300))

                act_result['code_executed'] = True
                act_result['execution_result'] = execution_result

                if execution_result.get('success'):
                    log_execution("Code executed successfully", status='success')
                    if execution_result.get('stdout'):
                        log_execution(f"Output: {execution_result.get('stdout')[:200]}")
                else:
                    log_execution(f"Code execution failed: {execution_result.get('error', 'Unknown error')[:100]}", status='error')
                    act_result['execution_error'] = execution_result.get('error', 'Unknown error')

        except Exception as e:
            log_execution(f"Error executing code: {str(e)[:100]}", status='error')
            act_result['code_executed'] = False
            act_result['execution_error'] = str(e)

        return act_result

    def _save_generated_code_artifacts(self, code_content: str, timestamp: str) -> None:
        """
        Save generated code to current_state/generated_code.py

        Args:
            code_content: The generated code (may contain markdown code blocks)
            timestamp: Timestamp string (unused now, kept for compatibility)
        """
        # Extract Python code using custom delimiters (preferred) or fallback to markdown
        if '===RAVL_CODE_START===' in code_content and '===RAVL_CODE_END===' in code_content:
            # Use custom delimiters (safe from truncation)
            start_marker = '===RAVL_CODE_START==='
            end_marker = '===RAVL_CODE_END==='
            start_idx = code_content.find(start_marker) + len(start_marker)
            end_idx = code_content.find(end_marker)
            code_content = code_content[start_idx:end_idx].strip()
        elif '```python' in code_content:
            # Fallback: Extract from markdown code blocks (legacy support)
            # Split on ```python and take the part after it
            parts = code_content.split('```python')
            if len(parts) > 1:
                # Take the first code block and split on closing ```
                code_content = parts[1].split('```')[0].strip()
        elif '```' in code_content:
            # Generic code block without language specifier
            parts = code_content.split('```')
            if len(parts) > 2:
                code_content = parts[1].strip()

        # Save to current_state/ (always latest)
        current_state_dir = self.learnings_dir / 'current_state'
        current_state_dir.mkdir(parents=True, exist_ok=True)
        latest_file = current_state_dir / 'generated_code.py'
        with open(latest_file, 'w', encoding='utf-8') as f:
            f.write(code_content)

        # Store for passing to LearningManager
        self._last_generated_code = code_content

    def save_verified_code(self, code: str, dsl: Optional[Dict[str, Any]] = None) -> None:
        """
        Save verified code and DSL to cache when verification passes 100%

        Delegates to CodeCacheManager for actual cache saving logic

        Args:
            code: The generated Python code that passed verification
            dsl: The DSL used to generate this code (optional)
        """
        self.cache_manager.save_verified_code(code, dsl)

    def verify(
        self,
        action_result: Optional[Dict[str, Any]],
        current_reflection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        VERIFY phase: Check both execution and domain independently

        Returns:
            Dict with 'execution' and 'domain' keys containing separate verification results
        """
        log_message("Verifying...", status='info')

        # EXECUTION VERIFICATION: Did code run successfully?
        execution_verification = self._verify_execution(action_result)

        # DOMAIN VERIFICATION: Did it solve the problem?
        domain_verification = self._verify_domain(action_result, current_reflection)

        # DSL-based learning: cache successful code or save failure analysis
        if self._should_attempt_code_generation() and action_result:
            self._handle_dsl_verification_outcome(execution_verification, domain_verification, action_result)

        # Combined result
        return {
            'execution': execution_verification,
            'domain': domain_verification,
            'overall_passed': execution_verification['passed'] and domain_verification.get('overall_passed', True),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def _verify_execution(self, action_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify execution infrastructure: did code run successfully?

        This is SOLUTION LEARNING - checking if infrastructure works.
        """
        if not action_result:
            return {'passed': True, 'message': 'No execution to verify'}

        # Check if code was executed (for any loop type)
        if action_result.get('code_executed'):
            execution_result = action_result.get('execution_result', {})

            # Check credentials (only for data ingress loops that explicitly validate)
            # SimpleCodeExecutor doesn't set this field, so only check if present
            if 'credential_validation_passed' in execution_result:
                if not execution_result.get('credential_validation_passed', False):
                    error_msg = execution_result.get('error', 'Missing credentials')
                    log_verification_error('Credential validation failed', error_msg, max_length=150)
                    return {
                        'passed': False,
                        'error_type': 'credential_validation',
                        'error_message': error_msg,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }

            # Check execution success
            if not execution_result.get('success', False):
                error_msg = execution_result.get('error', 'Execution failed')
                # Extract meaningful error message (show last line if multiline)
                error_preview = error_msg[:200] if error_msg else 'Unknown error'
                if '\n' in error_preview:
                    error_preview = error_preview.split('\n')[-1]  # Show last line of error
                log_verification_error('Code execution failed', error_preview, max_length=200)
                return {
                    'passed': False,
                    'error_type': execution_result.get('error_type', 'execution_error'),
                    'error_message': error_msg,
                    'exit_code': execution_result.get('exit_code'),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }

            # Execution succeeded - check for warnings even on success
            stderr = execution_result.get('stderr', '')
            warnings = self._extract_execution_warnings(stderr)

            return {
                'passed': True,
                'execution_time': execution_result.get('execution_time'),
                'has_warnings': len(warnings) > 0,
                'warnings': warnings,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        # No code execution, consider it passed
        return {'passed': True, 'message': 'No code execution to verify'}

    def _extract_execution_warnings(self, stderr: str) -> List[Dict[str, Any]]:
        """
        Extract warnings from stderr (deprecations, future warnings, etc.)

        Args:
            stderr: The stderr output from code execution

        Returns:
            List of warning dictionaries with type, message, and api fields
        """
        warnings = []

        if not stderr:
            return warnings

        import re

        # Extract DeprecationWarnings
        deprecation_pattern = r'DeprecationWarning: (.+?) is deprecated'
        for match in re.finditer(deprecation_pattern, stderr):
            warnings.append({
                'type': 'deprecation',
                'message': match.group(0),
                'api': match.group(1).strip()
            })

        # Extract FutureWarnings
        future_pattern = r'FutureWarning: (.+?)(?:\n|$)'
        for match in re.finditer(future_pattern, stderr):
            warnings.append({
                'type': 'future',
                'message': match.group(0).strip()
            })

        return warnings

    def _verify_domain(
        self,
        action_result: Optional[Dict[str, Any]],
        current_reflection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify domain criteria: did it solve the problem?

        This is LOOP LEARNING - checking if domain requirements met.
        """
        verify_instructions = self.phases.get('verify', '')
        if not verify_instructions:
            log_execution("No verification criteria defined, skipping", status='info', indent=4)
            return {
                'overall_passed': True,
                'message': 'No verification criteria defined',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        if not action_result:
            log_execution("No action result to verify", status='info', indent=4)
            return {
                'overall_passed': None,
                'message': 'No action result available for verification',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        # Load and format prompt
        prompt = self._load_prompt(
            'verify_phase',
            verify_instructions=verify_instructions,
            action_result=json.dumps(action_result, indent=2),
            current_context=self._build_context_summary(current_reflection)
        )

        llm_response = self.llm.complete(prompt, max_tokens=get_max_tokens('verification', 4096))

        # Parse LLM response (handle markdown code blocks)
        json_text = llm_response.strip()

        # Remove markdown code block markers if present
        if json_text.startswith('```'):
            lines = json_text.split('\n')
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            json_text = '\n'.join(lines)

        try:
            verification = json.loads(json_text)
        except json.JSONDecodeError:
            # If still can't parse, try to extract suggestions from raw text
            suggestions = []
            if 'suggestions' in llm_response.lower():
                # Try to extract suggestions list from text
                import re
                suggestion_match = re.search(r'"suggestions"\s*:\s*\[(.*?)\]', llm_response, re.DOTALL)
                if suggestion_match:
                    suggestions_text = suggestion_match.group(1)
                    # Extract individual suggestions
                    for match in re.finditer(r'"([^"]+)"', suggestions_text):
                        suggestions.append(match.group(1))

            verification = {
                'overall_passed': False,
                'raw_evaluation': llm_response,
                'error': 'Could not parse verification as JSON',
                'suggestions': suggestions
            }

        verification['timestamp'] = datetime.now(timezone.utc).isoformat()

        log_execution("Verification complete", status='success')

        return verification

    def _handle_dsl_verification_outcome(
        self,
        execution_verification: Dict[str, Any],
        domain_verification: Dict[str, Any],
        action_result: Dict[str, Any]
    ) -> None:
        """
        Handle DSL learning: delegate to CodeGenerator

        CodeGenerator handles caching successful code and failure analysis.
        Only uses execution verification (not domain).
        """
        self.code_gen.handle_verification_outcome(
            verification=execution_verification,
            act_result=action_result,
            save_verified_code_fn=self.save_verified_code
        )

    def learn(
        self,
        verification: Dict[str, Any],
        action_result: Dict[str, Any]
    ) -> None:
        """
        LEARN phase: Automatic learning from verification outcomes

        Splits learning into execution (infrastructure) and domain (problem space).
        """
        log_message("Learning...", status='info')

        # EXECUTION LEARNING: How to make code work
        if 'execution' in verification:
            # Pass domain verification too, so execution learning can check regeneration recommendation
            domain_verification = verification.get('domain', {})
            self._learn_execution(verification['execution'], action_result, domain_verification)

        # DOMAIN LEARNING: What the loop learned about its problem (THE "L" IN RAVL)
        if 'domain' in verification:
            self._learn_domain(verification['domain'], action_result)

        # REGENERATION ANALYSIS: Should code be regenerated next run?
        # Only analyze if we're generating code (not for pure markdown loops)
        if self._should_attempt_code_generation() and self._last_reflection and 'execution' in verification and 'domain' in verification:
            log_execution("Analyzing code regeneration need...", status='working')
            regeneration_analysis = self._analyze_regeneration_need(
                reflection=self._last_reflection,
                action_result=action_result,
                execution_verification=verification['execution'],
                domain_verification=verification['domain']
            )

            # Save recommendation for next REFLECT to read
            execution_learning_dir = self.learnings_dir / 'execution_learning'
            current_state_dir = execution_learning_dir / 'current_state'
            current_state_dir.mkdir(parents=True, exist_ok=True)

            recommendation_file = current_state_dir / 'regeneration_recommendation.json'
            with open(recommendation_file, 'w', encoding='utf-8') as f:
                json.dump(regeneration_analysis, f, indent=2)

            if regeneration_analysis.get('recommend_regeneration', False):
                rationale = regeneration_analysis.get('rationale', 'See regeneration_recommendation.json')
                log_execution(f"💡 Regeneration recommended: {rationale[:80]}", status='info')
            else:
                log_execution("✓ Code is working well - will reuse if successful", status='success')

        log_execution("Learning saved to execution_learning/ and loop_learning/", status='success')

    def _learn_execution(
        self,
        execution_verification: Dict[str, Any],
        action_result: Dict[str, Any],
        domain_verification: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Learn from execution outcomes (code generation, infrastructure)

        This is SOLUTION LEARNING - improving code generation and execution.
        """
        # Save execution attempt and track attempt number
        self._current_attempt_number = self.execution_learning_mgr.save_execution_attempt(
            execution_result=execution_verification,
            generated_code=self._last_generated_code,
            dsl=action_result.get('inferred_dsl')
        )

        # Check if LLM recommends code regeneration based on domain verification
        if domain_verification:
            recommend_regeneration = domain_verification.get('recommend_code_regeneration', False)
            regeneration_rationale = domain_verification.get('regeneration_rationale', '')

            if recommend_regeneration:
                log_execution(f"🔄 Domain verification recommends code regeneration: {regeneration_rationale}", status='info')
                # Explicitly invalidate cache to force regeneration on next run
                if hasattr(self, 'cache_manager'):
                    self.cache_manager._clear_cache()
                    log_execution("✓ Cache cleared - code will be regenerated on next run", status='success')
                return

        # Cache code only if execution succeeded AND has no warnings
        # If code has warnings, force regeneration with warning guidance
        if (execution_verification.get('passed', False) and
            not execution_verification.get('has_warnings', False) and
            self._last_generated_code):
            self.save_verified_code(self._last_generated_code, action_result.get('inferred_dsl'))
        elif execution_verification.get('has_warnings', False):
            # Invalidate cache to force regeneration with warning fixes
            log_execution("Code has warnings - invalidating cache to improve quality", status='info')

    def _learn_domain(
        self,
        domain_verification: Dict[str, Any],
        action_result: Dict[str, Any]
    ) -> None:
        """
        Learn from domain outcomes (problem space learning)

        This is LOOP LEARNING - THE ACTUAL "L" IN RAVL.
        """
        # Calculate domain metrics
        metrics = self._calculate_domain_metrics(domain_verification)

        # Save domain attempt
        self.loop_learning_mgr.save_domain_attempt(
            action_result=action_result,
            verification=domain_verification,
            metrics=metrics
        )

        # Synthesize insights from full RAVL run (REFLECT → ACT → VERIFY)
        if self._last_reflection:
            run_insights = self._synthesize_run_insights(
                reflection=self._last_reflection,
                action_result=action_result,
                verification=domain_verification
            )
            # Persist insights for next REFLECT to use, associated with the execution attempt
            attempt_num = getattr(self, '_current_attempt_number', None)
            self.loop_learning_mgr.save_run_insights(run_insights, attempt_number=attempt_num)

        # Update performance metrics
        self._update_performance_metrics(domain_verification)

    def _calculate_domain_metrics(self, verification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate domain metrics from verification results
        """
        criteria_results = verification.get('criteria_results', [])

        passed_count = 0
        total_count = len(criteria_results)

        for criterion in criteria_results:
            if isinstance(criterion, dict) and criterion.get('passed', False):
                passed_count += 1

        failed_count = total_count - passed_count

        return {
            'total_criteria': total_count,
            'total_passed': passed_count,
            'total_failed': failed_count,
            'pass_rate': passed_count / total_count if total_count > 0 else 0.0,
            'overall_passed': verification.get('overall_passed', False)
        }

    def _analyze_regeneration_need(
        self,
        reflection: Dict[str, Any],
        action_result: Dict[str, Any],
        execution_verification: Dict[str, Any],
        domain_verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze whether code should be regenerated on next run

        Analyzes loop definition, current run outcomes, and execution history
        to determine if fresh code generation would improve results.

        Args:
            reflection: Output from REFLECT phase
            action_result: Output from ACT phase
            execution_verification: Execution verification results
            domain_verification: Domain verification results

        Returns:
            Dict with regeneration recommendation and rationale
        """
        # Get act and verify sections from loop definition
        act_instructions = self.phases.get('act', '')
        verify_instructions = self.phases.get('verify', '')

        # Build execution history summary
        execution_learning_dir = self.learnings_dir / 'execution_learning'
        recent_attempts_dir = execution_learning_dir / 'recent_attempts'

        history_parts = []
        if recent_attempts_dir.exists():
            attempt_dirs = sorted(
                [d for d in recent_attempts_dir.iterdir() if d.is_dir() and d.name.startswith('attempt_')],
                key=lambda d: int(d.name.split('_')[1])
            )

            history_parts.append(f"Total attempts: {len(attempt_dirs)}")

            # Summarize last 5 attempts
            for attempt_dir in attempt_dirs[-5:]:
                attempt_num = attempt_dir.name
                result_file = attempt_dir / 'execution_result.json'
                if result_file.exists():
                    try:
                        with open(result_file, 'r', encoding='utf-8') as f:
                            result = json.load(f)
                        passed = result.get('passed', False)
                        status = "✓ PASSED" if passed else "✗ FAILED"
                        history_parts.append(f"{attempt_num}: {status}")
                    except (IOError, json.JSONDecodeError):
                        history_parts.append(f"{attempt_num}: Unknown")

            # Check if using cached code
            current_state_dir = execution_learning_dir / 'current_state'
            verified_code_file = current_state_dir / 'verified_code.py'
            if verified_code_file.exists():
                history_parts.append("\n⚠️  Currently using CACHED CODE (same code across runs)")

        execution_history = "\n".join(history_parts) if history_parts else "No execution history available"

        # Truncate summaries for LLM
        reflection_summary = self._truncate_for_llm(reflection, max_length=1000)
        action_summary = self._truncate_for_llm(action_result, max_length=1000)
        verification_summary = {
            'execution': execution_verification,
            'domain': domain_verification
        }
        verification_summary = self._truncate_for_llm(verification_summary, max_length=1000)

        # Load and format prompt
        prompt = self._load_prompt(
            'learn_regeneration_analysis',
            act_instructions=act_instructions,
            verify_instructions=verify_instructions,
            reflection_summary=json.dumps(reflection_summary, indent=2),
            action_summary=json.dumps(action_summary, indent=2),
            verification_summary=json.dumps(verification_summary, indent=2),
            execution_history=execution_history
        )

        llm_response = self.llm.complete(prompt, max_tokens=get_max_tokens('regeneration_analysis', 2048))

        # Parse JSON response
        try:
            analysis = self._parse_json_response(llm_response)
        except Exception as e:
            log_message(f"Warning: Could not parse regeneration analysis: {e}", status='error')
            analysis = {
                'recommend_regeneration': False,
                'rationale': f'Failed to parse analysis: {e}',
                'error': str(e)
            }

        # Add timestamp
        analysis['timestamp'] = datetime.now(timezone.utc).isoformat()

        return analysis

    def _synthesize_run_insights(
        self,
        reflection: Dict[str, Any],
        action_result: Dict[str, Any],
        verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze the entire RAVL run and extract domain insights

        This looks across REFLECT, ACT, and VERIFY to identify what worked,
        what didn't, and what patterns emerged in the problem domain.

        Args:
            reflection: Output from REFLECT phase
            action_result: Output from ACT phase
            verification: Output from VERIFY phase (domain verification)

        Returns:
            Dict with synthesized insights about domain effectiveness
        """
        log_execution("Synthesizing insights from full run...", status='working')

        # Truncate large outputs for LLM consumption
        reflection_summary = self._truncate_for_llm(reflection, max_length=2000)
        action_summary = self._truncate_for_llm(action_result, max_length=2000)
        verification_summary = self._truncate_for_llm(verification, max_length=2000)

        # Load and format prompt
        prompt = self._load_prompt(
            'synthesize_run',
            reflection=json.dumps(reflection_summary, indent=2),
            action_result=json.dumps(action_summary, indent=2),
            verification=json.dumps(verification_summary, indent=2)
        )

        llm_response = self.llm.complete(prompt, max_tokens=get_max_tokens('learn_insights', 4096))

        # Parse JSON response
        try:
            insights = self._parse_json_response(llm_response)
        except Exception as e:
            log_message(f"Warning: Could not parse run insights: {e}", status='error')
            insights = {
                'error': 'Failed to parse insights',
                'raw_response': llm_response[:500]
            }

        log_execution("Run insights synthesized", status='success')
        return insights

    def _truncate_for_llm(self, data: Any, max_length: int = 2000) -> Any:
        """
        Truncate data structure for LLM consumption

        Args:
            data: Data to truncate (dict, list, str, etc.)
            max_length: Maximum string length for any value

        Returns:
            Truncated copy of data
        """
        if isinstance(data, dict):
            return {k: self._truncate_for_llm(v, max_length) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._truncate_for_llm(item, max_length) for item in data]
        elif isinstance(data, str):
            if len(data) > max_length:
                return data[:max_length] + f"... (truncated {len(data) - max_length} chars)"
            return data
        else:
            return data

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code blocks

        Args:
            response: LLM response text

        Returns:
            Parsed JSON dict
        """
        json_text = response.strip()

        # Remove markdown code block markers if present
        if json_text.startswith('```'):
            lines = json_text.split('\n')
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            json_text = '\n'.join(lines)

        return json.loads(json_text)

    def _update_performance_metrics(self, current_verification: Optional[Dict[str, Any]] = None):
        """Calculate performance metrics from learning history"""
        history_file = self.learnings_dir / 'learning_history.jsonl'

        if not history_file.exists():
            return

        # Read all learning entries
        entries = []
        with open(history_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        if not entries:
            return

        # Calculate metrics
        total_runs = len(entries)
        passed_runs = sum(1 for e in entries if e.get('verification', {}).get('passed') is True)
        success_rate = passed_runs / total_runs if total_runs > 0 else 0.0

        # Collect recent suggestions
        recent_suggestions = []
        for entry in entries[-10:]:  # Last 10 runs
            suggestions = entry.get('verification', {}).get('suggestions', [])
            recent_suggestions.extend(suggestions)

        # Create metrics file (timestamped, append-only)
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        metrics_file = self.learnings_dir / f'metrics_{timestamp}.yml'

        metrics = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_runs': total_runs,
            'passed_runs': passed_runs,
            'success_rate': success_rate,
            'recent_suggestions': recent_suggestions[-5:]  # Last 5 suggestions
        }

        with open(metrics_file, 'w', encoding='utf-8') as f:
            yaml.dump(metrics, f, default_flow_style=False, sort_keys=False)

        log_execution(f"Metrics: {passed_runs}/{total_runs} passed ({success_rate:.1%})", status='success')
        
        # Display current verification details if provided and failed
        if current_verification and not current_verification.get('overall_passed', False):
            criteria_results = current_verification.get('criteria_results', [])
            if criteria_results:
                log_message("\n📋 Current Verification Details:", status='info')
                for i, criterion in enumerate(criteria_results, 1):
                    status = "✓" if criterion.get('passed', False) else "✗"
                    log_message(f"  {status} [{i}] {criterion.get('criterion', 'Unknown criterion')}", status='info', indent=4)
                    if not criterion.get('passed', False) and criterion.get('explanation'):
                        # Truncate long explanations for console readability
                        explanation = criterion['explanation']
                        if len(explanation) > 100:
                            explanation = explanation[:100] + "..."
                        log_message(explanation, status='info', indent=8)

    def _process_run_child_directives(self, act_instructions: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process run_child directives in Act markdown

        Delegates to ChildLoopExecutor for execution and aggregation.
        """
        return self.child_executor.process_run_child_directives(act_instructions)

    def _create_additional_outputs(
        self,
        llm_output: str,
        verify_instructions: str,
        timestamp: str
    ) -> List[str]:
        """
        Parse verification criteria and create additional output files

        For example, if verification requires "file in /ambitions folder",
        creates that file in addition to the action_result JSON.

        Returns list of created file paths
        """
        import re

        created_files = []

        # Look for patterns like "in the /folder_name folder" or "in /folder_name/"
        folder_pattern = r'in (?:the )?(/[\w_/-]+)/?(?:\s+folder)?'
        matches = re.findall(folder_pattern, verify_instructions, re.IGNORECASE)

        if not matches:
            return created_files

        # For each folder mentioned in verification criteria
        for folder_path in matches:
            folder_path = folder_path.strip('/')

            # Create folder relative to loop directory
            output_dir = self.loop_dir / folder_path
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename from context vars and timestamp
            # E.g., "2025-10-09-cto-ambitions.md" or "2025-10-09-delivery-lead-ambitions.md"
            date_str = timestamp.split('-')[:3]  # YYYY-MM-DD
            date_part = '-'.join(date_str)

            # Get role from context vars and slugify
            role_slug = ''
            for key, value in self.context_vars.items():
                if 'role' in key.lower():
                    role_slug = value.lower().replace(' ', '-')
                    break

            # Construct filename
            if role_slug:
                filename = f"{date_part}-{role_slug}-{folder_path.split('/')[-1]}.md"
            else:
                filename = f"{date_part}-{folder_path.split('/')[-1]}.md"

            output_file = output_dir / filename

            # Write LLM output to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(llm_output)

            created_files.append(str(output_file.relative_to(self.loop_dir)))
            log_execution(f"Additional output saved to {output_file.relative_to(self.loop_dir)}", status='success')

        return created_files

    def _build_context_summary(self, reflection: Dict[str, Any]) -> str:
        """Build human-readable context summary from reflection"""
        summary_parts = []

        # EXPLORATORY LOOP DETECTION (CRITICAL for cache invalidation decisions)
        is_exploratory = self._detect_exploratory_loop()
        if is_exploratory:
            summary_parts.append("## LOOP TYPE: EXPLORATORY/DISCOVERY")
            summary_parts.append("⚠️  This loop is designed for PROGRESSIVE DISCOVERY - each run should explore something NEW.")
            summary_parts.append("⚠️  Exploratory loops fundamentally conflict with code caching.")
            summary_parts.append("")

        # NEW: Execution History (CRITICAL for cache invalidation decisions)
        execution_learning_dir = self.learnings_dir / 'execution_learning'
        if execution_learning_dir.exists():
            recent_attempts_dir = execution_learning_dir / 'recent_attempts'
            if recent_attempts_dir.exists():
                attempt_count = len([d for d in recent_attempts_dir.iterdir()
                                    if d.is_dir() and d.name.startswith('attempt_')])

                if attempt_count > 0:
                    summary_parts.append("## Execution History")
                    summary_parts.append(f"- Total attempts: {attempt_count}")

                    # Check if using cached code
                    current_state_dir = execution_learning_dir / 'current_state'
                    verified_code_file = current_state_dir / 'verified_code.py'
                    if verified_code_file.exists():
                        summary_parts.append("- Status: Using CACHED CODE (same code across multiple runs)")
                        if is_exploratory:
                            summary_parts.append("  🚨 CRITICAL: Exploratory loop + cached code = repetitive exploration (NOT progressive)")
                        summary_parts.append("  ⚠️  If same error repeats, this indicates a CODE LOGIC issue, not transient failure")
                    else:
                        summary_parts.append("- Status: Generating fresh code each run")

                    # Show recent execution outcomes
                    attempt_dirs = sorted(
                        [d for d in recent_attempts_dir.iterdir() if d.is_dir() and d.name.startswith('attempt_')],
                        key=lambda d: int(d.name.split('_')[1])
                    )

                    if attempt_dirs:
                        summary_parts.append("- Recent execution results:")
                        for attempt_dir in attempt_dirs[-5:]:  # Last 5 attempts
                            attempt_num = attempt_dir.name
                            result_file = attempt_dir / 'execution_result.json'
                            if result_file.exists():
                                try:
                                    with open(result_file, 'r') as f:
                                        result = json.load(f)
                                    passed = result.get('passed', False)
                                    status = "✓" if passed else "✗"
                                    summary_parts.append(f"  {status} {attempt_num}")
                                except (IOError, json.JSONDecodeError):
                                    pass
                    summary_parts.append("")

        # Context vars
        if self.context_vars:
            summary_parts.append("## Context Variables")
            for key, value in self.context_vars.items():
                summary_parts.append(f"- {key}: {value}")
            summary_parts.append("")

        # Domain guidance from previous runs (MOST IMPORTANT - show first!)
        domain_guidance = reflection.get('domain_guidance', {})
        if domain_guidance and any(domain_guidance.values()):
            summary_parts.append("## Domain Guidance from Previous Runs")
            summary_parts.append("")
            summary_parts.append("Based on analysis of previous RAVL iterations:")
            summary_parts.append("")

            if domain_guidance.get('priority_focus'):
                summary_parts.append("### Priority Focus")
                for item in domain_guidance['priority_focus']:
                    summary_parts.append(f"- {item}")
                summary_parts.append("")

            if domain_guidance.get('successful_patterns'):
                summary_parts.append("### Patterns That Worked Well (Repeat These)")
                for pattern in domain_guidance['successful_patterns']:
                    summary_parts.append(f"- ✓ {pattern}")
                summary_parts.append("")

            if domain_guidance.get('failed_patterns'):
                summary_parts.append("### Patterns That Failed (Avoid These)")
                for pattern in domain_guidance['failed_patterns']:
                    summary_parts.append(f"- ✗ {pattern}")
                summary_parts.append("")

            if domain_guidance.get('new_strategies_to_try'):
                summary_parts.append("### New Strategies to Try")
                for strategy in domain_guidance['new_strategies_to_try']:
                    summary_parts.append(f"- → {strategy}")
                summary_parts.append("")

            if domain_guidance.get('verification_notes', {}).get('recent_failures'):
                summary_parts.append("### Recent Verification Failures")
                for failure in domain_guidance['verification_notes']['recent_failures']:
                    summary_parts.append(f"- {failure}")
                summary_parts.append("")

        # Learnings summary
        learnings = reflection.get('learnings', {})

        # This loop's learnings
        if 'this_loop' in learnings:
            this_learnings = learnings['this_loop']
            file_count = len(this_learnings.get('files', {}))
            subdir_count = len(this_learnings.get('subdirs', {}))

            if file_count > 0 or subdir_count > 0:
                summary_parts.append(f"## This Loop's Learnings ({file_count} files, {subdir_count} subdirs)")

                # Summarize key files
                files = this_learnings.get('files', {})
                if 'learning_history.jsonl' in files:
                    lines = files['learning_history.jsonl'].strip().split('\n')
                    summary_parts.append(f"- Learning history: {len(lines)} entries")

                # Show recent metrics
                metric_files = [f for f in files.keys() if f.startswith('metrics_')]
                if metric_files:
                    latest_metrics = files[sorted(metric_files)[-1]]
                    if isinstance(latest_metrics, dict):
                        summary_parts.append(f"- Success rate: {latest_metrics.get('success_rate', 0):.1%}")
                        summary_parts.append(f"- Total runs: {latest_metrics.get('total_runs', 0)}")

                # Summarize subdirectories
                subdirs = this_learnings.get('subdirs', {})
                if subdirs:
                    for subdir_name, subdir_data in subdirs.items():
                        subdir_file_count = len(subdir_data.get('files', {}))
                        summary_parts.append(f"- {subdir_name}/: {subdir_file_count} files")

                summary_parts.append("")

        # Parent loop's learnings
        if 'parent_loop' in learnings:
            parent_learnings = learnings['parent_loop']
            file_count = len(parent_learnings.get('files', {}))
            if file_count > 0:
                summary_parts.append(f"## Parent Loop's Learnings ({file_count} files)")
                summary_parts.append(f"Available for context")
                summary_parts.append("")

        # Sibling loops' learnings
        if 'sibling_loops' in learnings:
            sibling_count = len(learnings['sibling_loops'])
            if sibling_count > 0:
                summary_parts.append(f"## Sibling Loops' Learnings ({sibling_count} loops)")
                for sibling_name in learnings['sibling_loops'].keys():
                    file_count = len(learnings['sibling_loops'][sibling_name].get('files', {}))
                    summary_parts.append(f"- {sibling_name}: {file_count} files")
                summary_parts.append("")

        # Child loops' learnings
        if 'child_loops' in learnings:
            child_count = len(learnings['child_loops'])
            if child_count > 0:
                summary_parts.append(f"## Child Loops' Learnings ({child_count} loops)")
                for child_name in learnings['child_loops'].keys():
                    file_count = len(learnings['child_loops'][child_name].get('files', {}))
                    summary_parts.append(f"- {child_name}: {file_count} files")
                summary_parts.append("")

        return '\n'.join(summary_parts)


def main():
    """CLI entry point for testing"""
    import argparse

    parser = argparse.ArgumentParser(description='Execute a markdown RAVL loop')
    parser.add_argument('markdown_file', help='Path to markdown RAVL definition')
    parser.add_argument('--loop-dir', required=True, help='Path to loop directory')
    parser.add_argument('--var', action='append', help='Context variable in format key=value')
    parser.add_argument('--mode', default='fast', choices=['fast', 'full'],
                       help='Execution mode (fast=skip verify/learn, full=complete cycle)')

    args = parser.parse_args()

    # Parse context variables
    context_vars = {}
    if args.var:
        for var_spec in args.var:
            key, value = var_spec.split('=', 1)
            context_vars[key] = value

    # Read and substitute markdown
    markdown_path = Path(args.markdown_file)
    with open(markdown_path, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    # Perform template substitution
    for key, value in context_vars.items():
        markdown_text = markdown_text.replace(f"{{{key}}}", value)

    # Setup paths
    loop_dir = Path(args.loop_dir)
    learnings_dir = loop_dir / 'learnings'

    # Create executor
    executor = MarkdownRAVLExecutor(
        markdown_text=markdown_text,
        loop_dir=loop_dir,
        learnings_dir=learnings_dir,
        context_vars=context_vars
    )

    log_message("=" * 80, status='info', indent=0)
    log_message("Markdown RAVL Executor", status='info', indent=0)
    log_message(f"Loop: {loop_dir.name}", status='info', indent=0)
    log_message(f"Context: {context_vars}", status='info', indent=0)
    log_message("=" * 80, status='info', indent=0)

    # Execute RAVL cycle
    reflection = executor.reflect()
    action_result = executor.act(reflection)

    if args.mode == 'full':
        # Load previous action for verification
        action_files = sorted(learnings_dir.glob('action_result_*.json'))
        previous_action = None
        if len(action_files) >= 2:
            with open(action_files[-2], 'r', encoding='utf-8') as f:
                previous_action = json.load(f)

        verification = executor.verify(previous_action, reflection)
        executor.learn(verification, action_result)

    log_message("=" * 80, status='info', indent=0)
    log_message("[✓] Markdown RAVL loop completed", status='success', indent=0)
    log_message("=" * 80, status='info', indent=0)


if __name__ == '__main__':
    main()
