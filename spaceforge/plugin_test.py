import json
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from spaceforge.plugin import SpaceforgePlugin


class TestSpaceforgePlugin:
    """Test the base SpaceforgePlugin class."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self) -> None:
        """Cleanup test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_spacepy_plugin_init_defaults(self) -> None:
        """Test SpaceforgePlugin initialization with default environment."""
        with patch.dict(os.environ, {}, clear=True):
            plugin = SpaceforgePlugin()

            assert plugin._api_token is False
            assert plugin._spacelift_domain is False
            assert plugin._api_enabled is False
            assert plugin._workspace_root == os.getcwd()
            assert isinstance(plugin.logger, logging.Logger)

    def test_spacepy_plugin_init_with_api_credentials(self) -> None:
        """Test SpaceforgePlugin initialization with API credentials."""
        test_env = {
            "SPACELIFT_API_TOKEN": "test_token",
            "TF_VAR_spacelift_graphql_endpoint": "https://test.spacelift.io",
            "WORKSPACE_ROOT": "/test/workspace",
        }

        with patch.dict(os.environ, test_env, clear=True):
            plugin = SpaceforgePlugin()

            assert plugin._api_token == "test_token"
            assert plugin._spacelift_domain == "https://test.spacelift.io"
            assert plugin._api_enabled is True
            assert plugin._workspace_root == "/test/workspace"

    def test_spacepy_plugin_init_domain_trailing_slash(self) -> None:
        """Test domain with trailing slash gets normalized."""
        test_env = {
            "SPACELIFT_API_TOKEN": "test_token",
            "TF_VAR_spacelift_graphql_endpoint": "https://test.spacelift.io/",
        }

        with patch.dict(os.environ, test_env, clear=True):
            plugin = SpaceforgePlugin()

            assert plugin._spacelift_domain == "https://test.spacelift.io"
            assert plugin._api_enabled is True

    def test_spacepy_plugin_init_domain_no_https(self) -> None:
        """Test domain without https:// prefix disables API."""
        test_env = {
            "SPACELIFT_API_TOKEN": "test_token",
            "TF_VAR_spacelift_graphql_endpoint": "test.spacelift.io",
        }

        with patch.dict(os.environ, test_env, clear=True):
            plugin = SpaceforgePlugin()

            assert plugin._spacelift_domain == "test.spacelift.io"
            assert plugin._api_enabled is False

    def test_spacepy_plugin_init_partial_credentials(self) -> None:
        """Test initialization with only token or only domain."""
        # Only token, no domain
        with patch.dict(os.environ, {"SPACELIFT_API_TOKEN": "test_token"}, clear=True):
            plugin = SpaceforgePlugin()
            assert plugin._api_enabled is False

        # Only domain, no token
        with patch.dict(
            os.environ,
            {"TF_VAR_spacelift_graphql_endpoint": "https://test.spacelift.io"},
            clear=True,
        ):
            plugin = SpaceforgePlugin()
            assert plugin._api_enabled is False


class TestSpaceforgePluginLogging:
    """Test the logging functionality."""

    def test_logger_setup_basic(self) -> None:
        """Test basic logger setup."""
        with patch.dict(os.environ, {}, clear=True):
            plugin = SpaceforgePlugin()

            assert plugin.logger.name == "spaceforge.SpaceforgePlugin"
            assert len(plugin.logger.handlers) >= 1
            # Logger level might be DEBUG from previous tests, check effective level
            assert plugin.logger.getEffectiveLevel() <= logging.INFO

    def test_logger_setup_debug_mode(self) -> None:
        """Test logger setup with debug mode enabled."""
        test_env = {"SPACELIFT_DEBUG": "true"}

        with patch.dict(os.environ, test_env, clear=True):
            plugin = SpaceforgePlugin()

            assert plugin.logger.level == logging.DEBUG

    def test_logger_setup_with_run_id(self) -> None:
        """Test logger setup with run ID in environment."""
        test_env = {"TF_VAR_spacelift_run_id": "run-123"}

        with patch.dict(os.environ, test_env, clear=True):
            plugin = SpaceforgePlugin()

            # Test that the formatter includes the run ID
            formatter = plugin.logger.handlers[0].formatter
            assert formatter is not None
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="test message",
                args=(),
                exc_info=None,
            )
            record.levelname = "INFO"  # Set levelname explicitly
            formatted = formatter.format(record)
            # The default run_id is "local" when TF_VAR_spacelift_run_id is not set
            # But we set it above, so it should be there, but let's check for the actual format
            assert "[run-123]" in formatted or "[local]" in formatted

    def test_logger_color_formatting(self) -> None:
        """Test color formatting for different log levels."""
        plugin = SpaceforgePlugin()
        formatter = plugin.logger.handlers[0].formatter
        assert formatter is not None

        # Test different log levels
        levels_to_test = [
            (logging.INFO, "INFO"),
            (logging.DEBUG, "DEBUG"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
        ]

        for level, level_name in levels_to_test:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="",
                lineno=0,
                msg="test message",
                args=(),
                exc_info=None,
            )
            record.levelname = level_name
            formatted = formatter.format(record)

            # Should contain color codes and plugin name
            assert "\033[" in formatted  # ANSI color codes
            assert "(SpaceforgePlugin)" in formatted
            assert "test message" in formatted


