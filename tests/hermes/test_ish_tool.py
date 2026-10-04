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
    approval_module = types.ModuleType("tools.approval")
    approval_module.get_current_session_key = lambda default="": default
    spec = importlib.util.spec_from_file_location("ish_tool_under_test", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(
        sys.modules,
        {
            "tools": tools_package,
            "tools.registry": registry_module,
            "tools.approval": approval_module,
        },
    ):
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
            },
        )

        with patch.object(module, "_run_in_guest", return_value="ran") as run:
            self.assertEqual(
                module._handle_ish({"command": "pwd", "timeout": 30, "workdir": "/tmp"}),
                "ran",
            )
        run.assert_called_once_with("pwd", 30.0, workdir="/tmp")

    def test_background_pty_uses_tracked_process_session(self):
        module = _load_tool()
        class FakeRegistry:
            def _new_session(self, command, task_id, owner_task_id, session_key, cwd):
                return types.SimpleNamespace(
                    id="proc_test", command=command, task_id=task_id,
                    owner_task_id=owner_task_id, session_key=session_key, cwd=cwd,
                )

            def _reader_loop(self, session):
                pass

            def _track_started(self, session, reader, name):
                self.session = session

        class FakeHermesIos:
            def spawn(self, command, with_stdin=False):
                self.command = command
                self.with_stdin = with_stdin
                self.killed = False
                self.closed = False
                self.read_fd, write_fd = os.pipe()
                os.write(write_fd, b"started\n")
                os.close(write_fd)
                input_fd = None
                if with_stdin:
                    self.input_reader, input_fd = os.pipe()
                return (7, self.read_fd, input_fd) if with_stdin else (7, self.read_fd)

            def poll(self, task_id):
                return None

            def wait(self, task_id, timeout=None):
                return 130 if self.killed else None

            def kill(self, task_id):
                self.killed = True

            def close(self, task_id):
                self.closed = True

        native = FakeHermesIos()
        registry = FakeRegistry()
        process_registry_module = types.ModuleType("tools.process_registry")
        process_registry_module.process_registry = registry
        with patch.dict(
            sys.modules,
            {"_hermesios": native, "tools.process_registry": process_registry_module},
        ):
            result = module._handle_ish(
                {"command": "cat", "background": True, "pty": True, "workdir": "/tmp"},
                task_id="task-1",
            )

        self.assertEqual(result["session_id"], "proc_test")
        self.assertEqual(result["status"], "running")
        self.assertTrue(native.with_stdin)
        self.assertEqual(
            shlex.split(native.command),
            ["ish", "-c", "cd /tmp && cat"],
        )
        registry.session._pty.write(b"input\n")
        self.assertEqual(os.read(native.input_reader, 6), b"input\n")
        registry.session._pty.sendeof()
        self.assertEqual(os.read(native.input_reader, 1), b"\x04")
        registry.session._pty.terminate(force=True)
        self.assertTrue(native.killed)
        self.assertTrue(native.closed)
        registry.session.process.stdout.close()
        os.close(native.input_reader)

    def test_background_pipe_mode_does_not_allocate_interactive_stdin(self):
        module = _load_tool()
        class FakeRegistry:
            def _new_session(self, *args):
                return types.SimpleNamespace(id="proc_pipe")

            def _reader_loop(self, session):
                pass

            def _track_started(self, session, reader, name):
                self.session = session

        class FakeHermesIos:
            def spawn(self, command, with_stdin=False):
                self.with_stdin = with_stdin
                read_fd, write_fd = os.pipe()
                os.close(write_fd)
                return 9, read_fd

            def kill(self, task_id):
                pass

            def wait(self, task_id, timeout=None):
                return None

            def close(self, task_id):
                pass

        native = FakeHermesIos()
        registry = FakeRegistry()
        process_registry_module = types.ModuleType("tools.process_registry")
        process_registry_module.process_registry = registry
        with patch.dict(
            sys.modules,
            {"_hermesios": native, "tools.process_registry": process_registry_module},
        ):
            result = module._handle_ish({"command": "sleep 1", "background": True})
        self.assertFalse(native.with_stdin)
        self.assertIsNone(registry.session.process.stdin)
        self.assertEqual(result["session_id"], "proc_pipe")
        registry.session.process.stdout.close()

    def test_pty_requires_background_and_workdir_must_be_absolute(self):
        module = _load_tool()
        result = module._handle_ish({"command": "cat", "pty": True})
        self.assertIn("requires background=true", result["error"])
        result = module._handle_ish({"command": "pwd", "workdir": "relative/path"})
        self.assertIn("absolute path", result["error"])

    def test_background_only_notifications_require_background(self):
        module = _load_tool()
        result = module._handle_ish({"command": "pwd", "notify": True})
        self.assertIn("only apply to background", result["error"])


if __name__ == "__main__":
    unittest.main()
