#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-smarterkeys-smarterterminput-swift'
TARGET = 'Blink/SmarterKeys/SmarterTermInput.swift'
REPLACEMENTS = (
    (
        246,
        (
            '      return\n'
            '    }\n'
            '    \n'
            '    if traitCollection.userInterfaceIdiom != .pad {\n'
            '//      needToReload = (_inputAccessoryView as? KBAccessoryView) == nil\n'
            '      _setupAccessoryView()\n'
            '    }\n'
            '    \n'
            '  }\n'
            '  \n'
        ),
        (
            '      return\n'
            '    }\n'
            '    \n'
            '    // The custom smart-key bar is also required above the iPad software\n'
            '    // keyboard. The old phone-only guard left iPad without an input accessory\n'
            '    // after the terminal was reattached.\n'
            '    _setupAccessoryView()\n'
            '    \n'
            '  }\n'
            '  \n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-smarterkeys-smarterterminput-swift.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
