"""
Spaceforge - Spacelift Plugin Framework

A Python framework for building Spacelift plugins with hook-based functionality.
"""

from spaceforge._version import get_version
from spaceforge.cls import (
    Binary,
    Context,
    MountedFile,
    Parameter,
    Policy,
    Variable,
    Webhook,
)
from spaceforge.plugin import SpaceforgePlugin
from spaceforge.runner import PluginRunner

__version__ = get_version()
__all__ = [
    "SpaceforgePlugin",
    "PluginRunner",
    "Parameter",
    "Variable",
    "Context",
    "Webhook",
    "Policy",
    "MountedFile",
    "Binary",
]
