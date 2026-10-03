#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-xcodeproj-project-pbxproj-05'
TARGET = 'Blink.xcodeproj/project.pbxproj'
REPLACEMENTS = (
    (
        2960,
        (
            '\t\t\t\tBDFA97312D7F49EF0020BBF2 /* ConfettiSwiftUI */,\n'
            '\t\t\t);\n'
            '\t\t\tproductName = Blink;\n'
            '\t\t\tproductReference = EA0BA18B1C0CC57B00719C1A /* Blink.app */;\n'
            '\t\t\tproductType = "com.apple.product-type.application";\n'
            '\t\t};\n'
            '/* End PBXNativeTarget section */\n'
        ),
        (
            '\t\t\t\tBDFA97312D7F49EF0020BBF2 /* ConfettiSwiftUI */,\n'
            '\t\t\t);\n'
            '\t\t\tproductName = Blink;\n'
            '\t\t\tproductReference = EA0BA18B1C0CC57B00719C1A /* HermesLink.app */;\n'
            '\t\t\tproductType = "com.apple.product-type.application";\n'
            '\t\t};\n'
            '/* End PBXNativeTarget section */\n'
        ),
    ),
    (
        3306,
        (
            '\t\t\t\t07E3AED11D9191B4007BC086 /* blink.png in Resources */,\n'
            '\t\t\t\tD21A3FE721943BE200269705 /* dark-app-ipad-76pt@2x.png in Resources */,\n'
            '\t\t\t\tBDE84C3C2BAE335100457391 /* vim in Resources */,\n'
            '\t\t\t\tC9B2E02F1D6B612400B89F69 /* Settings.storyboard in Resources */,\n'
            '\t\t\t\tD2496F3F20038B3300E75FE9 /* hterm_all.min.js in Resources */,\n'
            '\t\t\t\tD21A3FDB21943BE200269705 /* dark-settings-ipad-29pt@2x.png in Resources */,\n'
        ),
        (
            '\t\t\t\t07E3AED11D9191B4007BC086 /* blink.png in Resources */,\n'
            '\t\t\t\tD21A3FE721943BE200269705 /* dark-app-ipad-76pt@2x.png in Resources */,\n'
            '\t\t\t\tBDE84C3C2BAE335100457391 /* vim in Resources */,\n'
            '\t\t\t\tF10000050000000000000001 /* hermesrt.zip in Resources */,\n'
            '\t\t\t\tDCA2F5F653C2C3F9662E8822 /* ish-rootfs.tar.gz in Resources */,\n'
            '\t\t\t\tC9B2E02F1D6B612400B89F69 /* Settings.storyboard in Resources */,\n'
            '\t\t\t\tD2496F3F20038B3300E75FE9 /* hterm_all.min.js in Resources */,\n'
            '\t\t\t\tD21A3FDB21943BE200269705 /* dark-settings-ipad-29pt@2x.png in Resources */,\n'
        ),
    ),
    (
        3649,
        (
            '\t\t\t\tD2C24418238E44AB0082C69C /* KBConfigView.swift in Sources */,\n'
            '\t\t\t\tD2BF5F7F265BA0A80070F839 /* UserDefaults.swift in Sources */,\n'
            '\t\t\t\tD2F330CA20A6CB840074ADD7 /* help.m in Sources */,\n'
            '\t\t\t\tD28C357626A56DDF00202C4D /* FileProviderDomain.swift in Sources */,\n'
            '\t\t\t\tD241CBD223040734003D64A5 /* KBDevice.swift in Sources */,\n'
            '\t\t\t\tD23B4C6E2A6FCAC2002E689B /* SearchTextInput.swift in Sources */,\n'
        ),
        (
            '\t\t\t\tD2C24418238E44AB0082C69C /* KBConfigView.swift in Sources */,\n'
            '\t\t\t\tD2BF5F7F265BA0A80070F839 /* UserDefaults.swift in Sources */,\n'
            '\t\t\t\tD2F330CA20A6CB840074ADD7 /* help.m in Sources */,\n'
            '\t\t\t\tF10000010000000000000001 /* hermes.m in Sources */,\n'
            '\t\t\t\tF1A1CE560000000000000001 /* ish.m in Sources */,\n'
            '\t\t\t\tF1A1CE570000000000000001 /* ishfs.m in Sources */,\n'
            '\t\t\t\t3EC2EABECFB079180991531B /* ish_kernel_bridge_stub.m in Sources */,\n'
            '\t\t\t\tF1A1CE580000000000000001 /* ISHRootfsProfiles.m in Sources */,\n'
            '\t\t\t\tF1A1CE590000000000000001 /* ISHRootfsSettingsView.swift in Sources */,\n'
            '\t\t\t\tD28C357626A56DDF00202C4D /* FileProviderDomain.swift in Sources */,\n'
            '\t\t\t\tD241CBD223040734003D64A5 /* KBDevice.swift in Sources */,\n'
            '\t\t\t\tD23B4C6E2A6FCAC2002E689B /* SearchTextInput.swift in Sources */,\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-xcodeproj-project-pbxproj-05.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
