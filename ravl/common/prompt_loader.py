"""
Utility for loading and formatting LLM prompts from external files
"""

import os
from pathlib import Path
from typing import Dict, Any


class PromptLoader:
    """Loads and formats prompts from text files"""

    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            # Default to prompts directory relative to this file
            self.prompts_dir = Path(__file__).parent / 'prompts'
        else:
            self.prompts_dir = Path(prompts_dir)

    def load_prompt(self, prompt_name: str, **kwargs: Any) -> str:
        """
        Load a prompt template from file and format with provided kwargs

        Args:
            prompt_name: Name of the prompt file (without .md extension)
            **kwargs: Variables to substitute in the prompt template

        Returns:
            Formatted prompt string

        Example:
            loader = PromptLoader()
            prompt = loader.load_prompt('prompt_coherence_analysis',
                                       context="...",
                                       file_summaries="...")
        """
        prompt_path = self.prompts_dir / f"{prompt_name}.md"

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()

        # Format the template with provided kwargs
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required prompt variable: {e}")

    def list_prompts(self) -> list:
        """List all available prompt templates"""
        if not self.prompts_dir.exists():
            return []

        return [
            p.stem for p in self.prompts_dir.glob('*.md')
        ]