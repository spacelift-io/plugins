"""Tests for PluginRunner hook execution functionality."""

import os
from unittest.mock import Mock, patch

import pytest

from spaceforge.runner import PluginRunner


class TestPluginRunnerExecution:
    """Test hook execution functionality."""

    def test_should_load_plugin_automatically_when_not_already_loaded(
        self, test_plugin_file: str
    ) -> None:
        """Should call load_plugin when plugin_instance is None."""
        # Arrange
        runner = PluginRunner(test_plugin_file)

        # Act
        with patch.object(runner, "load_plugin") as mock_load:
            mock_instance = Mock()
            mock_instance.after_plan = Mock()
            runner.plugin_instance = None
            runner.run_hook("after_plan")

        # Assert
        mock_load.assert_called_once()

    def test_should_execute_hook_and_log_success_when_hook_exists(
        self, temp_dir: str
    ) -> None:
        """Should successfully execute hook method and log completion."""
        # Arrange
        runner_plugin_path = os.path.join(temp_dir, "runner_plugin.py")
        with open(runner_plugin_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin

class TestRunnerPlugin(SpaceforgePlugin):
    def __init__(self):
        super().__init__()
        self.executed_hooks = []
    
    def after_plan(self):
        self.executed_hooks.append('after_plan')
"""
            )

        runner = PluginRunner(runner_plugin_path)
        runner.load_plugin()

        # Act
        with patch("builtins.print") as mock_print:
            runner.run_hook("after_plan")

        # Assert
        assert runner.plugin_instance is not None
        assert hasattr(runner.plugin_instance, "executed_hooks")
        assert "after_plan" in getattr(runner.plugin_instance, "executed_hooks")

        mock_print.assert_any_call("[SpaceForge] Running hook: after_plan")
        mock_print.assert_any_call("[SpaceForge] Hook completed: after_plan")

    def test_should_print_error_when_hook_method_not_found(
        self, test_plugin_file: str
    ) -> None:
        """Should print error message when hook method doesn't exist."""
        # Arrange
        runner = PluginRunner(test_plugin_file)
        runner.load_plugin()

        # Act
        with patch("builtins.print") as mock_print:
            runner.run_hook("nonexistent_hook")

        # Assert
        mock_print.assert_called_with(
            "Hook method 'nonexistent_hook' not found in plugin"
        )

    def test_should_print_error_when_hook_exists_but_not_callable(
        self, test_plugin_file: str
    ) -> None:
        """Should print error when hook attribute exists but is not callable."""
        # Arrange
        runner = PluginRunner(test_plugin_file)
        runner.load_plugin()

        assert runner.plugin_instance is not None
        setattr(runner.plugin_instance, "not_callable", "not a method")

        # Act
        with patch("builtins.print") as mock_print:
            runner.run_hook("not_callable")

        # Assert
        mock_print.assert_called_with("'not_callable' is not a callable method")

    def test_should_print_error_and_reraise_when_hook_execution_fails(
        self, temp_dir: str
    ) -> None:
        """Should print error and re-raise exception when hook execution fails."""
        # Arrange
        error_plugin_path = os.path.join(temp_dir, "error_plugin.py")
        with open(error_plugin_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin

class ErrorPlugin(SpaceforgePlugin):
    def error_hook(self):
        raise ValueError("Test error from hook")
"""
            )

        runner = PluginRunner(error_plugin_path)
        runner.load_plugin()

        # Act & Assert
        with patch("builtins.print") as mock_print:
            with pytest.raises(ValueError, match="Test error from hook"):
                runner.run_hook("error_hook")

        mock_print.assert_any_call(
            "[SpaceForge] Error running hook 'error_hook': Test error from hook"
        )

    def test_should_execute_multiple_hooks_maintaining_state(
        self, temp_dir: str
    ) -> None:
        """Should execute multiple hooks while maintaining plugin instance state."""
        # Arrange
        multi_hook_path = os.path.join(temp_dir, "multi_hook.py")
        with open(multi_hook_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin

class MultiHookPlugin(SpaceforgePlugin):
    def __init__(self):
        super().__init__()
        self.executed_hooks = []
    
    def after_plan(self):
        self.executed_hooks.append('after_plan')
        
    def before_apply(self):
        self.executed_hooks.append('before_apply')
"""
            )

        runner = PluginRunner(multi_hook_path)
        runner.load_plugin()

        # Act
        with patch("builtins.print"):
            runner.run_hook("after_plan")
            runner.run_hook("before_apply")

        # Assert
        assert runner.plugin_instance is not None
        assert hasattr(runner.plugin_instance, "executed_hooks")
        executed = getattr(runner.plugin_instance, "executed_hooks")
        assert "after_plan" in executed
        assert "before_apply" in executed
        assert len(executed) == 2
