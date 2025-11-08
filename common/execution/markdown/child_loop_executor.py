#!/usr/bin/env python3
"""
Child Loop Executor

Handles execution of child loops and creation of additional outputs.
Manages ```run_child directive processing and output generation.
"""

import re
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, Tuple, Any, Optional


class ChildLoopExecutor:
    """
    Handles execution of child loops

    Responsibilities:
    - Process run_child directives in Act markdown
    - Execute referenced child loops
    - Aggregate child results
    - Create additional outputs from verification criteria
    """

    def __init__(self, loop_dir: Path, learnings_dir: Path):
        """
        Initialize child loop executor

        Args:
            loop_dir: Path to the parent loop directory
            learnings_dir: Path to learnings directory
        """
        self.loop_dir = loop_dir
        self.learnings_dir = learnings_dir

    def process_run_child_directives(self, act_instructions: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process run_child directives in Act markdown

        Finds ```run_child blocks, executes those child loops, and replaces
        the blocks with execution summaries.

        Args:
            act_instructions: Raw Act markdown

        Returns:
            Tuple of (processed_markdown, child_results_dict)
        """
        child_results = {}
        processed_instructions = act_instructions

        # Pattern to match ```run_child ... ``` blocks
        pattern = r'```run_child\s*\n([^\n]+)\n```'
        matches = list(re.finditer(pattern, act_instructions))

        if not matches:
            return act_instructions, child_results

        # Process each run_child directive
        for match in matches:
            full_match = match.group(0)
            child_command = match.group(1).strip()

            # Parse command: "loop_name --arg value"
            parts = child_command.split()
            child_name = parts[0]
            child_args = parts[1:] if len(parts) > 1 else []

            print(f"\n  ▶️  Running child loop: {child_name}", file=sys.stderr)

            # Find child loop directory
            child_dir = self.loop_dir / 'ravl_loops' / child_name

            if not child_dir.exists():
                error_msg = f"Child loop not found: {child_name} at {child_dir}"
                print(f"  ⚠️  {error_msg}", file=sys.stderr)
                replacement = f"**Error:** {error_msg}"
                processed_instructions = processed_instructions.replace(full_match, replacement)
                continue

            # Execute child loop using the universal ravl runner
            project_root = self.loop_dir
            while project_root.parent != project_root:
                if (project_root / '.ravl').exists():
                    break
                project_root = project_root.parent

            ravl_cmd = [str(project_root / '.ravl' / 'bin' / 'ravl'), child_name] + child_args

            try:
                result = subprocess.run(
                    ravl_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(project_root)
                )

                # Parse result
                child_output = result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
                child_results[child_name] = {
                    'success': result.returncode == 0,
                    'output': child_output[:500],  # Truncate for readability
                    'exit_code': result.returncode
                }

                # Replace directive with result summary
                result_summary = f"✓ {child_name} executed successfully" if result.returncode == 0 else f"✗ {child_name} failed"
                processed_instructions = processed_instructions.replace(full_match, result_summary)

                print(f"  [{'✓' if result.returncode == 0 else '✗'}] {child_name}: {result_summary}", file=sys.stderr)

            except subprocess.TimeoutExpired:
                error_msg = f"Child loop {child_name} execution timed out"
                print(f"  ✗ {error_msg}", file=sys.stderr)
                child_results[child_name] = {'success': False, 'error': 'timeout'}
                replacement = f"**Error:** {error_msg}"
                processed_instructions = processed_instructions.replace(full_match, replacement)

            except Exception as e:
                error_msg = f"Child loop execution failed: {str(e)[:100]}"
                print(f"  ✗ {error_msg}", file=sys.stderr)
                child_results[child_name] = {'success': False, 'error': str(e)[:100]}
                replacement = f"**Error:** {error_msg}"
                processed_instructions = processed_instructions.replace(full_match, replacement)

        return processed_instructions, child_results

    def create_additional_outputs(
        self,
        llm_response: str,
        verify_criteria: str,
        timestamp: str
    ) -> Optional[Dict[str, str]]:
        """
        Create additional file outputs based on verification criteria

        If verify section specifies additional outputs, create and save them.

        Args:
            llm_response: LLM-generated response content
            verify_criteria: Verification criteria from markdown
            timestamp: Timestamp for output files

        Returns:
            Dictionary mapping filename to output file path, or None
        """
        # Check if verification criteria asks for specific output files
        # Pattern: "Create file: filename" or "Output to: filename.ext"
        patterns = [
            r'[Cc]reate file[:\s]+([^\n]+)',
            r'[Oo]utput to[:\s]+([^\n]+)',
            r'[Ss]ave.*as[:\s]+([^\n]+)',
        ]

        additional_files = {}

        for pattern in patterns:
            matches = re.findall(pattern, verify_criteria)
            for filename_match in matches:
                filename = filename_match.strip()
                if not filename:
                    continue

                # Create output file
                try:
                    output_file = self.learnings_dir / f'{filename}_{timestamp}'
                    with open(output_file, 'w', encoding='utf-8') as f:
                        # Write relevant portion of LLM response
                        # Extract JSON or structured content if present
                        if filename.endswith('.json'):
                            try:
                                # Try to extract JSON from response
                                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                                if json_match:
                                    f.write(json_match.group(0))
                                else:
                                    f.write(llm_response)
                            except:
                                f.write(llm_response)
                        else:
                            f.write(llm_response)

                    additional_files[filename] = str(output_file.name)
                    print(f"  [✓] Created additional output: {output_file.name}", file=sys.stderr)

                except Exception as e:
                    print(f"  [i] Failed to create output file {filename}: {str(e)[:100]}", file=sys.stderr)

        return additional_files if additional_files else None
