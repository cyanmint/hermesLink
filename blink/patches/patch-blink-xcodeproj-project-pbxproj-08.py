#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-xcodeproj-project-pbxproj-08'
TARGET = 'Blink.xcodeproj/project.pbxproj'
REPLACEMENTS = (
    (
        5233,
        (
            '\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = "$(BUNDLE_ID).BlinkTests";\n'
            '\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";\n'
            '\t\t\t\tSWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;\n'
            '\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = "-Onone";\n'
            '\t\t\t\tSWIFT_VERSION = 5.0;\n'
            '\t\t\t\tTEST_HOST = "$(BUILT_PRODUCTS_DIR)/Blink.app/Blink";\n'
            '\t\t\t};\n'
            '\t\t\tname = Debug;\n'
            '\t\t};\n'
        ),
        (
            '\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = "$(BUNDLE_ID).BlinkTests";\n'
            '\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";\n'
            '\t\t\t\tSWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;\n'
            '\t\t\t\tSWIFT_OBJC_BRIDGING_HEADER = "Blink/Blink-bridge.h";\n'
            '\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = "-Onone";\n'
            '\t\t\t\tSWIFT_VERSION = 5.0;\n'
            '\t\t\t\tTEST_HOST = "$(BUILT_PRODUCTS_DIR)/HermesLink.app/HermesLink";\n'
            '\t\t\t};\n'
            '\t\t\tname = Debug;\n'
            '\t\t};\n'
        ),
    ),
    (
        5267,
        (
            '\t\t\t\tMTL_FAST_MATH = YES;\n'
            '\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = "$(BUNDLE_ID).BlinkTests";\n'
            '\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";\n'
            '\t\t\t\tSWIFT_VERSION = 5.0;\n'
            '\t\t\t\tTEST_HOST = "$(BUILT_PRODUCTS_DIR)/Blink.app/Blink";\n'
            '\t\t\t};\n'
            '\t\t\tname = Release;\n'
            '\t\t};\n'
        ),
        (
            '\t\t\t\tMTL_FAST_MATH = YES;\n'
            '\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = "$(BUNDLE_ID).BlinkTests";\n'
            '\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";\n'
            '\t\t\t\tSWIFT_OBJC_BRIDGING_HEADER = "Blink/Blink-bridge.h";\n'
            '\t\t\t\tSWIFT_VERSION = 5.0;\n'
            '\t\t\t\tTEST_HOST = "$(BUILT_PRODUCTS_DIR)/HermesLink.app/HermesLink";\n'
            '\t\t\t};\n'
            '\t\t\tname = Release;\n'
            '\t\t};\n'
        ),
    ),
    (
        5391,
        (
            '\t\t\t\tCODE_SIGN_IDENTITY = "iPhone Developer";\n'
            '\t\t\t\t"CODE_SIGN_IDENTITY[sdk=iphoneos*]" = "iPhone Developer";\n'
            '\t\t\t\tCODE_SIGN_STYLE = Automatic;\n'
            '\t\t\t\tCURRENT_PROJECT_VERSION = 1097;\n'
            '\t\t\t\tDEAD_CODE_STRIPPING = NO;\n'
            '\t\t\t\tDEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";\n'
            '\t\t\t\tDEFINES_MODULE = YES;\n'
        ),
        (
            '\t\t\t\tCODE_SIGN_IDENTITY = "iPhone Developer";\n'
            '\t\t\t\t"CODE_SIGN_IDENTITY[sdk=iphoneos*]" = "iPhone Developer";\n'
            '\t\t\t\tCODE_SIGN_STYLE = Automatic;\n'
            '\t\t\t\tCURRENT_PROJECT_VERSION = 1098;\n'
            '\t\t\t\tDEAD_CODE_STRIPPING = NO;\n'
            '\t\t\t\tDEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";\n'
            '\t\t\t\tDEFINES_MODULE = YES;\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-xcodeproj-project-pbxproj-08.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
