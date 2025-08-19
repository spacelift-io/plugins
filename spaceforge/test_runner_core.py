"""Tests for PluginRunner core functionality."""

import os
from typing import List
from unittest.mock import Mock, patch

import pytest

from spaceforge.plugin import SpaceforgePlugin
from spaceforge.runner import PluginRunner


class RunnerTestPlugin(SpaceforgePlugin):
    """Reusable test plugin for runner tests."""

    def __init__(self) -> None:
        super().__init__()
        self.executed_hooks: List[str] = []

    def after_plan(self) -> None:
        self.executed_hooks.append("after_plan")

    def before_apply(self) -> None:
        self.executed_hooks.append("before_apply")

    def error_hook(self) -> None:
        raise ValueError("Test error from hook")


class TestPluginRunnerInitialization:
    """Test PluginRunner initialization and configuration."""

    def test_should_initialize_with_custom_plugin_path(self) -> None:
        """Should accept and store custom plugin file path."""
        # Arrange & Act
        runner = PluginRunner("custom_plugin.py")

        # Assert
        assert runner.plugin_path == "custom_plugin.py"
        assert runner.plugin_instance is None

    def test_should_use_default_plugin_path_when_none_provided(self) -> None:
        """Should use 'plugin.py' as default when no path specified."""
        # Arrange & Act
        runner = PluginRunner()

        # Assert
        assert runner.plugin_path == "plugin.py"
        assert runner.plugin_instance is None


class TestPluginRunnerLoading:
    """Test plugin loading functionality."""

    def test_should_raise_file_not_found_when_plugin_file_missing(self) -> None:
        """Should raise FileNotFoundError when plugin file doesn't exist."""
        # Arrange
        runner = PluginRunner("nonexistent.py")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Plugin file not found"):
            runner.load_plugin()

    def test_should_raise_exception_when_plugin_file_has_syntax_errors(
        self, temp_dir: str
    ) -> None:
        """Should raise exception when plugin file has invalid Python syntax."""
        # Arrange
        invalid_path = os.path.join(temp_dir, "invalid.py")
        with open(invalid_path, "w") as f:
            f.write("invalid python syntax }")

        runner = PluginRunner(invalid_path)

        # Act & Assert
        with pytest.raises(Exception):  # Could be syntax error
            runner.load_plugin()

    def test_should_raise_value_error_when_no_spaceforge_plugin_found(
        self, temp_dir: str
    ) -> None:
        """Should raise ValueError when file has no SpaceforgePlugin subclass."""
        # Arrange
        no_plugin_path = os.path.join(temp_dir, "no_plugin.py")
        with open(no_plugin_path, "w") as f:
            f.write(
                """
class NotAPlugin:
    pass
"""
            )

        runner = PluginRunner(no_plugin_path)

        # Act & Assert
        with pytest.raises(ValueError, match="No SpaceforgePlugin subclass found"):
            runner.load_plugin()

    def test_should_load_plugin_successfully_when_valid_file_provided(
        self, test_plugin_file: str
    ) -> None:
        """Should successfully load plugin from valid file."""
        # Arrange
        runner = PluginRunner(test_plugin_file)

        # Act
        runner.load_plugin()

        # Assert
        assert runner.plugin_instance is not None
        assert runner.plugin_instance.__class__.__name__ == "TestPlugin"

    @patch("spaceforge.runner.importlib.util.spec_from_file_location")
    def test_should_raise_import_error_when_spec_is_none(
        self, mock_spec: Mock, test_plugin_file: str
    ) -> None:
        """Should raise ImportError when importlib spec creation fails."""
        # Arrange
        mock_spec.return_value = None
        runner = PluginRunner(test_plugin_file)

        # Act & Assert
        with pytest.raises(ImportError, match="Could not load plugin"):
            runner.load_plugin()
