#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-xcodeproj-project-pbxproj-06'
TARGET = 'Blink.xcodeproj/project.pbxproj'
REPLACEMENTS = (
    (
        4233,
        (
            '\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = "-Onone";\n'
            '\t\t\t\tSWIFT_VERSION = 5.0;\n'
            '\t\t\t\tTARGETED_DEVICE_FAMILY = "1,2";\n'
            '\t\t\t\tTEST_HOST = "$(BUILT_PRODUCTS_DIR)/Blink.app/Blink";\n'
            '\t\t\t};\n'
            '\t\t\tname = Debug;\n'
            '\t\t};\n'
        ),
        (
            '\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = "-Onone";\n'
            '\t\t\t\tSWIFT_VERSION = 5.0;\n'
            '\t\t\t\tTARGETED_DEVICE_FAMILY = "1,2";\n'
            '\t\t\t\tTEST_HOST = "$(BUILT_PRODUCTS_DIR)/HermesLink.app/HermesLink";\n'
            '\t\t\t};\n'
            '\t\t\tname = Debug;\n'
            '\t\t};\n'
        ),
    ),
    (
        4265,
        (
            '\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";\n'
            '\t\t\t\tSWIFT_VERSION = 5.0;\n'
            '\t\t\t\tTARGETED_DEVICE_FAMILY = "1,2";\n'
            '\t\t\t\tTEST_HOST = "$(BUILT_PRODUCTS_DIR)/Blink.app/Blink";\n'
            '\t\t\t};\n'
            '\t\t\tname = Release;\n'
            '\t\t};\n'
        ),
        (
            '\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";\n'
            '\t\t\t\tSWIFT_VERSION = 5.0;\n'
            '\t\t\t\tTARGETED_DEVICE_FAMILY = "1,2";\n'
            '\t\t\t\tTEST_HOST = "$(BUILT_PRODUCTS_DIR)/HermesLink.app/HermesLink";\n'
            '\t\t\t};\n'
            '\t\t\tname = Release;\n'
            '\t\t};\n'
        ),
    ),
    (
        4506,
        (
            '\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = "-Onone";\n'
            '\t\t\t\tSWIFT_VERSION = 5.0;\n'
            '\t\t\t\tTARGETED_DEVICE_FAMILY = "1,2";\n'
            '\t\t\t\tTEST_HOST = "$(BUILT_PRODUCTS_DIR)/Blink.app/$(BUNDLE_EXECUTABLE_FOLDER_PATH)/Blink";\n'
            '\t\t\t};\n'
            '\t\t\tname = Debug;\n'
            '\t\t};\n'
        ),
        (
            '\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = "-Onone";\n'
            '\t\t\t\tSWIFT_VERSION = 5.0;\n'
            '\t\t\t\tTARGETED_DEVICE_FAMILY = "1,2";\n'
            '\t\t\t\tTEST_HOST = "$(BUILT_PRODUCTS_DIR)/HermesLink.app/$(BUNDLE_EXECUTABLE_FOLDER_PATH)/HermesLink";\n'
            '\t\t\t};\n'
            '\t\t\tname = Debug;\n'
            '\t\t};\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-xcodeproj-project-pbxproj-06.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
