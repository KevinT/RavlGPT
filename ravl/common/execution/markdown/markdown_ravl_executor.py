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
try:
    import tomllib
except ImportError:
    import tomli as tomllib
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
sys.path.insert(0, str(_common_dir / 'cli'))

from ravl.common.config.config_loader import get_max_tokens
from ravl.common.config.config_service import ConfigService
from llm_providers import LLMProviderFactory, LLMProvider
from credential_validator import CredentialValidator
from dsl_inference_engine import DSLInferenceEngine
from schema_adapters import enhance_llm_guidance_with_schema_adaptation
from markdown_parser import MarkdownParser
from code_cache_manager import CodeCacheManager
from code_generator import CodeGenerator
from loop_context_builder import LoopContextBuilder
from child_loop_executor import ChildLoopExecutor
from llm_response_helper import LLMResponseHelper
from verification_manager import VerificationManager
from learning_coordinator import LearningCoordinator
from reflection_orchestrator import ReflectionOrchestrator
from act_orchestrator import ActOrchestrator
from ravl_cli_base import RAVLCLIBase

# Import utilities
from file_utils import load_json_file, save_json_file, append_to_jsonl, load_toml_file
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
from simple_code_executor import SimpleCodeExecutor

# Lazy import to avoid circular dependencies
DataIngressExecutor = None


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

        # Load loop configuration (needed for LLM resolution)
        self.config = self._load_config()

        # Setup LLM provider with hierarchical configuration resolution
        if llm_provider:
            # Use provided LLM provider (typically from parent loops or tests)
            self.llm = llm_provider
        else:
            # Resolve LLM config from hierarchy: loop → parent → project → .env → auto-detect
            from ravl_runner import RAVLRunner
            llm_config = RAVLRunner.resolve_llm_config(
                loop_dir=self.loop_dir,
                loop_config=self.config,
                project_root=self.project_root
            )

            # Validate API key for selected provider (hard failure if missing)
            provider_name = llm_config.get('provider', 'anthropic')
            api_key_valid, error_message = self._validate_provider_api_key(provider_name)
            if not api_key_valid:
                # Log to execution learning before failing
                self._log_configuration_failure('llm_provider', provider_name, error_message)
                raise ValueError(error_message)

            # Create provider with full config (model + parameters)
            self.llm = LLMProviderFactory.create_provider(
                provider_name,
                model=llm_config.get('model'),
                temperature=llm_config.get('temperature'),
                max_tokens=llm_config.get('max_tokens'),
                top_p=llm_config.get('top_p')
            )

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

        # Initialize LLM Response Helper
        self.llm_helper = LLMResponseHelper(self.prompts_dir)

        # Initialize SimpleCodeExecutor for general-purpose code execution
        self.simple_code_executor = SimpleCodeExecutor(self.loop_dir, self.project_root)

        # Initialize ConfigService for configuration resolution
        self.config_service = ConfigService(self.loop_dir, self.project_root)

        # Initialize orchestrators for RAVL phases
        self.reflection_orchestrator = ReflectionOrchestrator(
            loop_dir=self.loop_dir,
            learnings_dir=self.learnings_dir,
            context_vars=self.context_vars,
            llm_provider=self.llm,
            llm_helper=self.llm_helper,
            context_builder=self.context_builder,
            should_skip_cache_fn=self._should_skip_cache,
            check_has_domain_learnings_fn=self._check_has_domain_learnings,
            config_service=self.config_service
        )

        self.act_orchestrator = ActOrchestrator(
            loop_dir=self.loop_dir,
            learnings_dir=self.learnings_dir,
            project_root=self.project_root,
            context_vars=self.context_vars,
            config=self.config,
            llm_provider=self.llm,
            llm_helper=self.llm_helper,
            phases_accessor=lambda: self.phases,
            code_generator=self.code_gen,
            cache_manager=self.cache_manager,
            child_executor=self.child_executor,
            simple_code_executor=self.simple_code_executor,
            should_attempt_code_generation_fn=self._should_attempt_code_generation,
            is_data_ingress_loop_fn=self._is_data_ingress_loop,
            get_available_credentials_fn=self._get_available_notion_credentials
        )

        self.verification_manager = VerificationManager(
            llm_provider=self.llm,
            llm_helper=self.llm_helper,
            phases_accessor=lambda: self.phases,  # Lazy accessor
            code_generator=self.code_gen,
            should_attempt_code_generation=self._should_attempt_code_generation
        )

        self.learning_coordinator = LearningCoordinator(
            learnings_dir=self.learnings_dir,
            execution_learning_mgr=self.execution_learning_mgr,
            loop_learning_mgr=self.loop_learning_mgr,
            llm_provider=self.llm,
            llm_helper=self.llm_helper,
            phases_accessor=lambda: self.phases,  # Lazy accessor
            cache_manager=self.cache_manager,
            should_attempt_code_generation=self._should_attempt_code_generation
        )

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
        """Find project root using framework utility"""
        from ravl.common.cli.ravl_cli_base import RAVLCLIBase
        return RAVLCLIBase.find_project_root(
            start_path=self.loop_dir,
            required=False
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load loop configuration from config/ravl.toml if it exists"""
        config_file = self.loop_dir / 'config' / 'ravl.toml'
        if not config_file.exists():
            return {}

        try:
            with open(config_file, 'rb') as f:
                return tomllib.load(f) or {}
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
        """Load a prompt template and substitute variables - delegates to LLMResponseHelper"""
        return self.llm_helper.load_prompt(prompt_name, **variables)

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
            project_root = RAVLCLIBase.find_project_root(self.loop_dir, required=False)
            relative_dir = str(learnings_dir.relative_to(project_root))
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
                                with open(file_path, 'rb') as f:
                                    subdir_data['files'][file_path.name] = tomllib.load(f)
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
                        with open(item_path, 'rb') as f:
                            learnings['files'][item_path.name] = tomllib.load(f)
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

        Delegates to ReflectionOrchestrator for implementation.
        """
        reflection = self.reflection_orchestrator.reflect(read_learnings_fn=self._read_learnings_files)

        # Store reflection for lazy phase parsing and later use
        self._last_reflection = reflection

        return reflection

    def act(self, reflection: Dict[str, Any], mode: str = 'full') -> Dict[str, Any]:
        """
        ACT phase: Execute instructions from markdown

        Delegates to ActOrchestrator for implementation.

        Args:
            reflection: Output from REFLECT phase
            mode: Execution mode ('full', 'fast', or 'execute')
        """
        # Store reflection for LEARN phase synthesis
        self._last_reflection = reflection

        # Delegate to ActOrchestrator
        action_result = self.act_orchestrator.act(
            reflection=reflection,
            build_context_fn=self._build_context_summary,
            mode=mode
        )

        # Track generated code for learning
        self._last_generated_code = self.act_orchestrator.last_generated_code

        return action_result

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

        Delegates to VerificationManager for implementation.
        """
        return self.verification_manager.verify(
            action_result=action_result,
            current_reflection=current_reflection,
            save_verified_code_fn=self.save_verified_code
        )

    def learn(
        self,
        verification: Dict[str, Any],
        action_result: Dict[str, Any]
    ) -> None:
        """
        LEARN phase: Automatic learning from verification outcomes

        Delegates to LearningCoordinator for implementation.
        """
        self.learning_coordinator.learn(
            verification=verification,
            action_result=action_result,
            last_reflection=self._last_reflection,
            last_generated_code=self._last_generated_code,
            save_verified_code_fn=self.save_verified_code
        )

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

    def _validate_provider_api_key(self, provider_type: str) -> Tuple[bool, str]:
        """
        Validate that API key exists for selected LLM provider

        Args:
            provider_type: Provider name (anthropic, openai, google, ollama)

        Returns:
            Tuple of (valid: bool, error_message: str)
        """
        # Map providers to required API keys
        key_map = {
            'anthropic': 'ANTHROPIC_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'google': 'GOOGLE_API_KEY',
            'ollama': None  # Local, no key needed
        }

        required_key = key_map.get(provider_type)

        # Ollama doesn't need API key
        if required_key is None:
            return (True, "")

        # Check if key exists
        if not os.environ.get(required_key):
            error = f"""
LLM Provider Configuration Error:
  Provider: {provider_type}
  Required API Key: {required_key}
  Status: NOT FOUND

The loop is configured to use '{provider_type}' but the required API key is missing.

To fix this:
1. Add API key to .env file at project root:
   {required_key}=your-api-key-here

2. Or change provider in config/ravl.toml:
   llm_provider:
     provider: anthropic  # or openai, google, ollama

3. Or use auto-detection (remove llm_provider config entirely)

Configuration hierarchy checked:
  - Loop config: {self.loop_dir}/config/ravl.toml
  - Parent configs: (checked full parent chain)
  - Project config: ravl_loops/config/ravl.toml
  - .env file: RAVL_DEFAULT_LLM_PROVIDER
"""
            return (False, error)

        return (True, "")

    def _log_configuration_failure(self, config_type: str, config_value: str, error_message: str):
        """
        Log configuration failure to execution learning directory

        Creates:
        - execution_learning/current_state/configuration_failure.json
        - execution_learning/history/configuration_failures.jsonl

        Args:
            config_type: Type of configuration that failed (e.g., 'llm_provider')
            config_value: Value that failed (e.g., 'anthropic')
            error_message: Full error message explaining the failure
        """
        failure_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'failure_type': 'configuration_error',
            'config_type': config_type,
            'config_value': config_value,
            'error_message': error_message,
            'loop_dir': str(self.loop_dir),
            'loop_name': self.loop_dir.name
        }

        # Log to execution_learning/current_state/
        execution_learning_dir = self.learnings_dir / 'execution_learning'
        execution_learning_dir.mkdir(parents=True, exist_ok=True)

        failure_file = execution_learning_dir / 'current_state' / 'configuration_failure.json'
        failure_file.parent.mkdir(parents=True, exist_ok=True)

        with open(failure_file, 'w', encoding='utf-8') as f:
            json.dump(failure_data, f, indent=2)

        # Also append to history
        history_file = execution_learning_dir / 'history' / 'configuration_failures.jsonl'
        history_file.parent.mkdir(parents=True, exist_ok=True)

        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(failure_data) + '\n')


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
