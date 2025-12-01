"""
Unit tests for path detection with correct ravl_loops/ marker.

Tests cover:
- Finding project by ravl_loops/ directory
- UV vs submodule installation type detection
- Config path resolution for both install types
- Required vs optional project detection
"""

import pytest
from pathlib import Path
from ravl.common.cli.ravl_cli_base import RAVLCLIBase


class TestPathDetection:
    """Test path detection with correct ravl_loops/ marker."""

    def test_find_project_with_ravl_loops(self, tmp_path):
        """Test finding project by ravl_loops/ directory."""
        # Create project structure
        ravl_loops = tmp_path / 'ravl_loops'
        ravl_loops.mkdir()

        # Create nested directory structure
        nested = tmp_path / 'a' / 'b' / 'c'
        nested.mkdir(parents=True)

        # Should find project root from nested directory
        result = RAVLCLIBase.find_project_root(start_path=nested, required=False)
        assert result == tmp_path

    def test_find_project_no_ravl_loops_fallback(self, tmp_path):
        """Test fallback when no ravl_loops/ found and required=False."""
        nested = tmp_path / 'some' / 'dir'
        nested.mkdir(parents=True)

        result = RAVLCLIBase.find_project_root(
            start_path=nested,
            required=False
        )
        # Should return the start path (or cwd if start_path not provided)
        assert result == nested.resolve()

    def test_find_project_required_fails(self, tmp_path):
        """Test error when required=True and no project found."""
        with pytest.raises(RuntimeError, match="no ravl_loops/ directory"):
            RAVLCLIBase.find_project_root(
                start_path=tmp_path,
                required=True
            )

    def test_find_project_multiple_levels(self, tmp_path):
        """Test finding project through multiple directory levels."""
        # Create ravl_loops at root
        (tmp_path / 'ravl_loops').mkdir()

        # Create deeply nested structure
        deep = tmp_path / 'a' / 'b' / 'c' / 'd' / 'e'
        deep.mkdir(parents=True)

        # Should find project root from deep nesting
        result = RAVLCLIBase.find_project_root(start_path=deep, required=True)
        assert result == tmp_path

    def test_find_project_ignores_git_directory(self, tmp_path):
        """Test that .git directory is NOT used as project marker."""
        # Create .git directory (version control marker)
        (tmp_path / '.git').mkdir()

        # No ravl_loops/ directory
        # Should NOT find project based on .git/
        with pytest.raises(RuntimeError, match="no ravl_loops/ directory"):
            RAVLCLIBase.find_project_root(
                start_path=tmp_path,
                required=True
            )

    def test_find_project_ignores_ravl_directory(self, tmp_path):
        """Test that .ravl/ directory is NOT used as project marker."""
        # Create .ravl directory (submodule convention)
        (tmp_path / '.ravl').mkdir()

        # No ravl_loops/ directory
        # Should NOT find project based on .ravl/
        with pytest.raises(RuntimeError, match="no ravl_loops/ directory"):
            RAVLCLIBase.find_project_root(
                start_path=tmp_path,
                required=True
            )

    def test_installation_type_detection(self):
        """Test detecting UV vs submodule install."""
        install_type = RAVLCLIBase.get_installation_type()
        assert install_type in ['package', 'submodule']

    def test_config_path_exists_or_parent_exists(self):
        """Test config path is valid (file or parent directory exists)."""
        config_path = RAVLCLIBase.get_config_path()
        # Config file might not exist yet, but parent directory should
        assert config_path.parent.exists() or config_path.exists()

    def test_config_path_submodule_uses_ravl_dir(self, tmp_path, monkeypatch):
        """Test that submodule install uses .ravl/config.toml if available."""
        # Create project structure with .ravl submodule
        (tmp_path / 'ravl_loops').mkdir()
        (tmp_path / '.ravl').mkdir()

        # Mock get_installation_type to return 'submodule'
        monkeypatch.setattr(
            RAVLCLIBase,
            'get_installation_type',
            lambda: 'submodule'
        )

        # Mock find_project_root to return tmp_path
        monkeypatch.setattr(
            RAVLCLIBase,
            'find_project_root',
            lambda required=True: tmp_path
        )

        config_path = RAVLCLIBase.get_config_path()
        # Should use .ravl/config.toml for submodule install
        assert config_path == tmp_path / '.ravl' / 'config.toml'

    def test_config_path_package_uses_home_config(self, monkeypatch):
        """Test that UV/pip install uses ~/.config/ravl/config.toml."""
        # Mock get_installation_type to return 'package'
        monkeypatch.setattr(
            RAVLCLIBase,
            'get_installation_type',
            lambda: 'package'
        )

        config_path = RAVLCLIBase.get_config_path()
        # Should use ~/.config/ravl/config.toml for package install
        assert '.config' in str(config_path)
        assert 'ravl' in str(config_path)
        assert config_path.name == 'config.toml'

    def test_find_framework_root_returns_path(self):
        """Test that find_framework_root returns a valid Path."""
        framework_root = RAVLCLIBase.find_framework_root()
        assert isinstance(framework_root, Path)
        assert framework_root.exists()


class TestPathDetectionEdgeCases:
    """Test edge cases and error conditions."""

    def test_find_project_from_root_directory(self):
        """Test behavior when starting from filesystem root."""
        # Starting from root should not crash
        root = Path('/')
        result = RAVLCLIBase.find_project_root(start_path=root, required=False)
        # Should return root or cwd as fallback
        assert isinstance(result, Path)

    def test_find_project_with_symlinks(self, tmp_path):
        """Test project detection works through symlinks."""
        # Create project structure
        (tmp_path / 'ravl_loops').mkdir()

        # Create symlink to nested directory
        (tmp_path / 'nested').mkdir()
        symlink = tmp_path / 'nested' / 'link'
        try:
            symlink.symlink_to(tmp_path)
            # Should resolve symlinks and find project
            result = RAVLCLIBase.find_project_root(
                start_path=symlink,
                required=False
            )
            # Should find project root through symlink
            assert result == tmp_path.resolve() or result == symlink.resolve()
        except OSError:
            # Skip test if symlinks not supported (e.g., Windows without permissions)
            pytest.skip("Symlinks not supported on this system")

    def test_find_project_with_multiple_ravl_loops_finds_nearest(self, tmp_path):
        """Test that nearest ravl_loops/ directory is found."""
        # Create outer project
        (tmp_path / 'ravl_loops').mkdir()

        # Create nested project
        nested = tmp_path / 'nested' / 'project'
        nested.mkdir(parents=True)
        (nested / 'ravl_loops').mkdir()

        # Create directory inside nested project
        deep = nested / 'some' / 'dir'
        deep.mkdir(parents=True)

        # Should find nearest ravl_loops/ (nested, not outer)
        result = RAVLCLIBase.find_project_root(start_path=deep, required=True)
        assert result == nested
