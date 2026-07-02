#!/usr/bin/env python3
"""Validate all plugin files by importing them and checking for errors."""

import ast
import importlib.util
import sys
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


def check_conventions(plugin_file: Path) -> list[str]:
    """
    Check Spaceforge plugin conventions on a plugin's source.

    Every class extending SpaceforgePlugin must have a docstring and a
    __plugin_name__ that starts with a capital letter. (Previously enforced by a
    custom pylint checker.)
    """
    violations: list[str] = []
    tree = ast.parse(plugin_file.read_text(), filename=str(plugin_file))

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(
            isinstance(base, ast.Name) and base.id == "SpaceforgePlugin"
            for base in node.bases
        ):
            continue

        if ast.get_docstring(node) is None:
            violations.append(f"class '{node.name}' must have a docstring")

        for item in node.body:
            if (
                isinstance(item, ast.Assign)
                and len(item.targets) == 1
                and isinstance(item.targets[0], ast.Name)
                and item.targets[0].id == "__plugin_name__"
                and isinstance(item.value, ast.Constant)
                and isinstance(item.value.value, str)
                and item.value.value
                and not item.value.value[0].isupper()
            ):
                violations.append(
                    f"__plugin_name__ '{item.value.value}' should start with a capital letter"
                )

    return violations


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
        violations = check_conventions(plugin_file) if success else []

        if success and not violations:
            print("✓")
        else:
            print("✗")
            if error_msg:
                print(f"    ERROR: {error_msg}")
            for violation in violations:
                print(f"    ERROR: {violation}")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(validate_plugins())
