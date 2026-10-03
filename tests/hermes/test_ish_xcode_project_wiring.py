# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Validates the Xcode project wiring for the iSH integration:
- ISHBridge sources are registered in the project, with only the command and
  disabled-build stub compiled directly into the Blink app;
- Ish.framework is conditionally linked and embedded by the app target;
- ishbridge/ISHNative.xcconfig defaults to the safe stub mode;
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
XCCONFIG = ROOT / "ishbridge" / "ISHNative.xcconfig"
TEMPLATE_XCCONFIG = ROOT / "template_setup.xcconfig"
ISH_DIR = ROOT / "ishbridge"


@unittest.skipUnless(
    (ROOT / "Resources" / "blinkCommandsDictionary.plist").is_file(),
    "Blink source is materialized from the pinned upstream checkout during builds",
)
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

    def test_ish_populates_and_refreshes_resolver_from_the_app_process(self) -> None:
        bridge = (ISH_DIR / "ish_kernel_bridge.m").read_text(encoding="utf-8")
        self.assertIn("res_ninit(&resolver)", bridge)
        self.assertIn("res_getservers(&resolver", bridge)
        self.assertIn("ish_rootfs_update_resolv_conf(g_rootfs_path, resolv_conf, length)", bridge)
        self.assertNotIn("linux_write_file", bridge)
        self.assertIn("SCNetworkReachabilitySetCallback", bridge)
        self.assertIn("ish_network_reachability_changed", bridge)
        self.assertIn("ish_configure_guest_dns();", bridge)

    def test_guest_kernel_disables_smp_for_the_vfork_panic_workaround(self) -> None:
        bridge = (ISH_DIR / "ish_kernel_bridge.m").read_text(encoding="utf-8")
        self.assertIn('actuate_kernel("nosmp")', bridge)

    def test_ishfs_is_registered_with_profile_lifecycle_operations(self) -> None:
        with COMMANDS_PLIST.open("rb") as handle:
            commands = plistlib.load(handle)
        self.assertEqual(commands["ishfs"], ["MAIN", "ishfs_main", "", "no"])
        source = (ROOT / "Blink" / "Commands" / "ishfs.m").read_text(encoding="utf-8")
        for operation in ("list", "create", "import", "rename", "delete", "use"):
            with self.subTest(operation=operation):
                self.assertIn(f'"{operation}"', source)

    def test_bridge_uses_host_rootfs_writes_instead_of_guest_kernel_file_apis(self) -> None:
        bridge = (ISH_DIR / "ish_kernel_bridge.m").read_text(encoding="utf-8")
        self.assertIn("ish_rootfs_update_resolv_conf", bridge)
        self.assertNotIn("linux_write_file", bridge)
        self.assertNotIn("current =", bridge)
        self.assertNotIn("generic_open(", bridge)
        self.assertNotIn("generic_mkdirat(", bridge)
        self.assertNotIn("do_mount(", bridge)


