#!/usr/bin/env python3
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Apply iOS-only runtime safety patches to the packaged agent."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def patch_usage_pricing(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    anchor = '''    bundled_entry = _lookup_official_docs_pricing(route)\n    if bundled_entry:\n        return bundled_entry\n    if route.base_url:\n'''
    replacement = '''    bundled_entry = _lookup_official_docs_pricing(route)\n    if bundled_entry:\n        return bundled_entry\n    # iOS static builds must not perform the optional pricing metadata probe.\n    # That background requests/SSLContext path can abort the process in the\n    # statically linked OpenSSL runtime after an otherwise successful turn.\n    return None\n    if route.base_url:\n'''
    if "iOS static builds must not perform the optional pricing metadata probe." in text:
        return
    if anchor not in text:
        raise SystemExit(f"usage pricing patch anchor not found: {path}")
    path.write_text(text.replace(anchor, replacement, 1), encoding="utf-8", newline="\n")


def patch_process_title(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    anchor = "    import ctypes\n    import platform\n"
    replacement = "    try:\n        import ctypes\n    except ImportError:\n        return\n    import platform\n"
    if "except ImportError:\n        return\n    import platform" in text:
        return
    if anchor not in text:
        raise SystemExit(f"process title patch anchor not found: {path}")
    path.write_text(text.replace(anchor, replacement, 1), encoding="utf-8", newline="\n")


def patch_ios_terminal(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old = "    if not sys.stdin.isatty():\n"
    new = "    if not sys.stdin.isatty() and os.environ.get(\"HERMES_IOS_TERMINAL\") != \"1\":\n"
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"interactive terminal guard not found: {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def patch_ios_local_terminal(path: Path) -> None:
    """Allow foreground ios_system commands; reject unsupported async and PTY modes."""
    text = path.read_text(encoding="utf-8")
    marker = "ios_system local terminal supports foreground non-PTY commands only"
    if marker in text:
        return
    anchor = "        env = _acquire_env(plan, task_id)\n"
    legacy_marker = "CPython disables subprocess creation on iOS"
    if legacy_marker in text:
        legacy_at = text.index(legacy_marker)
        legacy_start = text.rfind('        if plan.env_type == "local" and (', 0, legacy_at)
        legacy_end = text.find(anchor, legacy_at)
        if legacy_start < 0 or legacy_end < 0:
            raise SystemExit(f"legacy iOS terminal guard boundaries not found: {path}")
        text = text[:legacy_start] + text[legacy_end:]
    replacement = '''        if plan.env_type == "local" and (
            sys.platform == "ios" or os.environ.get("HERMES_IOS_TERMINAL") == "1"
        ) and (background or pty):
            return _error_json(
                "The ios_system local terminal supports foreground non-PTY commands only; "
                "background processes and PTY sessions are unavailable.",
                exit_code=126,
                status="unsupported",
            )
        env = _acquire_env(plan, task_id)
'''
    if anchor not in text:
        raise SystemExit(f"local terminal environment acquisition anchor not found: {path}")
    path.write_text(text.replace(anchor, replacement, 1), encoding="utf-8", newline="\n")


def patch_ios_local_environment(path: Path) -> None:
    """Run local iOS shell commands through ios_system, never subprocess.Popen."""
    text = path.read_text(encoding="utf-8")
    if "class _IosSystemAsyncProcess:" in text:
        return

    if not re.search(r"(?m)^import shlex$", text):
        import_anchor = "import re\n"
        if text.count(import_anchor) != 1:
            raise SystemExit(f"LocalEnvironment import anchor expected once: {path}")
        text = text.replace(import_anchor, import_anchor + "import shlex\n", 1)

    class_anchor = "class LocalEnvironment(BaseEnvironment):\n"
    helper = '''class _IosSystemAsyncProcess:
    def __init__(self, native, task_id: int, output_fd: int):
        self._native = native
        self._task_id = task_id
        self._released = False
        self.pid = None
        self.returncode = None
        self.stdout = os.fdopen(output_fd, "r", encoding="utf-8", errors="replace")

    def _release(self):
        if not self._released:
            self._native.close(self._task_id)
            self._released = True

    def poll(self):
        if self.returncode is None:
            self.returncode = self._native.poll(self._task_id)
            if self.returncode is not None:
                self._release()
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = self._native.wait(self._task_id, timeout)
            if self.returncode is not None:
                self._release()
        return self.returncode

    def kill(self):
        if self.returncode is None:
            self._native.kill(self._task_id)
            self.returncode = self._native.wait(self._task_id, 2.0)
            self._release()


def _ios_system_run_command(command: str, env: dict):
    import _hermesios

    argv = ["env", "-i"]
    argv.extend(
        f"{key}={value}"
        for key, value in env.items()
        if isinstance(key, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
    )
    argv.extend(("sh", "-c", command))
    ios_command = " ".join(shlex.quote(argument) for argument in argv)
    task_id, output_fd = _hermesios.spawn(ios_command)
    return _IosSystemAsyncProcess(_hermesios, task_id, output_fd)


'''
    old_helper_anchor = "class _IosSystemCompletedProcess:\n"
    if old_helper_anchor in text:
        old_helper_start = text.index(old_helper_anchor)
        old_helper_end = text.find(class_anchor, old_helper_start)
        if old_helper_end < 0:
            raise SystemExit(f"legacy iOS process helper boundary not found: {path}")
        text = text[:old_helper_start] + helper + text[old_helper_end:]
    class_replacement = '''class LocalEnvironment(BaseEnvironment):
    def _ios_system_runtime(self) -> bool:
        return sys.platform == "ios" or os.environ.get("HERMES_IOS_TERMINAL") == "1"

    def init_session(self):
        if self._ios_system_runtime():
            # ios_system has no Bash login process or persistent shell snapshot.
            self._snapshot_ready = False
            self._prefer_nonlogin = True
            return
        return super().init_session()

    def _wrap_command(self, command: str, cwd: str) -> str:
        if self._ios_system_runtime():
            return (
                f"cd {self._quote_cwd_for_cd(cwd)} && {command} "
                f"&& echo {self._cwd_marker}$PWD {self._cwd_marker}"
            )
        return super()._wrap_command(command, cwd)
'''
    if text.count(class_anchor) != 1:
        raise SystemExit(f"LocalEnvironment class anchor expected once: {path}")
    initial_class_start = text.find(class_anchor)
    initial_body_start = initial_class_start + len(class_anchor)
    initial_sibling = re.search(r"(?m)^class ", text[initial_body_start:])
    initial_class_end = initial_body_start + initial_sibling.start() if initial_sibling else len(text)
    runtime_method_present = "def _ios_system_runtime(self)" in text[initial_class_start:initial_class_end]
    helper_present = "class _IosSystemAsyncProcess:" in text
    if not runtime_method_present:
        insertion = ("" if helper_present else helper) + class_replacement
        text = text.replace(class_anchor, insertion, 1)
    elif not helper_present:
        text = text.replace(class_anchor, helper + class_anchor, 1)

    local_class_start = text.find(class_anchor)
    local_body_start = local_class_start + len(class_anchor)
    sibling_class = re.search(r"(?m)^class ", text[local_body_start:])
    local_class_end = local_body_start + sibling_class.start() if sibling_class else len(text)
    local_class = text[local_class_start:local_class_end]
    init_matches = list(re.finditer(r"(?m)^(    def init_session\([^\n]*\)):(.*)\n", local_class))
    init_guard = (
        "        if self._ios_system_runtime():\n"
        "            self._snapshot_ready = False\n"
        "            self._prefer_nonlogin = True\n"
        "            return\n"
    )
    for init_match in reversed(init_matches):
        init_start = init_match.start()
        init_body = init_match.end()
        method_end = local_class.find("\n    def ", init_body)
        if method_end < 0:
            method_end = len(local_class)
        if init_guard not in local_class[init_body:method_end]:
            inline_body = init_match.group(2).strip()
            if inline_body:
                replacement = init_match.group(1) + ":\n" + init_guard + "        " + inline_body + "\n"
                local_class = local_class[:init_start] + replacement + local_class[init_body:]
            else:
                local_class = local_class[:init_body] + init_guard + local_class[init_body:]
    text = text[:local_class_start] + local_class + text[local_class_end:]

    local_class_start = text.find(class_anchor)
    local_body_start = local_class_start + len(class_anchor)
    sibling_class = re.search(r"(?m)^class ", text[local_body_start:])
    local_class_end = local_body_start + sibling_class.start() if sibling_class else len(text)
    local_class = text[local_class_start:local_class_end]
    method_start = local_class.find("    def _run_bash(")
    if method_start < 0:
        raise SystemExit(f"LocalEnvironment _run_bash method boundary not found: {path}")
    method_end = local_class.find("\n    def _kill_process(", method_start)
    if method_end < 0:
        method_end = local_class.find("\n    def ", method_start + len("    def _run_bash("))
    if method_end < 0:
        method_end = len(local_class)
    method = local_class[method_start:method_end]
    ios_line = "        ios_system_runtime = self._ios_system_runtime()\n"
    ios_branch = (
        "        if ios_system_runtime:\n"
        "            if stdin_data is not None:\n"
        '                raise OSError("ios_system terminal does not support piped stdin")\n'
        "            self._recover_cwd()\n"
        "            return _ios_system_run_command(cmd_string, _make_run_env(self.env))\n"
    )
    if ios_line in method:
        shell_anchor = "        bash = _find_bash()\n"
        branch_start = method.find("        if ios_system_runtime:\n", method.find(ios_line) + len(ios_line))
        shell_start = method.find(shell_anchor, branch_start)
        if branch_start >= 0 and shell_start >= 0:
            method = method[:branch_start] + ios_branch + method[shell_start:]
        elif ios_branch not in method:
            method = method.replace(ios_line, ios_line + ios_branch, 1)
    else:
        shell_anchor = "        bash = _find_bash()\n"
        if method.count(shell_anchor) != 1:
            raise SystemExit(f"LocalEnvironment shell discovery anchor expected once: {path}")
        method = method.replace(
            shell_anchor,
            "        ios_system_runtime = self._ios_system_runtime()\n" + ios_branch + shell_anchor,
            1,
        )
    method = method.replace(
        '        if ios_system_runtime:\n            ios_run_env["HERMES_IOS_SYSTEM_SUBPROCESS"] = "1"\n',
        "",
    )
    method = method.replace(") -> subprocess.Popen:", ") -> _IosSystemAsyncProcess | subprocess.Popen:", 1)
    local_class = local_class[:method_start] + method + local_class[method_end:]
    text = text[:local_class_start] + local_class + text[local_class_end:]

    local_class_start = text.find(class_anchor)
    local_body_start = local_class_start + len(class_anchor)
    sibling_class = re.search(r"(?m)^class ", text[local_body_start:])
    local_class_end = local_body_start + sibling_class.start() if sibling_class else len(text)
    local_class = text[local_class_start:local_class_end]
    kill_start = local_class.find("    def _kill_process(")
    ios_kill_guard = (
        "        if self._ios_system_runtime():\n"
        "            with contextlib.suppress(OSError):\n"
        "                proc.kill()\n"
        "            return\n"
    )
    if kill_start < 0:
        if local_class and not local_class.endswith("\n"):
            local_class += "\n"
        local_class += (
            "\n    def _kill_process(self, proc):\n"
            + ios_kill_guard
            + "        return super()._kill_process(proc)\n"
        )
        text = text[:local_class_start] + local_class + text[local_class_end:]
    else:
        signature_end = local_class.find("\n", kill_start)
        signature_line = local_class[kill_start:signature_end]
        if ":" not in signature_line:
            raise SystemExit(f"LocalEnvironment _kill_process signature malformed: {path}")
        header, inline_body = signature_line.split(":", 1)
        if ios_kill_guard not in local_class[signature_end + 1:]:
            if inline_body.strip():
                replacement = (
                    header
                    + ":\n"
                    + ios_kill_guard
                    + "        "
                    + inline_body.strip()
                    + "\n"
                )
                local_class = local_class[:kill_start] + replacement + local_class[signature_end + 1:]
            else:
                local_class = local_class[:signature_end + 1] + ios_kill_guard + local_class[signature_end + 1:]
        text = text[:local_class_start] + local_class + text[local_class_end:]
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-ios-stability.py <staging-hermes-root>")
    root = Path(sys.argv[1])
    patch_usage_pricing(root / "agent" / "usage_pricing.py")
    patch_process_title(root / "hermes_cli" / "main.py")
    patch_ios_terminal(root / "hermes_cli" / "main.py")
    patch_ios_local_terminal(root / "tools" / "terminal_tool.py")
    patch_ios_local_environment(root / "tools" / "environments" / "local.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
