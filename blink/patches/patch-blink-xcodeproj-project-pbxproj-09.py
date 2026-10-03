#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-xcodeproj-project-pbxproj-09'
TARGET = 'Blink.xcodeproj/project.pbxproj'
REPLACEMENTS = (
    (
        5403,
        (
            '\t\t\t\t\t"$(inherited)",\n'
            '\t\t\t\t);\n'
            '\t\t\t\tINFOPLIST_FILE = Blink/Info.plist;\n'
            '\t\t\t\tINFOPLIST_KEY_CFBundleDisplayName = "Blink Shell";\n'
            '\t\t\t\tINFOPLIST_KEY_LSApplicationCategoryType = "public.app-category.developer-tools";\n'
            '\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.6;\n'
            '\t\t\t\tLD_RUNPATH_SEARCH_PATHS = (\n'
        ),
        (
            '\t\t\t\t\t"$(inherited)",\n'
            '\t\t\t\t);\n'
            '\t\t\t\tINFOPLIST_FILE = Blink/Info.plist;\n'
            '\t\t\t\tINFOPLIST_KEY_CFBundleDisplayName = HermesLink;\n'
            '\t\t\t\tINFOPLIST_KEY_LSApplicationCategoryType = "public.app-category.developer-tools";\n'
            '\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.6;\n'
            '\t\t\t\tLD_RUNPATH_SEARCH_PATHS = (\n'
        ),
    ),
    (
        5414,
        (
            '\t\t\t\t\t"$(inherited)",\n'
            '\t\t\t\t\t"$(PROJECT_DIR)/Frameworks",\n'
            '\t\t\t\t);\n'
            '\t\t\t\tMARKETING_VERSION = 18.7.0;\n'
            '\t\t\t\tNEW_SETTING = "";\n'
            '\t\t\t\tOTHER_CFLAGS = "$(BLINK_OTHER_CFLAGS)";\n'
        ),
        (
            '\t\t\t\t\t"$(inherited)",\n'
            '\t\t\t\t\t"$(PROJECT_DIR)/Frameworks",\n'
            '\t\t\t\t);\n'
            '\t\t\t\tFRAMEWORK_SEARCH_PATHS = (\n'
            '\t\t\t\t\t"$(inherited)",\n'
            '\t\t\t\t\t"$(PROJECT_DIR)/Frameworks",\n'
            '\t\t\t\t);\n'
            '\t\t\t\tMARKETING_VERSION = 18.7.0;\n'
            '\t\t\t\tNEW_SETTING = "";\n'
            '\t\t\t\tOTHER_CFLAGS = "$(BLINK_OTHER_CFLAGS)";\n'
        ),
    ),
    (
        5427,
        (
            '\t\t\t\t);\n'
            '\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = "$(BUNDLE_ID)";\n'
            '\t\t\t\tPRODUCT_NAME = Blink;\n'
            '\t\t\t\tPROVISIONING_PROFILE_SPECIFIER = "";\n'
            '\t\t\t\tRUN_CLANG_STATIC_ANALYZER = YES;\n'
            '\t\t\t\tSTRIP_STYLE = "non-global";\n'
        ),
        (
            '\t\t\t\t);\n'
            '\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = "$(BUNDLE_ID)";\n'
            '\t\t\t\tPRODUCT_NAME = Blink;\n'
            '\t\t\t\tEXECUTABLE_NAME = HermesLink;\n'
            '\t\t\t\tPRODUCT_MODULE_NAME = Blink;\n'
            '\t\t\t\tWRAPPER_NAME = HermesLink.app;\n'
            '\t\t\t\tPROVISIONING_PROFILE_SPECIFIER = "";\n'
            '\t\t\t\tRUN_CLANG_STATIC_ANALYZER = YES;\n'
            '\t\t\t\tSTRIP_STYLE = "non-global";\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-xcodeproj-project-pbxproj-09.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
