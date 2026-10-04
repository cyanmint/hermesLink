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


def _run_in_guest(command: str, timeout) -> str:
    import _hermesios

    ios_command = "ish " + shlex.quote(command)
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


def _handle_ish(args, **_kw):
    command = args.get("command")
    if not isinstance(command, str) or not command.strip():
        return tool_error("ish requires a non-empty 'command' string")
    timeout = args.get("timeout") or ISH_DEFAULT_TIMEOUT
    try:
        timeout = min(float(timeout), ISH_MAX_FOREGROUND_TIMEOUT)
    except (TypeError, ValueError):
        timeout = ISH_DEFAULT_TIMEOUT
    return _run_in_guest(command, timeout)


ISH_SCHEMA = {
    "name": "ish",
    "description": (
        "Run a shell command inside HermesLink's persistent Alpine Linux guest "
        "(a real Linux kernel + userland, distinct from the host `terminal` "
        "tool's ios_system environment). Useful for tools that need an actual "
        "Linux syscall surface, apk-installable packages, or a filesystem that "
        "persists guest-side state across turns. Foreground only (like "
        "`terminal` on iOS); no background/PTY modes."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to run inside the Alpine guest (via /bin/sh -c).",
            },
            "timeout": {
                "type": "integer",
                "description": f"Max seconds to wait (default: {ISH_DEFAULT_TIMEOUT}, max: {ISH_MAX_FOREGROUND_TIMEOUT}).",
                "minimum": 1,
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
