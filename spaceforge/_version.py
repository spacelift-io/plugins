"""
Version detection using setuptools_scm.
"""


def get_version() -> str:
    """
    Get the package version.

    Uses setuptools_scm generated version file, which is created during build.
    Falls back to a development version if not available.

    Returns:
        Version string
    """
    # Try setuptools-scm generated version file (created during build)
    try:
        from ._version_scm import version  # type: ignore[import-not-found]

        return str(version)
    except ImportError:
        pass

    # Try setuptools-scm directly (works in development)
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
