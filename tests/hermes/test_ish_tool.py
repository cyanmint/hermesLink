import importlib.util
import os
import shlex
import sys
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "hermes" / "overlay" / "hermes" / "tools" / "ish_tool.py"


def _load_tool():
    tools_package = types.ModuleType("tools")
    tools_package.__path__ = []
    registry_module = types.ModuleType("tools.registry")
    registry_module.registry = types.SimpleNamespace(register=lambda **_: None)
    registry_module.tool_error = lambda message, **extra: {"error": message, **extra}
    registry_module.tool_result = lambda **result: result
    spec = importlib.util.spec_from_file_location("ish_tool_under_test", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"tools": tools_package, "tools.registry": registry_module}):
        spec.loader.exec_module(module)
    return module


class IshToolTests(unittest.TestCase):
    def test_drains_output_while_guest_command_is_running(self):
        module = _load_tool()
        payload = b"ish-output-" * 65536

        class FakeHermesIos:
            def __init__(self):
                self.read_fd = None
                self.writer = None

            def spawn(self, command):
                self.asserted_command = command
                self.read_fd, write_fd = os.pipe()

                def write_output():
                    try:
                        offset = 0
                        while offset < len(payload):
                            offset += os.write(write_fd, payload[offset:offset + 8192])
                    finally:
                        os.close(write_fd)

                self.writer = threading.Thread(target=write_output, daemon=True)
                self.writer.start()
                return 1, self.read_fd

            def poll(self, task_id):
                return None if self.writer.is_alive() else 0

            def wait(self, task_id, timeout=None):
                self.writer.join(timeout)
                return 0 if not self.writer.is_alive() else None

            def kill(self, task_id):
                raise AssertionError("completed test command must not be killed")

            def close(self, task_id):
                pass

        native = FakeHermesIos()
        with patch.dict(sys.modules, {"_hermesios": native}):
            result = module._run_in_guest("printf output", 5, workdir="/workspace with spaces")

        native.writer.join(1)
        self.assertFalse(native.writer.is_alive())
        self.assertEqual(result["output"].encode(), payload)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(
            shlex.split(native.asserted_command),
            ["ish", "-c", "cd '/workspace with spaces' && printf output"],
        )

    def test_terminal_compatible_foreground_options(self):
        module = _load_tool()
        self.assertEqual(
            set(module.ISH_SCHEMA["parameters"]["properties"]),
            {
                "command", "background", "timeout", "workdir", "pty", "notify",
                "heartbeat", "persist_on_release",
            },
        )

        with patch.object(module, "_run_in_guest", return_value="ran") as run:
            self.assertEqual(
                module._handle_ish({"command": "pwd", "timeout": 30, "workdir": "/tmp"}),
                "ran",
            )
        run.assert_called_once_with("pwd", 30.0, workdir="/tmp")

    def test_rejects_terminal_modes_unavailable_to_ios_ish_backend(self):
        module = _load_tool()
        for unsupported in ({"background": True}, {"pty": True}):
            with self.subTest(unsupported=unsupported):
                result = module._handle_ish({"command": "sleep 1", **unsupported})
                self.assertIn("foreground non-PTY", result["error"])

        result = module._handle_ish({"command": "pwd", "workdir": "relative/path"})
        self.assertIn("absolute path", result["error"])

    def test_rejects_background_only_options_on_foreground_ish_calls(self):
        module = _load_tool()
        result = module._handle_ish({"command": "pwd", "notify": True})
        self.assertIn("only apply to background", result["error"])

        result = module._handle_ish({"command": "pwd", "persist_on_release": True})
        self.assertIn("only applies to background", result["error"])


if __name__ == "__main__":
    unittest.main()
