"""Custom pylint checker for Spaceforge plugin conventions."""

import os
from typing import TYPE_CHECKING

from pylint.checkers import BaseChecker

if TYPE_CHECKING:
    from pylint.lint import PyLinter


class SpaceforgePluginChecker(BaseChecker):
    """Checker for Spaceforge plugin naming conventions."""

    name = "spaceforge-plugin"
    msgs = {
        "E9001": (
            "Plugin name '%s' should start with a capital letter",
            "plugin-name-not-capitalized",
            "The __plugin_name__ attribute must start with a capital letter for consistency.",
        ),
        "E9002": (
            "Plugin class '%s' must have a docstring",
            "plugin-missing-docstring",
            "All plugin classes extending SpaceforgePlugin must have a docstring explaining what the plugin does.",
        ),
    }

    def visit_classdef(self, node):
        """Check class definitions that extend SpaceforgePlugin."""
        # Skip test files
        filename = os.path.basename(node.root().file)
        if filename.startswith("test_") or filename == "conftest.py":
            return

        # Check if this class extends SpaceforgePlugin
        if not any(
            base.name == "SpaceforgePlugin"
            for base in node.bases
            if hasattr(base, "name")
        ):
            return

        # Check if the plugin class has a docstring
        # In astroid, docstrings are stored in the doc_node attribute
        if not node.doc_node:
            self.add_message(
                "plugin-missing-docstring",
                node=node,
                args=(node.name,),
            )

        # Look for __plugin_name__ attribute in the class body
        for item in node.body:
            if (
                hasattr(item, "targets")
                and len(item.targets) == 1
                and hasattr(item.targets[0], "name")
                and item.targets[0].name == "__plugin_name__"
            ):
                # Get the value of __plugin_name__
                if hasattr(item.value, "value") and isinstance(item.value.value, str):
                    plugin_name = item.value.value
                    if plugin_name and not plugin_name[0].isupper():
                        self.add_message(
                            "plugin-name-not-capitalized",
                            node=item,
                            args=(plugin_name,),
                        )
                break


def register(linter: "PyLinter") -> None:
    """Register the checker with pylint."""
    linter.register_checker(SpaceforgePluginChecker(linter))
