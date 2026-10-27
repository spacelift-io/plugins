"""Tests for PluginGenerator hook detection."""

import os
import pathlib

from pytest import MonkeyPatch

from spaceforge.generator import PluginGenerator
from spaceforge.plugin import SpaceforgePlugin


class TestPluginGeneratorHooks:
    """Test hook method detection functionality."""

    def test_should_detect_overridden_hook_methods(self) -> None:
        """Should identify hook methods that have been overridden in plugin."""

        # Arrange
        class HookedPlugin(SpaceforgePlugin):
            def after_plan(self) -> None:
                pass

            def before_apply(self) -> None:
                pass

        generator = PluginGenerator()
        generator.plugin_class = HookedPlugin

        # Act
        hooks = generator.get_available_hooks()

        # Assert
        assert "after_plan" in hooks
        assert "before_apply" in hooks
        assert len(hooks) == 2

    def test_should_return_empty_list_when_no_hooks_overridden(self) -> None:
        """Should return empty list when plugin has no overridden hook methods."""

        # Arrange
        class NoHooksPlugin(SpaceforgePlugin):
            pass

        generator = PluginGenerator()
        generator.plugin_class = NoHooksPlugin

        # Act
        hooks = generator.get_available_hooks()

        # Assert
        assert hooks == []

    def test_contexts_should_not_have_duplicates_pip_install_in_hooks(
        self, temp_dir: str, monkeypatch: MonkeyPatch
    ) -> None:
        """Should not have duplicate hook methods in the list."""

        # Arrange
        plugin_content = """
from spaceforge import SpaceforgePlugin
class DuplicateHooksPlugin(SpaceforgePlugin):
    def before_init(self) -> None:
        pass
        """

        requirements_content = """
requests
        """

        plugin_path = os.path.join(temp_dir, "plugin.py")
        with open(plugin_path, "w") as f:
            f.write(plugin_content)
        with open(os.path.join(temp_dir, "requirements.txt"), "w") as f:
            f.write(requirements_content)

        # Change to temporary directory (automatically restored after test)
        monkeypatch.chdir(temp_dir)

        generator = PluginGenerator(plugin_path)
        generator.load_plugin()

        # Act
        contexts = generator.get_plugin_contexts()
        hooks = contexts[0].hooks
        assert hooks is not None

        # Assert
        processed_hooks = []
        for hook in hooks["before_init"]:
            assert hook not in processed_hooks
            processed_hooks.append(hook)


def test_hook_script_runs_plugin_from_hook_cwd_without_project_root(
    tmp_path: pathlib.Path,
) -> None:
    """Module test runs leave TF_VAR_spacelift_project_root empty; the wrapper
    must run the plugin from the directory the hook started in."""
    import subprocess

    plugin_dir = os.path.join(tmp_path, "plugin")
    bin_dir = os.path.join(plugin_dir, "venv", "bin")
    os.makedirs(bin_dir)
    open(os.path.join(bin_dir, "activate"), "w").close()
    fake_python = os.path.join(bin_dir, "python")
    with open(fake_python, "w") as f:
        f.write('#!/bin/sh\n[ "$1" = "-m" ] && pwd\nexit 0\n')
    os.chmod(fake_python, 0o755)
    project_root = os.path.join(tmp_path, "examples")
    os.makedirs(project_root)

    script = (
        PluginGenerator()
        .jinja.get_template("ensure_spaceforge_and_run.sh.j2")
        .render(
            plugin_path=plugin_dir,
            plugin_file="plugin.py",
            phase="after_plan",
            has_binaries=False,
        )
    )
    env = {**os.environ, "TF_VAR_spacelift_project_root": ""}
    result = subprocess.run(
        ["sh", "-c", script],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == os.path.realpath(project_root)
