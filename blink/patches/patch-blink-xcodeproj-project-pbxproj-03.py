#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-xcodeproj-project-pbxproj-03'
TARGET = 'Blink.xcodeproj/project.pbxproj'
REPLACEMENTS = (
    (
        1583,
        (
            '\t\t\t\tC94437641D838ABF0096F84E /* Fonts */,\n'
            '\t\t\t\tC944375F1D831CD30096F84E /* Themes */,\n'
            '\t\t\t\t0732F04A1D062B9A00AB5438 /* locales.bundle */,\n'
            '\t\t\t);\n'
            '\t\t\tpath = Resources;\n'
            '\t\t\tsourceTree = "<group>";\n'
        ),
        (
            '\t\t\t\tC94437641D838ABF0096F84E /* Fonts */,\n'
            '\t\t\t\tC944375F1D831CD30096F84E /* Themes */,\n'
            '\t\t\t\t0732F04A1D062B9A00AB5438 /* locales.bundle */,\n'
            '\t\t\t\tF10000060000000000000001 /* hermesrt.zip */,\n'
            '\t\t\t\tF2A5A0040000000000000001 /* WasmRuntime */,\n'
            '\t\t\t\t314E2F04FE0F5B60CB0D4E61 /* ish-rootfs.tar.gz */,\n'
            '\t\t\t);\n'
            '\t\t\tpath = Resources;\n'
            '\t\t\tsourceTree = "<group>";\n'
        ),
    ),
    (
        1603,
        (
            '\t\t\t\tD2334F0A25C1C3A000385378 /* OpenSSH.xcframework */,\n'
            '\t\t\t\tD2334ECA25C1C04700385378 /* files.xcframework */,\n'
            '\t\t\t\tD2334ED025C1C04700385378 /* ios_system.xcframework */,\n'
            '\t\t\t\tD2334EC425C1C04700385378 /* LibSSH.xcframework */,\n'
            '\t\t\t\tD2334EC525C1C04700385378 /* mosh.xcframework */,\n'
            '\t\t\t\tD2334EC625C1C04700385378 /* network_ios.xcframework */,\n'
        ),
        (
            '\t\t\t\tD2334F0A25C1C3A000385378 /* OpenSSH.xcframework */,\n'
            '\t\t\t\tD2334ECA25C1C04700385378 /* files.xcframework */,\n'
            '\t\t\t\tD2334ED025C1C04700385378 /* ios_system.xcframework */,\n'
            '\t\t\t\tF10000090000000000000001 /* HermesRuntime.framework */,\n'
            '\t\t\t\tD2334EC425C1C04700385378 /* LibSSH.xcframework */,\n'
            '\t\t\t\tD2334EC525C1C04700385378 /* mosh.xcframework */,\n'
            '\t\t\t\tD2334EC625C1C04700385378 /* network_ios.xcframework */,\n'
        ),
    ),
    (
        2053,
        (
            '\t\t\tisa = PBXGroup;\n'
            '\t\t\tchildren = (\n'
            '\t\t\t\tD2AD8E8327A2C80C00DED28D /* SettingsView.swift */,\n'
            '\t\t\t\tC94E9B611D6BA21C00DA4DD6 /* DismissSegue.h */,\n'
            '\t\t\t\tC94E9B621D6BA21C00DA4DD6 /* DismissSegue.m */,\n'
            '\t\t\t\tC9B2E0041D6B612300B89F69 /* Settings.storyboard */,\n'
        ),
        (
            '\t\t\tisa = PBXGroup;\n'
            '\t\t\tchildren = (\n'
            '\t\t\t\tD2AD8E8327A2C80C00DED28D /* SettingsView.swift */,\n'
            '\t\t\t\tF1A1CE5D0000000000000001 /* ISHRootfsSettingsView.swift */,\n'
            '\t\t\t\tC94E9B611D6BA21C00DA4DD6 /* DismissSegue.h */,\n'
            '\t\t\t\tC94E9B621D6BA21C00DA4DD6 /* DismissSegue.m */,\n'
            '\t\t\t\tC9B2E0041D6B612300B89F69 /* Settings.storyboard */,\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-xcodeproj-project-pbxproj-03.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
