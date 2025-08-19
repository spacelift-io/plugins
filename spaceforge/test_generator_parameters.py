"""Tests for PluginGenerator parameter handling."""

from spaceforge.cls import Parameter
from spaceforge.generator import PluginGenerator
from spaceforge.plugin import SpaceforgePlugin


class TestPluginGeneratorParameters:
    """Test parameter extraction and processing."""

    def test_should_extract_parameters_when_defined(self) -> None:
        """Should extract and return parameter list when plugin defines them."""

        # Arrange
        class ParameterizedPlugin(SpaceforgePlugin):
            __parameters__ = [
                Parameter(
                    name="api_key",
                    description="API key for authentication",
                    required=True,
                    sensitive=True,
                ),
                Parameter(
                    name="endpoint",
                    description="API endpoint URL",
                    required=False,
                    default="https://api.example.com",
                ),
            ]

        generator = PluginGenerator()
        generator.plugin_class = ParameterizedPlugin

        # Act
        parameters = generator.get_plugin_parameters()

        # Assert
        assert parameters is not None
        assert len(parameters) == 2
        assert parameters[0].name == "api_key"
        assert parameters[0].sensitive is True
        assert parameters[1].name == "endpoint"
        assert parameters[1].default == "https://api.example.com"

    def test_should_return_none_when_no_parameters_defined(self) -> None:
        """Should return None when plugin has no parameters."""

        # Arrange
        class NoParamsPlugin(SpaceforgePlugin):
            pass

        generator = PluginGenerator()
        generator.plugin_class = NoParamsPlugin

        # Act
        parameters = generator.get_plugin_parameters()

        # Assert
        assert parameters is None
