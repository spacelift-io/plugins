"""
Plugin runner for executing hook methods.
"""

import importlib.util
import os
from typing import Optional


class PluginRunner:
    """Runs plugin hook methods."""

    def __init__(self, plugin_path: str = "plugin.py") -> None:
        """
        Initialize the runner.

        Args:
            plugin_path: Path to the plugin Python file
        """
        self.plugin_path = plugin_path
        self.plugin_instance: Optional[object] = None

    def load_plugin(self) -> None:
        """Load the plugin from the specified path."""
        if not os.path.exists(self.plugin_path):
            raise FileNotFoundError(f"Plugin file not found: {self.plugin_path}")

        # Load the module
        spec = importlib.util.spec_from_file_location("plugin_module", self.plugin_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load plugin from {self.plugin_path}")

        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)

        # Find the plugin class (should inherit from SpaceforgePlugin)
        from .plugin import SpaceforgePlugin

        plugin_class = None
        for attr_name in dir(plugin_module):
            attr = getattr(plugin_module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, SpaceforgePlugin)
                and attr != SpaceforgePlugin
            ):
                plugin_class = attr
                break

        if plugin_class is None:
            raise ValueError("No SpaceforgePlugin subclass found in plugin file")

        # Instantiate the plugin
        self.plugin_instance = plugin_class()

    def run_hook(self, hook_name: str) -> None:
        """
        Run a specific hook method.

        Args:
            hook_name: Name of the hook method to run
        """
        if self.plugin_instance is None:
            self.load_plugin()

        if not hasattr(self.plugin_instance, hook_name):
            print(f"Hook method '{hook_name}' not found in plugin")
            return

        method = getattr(self.plugin_instance, hook_name)
        if not callable(method):
            print(f"'{hook_name}' is not a callable method")
            return

        try:
            print(f"[SpaceForge] Running hook: {hook_name}")
            method()
            print(f"[SpaceForge] Hook completed: {hook_name}")
        except Exception as e:
            print(f"[SpaceForge] Error running hook '{hook_name}': {e}")
            raise


import click


@click.command(name="runner")
@click.argument("hook_name")
@click.option(
    "--plugin-file",
    default="plugin.py",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to the plugin Python file (default: plugin.py)",
)
def runner_command(hook_name: str, plugin_file: str) -> None:
    """Run a specific hook method from a plugin.

    HOOK_NAME: Name of the hook method to execute (e.g., after_plan, before_apply)

    This command is typically used internally by Spacelift to execute plugin hooks.
    """
    runner = PluginRunner(plugin_file)
    runner.run_hook(hook_name)
