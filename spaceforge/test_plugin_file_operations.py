"""Tests for SpaceforgePlugin file operation methods."""

import json
import os
from typing import Any, Dict
from unittest.mock import patch

import pytest

from spaceforge.plugin import SpaceforgePlugin


class TestSpaceforgePluginFileOperations:
    """Test file reading and parsing functionality."""

    def test_should_return_plan_data_when_plan_file_exists(self, temp_dir: str) -> None:
        """Should parse and return plan JSON when file exists and is valid."""
        # Arrange
        plugin = SpaceforgePlugin()
        plugin._workspace_root = temp_dir
        plan_data = {"resource_changes": [{"type": "create"}]}
        plan_path = os.path.join(temp_dir, "spacelift.plan.json")

        with open(plan_path, "w") as f:
            json.dump(plan_data, f)

        # Act
        result = plugin.get_plan_json()

        # Assert
        assert result == plan_data

    def test_should_return_none_and_log_error_when_plan_file_missing(
        self, temp_dir: str
    ) -> None:
        """Should return None and log error when plan file doesn't exist."""
        # Arrange
        plugin = SpaceforgePlugin()
        plugin._workspace_root = temp_dir

        # Act
        with patch.object(plugin.logger, "error") as mock_error:
            result = plugin.get_plan_json()

        # Assert
        assert result is None
        mock_error.assert_called_with("spacelift.plan.json does not exist.")

    def test_should_raise_json_decode_error_when_plan_file_invalid(
        self, temp_dir: str
    ) -> None:
        """Should raise JSONDecodeError when plan file contains invalid JSON."""
        # Arrange
        plugin = SpaceforgePlugin()
        plugin._workspace_root = temp_dir
        plan_path = os.path.join(temp_dir, "spacelift.plan.json")

        with open(plan_path, "w") as f:
            f.write("invalid json {")

        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            plugin.get_plan_json()

    def test_should_return_state_data_when_state_file_exists(
        self, temp_dir: str
    ) -> None:
        """Should parse and return state JSON when file exists and is valid."""
        # Arrange
        plugin = SpaceforgePlugin()
        plugin._workspace_root = temp_dir
        state_data: Dict[str, Any] = {"values": {"root_module": {}}}
        state_path = os.path.join(temp_dir, "spacelift.state.before.json")

        with open(state_path, "w") as f:
            json.dump(state_data, f)

        # Act
        result = plugin.get_state_before_json()

        # Assert
        assert result == state_data

    def test_should_return_none_and_log_error_when_state_file_missing(
        self, temp_dir: str
    ) -> None:
        """Should return None and log error when state file doesn't exist."""
        # Arrange
        plugin = SpaceforgePlugin()
        plugin._workspace_root = temp_dir

        # Act
        with patch.object(plugin.logger, "error") as mock_error:
            result = plugin.get_state_before_json()

        # Assert
        assert result is None
        mock_error.assert_called_with("spacelift.state.before.json does not exist.")

    def test_custom_policy_input(
        self, temp_dir: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return custom policy input when file exists."""
        # Arrange
        monkeypatch.chdir(temp_dir)
        plugin = SpaceforgePlugin()
        plugin._is_local = False
        plugin._workspace_root = temp_dir
        custom_policy_data = {"test": "input"}

        # Act
        plugin.add_to_policy_input("test", custom_policy_data)

        with open(temp_dir + "/test.custom.spacelift.json", "r") as f:
            policy_data = json.load(f)

        # Assert
        assert policy_data == custom_policy_data
