"""Constants for RAVL framework

Centralizes magic numbers and hardcoded values for easier maintenance.
"""

# Execution timeouts (in seconds)
DEFAULT_EXECUTION_TIMEOUT = 300  # 5 minutes
CODE_EXECUTION_TIMEOUT = 300  # 5 minute
CHILD_LOOP_TIMEOUT = 300  # 5 minutes

# File content limits
MAX_FILE_CONTENT_LENGTH = 50000  # Characters to keep when truncating files
PREVIEW_OUTPUT_LENGTH = 500  # Characters to show in output preview

# Model versioning
VERSION_INCREMENT = 0.1

# Cache settings
CONTEXT_DOCUMENTATION_CACHE_TTL = 7 * 24 * 60 * 60  # 1 week in seconds

# Learning and DSL settings
LLAMA_INDEX_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # 1 week
DEFAULT_SUGGEST_ITERATIONS = 10

# Child loop discovery
CHILD_LOOP_BATCH_SIZE = 5

# Learnings file paths (relative to learnings directory)
LEARNINGS_FILES = {
    'verified_code': 'verified_code.py',
    'verified_dsl': 'verified_dsl.json',
    'failure_analysis': 'history/failure_analysis.jsonl',
    'interpreted_loop': 'interpreted_ravl_loop.md',
    'model': 'model.yml',
    'latest_run': 'latest_run.json',
}

# Logging settings
LOG_INDENT_BASE = 2
LOG_INDENT_ERROR = 6

# Path patterns for model discovery
MODEL_PATTERN = 'model-*.yml'
TIMESTAMPED_FILE_PATTERN = '*-*.json'
