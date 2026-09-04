import importlib.util
import threading
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

_PLUGIN_PATH = Path(__file__).with_name("plugin.py")
_PLUGIN_SPEC = importlib.util.spec_from_file_location("wiz_plugin", _PLUGIN_PATH)
if _PLUGIN_SPEC is None or _PLUGIN_SPEC.loader is None:
    raise ImportError(f"Could not load Wiz plugin from {_PLUGIN_PATH}")

_PLUGIN_MODULE = importlib.util.module_from_spec(_PLUGIN_SPEC)
_PLUGIN_SPEC.loader.exec_module(_PLUGIN_MODULE)
WizPlugin: Any = getattr(_PLUGIN_MODULE, "WizPlugin")


def test_run_scan_emits_heartbeat_while_wizcli_is_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = WizPlugin()
    heartbeat_seen = threading.Event()

    monkeypatch.setattr(plugin, "_SCAN_HEARTBEAT_INTERVAL_SECONDS", 0.01)

    def capture_log(message: str) -> None:
        if message == "Wiz scan is still running...":
            heartbeat_seen.set()

    def wait_for_heartbeat(
        *args: str, **kwargs: Any
    ) -> tuple[int, list[str], list[str]]:
        assert heartbeat_seen.wait(timeout=1)
        return 0, ["scan complete"], []

    with (
        patch.object(plugin.logger, "info", side_effect=capture_log),
        patch.object(plugin, "run_cli", side_effect=wait_for_heartbeat) as run_cli,
    ):
        result = plugin._run_scan("wizcli", "scan", "dir", "./")

    assert result == (0, ["scan complete"], [])
    run_cli.assert_called_once_with("wizcli", "scan", "dir", "./", print_output=False)
