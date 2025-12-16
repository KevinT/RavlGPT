"""
Test virtual environment path resolution across installation modes.

Tests ensure that:
1. Submodule mode defaults to .ravl/venv
2. UV/package mode defaults to .venv at project root
3. Priority chain is respected (CLI > config > env var > default)
4. Explicit config overrides installation type
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from ravl.common.ravl_runner import RAVLRunner
from ravl.common.cli.ravl_cli_base import RAVLCLIBase


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()
    (project_root / 'ravl_loops').mkdir()
    (project_root / '.ravl').mkdir(exist_ok=True)
    return project_root


def test_submodule_default_uses_ravl_venv(temp_project):
    """Submodule installation should use .ravl/venv by default."""
    with patch('ravl.common.ravl_runner.RAVLCLIBase.get_installation_type', return_value='submodule'):
        result = RAVLRunner.resolve_venv_path(
            loop_dir=temp_project / 'ravl_loops',
            project_root=temp_project
        )

        assert result == (temp_project / '.ravl' / 'venv').resolve()


def test_uv_default_uses_project_venv(temp_project):
    """UV/package installation should use .venv at project root by default."""
    with patch('ravl.common.ravl_runner.RAVLCLIBase.get_installation_type', return_value='package'):
        result = RAVLRunner.resolve_venv_path(
            loop_dir=temp_project / 'ravl_loops',
            project_root=temp_project
        )

        assert result == (temp_project / '.venv').resolve()


def test_cli_flag_overrides_installation_type(temp_project):
    """Explicit cli_venv_path parameter should override installation type detection."""
    custom_venv = temp_project / 'custom_venv'

    # Even in UV mode, explicit cli_venv_path should win
    with patch('ravl.common.ravl_runner.RAVLCLIBase.get_installation_type', return_value='package'):
        result = RAVLRunner.resolve_venv_path(
            loop_dir=temp_project / 'ravl_loops',
            project_root=temp_project,
            cli_venv_path=custom_venv
        )

        assert result == custom_venv.resolve()


def test_loop_config_overrides_default(temp_project, monkeypatch):
    """Loop config venv_path should override installation type default."""
    custom_venv = temp_project / 'loop_custom_venv'

    # Mock loop config to return custom venv path
    mock_config = {'venv_path': str(custom_venv)}

    with patch('ravl.common.ravl_runner.RAVLCLIBase.get_installation_type', return_value='package'):
        result = RAVLRunner.resolve_venv_path(
            loop_dir=temp_project / 'ravl_loops',
            project_root=temp_project,
            loop_config=mock_config
        )

        assert result == custom_venv.resolve()


def test_env_var_overrides_default(temp_project, monkeypatch):
    """RAVL_DEFAULT_VENV_DIRECTORY env var should override installation type default."""
    custom_venv = temp_project / 'env_custom_venv'

    # Mock .env file loading
    def mock_load_env(project_root):
        return {'RAVL_DEFAULT_VENV_DIRECTORY': str(custom_venv)}

    with patch('ravl.common.ravl_runner.RAVLCLIBase.get_installation_type', return_value='package'), \
         patch('ravl.common.ravl_runner.RAVLRunner.load_env_file', side_effect=mock_load_env):
        result = RAVLRunner.resolve_venv_path(
            loop_dir=temp_project / 'ravl_loops',
            project_root=temp_project
        )

        assert result == custom_venv.resolve()


def test_priority_chain_order(temp_project):
    """Test that priority chain is respected: CLI > loop config > project config > env > default."""
    cli_venv = temp_project / 'cli_venv'
    loop_venv = temp_project / 'loop_venv'

    # CLI flag should win even if loop config is set
    with patch('ravl.common.ravl_runner.RAVLCLIBase.get_installation_type', return_value='package'):
        result = RAVLRunner.resolve_venv_path(
            loop_dir=temp_project / 'ravl_loops',
            project_root=temp_project,
            cli_venv_path=cli_venv,
            loop_config={'venv_path': str(loop_venv)}
        )

        assert result == cli_venv.resolve()


def test_submodule_without_project_root(temp_project):
    """Submodule mode should find project root when not provided."""
    with patch('ravl.common.ravl_runner.RAVLCLIBase.get_installation_type', return_value='submodule'), \
         patch('ravl.common.ravl_runner.RAVLCLIBase.find_project_root', return_value=temp_project):
        result = RAVLRunner.resolve_venv_path(
            loop_dir=temp_project / 'ravl_loops'
            # No project_root provided
        )

        assert result == (temp_project / '.ravl' / 'venv').resolve()


def test_uv_without_project_root(temp_project):
    """UV mode should find project root when not provided."""
    with patch('ravl.common.ravl_runner.RAVLCLIBase.get_installation_type', return_value='package'), \
         patch('ravl.common.ravl_runner.RAVLCLIBase.find_project_root', return_value=temp_project):
        result = RAVLRunner.resolve_venv_path(
            loop_dir=temp_project / 'ravl_loops'
            # No project_root provided
        )

        assert result == (temp_project / '.venv').resolve()


def test_backward_compatibility_with_explicit_config(temp_project):
    """Existing projects with explicit venv config should continue working."""
    # Simulate project that has explicitly configured venv path
    explicit_venv = temp_project / 'my_custom_venv'

    # Should use explicit config regardless of installation type
    with patch('ravl.common.ravl_runner.RAVLCLIBase.get_installation_type', return_value='package'):
        result = RAVLRunner.resolve_venv_path(
            loop_dir=temp_project / 'ravl_loops',
            project_root=temp_project,
            loop_config={'venv_path': str(explicit_venv)}
        )

        assert result == explicit_venv.resolve()
