#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-settings-viewcontrollers-appearance-stylecustomizationview-swift'
TARGET = 'Settings/ViewControllers/Appearance/StyleCustomizationView.swift'
REPLACEMENTS = (
    (
        266,
        (
            '\n'
            '    var rawMode: Bool = false\n'
            '\n'
            '    func viewIsReady() {\n'
            '      guard let tv = termView else { return }\n'
            '      tv.setWidth(60)\n'
        ),
        (
            '\n'
            '    var rawMode: Bool = false\n'
            '\n'
            '    func attachInput(_ termInput: (UIView & TermInput)!) {}\n'
            '    func focus() {}\n'
            '\n'
            '    func viewIsReady() {\n'
            '      guard let tv = termView else { return }\n'
            '      tv.setWidth(60)\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-settings-viewcontrollers-appearance-stylecustomizationview-swift.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
