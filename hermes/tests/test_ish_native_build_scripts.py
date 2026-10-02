# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Validates the iSH native build/install scripts: preflight robustness of
hermes/build/build-ish-static.sh (it must fail clearly when Xcode/Meson/Ninja
are unavailable, as in this Linux sandbox, rather than attempt a broken
partial build) and the install/copy behavior of install_ish_runtime.sh,
exercised end-to-end against the real pinned rootfs archive when present."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT / "hermes" / "build" / "build-ish-static.sh"
INSTALL_SCRIPT = ROOT / "install_ish_runtime.sh"
PINNED_ROOTFS = ROOT / "hermes" / "build" / "external" / "ish" / "rootfs.tar.gz"
PINNED_SOURCE = ROOT / "hermes" / "build" / "external" / "ish" / "source"


class BuildIshStaticScriptTests(unittest.TestCase):
    def test_script_has_valid_bash_syntax(self) -> None:
        result = subprocess.run(["bash", "-n", str(BUILD_SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_script_preflights_darwin_meson_and_ninja(self) -> None:
        source = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('uname -s', source)
        self.assertIn("command -v meson", source)
        self.assertIn("command -v ninja", source)
        self.assertIn("xcrun --sdk iphoneos --find clang", source)

    def test_script_drives_upstreams_own_meson_and_ninja_build_phase_scripts(self) -> None:
        source = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("app/xcode-meson.sh", source)
        self.assertIn("app/xcode-ninja.sh", source)
        self.assertIn("ISH_KERNEL=linux", source)

    def test_script_verifies_pinned_source_before_building(self) -> None:
        source = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("verify-ish-source.py", source)

    @unittest.skipUnless(PINNED_SOURCE.exists(), "pinned iSH source has not been fetched")
    def test_script_fails_clearly_and_safely_without_macos_xcode_meson(self) -> None:
        # This IS the genuinely-blocked validation path: on this Linux
        # sandbox there is no Xcode/Meson, so the script must stop at the
        # preflight check with a clear, actionable message and a non-zero
        # exit code, rather than attempt (and likely corrupt) a partial
        # native build.
        result = subprocess.run(["bash", str(BUILD_SCRIPT)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("build-ish-static.sh:", combined)
        self.assertTrue(
            any(keyword in combined for keyword in ("Darwin", "macOS", "meson", "Xcode")),
            combined,
        )


class InstallIshRuntimeScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(tempfile.mkdtemp(prefix="install-ish-runtime-", dir=str(Path.home())))

    def tearDown(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def test_script_has_valid_bash_syntax(self) -> None:
        result = subprocess.run(["bash", "-n", str(INSTALL_SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_input_directory_fails_clearly(self) -> None:
        blink_root = self.work_dir / "blink-root"
        blink_root.mkdir()
        result = subprocess.run(
            ["bash", str(INSTALL_SCRIPT), str(self.work_dir / "does-not-exist")],
            capture_output=True, text=True,
            env={"BLINK_ROOT": str(blink_root), "PATH": "/usr/bin:/bin"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing", result.stderr)

    def _fake_input_with(self, rootfs_path: Path, archive_names=("libFakeKernel.a", "libFakeUser.a")) -> Path:
        input_root = self.work_dir / "input"
        lib_dir = input_root / "lib"
        lib_dir.mkdir(parents=True)
        for index, name in enumerate(archive_names):
            (lib_dir / name).write_bytes(f"not a real archive, placeholder #{index}".encode())
        header_source = PINNED_SOURCE / "app" / "LinuxInterop.h"
        if header_source.exists():
            (lib_dir / "LinuxInterop.h").write_text(header_source.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            (lib_dir / "LinuxInterop.h").write_text("/* placeholder */\n", encoding="utf-8")
        (input_root / "rootfs.tar.gz").write_bytes(rootfs_path.read_bytes())
        return input_root

    @unittest.skipUnless(PINNED_ROOTFS.exists(), "pinned iSH rootfs has not been fetched")
    def test_valid_input_is_installed_under_the_fixed_canonical_library_names(self) -> None:
        input_root = self._fake_input_with(PINNED_ROOTFS)
        blink_root = self.work_dir / "blink-root"
        blink_root.mkdir()
        result = subprocess.run(
            ["bash", str(INSTALL_SCRIPT), str(input_root)],
            capture_output=True, text=True,
            env={"BLINK_ROOT": str(blink_root), "PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # hermes/build/ISHNative.xcconfig links -lISHLinuxKernel -lISHLinuxUser
        # unconditionally once enabled, so these exact names matter.
        self.assertTrue((blink_root / "Frameworks" / "ISHLinux" / "libISHLinuxKernel.a").is_file())
        self.assertTrue((blink_root / "Frameworks" / "ISHLinux" / "libISHLinuxUser.a").is_file())
        self.assertTrue((blink_root / "Frameworks" / "ISHLinux" / "LinuxInterop.h").is_file())
        installed_rootfs = blink_root / "Resources" / "ish-rootfs.tar.gz"
        self.assertTrue(installed_rootfs.is_file())
        self.assertEqual(installed_rootfs.read_bytes(), PINNED_ROOTFS.read_bytes())

    @unittest.skipUnless(PINNED_ROOTFS.exists(), "pinned iSH rootfs has not been fetched")
    def test_unexpected_archive_count_is_rejected_rather_than_guessed(self) -> None:
        input_root = self._fake_input_with(
            PINNED_ROOTFS, archive_names=("libOne.a", "libTwo.a", "libThree.a"),
        )
        blink_root = self.work_dir / "blink-root"
        blink_root.mkdir()
        result = subprocess.run(
            ["bash", str(INSTALL_SCRIPT), str(input_root)],
            capture_output=True, text=True,
            env={"BLINK_ROOT": str(blink_root), "PATH": "/usr/bin:/bin"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to guess", result.stderr)
        self.assertFalse((blink_root / "Frameworks" / "ISHLinux").exists())

    def test_corrupt_rootfs_archive_is_rejected_by_integrity_verification(self) -> None:
        corrupt_rootfs = self.work_dir / "corrupt.tar.gz"
        corrupt_rootfs.write_bytes(b"not a real gzip archive")
        input_root = self._fake_input_with(corrupt_rootfs)
        blink_root = self.work_dir / "blink-root"
        blink_root.mkdir()
        result = subprocess.run(
            ["bash", str(INSTALL_SCRIPT), str(input_root)],
            capture_output=True, text=True,
            env={"BLINK_ROOT": str(blink_root), "PATH": "/usr/bin:/bin"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((blink_root / "Resources" / "ish-rootfs.tar.gz").exists())


if __name__ == "__main__":
    unittest.main()
