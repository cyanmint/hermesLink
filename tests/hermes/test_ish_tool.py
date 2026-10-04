import importlib.util
import os
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
            result = module._run_in_guest("printf output", 5)

        native.writer.join(1)
        self.assertFalse(native.writer.is_alive())
        self.assertEqual(result["output"].encode(), payload)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(native.asserted_command, "ish 'printf output'")


if __name__ == "__main__":
    unittest.main()