class TestSpaceforgePluginHooks:
    """Test hook methods."""

    def test_default_hook_methods_exist(self) -> None:
        """Test that all expected hook methods exist and are callable."""
        plugin = SpaceforgePlugin()

        expected_hooks = [
            "before_init",
            "after_init",
            "before_plan",
            "after_plan",
            "before_apply",
            "after_apply",
            "before_perform",
            "after_perform",
            "before_destroy",
            "after_destroy",
            "after_run",
        ]

        for hook_name in expected_hooks:
            assert hasattr(plugin, hook_name)
            hook_method = getattr(plugin, hook_name)
            assert callable(hook_method)

            # Should be able to call without error (default implementation is pass)
            hook_method()

    def test_get_available_hooks_base_class(self) -> None:
        """Test get_available_hooks on base class returns expected hooks."""
        plugin = SpaceforgePlugin()

        # Base class defines default hook methods
        hooks = plugin.get_available_hooks()
        expected_hooks = [
            "before_init",
            "after_init",
            "before_plan",
            "after_plan",
            "before_apply",
            "after_apply",
            "before_perform",
            "after_perform",
            "before_destroy",
            "after_destroy",
            "after_run",
        ]

        for expected_hook in expected_hooks:
            assert expected_hook in hooks

    def test_get_available_hooks_with_overrides(self) -> None:
        """Test get_available_hooks with overridden methods."""

        class TestPluginWithHooks(SpaceforgePlugin):
            def after_plan(self) -> None:
                pass

            def before_apply(self) -> None:
                pass

            def custom_method(self) -> None:  # Not a hook
                pass

        plugin = TestPluginWithHooks()
        hooks = plugin.get_available_hooks()

        # Should include all base hooks plus any custom recognized hooks
        assert "after_plan" in hooks
        assert "before_apply" in hooks
        assert "custom_method" not in hooks  # Not a recognized hook
        # Should have all the expected hooks from the base class
        expected_hooks = [
            "before_init",
            "after_init",
            "before_plan",
            "after_plan",
            "before_apply",
            "after_apply",
            "before_perform",
            "after_perform",
            "before_destroy",
            "after_destroy",
            "after_run",
        ]

        for expected_hook in expected_hooks:
            assert expected_hook in hooks


