# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Every wholly-new authored file this iSH integration adds must be listed
in AI-GENERATED-FILES.md (the project's attribution policy), and every
listed path must actually exist. This also guards against the inventory
silently drifting out of sync with the ISHBridge/ and related directories
as files are added or renamed."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "AI-GENERATED-FILES.md"

NEW_FILES_FROM_THIS_CHANGE = [
    "hermes/blink/overlay/Blink/Commands/hermes.m",
    "hermes/blink/overlay/Blink/Commands/ish.m",
    "hermes/blink/overlay/Blink/Commands/ishfs.m",
    "hermes/blink/overlay/Settings/ISHRootfsSettingsView.swift",
    "hermes/blink/apply-patches.py",
    "hermes/blink/patches/_patch_utils.py",
    "ISHBridge/ish_exit_protocol.c",
    "ISHBridge/ish_exit_protocol.h",
    "ISHBridge/ish_kernel_bridge.h",
    "ISHBridge/ish_kernel_bridge.m",
    "ISHBridge/ish_kernel_bridge_stub.m",
    "ISHBridge/ish_path_safety.c",
    "ISHBridge/ish_path_safety.h",
    "ISHBridge/ish_rootfs.c",
    "ISHBridge/ish_rootfs.h",
    "hermes/build/ISHNative.xcconfig",
    "hermes/build/build-ish-static.sh",
    "hermes/build/ish-documents-fs.c",
    "hermes/build/patch-ish-pty.py",
    "hermes/build/patch-ish-documents-fs.py",
    "hermes/build/package-ish-framework.sh",
    "hermes/build/prepare-blink-source.sh",
    "hermes/overlay/hermes/tools/ish_tool.py",
    "hermes/overlay/patches/patch-ish-tool.py",
    "hermes/tests/ish_bridge/ish_bridge_test_main.c",
    "hermes/tests/test_blink_source_patch.py",
    "hermes/tests/test_ish_bridge_c.py",
    "hermes/tests/test_ish_ci_workflow.py",
    "hermes/tests/test_ish_ai_generated_files_inventory.py",
    "hermes/tests/test_ish_native_build_scripts.py",
    "hermes/tests/test_ish_tool_registration.py",
    "hermes/tests/test_ish_xcode_project_wiring.py",
    "install_ish_runtime.sh",
]


class AiGeneratedFilesInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.listed_paths = set(re.findall(r"^- `([^`]+)`$", INVENTORY.read_text(encoding="utf-8"), re.MULTILINE))

    def test_every_new_file_from_this_change_is_listed(self) -> None:
        for path in NEW_FILES_FROM_THIS_CHANGE:
            with self.subTest(path=path):
                self.assertIn(path, self.listed_paths)

    def test_every_new_file_from_this_change_exists_on_disk(self) -> None:
        for path in NEW_FILES_FROM_THIS_CHANGE:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), f"listed/expected file missing: {path}")

    def test_every_listed_path_exists_on_disk(self) -> None:
        missing = [path for path in sorted(self.listed_paths) if not (ROOT / path).is_file()]
        self.assertEqual(missing, [])

    def test_all_blink_patch_scripts_are_in_the_inventory(self) -> None:
        patch_dir = ROOT / "hermes" / "blink" / "patches"
        patch_paths = {
            path.relative_to(ROOT).as_posix() for path in patch_dir.glob("patch-*.py")
        }
        self.assertTrue(patch_paths)
        self.assertEqual(patch_paths - self.listed_paths, set())

    def test_all_ishbridge_sources_are_listed(self) -> None:
        ish_bridge_dir = ROOT / "ISHBridge"
        on_disk = {
            path.relative_to(ROOT).as_posix() for path in ish_bridge_dir.glob("*")
            if path.is_file()
        }
        self.assertTrue(on_disk, "expected ISHBridge/ to contain at least one file")
        missing_from_inventory = on_disk - self.listed_paths
        self.assertEqual(missing_from_inventory, set())


if __name__ == "__main__":
    unittest.main()
