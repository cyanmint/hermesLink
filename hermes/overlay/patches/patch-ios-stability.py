#!/usr/bin/env python3
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Apply iOS-only runtime safety patches to the packaged agent."""
from __future__ import annotations

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
    """Use ios_system's registered ``sh`` for synchronous local foreground commands."""
    text = path.read_text(encoding="utf-8")
    marker = "ios_system_runtime = self._ios_system_runtime()"
    if marker in text:
        return

    class_anchor = "class LocalEnvironment(BaseEnvironment):\n"
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
    text = text.replace(class_anchor, class_replacement, 1)

    method_start = text.find("    def _run_bash(")
    method_end = text.find("\n    def _kill_process(", method_start)
    if method_start < 0 or method_end < 0:
        raise SystemExit(f"LocalEnvironment _run_bash method boundary not found: {path}")
    method = text[method_start:method_end]
    replacements = (
        (
            "        bash = _find_bash()\n",
            '        ios_system_runtime = self._ios_system_runtime()\n'
            '        bash = "sh" if ios_system_runtime else _find_bash()\n',
            "LocalEnvironment shell discovery",
        ),
        (
            "        ios_system_runtime = self._ios_system_runtime()\n",
            "        ios_system_runtime = self._ios_system_runtime()\n"
            "        if ios_system_runtime and stdin_data is not None:\n"
            '            raise OSError("ios_system terminal does not support piped stdin")\n',
            "LocalEnvironment piped stdin capability guard",
        ),
        (
            "        if login:\n",
            "        if login and not ios_system_runtime:\n",
            "LocalEnvironment login shell",
        ),
        (
            '        args = [bash, *(["-l"] if login else []), "-c", cmd_string]\n',
            '        args = ["sh", "-c", cmd_string] if ios_system_runtime else [\n'
            '            bash, *(["-l"] if login else []), "-c", cmd_string,\n'
            "        ]\n",
            "LocalEnvironment shell argv",
        ),
        (
            "        self._recover_cwd()\n",
            "        self._recover_cwd()\n"
            "        ios_run_env = _make_run_env(self.env)\n"
            "        if ios_system_runtime:\n"
            '            ios_run_env["HERMES_IOS_SYSTEM_SUBPROCESS"] = "1"\n',
            "LocalEnvironment ios_system environment opt-in",
        ),
        (
            "env=_make_run_env(self.env)",
            "env=ios_run_env",
            "LocalEnvironment subprocess environment",
        ),
        (
            "            start_new_session=True, cwd=self.cwd,\n",
            "            start_new_session=not ios_system_runtime, cwd=self.cwd,\n",
            "LocalEnvironment process session",
        ),
        (
            "        if not _IS_WINDOWS:\n            with contextlib.suppress(ProcessLookupError):\n                proc._hermes_pgid = os.getpgid(proc.pid)\n",
            "        if not _IS_WINDOWS and not ios_system_runtime:\n"
            "            with contextlib.suppress(ProcessLookupError):\n"
            "                proc._hermes_pgid = os.getpgid(proc.pid)\n",
            "LocalEnvironment process-group probe",
        ),
    )
    for old, new, label in replacements:
        if method.count(old) != 1:
            raise SystemExit(f"{label} anchor expected once in {path}")
        method = method.replace(old, new, 1)
    text = text[:method_start] + method + text[method_end:]
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
