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
            "def terminal_tool(plan, task_id=None, background=False, pty=False):\n"
            "        env = _acquire_env(plan, task_id)\n"
            "        return env\n",
            encoding="utf-8",
            newline="\n",
        )
        return path

    def test_patches_ios_local_backend_and_leaves_api_backend_dispatch_available(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._terminal_module(directory)
            patcher.patch_ios_local_terminal(path)
            source = path.read_text(encoding="utf-8")
            namespace = {}
            exec(compile(source, str(path), "exec"), namespace)

            with patch.dict(os.environ, {"HERMES_IOS_TERMINAL": "1"}):
                local = namespace["terminal_tool"](SimpleNamespace(env_type="local"))
                background = namespace["terminal_tool"](
                    SimpleNamespace(env_type="local"), background=True
                )
                pty = namespace["terminal_tool"](SimpleNamespace(env_type="local"), pty=True)
                remote = namespace["terminal_tool"](SimpleNamespace(env_type="modal"))

            self.assertEqual(local, "environment-acquired")
            self.assertEqual(background["status"], "unsupported")
            self.assertEqual(pty["status"], "unsupported")
            self.assertIn("foreground", background["error"])
            self.assertEqual(remote, "environment-acquired")

    def test_ios_platform_without_marker_keeps_foreground_local_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._terminal_module(directory)
            patcher.patch_ios_local_terminal(path)
            namespace = {}
            exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)

            with patch.object(sys, "platform", "ios"), patch.dict(os.environ, {}, clear=True):
                result = namespace["terminal_tool"](SimpleNamespace(env_type="local"))

            self.assertEqual(result, "environment-acquired")

    def test_local_environment_uses_ios_system_sh_and_avoids_posix_process_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "local.py"
            path.write_text(
                "import os, subprocess, sys\n"
                "_IS_WINDOWS = False\n"
                "def _find_bash(): return '/bin/bash'\n"
                "def _make_run_env(env): return env\n"
                "def _pipe_stdin(proc, data): pass\n"
                "def windows_hide_flags(): return 0\n"
                "class BaseEnvironment:\n"
                "    pass\n"
                "    def _quote_cwd_for_cd(self, cwd): return \"'\" + cwd + \"'\"\n"
                "class LocalEnvironment(BaseEnvironment):\n"
                "    def init_session(self): super().init_session()\n"
                "    def _recover_cwd(self): pass\n"
                "    def _run_bash(self, cmd_string, login=False, timeout=120, stdin_data=None):\n"
                "        bash = _find_bash()\n"
                "        if login:\n"
                "            cmd_string = cmd_string + '-login'\n"
                "        args = [bash, *([\"-l\"] if login else []), \"-c\", cmd_string]\n"
                "        self._recover_cwd()\n"
                "        proc = subprocess.Popen(\n"
                "            args, env=_make_run_env(self.env),\n"
                "            start_new_session=True, cwd=self.cwd,\n"
                "        )\n"
                "        if not _IS_WINDOWS:\n"
                "            with contextlib.suppress(ProcessLookupError):\n"
                "                proc._hermes_pgid = os.getpgid(proc.pid)\n"
                "        return proc\n"
                "    def _kill_process(self, proc): pass\n",
                encoding="utf-8",
                newline="\n",
            )
            patcher.patch_ios_local_environment(path)
            source = path.read_text(encoding="utf-8")
            patcher.patch_ios_local_environment(path)
            self.assertEqual(path.read_text(encoding="utf-8"), source)
            namespace = {}
            exec(compile(source, str(path), "exec"), namespace)
            env_type = namespace["LocalEnvironment"]
            env = env_type()
            env.cwd = "/Documents/workspace"
            env._cwd_marker = "__HERMES_CWD_test__"
            env.env = {}
            calls = []

            class _Proc:
                pid = 123

            def fake_popen(args, **kwargs):
                calls.append((args, kwargs))
                return _Proc()

            with patch.dict(os.environ, {"HERMES_IOS_TERMINAL": "1"}), patch.object(
                namespace["subprocess"], "Popen", side_effect=fake_popen
            ):
                env._run_bash("pwd", login=True)
                wrapped = env._wrap_command("pwd", "/Documents/workspace")
                with self.assertRaisesRegex(OSError, "does not support piped stdin"):
                    env._run_bash("read", stdin_data="answer")

            self.assertEqual(calls[0][0], ["sh", "-c", "pwd"])
            self.assertFalse(calls[0][1]["start_new_session"])
            self.assertEqual(calls[0][1]["cwd"], "/Documents/workspace")
            self.assertEqual(calls[0][1]["env"]["HERMES_IOS_SYSTEM_SUBPROCESS"], "1")
            self.assertEqual(
                wrapped,
                "cd '/Documents/workspace' && pwd "
                "&& echo __HERMES_CWD_test__$PWD __HERMES_CWD_test__",
            )

    def test_patch_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._terminal_module(directory)
            patcher.patch_ios_local_terminal(path)
            first = path.read_text(encoding="utf-8")
            patcher.patch_ios_local_terminal(path)
            self.assertEqual(path.read_text(encoding="utf-8"), first)

    def test_missing_anchor_fails_build(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "terminal_tool.py"
            path.write_text("def terminal_tool():\n    pass\n", encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(SystemExit, "environment acquisition anchor not found"):
                patcher.patch_ios_local_terminal(path)


if __name__ == "__main__":
    unittest.main()
