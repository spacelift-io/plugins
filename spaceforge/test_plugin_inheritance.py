"""Tests for SpaceforgePlugin inheritance and customization."""

import os
from typing import Dict
from unittest.mock import patch

from spaceforge.plugin import SpaceforgePlugin


class TestSpaceforgePluginInheritance:
    """Test custom plugin creation and inheritance patterns."""

    def test_should_support_custom_plugin_with_metadata(self) -> None:
        """Should allow creation of custom plugins with metadata attributes."""

        # Arrange & Act
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

        # Assert
        assert plugin.__plugin_name__ == "custom"
        assert plugin.__version__ == "2.0.0"
        assert plugin.__author__ == "Custom Author"
        assert plugin.custom_state == "initialized"
        assert plugin.custom_method() == "custom_result"

        # Test hook override
        plugin.after_plan()
        assert plugin.custom_state == "plan_executed"

        # Test inherited functionality
        assert hasattr(plugin, "logger")
        assert hasattr(plugin, "run_cli")

    def test_should_support_complex_initialization_logic(self) -> None:
        """Should allow complex initialization patterns in custom plugins."""

        # Arrange & Act
        class ComplexPlugin(SpaceforgePlugin):
            def __init__(self) -> None:
                super().__init__()
                self.config = self._load_config()
                self.initialized = True

            def _load_config(self) -> Dict[str, str]:
                return {"setting1": "value1", "setting2": "value2"}

            def after_plan(self) -> None:
                self.config_info = f"Config loaded: {self.config}"

        plugin = ComplexPlugin()

        # Assert
        assert plugin.initialized is True
        assert plugin.config == {"setting1": "value1", "setting2": "value2"}

        plugin.after_plan()
        assert hasattr(plugin, "config_info")
        assert "Config loaded:" in plugin.config_info

    def test_should_support_environment_variable_access_in_custom_plugins(self) -> None:
        """Should allow custom plugins to access environment variables."""

        # Arrange
        class EnvPlugin(SpaceforgePlugin):
            def get_custom_env(self) -> str:
                return os.environ.get("CUSTOM_ENV", "default_value")

        plugin = EnvPlugin()

        # Act & Assert - no environment variable
        assert plugin.get_custom_env() == "default_value"

        # Act & Assert - with environment variable set
        with patch.dict(os.environ, {"CUSTOM_ENV": "custom_value"}):
            assert plugin.get_custom_env() == "custom_value"

    def test_should_share_logger_instances_across_plugin_instances(self) -> None:
        """Should use the same logger instance for multiple plugin instances of same class."""
        # Arrange & Act
        plugin1 = SpaceforgePlugin()
        plugin2 = SpaceforgePlugin()

        # Assert
        # Python loggers are singletons by name, so they should be the same instance
        assert plugin1.logger is plugin2.logger
        assert plugin1.logger.name == "spaceforge.SpaceforgePlugin"
        assert plugin2.logger.name == "spaceforge.SpaceforgePlugin"
