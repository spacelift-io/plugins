"""Tests for PluginGenerator binary handling."""

from typing import Dict, List

import pytest

from spaceforge.cls import Binary
from spaceforge.generator import PluginGenerator
from spaceforge.plugin import SpaceforgePlugin


class TestPluginGeneratorBinaries:
    """Test binary extraction and installation command generation."""

    def test_should_extract_binaries_when_defined(self) -> None:
        """Should extract and return binary list when plugin defines them."""

        # Arrange
        class BinaryPlugin(SpaceforgePlugin):
            __binaries__ = [
                Binary(
                    name="test-cli",
                    download_urls={
                        "amd64": "https://example.com/test-cli-amd64",
                        "arm64": "https://example.com/test-cli-arm64",
                    },
                )
            ]

        generator = PluginGenerator()
        generator.plugin_class = BinaryPlugin

        # Act
        binaries = generator.get_plugin_binaries()

        # Assert
        assert binaries is not None
        assert len(binaries) == 1
        assert binaries[0].name == "test-cli"
        assert "amd64" in binaries[0].download_urls
        assert "arm64" in binaries[0].download_urls

    def test_should_return_none_when_no_binaries_defined(self) -> None:
        """Should return None when plugin has no binaries."""

        # Arrange
        class NoBinariesPlugin(SpaceforgePlugin):
            pass

        generator = PluginGenerator()
        generator.plugin_class = NoBinariesPlugin

        # Act
        binaries = generator.get_plugin_binaries()

        # Assert
        assert binaries is None

    def test_should_generate_binary_install_command_for_multi_arch(self) -> None:
        """Should generate installation commands for multiple architectures."""

        # Arrange
        class MultiArchPlugin(SpaceforgePlugin):
            __binaries__ = [
                Binary(
                    name="multi-cli",
                    download_urls={
                        "amd64": "https://example.com/multi-cli-amd64",
                        "arm64": "https://example.com/multi-cli-arm64",
                    },
                )
            ]

        generator = PluginGenerator()
        generator.plugin_class = MultiArchPlugin
        generator.plugin_working_directory = "/mnt/workspace/plugins/multiarch"
        generator.config = {
            "setup_virtual_env": "cd /mnt/workspace/plugins/multiarch && python -m venv ./venv && source venv/bin/activate && pip install spaceforge",
            "plugin_mounted_path": "/mnt/workspace/plugins/multiarch/plugin.py",
        }

        hooks: Dict[str, List[str]] = {"before_init": []}
        mounted_files: List = []

        # Act
        generator._generate_binary_install_command(hooks, mounted_files)

        # Assert
        # Should have added a script execution to hooks
        assert len(hooks["before_init"]) == 1
        command = hooks["before_init"][0]

        # Should have added a mounted file with script content
        assert len(mounted_files) == 1
        script_content = mounted_files[0].content

        # Check that hook command runs the script
        assert "chmod +x" in command
        assert "binary_install_multi-cli.sh" in command

        # Check script content contains binary installation logic
        assert "multi-cli" in script_content
        assert "https://example.com/multi-cli-amd64" in script_content
        assert "https://example.com/multi-cli-arm64" in script_content

    def test_should_not_add_commands_when_no_binaries(self) -> None:
        """Should not add installation commands when plugin has no binaries."""

        # Arrange
        class NoBinariesPlugin(SpaceforgePlugin):
            pass

        generator = PluginGenerator()
        generator.plugin_class = NoBinariesPlugin
        generator.plugin_working_directory = "/mnt/workspace/plugins/nobinaries"
        generator.config = {
            "setup_virtual_env": "cd /mnt/workspace/plugins/nobinaries && python -m venv ./venv && source venv/bin/activate && pip install spaceforge",
            "plugin_mounted_path": "/mnt/workspace/plugins/nobinaries/plugin.py",
        }

        hooks: Dict[str, List[str]] = {"before_init": []}
        mounted_files: List = []

        # Act
        generator._generate_binary_install_command(hooks, mounted_files)

        # Assert
        # No binaries should mean no new commands or files added
        assert len(hooks["before_init"]) == 0
        assert len(mounted_files) == 0

    def test_should_raise_error_when_binary_has_no_download_urls(self) -> None:
        """Should raise ValueError when binary has empty download URLs."""

        # Arrange
        class InvalidBinaryPlugin(SpaceforgePlugin):
            __binaries__ = [Binary(name="invalid", download_urls={})]

        generator = PluginGenerator()
        generator.plugin_class = InvalidBinaryPlugin
        generator.plugin_working_directory = "/mnt/workspace/plugins/invalidbinary"
        generator.config = {
            "setup_virtual_env": "cd /mnt/workspace/plugins/invalidbinary && python -m venv ./venv && source venv/bin/activate && pip install spaceforge",
            "plugin_mounted_path": "/mnt/workspace/plugins/invalidbinary/plugin.py",
        }

        hooks: Dict[str, List[str]] = {"before_init": []}
        mounted_files: List = []

        # Act & Assert
        with pytest.raises(ValueError, match="must have at least one download URL"):
            generator._generate_binary_install_command(hooks, mounted_files)

    def test_should_handle_single_architecture_binary(self) -> None:
        """Should generate appropriate commands for single architecture binary."""

        # Arrange
        class SingleArchPlugin(SpaceforgePlugin):
            __binaries__ = [
                Binary(
                    name="single-arch",
                    download_urls={"amd64": "https://example.com/binary-amd64"},
                )
            ]

        generator = PluginGenerator()
        generator.plugin_class = SingleArchPlugin
        generator.plugin_working_directory = "/mnt/workspace/plugins/singlearch"
        generator.config = {
            "setup_virtual_env": "cd /mnt/workspace/plugins/singlearch && python -m venv ./venv && source venv/bin/activate && pip install spaceforge",
            "plugin_mounted_path": "/mnt/workspace/plugins/singlearch/plugin.py",
        }

        hooks: Dict[str, List[str]] = {"before_init": []}
        mounted_files: List = []

        # Act
        generator._generate_binary_install_command(hooks, mounted_files)

        # Assert
        # Should have added a script execution to hooks
        assert len(hooks["before_init"]) == 1
        command = hooks["before_init"][0]

        # Should have added a mounted file with script content
        assert len(mounted_files) == 1
        script_content = mounted_files[0].content

        # Check that hook command runs the script
        assert "chmod +x" in command
        assert "binary_install_single-arch.sh" in command

        # Check script content contains the binary URL
        assert "https://example.com/binary-amd64" in script_content
