"""Tests for PluginRunner CLI interface."""

import os
from unittest.mock import Mock, patch

from spaceforge.runner import runner_command


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
