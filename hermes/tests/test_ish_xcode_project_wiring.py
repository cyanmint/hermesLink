# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Validates the Xcode project wiring for the iSH integration:
- ISHBridge sources are registered in the project, with only the command and
  disabled-build stub compiled directly into the Blink app;
- Ish.framework is conditionally linked and embedded by the app target;
- hermes/build/ISHNative.xcconfig defaults to the safe stub mode;
- Resources/blinkCommandsDictionary.plist registers the native `ish`
  command as `ish_main` (not an `ish container` subcommand).

This does not invoke xcodebuild (unavailable in this sandbox; see
BUILD.md); it validates the project file's own structure/content."""

from __future__ import annotations

import plistlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PBXPROJ = ROOT / "Blink.xcodeproj" / "project.pbxproj"
COMMANDS_PLIST = ROOT / "Resources" / "blinkCommandsDictionary.plist"
XCCONFIG = ROOT / "hermes" / "build" / "ISHNative.xcconfig"
TEMPLATE_XCCONFIG = ROOT / "template_setup.xcconfig"
ISH_DIR = ROOT / "ISHBridge"


class CommandRegistrationTests(unittest.TestCase):
    def test_ish_is_registered_as_a_top_level_native_command_not_a_subcommand(self) -> None:
        with COMMANDS_PLIST.open("rb") as handle:
            commands = plistlib.load(handle)
        self.assertIn("ish", commands)
        self.assertNotIn("ish container", commands)
        entry = commands["ish"]
        self.assertEqual(entry, ["MAIN", "ish_main", "", "no"])

    def test_native_command_source_defines_ish_main(self) -> None:
        source = (ROOT / "Blink" / "Commands" / "ish.m").read_text(encoding="utf-8")
        self.assertIn("int ish_main(int argc, char *argv[])", source)
        self.assertIn('#include "ish_kernel_bridge.h"', source)


class PbxprojWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = PBXPROJ.read_text(encoding="utf-8")

    def test_braces_and_parens_remain_balanced(self) -> None:
        # A cheap, dependency-free structural sanity check on the
        # hand-edited project file (OpenStep plist "ASCII plist" format).
        self.assertEqual(self.source.count("{"), self.source.count("}"))
        self.assertEqual(self.source.count("("), self.source.count(")"))

    def test_every_new_source_file_has_a_file_reference(self) -> None:
        expected_paths = [
            "ish_path_safety.h", "ish_path_safety.c",
            "ish_rootfs.h", "ish_rootfs.c",
            "ish_exit_protocol.h", "ish_exit_protocol.c",
            "ish_kernel_bridge.h", "ish_kernel_bridge.m",
            "ish_kernel_bridge_stub.m",
        ]
        for name in expected_paths:
            with self.subTest(name=name):
                self.assertIn(f"path = {name};", self.source)

    def test_ish_m_and_rootfs_resource_have_file_references(self) -> None:
        self.assertIn("path = ish.m;", self.source)
        self.assertIn('path = "ish-rootfs.tar.gz";', self.source)

    def test_only_command_and_stub_are_compiled_into_the_app_target(self) -> None:
        self.assertIn("ish.m in Sources */,", self.source)
        self.assertIn("ish_kernel_bridge_stub.m in Sources */,", self.source)
        for name in ("ish_path_safety.c", "ish_rootfs.c", "ish_exit_protocol.c", "ish_kernel_bridge.m"):
            with self.subTest(name=name):
                self.assertNotIn(f"{name} in Sources */,", self.source)

    def test_headers_are_not_attached_to_any_build_phase(self) -> None:
        # Headers should be plain, visible file references only: none of
        # these names should show up as "<name> in Headers" (other targets
        # in this project, e.g. frameworks, legitimately have their own
        # PBXHeadersBuildPhase, so this does not assert that phase type is
        # absent from the whole file — only that our headers aren't in one).
        for name in (
            "ish_path_safety.h", "ish_rootfs.h",
            "ish_exit_protocol.h", "ish_kernel_bridge.h",
        ):
            with self.subTest(name=name):
                self.assertNotIn(f"{name} in Headers", self.source)

    def test_rootfs_archive_is_in_the_resources_build_phase(self) -> None:
        self.assertIn("ish-rootfs.tar.gz in Resources */,", self.source)

    def test_ishbridge_group_exists_and_lists_all_its_files(self) -> None:
        group_start = self.source.index('/* ISHBridge */ = {\n\t\t\tisa = PBXGroup;')
        group_end = self.source.index("};", group_start)
        group_body = self.source[group_start:group_end]
        for name in (
            "ish_path_safety.h", "ish_path_safety.c",
            "ish_rootfs.h", "ish_rootfs.c",
            "ish_exit_protocol.h", "ish_exit_protocol.c",
            "ish_kernel_bridge.h", "ish_kernel_bridge.m", "ish_kernel_bridge_stub.m",
        ):
            with self.subTest(name=name):
                self.assertIn(name, group_body)
        self.assertIn("path = ISHBridge;", group_body)

    def test_no_preexisting_entries_were_removed(self) -> None:
        # The diff that produced this file should be purely additive;
        # spot-check a handful of representative, untouched entries.
        for marker in (
            'F10000020000000000000001 /* hermes.m */ = {isa = PBXFileReference;',
            'F10000060000000000000001 /* hermesrt.zip */ = {isa = PBXFileReference;',
            'EA0BA18C1C0CC57B00719C1A /* Products */ = {',
            '0716B5231CFFAB9300268B5B /* Blink */,',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.source)


