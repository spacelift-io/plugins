"""Tests for PluginRunner CLI interface."""

import os
import sys
from unittest.mock import Mock, patch

import pytest

from spaceforge.runner import main, runner_command


class TestRunnerClickCommand:
    """Test Click command interface."""

    def test_should_execute_hook_via_click_command(self, temp_dir: str) -> None:
        """Should execute hook through Click command interface."""
        # Arrange
        click_plugin_path = os.path.join(temp_dir, "click_plugin.py")
        with open(click_plugin_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin

class ClickTestPlugin(SpaceforgePlugin):
    def after_plan(self):
        print("Hook executed via click")
"""
            )

        # Act
        from click.testing import CliRunner

        cli_runner = CliRunner()

        with patch("spaceforge.runner.PluginRunner") as mock_runner_class:
            mock_runner = Mock()
            mock_runner_class.return_value = mock_runner

            result = cli_runner.invoke(
                runner_command, ["after_plan", "--plugin-file", click_plugin_path]
            )

        # Assert
        assert result.exit_code == 0
        mock_runner_class.assert_called_once_with(click_plugin_path)
        mock_runner.run_hook.assert_called_once_with("after_plan")

    def test_should_use_custom_plugin_file_when_specified(self, temp_dir: str) -> None:
        """Should use specified plugin file path instead of default."""
        # Arrange
        custom_plugin_path = os.path.join(temp_dir, "custom_plugin.py")
        # Create the file since Click validates existence
        with open(custom_plugin_path, "w") as f:
            f.write("# dummy plugin file for testing")

        # Act
        from click.testing import CliRunner

        cli_runner = CliRunner()

        with patch("spaceforge.runner.PluginRunner") as mock_runner_class:
            mock_runner = Mock()
            mock_runner_class.return_value = mock_runner

            result = cli_runner.invoke(
                runner_command, ["before_apply", "--plugin-file", custom_plugin_path]
            )

        # Assert
        assert result.exit_code == 0
        mock_runner_class.assert_called_once_with(custom_plugin_path)
        mock_runner.run_hook.assert_called_once_with("before_apply")


class TestLegacyMainFunction:
    """Test legacy main function compatibility."""

    @patch("spaceforge.runner.PluginRunner")
    @patch("builtins.print")
    def test_should_exit_with_usage_when_insufficient_args(
        self, mock_print: Mock, mock_runner_class: Mock
    ) -> None:
        """Should print usage and exit when no hook name provided."""
        # Arrange
        original_argv = sys.argv

        # Act & Assert
        try:
            sys.argv = ["runner.py"]  # Missing hook_name

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            mock_print.assert_called_with(
                "Usage: python -m spaceforge.runner <hook_name>"
            )
            mock_runner_class.assert_not_called()

        finally:
            sys.argv = original_argv

    @patch("spaceforge.runner.PluginRunner")
    @patch("builtins.print")
    def test_should_exit_with_usage_when_too_many_args(
        self, mock_print: Mock, mock_runner_class: Mock
    ) -> None:
        """Should print usage and exit when too many arguments provided."""
        # Arrange
        original_argv = sys.argv

        # Act & Assert
        try:
            sys.argv = ["runner.py", "after_plan", "extra_arg"]

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            mock_print.assert_called_with(
                "Usage: python -m spaceforge.runner <hook_name>"
            )
            mock_runner_class.assert_not_called()

        finally:
            sys.argv = original_argv

    @patch("spaceforge.runner.PluginRunner")
    def test_should_execute_hook_when_valid_args_provided(
        self, mock_runner_class: Mock
    ) -> None:
        """Should execute hook when correct number of arguments provided."""
        # Arrange
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner
        original_argv = sys.argv

        # Act
        try:
            sys.argv = ["runner.py", "after_plan"]
            main()

        finally:
            sys.argv = original_argv

        # Assert
        mock_runner_class.assert_called_once_with()
        mock_runner.run_hook.assert_called_once_with("after_plan")
