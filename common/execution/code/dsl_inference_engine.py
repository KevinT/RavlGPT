#!/usr/bin/env python3
"""
DSL Inference Engine for RAVL Loops

Analyzes loop specifications (Act + Verify sections) to infer the optimal DSL
that guides code generation. Learns from previous attempts to improve inference.
"""

import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

from common.config.config_loader import get_max_tokens


class DSLInferenceEngine:
    """
    Infers optimal DSL for a RAVL loop based on its specification and learning history.

    The DSL tells the LLM how to structure generated code to satisfy verification.
    """

    def __init__(self, loop_dir: Path, learnings_dir: Path):
        """
        Initialize inference engine

        Args:
            loop_dir: Path to the loop directory
            learnings_dir: Path to learnings directory (for loading previous attempts)
        """
        self.loop_dir = loop_dir
        self.learnings_dir = learnings_dir

    def infer(self, act_section: str, verify_section: str) -> Dict[str, Any]:
        """
        Infer DSL from loop specification

        Args:
            act_section: Content of Act section from ravl_loop.md
            verify_section: Content of Verify section from ravl_loop.md

        Returns:
            Inferred DSL as dictionary
        """
        dsl = {
            'inferred_at': self._get_timestamp(),
            'attempt_number': self._get_next_attempt_number(),
        }

        # Analyze verify section to infer output requirements
        dsl['output'] = self._infer_output_requirements(verify_section)

        # Analyze verify section to infer data structure
        dsl['data_structure'] = self._infer_data_structure(verify_section)

        # Analyze verify section to infer persistence needs
        dsl['persistence'] = self._infer_persistence_requirements(verify_section)

        # Analyze act section for special requirements
        dsl['act_requirements'] = self._analyze_act_section(act_section)

        # Load previous DSL attempts and failures
        dsl['previous_attempts'] = self._load_previous_attempts()

        # Load failure analysis for iterative learning
        dsl['failure_analysis'] = self._load_failure_analysis()

        # Load warning history for code quality improvements
        dsl['warning_history'] = self._load_warning_history()

        # Generate guidance for LLM based on analysis
        dsl['llm_guidance'] = self._generate_llm_guidance(dsl, verify_section)

        return dsl

    def should_generate_code(self, act_section: str, verify_section: str) -> bool:
        """
        Intelligently decide if code generation is needed for this loop.

        Code generation is needed if the loop requires:
        - File I/O operations (create, write, save, read files)
        - Data transformation (fetch, process, transform, calculate)
        - API interactions (fetch, call, query, request)
        - Complex operations that can't be done with simple introspection

        Args:
            act_section: Content of Act section from ravl_loop.md
            verify_section: Content of Verify section from ravl_loop.md

        Returns:
            True if code generation is likely needed, False otherwise
        """
        combined_text = (act_section + " " + verify_section).lower()

        # Keywords that indicate code generation is needed
        code_generation_keywords = {
            # File operations
            'file', 'write', 'create', 'save', 'generate', 'output', 'folder', 'directory',
            'path', 'exists', 'content', 'data',
            # API operations
            'api', 'endpoint', 'fetch', 'call', 'request', 'response', 'json', 'http',
            # Data operations
            'process', 'transform', 'calculate', 'query', 'database', 'csv', 'extract',
            'parse', 'analyze', 'aggregate', 'filter', 'sort',
            # Complex operations
            'function', 'code', 'script', 'python', 'execute', 'run',
        }

        # Count how many keywords appear
        keyword_count = sum(1 for keyword in code_generation_keywords if keyword in combined_text)

        # If multiple code-generation keywords appear, code is likely needed
        if keyword_count >= 2:
            return True

        # If any ACT section mentions creating/writing/fetching, definitely needs code
        act_text = act_section.lower()
        action_keywords = {'create', 'write', 'save', 'fetch', 'generate', 'file', 'code'}
        if any(keyword in act_text for keyword in action_keywords):
            return True

        return False

    def _infer_output_requirements(self, verify_section: str) -> Dict[str, Any]:
        """
        Infer how results should be returned based on verification criteria
        """
        output = {
            'format': 'json',  # Default
            'destination': 'stdout',  # Default
            'include_metadata': False,
        }

        # Check for indicators of what format is needed
        if 'file' in verify_section.lower():
            output['destination'] = 'file'

            # Extract file location if specified
            file_match = re.search(r'(data/|\.ravl/|/[a-z_/]*)', verify_section)
            if file_match:
                location = file_match.group(1)
                # Normalize absolute paths to relative paths
                # Convert /path to path/ (e.g., /_data -> _data/)
                if location.startswith('/') and not location.startswith('./'):
                    location = location.lstrip('/') + ('/' if not location.endswith('/') else '')
                output['file_location'] = location

        if 'json' in verify_section.lower():
            output['format'] = 'json'
        elif 'csv' in verify_section.lower():
            output['format'] = 'csv'

        # Check if metadata is needed
        if any(word in verify_section.lower() for word in ['timestamp', 'date', 'time', 'count', 'changed']):
            output['include_metadata'] = True

        return output

    def _infer_data_structure(self, verify_section: str) -> Dict[str, Any]:
        """
        Infer the structure of returned data based on verification criteria
        """
        structure = {
            'type': 'unknown',
            'fields': [],
            'constraints': [],
        }

        # Count mentions of specific items to infer structure
        activity_match = re.search(r'(\d+)\s*(activities|records|items|entries)', verify_section, re.IGNORECASE)
        if activity_match:
            structure['type'] = 'array'
            structure['expected_count'] = int(activity_match.group(1))
            structure['item_type'] = activity_match.group(2).lower()

        # Extract field names mentioned in verify section
        # Look for patterns like "activity", "responsible", "accountable", etc.
        field_patterns = [
            'activity', 'responsible', 'accountable', 'consulted', 'informed',
            'name', 'email', 'id', 'person', 'people', 'role', 'title',
            'status', 'state', 'value', 'data'
        ]

        for field in field_patterns:
            if field in verify_section.lower():
                structure['fields'].append(field)

        # Extract constraints
        if 'must have' in verify_section.lower() or 'must include' in verify_section.lower():
            constraint_match = re.findall(r'must\s+(have|include|contain|be|not be)\s+([^,\n.]+)',
                                        verify_section, re.IGNORECASE)
            for constraint in constraint_match:
                structure['constraints'].append(' '.join(constraint))

        return structure

    def _infer_persistence_requirements(self, verify_section: str) -> Dict[str, Any]:
        """
        Infer if/how results should be persisted
        """
        persistence = {
            'enabled': False,
            'format': None,
            'location': None,
            'change_detection': None,
        }

        # Check if persistence is mentioned
        if any(word in verify_section.lower() for word in ['file', 'save', 'persist', 'write', 'create', 'store']):
            persistence['enabled'] = True

            # Infer format
            if 'json' in verify_section.lower():
                persistence['format'] = 'json'
            elif 'csv' in verify_section.lower():
                persistence['format'] = 'csv'

            # Extract location
            location_match = re.search(r'(data/|\.ravl/|\.?[a-z_/]+/)', verify_section)
            if location_match:
                persistence['location'] = location_match.group(1)

            # Check for change detection
            if any(word in verify_section.lower() for word in ['changed', 'change', 'different', 'new', 'only if']):
                persistence['change_detection'] = 'hash_based'

        return persistence

    def _analyze_act_section(self, act_section: str) -> Dict[str, Any]:
        """
        Extract requirements from Act section
        """
        requirements = {
            'has_api_call': False,
            'api_types': [],  # Changed from api_type to api_types (array)
            'has_transformation': False,
            'has_aggregation': False,
        }

        # Check for API indicators
        if any(word in act_section.lower() for word in ['api', 'fetch', 'query', 'request', 'call']):
            requirements['has_api_call'] = True

            # Detect multiple APIs in ACT section
            act_lower = act_section.lower()
            api_types = []

            if 'notion' in act_lower:
                api_types.append('notion')
            if 'hibob' in act_lower:
                api_types.append('hibob')
            if 'google' in act_lower or 'google docs' in act_lower or 'google sheets' in act_lower:
                api_types.append('google')
            if 'clickup' in act_lower:
                api_types.append('clickup')

            requirements['api_types'] = api_types

        # Check for transformation
        if any(word in act_section.lower() for word in ['transform', 'convert', 'map', 'extract', 'parse']):
            requirements['has_transformation'] = True

        # Check for aggregation
        if any(word in act_section.lower() for word in ['aggregate', 'group', 'summarize', 'count', 'total']):
            requirements['has_aggregation'] = True

        # Check for link following requirements
        link_keywords = ['follow link', 'linked page', 'links from', 'link from', 'recursively', 'traverse',
                        'follow page', 'linked from', 'pages that are linked']
        if any(keyword in act_section.lower() for keyword in link_keywords):
            requirements['needs_link_following'] = True

            # Check if it's direct links only (1 level) vs recursive (multiple levels)
            direct_keywords = ['directly linked', 'direct link', 'directly from']
            recursive_keywords = ['recursively', 'all linked', 'traverse all']

            act_lower = act_section.lower()
            if any(keyword in act_lower for keyword in direct_keywords):
                requirements['link_following_depth'] = 'direct'  # Only 1 level deep
            elif any(keyword in act_lower for keyword in recursive_keywords):
                requirements['link_following_depth'] = 'recursive'  # Multiple levels
            else:
                requirements['link_following_depth'] = 'direct'  # Default to direct if ambiguous

        # Check for subprocess/child loop execution requirements
        subprocess_keywords = ['run child loop', 'child loop', 'execute child', 'call loop',
                               'run loop', 'subprocess', 'child process', 'ravl loop', 'ravl framework']
        if any(keyword in act_section.lower() for keyword in subprocess_keywords):
            requirements['needs_subprocess_execution'] = True

        # Check for LLM usage requirements
        llm_keywords = ['summarize', 'analyze with llm', 'extract with llm', 'use llm', 'llm call',
                        'claude', 'opencode', 'gemini', 'gpt', 'language model', 'llm to', 'ask llm', 'prompt llm',
                        'llm-based', 'using llm', 'use an llm', 'call llm']
        if any(keyword in act_section.lower() for keyword in llm_keywords):
            requirements['needs_llm_calls'] = True

        return requirements

    def _load_previous_attempts(self) -> List[Dict[str, Any]]:
        """
        Load and analyze previous DSL attempts from learning history
        """
        attempts = []

        if not self.learnings_dir.exists():
            return attempts

        # Look for dsl_iteration_*.json files
        for file_path in sorted(self.learnings_dir.glob('dsl_iteration_*.json')):
            try:
                with open(file_path, 'r') as f:
                    attempt = json.load(f)
                    attempts.append({
                        'iteration': file_path.stem,
                        'status': attempt.get('status'),
                        'failures': attempt.get('verification_failures', []),
                        'suggestions': attempt.get('suggestions_for_next_iteration', []),
                    })
            except Exception:
                continue

        return attempts

    def _load_failure_analysis(self) -> Dict[str, Any]:
        """
        Load failure analysis from previous attempts for iterative learning.
        Extracts specific failure categories and improvement suggestions.
        """
        if not self.learnings_dir.exists():
            return {
                'has_failures': False,
                'failure_categories': [],
                'improvement_suggestions': [],
                'recent_failures': []
            }

        analysis_file = self.learnings_dir / 'history' / 'failure_analysis.jsonl'
        if not analysis_file.exists():
            return {
                'has_failures': False,
                'failure_categories': [],
                'improvement_suggestions': [],
                'recent_failures': []
            }

        # Load all failure analysis entries
        try:
            all_failures = []
            with open(analysis_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        all_failures.append(entry)
                    except json.JSONDecodeError:
                        continue

            if not all_failures:
                return {
                    'has_failures': False,
                    'failure_categories': [],
                    'improvement_suggestions': [],
                    'recent_failures': []
                }

            # Aggregate failure categories across all failures
            all_categories = set()
            all_suggestions = []
            all_error_categories = set()
            all_error_hints = []
            for failure in all_failures:
                all_categories.update(failure.get('failure_categories', []))
                all_suggestions.extend(failure.get('suggestions_for_next_attempt', []))

                # Extract semantic error categories and hints
                if failure.get('error_category'):
                    all_error_categories.add(failure.get('error_category'))

                if failure.get('error_hints'):
                    for hint in failure.get('error_hints', []):
                        if isinstance(hint, dict) and 'suggestion' in hint:
                            all_error_hints.append(hint['suggestion'])

            # Get recent failures (last 3) for context
            recent = all_failures[-3:]

            return {
                'has_failures': True,
                'total_failures': len(all_failures),
                'failure_categories': list(all_categories),
                'improvement_suggestions': list(set(all_suggestions)),  # Deduplicate
                'error_categories': list(all_error_categories),  # Semantic error types
                'error_hints': list(set(all_error_hints)),  # Semantic suggestions
                'recent_failures': recent
            }

        except Exception:
            return {
                'has_failures': False,
                'failure_categories': [],
                'improvement_suggestions': [],
                'recent_failures': []
            }

    def _load_warning_history(self) -> Dict[str, Any]:
        """
        Load warning history from previous executions for code quality improvements.
        Extracts deprecation warnings and suggests better alternatives.
        """
        if not self.learnings_dir.exists():
            return {
                'has_warnings': False,
                'warning_patterns': {},
                'recent_warnings': []
            }

        # Look in execution_learning/history for warnings
        exec_learning_dir = self.learnings_dir.parent / 'execution_learning'
        warnings_file = exec_learning_dir / 'history' / 'execution_warnings.jsonl'

        if not warnings_file.exists():
            return {
                'has_warnings': False,
                'warning_patterns': {},
                'recent_warnings': []
            }

        # Load all warnings
        try:
            all_warnings = []
            with open(warnings_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        all_warnings.append(entry)
                    except json.JSONDecodeError:
                        continue

            if not all_warnings:
                return {
                    'has_warnings': False,
                    'warning_patterns': {},
                    'recent_warnings': []
                }

            # Aggregate warning patterns by deprecated API
            warning_patterns = {}
            for warning in all_warnings:
                api = warning.get('api')
                warning_type = warning.get('type')
                message = warning.get('message')

                if api and warning_type == 'deprecation':
                    if api not in warning_patterns:
                        warning_patterns[api] = {
                            'count': 0,
                            'type': warning_type,
                            'message': message,
                            'suggestion': self._get_deprecation_fix(api, message)
                        }
                    warning_patterns[api]['count'] += 1

            # Get recent unique warnings (last 5)
            recent_unique = []
            seen_apis = set()
            for warning in reversed(all_warnings):
                api = warning.get('api') or warning.get('message')
                if api and api not in seen_apis:
                    recent_unique.append(warning)
                    seen_apis.add(api)
                    if len(recent_unique) >= 5:
                        break

            return {
                'has_warnings': True,
                'total_warnings': len(all_warnings),
                'warning_patterns': warning_patterns,
                'recent_warnings': list(reversed(recent_unique))
            }

        except Exception:
            return {
                'has_warnings': False,
                'warning_patterns': {},
                'recent_warnings': []
            }

    def _get_deprecation_fix(self, api: str, message: str) -> str:
        """
        Suggest a fix for common deprecation warnings

        Args:
            api: The deprecated API name
            message: The deprecation warning message

        Returns:
            Suggested fix as a string
        """
        # Common deprecation patterns and their fixes
        fixes = {
            'datetime.datetime.utcnow()': 'Use datetime.now(timezone.utc) instead',
            'datetime.utcnow()': 'Use datetime.now(timezone.utc) instead',
            'datetime.utcfromtimestamp': 'Use datetime.fromtimestamp(ts, tz=timezone.utc) instead'
        }

        # Check for exact matches
        for deprecated_api, fix in fixes.items():
            if deprecated_api in api or deprecated_api in message:
                return fix

        # Default suggestion
        return f"Avoid using {api} - check Python documentation for modern alternative"

    def _generate_llm_guidance(self, dsl: Dict[str, Any], verify_section: str) -> str:
        """
        Generate natural language guidance for the LLM based on inferred DSL
        """
        guidance_lines = [
            "# Code Generation Guidance",
            "",
            "Generate Python code wrapped in custom delimiters (NOT markdown code blocks):",
            "===RAVL_CODE_START===",
            "[Your Python code here]",
            "===RAVL_CODE_END===",
            "",
            "Your generated code should:",
            ""
        ]

        # Output guidance
        output = dsl['output']
        if output['destination'] == 'stdout':
            guidance_lines.append(f"- Output results as {output['format'].upper()} to stdout")
        elif output['destination'] == 'file':
            location = output.get('file_location', 'data/')
            guidance_lines.append(f"- Save results to file in: {location} (use relative path, not absolute)")
            if output['format']:
                guidance_lines.append(f"- File format: {output['format'].upper()}")

        if output['include_metadata']:
            guidance_lines.append("- Include metadata: timestamp, record count, if data changed")

        # Data structure guidance
        structure = dsl['data_structure']
        if structure['type'] == 'array':
            count = structure.get('expected_count', '?')
            item_type = structure.get('item_type', 'items')
            guidance_lines.append(f"- Return results as array/list of {count} {item_type}")

        if structure['fields']:
            fields = ', '.join(structure['fields'])
            guidance_lines.append(f"- Each item should have fields: {fields}")

        # Persistence guidance
        persistence = dsl['persistence']
        if persistence['enabled']:
            if persistence['change_detection']:
                guidance_lines.append("- Implement change detection (hash-based comparison)")
                guidance_lines.append("- Only save if data has changed from previous run")
                guidance_lines.append("")
                guidance_lines.append("**IMPORTANT - State File Placement:**")
                guidance_lines.append("- Deliverable output files: Write to specified path (e.g., output/, data/)")
                guidance_lines.append("- State/tracking files (status.json, hashes, etc.): Write to learning directory")
                guidance_lines.append("- Use: Path(os.environ['RAVL_LEARNINGS_DIR']) / 'state' / 'status.json'")
                guidance_lines.append("- Keep deliverables and state files separate")

        # API guidance
        act_req = dsl['act_requirements']
        api_types = act_req.get('api_types', [])
        if api_types:
            if len(api_types) == 1:
                guidance_lines.append(f"- Use {api_types[0].upper()} API authentication from environment")
            else:
                api_names = ', '.join([api.upper() for api in api_types])
                guidance_lines.append(f"- Use appropriate API authentication from environment for: {api_names}")

        # Link following guidance (API-aware)
        if act_req.get('needs_link_following'):
            # Build lowercase string of all API types for checking
            api_types_str = ' '.join(api_types).lower()
            link_depth = act_req.get('link_following_depth', 'direct')

            guidance_lines.append("")
            if link_depth == 'direct':
                guidance_lines.append("# Direct Link Following (1 Level Only):")
                guidance_lines.append("- Fetch ONLY pages directly linked/mentioned in the main page")
                guidance_lines.append("- Do NOT recursively fetch links from those linked pages")
                guidance_lines.append("- Set max_depth=1 or depth limit to prevent deep recursion")
            else:
                guidance_lines.append("# Recursive Link Following (Multiple Levels):")
                guidance_lines.append("- Recursively fetch all linked pages")
                guidance_lines.append("- Follow links from linked pages (deep traversal)")
                guidance_lines.append("- Implement cycle detection to prevent infinite loops")

            if 'notion' in api_types_str:
                guidance_lines.append("- OPTIONAL HELPER: from ravl.common.integrations.notion_helpers import NotionLinkExtractor")
                guidance_lines.append("- Use NotionLinkExtractor.extract_page_mentions(rich_text) to get linked page IDs")
                guidance_lines.append("- Or implement your own parsing logic for type='mention' with mention.type='page'")
                if link_depth == 'direct':
                    guidance_lines.append("- Fetch content from main page, then fetch each directly linked page (stop there)")
                else:
                    guidance_lines.append("- Recursively fetch and merge content from all linked pages")
                guidance_lines.append("- Example: For each block, extract rich_text → extract mentions → fetch linked pages → merge content")
            elif 'google' in api_types_str:
                guidance_lines.append("- Parse document content for links to other Google Docs")
                guidance_lines.append("- Extract document IDs from URLs")
                if link_depth == 'direct':
                    guidance_lines.append("- Fetch only directly linked documents (1 level)")
                else:
                    guidance_lines.append("- Recursively fetch linked document content (multiple levels)")
                guidance_lines.append("- Merge results appropriately")
            else:
                # Generic guidance for other APIs
                guidance_lines.append("- Detect links/references in response data")
                guidance_lines.append("- Recursively fetch linked content")
                guidance_lines.append("- Merge results appropriately")

        # Subprocess/child loop execution guidance
        if act_req.get('needs_subprocess_execution'):
            guidance_lines.append("")
            guidance_lines.append("# Subprocess/Child Loop Execution:")
            guidance_lines.append("- OPTIONAL HELPER: from ravl.common.execution.subprocess_helpers import SubprocessHelper")
            guidance_lines.append("- Use SubprocessHelper.get_project_root() to find ravl script location")
            guidance_lines.append("- Use SubprocessHelper.call_with_clean_env() to run commands without venv interference")
            guidance_lines.append("- Or implement environment cleanup inline (remove VIRTUAL_ENV, clean PATH)")
            guidance_lines.append("- Example: SubprocessHelper.call_with_clean_env([f'{project_root}/ravl', 'child_loop'], cwd=project_root)")

        # LLM API calling guidance
        if act_req.get('needs_llm_calls'):
            # Get recommended token limit for user-generated LLM calls
            recommended_tokens = get_max_tokens('default')
            guidance_lines.append("")
            guidance_lines.append("# REQUIRED: LLM API Calls:")
            guidance_lines.append("- YOU MUST use framework LLM provider (automatic logging and error handling)")
            guidance_lines.append("- from common.llm.llm_providers import LLMProviderFactory")
            guidance_lines.append("- provider = LLMProviderFactory.create_provider('anthropic')  # or 'openai', 'google', 'ollama'")
            guidance_lines.append(f"- response = provider.complete(prompt, max_tokens={recommended_tokens})")
            guidance_lines.append("- DO NOT make direct Anthropic/OpenAI API calls - this bypasses framework logging")
            guidance_lines.append("- All LLM calls must go through LLMProvider for debugging and health monitoring")

        # Learning from previous failures (new detailed analysis)
        failure_analysis = dsl.get('failure_analysis', {})
        if failure_analysis.get('has_failures'):
            guidance_lines.append("")
            guidance_lines.append("# CRITICAL: Learning from Previous Failures:")
            guidance_lines.append(f"This code has failed {failure_analysis.get('total_failures', 0)} time(s) before.")
            guidance_lines.append("Failures were due to:")
            for category in failure_analysis.get('failure_categories', []):
                guidance_lines.append(f"- {category}")

            # Add semantic error categories and hints (highest priority)
            if failure_analysis.get('error_categories'):
                guidance_lines.append("")
                guidance_lines.append("API/Resource Error Patterns Detected:")
                for error_cat in failure_analysis.get('error_categories', []):
                    guidance_lines.append(f"- {error_cat}")

            if failure_analysis.get('error_hints'):
                guidance_lines.append("")
                guidance_lines.append("Strategic adjustments needed:")
                for hint in failure_analysis.get('error_hints', []):
                    guidance_lines.append(f"- {hint}")

            guidance_lines.append("")
            guidance_lines.append("To succeed this time:")
            for suggestion in failure_analysis.get('improvement_suggestions', []):
                guidance_lines.append(f"- {suggestion}")

            # Add specific details from most recent failure
            recent = failure_analysis.get('recent_failures', [])
            if recent:
                last_failure = recent[-1]
                guidance_lines.append("")
                guidance_lines.append(f"# Most Recent Failure (Attempt {last_failure.get('attempt_number')}):")

                # Show semantic error info if available
                if last_failure.get('error_category'):
                    guidance_lines.append(f"Error Category: {last_failure.get('error_category')}")
                    if last_failure.get('error_hints'):
                        for hint in last_failure.get('error_hints', [])[:2]:
                            if isinstance(hint, dict):
                                guidance_lines.append(f"  → {hint.get('suggestion', '')}")

                for criterion in last_failure.get('failed_criteria', [])[:2]:
                    guidance_lines.append(f"- {criterion.get('criterion', 'Unknown')}: {criterion.get('explanation', '')[:100]}")

        elif dsl['previous_attempts']:
            # Fallback to old attempt data if new analysis not available
            guidance_lines.append("")
            guidance_lines.append("# Learning from Previous Attempts:")
            for attempt in dsl['previous_attempts'][-2:]:  # Last 2 attempts
                if attempt['status'] == 'failed' and attempt['suggestions']:
                    for suggestion in attempt['suggestions']:
                        guidance_lines.append(f"- {suggestion}")

        # Code quality warnings (deprecations, future warnings)
        warning_history = dsl.get('warning_history', {})
        if warning_history.get('has_warnings'):
            guidance_lines.append("")
            guidance_lines.append("# IMPORTANT: Code Quality Improvements:")
            guidance_lines.append(f"Previous code generated {warning_history.get('total_warnings', 0)} warning(s).")
            guidance_lines.append("Avoid these deprecated APIs:")

            warning_patterns = warning_history.get('warning_patterns', {})
            for api, pattern_info in warning_patterns.items():
                count = pattern_info.get('count', 0)
                suggestion = pattern_info.get('suggestion', 'Check documentation for modern alternative')
                guidance_lines.append(f"- ❌ DO NOT USE: {api} (appeared {count}x)")
                guidance_lines.append(f"  ✅ {suggestion}")

        # Add verification criteria
        guidance_lines.append("")
        guidance_lines.append("# Your code will be verified against:")
        for line in verify_section.strip().split('\n'):
            if line.strip():
                guidance_lines.append(f"- {line.strip()}")

        return '\n'.join(guidance_lines)

    def _get_timestamp(self) -> str:
        """Get ISO timestamp"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def _get_next_attempt_number(self) -> int:
        """Get the next attempt number based on learning history"""
        if not self.learnings_dir.exists():
            return 1

        attempts = list(self.learnings_dir.glob('dsl_iteration_*.json'))
        if not attempts:
            return 1

        # Extract attempt numbers and find max
        numbers = []
        for file_path in attempts:
            try:
                num = int(file_path.stem.split('_')[-1])
                numbers.append(num)
            except ValueError:
                continue

        return max(numbers) + 1 if numbers else 1
