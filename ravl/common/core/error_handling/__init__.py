"""
Error handling and analysis for RAVL framework

Provides:
- Semantic error analysis (extract error categories from stderr)
- Error recovery strategies
- Failure pattern recognition
"""

from .error_semantic_analyzer import ErrorSemanticAnalyzer, ErrorHint

__all__ = ['ErrorSemanticAnalyzer', 'ErrorHint']