@unittest.skipUnless(
    PBXPROJ.is_file(),
    "Blink source is materialized from the pinned upstream checkout during builds",
)
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
            "ISHRootfsProfiles.h", "ISHRootfsProfiles.m",
        ]
        for name in expected_paths:
            with self.subTest(name=name):
                self.assertIn(f"path = {name};", self.source)

    def test_ish_m_and_rootfs_resource_have_file_references(self) -> None:
        self.assertIn("path = ish.m;", self.source)
        self.assertIn('path = "ish-rootfs.tar.gz";', self.source)

    def test_app_sources_include_profile_tools_but_keep_kernel_glue_in_the_framework(self) -> None:
        self.assertIn("ish.m in Sources */,", self.source)
        self.assertIn("ishfs.m in Sources */,", self.source)
        self.assertIn("ish_kernel_bridge_stub.m in Sources */,", self.source)
        self.assertIn("ISHRootfsProfiles.m in Sources */,", self.source)
        self.assertIn("ISHRootfsSettingsView.swift in Sources */,", self.source)
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
            "ISHRootfsProfiles.h", "ISHRootfsProfiles.m",
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
        self.assertIn("int ish_configure_documents(const char *host_path)", source)
        self.assertIn("if (g_boot_started) {", source)
        self.assertIn("return ISH_RUN_OK;", source)
        self.assertNotIn("#import <BlinkConfig/BlinkPaths.h>", source)
        self.assertNotIn("extern void HermesLinkAppendLog", source)

    @unittest.skipUnless(
        (ROOT / "Settings" / "ISHRootfsSettingsView.swift").is_file(),
        "Blink source is materialized from the pinned upstream checkout during builds",
    )
    def test_documents_mount_is_manual_and_script_is_written_for_profiles(self) -> None:
        view = (ROOT / "Settings" / "ISHRootfsSettingsView.swift").read_text(encoding="utf-8")
        self.assertIn("Run /ish/mount-documents.sh inside iSH", view)
        self.assertNotIn("Automatically mount Documents", view)
        rootfs = (ISH_DIR / "ish_rootfs.c").read_text(encoding="utf-8")
        self.assertIn("ish_rootfs_write_documents_mount_script", rootfs)
        profiles = (ISH_DIR / "ISHRootfsProfiles.m").read_text(encoding="utf-8")
        self.assertIn("ish_rootfs_write_documents_mount_script(", profiles)
        bridge = (ISH_DIR / "ish_kernel_bridge.m").read_text(encoding="utf-8")
        self.assertIn("ish_rootfs_write_documents_mount_script(", bridge)
        command = (ROOT / "Blink" / "Commands" / "ish.m").read_text(encoding="utf-8")
        self.assertIn("ISHDocumentsHostPath().UTF8String", command)
        self.assertNotIn("ish_mount_documents", (ROOT / "scripts" / "hermes" / "build" / "patch-ish-pty.py").read_text(encoding="utf-8"))
        command = (ROOT / "Blink" / "Commands" / "ishfs.m").read_text(encoding="utf-8")
        self.assertNotIn('"documents"', command)

    def test_real_bridge_passes_capturable_argument_pointers_to_session_block(self) -> None:
        source = (ISH_DIR / "ish_kernel_bridge.m").read_text(encoding="utf-8")
        self.assertIn("const char *argv_values[]", source)
        self.assertIn("const char *envp_values[]", source)
        self.assertIn("const char **argv = argv_values", source)
        self.assertIn("const char **envp = envp_values", source)

    @unittest.skipUnless(
        (ROOT / "Blink" / "Commands" / "ish.m").is_file(),
        "Blink source is materialized from the pinned upstream checkout during builds",
    )
    def test_guest_rootfs_uses_files_visible_documents_iSH_directory(self) -> None:
        command = (ROOT / "Blink" / "Commands" / "ish.m").read_text(encoding="utf-8")
        bridge = (ISH_DIR / "ish_kernel_bridge.m").read_text(encoding="utf-8")
        header = (ISH_DIR / "ish_kernel_bridge.h").read_text(encoding="utf-8")
        profiles = (ISH_DIR / "ISHRootfsProfiles.m").read_text(encoding="utf-8")

        self.assertIn("ISHRootfsActiveProfilePath", command)
        self.assertIn('stringByAppendingPathComponent:@"iSH"', profiles)
        self.assertIn("return [ISHDocumentsRoot() stringByAppendingPathComponent:name];", profiles)
        self.assertIn('stringByAppendingPathComponent:@"Profiles"', profiles)
        self.assertIn('stringByAppendingPathComponent:@"iSH-Profiles"', profiles)
        self.assertIn('ISHDefaultProfileName = @"Alpine"', profiles)
        self.assertIn("ISHPathEntryExists(defaultPath)", profiles)
        self.assertIn("ISHMoveProfiles(alternateProfilesRoot, documentsRoot, NO, error)", profiles)
        self.assertIn("ISHLegacyProfilesRootContainsProfiles(legacyProfilesRoot)", profiles)
        self.assertIn("NSDocumentDirectory", bridge)
        self.assertIn('stringByAppendingPathComponent:@"iSH"', bridge)
        self.assertIn("Files-visible Documents/iSH", header)
        self.assertIn('@"data"', bridge)
        self.assertIn('@"bin/busybox"', bridge)
        self.assertIn('@"etc/alpine-release"', bridge)
        self.assertIn('@"sbin/init"', bridge)
        self.assertIn("ish_rootfs_prepare_fakefs", bridge)
        self.assertIn("incomplete or incompatible; remove it", bridge)
        self.assertIn("g_boot_started = 0", bridge)
        self.assertIn("guest session startup failed (upstream status %d", bridge)
        self.assertIn('stringByAppendingPathComponent:@"Alpine"', bridge)
        self.assertIn("int *session_error_out", bridge)
        self.assertIn("upstream error %d; see diagnostics log", command)
        self.assertIn("#define ISH_SESSION_START_ENODEV_RETRIES 2", bridge)
        self.assertIn("start_retval != -ENODEV || start_terminal != NULL", bridge)
        self.assertIn("usleep(ISH_SESSION_START_RETRY_DELAY_MICROSECONDS * (attempt + 1))", bridge)

    def test_kernel_readiness_waits_for_session_initcalls_instead_of_probing_workqueue(self) -> None:
        source = (ISH_DIR / "ish_kernel_bridge.m").read_text(encoding="utf-8")
        fs_initialize = source.split("void FsInitialize(void)", 1)[1].split("\n}", 1)[0]
        readiness = source.split("static int ish_wait_for_kernel_ready(void)", 1)[1].split("\n}", 1)[0]
        self.assertIn("g_kernel_ready = 1", fs_initialize)
        self.assertIn("pthread_cond_broadcast(&g_kernel_ready_cond)", fs_initialize)
        self.assertLess(
            fs_initialize.index("g_kernel_ready = 1"),
            fs_initialize.index("async_do_in_ios"),
        )
        self.assertNotIn("ish_configure_guest_dns();", fs_initialize)
        self.assertIn("pthread_cond_timedwait", readiness)
        self.assertNotIn("ish_sync_do_in_workqueue", readiness)
        self.assertIn("g_kernel_panicked", readiness)
        pty_patcher = (ROOT / "scripts" / "hermes" / "build" / "patch-ish-pty.py").read_text(encoding="utf-8")
        self.assertIn("rootfs_initcall(ish_rootfs);", pty_patcher)
        self.assertIn("late_initcall(ish_session_ready);", pty_patcher)
        network_callback = source.split(
            "static void ish_network_reachability_changed", 1
        )[1].split("\n}", 1)[0]
        self.assertNotIn("async_do_in_workqueue", network_callback)
        self.assertIn("ish_configure_guest_dns();", network_callback)
        dns_writer = source.split("static void ish_configure_guest_dns(void)", 1)[1].split("\n}", 1)[0]
        self.assertIn("ish_rootfs_update_resolv_conf(g_rootfs_path, resolv_conf, length)", dns_writer)
        self.assertNotIn("memset(resolv_conf + length", dns_writer)
        self.assertIn("ish_rootfs_prepare_resolv_conf(root.fileSystemRepresentation)", source)

    def test_profile_management_preserves_legacy_rootfs_and_blocks_unsafe_names(self) -> None:
        source = (ISH_DIR / "ISHRootfsProfiles.m").read_text(encoding="utf-8")
        self.assertIn('@"bin/busybox"', source)
        self.assertIn('@"etc/alpine-release"', source)
        self.assertIn('stringByAppendingPathComponent:@"iSH"', source)
        self.assertIn('stringByAppendingPathComponent:@"iSH-Profiles"', source)
        self.assertIn("ISHDirectoryContainsOnlyEntry(documentsRoot, @\"Profiles\")", source)
        self.assertIn("movedNames.reverseObjectEnumerator", source)
        self.assertIn("unrecognized files", source)
        self.assertIn('[newName isEqualToString:ISHDefaultProfileName]', source)
        self.assertIn("ISHValidProfileName", source)
        self.assertIn("lstat(path.fileSystemRepresentation", source)
        self.assertIn("S_ISDIR(attributes.st_mode)", source)
        self.assertIn("moveItemAtPath:source toPath:destination", source)
        self.assertIn("ish_kernel_has_booted()", source)
        self.assertIn("ish_import_rootfs_archive", source)
        self.assertIn("ish_rootfs_prepare_fakefs", source)
        self.assertIn("ish_rootfs_prepare_resolv_conf", source)
        self.assertIn("names.count < 2", source)
        self.assertIn("Could not reset the only rootfs profile", source)

    @unittest.skipUnless(
        (ROOT / "Settings" / "ISHRootfsSettingsView.swift").is_file(),
        "Blink source is materialized from the pinned upstream checkout during builds",
    )
    def test_settings_exposes_rootfs_profiles(self) -> None:
        settings = (ROOT / "Settings" / "SettingsView.swift").read_text(encoding="utf-8")
        profile_view = (ROOT / "Settings" / "ISHRootfsSettingsView.swift").read_text(encoding="utf-8")
        self.assertIn('Section("iSH")', settings)
        self.assertIn("ISHRootfsSettingsView()", settings)
        for operation in ("ISHRootfsCreateProfile", "ISHRootfsImportProfile",
                          "ISHRootfsRenameProfile", "ISHRootfsDeleteProfile", "ISHRootfsSelectProfile"):
            with self.subTest(operation=operation):
                self.assertIn(operation, profile_view)
        self.assertIn("Force-quit and reopen Blink", profile_view)

    @unittest.skipUnless(
        (ROOT / "template_setup.xcconfig").is_file(),
        "Blink source is materialized from the pinned upstream checkout during builds",
    )
    def test_template_setup_includes_the_ish_native_xcconfig(self) -> None:
        source = TEMPLATE_XCCONFIG.read_text(encoding="utf-8")
        self.assertIn('#include "ISHBridge/ISHNative.xcconfig"', source)

    def test_both_kernel_bridge_implementation_files_exist_on_disk(self) -> None:
        self.assertTrue((ISH_DIR / "ish_kernel_bridge.m").is_file())
        self.assertTrue((ISH_DIR / "ish_kernel_bridge_stub.m").is_file())

    def test_stub_implements_the_same_public_entry_points_as_the_real_bridge(self) -> None:
        header = (ISH_DIR / "ish_kernel_bridge.h").read_text(encoding="utf-8")
        stub = (ISH_DIR / "ish_kernel_bridge_stub.m").read_text(encoding="utf-8")
        for symbol in ("ish_configure", "ish_import_rootfs_archive", "ish_kernel_ensure_booted",
                       "ish_kernel_has_booted", "ish_run_command"):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, header)
                self.assertIn(symbol, stub)
        self.assertIn("ISH_RUN_ERR_NOT_AVAILABLE", stub)

    @unittest.skipUnless(
        PBXPROJ.is_file(),
        "Blink source is materialized from the pinned upstream checkout during builds",
    )
    def test_app_conditionally_embeds_the_dynamic_ish_framework(self) -> None:
        project = PBXPROJ.read_text(encoding="utf-8")
        self.assertIn("Embed Ish.framework when enabled", project)
        self.assertIn('ISH_NATIVE_AVAILABLE:-NO', project)
        package_script = (ROOT / "scripts" / "hermes" / "build" / "package-ish-framework.sh").read_text()
        self.assertIn('@rpath/Ish.framework/Ish', package_script)
        for symbol in ("_ish_import_rootfs_archive", "_ish_kernel_has_booted"):
            with self.subTest(symbol=symbol):
                self.assertIn(f"-Wl,-exported_symbol,{symbol}", package_script)


if __name__ == "__main__":
    unittest.main()
