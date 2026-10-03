#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-migrator-1860migration-swift'
TARGET = 'Blink/Migrator/1860Migration.swift'
REPLACEMENTS = (
    (
        37,
        (
            '  func execute() throws {\n'
            '    BLKDefaults.loadDefaults()\n'
            '\n'
            '    let legacy = BLKDefaults.legacyInstance()!\n'
            '    let store = TerminalStyleStore.shared\n'
            '    let builtIn = TerminalStyle.makeBuiltInDefault()\n'
            '\n'
        ),
        (
            '  func execute() throws {\n'
            '    BLKDefaults.loadDefaults()\n'
            '\n'
            '    guard let legacy = BLKDefaults.legacyInstance() else {\n'
            '      return\n'
            '    }\n'
            '    let store = TerminalStyleStore.shared\n'
            '    let builtIn = TerminalStyle.makeBuiltInDefault()\n'
            '\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-migrator-1860migration-swift.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
