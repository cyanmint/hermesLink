import importlib.util
import os
import shlex
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

    def test_local_environment_runs_foreground_commands_without_popen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "local.py"
            path.write_text(
                "import contextlib\n"
                "import os\n"
                "import re\n"
                "import subprocess\n"
                "import sys\n"
                "import tempfile\n"
                "_IS_WINDOWS = False\n"
                "def _find_bash(): return '/bin/bash'\n"
                "def _make_run_env(env): return env\n"
                "def _pipe_stdin(proc, data): pass\n"
                "def windows_hide_flags(): return 0\n"
                "class BaseEnvironment:\n"
                "    pass\n"
                "    def _quote_cwd_for_cd(self, cwd): return \"'\" + cwd + \"'\"\n"
                "    def local_quote(self, value):\n"
                "        import shlex\n"
                "        return shlex.quote(value)\n"
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
                "    def _kill_process(self, proc): pass\n"
                "class SiblingEnvironment:\n"
                "    def _ios_system_runtime(self): return True\n"
                "    def init_session(self): self.sibling_init_called = True\n",
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
            sibling = namespace["SiblingEnvironment"]()
            sibling.init_session()
            self.assertTrue(sibling.sibling_init_called)
            self.assertFalse(hasattr(sibling, "_snapshot_ready"))
            env = env_type()
            env.cwd = "/Documents/workspace"
            env._cwd_marker = "__HERMES_CWD_test__"
            env.env = {"PATH": "/usr/bin:/bin", "TEST_VALUE": "with spaces"}
            calls = []

            def fake_system(command):
                calls.append(command)
                args = shlex.split(command)
                output_path = args[args.index(">") + 1]
                Path(output_path).write_text("ios-system-output\n", encoding="utf-8")
                return 7

            with patch.dict(os.environ, {"HERMES_IOS_TERMINAL": "1"}), patch.object(
                namespace["subprocess"], "Popen", side_effect=AssertionError("Popen must not run on iOS")
            ), patch.object(
                namespace["os"], "system", side_effect=fake_system
            ):
                env._snapshot_ready = True
                env._prefer_nonlogin = False
                env.init_session()
                self.assertFalse(env._snapshot_ready)
                self.assertTrue(env._prefer_nonlogin)
                wrapped = env._wrap_command("command -v rg 2>/dev/null", "/Documents/workspace")
                proc = env._run_bash(wrapped, login=True)
                with self.assertRaisesRegex(OSError, "does not support piped stdin"):
                    env._run_bash("read", stdin_data="answer")

            self.assertEqual(len(calls), 1)
            args = shlex.split(calls[0])
            self.assertEqual(args[:2], ["env", "-i"])
            self.assertIn("TEST_VALUE=with spaces", args)
            shell_index = args.index("sh")
            self.assertEqual(args[shell_index + 1], "-c")
            self.assertIn("cd '/Documents/workspace' && command -v rg 2>/dev/null", args[shell_index + 2])
            self.assertEqual(args[args.index(">") + 2 :], ["2>&1"])
            self.assertNotIn("HERMES_IOS_SYSTEM_SUBPROCESS", calls[0])
            self.assertEqual(proc.poll(), 7)
            self.assertEqual(proc.wait(), 7)
            self.assertEqual(proc.stdout.read(), "ios-system-output\n")
            proc.stdout.close()
            self.assertEqual(
                wrapped,
                "cd '/Documents/workspace' && command -v rg 2>/dev/null "
                "&& echo __HERMES_CWD_test__$PWD __HERMES_CWD_test__",
            )

    def test_local_environment_replaces_legacy_ios_popen_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "local.py"
            path.write_text(
                "import contextlib\n"
                "import os\n"
                "import re\n"
                "import subprocess\n"
                "import sys\n"
                "import tempfile\n"
                "_IS_WINDOWS = False\n"
                "def _find_bash(): return 'sh'\n"
                "def _make_run_env(env): return env\n"
                "class BaseEnvironment:\n"
                "    def _wrap_command(self, command, cwd): return command\n"
                "class LocalEnvironment(BaseEnvironment):\n"
                "    def _ios_system_runtime(self): return True\n"
                "    def _recover_cwd(self): pass\n"
                "    def _run_bash(self, cmd_string, *, login=False, timeout=120, stdin_data=None):\n"
                "        ios_system_runtime = self._ios_system_runtime()\n"
                "        bash = 'sh' if ios_system_runtime else _find_bash()\n"
                "        self._recover_cwd()\n"
                "        ios_run_env = _make_run_env(self.env)\n"
                "        if ios_system_runtime:\n"
                "            ios_run_env[\"HERMES_IOS_SYSTEM_SUBPROCESS\"] = \"1\"\n"
                "        proc = subprocess.Popen([bash, '-c', cmd_string], env=ios_run_env, cwd=self.cwd, start_new_session=not ios_system_runtime)\n"
                "        if not _IS_WINDOWS and not ios_system_runtime:\n"
                "            proc._hermes_pgid = os.getpgid(proc.pid)\n"
                "        return proc\n"
                "    def _kill_process(self, proc): pass\n",
                encoding="utf-8",
                newline="\n",
            )

            patcher.patch_ios_local_environment(path)
            first = path.read_text(encoding="utf-8")
            patcher.patch_ios_local_environment(path)
            self.assertEqual(path.read_text(encoding="utf-8"), first)
            namespace = {}
            exec(compile(first, str(path), "exec"), namespace)

            env = namespace["LocalEnvironment"]()
            env.cwd = "/Documents/workspace"
            env._cwd_marker = "__HERMES_CWD_test__"
            env.env = {"PATH": "/usr/bin:/bin"}
            calls = []

            def fake_system(command):
                calls.append(command)
                args = shlex.split(command)
                Path(args[args.index(">") + 1]).write_text("ok\n", encoding="utf-8")
                return 0

            with patch.object(
                namespace["subprocess"], "Popen", side_effect=AssertionError("legacy Popen path ran")
            ), patch.object(namespace["os"], "system", side_effect=fake_system):
                result = env._run_bash("cd '/Documents/workspace' && pwd", login=True)

            self.assertEqual(len(calls), 1)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.read(), "ok\n")
            result.stdout.close()
            self.assertNotIn("HERMES_IOS_SYSTEM_SUBPROCESS", first)

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
