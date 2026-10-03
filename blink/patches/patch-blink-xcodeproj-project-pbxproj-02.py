#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-xcodeproj-project-pbxproj-02'
TARGET = 'Blink.xcodeproj/project.pbxproj'
REPLACEMENTS = (
    (
        1249,
        (
            '\t\tD2ECBF4829645814004E95C4 /* BuildApi.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = BuildApi.swift; sourceTree = "<group>"; };\n'
            '\t\tD2ED4A6E239BB12E000DC67F /* KeyCaptureView.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = KeyCaptureView.swift; sourceTree = "<group>"; };\n'
            '\t\tD2F30EAC205009CD008C5F35 /* base64js.min.js */ = {isa = PBXFileReference; fileEncoding = 4; lastKnownFileType = sourcecode.javascript; path = base64js.min.js; sourceTree = "<group>"; };\n'
            '\t\tD2F330C920A6CB840074ADD7 /* help.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = help.m; sourceTree = "<group>"; };\n'
            '\t\tD2F330CB20A6D98C0074ADD7 /* config.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = config.m; sourceTree = "<group>"; };\n'
            '\t\tD2F330D120A6EF020074ADD7 /* showkey.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = showkey.m; sourceTree = "<group>"; };\n'
        ),
        (
            '\t\tD2ECBF4829645814004E95C4 /* BuildApi.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = BuildApi.swift; sourceTree = "<group>"; };\n'
            '\t\tD2ED4A6E239BB12E000DC67F /* KeyCaptureView.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = KeyCaptureView.swift; sourceTree = "<group>"; };\n'
            '\t\tD2F30EAC205009CD008C5F35 /* base64js.min.js */ = {isa = PBXFileReference; fileEncoding = 4; lastKnownFileType = sourcecode.javascript; path = base64js.min.js; sourceTree = "<group>"; };\n'
            '\t\tF10000020000000000000001 /* hermes.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = hermes.m; sourceTree = "<group>"; };\n'
            '\t\tF10000090000000000000001 /* HermesRuntime.framework */ = {isa = PBXFileReference; lastKnownFileType = wrapper.framework; path = HermesRuntime.framework; sourceTree = "<group>"; };\n'
            '\t\tF10000060000000000000001 /* hermesrt.zip */ = {isa = PBXFileReference; lastKnownFileType = archive.zip; path = hermesrt.zip; sourceTree = "<group>"; };\n'
            '\t\tF1A1CE550000000000000001 /* ish.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = ish.m; sourceTree = "<group>"; };\n'
            '\t\tF1A1CE5A0000000000000001 /* ishfs.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = ishfs.m; sourceTree = "<group>"; };\n'
            '\t\tF1A1CE5B0000000000000001 /* ISHRootfsProfiles.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = ISHRootfsProfiles.m; sourceTree = "<group>"; };\n'
            '\t\tF1A1CE5C0000000000000001 /* ISHRootfsProfiles.h */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.h; path = ISHRootfsProfiles.h; sourceTree = "<group>"; };\n'
            '\t\tF1A1CE5D0000000000000001 /* ISHRootfsSettingsView.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = ISHRootfsSettingsView.swift; sourceTree = "<group>"; };\n'
            '\t\t314E2F04FE0F5B60CB0D4E61 /* ish-rootfs.tar.gz */ = {isa = PBXFileReference; lastKnownFileType = archive.gzip; path = "ish-rootfs.tar.gz"; sourceTree = "<group>"; };\n'
            '\t\t165BD920B521DB9E8903D82D /* ish_path_safety.h */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.h; path = ish_path_safety.h; sourceTree = "<group>"; };\n'
            '\t\t7D974064786F253981F25015 /* ish_path_safety.c */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.c; path = ish_path_safety.c; sourceTree = "<group>"; };\n'
            '\t\t79DE6581D7BAC48AAD1ECC0B /* ish_rootfs.h */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.h; path = ish_rootfs.h; sourceTree = "<group>"; };\n'
            '\t\t34208DB0A0A73B1BACFEE7CE /* ish_rootfs.c */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.c; path = ish_rootfs.c; sourceTree = "<group>"; };\n'
            '\t\t191ABC14FEED1E0274186220 /* ish_exit_protocol.h */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.h; path = ish_exit_protocol.h; sourceTree = "<group>"; };\n'
            '\t\t6B7C99FC5893913D822D64FD /* ish_exit_protocol.c */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.c; path = ish_exit_protocol.c; sourceTree = "<group>"; };\n'
            '\t\t2E4F976EA6332326BB0C5C05 /* ish_kernel_bridge.h */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.h; path = ish_kernel_bridge.h; sourceTree = "<group>"; };\n'
            '\t\tF8AA606AEC0B09E8279F79DF /* ish_kernel_bridge.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = ish_kernel_bridge.m; sourceTree = "<group>"; };\n'
            '\t\t1E3F68EDDDED7F8AAF6CD86C /* ish_kernel_bridge_stub.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = ish_kernel_bridge_stub.m; sourceTree = "<group>"; };\n'
            '\t\tD2F330C920A6CB840074ADD7 /* help.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = help.m; sourceTree = "<group>"; };\n'
            '\t\tD2F330CB20A6D98C0074ADD7 /* config.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = config.m; sourceTree = "<group>"; };\n'
            '\t\tD2F330D120A6EF020074ADD7 /* showkey.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = showkey.m; sourceTree = "<group>"; };\n'
        ),
    ),
    (
        1277,
        (
            '\t\tD2F64C9525CA99AD00F2225D /* libssh2.xcframework */ = {isa = PBXFileReference; lastKnownFileType = wrapper.xcframework; name = libssh2.xcframework; path = xcfs/.build/artifacts/xcfs/libssh2/libssh2.xcframework; sourceTree = SOURCE_ROOT; };\n'
            '\t\tD2FBEC0727CF505D00FD974A /* browse.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = browse.swift; sourceTree = "<group>"; };\n'
            '\t\tD2FCB4DC2339F9DB00A88108 /* UIScrollView+Paging.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = "UIScrollView+Paging.swift"; sourceTree = "<group>"; };\n'
            '\t\tEA0BA18B1C0CC57B00719C1A /* Blink.app */ = {isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = Blink.app; sourceTree = BUILT_PRODUCTS_DIR; };\n'
            '/* End PBXFileReference section */\n'
            '\n'
            '/* Begin PBXFileSystemSynchronizedBuildFileExceptionSet section */\n'
        ),
        (
            '\t\tD2F64C9525CA99AD00F2225D /* libssh2.xcframework */ = {isa = PBXFileReference; lastKnownFileType = wrapper.xcframework; name = libssh2.xcframework; path = xcfs/.build/artifacts/xcfs/libssh2/libssh2.xcframework; sourceTree = SOURCE_ROOT; };\n'
            '\t\tD2FBEC0727CF505D00FD974A /* browse.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = browse.swift; sourceTree = "<group>"; };\n'
            '\t\tD2FCB4DC2339F9DB00A88108 /* UIScrollView+Paging.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = "UIScrollView+Paging.swift"; sourceTree = "<group>"; };\n'
            '\t\tEA0BA18B1C0CC57B00719C1A /* HermesLink.app */ = {isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = HermesLink.app; sourceTree = BUILT_PRODUCTS_DIR; };\n'
            '/* End PBXFileReference section */\n'
            '\n'
            '/* Begin PBXFileSystemSynchronizedBuildFileExceptionSet section */\n'
        ),
    ),
    (
        1484,
        (
            '\t\t\t\tD2C7710726EA49AA001B5659 /* openssl.xcframework in Frameworks */,\n'
            '\t\t\t\tD222780C2A26216900D4C708 /* TreeSitterBashRunestone in Frameworks */,\n'
            '\t\t\t\tD2334EF425C1C28F00385378 /* ios_system.xcframework in Frameworks */,\n'
            '\t\t\t\t07FABBC425C9AECF00E1CC2C /* BlinkFiles.framework in Frameworks */,\n'
            '\t\t\t\tBD7AFC4128E8E98C004BCDA4 /* Base32Kit in Frameworks */,\n'
            '\t\t\t\t0732F1291D06324200AB5438 /* libcurses.tbd in Frameworks */,\n'
        ),
        (
            '\t\t\t\tD2C7710726EA49AA001B5659 /* openssl.xcframework in Frameworks */,\n'
            '\t\t\t\tD222780C2A26216900D4C708 /* TreeSitterBashRunestone in Frameworks */,\n'
            '\t\t\t\tD2334EF425C1C28F00385378 /* ios_system.xcframework in Frameworks */,\n'
            '\t\t\t\tF10000070000000000000001 /* HermesRuntime.framework in Frameworks */,\n'
            '\t\t\t\t07FABBC425C9AECF00E1CC2C /* BlinkFiles.framework in Frameworks */,\n'
            '\t\t\t\tBD7AFC4128E8E98C004BCDA4 /* Base32Kit in Frameworks */,\n'
            '\t\t\t\t0732F1291D06324200AB5438 /* libcurses.tbd in Frameworks */,\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-xcodeproj-project-pbxproj-02.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
