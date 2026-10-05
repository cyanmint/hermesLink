# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""`ish` tool: run a shell command in HermesLink's persistent Alpine Linux
guest (the iSH-based kernel booted once per app process; see DEVELOP.md and
ishbridge/ish_kernel_bridge.m), alongside the existing `terminal` tool which
runs commands in the host ios_system environment.

This is a thin wrapper: it does not reimplement process execution. It
reuses the exact same native bridge the `terminal` tool's iOS local
backend uses to run ios_system commands asynchronously without blocking the
embedded Python interpreter's only thread (see tools/environments/local.py's
`_IosSystemAsyncProcess`, installed by
hermes/overlay/patches/patch-ios-stability.py) — here pointed at the native
`ish` shell command (Blink/Commands/ish.m / Resources/blinkCommandsDictionary.plist)
instead of a host `sh -c`. `ish` itself runs the user's command inside the
guest and prints only the guest's own output on the outer ios_system
stdout, so nothing further needs to be stripped here.
"""

from __future__ import annotations

import os
import select
import shlex
import sys
import time

from tools.registry import registry, tool_error, tool_result

# Hard cap mirroring TERMINAL's own foreground ceiling (tools/terminal_tool.py);
# kept independent so one tool's config can't silently change the other's limit.
ISH_MAX_FOREGROUND_TIMEOUT = 600
ISH_DEFAULT_TIMEOUT = 180


class _IshProcess:
    def __init__(self, native, task_id, output_fd, input_fd=None):
        self._native = native
        self._task_id = task_id
        self._native_closed = False
        self.pid = None
        self.returncode = None
        self.stdout = os.fdopen(output_fd, "r", encoding="utf-8", errors="replace")
        self.stdin = (
            os.fdopen(input_fd, "wb", buffering=0)
            if input_fd is not None else None
        )

    def _close_native(self):
        if not self._native_closed:
            self._native.close(self._task_id)
            self._native_closed = True

    def poll(self):
        if self.returncode is None:
            self.returncode = self._native.poll(self._task_id)
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = self._native.wait(self._task_id, timeout)
        if self.returncode is not None:
            self._close_native()
        return self.returncode

    def kill(self):
        if self.returncode is None:
            self._native.kill(self._task_id)
            self.wait(2.0)


class _IshPty:
    def __init__(self, process, interactive):
        self.process = process
        self.interactive = interactive

    def write(self, data):
        if not self.interactive or self.process.stdin is None:
            raise OSError("Process stdin not available")
        self.process.stdin.write(data)
        self.process.stdin.flush()

    def sendeof(self):
        if not self.interactive or self.process.stdin is None:
            raise OSError("Process stdin not available")
        self.write(b"\x04")
        self.process.stdin.close()

    def terminate(self, force=False):
        self.process.kill()

    def close(self):
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()


def _ios_system_runtime() -> bool:
    """True when running embedded in HermesLink's iOS ios_system host (or
    under test with HERMES_IOS_TERMINAL=1), mirroring the same check used by
    tools/terminal_tool.py's iOS-only code paths."""
    return sys.platform == "ios" or os.environ.get("HERMES_IOS_TERMINAL") == "1"


def check_ish_requirements() -> bool:
    """The guest only exists inside the iOS app's embedded ios_system host,
    and only once the native `_hermesios` async-process bridge is present."""
    if not _ios_system_runtime():
        return False
    try:
        import _hermesios  # noqa: F401
    except ImportError:
        return False
    return True


def _run_in_guest(command: str, timeout, workdir=None) -> str:
    import _hermesios

    if workdir is not None:
        command = f"cd {shlex.quote(workdir)} && {command}"
    ios_command = "ish -c " + shlex.quote(command)
    try:
        task_id, output_fd = _hermesios.spawn(ios_command)
    except OSError as error:
        return tool_error(f"could not start the ish guest command: {error}")

    output = bytearray()
    deadline = time.monotonic() + timeout
    output_open = True
    try:
        while True:
            status = _hermesios.poll(task_id)
            if status is not None:
                while output_open and select.select([output_fd], [], [], 0)[0]:
                    chunk = os.read(output_fd, 65536)
                    if not chunk:
                        output_open = False
                        break
                    output.extend(chunk)
                return tool_result(
                    output=output.decode("utf-8", errors="replace"),
                    exit_code=status,
                    status="completed" if status == 0 else "failed",
                )

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                try:
                    _hermesios.kill(task_id)
                except OSError:
                    pass
                _hermesios.wait(task_id, 2.0)
                return tool_error(
                    f"ish command timed out after {timeout}s and was killed",
                    exit_code=124, status="timeout",
                )

            if output_open:
                readable, _, _ = select.select([output_fd], [], [], min(0.1, remaining))
                if readable:
                    chunk = os.read(output_fd, 65536)
                    if chunk:
                        output.extend(chunk)
                    else:
                        output_open = False
            else:
                time.sleep(min(0.1, remaining))
    finally:
        _hermesios.close(task_id)
        os.close(output_fd)


