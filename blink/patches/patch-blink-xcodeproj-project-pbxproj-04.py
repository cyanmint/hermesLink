#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-xcodeproj-project-pbxproj-04'
TARGET = 'Blink.xcodeproj/project.pbxproj'
REPLACEMENTS = (
    (
        2437,
        (
            '\t\t\t\tD2334D1221495DAE00D26AC3 /* udptunnel */,\n'
            '\t\t\t\tD2F330D320A6F1DF0074ADD7 /* clear.m */,\n'
            '\t\t\t\tD2F330CB20A6D98C0074ADD7 /* config.m */,\n'
            '\t\t\t\tD264D2B528F84724002B1B14 /* whatsnew.m */,\n'
            '\t\t\t\tD2F330C920A6CB840074ADD7 /* help.m */,\n'
            '\t\t\t\tD263A7672AA9AFE7001C6CFC /* device_info.m */,\n'
        ),
        (
            '\t\t\t\tD2334D1221495DAE00D26AC3 /* udptunnel */,\n'
            '\t\t\t\tD2F330D320A6F1DF0074ADD7 /* clear.m */,\n'
            '\t\t\t\tD2F330CB20A6D98C0074ADD7 /* config.m */,\n'
            '\t\t\t\tF10000020000000000000001 /* hermes.m */,\n'
            '\t\t\t\tF1A1CE550000000000000001 /* ish.m */,\n'
            '\t\t\t\tF1A1CE5A0000000000000001 /* ishfs.m */,\n'
            '\t\t\t\tD264D2B528F84724002B1B14 /* whatsnew.m */,\n'
            '\t\t\t\tD2F330C920A6CB840074ADD7 /* help.m */,\n'
            '\t\t\t\tD263A7672AA9AFE7001C6CFC /* device_info.m */,\n'
        ),
    ),
    (
        2497,
        (
            '\t\t\t\t07F670621D05EEE200C0A53C /* Sessions */,\n'
            '\t\t\t\t0716B5231CFFAB9300268B5B /* Blink */,\n'
            '\t\t\t\tBDEC856B2E8397520096BF4C /* Common */,\n'
            '\t\t\t\tEA0BA18C1C0CC57B00719C1A /* Products */,\n'
            '\t\t\t);\n'
            '\t\t\tindentWidth = 2;\n'
            '\t\t\tsourceTree = "<group>";\n'
            '\t\t\ttabWidth = 2;\n'
            '\t\t};\n'
            '\t\tEA0BA18C1C0CC57B00719C1A /* Products */ = {\n'
            '\t\t\tisa = PBXGroup;\n'
            '\t\t\tchildren = (\n'
            '\t\t\t\tEA0BA18B1C0CC57B00719C1A /* Blink.app */,\n'
            '\t\t\t\tD265FBBA2317DD3C0017EAC4 /* BlinkTests.xctest */,\n'
            '\t\t\t\t07FABB8425C9AEC000E1CC2C /* SSH.framework */,\n'
            '\t\t\t\t07FABB8C25C9AEC100E1CC2C /* SSHTests.xctest */,\n'
        ),
        (
            '\t\t\t\t07F670621D05EEE200C0A53C /* Sessions */,\n'
            '\t\t\t\t0716B5231CFFAB9300268B5B /* Blink */,\n'
            '\t\t\t\tBDEC856B2E8397520096BF4C /* Common */,\n'
            '\t\t\t\tF027E8B0C7B7ACEAE2E693F1 /* ISHBridge */,\n'
            '\t\t\t\tEA0BA18C1C0CC57B00719C1A /* Products */,\n'
            '\t\t\t);\n'
            '\t\t\tindentWidth = 2;\n'
            '\t\t\tsourceTree = "<group>";\n'
            '\t\t\ttabWidth = 2;\n'
            '\t\t};\n'
            '\t\tF027E8B0C7B7ACEAE2E693F1 /* ISHBridge */ = {\n'
            '\t\t\tisa = PBXGroup;\n'
            '\t\t\tchildren = (\n'
            '\t\t\t\t165BD920B521DB9E8903D82D /* ish_path_safety.h */,\n'
            '\t\t\t\t7D974064786F253981F25015 /* ish_path_safety.c */,\n'
            '\t\t\t\t79DE6581D7BAC48AAD1ECC0B /* ish_rootfs.h */,\n'
            '\t\t\t\t34208DB0A0A73B1BACFEE7CE /* ish_rootfs.c */,\n'
            '\t\t\t\t191ABC14FEED1E0274186220 /* ish_exit_protocol.h */,\n'
            '\t\t\t\t6B7C99FC5893913D822D64FD /* ish_exit_protocol.c */,\n'
            '\t\t\t\t2E4F976EA6332326BB0C5C05 /* ish_kernel_bridge.h */,\n'
            '\t\t\t\tF8AA606AEC0B09E8279F79DF /* ish_kernel_bridge.m */,\n'
            '\t\t\t\t1E3F68EDDDED7F8AAF6CD86C /* ish_kernel_bridge_stub.m */,\n'
            '\t\t\t\tF1A1CE5B0000000000000001 /* ISHRootfsProfiles.m */,\n'
            '\t\t\t\tF1A1CE5C0000000000000001 /* ISHRootfsProfiles.h */,\n'
            '\t\t\t);\n'
            '\t\t\tpath = ISHBridge;\n'
            '\t\t\tsourceTree = "<group>";\n'
            '\t\t};\n'
            '\t\tEA0BA18C1C0CC57B00719C1A /* Products */ = {\n'
            '\t\t\tisa = PBXGroup;\n'
            '\t\t\tchildren = (\n'
            '\t\t\t\tEA0BA18B1C0CC57B00719C1A /* HermesLink.app */,\n'
            '\t\t\t\tD265FBBA2317DD3C0017EAC4 /* BlinkTests.xctest */,\n'
            '\t\t\t\t07FABB8425C9AEC000E1CC2C /* SSH.framework */,\n'
            '\t\t\t\t07FABB8C25C9AEC100E1CC2C /* SSHTests.xctest */,\n'
        ),
    ),
    (
        2927,
        (
            '\t\t\t\tEA0BA1871C0CC57B00719C1A /* Sources */,\n'
            '\t\t\t\tEA0BA1881C0CC57B00719C1A /* Frameworks */,\n'
            '\t\t\t\tEA0BA1891C0CC57B00719C1A /* Resources */,\n'
            '\t\t\t\t07A06D8C1D0618FC00ABEAFA /* Embed Frameworks */,\n'
            '\t\t\t\tD218069F25CC27C100B98902 /* Embed PlugIns */,\n'
            '\t\t\t);\n'
        ),
        (
            '\t\t\t\tEA0BA1871C0CC57B00719C1A /* Sources */,\n'
            '\t\t\t\tEA0BA1881C0CC57B00719C1A /* Frameworks */,\n'
            '\t\t\t\tEA0BA1891C0CC57B00719C1A /* Resources */,\n'
            '\t\t\t\tF100000A0000000000000001 /* Embed Ish.framework when enabled */,\n'
            '\t\t\t\t07A06D8C1D0618FC00ABEAFA /* Embed Frameworks */,\n'
            '\t\t\t\tD218069F25CC27C100B98902 /* Embed PlugIns */,\n'
            '\t\t\t);\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-xcodeproj-project-pbxproj-04.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