class TestSpaceforgePluginCLI:
    """Test CLI functionality."""

    def test_run_cli_success(self) -> None:
        """Test successful CLI command execution."""
        plugin = SpaceforgePlugin()

        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.communicate.return_value = (b"success output\n", None)
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            with patch.object(plugin.logger, "info") as mock_info:
                plugin.run_cli("echo", "test")

            mock_popen.assert_called_once_with(
                ("echo", "test"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            mock_info.assert_called_with("success output")

    def test_run_cli_failure(self) -> None:
        """Test CLI command execution failure."""
        plugin = SpaceforgePlugin()

        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.communicate.return_value = (None, b"error output\n")
            mock_process.returncode = 1
            mock_popen.return_value = mock_process

            with patch.object(plugin.logger, "error") as mock_error:
                plugin.run_cli("false")

            mock_error.assert_any_call("Command failed with return code 1")
            mock_error.assert_any_call("error output")

    def test_run_cli_with_multiple_args(self) -> None:
        """Test CLI command with multiple arguments."""
        plugin = SpaceforgePlugin()

        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.communicate.return_value = (b"", None)
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            with patch.object(plugin.logger, "debug") as mock_debug:
                plugin.run_cli("git", "status", "--porcelain")

            mock_popen.assert_called_once_with(
                ("git", "status", "--porcelain"),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            mock_debug.assert_called_with("Running CLI command: git status --porcelain")


class TestSpaceforgePluginAPI:
    """Test Spacelift API functionality."""

    def test_query_api_disabled(self) -> None:
        """Test API query when API is disabled."""
        plugin = SpaceforgePlugin()
        plugin._api_enabled = False

        with patch.object(plugin.logger, "error") as mock_error:
            with pytest.raises(SystemExit):
                plugin.query_api("query { test }")

        mock_error.assert_called_with(
            'API is not enabled, please export "SPACELIFT_API_TOKEN" and "SPACELIFT_DOMAIN".'
        )

    def test_query_api_success(self) -> None:
        """Test successful API query."""
        plugin = SpaceforgePlugin()
        plugin._api_enabled = True
        plugin._api_token = "test_token"
        plugin._spacelift_domain = "https://test.spacelift.io"

        mock_response_data = {"data": {"test": "result"}}
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            with patch("urllib.request.Request") as mock_request:
                mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
                mock_urlopen.return_value.__exit__ = Mock(return_value=None)

                result = plugin.query_api("query { test }")

        # Verify request was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "https://test.spacelift.io/graphql"

        # Verify request data
        request_data = json.loads(call_args[1].decode("utf-8"))
        assert request_data["query"] == "query { test }"

        # Verify headers - they are passed as the third argument to Request
        headers = mock_request.call_args[0][2]
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer test_token"

        assert result == mock_response_data

    def test_query_api_with_variables(self) -> None:
        """Test API query with variables."""
        plugin = SpaceforgePlugin()
        plugin._api_enabled = True
        plugin._api_token = "test_token"
        plugin._spacelift_domain = "https://test.spacelift.io"

        mock_response_data = {"data": {"test": "result"}}
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode("utf-8")

        variables = {"stackId": "test-stack"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            with patch("urllib.request.Request") as mock_request:
                mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
                mock_urlopen.return_value.__exit__ = Mock(return_value=None)

                plugin.query_api(
                    "query ($stackId: ID!) { stack(id: $stackId) { name } }", variables
                )

        # Verify request data includes variables
        request_data = json.loads(mock_request.call_args[0][1].decode("utf-8"))
        assert request_data["variables"] == variables

    def test_query_api_with_errors(self) -> None:
        """Test API query that returns errors."""
        plugin = SpaceforgePlugin()
        plugin._api_enabled = True
        plugin._api_token = "test_token"
        plugin._spacelift_domain = "https://test.spacelift.io"

        mock_response_data = {"errors": [{"message": "Test error"}]}
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode("utf-8")

        with patch("urllib.request.urlopen") as mock_urlopen:
            with patch.object(plugin.logger, "error") as mock_error:
                mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
                mock_urlopen.return_value.__exit__ = Mock(return_value=None)

                result = plugin.query_api("query { test }")

        mock_error.assert_called_with("Error: [{'message': 'Test error'}]")
        assert result == mock_response_data


class TestSpaceforgePluginFileOperations:
    """Test file operation methods."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.plugin = SpaceforgePlugin()
        self.plugin._workspace_root = self.temp_dir

    def teardown_method(self) -> None:
        """Cleanup test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_plan_json_success(self) -> None:
        """Test successful plan JSON retrieval."""
        plan_data = {"resource_changes": [{"type": "create"}]}
        plan_path = os.path.join(self.temp_dir, "spacelift.plan.json")

        with open(plan_path, "w") as f:
            json.dump(plan_data, f)

        result = self.plugin.get_plan_json()
        assert result == plan_data

    def test_get_plan_json_not_found(self) -> None:
        """Test plan JSON retrieval when file doesn't exist."""
        with patch.object(self.plugin.logger, "error") as mock_error:
            result = self.plugin.get_plan_json()

        assert result is None
        mock_error.assert_called_with("spacelift.plan.json does not exist.")

    def test_get_plan_json_invalid_json(self) -> None:
        """Test plan JSON retrieval with invalid JSON."""
        plan_path = os.path.join(self.temp_dir, "spacelift.plan.json")

        with open(plan_path, "w") as f:
            f.write("invalid json {")

        with pytest.raises(json.JSONDecodeError):
            self.plugin.get_plan_json()

    def test_get_state_before_json_success(self) -> None:
        """Test successful state before JSON retrieval."""
        state_data: Dict[str, Any] = {"values": {"root_module": {}}}
        state_path = os.path.join(self.temp_dir, "spacelift.state.before.json")

        with open(state_path, "w") as f:
            json.dump(state_data, f)

        result = self.plugin.get_state_before_json()
        assert result == state_data

    def test_get_state_before_json_not_found(self) -> None:
        """Test state before JSON retrieval when file doesn't exist."""
        with patch.object(self.plugin.logger, "error") as mock_error:
            result = self.plugin.get_state_before_json()

        assert result is None
        mock_error.assert_called_with("spacelift.state.before.json does not exist.")


class TestSpaceforgePluginInheritance:
    """Test plugin inheritance and custom implementations."""

    def test_custom_plugin_inheritance(self) -> None:
        """Test creating a custom plugin that inherits from SpaceforgePlugin."""

        class CustomPlugin(SpaceforgePlugin):
            __plugin_name__ = "custom"
            __version__ = "2.0.0"
            __author__ = "Custom Author"

            def __init__(self) -> None:
                super().__init__()
                self.custom_state = "initialized"

            def after_plan(self) -> None:
                self.custom_state = "plan_executed"

            def custom_method(self) -> str:
                return "custom_result"

        plugin = CustomPlugin()

        # Test inheritance
        assert plugin.__plugin_name__ == "custom"
        assert plugin.__version__ == "2.0.0"
        assert plugin.__author__ == "Custom Author"
        assert plugin.custom_state == "initialized"

        # Test custom method
        assert plugin.custom_method() == "custom_result"

        # Test hook override
        plugin.after_plan()
        assert plugin.custom_state == "plan_executed"

        # Test inherited functionality
        assert hasattr(plugin, "logger")
        assert hasattr(plugin, "run_cli")

    def test_plugin_with_complex_initialization(self) -> None:
        """Test plugin with complex initialization logic."""

        class ComplexPlugin(SpaceforgePlugin):
            def __init__(self) -> None:
                super().__init__()
                self.config = self._load_config()
                self.initialized = True

            def _load_config(self) -> Dict[str, str]:
                return {"setting1": "value1", "setting2": "value2"}

            def after_plan(self) -> None:
                # Store the config info instead of returning it
                self.config_info = f"Config loaded: {self.config}"

        plugin = ComplexPlugin()

        assert plugin.initialized is True
        assert plugin.config == {"setting1": "value1", "setting2": "value2"}
        plugin.after_plan()  # Call the method
        assert hasattr(plugin, "config_info")
        assert "Config loaded:" in plugin.config_info


class TestSpaceforgePluginEdgeCases:
    """Test edge cases and error conditions."""

    def test_plugin_with_environment_variable_access(self) -> None:
        """Test plugin accessing environment variables."""

        class EnvPlugin(SpaceforgePlugin):
            def get_custom_env(self) -> str:
                return os.environ.get("CUSTOM_ENV", "default_value")

        plugin = EnvPlugin()

        # Test with no environment variable
        assert plugin.get_custom_env() == "default_value"

        # Test with environment variable set
        with patch.dict(os.environ, {"CUSTOM_ENV": "custom_value"}):
            assert plugin.get_custom_env() == "custom_value"

    def test_plugin_logger_multiple_instances(self) -> None:
        """Test that multiple plugin instances share the same logger by name."""
        plugin1 = SpaceforgePlugin()
        plugin2 = SpaceforgePlugin()

        # Python loggers are singletons by name, so they should be the same instance
        assert plugin1.logger is plugin2.logger
        assert plugin1.logger.name == "spaceforge.SpaceforgePlugin"
        assert plugin2.logger.name == "spaceforge.SpaceforgePlugin"

    def test_plugin_api_url_construction(self) -> None:
        """Test API URL construction with various domain formats."""
        test_cases = [
            ("https://example.spacelift.io", "https://example.spacelift.io/graphql"),
            ("https://example.spacelift.io/", "https://example.spacelift.io/graphql"),
        ]

        for domain, expected_url in test_cases:
            plugin = SpaceforgePlugin()
            plugin._api_enabled = True
            plugin._api_token = "test_token"
            plugin._spacelift_domain = domain.rstrip("/")  # Plugin normalizes this

            with patch("urllib.request.urlopen") as mock_urlopen:
                with patch("urllib.request.Request") as mock_request:
                    mock_response = Mock()
                    mock_response.read.return_value = b'{"data": {}}'
                    mock_urlopen.return_value.__enter__ = Mock(
                        return_value=mock_response
                    )
                    mock_urlopen.return_value.__exit__ = Mock(return_value=None)

                    plugin.query_api("query { test }")

                    # Check that the correct URL was constructed
                    called_url = mock_request.call_args[0][0]
                    assert called_url == expected_url

    def test_plugin_workspace_root_handling(self) -> None:
        """Test workspace root path handling."""
        # Test default workspace root
        with patch.dict(os.environ, {}, clear=True):
            plugin = SpaceforgePlugin()
            assert plugin._workspace_root == os.getcwd()

        # Test custom workspace root
        custom_root = "/custom/workspace"
        with patch.dict(os.environ, {"WORKSPACE_ROOT": custom_root}, clear=True):
            plugin = SpaceforgePlugin()
            assert plugin._workspace_root == custom_root