def _spawn_background_in_guest(command, workdir, interactive, task_id, session_key, notify, watch_patterns):
    import _hermesios
    from tools.process_registry import process_registry

    guest_command = command
    if workdir is not None:
        guest_command = f"cd {shlex.quote(workdir)} && {guest_command}"
    ios_command = "ish -c " + shlex.quote(guest_command)
    try:
        spawned = _hermesios.spawn(ios_command, interactive)
    except OSError as error:
        return tool_error(f"could not start the iSH guest process: {error}")
    native_task_id, output_fd, *input_fds = spawned
    process = _IshProcess(
        _hermesios, native_task_id, output_fd,
        input_fd=input_fds[0] if input_fds else None,
    )
    session = None
    try:
        session_key = session_key or task_id or ""
        session = process_registry._new_session(
            command, task_id or "", task_id or "", session_key, workdir or "/",
        )
        session.process = process
        session._pty = _IshPty(process, interactive)
        session.notify_on_complete = notify
        session.watch_patterns = list(watch_patterns or [])
        result = {
            "output": "Background iSH process started",
            "session_id": session.id,
            "pid": None,
            "exit_code": 0,
            "status": "running",
        }
        if notify or watch_patterns:
            from tools.terminal_tool_background import (
                _apply_async_support, _register_completion_watcher,
            )

            notify, watch_patterns = _apply_async_support(
                session, result, notify, list(watch_patterns or []) or None,
            )
            session.notify_on_complete = bool(notify)
            session.watch_patterns = list(watch_patterns or [])
        process_registry._track_started(
            session, process_registry._reader_loop, f"ish-proc-reader-{session.id}",
        )
    except Exception:
        process.kill()
        process.wait(2.0)
        for stream in (process.stdout, process.stdin):
            if stream is not None:
                stream.close()
        _hermesios.close(native_task_id)
        raise

    if notify and session.watcher_platform:
        _register_completion_watcher(process_registry, session, session_key)
    return tool_result(**result)


def _handle_ish(args, **_kw):
    command = args.get("command")
    if not isinstance(command, str) or not command.strip():
        return tool_error("ish requires a non-empty 'command' string")
    background = bool(args.get("background", False))
    interactive = bool(args.get("pty", False))
    if interactive and not background:
        return tool_error(
            "pty requires background=true so the iSH guest session can be managed "
            "with process_manage write/submit actions."
        )
    notify = args.get("notify", args.get("notify_on_complete", False))
    watch_patterns = args.get("watch_patterns")
    if isinstance(notify, list):
        watch_patterns = notify
        notify = False
    if not isinstance(notify, bool):
        return tool_error("notify must be true/false or a list of strings")
    if watch_patterns is not None and (
        not isinstance(watch_patterns, list)
        or any(not isinstance(pattern, str) for pattern in watch_patterns)
    ):
        return tool_error("watch_patterns must be a list of strings")
    if args.get("heartbeat"):
        return tool_error("heartbeat notifications are not available for iSH processes")
    if not background and (notify or watch_patterns):
        return tool_error(
            "notify/heartbeat only apply to background commands (foreground "
            "results return directly). Either drop them, or run as "
            "ish(command=..., background=true, notify=...)."
        )
    workdir = args.get("workdir")
    if workdir is not None and (not isinstance(workdir, str) or not workdir.startswith("/")):
        return tool_error("workdir must be an absolute path inside the iSH guest")
    if background:
        try:
            from tools.approval import get_current_session_key
            session_key = get_current_session_key(default="") or _kw.get("task_id") or ""
        except ImportError:
            session_key = _kw.get("task_id") or ""

        return _spawn_background_in_guest(
            command, workdir, interactive, _kw.get("task_id"),
            session_key,
            notify, watch_patterns,
        )
    timeout = args.get("timeout") or ISH_DEFAULT_TIMEOUT
    try:
        timeout = min(float(timeout), ISH_MAX_FOREGROUND_TIMEOUT)
    except (TypeError, ValueError):
        timeout = ISH_DEFAULT_TIMEOUT
    return _run_in_guest(command, timeout, workdir=workdir)


ISH_SCHEMA = {
    "name": "ish",
    "description": (
        "Run a shell command inside HermesLink's persistent Alpine Linux guest "
        "(a real Linux kernel + userland, distinct from the host `terminal` "
        "tool's ios_system environment). Useful for tools that need an actual "
        "Linux syscall surface, apk-installable packages, or a filesystem that "
        "persists guest-side state across turns. Background sessions are managed "
        "with process_manage; add pty=true for an interactive guest terminal."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to run inside the Alpine guest (via /bin/sh -c).",
            },
            "background": {
                "type": "boolean",
                "description": "Run in the background and manage it with process_manage.",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": f"Foreground wait limit in seconds (default: {ISH_DEFAULT_TIMEOUT}, max: {ISH_MAX_FOREGROUND_TIMEOUT}); background sessions continue until stopped or completed.",
                "minimum": 1,
            },
            "workdir": {
                "type": "string",
                "description": "Absolute working directory inside the iSH guest.",
            },
            "pty": {
                "type": "boolean",
                "description": "With background=true, allow interactive input through the guest PTY.",
                "default": False,
            },
            "notify": {
                "description": "With background=true: notify on completion or matching output.",
                "anyOf": [
                    {"type": "boolean"},
                    {"type": "array", "items": {"type": "string"}},
                ],
            },
        },
        "required": ["command"],
    },
}

registry.register(
    name="ish",
    toolset="ish",
    schema=ISH_SCHEMA,
    handler=_handle_ish,
    check_fn=check_ish_requirements,
    emoji="🐧",
)
