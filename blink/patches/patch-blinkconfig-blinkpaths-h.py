#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blinkconfig-blinkpaths-h'
TARGET = 'BlinkConfig/BlinkPaths.h'
REPLACEMENTS = (
    (
        38,
        (
            '\n'
            '+ (NSString *) groupContainerPath;\n'
            '+ (NSString *) documentsPath;\n'
            '+ (NSString *) iCloudDriveDocuments;\n'
            '\n'
            '// ~/.blink\n'
        ),
        (
            '\n'
            '+ (NSString *) groupContainerPath;\n'
            '+ (NSString *) documentsPath;\n'
            '+ (NSString *) hermesHomePath;\n'
            '+ (NSString *) iCloudDriveDocuments;\n'
            '\n'
            '// ~/.blink\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blinkconfig-blinkpaths-h.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
