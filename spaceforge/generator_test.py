import os
import tempfile
from typing import Optional
from unittest.mock import Mock, mock_open, patch

import pytest

from spaceforge.cls import (
    Binary,
    Context,
    MountedFile,
    Parameter,
    PluginManifest,
    Policy,
    Variable,
    Webhook,
)
from spaceforge.generator import PluginGenerator
from spaceforge.plugin import SpaceforgePlugin


class PluginExample(SpaceforgePlugin):
    """Test plugin for generator testing."""

    __plugin_name__ = "test_plugin"
    __version__ = "2.0.0"
    __author__ = "Test Author"

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

    __binaries__ = [
        Binary(
            name="test-cli",
            download_urls={
                "amd64": "https://example.com/test-cli-amd64",
                "arm64": "https://example.com/test-cli-arm64",
            },
        )
    ]

    __contexts__ = [
        Context(
            name_prefix="test_context",
            description="Test context",
            labels={"env": "test"},
            env=[Variable(key="TEST_VAR", value="test_value")],
        )
    ]

    __webhooks__ = [
        Webhook(
            name_prefix="test_webhook",
            endpoint="https://webhook.example.com",
            secrets=[Variable(key="SECRET_KEY", value_from_parameter="api_key")],
        )
    ]

    __policies__ = [
        Policy(
            name_prefix="test_policy",
            type="notification",
            body="package test",
            labels={"type": "security"},
        )
    ]

    def after_plan(self) -> None:
        """Override hook method."""
        pass

    def before_apply(self) -> None:
        """Override hook method."""
        pass