class IshNativeXcconfigTests(unittest.TestCase):
    def test_xcconfig_file_exists_and_defaults_to_disabled(self) -> None:
        source = XCCONFIG.read_text(encoding="utf-8")
        self.assertIn("ISH_NATIVE_AVAILABLE = NO", source)

    def test_xcconfig_selects_the_framework_or_default_app_stub(self) -> None:
        source = XCCONFIG.read_text(encoding="utf-8")
        self.assertIn("ISH_EXCLUDED_SOURCES_NO =", source)
        self.assertIn("ISH_EXCLUDED_SOURCES_YES = ish_kernel_bridge_stub.m", source)
        self.assertIn("EXCLUDED_SOURCE_FILE_NAMES", source)

    def test_xcconfig_links_the_ish_framework_only_when_enabled(self) -> None:
        source = XCCONFIG.read_text(encoding="utf-8")
        self.assertIn("ISH_LDFLAGS_YES = -framework Ish", source)
        self.assertIn(
            "BLINK_OTHER_LDFLAGS = $(inherited) $(ISH_LDFLAGS_$(ISH_NATIVE_AVAILABLE))",
            source,
        )
        self.assertFalse(any(line.startswith("OTHER_LDFLAGS =") for line in source.splitlines()))

    def test_real_bridge_provides_framework_configuration_api(self) -> None:
        source = (ISH_DIR / "ish_kernel_bridge.m").read_text(encoding="utf-8")
        self.assertIn("void FsInitialize(void)", source)
        self.assertIn("int ish_configure(const char *root_path, ish_log_handler log_handler)", source)
        self.assertNotIn("#import <BlinkConfig/BlinkPaths.h>", source)
        self.assertNotIn("extern void HermesLinkAppendLog", source)

    def test_real_bridge_passes_capturable_argument_pointers_to_session_block(self) -> None:
        source = (ISH_DIR / "ish_kernel_bridge.m").read_text(encoding="utf-8")
        self.assertIn("const char *argv_values[]", source)
        self.assertIn("const char *envp_values[]", source)
        self.assertIn("const char **argv = argv_values", source)
        self.assertIn("const char **envp = envp_values", source)

    def test_guest_rootfs_uses_files_visible_documents_iSH_directory(self) -> None:
        command = (ROOT / "Blink" / "Commands" / "ish.m").read_text(encoding="utf-8")
        bridge = (ISH_DIR / "ish_kernel_bridge.m").read_text(encoding="utf-8")
        header = (ISH_DIR / "ish_kernel_bridge.h").read_text(encoding="utf-8")

        self.assertIn(
            '[[BlinkPaths documentsPath] stringByAppendingPathComponent:@"iSH"]',
            command,
        )
        self.assertIn("NSDocumentDirectory", bridge)
        self.assertIn('stringByAppendingPathComponent:@"iSH"', bridge)
        self.assertIn("Files-visible Documents/iSH", header)
        self.assertIn('@"sbin/init"', bridge)

    def test_template_setup_includes_the_ish_native_xcconfig(self) -> None:
        source = TEMPLATE_XCCONFIG.read_text(encoding="utf-8")
        self.assertIn('#include "hermes/build/ISHNative.xcconfig"', source)

    def test_both_kernel_bridge_implementation_files_exist_on_disk(self) -> None:
        self.assertTrue((ISH_DIR / "ish_kernel_bridge.m").is_file())
        self.assertTrue((ISH_DIR / "ish_kernel_bridge_stub.m").is_file())

    def test_stub_implements_the_same_public_entry_points_as_the_real_bridge(self) -> None:
        header = (ISH_DIR / "ish_kernel_bridge.h").read_text(encoding="utf-8")
        stub = (ISH_DIR / "ish_kernel_bridge_stub.m").read_text(encoding="utf-8")
        for symbol in ("ish_configure", "ish_kernel_ensure_booted", "ish_run_command"):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, header)
                self.assertIn(symbol, stub)
        self.assertIn("ISH_RUN_ERR_NOT_AVAILABLE", stub)

    def test_app_conditionally_embeds_the_dynamic_ish_framework(self) -> None:
        project = PBXPROJ.read_text(encoding="utf-8")
        self.assertIn("Embed Ish.framework when enabled", project)
        self.assertIn('ISH_NATIVE_AVAILABLE:-NO', project)
        self.assertIn('@rpath/Ish.framework/Ish', (ROOT / "hermes" / "build" / "package-ish-framework.sh").read_text())


if __name__ == "__main__":
    unittest.main()
