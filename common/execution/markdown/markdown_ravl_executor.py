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
                print(f"  [i] Venv needs recreation: {issue}", file=sys.stderr)
                delete_success, delete_error = venv_manager.delete()
                if not delete_success:
                    return {
                        'success': False,
                        'error': f'Failed to delete incompatible venv: {delete_error}',
                        'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                    }
                print(f"  [i] Deleted incompatible venv, will recreate with correct Python", file=sys.stderr)

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

                # Load .env file from project root and add to environment
                from ravl_runner import RAVLRunner
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
        llm_provider: Optional[LLMProvider] = None
    ):
        """
        Initialize executor

        Args:
            markdown_text: Pre-substituted markdown content (template vars already replaced)
            loop_dir: Path to this loop's directory (for discovering parent/child/sibling)
            learnings_dir: Path to this loop's learnings directory
            context_vars: Context variables (e.g., {"current role": "CTO"})
            llm_provider: LLM provider to use (defaults to Anthropic)
        """
        self.markdown_text = markdown_text
        self.loop_dir = loop_dir
        self.learnings_dir = learnings_dir
        self.context_vars = context_vars or {}
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

    def _get_available_notion_credentials(self) -> List[str]:
        """Get list of available Notion credential environment variable names"""
        import os
        candidates = ['NOTION_API_TOKEN', 'NOTION_TOKEN', 'NOTION_API_KEY']
        available = [name for name in candidates if os.environ.get(name)]
        return available or candidates  # Return what's available, or suggest all options

    def _is_data_ingress_loop(self) -> bool:
        """
        Detect if this loop is for data ingestion (API data fetching)

        Returns True if:
        - Config has api_endpoint field, OR
        - Config has context7_docs_path field (Context7 API docs), OR
        - Has both ACT and VERIFY sections in markdown
        """
        has_api_config = 'api_endpoint' in self.config or 'context7_docs_path' in self.config
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
        print(f"  Reflecting...", file=sys.stderr)

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
            print(f"  [i]  Found domain learnings from previous runs", file=sys.stderr)
        else:
            print(f"  [i]  No prior domain learnings (fresh start)", file=sys.stderr)
        
        # Synthesize domain guidance from this loop's learnings
        reflection['domain_guidance'] = self._synthesize_domain_context(
            reflection['learnings']['this_loop']
        )

        # Discover and read related loops
        related_loops = self._discover_related_loops()

        if related_loops['parent']:
            parent_learnings_dir = related_loops['parent'] / 'learnings'
            reflection['learnings']['parent_loop'] = self._read_learnings_files(parent_learnings_dir)
            print(f"  [i]  Found parent loop learnings", file=sys.stderr)

        if related_loops['children']:
            reflection['learnings']['child_loops'] = {}
            for child_dir in related_loops['children']:
                child_name = child_dir.name
                child_learnings_dir = child_dir / 'learnings'
                reflection['learnings']['child_loops'][child_name] = self._read_learnings_files(child_learnings_dir)
            print(f"  [i]  Found {len(related_loops['children'])} child loop(s)", file=sys.stderr)

        if related_loops['siblings']:
            reflection['learnings']['sibling_loops'] = {}
            for sibling_dir in related_loops['siblings']:
                sibling_name = sibling_dir.name
                sibling_learnings_dir = sibling_dir / 'learnings'
                reflection['learnings']['sibling_loops'][sibling_name] = self._read_learnings_files(sibling_learnings_dir)
            print(f"  [i]  Found {len(related_loops['siblings'])} sibling loop(s)", file=sys.stderr)

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

        print(f"  [•] Synthesizing domain context for ACT...", file=sys.stderr)

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
            print(f"  [!] Warning: Could not parse domain guidance: {e}", file=sys.stderr)
            domain_guidance = {
                'priority_focus': [],
                'successful_patterns': [],
                'failed_patterns': [],
                'new_strategies_to_try': [],
                'context_needs': [],
                'verification_notes': {},
                'error': f'Failed to parse guidance: {e}'
            }

        print(f"  [✓] Domain context synthesized", file=sys.stderr)
        return domain_guidance

    def act(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        """
        ACT phase: Execute instructions from markdown

        For data ingestion loops: infers DSL, checks cache, and generates code accordingly
        """
        print(f"  Acting...", file=sys.stderr)

        # Store reflection for LEARN phase synthesis
        self._last_reflection = reflection

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

        print(f"  [✓] Action phase completed", file=sys.stderr)

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

        Delegates core logic to CodeGenerator while handling caching,
        code execution, and result persistence locally.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')

        # Check for cached verified code
        cache_result = self._check_code_cache()
        if cache_result:
            cached_code, cached_dsl = cache_result
            log_execution("Using cached verified code - executing...")
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
            if self._should_attempt_code_generation():
                action_result = self._execute_generated_code(cached_code, action_result)

            # Save human-readable companion files for cached code
            if action_result.get('output'):
                self._save_generated_code_artifacts(action_result['output'], timestamp)

            log_execution("Cached code executed", status='success')
            return action_result

        # Not cached - delegate DSL inference and code generation to CodeGenerator
        gen_result = self.code_gen.generate_with_dsl_inference(
            act_spec=act_instructions,
            verify_spec=verify_instructions,
            reflection=reflection,
            load_prompt_fn=self._load_prompt,
            build_context_fn=self._build_context_summary,
            available_credentials_fn=self._get_available_notion_credentials
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
            if self._is_data_ingress_loop():
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
        print(f"  Verifying...", file=sys.stderr)

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
            print(f"  [i]  No verification criteria defined, skipping", file=sys.stderr)
            return {
                'overall_passed': True,
                'message': 'No verification criteria defined',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        if not action_result:
            print(f"  [i]  No action result to verify", file=sys.stderr)
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

        print(f"  [✓] Verification complete", file=sys.stderr)

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
        print(f"  Learning...", file=sys.stderr)

        # EXECUTION LEARNING: How to make code work
        if 'execution' in verification:
            # Pass domain verification too, so execution learning can check regeneration recommendation
            domain_verification = verification.get('domain', {})
            self._learn_execution(verification['execution'], action_result, domain_verification)

        # DOMAIN LEARNING: What the loop learned about its problem (THE "L" IN RAVL)
        if 'domain' in verification:
            self._learn_domain(verification['domain'], action_result)

        print(f"  [✓] Learning saved to execution_learning/ and loop_learning/", file=sys.stderr)

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
                log_execution(f"Domain verification recommends code regeneration: {regeneration_rationale}", status='info')
                # Don't cache code - force regeneration on next run
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
        print(f"  [•] Synthesizing insights from full run...", file=sys.stderr)

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
            print(f"  [!] Warning: Could not parse run insights: {e}", file=sys.stderr)
            insights = {
                'error': 'Failed to parse insights',
                'raw_response': llm_response[:500]
            }

        print(f"  [✓] Run insights synthesized", file=sys.stderr)
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

        print(f"  [✓] Metrics: {passed_runs}/{total_runs} passed ({success_rate:.1%})", file=sys.stderr)
        
        # Display current verification details if provided and failed
        if current_verification and not current_verification.get('overall_passed', False):
            criteria_results = current_verification.get('criteria_results', [])
            if criteria_results:
                print(f"\n  📋 Current Verification Details:", file=sys.stderr)
                for i, criterion in enumerate(criteria_results, 1):
                    status = "✓" if criterion.get('passed', False) else "✗"
                    print(f"     {status} [{i}] {criterion.get('criterion', 'Unknown criterion')}", file=sys.stderr)
                    if not criterion.get('passed', False) and criterion.get('explanation'):
                        # Truncate long explanations for console readability
                        explanation = criterion['explanation']
                        if len(explanation) > 100:
                            explanation = explanation[:100] + "..."
                        print(f"         {explanation}", file=sys.stderr)

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
            print(f"  [✓] Additional output saved to {output_file.relative_to(self.loop_dir)}", file=sys.stderr)

        return created_files

    def _build_context_summary(self, reflection: Dict[str, Any]) -> str:
        """Build human-readable context summary from reflection"""
        summary_parts = []

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

    print("=" * 80, file=sys.stderr)
    print(f"Markdown RAVL Executor", file=sys.stderr)
    print(f"Loop: {loop_dir.name}", file=sys.stderr)
    print(f"Context: {context_vars}", file=sys.stderr)
    print("=" * 80, file=sys.stderr)

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

    print("=" * 80, file=sys.stderr)
    print("[✓] Markdown RAVL loop completed", file=sys.stderr)
    print("=" * 80, file=sys.stderr)


if __name__ == '__main__':
    main()