class TestPluginGenerator:

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_plugin_path = os.path.join(self.temp_dir, "plugin.py")
        self.test_output_path = os.path.join(self.temp_dir, "plugin.yaml")

        # Create a test plugin file
        with open(self.test_plugin_path, "w") as f:
            f.write(
                """
from spaceforge import SpaceforgePlugin, Parameter

class TestPlugin(SpaceforgePlugin):
    __plugin_name__ = "test"
    __version__ = "1.0.0"
    __author__ = "Test"
    
    __parameters__ = [
        Parameter(name="test_param", description="Test parameter", required=False, default="default_value")
    ]
    
    def after_plan(self) -> None:
        pass
"""
            )

    def teardown_method(self) -> None:
        """Cleanup test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plugin_generator_init(self) -> None:
        """Test PluginGenerator initialization."""
        generator = PluginGenerator("plugin_test.py", "output_test.yaml")

        assert generator.plugin_path == "plugin_test.py"
        assert generator.output_path == "output_test.yaml"
        assert generator.plugin_class is None
        assert generator.plugin_instance is None
        assert generator.plugin_working_directory is None

    def test_plugin_generator_init_defaults(self) -> None:
        """Test PluginGenerator initialization with default values."""
        generator = PluginGenerator()

        assert generator.plugin_path == "plugin.py"
        assert generator.output_path == "plugin.yaml"

    def test_load_plugin_file_not_found(self) -> None:
        """Test loading plugin when file doesn't exist."""
        generator = PluginGenerator("nonexistent.py")

        with pytest.raises(FileNotFoundError, match="Plugin file not found"):
            generator.load_plugin()

    def test_load_plugin_invalid_module(self) -> None:
        """Test loading invalid Python module."""
        invalid_path = os.path.join(self.temp_dir, "invalid.py")
        with open(invalid_path, "w") as f:
            f.write("invalid python syntax }")

        generator = PluginGenerator(invalid_path)

        with pytest.raises(Exception):  # Could be syntax error or import error
            generator.load_plugin()

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

        generator = PluginGenerator(no_plugin_path)

        with pytest.raises(ValueError, match="No SpaceforgePlugin subclass found"):
            generator.load_plugin()

    def test_load_plugin_success(self) -> None:
        """Test successful plugin loading."""
        generator = PluginGenerator(self.test_plugin_path)
        generator.load_plugin()

        assert generator.plugin_class is not None
        assert generator.plugin_instance is not None
        assert generator.plugin_class.__name__ == "TestPlugin"
        assert generator.plugin_working_directory == "/mnt/workspace/plugins/test"

    @patch("spaceforge.generator.importlib.util.spec_from_file_location")
    def test_load_plugin_spec_none(self, mock_spec: Mock) -> None:
        """Test plugin loading when spec is None."""
        mock_spec.return_value = None

        generator = PluginGenerator(self.test_plugin_path)

        with pytest.raises(ImportError, match="Could not load plugin"):
            generator.load_plugin()

    def test_get_plugin_metadata_with_all_attributes(self) -> None:
        """Test metadata extraction with all attributes present."""
        generator = PluginGenerator()
        generator.plugin_class = PluginExample

        metadata = generator.get_plugin_metadata()

        assert metadata["name_prefix"] == "test_plugin"
        assert metadata["version"] == "2.0.0"
        assert metadata["author"] == "Test Author"
        assert metadata["description"] == "Test plugin for generator testing."

    def test_get_plugin_metadata_with_defaults(self) -> None:
        """Test metadata extraction with missing attributes."""

        class MinimalPlugin(SpaceforgePlugin):
            pass

        generator = PluginGenerator()
        generator.plugin_class = MinimalPlugin

        metadata = generator.get_plugin_metadata()

        # MinimalPlugin inherits __plugin_name__ from SpaceforgePlugin
        assert metadata["name_prefix"] == "SpaceforgePlugin"
        assert metadata["version"] == "1.0.0"  # inherited from base
        assert metadata["author"] == "Spacelift Team"  # inherited from base
        assert "MinimalPlugin" in metadata["description"]

    def test_get_plugin_metadata_class_name_fallback(self) -> None:
        """Test metadata extraction using class name when __plugin_name__ not set."""

        # Test the fallback behavior by mocking the plugin class itself
        class MinimalPlugin:  # Don't inherit from SpaceforgePlugin
            __name__ = "MinimalPlugin"

        generator = PluginGenerator()
        generator.plugin_class = MinimalPlugin  # type: ignore[assignment]

        metadata = generator.get_plugin_metadata()

        # Should use class name fallback logic
        assert (
            metadata["name_prefix"] == "minimal"
        )  # class name lowercased with 'plugin' removed
        assert metadata["version"] == "1.0.0"  # default
        assert metadata["author"] == "Unknown"  # default
        assert "MinimalPlugin" in metadata["description"]

    def test_get_plugin_parameters(self) -> None:
        """Test parameter extraction."""
        generator = PluginGenerator()
        generator.plugin_class = PluginExample

        parameters = generator.get_plugin_parameters()

        assert parameters is not None
        assert len(parameters) == 2
        assert parameters[0].name == "api_key"
        assert parameters[0].sensitive is True
        assert parameters[1].name == "endpoint"
        assert parameters[1].default == "https://api.example.com"

    def test_get_plugin_parameters_none(self) -> None:
        """Test parameter extraction when no parameters defined."""

        class NoParamsPlugin(SpaceforgePlugin):
            pass

        generator = PluginGenerator()
        generator.plugin_class = NoParamsPlugin

        parameters = generator.get_plugin_parameters()
        assert parameters is None

    def test_get_available_hooks(self) -> None:
        """Test hook method detection."""
        generator = PluginGenerator()
        generator.plugin_class = PluginExample

        hooks = generator.get_available_hooks()

        assert "after_plan" in hooks
        assert "before_apply" in hooks
        assert len(hooks) == 2

    def test_get_available_hooks_no_overrides(self) -> None:
        """Test hook detection with no overridden methods."""

        class NoHooksPlugin(SpaceforgePlugin):
            pass

        generator = PluginGenerator()
        generator.plugin_class = NoHooksPlugin

        hooks = generator.get_available_hooks()
        assert hooks == []

    def test_get_plugin_binaries(self) -> None:
        """Test binary extraction."""
        generator = PluginGenerator()
        generator.plugin_class = PluginExample

        binaries = generator.get_plugin_binaries()

        assert binaries is not None
        assert len(binaries) == 1
        assert binaries[0].name == "test-cli"
        assert "amd64" in binaries[0].download_urls
        assert "arm64" in binaries[0].download_urls

    def test_get_plugin_binaries_none(self) -> None:
        """Test binary extraction when no binaries defined."""

        class NoBinariesPlugin(SpaceforgePlugin):
            pass

        generator = PluginGenerator()
        generator.plugin_class = NoBinariesPlugin

        binaries = generator.get_plugin_binaries()
        assert binaries is None

    def test_generate_binary_install_command(self) -> None:
        """Test binary installation command generation."""
        generator = PluginGenerator()
        generator.plugin_class = PluginExample

        command = generator.generate_binary_install_command()

        assert "mkdir -p /mnt/workspace/plugins/plugin_binaries" in command
        assert "curl https://example.com/test-cli-amd64" in command
        assert "curl https://example.com/test-cli-arm64" in command
        assert "arch" in command
        assert "x86_64" in command

    def test_generate_binary_install_command_no_binaries(self) -> None:
        """Test binary command generation when no binaries."""

        class NoBinariesPlugin(SpaceforgePlugin):
            pass

        generator = PluginGenerator()
        generator.plugin_class = NoBinariesPlugin

        command = generator.generate_binary_install_command()
        assert command == ""

    def test_generate_binary_install_command_missing_urls(self) -> None:
        """Test binary command generation with missing URLs."""

        class InvalidBinaryPlugin(SpaceforgePlugin):
            __binaries__ = [Binary(name="invalid", download_urls={})]

        generator = PluginGenerator()
        generator.plugin_class = InvalidBinaryPlugin

        with pytest.raises(ValueError, match="must have at least one download URL"):
            generator.generate_binary_install_command()

    def test_get_plugin_policies(self) -> None:
        """Test policy extraction."""
        generator = PluginGenerator()
        generator.plugin_class = PluginExample

        policies = generator.get_plugin_policies()

        assert policies is not None
        assert len(policies) == 1
        assert policies[0].name_prefix == "test_policy"
        assert policies[0].type == "notification"
        assert policies[0].body == "package test"

    def test_get_plugin_webhooks(self) -> None:
        """Test webhook extraction."""
        generator = PluginGenerator()
        generator.plugin_class = PluginExample

        webhooks = generator.get_plugin_webhooks()

        assert webhooks is not None
        assert len(webhooks) == 1
        assert webhooks[0].name_prefix == "test_webhook"
        assert webhooks[0].endpoint == "https://webhook.example.com"

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="requirements content")
    def test_get_plugin_contexts_with_requirements(
        self, mock_file: Mock, mock_exists: Mock
    ) -> None:
        """Test context generation with requirements.txt."""
        mock_exists.side_effect = (
            lambda path: path == "requirements.txt" or "plugin.py" in path
        )

        generator = PluginGenerator(self.test_plugin_path)
        generator.plugin_class = PluginExample
        generator.plugin_working_directory = "/mnt/workspace/plugins/test_plugin"

        contexts = generator.get_plugin_contexts()

        assert len(contexts) == 1
        context = contexts[0]

        # Should have before_init hooks for venv setup
        assert context.hooks is not None
        assert "before_init" in context.hooks
        venv_command = None
        for cmd in context.hooks["before_init"]:
            if "python -m venv" in cmd:
                venv_command = cmd
                break
        assert venv_command is not None

        # Should have requirements.txt as mounted file
        assert context.mounted_files is not None
        req_file = None
        for mf in context.mounted_files:
            if "requirements.txt" in mf.path:
                req_file = mf
                break
        assert req_file is not None
        assert req_file.content == "requirements content"

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="plugin content")
    def test_get_plugin_contexts_basic(
        self, mock_file: Mock, mock_exists: Mock
    ) -> None:
        """Test basic context generation."""
        mock_exists.side_effect = lambda path: "plugin.py" in path

        generator = PluginGenerator(self.test_plugin_path)
        generator.plugin_class = PluginExample
        generator.plugin_working_directory = "/mnt/workspace/plugins/test_plugin"

        with patch.object(
            generator, "get_available_hooks", return_value=["after_plan"]
        ):
            contexts = generator.get_plugin_contexts()

        assert len(contexts) == 1
        context = contexts[0]

        # Should have plugin file mounted
        assert context.mounted_files is not None
        plugin_file = None
        for mf in context.mounted_files:
            if "plugin.py" in mf.path:
                plugin_file = mf
                break
        assert plugin_file is not None

        # Should have spacepy runner hooks
        assert context.hooks is not None
        assert "after_plan" in context.hooks
        runner_command = context.hooks["after_plan"][0]
        assert "python -m spaceforge runner" in runner_command
        assert "after_plan" in runner_command

    def test_generate_manifest(self) -> None:
        """Test complete manifest generation."""
        generator = PluginGenerator(self.test_plugin_path)

        with patch.object(generator, "load_plugin"):
            generator.plugin_class = PluginExample
            manifest = generator.generate_manifest()

        assert isinstance(manifest, PluginManifest)
        assert manifest.version == "2.0.0"
        assert manifest.author == "Test Author"
        assert manifest.description == "Test plugin for generator testing."
        assert manifest.parameters is not None
        assert manifest.contexts is not None
        assert manifest.webhooks is not None
        assert manifest.policies is not None

    @patch("builtins.open", new_callable=mock_open)
    @patch("spaceforge.generator.yaml.dump")
    def test_write_yaml(self, mock_yaml_dump: Mock, mock_file: Mock) -> None:
        """Test YAML writing functionality."""
        generator = PluginGenerator(output_path=self.test_output_path)
        manifest = PluginManifest(
            name_prefix="test",
            version="1.0.0",
            description="Test",
            author="Test Author",
        )

        generator.write_yaml(manifest)

        mock_file.assert_called_once_with(self.test_output_path, "w")
        mock_yaml_dump.assert_called_once()

        # Verify yaml.dump was called with correct parameters
        args, kwargs = mock_yaml_dump.call_args
        assert args[0] == manifest
        assert kwargs["default_flow_style"] is False
        assert kwargs["sort_keys"] is False
        assert kwargs["indent"] == 2

    @patch.object(PluginGenerator, "write_yaml")
    @patch.object(PluginGenerator, "generate_manifest")
    def test_generate(
        self, mock_generate_manifest: Mock, mock_write_yaml: Mock
    ) -> None:
        """Test complete generate method."""
        generator = PluginGenerator()
        mock_manifest = PluginManifest(
            name_prefix="test", version="1.0.0", description="Test", author="Test"
        )
        mock_generate_manifest.return_value = mock_manifest

        generator.generate()

        mock_generate_manifest.assert_called_once()
        mock_write_yaml.assert_called_once_with(mock_manifest)

    def test_integration_full_workflow(self) -> None:
        """Integration test for complete workflow."""
        # Create a complete test plugin file
        full_plugin_path = os.path.join(self.temp_dir, "full_plugin.py")
        with open(full_plugin_path, "w") as f:
            f.write(
                '''
from spaceforge import SpaceforgePlugin, Parameter

class FullTestPlugin(SpaceforgePlugin):
    """A full test plugin."""
    
    __plugin_name__ = "full_test"
    __version__ = "1.5.0"
    __author__ = "Integration Test"
    
    __parameters__ = [
        Parameter(
            name="test_param",
            description="Test parameter",
            required=False,
            default="test_value"
        )
    ]
    
    def after_plan(self):
        """Override after_plan hook."""
        pass
'''
            )

        generator = PluginGenerator(full_plugin_path, self.test_output_path)

        # This should work end-to-end
        generator.load_plugin()
        assert generator.plugin_class is not None
        assert generator.plugin_class.__name__ == "FullTestPlugin"

        metadata = generator.get_plugin_metadata()
        assert metadata["name_prefix"] == "full_test"
        assert metadata["version"] == "1.5.0"

        hooks = generator.get_available_hooks()
        assert "after_plan" in hooks

        manifest = generator.generate_manifest()
        assert manifest.version == "1.5.0"
        assert manifest.description == "A full test plugin."


