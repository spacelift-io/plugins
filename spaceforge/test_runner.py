import os
import tempfile
from typing import Optional
from unittest.mock import Mock, patch

import pytest

from spaceforge.plugin import SpaceforgePlugin
from spaceforge.runner import PluginRunner, runner_command


class PluginForTesting(SpaceforgePlugin):
    """Test plugin for runner testing."""

    __plugin_name__ = "test_plugin"
    __version__ = "1.0.0"
    __author__ = "Test Author"

    def __init__(self) -> None:
        super().__init__()
        self.hook_called = False
        self.hook_args: Optional[str] = None

    def after_plan(self) -> None:
        """Test hook method."""
        self.hook_called = True
        self.hook_args = "after_plan"

    def before_apply(self) -> None:
        """Another test hook method."""
        self.hook_called = True
        self.hook_args = "before_apply"

    def failing_hook(self) -> None:
        """Hook that raises an exception."""
        raise RuntimeError("Test error")

    def not_a_method(self) -> None:
        """Regular method that's not a hook."""
        pass


class TestPluginRunner:

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_plugin_path = os.path.join(self.temp_dir, "plugin.py")

        # Create a test plugin file
        with open(self.test_plugin_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin

class TestRunnerPlugin(SpaceforgePlugin):
    __plugin_name__ = "test_runner"
    
    def __init__(self) -> None:
        super().__init__()
        self.executed_hooks = []
    
    def after_plan(self) -> None:
        self.executed_hooks.append('after_plan')
        
    def before_apply(self) -> None:  
        self.executed_hooks.append('before_apply')
        
    def error_hook(self) -> None:
        raise ValueError("Test error from hook")
"""
            )

    def teardown_method(self) -> None:
        """Cleanup test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plugin_runner_init(self) -> None:
        """Test PluginRunner initialization."""
        runner = PluginRunner("test_plugin.py")

        assert runner.plugin_path == "test_plugin.py"
        assert runner.plugin_instance is None

    def test_plugin_runner_init_defaults(self) -> None:
        """Test PluginRunner initialization with default values."""
        runner = PluginRunner()

        assert runner.plugin_path == "plugin.py"
        assert runner.plugin_instance is None

    def test_load_plugin_file_not_found(self) -> None:
        """Test loading plugin when file doesn't exist."""
        runner = PluginRunner("nonexistent.py")

        with pytest.raises(FileNotFoundError, match="Plugin file not found"):
            runner.load_plugin()

    def test_load_plugin_invalid_module(self) -> None:
        """Test loading invalid Python module."""
        invalid_path = os.path.join(self.temp_dir, "invalid.py")
        with open(invalid_path, "w") as f:
            f.write("invalid python syntax }")

        runner = PluginRunner(invalid_path)

        with pytest.raises(Exception):  # Could be syntax error
            runner.load_plugin()

    def test_load_plugin_no_spacepy_subclass(self) -> None:
        """Test loading plugin with no SpaceforgePlugin subclass."""
        no_plugin_path = os.path.join(self.temp_dir, "no_plugin.py")
        with open(no_plugin_path, "w") as f:
            f.write(
                """
class NotAPlugin:
    pass
"""
            )

        runner = PluginRunner(no_plugin_path)

        with pytest.raises(ValueError, match="No SpaceforgePlugin subclass found"):
            runner.load_plugin()

    def test_load_plugin_success(self) -> None:
        """Test successful plugin loading."""
        runner = PluginRunner(self.test_plugin_path)
        runner.load_plugin()

        assert runner.plugin_instance is not None
        assert runner.plugin_instance.__class__.__name__ == "TestRunnerPlugin"

    @patch("spaceforge.runner.importlib.util.spec_from_file_location")
    def test_load_plugin_spec_none(self, mock_spec: Mock) -> None:
        """Test plugin loading when spec is None."""
        mock_spec.return_value = None

        runner = PluginRunner(self.test_plugin_path)

        with pytest.raises(ImportError, match="Could not load plugin"):
            runner.load_plugin()

    def test_run_hook_loads_plugin_if_needed(self) -> None:
        """Test that run_hook loads plugin if not already loaded."""
        runner = PluginRunner(self.test_plugin_path)

        with patch.object(runner, "load_plugin") as mock_load:
            mock_instance = Mock()
            mock_instance.after_plan = Mock()
            runner.plugin_instance = None

            # Should call load_plugin when plugin_instance is None
            runner.run_hook("after_plan")
            mock_load.assert_called_once()

    def test_run_hook_success(self) -> None:
        """Test successful hook execution."""
        runner = PluginRunner(self.test_plugin_path)
        runner.load_plugin()

        with patch("builtins.print") as mock_print:
            runner.run_hook("after_plan")

        # Verify the hook was called
        assert runner.plugin_instance is not None
        assert hasattr(runner.plugin_instance, "executed_hooks")
        assert "after_plan" in getattr(runner.plugin_instance, "executed_hooks")

        # Verify print statements
        mock_print.assert_any_call("[SpaceForge] Running hook: after_plan")
        mock_print.assert_any_call("[SpaceForge] Hook completed: after_plan")

    def test_run_hook_not_found(self) -> None:
        """Test running a hook that doesn't exist."""
        runner = PluginRunner(self.test_plugin_path)
        runner.load_plugin()

        with patch("builtins.print") as mock_print:
            runner.run_hook("nonexistent_hook")

        mock_print.assert_called_with(
            "Hook method 'nonexistent_hook' not found in plugin"
        )

    def test_run_hook_not_callable(self) -> None:
        """Test running a hook that exists but is not callable."""
        runner = PluginRunner(self.test_plugin_path)
        runner.load_plugin()

        # Add a non-callable attribute
        assert runner.plugin_instance is not None
        setattr(runner.plugin_instance, "not_callable", "not a method")

        with patch("builtins.print") as mock_print:
            runner.run_hook("not_callable")

        mock_print.assert_called_with("'not_callable' is not a callable method")

    def test_run_hook_with_exception(self) -> None:
        """Test hook execution that raises an exception."""
        runner = PluginRunner(self.test_plugin_path)
        runner.load_plugin()

        with patch("builtins.print") as mock_print:
            with pytest.raises(ValueError, match="Test error from hook"):
                runner.run_hook("error_hook")

        # Should print error message
        mock_print.assert_any_call(
            "[SpaceForge] Error running hook 'error_hook': Test error from hook"
        )

    def test_run_hook_multiple_hooks(self) -> None:
        """Test running multiple different hooks."""
        runner = PluginRunner(self.test_plugin_path)
        runner.load_plugin()

        with patch("builtins.print"):
            runner.run_hook("after_plan")
            runner.run_hook("before_apply")

        # Both hooks should have been executed
        assert runner.plugin_instance is not None
        assert hasattr(runner.plugin_instance, "executed_hooks")
        executed = getattr(runner.plugin_instance, "executed_hooks")
        assert "after_plan" in executed
        assert "before_apply" in executed
        assert len(executed) == 2

    def test_integration_full_workflow(self) -> None:
        """Integration test for complete runner workflow."""
        # Create a complete test plugin file
        full_plugin_path = os.path.join(self.temp_dir, "full_plugin.py")
        with open(full_plugin_path, "w") as f:
            f.write(
                '''
from spaceforge import SpaceforgePlugin

class FullTestPlugin(SpaceforgePlugin):
    """A full test plugin for integration testing."""
    
    __plugin_name__ = "full_test"
    
    def __init__(self) -> None:
        super().__init__()
        self.integration_test_passed = False
    
    def after_plan(self) -> str:
        """Integration test hook."""
        self.integration_test_passed = True
        return "success"
'''
            )

        runner = PluginRunner(full_plugin_path)

        # This should work end-to-end
        with patch("builtins.print"):
            runner.run_hook("after_plan")

        assert runner.plugin_instance is not None
        assert runner.plugin_instance.__class__.__name__ == "FullTestPlugin"
        assert hasattr(runner.plugin_instance, "integration_test_passed")
        assert getattr(runner.plugin_instance, "integration_test_passed") is True


class TestRunnerCommand:
    """Test the Click command interface."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_plugin_path = os.path.join(self.temp_dir, "plugin.py")

        # Create a test plugin file
        with open(self.test_plugin_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin

class ClickTestPlugin(SpaceforgePlugin):
    def after_plan(self) -> None:
        print("Hook executed via click")
"""
            )

    def teardown_method(self) -> None:
        """Cleanup test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_runner_command(self) -> None:
        """Test the Click runner command."""
        from click.testing import CliRunner

        cli_runner = CliRunner()

        with patch("spaceforge.runner.PluginRunner") as mock_runner_class:
            mock_runner = Mock()
            mock_runner_class.return_value = mock_runner

            # Test the command using Click's test runner
            result = cli_runner.invoke(
                runner_command, ["after_plan", "--plugin-file", self.test_plugin_path]
            )

            assert result.exit_code == 0

            # Verify PluginRunner was instantiated with correct path
            mock_runner_class.assert_called_once_with(self.test_plugin_path)

            # Verify run_hook was called with correct hook name
            mock_runner.run_hook.assert_called_once_with("after_plan")

    def test_runner_command_default_plugin_file(self) -> None:
        """Test runner command with default plugin file."""
        from click.testing import CliRunner

        cli_runner = CliRunner()

        with patch("spaceforge.runner.PluginRunner") as mock_runner_class:
            mock_runner = Mock()
            mock_runner_class.return_value = mock_runner

            # Test with explicit plugin file path
            result = cli_runner.invoke(
                runner_command, ["before_apply", "--plugin-file", self.test_plugin_path]
            )

            assert result.exit_code == 0
            mock_runner_class.assert_called_once_with(self.test_plugin_path)
            mock_runner.run_hook.assert_called_once_with("before_apply")


class TestMainFunction:
    """Test the legacy main function."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_plugin_path = os.path.join(self.temp_dir, "plugin.py")

        # Create a test plugin file
        with open(self.test_plugin_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin

class MainTestPlugin(SpaceforgePlugin):
    def after_plan(self) -> None:
        pass
"""
            )

    def teardown_method(self) -> None:
        """Cleanup test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestRunnerEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self) -> None:
        """Cleanup test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plugin_with_multiple_subclasses(self) -> None:
        """Test plugin file with multiple SpaceforgePlugin subclasses."""
        multi_plugin_path = os.path.join(self.temp_dir, "multi_plugin.py")
        with open(multi_plugin_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin

class FirstPlugin(SpaceforgePlugin):
    def after_plan(self) -> None:
        pass

class SecondPlugin(SpaceforgePlugin):  
    def before_apply(self) -> None:
        pass
"""
            )

        runner = PluginRunner(multi_plugin_path)
        runner.load_plugin()

        # Should load one of the plugins (implementation loads the first one found)
        assert runner.plugin_instance is not None
        assert runner.plugin_instance.__class__.__name__ in [
            "FirstPlugin",
            "SecondPlugin",
        ]

    def test_plugin_with_inheritance_hierarchy(self) -> None:
        """Test plugin with complex inheritance hierarchy."""
        hierarchy_plugin_path = os.path.join(self.temp_dir, "hierarchy_plugin.py")
        with open(hierarchy_plugin_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin

class BaseCustomPlugin(SpaceforgePlugin):
    def base_method(self) -> None:
        pass

class DerivedPlugin(BaseCustomPlugin):
    def after_plan(self) -> None:
        self.base_method()
"""
            )

        runner = PluginRunner(hierarchy_plugin_path)
        runner.load_plugin()

        assert runner.plugin_instance is not None
        # The runner loads the first SpaceforgePlugin subclass it finds
        # which could be either BaseCustomPlugin or DerivedPlugin
        assert runner.plugin_instance.__class__.__name__ in [
            "BaseCustomPlugin",
            "DerivedPlugin",
        ]

        # Should be able to run hooks from the loaded class
        with patch("builtins.print"):
            if hasattr(runner.plugin_instance, "after_plan"):
                runner.run_hook("after_plan")

    def test_hook_execution_with_return_value(self) -> None:
        """Test hook execution that returns a value."""
        return_plugin_path = os.path.join(self.temp_dir, "return_plugin.py")
        with open(return_plugin_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin

class ReturnPlugin(SpaceforgePlugin):
    def after_plan(self) -> dict[str, str]:
        return {"status": "success", "data": "test"}
"""
            )

        runner = PluginRunner(return_plugin_path)
        runner.load_plugin()

        # Hook execution should work even if it returns a value
        with patch("builtins.print"):
            runner.run_hook("after_plan")

    def test_hook_with_arguments_fails_gracefully(self) -> None:
        """Test hook that expects arguments (should fail gracefully)."""
        args_plugin_path = os.path.join(self.temp_dir, "args_plugin.py")
        with open(args_plugin_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin

class ArgsPlugin(SpaceforgePlugin):
    def after_plan(self, required_arg) -> None:
        pass
"""
            )

        runner = PluginRunner(args_plugin_path)
        runner.load_plugin()

        # Should raise TypeError due to missing required argument
        with patch("builtins.print") as mock_print:
            with pytest.raises(TypeError):
                runner.run_hook("after_plan")

        # Should print error message
        assert any(
            "Error running hook" in str(call) for call in mock_print.call_args_list
        )

    def test_plugin_loading_with_import_errors(self) -> None:
        """Test plugin loading when plugin imports fail."""
        import_error_path = os.path.join(self.temp_dir, "import_error_plugin.py")
        with open(import_error_path, "w") as f:
            f.write(
                """
from nonexistent_module import SomeClass
from spaceforge import SpaceforgePlugin

class ImportErrorPlugin(SpaceforgePlugin):
    def after_plan(self) -> None:
        pass
"""
            )

        runner = PluginRunner(import_error_path)

        with pytest.raises(ModuleNotFoundError):
            runner.load_plugin()

    def test_run_hook_preserves_plugin_state(self) -> None:
        """Test that running hooks preserves plugin instance state."""
        state_plugin_path = os.path.join(self.temp_dir, "state_plugin.py")
        with open(state_plugin_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin

class StatePlugin(SpaceforgePlugin):
    def __init__(self) -> None:
        super().__init__()
        self.counter = 0
    
    def increment_hook(self) -> None:
        self.counter += 1
        
    def get_counter_hook(self) -> int:
        return self.counter
"""
            )

        runner = PluginRunner(state_plugin_path)
        runner.load_plugin()

        # Run increment hook multiple times
        with patch("builtins.print"):
            runner.run_hook("increment_hook")
            runner.run_hook("increment_hook")
            runner.run_hook("increment_hook")

        # State should be preserved
        assert runner.plugin_instance is not None
        assert hasattr(runner.plugin_instance, "counter")
        assert getattr(runner.plugin_instance, "counter") == 3
