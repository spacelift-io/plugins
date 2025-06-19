"""
Spaceforge - Spacelift Plugin Framework

A Python framework for building Spacelift plugins with hook-based functionality.
"""

from ._version import get_version
from .cls import Binary, Context, MountedFile, Parameter, Policy, Variable, Webhook
from .plugin import SpaceforgePlugin
from .runner import PluginRunner

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
