#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-migrator-migrator-swift'
TARGET = 'Blink/Migrator/Migrator.swift'
REPLACEMENTS = (
    (
        35,
        (
            '\n'
            '@objc class Migrator : NSObject {\n'
            '  @objc static func perform() {\n'
            '    Self.perform(steps: [MigrationToAppGroup(),\n'
            '                         MigrationAddSnippetsShortcut(),\n'
            '                         MigrationFileProviderReplicatedExtension(),\n'
            '                         MigrationStyleFromDefaults(),\n'
            '                         MigrationWipeSessionRegistry()\n'
            '                        ])\n'
        ),
        (
            '\n'
            '@objc class Migrator : NSObject {\n'
            '  @objc static func perform() {\n'
            '    // HermesLink has a new bundle identifier and therefore no legacy Blink\n'
            '    // data to migrate. More importantly, TrollStore/ad-hoc installs do not\n'
            '    // have the provisioned containers expected by these old migrations.\n'
            '    // Running them during launch can throw Objective-C exceptions before the\n'
            '    // first scene is created, so HermesLink must start without legacy work.\n'
            '    guard Bundle.main.bundleIdentifier != "com.hermeslink.app" else {\n'
            '      return\n'
            '    }\n'
            '\n'
            '    Self.perform(steps: [MigrationToAppGroup(),\n'
            '                         MigrationAddSnippetsShortcut(),\n'
            '                         MigrationStyleFromDefaults(),\n'
            '                         MigrationWipeSessionRegistry()\n'
            '                        ])\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-migrator-migrator-swift.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
