#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-info-plist'
TARGET = 'Blink/Info.plist'
REPLACEMENTS = (
    (
        12,
        (
            '\t<key>CFBundleDevelopmentRegion</key>\n'
            '\t<string>en</string>\n'
            '\t<key>CFBundleDisplayName</key>\n'
            '\t<string>Blink</string>\n'
            '\t<key>CFBundleExecutable</key>\n'
            '\t<string>$(EXECUTABLE_NAME)</string>\n'
            '\t<key>CFBundleIcons</key>\n'
        ),
        (
            '\t<key>CFBundleDevelopmentRegion</key>\n'
            '\t<string>en</string>\n'
            '\t<key>CFBundleDisplayName</key>\n'
            '\t<string>HermesLink</string>\n'
            '\t<key>CFBundleExecutable</key>\n'
            '\t<string>$(EXECUTABLE_NAME)</string>\n'
            '\t<key>CFBundleIcons</key>\n'
        ),
    ),
    (
        130,
        (
            '\t<string>storing commands</string>\n'
            '\t<key>NSUbiquitousContainers</key>\n'
            '\t<dict>\n'
            '\t\t<key>iCloud.sh.blink.blinkshell</key>\n'
            '\t\t<dict>\n'
            '\t\t\t<key>NSUbiquitousContainerIsDocumentScopePublic</key>\n'
            '\t\t\t<true/>\n'
            '\t\t\t<key>NSUbiquitousContainerName</key>\n'
            '\t\t\t<string>Blink</string>\n'
            '\t\t\t<key>NSUbiquitousContainerSupportedFolderLevels</key>\n'
            '\t\t\t<string>Any</string>\n'
            '\t\t</dict>\n'
        ),
        (
            '\t<string>storing commands</string>\n'
            '\t<key>NSUbiquitousContainers</key>\n'
            '\t<dict>\n'
            '\t\t<key>iCloud.com.hermeslink.app</key>\n'
            '\t\t<dict>\n'
            '\t\t\t<key>NSUbiquitousContainerIsDocumentScopePublic</key>\n'
            '\t\t\t<true/>\n'
            '\t\t\t<key>NSUbiquitousContainerName</key>\n'
            '\t\t\t<string>HermesLink</string>\n'
            '\t\t\t<key>NSUbiquitousContainerSupportedFolderLevels</key>\n'
            '\t\t\t<string>Any</string>\n'
            '\t\t</dict>\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-info-plist.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
