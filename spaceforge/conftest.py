"""Shared test fixtures for spaceforge tests."""

import os
import tempfile
from typing import Dict, Generator, List
from unittest.mock import Mock

import pytest

from spaceforge.plugin import SpaceforgePlugin


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Provide a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_plugin_content() -> str:
    """Basic test plugin content."""
    return """
from spaceforge import SpaceforgePlugin, Parameter

class TestPlugin(SpaceforgePlugin):
    __plugin_name__ = "test"
    __version__ = "1.0.0"
    __author__ = "Test Author"
    
    __parameters__ = [
        Parameter(
            name="test_param",
            description="Test parameter",
            required=False,
            default="default_value"
        )
    ]
    
    def after_plan(self) -> None:
        pass
"""


@pytest.fixture
def test_plugin_file(temp_dir: str, test_plugin_content: str) -> str:
    """Create a test plugin file."""
    plugin_path = os.path.join(temp_dir, "plugin.py")
    with open(plugin_path, "w") as f:
        f.write(test_plugin_content)
    return plugin_path


@pytest.fixture
def mock_env() -> Dict[str, str]:
    """Common test environment variables."""
    return {
        "SPACELIFT_API_TOKEN": "test_token",
        "TF_VAR_spacelift_graphql_endpoint": "https://test.spacelift.io",
    }


@pytest.fixture
def mock_api_response() -> Mock:
    """Mock API response for testing."""
    mock_response = Mock()
    mock_response.read.return_value = b'{"data": {"test": "result"}}'
    return mock_response


class ExampleTestPlugin(SpaceforgePlugin):
    """Reusable test plugin class."""

    __plugin_name__ = "example"
    __version__ = "1.0.0"
    __author__ = "Test"

    def __init__(self) -> None:
        super().__init__()
        self.hook_calls: List[str] = []

    def after_plan(self) -> None:
        self.hook_calls.append("after_plan")

    def before_apply(self) -> None:
        self.hook_calls.append("before_apply")