class TestPluginGeneratorEdgeCases:
    """Test edge cases and error conditions."""

    def test_plugin_with_docstring_multiline(self) -> None:
        """Test plugin with multiline docstring."""

        class MultilineDocPlugin(SpaceforgePlugin):
            """
            This is a multiline
            docstring with multiple
            lines of description.
            """

            pass

        generator = PluginGenerator()
        generator.plugin_class = MultilineDocPlugin

        metadata = generator.get_plugin_metadata()
        assert "multiline" in metadata["description"]
        assert "multiple" in metadata["description"]

    def test_plugin_class_name_with_plugin_suffix(self) -> None:
        """Test plugin class name ending with 'Plugin'."""

        class MyAwesomePlugin:  # Don't inherit from SpaceforgePlugin
            __name__ = "MyAwesomePlugin"

        generator = PluginGenerator()
        generator.plugin_class = MyAwesomePlugin  # type: ignore[assignment]

        metadata = generator.get_plugin_metadata()
        assert metadata["name_prefix"] == "myawesome"  # 'plugin' removed and lowercased

    def test_binary_install_single_arch(self) -> None:
        """Test binary installation with only one architecture."""

        class SingleArchPlugin(SpaceforgePlugin):
            __binaries__ = [
                Binary(
                    name="single-arch",
                    download_urls={"amd64": "https://example.com/binary-amd64"},
                )
            ]

        generator = PluginGenerator()
        generator.plugin_class = SingleArchPlugin

        command = generator.generate_binary_install_command()

        assert "https://example.com/binary-amd64" in command
        assert "arm64 binary not available" in command

    def test_context_merging_with_existing(self) -> None:
        """Test that generated hooks are merged with existing context hooks."""

        class ExistingHooksPlugin(SpaceforgePlugin):
            __plugin_name__ = "existing_hooks"

            __contexts__ = [
                Context(
                    name_prefix="existing",
                    description="Existing context",
                    hooks={"before_init": ["echo 'existing hook'"]},
                    mounted_files=[
                        MountedFile(
                            path="/existing", content="existing", sensitive=False
                        )
                    ],
                    env=[Variable(key="EXISTING", value="existing")],
                )
            ]

            def after_plan(self) -> None:
                pass

        generator = PluginGenerator("/fake/path")
        generator.plugin_class = ExistingHooksPlugin
        generator.plugin_working_directory = "/mnt/workspace/plugins/existing_hooks"

        with patch("os.path.exists") as mock_exists:
            # Only plugin file exists, not requirements.txt
            mock_exists.side_effect = lambda path: path == "/fake/path"
            with patch("builtins.open", mock_open(read_data="fake content")):
                contexts = generator.get_plugin_contexts()

        context = contexts[0]

        # The update() method replaces the existing hooks completely
        assert context.hooks is not None
        assert "after_plan" in context.hooks
        assert any("mkdir -p" in cmd for cmd in context.hooks["before_init"])

        # Should have both existing and generated mounted files
        assert context.mounted_files is not None
        existing_files = [mf for mf in context.mounted_files if mf.path == "/existing"]
        assert len(existing_files) == 1

        # Plugin file should be mounted (path contains the working directory)
        plugin_files = [
            mf
            for mf in context.mounted_files
            if "/mnt/workspace/plugins/existing_hooks" in mf.path
        ]
        assert len(plugin_files) == 1

        # Should have existing env vars
        assert context.env is not None
        existing_vars = [var for var in context.env if var.key == "EXISTING"]
        assert len(existing_vars) == 1
