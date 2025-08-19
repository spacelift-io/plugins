"""
Dynamic version detection from git tags.
"""

import subprocess
from typing import Optional


def get_git_version() -> Optional[str]:
    """
    Get version from git tags.

    Returns:
        Version string (without 'v' prefix) or None if not available
    """
    try:
        # Try to get the current tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            capture_output=True,
            text=True,
            check=True,
        )
        tag = result.stdout.strip()
        # Remove 'v' prefix if present
        return tag[1:] if tag.startswith("v") else tag
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fall back to describe with commit info
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                capture_output=True,
                text=True,
                check=True,
            )
            tag = result.stdout.strip()
            # Remove 'v' prefix if present
            return tag[1:] if tag.startswith("v") else tag
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None


def get_version() -> str:
    """
    Get the package version.

    Tries git tags first, then setuptools-scm, falls back to default version.

    Returns:
        Version string
    """
    # Try git version first
    git_version = get_git_version()
    if git_version:
        return git_version

    # Try setuptools-scm generated version file
    try:
        from ._version_scm import version  # type: ignore[import-not-found]

        return str(version)
    except ImportError:
        pass

    # Try setuptools-scm directly
    try:
        from setuptools_scm import (
            get_version as scm_get_version,  # type: ignore[import-untyped]
        )

        result = scm_get_version(root="..", relative_to=__file__)
        return str(result)
    except ImportError:
        pass
    except Exception:
        # setuptools_scm might fail in various ways, ignore
        pass

    # Fall back to default version for development
    return "0.1.0-dev"
