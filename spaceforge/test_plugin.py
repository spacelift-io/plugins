import json
import logging
import os
import subprocess
from typing import Dict
from unittest.mock import Mock, patch

import pytest

from spaceforge.plugin import SpaceforgePlugin


class TestSpaceforgePluginInitialization:
    """Test SpaceforgePlugin initialization and configuration."""

    def test_should_initialize_with_defaults_when_no_environment_set(self) -> None:
        """Should set default values when no environment variables are provided."""
        # Arrange & Act
        with patch.dict(os.environ, {}, clear=True):
            plugin = SpaceforgePlugin()

        # Assert
        assert plugin._api_token is False
        assert plugin._api_endpoint is False
        assert plugin._api_enabled is False
        assert plugin._workspace_root == os.getcwd()
        assert isinstance(plugin.logger, logging.Logger)

    def test_should_enable_api_when_valid_credentials_provided(
        self, mock_env: Dict[str, str]
    ) -> None:
        """Should enable API access when both token and endpoint are provided."""
        # Arrange & Act
        with patch.dict(os.environ, mock_env, clear=True):
            plugin = SpaceforgePlugin()

        # Assert
        assert plugin._api_token == "test_token"
        assert plugin._api_endpoint == "https://test.spacelift.io"
        assert plugin._api_enabled is True
        assert plugin._workspace_root == os.getcwd()

    def test_should_normalize_domain_with_trailing_slash(self) -> None:
        """Should remove trailing slash from domain URL."""
        # Arrange
        test_env = {
            "SPACELIFT_API_TOKEN": "test_token",
            "TF_VAR_spacelift_graphql_endpoint": "https://test.spacelift.io/",
        }

        # Act
        with patch.dict(os.environ, test_env, clear=True):
            plugin = SpaceforgePlugin()

        # Assert
        assert plugin._api_endpoint == "https://test.spacelift.io"
        assert plugin._api_enabled is True

    def test_should_disable_api_when_domain_has_no_https_prefix(self) -> None:
        """Should disable API when domain doesn't use HTTPS."""
        # Arrange
        test_env = {
            "SPACELIFT_API_TOKEN": "test_token",
            "TF_VAR_spacelift_graphql_endpoint": "test.spacelift.io",
        }

        # Act
        with patch.dict(os.environ, test_env, clear=True):
            plugin = SpaceforgePlugin()

        # Assert
        assert plugin._api_endpoint == "test.spacelift.io"
        assert plugin._api_enabled is False

    def test_should_disable_api_when_only_token_provided(self) -> None:
        """Should disable API when only token is provided without domain."""
        # Arrange & Act
        with patch.dict(os.environ, {"SPACELIFT_API_TOKEN": "test_token"}, clear=True):
            plugin = SpaceforgePlugin()

        # Assert
        assert plugin._api_enabled is False

    def test_should_disable_api_when_only_domain_provided(self) -> None:
        """Should disable API when only domain is provided without token."""
        # Arrange & Act
        with patch.dict(
            os.environ,
            {"TF_VAR_spacelift_graphql_endpoint": "https://test.spacelift.io"},
            clear=True,
        ):
            plugin = SpaceforgePlugin()

        # Assert
        assert plugin._api_enabled is False


class TestSpaceforgePluginLogging:
    """Test logging configuration and functionality."""

    def test_should_configure_logger_with_correct_name_and_level(self) -> None:
        """Should set up logger with proper name and level."""
        # Arrange & Act
        with patch.dict(os.environ, {}, clear=True):
            plugin = SpaceforgePlugin()

        # Assert
        assert plugin.logger.name == "spaceforge.SpaceforgePlugin"
        assert len(plugin.logger.handlers) >= 1
        assert plugin.logger.getEffectiveLevel() <= logging.INFO

    def test_should_enable_debug_logging_when_debug_env_set(self) -> None:
        """Should set DEBUG level when SPACELIFT_DEBUG environment variable is true."""
        # Arrange
        test_env = {"SPACELIFT_DEBUG": "true"}

        # Act
        with patch.dict(os.environ, test_env, clear=True):
            plugin = SpaceforgePlugin()

        # Assert
        assert plugin.logger.level == logging.DEBUG

    def test_should_include_run_id_in_log_format(self) -> None:
        """Should include run ID in log message format when available."""
        # Arrange
        test_env = {"TF_VAR_spacelift_run_id": "run-123"}

        # Act
        with patch.dict(os.environ, test_env, clear=True):
            plugin = SpaceforgePlugin()
            formatter = plugin.logger.handlers[0].formatter

            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="test message",
                args=(),
                exc_info=None,
            )
            record.levelname = "INFO"

        # Assert
        assert formatter is not None
        formatted = formatter.format(record)
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


