#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-xcodeproj-project-pbxproj-10'
TARGET = 'Blink.xcodeproj/project.pbxproj'
REPLACEMENTS = (
    (
        5451,
        (
            '\t\t\t\tCODE_SIGN_IDENTITY = "iPhone Developer";\n'
            '\t\t\t\t"CODE_SIGN_IDENTITY[sdk=iphoneos*]" = "iPhone Developer";\n'
            '\t\t\t\tCODE_SIGN_STYLE = Automatic;\n'
            '\t\t\t\tCURRENT_PROJECT_VERSION = 1097;\n'
            '\t\t\t\tDEAD_CODE_STRIPPING = NO;\n'
            '\t\t\t\tDEFINES_MODULE = YES;\n'
            '\t\t\t\tDEVELOPMENT_TEAM = A2H2CL32AG;\n'
            '\t\t\t\tENABLE_BITCODE = NO;\n'
            '\t\t\t\tGCC_PREPROCESSOR_DEFINITIONS = "";\n'
            '\t\t\t\tINFOPLIST_FILE = Blink/Info.plist;\n'
            '\t\t\t\tINFOPLIST_KEY_CFBundleDisplayName = "Blink Shell";\n'
            '\t\t\t\tINFOPLIST_KEY_LSApplicationCategoryType = "public.app-category.developer-tools";\n'
            '\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.6;\n'
            '\t\t\t\tLD_RUNPATH_SEARCH_PATHS = (\n'
        ),
        (
            '\t\t\t\tCODE_SIGN_IDENTITY = "iPhone Developer";\n'
            '\t\t\t\t"CODE_SIGN_IDENTITY[sdk=iphoneos*]" = "iPhone Developer";\n'
            '\t\t\t\tCODE_SIGN_STYLE = Automatic;\n'
            '\t\t\t\tCURRENT_PROJECT_VERSION = 0;\n'
            '\t\t\t\tDEAD_CODE_STRIPPING = NO;\n'
            '\t\t\t\tDEFINES_MODULE = YES;\n'
            '\t\t\t\tDEVELOPMENT_TEAM = A2H2CL32AG;\n'
            '\t\t\t\tENABLE_BITCODE = NO;\n'
            '\t\t\t\tGCC_PREPROCESSOR_DEFINITIONS = "";\n'
            '\t\t\t\tINFOPLIST_FILE = Blink/Info.plist;\n'
            '\t\t\t\tINFOPLIST_KEY_CFBundleDisplayName = HermesLink;\n'
            '\t\t\t\tINFOPLIST_KEY_LSApplicationCategoryType = "public.app-category.developer-tools";\n'
            '\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.6;\n'
            '\t\t\t\tLD_RUNPATH_SEARCH_PATHS = (\n'
        ),
    ),
    (
        5469,
        (
            '\t\t\t\t\t"$(inherited)",\n'
            '\t\t\t\t\t"$(PROJECT_DIR)/Frameworks",\n'
            '\t\t\t\t);\n'
            '\t\t\t\tMARKETING_VERSION = 18.8.0;\n'
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
            '\t\t\t\tMARKETING_VERSION = 18.8.0;\n'
            '\t\t\t\tNEW_SETTING = "";\n'
            '\t\t\t\tOTHER_CFLAGS = "$(BLINK_OTHER_CFLAGS)";\n'
        ),
    ),
    (
        5482,
        (
            '\t\t\t\t);\n'
            '\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = "$(BUNDLE_ID)";\n'
            '\t\t\t\tPRODUCT_NAME = Blink;\n'
            '\t\t\t\tPROVISIONING_PROFILE_SPECIFIER = "";\n'
            '\t\t\t\tSTRIP_STYLE = "non-global";\n'
            '\t\t\t\tSTRIP_SWIFT_SYMBOLS = NO;\n'
        ),
        (
            '\t\t\t\t);\n'
            '\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = "$(BUNDLE_ID)";\n'
            '\t\t\t\tPRODUCT_NAME = Blink;\n'
            '\t\t\t\tEXECUTABLE_NAME = HermesLink;\n'
            '\t\t\t\tPRODUCT_MODULE_NAME = Blink;\n'
            '\t\t\t\tWRAPPER_NAME = HermesLink.app;\n'
            '\t\t\t\tPROVISIONING_PROFILE_SPECIFIER = "";\n'
            '\t\t\t\tSTRIP_STYLE = "non-global";\n'
            '\t\t\t\tSTRIP_SWIFT_SYMBOLS = NO;\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-xcodeproj-project-pbxproj-10.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
