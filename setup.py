"""
Setup script for RAVL Framework

Makes the framework pip-installable so generated code can import
ravl.common.llm and other utilities.

Install in editable mode:
    pip install -e /path/to/.ravl
"""

from setuptools import setup, find_packages

setup(
    name="ravl-framework",
    version="0.1.0",
    description="RAVL (Reflect-Act-Verify-Learn) autonomous agent framework",

    # Include common.* packages (common.llm, common.core, etc.)
    # Generated code will import as: from common.llm.llm_logger import log_llm_call
    packages=find_packages(include=["common", "common.*"]),

    python_requires=">=3.8",

    # Minimal dependencies - only what llm_logger needs
    install_requires=[
        # LLM logger has no external dependencies - just uses stdlib
    ],

    # Optional dependencies for LLM providers (not required for logger)
    extras_require={
        "llm": [
            "anthropic>=0.39.0",
            "openai>=1.0.0",
            "google-generativeai>=0.3.0",
            "requests>=2.31.0",
        ],
        "google": [
            "google-api-python-client>=2.0.0",
            "google-auth>=2.0.0",
        ],
    },

    # Include package data
    include_package_data=True,

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
