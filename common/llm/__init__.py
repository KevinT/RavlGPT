"""
LLM Module - Backward Compatibility Layer

DEPRECATED: This module structure is being reorganized for clarity.

Files have been moved to their appropriate locations:
- llm_providers.py -> stays here (LLM provider abstraction)
- llm_logger.py -> stays here (LLM logging)
- learning_manager.py -> moved to core/learning/
- error_semantic_analyzer.py -> moved to core/error_handling/
- schema_adapters.py -> moved to core/verification/
- credential_validator.py -> moved to integrations/
- dsl_inference_engine.py -> moved to execution/code/
- code_generator.py -> moved to execution/code/
- code_cache_manager.py -> moved to execution/code/
- data_ingress_executor.py -> moved to execution/code/
- markdown_ravl_executor.py -> moved to execution/markdown/
- markdown_parser.py -> moved to execution/markdown/
- loop_context_builder.py -> moved to execution/markdown/
- child_loop_executor.py -> moved to execution/markdown/
- migrate_learning_files.py -> moved to integrations/
- google_apis_mixin.py -> moved to integrations/

This __init__.py provides backward compatibility by re-exporting from new locations.
Old imports like "from llm.learning_manager import LearningManager" will continue to work.
"""

import sys
from pathlib import Path

# Add paths for cross-module imports
_llm_dir = Path(__file__).parent
_common_dir = _llm_dir.parent
_core_dir = _common_dir / 'core'
_exec_dir = _common_dir / 'execution'
_integ_dir = _common_dir / 'integrations'

sys.path.insert(0, str(_common_dir))
sys.path.insert(0, str(_core_dir))
sys.path.insert(0, str(_exec_dir))
sys.path.insert(0, str(_integ_dir))

# Re-export from new locations for backward compatibility
try:
    from learning_manager import LearningManager
    from core.learning import LearningManager  # Try direct import
except (ImportError, ModuleNotFoundError):
    LearningManager = None

try:
    from error_semantic_analyzer import ErrorSemanticAnalyzer, ErrorHint
except (ImportError, ModuleNotFoundError):
    try:
        from core.error_handling import ErrorSemanticAnalyzer, ErrorHint
    except (ImportError, ModuleNotFoundError):
        ErrorSemanticAnalyzer = None
        ErrorHint = None

try:
    from schema_adapters import schema_adapters
except (ImportError, ModuleNotFoundError):
    try:
        from core.verification import schema_adapters
    except (ImportError, ModuleNotFoundError):
        schema_adapters = None

try:
    from code_generator import CodeGenerator
    from code_cache_manager import CodeCacheManager
    from dsl_inference_engine import DSLInferenceEngine
    from data_ingress_executor import DataIngressExecutor
except (ImportError, ModuleNotFoundError):
    try:
        from execution.code import (
            CodeGenerator,
            CodeCacheManager,
            DSLInferenceEngine,
            DataIngressExecutor,
        )
    except (ImportError, ModuleNotFoundError):
        CodeGenerator = None
        CodeCacheManager = None
        DSLInferenceEngine = None
        DataIngressExecutor = None

try:
    from markdown_parser import MarkdownParser
    from markdown_ravl_executor import MarkdownRAVLExecutor
    from loop_context_builder import LoopContextBuilder
    from child_loop_executor import ChildLoopExecutor
except (ImportError, ModuleNotFoundError):
    try:
        from execution.markdown import (
            MarkdownParser,
            MarkdownRAVLExecutor,
            LoopContextBuilder,
            ChildLoopExecutor,
        )
    except (ImportError, ModuleNotFoundError):
        MarkdownParser = None
        MarkdownRAVLExecutor = None
        LoopContextBuilder = None
        ChildLoopExecutor = None

try:
    from credential_validator import CredentialValidator
except (ImportError, ModuleNotFoundError):
    try:
        from integrations import CredentialValidator
    except (ImportError, ModuleNotFoundError):
        CredentialValidator = None

# Items that stay in llm/
try:
    from llm_providers import LLMProviderFactory, LLMProvider
except (ImportError, ModuleNotFoundError):
    LLMProviderFactory = None
    LLMProvider = None

try:
    from llm_logger import log_llm_call
except (ImportError, ModuleNotFoundError):
    log_llm_call = None

__all__ = [
    # Core
    'LearningManager',
    'ErrorSemanticAnalyzer',
    'ErrorHint',
    'schema_adapters',
    # Execution
    'CodeGenerator',
    'CodeCacheManager',
    'DSLInferenceEngine',
    'DataIngressExecutor',
    'MarkdownParser',
    'MarkdownRAVLExecutor',
    'LoopContextBuilder',
    'ChildLoopExecutor',
    # Integrations
    'CredentialValidator',
    # LLM
    'LLMProviderFactory',
    'LLMProvider',
    'log_llm_call',
]
