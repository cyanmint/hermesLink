#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from _patch_utils import apply_file


PATCH_NAME = 'patch-blink-xcodeproj-project-pbxproj-01'
TARGET = 'Blink.xcodeproj/project.pbxproj'
REPLACEMENTS = (
    (
        466,
        (
            '\t\tD2ECBF4929645814004E95C4 /* BuildApi.swift in Sources */ = {isa = PBXBuildFile; fileRef = D2ECBF4829645814004E95C4 /* BuildApi.swift */; };\n'
            '\t\tD2ED4A6F239BB12E000DC67F /* KeyCaptureView.swift in Sources */ = {isa = PBXBuildFile; fileRef = D2ED4A6E239BB12E000DC67F /* KeyCaptureView.swift */; };\n'
            '\t\tD2F30EAD205009CD008C5F35 /* base64js.min.js in Resources */ = {isa = PBXBuildFile; fileRef = D2F30EAC205009CD008C5F35 /* base64js.min.js */; };\n'
            '\t\tD2F330CA20A6CB840074ADD7 /* help.m in Sources */ = {isa = PBXBuildFile; fileRef = D2F330C920A6CB840074ADD7 /* help.m */; };\n'
            '\t\tD2F330CC20A6D98C0074ADD7 /* config.m in Sources */ = {isa = PBXBuildFile; fileRef = D2F330CB20A6D98C0074ADD7 /* config.m */; };\n'
            '\t\tD2F330D220A6EF030074ADD7 /* showkey.m in Sources */ = {isa = PBXBuildFile; fileRef = D2F330D120A6EF020074ADD7 /* showkey.m */; };\n'
        ),
        (
            '\t\tD2ECBF4929645814004E95C4 /* BuildApi.swift in Sources */ = {isa = PBXBuildFile; fileRef = D2ECBF4829645814004E95C4 /* BuildApi.swift */; };\n'
            '\t\tD2ED4A6F239BB12E000DC67F /* KeyCaptureView.swift in Sources */ = {isa = PBXBuildFile; fileRef = D2ED4A6E239BB12E000DC67F /* KeyCaptureView.swift */; };\n'
            '\t\tD2F30EAD205009CD008C5F35 /* base64js.min.js in Resources */ = {isa = PBXBuildFile; fileRef = D2F30EAC205009CD008C5F35 /* base64js.min.js */; };\n'
            '\t\tF10000010000000000000001 /* hermes.m in Sources */ = {isa = PBXBuildFile; fileRef = F10000020000000000000001 /* hermes.m */; };\n'
            '\t\tF2A5A0010000000000000001 /* wasm.m in Sources */ = {isa = PBXBuildFile; fileRef = F2A5A0030000000000000001 /* wasm.m */; };\n'
            '\t\tF2A5A0020000000000000001 /* WasmRuntime in Resources */ = {isa = PBXBuildFile; fileRef = F2A5A0040000000000000001 /* WasmRuntime */; };\n'
            '\t\tF10000070000000000000001 /* HermesRuntime.framework in Frameworks */ = {isa = PBXBuildFile; fileRef = F10000090000000000000001 /* HermesRuntime.framework */; };\n'
            '\t\tF10000080000000000000001 /* HermesRuntime.framework in Embed Frameworks */ = {isa = PBXBuildFile; fileRef = F10000090000000000000001 /* HermesRuntime.framework */; settings = {ATTRIBUTES = (CodeSignOnCopy, RemoveHeadersOnCopy, ); }; };\n'
            '\t\tF10000050000000000000001 /* hermesrt.zip in Resources */ = {isa = PBXBuildFile; fileRef = F10000060000000000000001 /* hermesrt.zip */; };\n'
            '\t\tF1A1CE560000000000000001 /* ish.m in Sources */ = {isa = PBXBuildFile; fileRef = F1A1CE550000000000000001 /* ish.m */; };\n'
            '\t\tF1A1CE570000000000000001 /* ishfs.m in Sources */ = {isa = PBXBuildFile; fileRef = F1A1CE5A0000000000000001 /* ishfs.m */; };\n'
            '\t\tF1A1CE580000000000000001 /* ISHRootfsProfiles.m in Sources */ = {isa = PBXBuildFile; fileRef = F1A1CE5B0000000000000001 /* ISHRootfsProfiles.m */; };\n'
            '\t\tF1A1CE590000000000000001 /* ISHRootfsSettingsView.swift in Sources */ = {isa = PBXBuildFile; fileRef = F1A1CE5D0000000000000001 /* ISHRootfsSettingsView.swift */; };\n'
            '\t\t3EC2EABECFB079180991531B /* ish_kernel_bridge_stub.m in Sources */ = {isa = PBXBuildFile; fileRef = 1E3F68EDDDED7F8AAF6CD86C /* ish_kernel_bridge_stub.m */; };\n'
            '\t\tDCA2F5F653C2C3F9662E8822 /* ish-rootfs.tar.gz in Resources */ = {isa = PBXBuildFile; fileRef = 314E2F04FE0F5B60CB0D4E61 /* ish-rootfs.tar.gz */; };\n'
            '\t\tD2F330CA20A6CB840074ADD7 /* help.m in Sources */ = {isa = PBXBuildFile; fileRef = D2F330C920A6CB840074ADD7 /* help.m */; };\n'
            '\t\tD2F330CC20A6D98C0074ADD7 /* config.m in Sources */ = {isa = PBXBuildFile; fileRef = D2F330CB20A6D98C0074ADD7 /* config.m */; };\n'
            '\t\tD2F330D220A6EF030074ADD7 /* showkey.m in Sources */ = {isa = PBXBuildFile; fileRef = D2F330D120A6EF020074ADD7 /* showkey.m */; };\n'
        ),
    ),
    (
        727,
        (
            '\t\t\tdstPath = "";\n'
            '\t\t\tdstSubfolderSpec = 10;\n'
            '\t\t\tfiles = (\n'
            '\t\t\t\tD2A9B2F8272E6F26009FCBDE /* BlinkCode.framework in Embed Frameworks */,\n'
            '\t\t\t\tD2C7710826EA49AA001B5659 /* openssl.xcframework in Embed Frameworks */,\n'
            '\t\t\t\tBDF2B8D32BC480CC00B9C7EA /* vim.xcframework in Embed Frameworks */,\n'
        ),
        (
            '\t\t\tdstPath = "";\n'
            '\t\t\tdstSubfolderSpec = 10;\n'
            '\t\t\tfiles = (\n'
            '\t\t\t\tF10000080000000000000001 /* HermesRuntime.framework in Embed Frameworks */,\n'
            '\t\t\t\tD2A9B2F8272E6F26009FCBDE /* BlinkCode.framework in Embed Frameworks */,\n'
            '\t\t\t\tD2C7710826EA49AA001B5659 /* openssl.xcframework in Embed Frameworks */,\n'
            '\t\t\t\tBDF2B8D32BC480CC00B9C7EA /* vim.xcframework in Embed Frameworks */,\n'
        ),
    ),
    (
        767,
        (
            '\t\t};\n'
            '/* End PBXCopyFilesBuildPhase section */\n'
            '\n'
            '/* Begin PBXFileReference section */\n'
            '\t\t0716B5291CFFAB9300268B5B /* AppDelegate.h */ = {isa = PBXFileReference; fileEncoding = 4; lastKnownFileType = sourcecode.c.h; path = AppDelegate.h; sourceTree = "<group>"; };\n'
            '\t\t0716B52A1CFFAB9300268B5B /* AppDelegate.m */ = {isa = PBXFileReference; fileEncoding = 4; lastKnownFileType = sourcecode.c.objc; path = AppDelegate.m; sourceTree = "<group>"; };\n'
        ),
        (
            '\t\t};\n'
            '/* End PBXCopyFilesBuildPhase section */\n'
            '\n'
            '/* Begin PBXShellScriptBuildPhase section */\n'
            '\t\tF100000A0000000000000001 /* Embed Ish.framework when enabled */ = {\n'
            '\t\t\tisa = PBXShellScriptBuildPhase;\n'
            '\t\t\talwaysOutOfDate = 1;\n'
            '\t\t\tbuildActionMask = 2147483647;\n'
            '\t\t\tfiles = (\n'
            '\t\t\t);\n'
            '\t\t\tinputPaths = (\n'
            '\t\t\t\t"$(PROJECT_DIR)/Frameworks/Ish.framework",\n'
            '\t\t\t);\n'
            '\t\t\tname = "Embed Ish.framework when enabled";\n'
            '\t\t\toutputPaths = (\n'
            '\t\t\t\t"$(TARGET_BUILD_DIR)/$(FRAMEWORKS_FOLDER_PATH)/Ish.framework/Ish",\n'
            '\t\t\t);\n'
            '\t\t\trunOnlyForDeploymentPostprocessing = 0;\n'
            '\t\t\tshellPath = /bin/sh;\n'
            '\t\t\tshellScript = "set -e\\nif [ \\"${ISH_NATIVE_AVAILABLE:-NO}\\" != YES ]; then\\n  exit 0\\nfi\\nsource=\\"$PROJECT_DIR/Frameworks/Ish.framework\\"\\ndestination=\\"$TARGET_BUILD_DIR/$FRAMEWORKS_FOLDER_PATH/Ish.framework\\"\\nif [ ! -x \\"$source/Ish\\" ]; then\\n  echo \\"missing Ish.framework/Ish at $source\\" >&2\\n  exit 1\\nfi\\nmkdir -p \\"$(dirname \\"$destination\\")\\"\\nrm -rf \\"$destination\\"\\n/usr/bin/ditto \\"$source\\" \\"$destination\\"\\nif [ \\"${CODE_SIGNING_ALLOWED:-NO}\\" = YES ]; then\\n  /usr/bin/codesign --force --sign \\"${EXPANDED_CODE_SIGN_IDENTITY:--}\\" --timestamp=none \\"$destination\\"\\nfi\\n";\n'
            '\t\t};\n'
            '/* End PBXShellScriptBuildPhase section */\n'
            '\n'
            '/* Begin PBXFileReference section */\n'
            '\t\t0716B5291CFFAB9300268B5B /* AppDelegate.h */ = {isa = PBXFileReference; fileEncoding = 4; lastKnownFileType = sourcecode.c.h; path = AppDelegate.h; sourceTree = "<group>"; };\n'
            '\t\t0716B52A1CFFAB9300268B5B /* AppDelegate.m */ = {isa = PBXFileReference; fileEncoding = 4; lastKnownFileType = sourcecode.c.objc; path = AppDelegate.m; sourceTree = "<group>"; };\n'
        ),
    ),
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-blink-xcodeproj-project-pbxproj-01.py <blink-source-root>")
    apply_file(Path(sys.argv[1]).resolve(), TARGET, REPLACEMENTS, PATCH_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