# Hook tests moved to test_plugin_hooks.py


class TestSpaceforgePluginCLI:
    """Test command-line interface execution functionality."""

    def test_should_execute_cli_command_and_log_output_on_success(self) -> None:
        """Should run CLI command and log output when execution succeeds."""
        # Arrange
        plugin = SpaceforgePlugin()
        mock_process = Mock()
        mock_process.communicate.return_value = (b"success output\n", None)
        mock_process.returncode = 0

        # Act
        with patch("subprocess.Popen") as mock_popen:
            with patch.object(plugin.logger, "info") as mock_info:
                mock_popen.return_value = mock_process
                plugin.run_cli("echo", "test")

        # Assert
        mock_popen.assert_called_once_with(
            ("echo", "test"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        mock_info.assert_called_with("success output")

    def test_should_log_error_when_cli_command_fails(self) -> None:
        """Should log error details when CLI command returns non-zero exit code."""
        # Arrange
        plugin = SpaceforgePlugin()
        mock_process = Mock()
        mock_process.communicate.return_value = (None, b"error output\n")
        mock_process.returncode = 1

        # Act
        with patch("subprocess.Popen") as mock_popen:
            with patch.object(plugin.logger, "error") as mock_error:
                mock_popen.return_value = mock_process
                plugin.run_cli("false")

        # Assert
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
    """Test GraphQL API interaction functionality."""

    def test_should_exit_with_error_when_api_disabled(self) -> None:
        """Should exit with error message when API is not enabled."""
        # Arrange
        plugin = SpaceforgePlugin()
        plugin._api_enabled = False

        # Act & Assert
        with patch.object(plugin.logger, "error") as mock_error:
            with pytest.raises(SystemExit):
                plugin.query_api("query { test }")

        mock_error.assert_called_with(
            'API is not enabled, please export "SPACELIFT_API_TOKEN" and "TF_VAR_spacelift_graphql_endpoint".'
        )

    def test_should_make_successful_api_request_with_correct_format(
        self, mock_api_response: Mock
    ) -> None:
        """Should execute GraphQL query with proper authentication and format."""
        # Arrange
        plugin = SpaceforgePlugin()
        plugin._api_enabled = True
        plugin._api_token = "test_token"
        plugin._api_endpoint = "https://test.spacelift.io"

        expected_data = {"data": {"test": "result"}}
        mock_api_response.read.return_value = json.dumps(expected_data).encode("utf-8")

        # Act
        with patch("urllib.request.urlopen") as mock_urlopen:
            with patch("urllib.request.Request") as mock_request:
                mock_urlopen.return_value.__enter__ = Mock(
                    return_value=mock_api_response
                )
                mock_urlopen.return_value.__exit__ = Mock(return_value=None)

                result = plugin.query_api("query { test }")

        # Assert
        mock_request.assert_called_once()
        call_args = mock_request.call_args[0]
        assert call_args[0] == "https://test.spacelift.io"

        request_data = json.loads(call_args[1].decode("utf-8"))
        assert request_data["query"] == "query { test }"

        headers = mock_request.call_args[0][2]
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer test_token"

        assert result == expected_data

    def test_query_api_with_variables(self) -> None:
        """Test API query with variables."""
        plugin = SpaceforgePlugin()
        plugin._api_enabled = True
        plugin._api_token = "test_token"
        plugin._api_endpoint = "https://test.spacelift.io"

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
        plugin._api_endpoint = "https://test.spacelift.io"

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


# File operation tests moved to test_plugin_file_operations.py


# Inheritance tests moved to test_plugin_inheritance.py


# Edge case tests moved to test_plugin_inheritance.py
