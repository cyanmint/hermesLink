#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-blink-bridge-h'
TARGET = 'Blink/Blink-bridge.h'
REPLACEMENTS = (
    (
        33,
        (
            '#ifndef Blink_bridge_h\n'
            '#define Blink_bridge_h\n'
            '\n'
            '#include <stdio.h>\n'
            '#include <pthread.h>\n'
            '\n'
        ),
        (
            '#ifndef Blink_bridge_h\n'
            '#define Blink_bridge_h\n'
            '\n'
            '#import <UIKit/UIKit.h>\n'
            '#include <stdio.h>\n'
            '#include <pthread.h>\n'
            '\n'
        ),
    ),
    (
        43,
        (
            '\n'
            'typedef void (*mosh_state_callback) (const void *context, const void *buffer, size_t size);\n'
            '\n'
            '#import "BLKDefaults.h"\n'
            '#import "BKTheme.h"\n'
            '#import "BKFont.h"\n'
        ),
        (
            '\n'
            'typedef void (*mosh_state_callback) (const void *context, const void *buffer, size_t size);\n'
            '\n'
            'extern void HermesLinkAppendLog(const char *message);\n'
            'extern BOOL HermesLinkDiagnosticsEnabled(void);\n'
            'extern void HermesLinkSetDiagnosticsEnabled(BOOL enabled);\n'
            '\n'
            '#import "BLKDefaults.h"\n'
            '#import "BKTheme.h"\n'
            '#import "BKFont.h"\n'
        ),
    ),
    (
        69,
        (
            '#import "BlinkMenu.h"\n'
            '#import "GeoManager.h"\n'
            '#import "mosh/moshiosbridge.h"\n'
            '\n'
            '\n'
            '#endif /* Blink_bridge_h */\n'
        ),
        (
            '#import "BlinkMenu.h"\n'
            '#import "GeoManager.h"\n'
            '#import "mosh/moshiosbridge.h"\n'
            '#import "ISHRootfsProfiles.h"\n'
            '\n'
            '\n'
            '#endif /* Blink_bridge_h */\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-blink-bridge-h.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
