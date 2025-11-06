#!/usr/bin/env python3
"""Validate all plugin files by importing them and checking for errors."""

import sys
import importlib.util
from pathlib import Path


def validate_plugin(plugin_dir: Path, plugin_file: Path) -> tuple[bool, str]:
    """
    Validate a plugin by importing it.

    Returns:
        tuple of (success: bool, error_message: str)
    """
    sys.path.insert(0, str(plugin_dir))

    try:
        # Clear any previous imports
        if "plugin" in sys.modules:
            del sys.modules["plugin"]

        spec = importlib.util.spec_from_file_location("plugin", plugin_file)
        if spec is None or spec.loader is None:
            return False, "Could not load spec"

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, ""
    except Exception as e:
        return False, str(e)
    finally:
        sys.path.pop(0)


def validate_plugins():
    """Validate all plugin.py files in the plugins directory."""
    failed = False
    plugins_dir = Path("plugins")

    if not plugins_dir.exists():
        print("Error: plugins directory not found")
        return 1

    plugin_files = list(plugins_dir.glob("*/plugin.py"))

    if not plugin_files:
        print("Warning: No plugin files found")
        return 0

    for plugin_file in sorted(plugin_files):
        plugin_dir = plugin_file.parent
        plugin_name = plugin_dir.name

        print(f"  Validating {plugin_name}...", end=" ", flush=True)

        success, error_msg = validate_plugin(plugin_dir, plugin_file)

        if success:
            print("✓")
        else:
            print("✗")
            print(f"    ERROR: {error_msg}")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(validate_plugins())
