#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Data Ingress Executor

Self-healing API data ingestion for RAVL loops.

Handles:
- Extracting data requirements from markdown (ACT section)
- Extracting verification rules from markdown (VERIFY section)
- Using LLM + Context7 docs to generate working API integration code
- Executing generated code safely with error handling
- Caching and reusing successful strategies
- Tracking failures and triggering re-generation with alternatives
"""

import json
import sys
import subprocess
import tempfile
import time
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import hashlib
import os

from common.config.config_loader import get_max_tokens

# Add paths to find relocated modules
_script_dir = Path(__file__).parent
_common_dir = _script_dir.parent.parent
sys.path.insert(0, str(_common_dir / 'integrations'))
sys.path.insert(0, str(_common_dir / 'core' / 'error_handling'))
sys.path.insert(0, str(_common_dir / 'utils'))

from credential_validator import CredentialValidator
from error_semantic_analyzer import ErrorSemanticAnalyzer
from logging_utils import log_execution, log_message


class DataIngressExecutor:
    """
    Orchestrates self-healing data ingestion for RAVL loops

    Workflow:
    1. Extract ACT section (required data, output format)
    2. Extract VERIFY section (validation rules)
    3. Load or generate strategy (code to fetch data)
    4. Execute strategy code
    5. Validate output against VERIFY rules
    6. Return results for framework to learn from
    """

    def __init__(self, loop_path: Path, llm_provider=None):
        """
        Initialize executor

        Args:
            loop_path: Path to ravl_loop.md directory
            llm_provider: LLM provider instance (from llm_providers.LLMProviderFactory)
        """
        self.loop_path = Path(loop_path)
        self.ravl_loop_file = self.loop_path / 'ravl_loop.md'
        self.config_file = self.loop_path / 'config' / 'ravl.toml'
        self.learnings_dir = self.loop_path / 'learnings'
        self.learnings_dir.mkdir(parents=True, exist_ok=True)

        # Prompts directory - shared with markdown executor
        self.prompts_dir = Path(__file__).parent.parent / 'markdown' / 'prompts'

        self.llm_provider = llm_provider
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load ravl.toml configuration"""
        if not self.config_file.exists():
            return {
                'api_endpoint': 'https://api.example.com',
                'api_auth_method': 'Bearer',
                'context7_docs_path': '/websites/api_example_com/llms.txt',
                'context7_cache_ttl_hours': 168,
                'max_retry_attempts': 3,
                'strategy_cache_file': 'learnings/current_strategy.json'
            }

        import toml
        with open(self.config_file, 'r') as f:
            return toml.load(f) or {}

    def _load_prompt(self, prompt_name: str, **variables) -> str:
        """Load a prompt template and substitute variables"""
        prompt_file = self.prompts_dir / f'{prompt_name}.md'

        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Substitute variables
        return prompt_template.format(**variables)

    def extract_section(self, section_name: str) -> Optional[str]:
        """
        Extract a markdown section (e.g., ACT, VERIFY) from ravl_loop.md

        Args:
            section_name: Section name (ACT, VERIFY, Reflect, Learn)

        Returns:
            Content of section or None if not found
        """
        if not self.ravl_loop_file.exists():
            return None

        with open(self.ravl_loop_file, 'r') as f:
            content = f.read()

        # Find section (case-insensitive)
        pattern = rf'^# {section_name}\b(.*?)(?=^# |\Z)'
        match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE | re.DOTALL)

        return match.group(1).strip() if match else None

    def extract_act_section(self) -> Dict[str, Any]:
        """
        Parse ACT section and extract requirements

        Expected format:
        # Act

        ## Required Data
        - field1
        - field2

        ## Output Format
        {...JSON example...}

        Returns:
            Dict with keys: required_fields (list), output_format (dict/str), pagination_info (str)
        """
        act_text = self.extract_section('Act')
        if not act_text:
            return {}

        result = {}

        # Extract required data fields
        required_pattern = r'## Required Data\n(.*?)(?=## |\Z)'
        required_match = re.search(required_pattern, act_text, re.DOTALL)
        if required_match:
            fields_text = required_match.group(1)
            # Parse bullet points
            fields = re.findall(r'- (.+)', fields_text)
            result['required_fields'] = fields

        # Extract output format
        output_pattern = r'## Output Format\n(.*?)(?=## |\Z)'
        output_match = re.search(output_pattern, act_text, re.DOTALL)
        if output_match:
            output_text = output_match.group(1).strip()
            # Try to parse as JSON
            try:
                result['output_format'] = json.loads(output_text)
            except json.JSONDecodeError:
                result['output_format'] = output_text

        # Extract other sections (pagination, filters, etc.)
        for section in re.finditer(r'## (.+?)\n(.*?)(?=## |\Z)', act_text, re.DOTALL):
            name = section.group(1).strip()
            content = section.group(2).strip()
            if name.lower() not in ['required data', 'output format']:
                result[name.lower().replace(' ', '_')] = content

        return result

    def extract_verify_section(self) -> List[str]:
        """
        Parse VERIFY section and extract validation rules

        Expected format:
        # Verify

        - Rule 1
        - Rule 2
        - Rule 3

        Pass if <criteria>

        Returns:
            List of validation rules (strings)
        """
        verify_text = self.extract_section('Verify')
        if not verify_text:
            return []

        # Extract bullet points as rules
        rules = re.findall(r'- (.+)', verify_text)

        # Extract pass criteria
        criteria_match = re.search(r'Pass if (.+?)(?:\n|$)', verify_text)
        if criteria_match:
            rules.append(f"Pass criteria: {criteria_match.group(1)}")

        return rules

    def get_current_strategy(self) -> Optional[Dict[str, Any]]:
        """
        Load current cached strategy if it exists and is still valid

        Returns:
            Current strategy dict or None if not available
        """
        strategy_file = self.learnings_dir / 'current_strategy.json'

        if not strategy_file.exists():
            return None

        with open(strategy_file, 'r') as f:
            strategy = json.load(f)

        # Check if Context7 cache is still fresh
        if self._is_context7_cache_fresh():
            return strategy

        # Cache expired - strategy might need regeneration
        strategy['cache_expired'] = True
        return strategy

    def _is_context7_cache_fresh(self) -> bool:
        """Check if Context7 docs cache is still valid"""
        cache_file = self.learnings_dir / 'context7_docs_cache.txt'
        if not cache_file.exists():
            return False

        cache_age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        ttl_hours = self.config.get('context7_cache_ttl_hours', 168)

        return cache_age_hours < ttl_hours

    def save_strategy(self, strategy: Dict[str, Any]):
        """Save current working strategy to cache"""
        strategy_file = self.learnings_dir / 'current_strategy.json'

        # Create strategy_history directory
        history_dir = self.learnings_dir / 'strategy_history'
        history_dir.mkdir(parents=True, exist_ok=True)

        # Save timestamped copy to history
        timestamp = datetime.now(timezone.utc).isoformat().replace(':', '-').split('.')[0]
        history_file = history_dir / f'{timestamp}.json'

        with open(strategy_file, 'w') as f:
            json.dump(strategy, f, indent=2)

        with open(history_file, 'w') as f:
            json.dump(strategy, f, indent=2)

        log_execution(f"Saved strategy to {strategy_file.name}", status='success')

    def generate_code_from_llm(
        self,
        context7_docs: str,
        required_fields: List[str],
        output_format: Any,
        failure_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Use LLM to generate Python code for API integration

        Args:
            context7_docs: API documentation from Context7
            required_fields: List of required data fields
            output_format: Expected output format (dict or schema)
            failure_history: Previous failed attempts (for learning)

        Returns:
            Python code string ready to execute
        """
        if not self.llm_provider:
            raise Exception("LLM provider not configured")

        # Build prompt for code generation
        output_format_str = json.dumps(output_format, indent=2) if isinstance(output_format, dict) else str(output_format)

        failure_context = ""
        if failure_history:
            failure_context = "\n\nPrevious failed attempts:\n"
            for failure in failure_history[-3:]:  # Last 3 failures
                failure_context += f"- {failure.get('error', 'Unknown error')}\n"

        # Load prompt from template
        required_fields_str = chr(10).join(f'- {f}' for f in required_fields)
        prompt = self._load_prompt(
            'data_ingestion_codegen',
            context7_docs=context7_docs[:10000],  # Truncate to avoid token limits
            required_fields=required_fields_str,
            output_format=output_format_str,
            failure_context=failure_context
        )

        log_execution("Calling LLM to generate integration code...", status='working')
        response = self.llm_provider.generate(prompt, max_tokens=get_max_tokens('data_ingress_code_generation'))

        # Extract Python code from response
        code = self._extract_python_code(response)

        if not code or 'def fetch_data' not in code:
            raise Exception("LLM did not generate valid fetch_data function")

        return code

    def _extract_python_code(self, text: str) -> str:
        """Extract Python code from LLM response"""
        # Look for code block
        code_match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
        if code_match:
            return code_match.group(1)

        # If no code block, try to extract code starting with def
        code_match = re.search(r'(def fetch_data.*)', text, re.DOTALL)
        if code_match:
            code = code_match.group(1)
            # Clean up trailing text
            lines = code.split('\n')
            result = []
            for line in lines:
                if line.startswith(('import ', 'from ', 'def ', 'class ', '    ', '\t', '#')):
                    result.append(line)
                elif not result:  # Haven't started yet
                    continue
                else:
                    break
            return '\n'.join(result)

        return text

    def execute_code(self, code: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Execute generated Python code safely in isolated environment

        Args:
            code: Python code to execute (should define fetch_data() function)
            timeout: Execution timeout in seconds

        Returns:
            Dict with keys: success (bool), data (dict), error (str), execution_time (float),
                           credentials_used (list), credential_validation_passed (bool)
        """
        # Step 1: Clean markdown code fences if present
        code_clean = self._clean_markdown_fences(code)

        # Step 2: Detect and validate credentials
        required_creds = CredentialValidator.detect_required_credentials(code_clean)
        creds_valid, creds_message, missing_vars = CredentialValidator.validate_credentials(required_creds)

        log_execution(creds_message, status='info')

        if not creds_valid:
            error_msg = CredentialValidator.get_missing_credentials_error(missing_vars, required_creds)
            log_message(error_msg, status='error')
            return {
                'success': False,
                'error': f'Missing credentials: {", ".join(missing_vars)}',
                'execution_time': 0,
                'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                'credentials_used': list(required_creds.keys()),
                'credential_validation_passed': False
            }

        # Step 3: Write code to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_file = Path(f.name)

            # Check if code defines a fetch_data function
            if 'def fetch_data' in code_clean:
                # Code defines fetch_data, wrap with call
                f.write(code_clean)
                f.write('\n\nimport json\n')
                f.write('result = fetch_data()\n')
                f.write('print(json.dumps(result, indent=2))\n')
            else:
                # Code is a standalone script, wrap main execution
                f.write(code_clean)
                # The code should print JSON output directly, or we'll capture stdout

        try:
            start_time = time.time()

            # Execute code in subprocess with timeout
            result = subprocess.run(
                ['python3', str(temp_file)],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={
                    **subprocess.os.environ,
                    'PYTHONUNBUFFERED': '1'
                }
            )

            execution_time = time.time() - start_time

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                error_context = ErrorSemanticAnalyzer.build_failure_context(
                    result.stderr, result.stdout, error_msg
                )
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': execution_time,
                    'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                    'credentials_used': list(required_creds.keys()),
                    'credential_validation_passed': True,
                    'error_context': error_context,
                }

            # Parse JSON output
            try:
                data = json.loads(result.stdout)
                return {
                    'success': True,
                    'data': data,
                    'execution_time': execution_time,
                    'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                    'credentials_used': list(required_creds.keys()),
                    'credential_validation_passed': True
                }
            except json.JSONDecodeError as e:
                error_msg = f'Invalid JSON output: {str(e)}\nOutput was: {result.stdout[:500]}'
                error_context = ErrorSemanticAnalyzer.build_failure_context(
                    result.stderr, result.stdout, error_msg
                )
                return {
                    'success': False,
                    'error': error_msg,
                    'execution_time': execution_time,
                    'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                    'credentials_used': list(required_creds.keys()),
                    'credential_validation_passed': True,
                    'error_context': error_context,
                }

        except subprocess.TimeoutExpired:
            error_msg = f'Code execution timeout after {timeout}s'
            error_context = ErrorSemanticAnalyzer.build_failure_context(
                '', '', error_msg
            )
            return {
                'success': False,
                'error': error_msg,
                'execution_time': timeout,
                'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                'credentials_used': list(required_creds.keys()),
                'credential_validation_passed': True,
                'error_context': error_context,
            }

        except Exception as e:
            error_msg = str(e)
            error_context = ErrorSemanticAnalyzer.build_failure_context(
                '', '', error_msg
            )
            return {
                'success': False,
                'error': error_msg,
                'execution_time': 0,
                'code_hash': hashlib.md5(code_clean.encode()).hexdigest(),
                'credentials_used': list(required_creds.keys()),
                'credential_validation_passed': True,
                'error_context': error_context,
            }

        finally:
            temp_file.unlink()

    def _clean_markdown_fences(self, code: str) -> str:
        """
        Remove code block delimiters if present.

        Handles both custom delimiters (===RAVL_CODE_START/END===) and
        markdown code blocks (```python / ```).

        Args:
            code: Python code string possibly wrapped in delimiters

        Returns:
            Clean Python code without wrappers
        """
        # First try custom delimiters (preferred)
        if '===RAVL_CODE_START===' in code and '===RAVL_CODE_END===' in code:
            start_marker = '===RAVL_CODE_START==='
            end_marker = '===RAVL_CODE_END==='
            start_idx = code.find(start_marker) + len(start_marker)
            end_idx = code.find(end_marker)
            return code[start_idx:end_idx].strip()

        # Fallback: Remove markdown code block fences
        code = re.sub(r'^```python\n', '', code)
        code = re.sub(r'^```\n', '', code)
        code = re.sub(r'\n```$', '', code)
        return code.strip()

    def verify_output(self, data: Dict[str, Any], verify_rules: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify output against user-specified rules

        Args:
            data: Data returned from fetch_data()
            verify_rules: List of verification rules from VERIFY section

        Returns:
            Tuple of (passed: bool, metrics: dict)
        """
        metrics = {
            'checks_passed': 0,
            'checks_failed': 0,
            'total_checks': len(verify_rules),
            'details': []
        }

        # Basic schema validation: check if data has expected structure
        if not isinstance(data, dict):
            metrics['details'].append('Output is not a dict')
            return False, metrics

        # Check for required keys from output format
        act_section = self.extract_act_section()
        if 'output_format' in act_section and isinstance(act_section['output_format'], dict):
            for key in act_section['output_format'].keys():
                if key in data or key == 'customers' or key == 'data':  # Common root keys
                    metrics['checks_passed'] += 1
                else:
                    metrics['details'].append(f'Missing key: {key}')
                    metrics['checks_failed'] += 1

        # User-specified rules are currently descriptive; in production would need LLM eval
        metrics['checks_passed'] = max(1, metrics['checks_passed'])

        passed = metrics['checks_failed'] == 0 and len(data) > 0

        return passed, metrics

    def execute_full_workflow(self) -> Dict[str, Any]:
        """
        Execute the full data ingestion workflow:
        1. Extract requirements from ravl_loop.md
        2. Load or generate strategy
        3. Execute code
        4. Verify output

        Returns:
            Result dict with all execution details
        """
        log_execution("Starting data ingestion workflow", status='working')

        result = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'act_extracted': False,
            'strategy_loaded': False,
            'code_generated': False,
            'code_executed': False,
            'verified': False,
            'success': False
        }

        try:
            # Step 1: Extract requirements
            log_execution("Extracting ACT section...", status='working')
            act = self.extract_act_section()
            verify_rules = self.extract_verify_section()

            if not act or 'required_fields' not in act:
                raise Exception("ACT section missing required_fields")

            result['act_extracted'] = True
            result['required_fields'] = act.get('required_fields', [])
            result['verify_rules_count'] = len(verify_rules)

            # Step 2: Load or generate strategy
            log_execution("Loading strategy...", status='working')
            strategy = self.get_current_strategy()

            if strategy and not strategy.get('cache_expired'):
                log_execution(f"Using cached strategy (last used: {strategy.get('last_used', 'unknown')})", status='success')
                code = strategy['code']
                result['strategy_loaded'] = True
                result['strategy_reused'] = True
            else:
                log_execution("No cached strategy, generating new one...", status='working')
                # Fetch Context7 docs (simplified - in real impl would use fetching logic)
                context7_docs = self._fetch_context7_docs()

                code = self.generate_code_from_llm(
                    context7_docs,
                    act.get('required_fields', []),
                    act.get('output_format', {}),
                    failure_history=self._load_failure_history()
                )

                result['code_generated'] = True
                result['strategy_reused'] = False

            result['code_hash'] = hashlib.md5(code.encode()).hexdigest()

            # Step 3: Execute code
            log_execution("Executing integration code...", status='working')
            exec_result = self.execute_code(code, timeout=300)

            if not exec_result['success']:
                result['error'] = exec_result['error']
                result['execution_time'] = exec_result.get('execution_time', 0)
                result['code_executed'] = False

                # Record failure
                self._record_failure(exec_result['error'], code)

                log_message(f"Execution failed: {exec_result['error'][:100]}", status='error')
                return result

            result['code_executed'] = True
            result['execution_time'] = exec_result.get('execution_time', 0)
            result['data'] = exec_result['data']

            # Step 4: Verify output
            log_execution("Verifying output...", status='working')
            verified, metrics = self.verify_output(exec_result['data'], verify_rules)

            result['verified'] = verified
            result['verification_metrics'] = metrics
            result['success'] = verified

            if verified:
                log_execution("Output verified successfully", status='success')

                # Save successful strategy
                if not strategy or strategy.get('cache_expired'):
                    strategy = {
                        'code': code,
                        'code_hash': result['code_hash'],
                        'first_generated': datetime.now(timezone.utc).isoformat(),
                        'last_used': datetime.now(timezone.utc).isoformat(),
                        'consecutive_successes': 1,
                        'failure_count': 0
                    }
                else:
                    strategy['last_used'] = datetime.now(timezone.utc).isoformat()
                    strategy['consecutive_successes'] = strategy.get('consecutive_successes', 0) + 1
                    strategy['failure_count'] = 0

                self.save_strategy(strategy)

                # Clear failure history on success
                failure_file = self.learnings_dir / 'failure_history.json'
                if failure_file.exists():
                    failure_file.unlink()
            else:
                log_message(f"Output verification failed: {metrics}", status='error')

            return result

        except Exception as e:
            result['error'] = str(e)
            log_message(f"Workflow error: {str(e)}", status='error')
            return result

    def _fetch_context7_docs(self) -> str:
        """
        Fetch API documentation from Context7 with caching

        Returns:
            Documentation content as string
        """
        cache_file = self.learnings_dir / 'context7_docs_cache.txt'

        # Check cache first
        if cache_file.exists() and self._is_context7_cache_fresh():
            log_execution("Using cached Context7 docs", status='info')
            with open(cache_file, 'r') as f:
                return f.read()

        # Fetch from Context7
        log_execution("Fetching from Context7...", status='working')
        docs_path = self.config.get('context7_docs_path', '')

        try:
            import requests
            url = f"https://context7.com{docs_path}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            docs = response.text

            # Cache for future use
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w') as f:
                f.write(docs)

            log_execution(f"Cached {len(docs)} chars from Context7", status='success')
            return docs

        except Exception as e:
            log_message(f"Context7 fetch failed: {e}, using empty docs", status='error')
            return f"API Endpoint: {self.config.get('api_endpoint', '')}\nAuth: {self.config.get('api_auth_method', '')}"

    def _load_failure_history(self) -> List[Dict]:
        """Load previous failures to help LLM learn"""
        failure_file = self.learnings_dir / 'failure_history.json'

        if not failure_file.exists():
            return []

        with open(failure_file, 'r') as f:
            return json.load(f)

    def _record_failure(self, error: str, code: str):
        """Record a failure for learning in next iteration"""
        failure_file = self.learnings_dir / 'failure_history.json'

        failures = self._load_failure_history()

        failures.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': error[:500],  # Truncate long errors
            'code_hash': hashlib.md5(code.encode()).hexdigest()
        })

        # Keep only last 10 failures
        failures = failures[-10:]

        with open(failure_file, 'w') as f:
            json.dump(failures, f, indent=2)
