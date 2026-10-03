#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-settings-model-terminalstyle-swift'
TARGET = 'Settings/Model/TerminalStyle.swift'
REPLACEMENTS = (
    (
        45,
        (
            '  var themeName: String\n'
            '  var fontName: String\n'
            '  var fontSize: CGFloat\n'
            '  var cursorBlink: Bool\n'
            '  var boldMode: BoldMode\n'
            '  var boldAsBright: Bool\n'
        ),
        (
            '  var themeName: String\n'
            '  var fontName: String\n'
            '  var fontSize: CGFloat\n'
            '  var externalDisplayFontSize: CGFloat = 24\n'
            '  var cursorBlink: Bool\n'
            '  var boldMode: BoldMode\n'
            '  var boldAsBright: Bool\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-settings-model-terminalstyle-swift.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
