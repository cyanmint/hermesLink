#!/usr/bin/env python3
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Register the `ish` tool (hermes/overlay/hermes/tools/ish_tool.py) alongside
`terminal` in the shared Hermes Agent core tool list and toolset catalog, so
every standard Hermes bundle (hermes-cli, hermes-telegram, the `coding`
posture, etc.) includes it the same way those bundles already include
`terminal`/`process_manage`. Applied to a staged copy of hermes-agent's
toolsets.py (never the pinned, ignored checkout under
hermes/build/external/hermes-agent) by hermes/build/build-hermesrt-zip.sh."""
from __future__ import annotations

import sys
from pathlib import Path


def patch_core_tools(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if '"ish",\n' in text or '"terminal", "process_manage", "ish"' in text:
        return
    anchor = '    "terminal", "process_manage",\n'
    if text.count(anchor) != 1:
        raise SystemExit(f"_HERMES_CORE_TOOLS terminal/process_manage anchor expected once: {path}")
    replacement = '    "terminal", "process_manage", "ish",\n'
    path.write_text(text.replace(anchor, replacement, 1), encoding="utf-8", newline="\n")


def patch_ish_toolset_entry(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if '"ish": _ts(' in text:
        return
    anchor = (
        '    "terminal": _ts("Terminal/command execution and process management tools", '
        '["terminal", "process_manage"]),\n'
    )
    if text.count(anchor) != 1:
        raise SystemExit(f"'terminal' TOOLSETS entry anchor expected once: {path}")
    replacement = anchor + (
        '    "ish": _ts(\n'
        '        "Run commands inside the persistent Alpine Linux guest (a real Linux "\n'
        '        "kernel/userland distinct from the host ios_system terminal)",\n'
        '        ["ish"],\n'
        '    ),\n'
    )
    path.write_text(text.replace(anchor, replacement, 1), encoding="utf-8", newline="\n")


def patch_debugging_toolset(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    anchor = (
        '    "debugging": _ts("Debugging and troubleshooting toolkit", '
        '["terminal", "process_manage"], includes=["web", "file"]),\n'
    )
    if anchor not in text:
        if '"debugging": _ts("Debugging and troubleshooting toolkit", ["terminal", "process_manage", "ish"]' in text:
            return
        raise SystemExit(f"'debugging' TOOLSETS entry anchor not found: {path}")
    replacement = (
        '    "debugging": _ts("Debugging and troubleshooting toolkit", '
        '["terminal", "process_manage", "ish"], includes=["web", "file"]),\n'
    )
    path.write_text(text.replace(anchor, replacement, 1), encoding="utf-8", newline="\n")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-ish-tool.py <staging-hermes-root>/toolsets.py")
    toolsets_path = Path(sys.argv[1])
    patch_core_tools(toolsets_path)
    patch_ish_toolset_entry(toolsets_path)
    patch_debugging_toolset(toolsets_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
