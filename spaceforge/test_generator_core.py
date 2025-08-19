"""Tests for PluginGenerator core functionality."""

import os
from unittest.mock import Mock, patch

import pytest

from spaceforge.generator import PluginGenerator
from spaceforge.plugin import SpaceforgePlugin


class TestPluginGeneratorInitialization:
    """Test PluginGenerator initialization and configuration."""

    def test_should_initialize_with_custom_paths(self) -> None:
        """Should accept and store custom plugin and output paths."""
        # Arrange & Act
        generator = PluginGenerator("custom_plugin.py", "custom_output.yaml")

        # Assert
        assert generator.plugin_path == "custom_plugin.py"
        assert generator.output_path == "custom_output.yaml"
        assert generator.plugin_class is None
        assert generator.plugin_instance is None
        assert generator.plugin_working_directory is None

    def test_should_use_defaults_when_no_paths_provided(self) -> None:
        """Should use default paths when none specified."""
        # Arrange & Act
        generator = PluginGenerator()

        # Assert
        assert generator.plugin_path == "plugin.py"
        assert generator.output_path == "plugin.yaml"


class TestPluginGeneratorLoading:
    """Test plugin file loading functionality."""

    def test_should_raise_file_not_found_when_plugin_file_missing(self) -> None:
        """Should raise FileNotFoundError when plugin file doesn't exist."""
        # Arrange
        generator = PluginGenerator("nonexistent.py")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Plugin file not found"):
            generator.load_plugin()

    def test_should_raise_exception_when_plugin_file_has_syntax_errors(
        self, temp_dir: str
    ) -> None:
        """Should raise exception when plugin file has invalid Python syntax."""
        # Arrange
        invalid_path = os.path.join(temp_dir, "invalid.py")
        with open(invalid_path, "w") as f:
            f.write("invalid python syntax }")

        generator = PluginGenerator(invalid_path)

        # Act & Assert
        with pytest.raises(Exception):  # Could be syntax error or import error
            generator.load_plugin()

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

        generator = PluginGenerator(no_plugin_path)

        # Act & Assert
        with pytest.raises(ValueError, match="No SpaceforgePlugin subclass found"):
            generator.load_plugin()

    def test_should_load_plugin_successfully_when_valid_file_provided(
        self, test_plugin_file: str
    ) -> None:
        """Should successfully load plugin from valid file."""
        # Arrange
        generator = PluginGenerator(test_plugin_file)

        # Act
        generator.load_plugin()

        # Assert
        assert generator.plugin_class is not None
        assert generator.plugin_instance is not None
        assert generator.plugin_class.__name__ == "TestPlugin"
        assert generator.plugin_working_directory == "/mnt/workspace/plugins/test"

    @patch("spaceforge.generator.importlib.util.spec_from_file_location")
    def test_should_raise_import_error_when_spec_is_none(
        self, mock_spec: Mock, test_plugin_file: str
    ) -> None:
        """Should raise ImportError when importlib spec creation fails."""
        # Arrange
        mock_spec.return_value = None
        generator = PluginGenerator(test_plugin_file)

        # Act & Assert
        with pytest.raises(ImportError, match="Could not load plugin"):
            generator.load_plugin()


class TestPluginGeneratorMetadata:
    """Test metadata extraction functionality."""

    def test_should_extract_complete_metadata_when_all_attributes_present(self) -> None:
        """Should extract all metadata when plugin has complete attributes."""

        # Arrange
        class CompletePlugin(SpaceforgePlugin):
            """Complete test plugin."""

            __plugin_name__ = "complete_test"
            __version__ = "2.0.0"
            __author__ = "Test Author"

        generator = PluginGenerator()
        generator.plugin_class = CompletePlugin

        # Act
        metadata = generator.get_plugin_metadata()

        # Assert
        assert metadata["name_prefix"] == "complete_test"
        assert metadata["version"] == "2.0.0"
        assert metadata["author"] == "Test Author"
        assert metadata["description"] == "Complete test plugin."

    def test_should_use_defaults_when_metadata_attributes_missing(self) -> None:
        """Should use default values when plugin metadata attributes are missing."""

        # Arrange
        class MinimalPlugin(SpaceforgePlugin):
            pass

        generator = PluginGenerator()
        generator.plugin_class = MinimalPlugin

        # Act
        metadata = generator.get_plugin_metadata()

        # Assert
        assert metadata["name_prefix"] == "SpaceforgePlugin"  # inherited
        assert metadata["version"] == "1.0.0"  # inherited from base
        assert metadata["author"] == "Spacelift Team"  # inherited from base
        assert "MinimalPlugin" in metadata["description"]

    def test_should_generate_name_from_class_name_when_plugin_name_missing(
        self,
    ) -> None:
        """Should derive name from class name when __plugin_name__ not set."""

        # Arrange
        class MinimalPlugin:  # Don't inherit from SpaceforgePlugin
            __name__ = "MinimalPlugin"

        generator = PluginGenerator()
        generator.plugin_class = MinimalPlugin  # type: ignore[assignment]

        # Act
        metadata = generator.get_plugin_metadata()

        # Assert
        assert (
            metadata["name_prefix"] == "minimal"
        )  # class name lowercased with 'plugin' removed
        assert metadata["version"] == "1.0.0"  # default
        assert metadata["author"] == "Unknown"  # default
        assert "MinimalPlugin" in metadata["description"]
