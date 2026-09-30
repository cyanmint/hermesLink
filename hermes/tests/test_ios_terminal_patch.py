import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
PATCH_PATH = ROOT / "hermes" / "overlay" / "patches" / "patch-ios-stability.py"
SPEC = importlib.util.spec_from_file_location("ios_stability_patch_test", PATCH_PATH)
patcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patcher)


class IosTerminalPatchTests(unittest.TestCase):
    def _terminal_module(self, directory: str) -> Path:
        path = Path(directory) / "terminal_tool.py"
        path.write_text(
            "import os, sys\n"
            "def _error_json(error, **extra):\n"
            "    return {'error': error, **extra}\n"
            "def _acquire_env(plan, task_id):\n"
            "    return 'environment-acquired'\n"
            "def terminal_tool(plan, task_id=None):\n"
            "        env = _acquire_env(plan, task_id)\n"
            "        return env\n",
            encoding="utf-8",
            newline="\n",
        )
        return path

    def test_ios_local_backend_is_not_rejected_by_runtime_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._terminal_module(directory)
            source = path.read_text(encoding="utf-8")
            namespace = {}
            exec(compile(source, str(path), "exec"), namespace)

            with patch.dict(os.environ, {"HERMES_IOS_TERMINAL": "1"}):
                local = namespace["terminal_tool"](SimpleNamespace(env_type="local"))

            self.assertEqual(local, "environment-acquired")
            self.assertFalse(hasattr(patcher, "patch_ios_local_terminal"))

    def test_patch_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "main.py"
            path.write_text(
                "import os, sys\n"
                "def main():\n"
                "    if not sys.stdin.isatty():\n"
                "        return\n",
                encoding="utf-8",
                newline="\n",
            )
            patcher.patch_ios_terminal(path)
            first = path.read_text(encoding="utf-8")
            patcher.patch_ios_terminal(path)
            self.assertEqual(path.read_text(encoding="utf-8"), first)

    def test_missing_anchor_fails_build(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "main.py"
            path.write_text("def terminal_tool():\n    pass\n", encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(SystemExit, "interactive terminal guard not found"):
                patcher.patch_ios_terminal(path)


if __name__ == "__main__":
    unittest.main()
