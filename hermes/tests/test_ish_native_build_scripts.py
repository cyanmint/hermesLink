# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Validates the iSH native build/install scripts: preflight robustness of
hermes/build/build-ish-static.sh (it must fail clearly when Xcode/Meson/Ninja
are unavailable, as in this Linux sandbox, rather than attempt a broken
partial build) and the install/copy behavior of install_ish_runtime.sh,
exercised end-to-end against the real pinned rootfs archive when present."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT / "hermes" / "build" / "build-ish-static.sh"
PACKAGE_FRAMEWORK_SCRIPT = ROOT / "hermes" / "build" / "package-ish-framework.sh"
PREPARE_XCODE_PROJECT = ROOT / "hermes" / "build" / "prepare-ish-xcode-project.py"
REPACK_MESON_ARCHIVES = ROOT / "hermes" / "build" / "repack-ish-meson-archives.py"
PATCH_ISH_PTY = ROOT / "hermes" / "build" / "patch-ish-pty.py"
PATCH_ISH_DOCUMENTS_FS = ROOT / "hermes" / "build" / "patch-ish-documents-fs.py"
DOCUMENTS_FS_SOURCE = ROOT / "hermes" / "build" / "ish-documents-fs.c"
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
        self.assertIn('xcrun --sdk "$SDK_PLATFORM" --find clang', source)
        self.assertIn("BUILD_MODE=${1:-all}", source)
        self.assertIn('--meson-only', source)
        self.assertIn('--xcode-only', source)
        self.assertIn('--simulator', source)
        self.assertIn('SDK_PLATFORM=iphonesimulator', source)
        self.assertIn('if [ "$BUILD_MODE" = "--xcode-only" ] && [ "$HOST_OS" != Darwin ]; then', source)

    def test_build_patches_pty_and_session_readiness_only_for_the_host_library_build(self) -> None:
        source = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('trap restore_ish_source EXIT', source)
        self.assertIn('python3 "$ROOT/build/patch-ish-pty.py" "$ISH_SOURCE"', source)
        self.assertIn('cp "$ISH_SOURCE/app/LinuxRoot.c" "$SOURCE_PATCH_BACKUP/LinuxRoot.c"', source)
        self.assertIn('cp "$SOURCE_PATCH_BACKUP/LinuxRoot.c" "$ISH_SOURCE/app/LinuxRoot.c"', source)
        self.assertLess(source.index('if [ "$BUILD_MODE" = "--meson-only" ]; then'),
                        source.index('python3 "$ROOT/build/patch-ish-pty.py" "$ISH_SOURCE"'))

    def test_pty_patch_lazily_resolves_the_ptmx_mount_and_handles_errors(self) -> None:
        spec = importlib.util.spec_from_file_location("patch_ish_pty", PATCH_ISH_PTY)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        patcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(patcher)

        with tempfile.TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            app = source_root / "app"
            app.mkdir()
            pty_path = app / "LinuxPTY.c"
            interop_path = app / "LinuxInterop.c"
            root_path = app / "LinuxRoot.c"
            pty_path.write_text(
                patcher.PTY_PATH_DECLARATION + "\n" +
                patcher.PTY_INIT + "\n" + patcher.PTY_OPEN + "\n",
                encoding="utf-8",
            )
            interop_path.write_text(patcher.SESSION_TTY + "\n", encoding="utf-8")
            root_path.write_text(
                patcher.ROOT_DOCUMENTS_DECLARATION + "\n"
                "static __init int ish_rootfs(void) {\n"
                "    init_chroot(\".\");\n\n"
                "    FsInitialize();\n" +
                patcher.ROOTFS_INITCALL + "\n",
                encoding="utf-8",
            )

            patcher.patch(source_root)
            patched_pty = pty_path.read_text(encoding="utf-8")
            patched_interop = interop_path.read_text(encoding="utf-8")
            patched_root = root_path.read_text(encoding="utf-8")
            patcher.patch(source_root)
            self.assertEqual(pty_path.read_text(encoding="utf-8"), patched_pty)
            self.assertEqual(interop_path.read_text(encoding="utf-8"), patched_interop)
            self.assertEqual(root_path.read_text(encoding="utf-8"), patched_root)

        self.assertIn("ios_pty_ensure_initialized()", patched_pty)
        self.assertLess(
            patched_pty.index("static int ios_pty_ensure_initialized(void);"),
            patched_pty.index("struct file *ios_pty_open"),
        )
        self.assertIn('kern_path("/dev/pts/ptmx", 0, &ptmx_path)', patched_pty)
        self.assertIn("return ERR_PTR(err);", patched_pty)
        self.assertIn("if (IS_ERR(session->tty))", patched_interop)
        self.assertIn("done(err, 0, NULL);", patched_interop)
        self.assertIn("rootfs_initcall(ish_rootfs);", patched_root)
        self.assertIn("late_initcall(ish_session_ready);", patched_root)
        self.assertLess(
            patched_root.index("rootfs_initcall(ish_rootfs);"),
            patched_root.index("late_initcall(ish_session_ready);"),
        )
        self.assertLess(
            patched_root.index("init_chroot(\".\");"),
            patched_root.index("ish_mount_documents();"),
        )
        self.assertLess(
            patched_root.index("ish_mount_documents();"),
            patched_root.index("FsInitialize();"),
        )
        self.assertIn("DefaultDocumentsMask()", patched_root)

    def test_documents_filesystem_patch_adds_source_to_pinned_meson_build(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "patch_ish_documents_fs", PATCH_ISH_DOCUMENTS_FS
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        patcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(patcher)

        with tempfile.TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            (source_root / "linux").mkdir()
            meson = source_root / "meson.build"
            meson.write_text(
                "kernel_src = [\n        'linux/fakefs.c',\n]\n",
                encoding="utf-8",
            )
            patcher.patch(source_root, DOCUMENTS_FS_SOURCE)
            patched = meson.read_text(encoding="utf-8")
            patcher.patch(source_root, DOCUMENTS_FS_SOURCE)
            self.assertEqual(meson.read_text(encoding="utf-8"), patched)
            self.assertEqual(patched.count("'linux/documentsfs.c',"), 1)
            self.assertEqual(
                (source_root / "linux" / "documentsfs.c").read_text(encoding="utf-8"),
                DOCUMENTS_FS_SOURCE.read_text(encoding="utf-8"),
            )

    def test_documents_filesystem_supports_mask_remount_without_fakefs_metadata(self) -> None:
        source = DOCUMENTS_FS_SOURCE.read_text(encoding="utf-8")
        self.assertIn('strcmp(param->key, "mask")', source)
        self.assertIn(".reconfigure = documentsfs_reconfigure", source)
        self.assertIn("documentsfs_apply_mask", source)
        self.assertNotIn(".symlink =", source)
        self.assertIn("ATTR_SIZE | ATTR_CTIME", source)
        self.assertIn("-EOPNOTSUPP", source)
        build_script = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('python3 "$ROOT/build/patch-ish-documents-fs.py"', build_script)
        self.assertIn('rm -f "$ISH_SOURCE/linux/documentsfs.c"', build_script)

    def test_pty_patcher_matches_pinned_initcall_declaration(self) -> None:
        source = PATCH_ISH_PTY.read_text(encoding="utf-8")
        self.assertIn("PTY_INIT = \"\"\"static __init int ios_pty_init(void)", source)
        self.assertNotIn("PTY_INIT = \"\"\"static int __init ios_pty_init(void)", source)

    def test_script_builds_upstream_kernel_and_host_interop_targets(self) -> None:
        source = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("app/xcode-meson.sh", source)
        self.assertIn("app/xcode-ninja.sh", source)
        self.assertIn('xcodebuild \\', source)
        self.assertIn('-target "$target"', source)
        self.assertNotIn('-derivedDataPath "$BUILD_ROOT/xcode"', source)
        self.assertIn('CONFIGURATION_BUILD_DIR="$PRODUCTS_DIR"', source)
        self.assertIn('PRODUCTS_DIR="$BUILD_ROOT/xcode/Build/Products/$CONFIGURATION-$SDK_PLATFORM"', source)
        self.assertIn('libiSHLinux.a', source)
        self.assertIn('deps/liblinux.a', source)
        self.assertIn('libfakefs.a', source)
        self.assertIn('libish_emu.a', source)
        self.assertIn("ISH_KERNEL=linux", source)
        self.assertIn('xcrun --sdk "$SDK_PLATFORM" --show-sdk-path', source)
        self.assertIn('exec "$LLVM_BIN/clang" -target "$TARGET_TRIPLE" -isysroot "$SDKROOT"', source)
        self.assertIn('"$MIN_VERSION_FLAG=$IPHONEOS_DEPLOYMENT_TARGET"', source)
        self.assertIn('-sdk "$SDK_PLATFORM"', source)
        self.assertIn('PATH="$TOOLCHAIN_BIN:$PATH"', source)
        self.assertIn('PATH="$LLVM_BIN:$LLD_BIN:$PATH"', source)
        self.assertIn("--target=arm64-apple-ios${IPHONEOS_DEPLOYMENT_TARGET}", source)
        self.assertIn('llvm-ranlib "$MESON_BUILD_DIR/$archive"', source)
        self.assertIn('NINJA_TARGETS="$NINJA_TARGETS"', source)
        self.assertIn("prepare-ish-xcode-project.py", source)
        self.assertIn("brew --prefix llvm", source)
        self.assertIn("brew --prefix lld", source)


class PackageIshFrameworkTests(unittest.TestCase):
    def test_script_has_valid_bash_syntax(self) -> None:
        result = subprocess.run(["bash", "-n", str(PACKAGE_FRAMEWORK_SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_script_links_static_kernel_inputs_into_a_dynamic_framework(self) -> None:
        source = PACKAGE_FRAMEWORK_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("-dynamiclib", source)
        self.assertIn("-D_DARWIN_C_SOURCE=1", source)
        self.assertIn("ish-sections.o", source)
        self.assertIn("-Wl,-sectalign,__DATA,__percpu_first,1000", source)
        self.assertIn("-Wl,-sectalign,__DATA,__tracepoints,20", source)
        self.assertIn("-Wl,-force_load", source)
        self.assertIn("@rpath/Ish.framework/Ish", source)
        self.assertIn("_ish_run_command", source)
        self.assertIn("_ish_rootfs_prepare_fakefs", source)
        self.assertIn("-framework SystemConfiguration", source)
        self.assertIn('-Wl,-force_load,"$LIB_DIR/libfakefs.a"', source)
        self.assertIn("-lresolv", source)
        self.assertNotIn("kernel/errno.h", source)
        self.assertIn("ish_kernel_bridge.m", source)
        self.assertIn('SDK_NAME=${SDK_NAME:-iphoneos}', source)
        self.assertIn("iPhoneSimulator", source)
        self.assertIn("-simulator", source)

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


class PrepareIshXcodeProjectTests(unittest.TestCase):
    def test_removes_only_the_mesongenerated_linux_dependencies(self) -> None:
        project = (
            "/* Begin PBXNativeTarget section */\n"
            "\t\tA /* libiSHLinux */ = {\n"
            "\t\t\tdependencies = (\n"
            "\t\t\t\tBBECF3BE2691417C00DEC937 /* PBXTargetDependency */,\n"
            "\t\t\t);\n"
            "\t\t};\n"
            "\t\tB /* libiSHLinuxUser */ = {\n"
            "\t\t\tdependencies = (\n"
            "\t\t\t\tBBBDDF812CE00F6A0071F1F3 /* PBXTargetDependency */,\n"
            "\t\t\t);\n"
            "\t\t};\n"
            "\t\tC /* liblinux */ = {\n"
            "\t\t\tdependencies = (\n"
            "\t\t\t\tBBECF3B0269136E100DEC937 /* PBXTargetDependency */,\n"
            "\t\t\t);\n"
            "\t\t};\n"
            "/* End PBXNativeTarget section */\n"
            "/* Begin PBXTargetDependency section */\n"
            "\t\tBBECF3BE2691417C00DEC937 /* PBXTargetDependency */ = {\n"
            "\t\t\ttarget = BBECF3AF269136E100DEC937 /* liblinux */;\n"
            "\t\t};\n"
            "\t\tBBBDDF812CE00F6A0071F1F3 /* PBXTargetDependency */ = {\n"
            "\t\t\ttarget = BBECF3AF269136E100DEC937 /* liblinux */;\n"
            "\t\t};\n"
            "/* End PBXTargetDependency section */\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.pbxproj"
            project_path.write_text(project, encoding="utf-8")
            result = subprocess.run(
                ["python3", str(PREPARE_XCODE_PROJECT), str(project_path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            patched = project_path.read_text(encoding="utf-8")
            rerun = subprocess.run(
                ["python3", str(PREPARE_XCODE_PROJECT), str(project_path)],
                capture_output=True,
                text=True,
            )

        self.assertIn("A /* libiSHLinux */ = {\n\t\t\tdependencies = (\n\t\t\t);", patched)
        self.assertIn("B /* libiSHLinuxUser */ = {\n\t\t\tdependencies = (\n\t\t\t);", patched)
        self.assertIn("C /* liblinux */ = {\n\t\t\tdependencies = (\n\t\t\t\tBBECF3B0269136E100DEC937", patched)
        self.assertEqual(rerun.returncode, 0, rerun.stderr)

    def test_rejects_unexpected_upstream_dependency_layout(self) -> None:
        project = (
            "\t\tA /* libiSHLinux */ = {\n"
            "\t\t\tdependencies = (\n"
            "\t\t\t\tBBECF3BE2691417C00DEC937 /* PBXTargetDependency */,\n"
            "\t\t\t\tOTHER /* PBXTargetDependency */,\n"
            "\t\t\t);\n"
            "\t\t};\n"
            "\t\tBBECF3BE2691417C00DEC937 /* PBXTargetDependency */ = {\n"
            "\t\t\ttarget = BBECF3AF269136E100DEC937 /* liblinux */;\n"
            "\t\t};\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "project.pbxproj"
            project_path.write_text(project, encoding="utf-8")
            result = subprocess.run(
                ["python3", str(PREPARE_XCODE_PROJECT), str(project_path)],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected dependency list", result.stderr)


class RepackIshMesonArchivesTests(unittest.TestCase):
    def test_repackages_duplicate_linux_archive_members_using_apple_libtool(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_dir = root / "meson"
            (build_dir / "deps").mkdir(parents=True)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            for archive in ("deps/liblinux.a", "libfakefs.a", "libish_emu.a"):
                (build_dir / archive).write_bytes(b"GNU archive")

            llvm_ar = fake_bin / "llvm-ar"
            llvm_ar.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "from pathlib import Path\n"
                "if sys.argv[1] == 't':\n"
                "    print('duplicate.o\\nduplicate.o\\nunique.o')\n"
                "elif sys.argv[1] == 'xN':\n"
                "    count, archive, member = sys.argv[2:5]\n"
                "    Path(member).write_bytes(f'{member}-{count}'.encode())\n",
                encoding="utf-8",
            )
            llvm_ar.chmod(0o755)

            libtool = fake_bin / "libtool"
            libtool.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "from pathlib import Path\n"
                "output = Path(sys.argv[sys.argv.index('-o') + 1])\n"
                "objects = [Path(arg).read_bytes() for arg in sys.argv[sys.argv.index('-o') + 2:]]\n"
                "output.write_bytes(b'|'.join(objects))\n",
                encoding="utf-8",
            )
            libtool.chmod(0o755)

            result = subprocess.run(
                ["python3", str(REPACK_MESON_ARCHIVES), str(build_dir)],
                capture_output=True,
                text=True,
                env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            for archive in ("deps/liblinux.a", "libfakefs.a", "libish_emu.a"):
                self.assertEqual(
                    (build_dir / archive).read_bytes(),
                    b"duplicate.o-1|duplicate.o-2|unique.o-1",
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

    def _fake_input_with(self, rootfs_path: Path, *, nested_rootfs: bool = False) -> Path:
        input_root = self.work_dir / "input"
        framework = input_root / "Frameworks" / "Ish.framework"
        (framework / "Headers").mkdir(parents=True)
        (framework / "Ish").write_bytes(b"Mach-O Ish framework executable")
        (framework / "Ish").chmod(0o755)
        (framework / "Info.plist").write_text("<plist/>", encoding="utf-8")
        (framework / "Headers" / "ish_kernel_bridge.h").write_text("/* placeholder */\n", encoding="utf-8")
        if nested_rootfs:
            destination = input_root / "Resources" / "ish-rootfs.tar.gz"
            destination.parent.mkdir(parents=True)
        else:
            destination = input_root / "rootfs.tar.gz"
        destination.write_bytes(rootfs_path.read_bytes())
        return input_root

    @unittest.skipUnless(PINNED_ROOTFS.exists(), "pinned iSH rootfs has not been fetched")
    def test_valid_input_installs_the_framework_and_rootfs(self) -> None:
        input_root = self._fake_input_with(PINNED_ROOTFS)
        blink_root = self.work_dir / "blink-root"
        blink_root.mkdir()
        result = subprocess.run(
            ["bash", str(INSTALL_SCRIPT), str(input_root)],
            capture_output=True, text=True,
            env={"BLINK_ROOT": str(blink_root), "PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((blink_root / "Frameworks" / "Ish.framework" / "Ish").is_file())
        self.assertTrue((blink_root / "Frameworks" / "Ish.framework" / "Headers" / "ish_kernel_bridge.h").is_file())
        installed_rootfs = blink_root / "Resources" / "ish-rootfs.tar.gz"
        self.assertTrue(installed_rootfs.is_file())
        self.assertEqual(installed_rootfs.read_bytes(), PINNED_ROOTFS.read_bytes())

    @unittest.skipUnless(PINNED_ROOTFS.exists(), "pinned iSH rootfs has not been fetched")
    def test_runtime_release_layout_installs_nested_rootfs_resource(self) -> None:
        input_root = self._fake_input_with(PINNED_ROOTFS, nested_rootfs=True)
        blink_root = self.work_dir / "blink-root"
        blink_root.mkdir()
        result = subprocess.run(
            ["bash", str(INSTALL_SCRIPT), str(input_root)],
            capture_output=True, text=True,
            env={"BLINK_ROOT": str(blink_root), "PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        installed_rootfs = blink_root / "Resources" / "ish-rootfs.tar.gz"
        self.assertEqual(installed_rootfs.read_bytes(), PINNED_ROOTFS.read_bytes())

    @unittest.skipUnless(PINNED_ROOTFS.exists(), "pinned iSH rootfs has not been fetched")
    def test_missing_framework_executable_is_rejected(self) -> None:
        input_root = self._fake_input_with(PINNED_ROOTFS)
        (input_root / "Frameworks" / "Ish.framework" / "Ish").unlink()
        blink_root = self.work_dir / "blink-root"
        blink_root.mkdir()
        result = subprocess.run(
            ["bash", str(INSTALL_SCRIPT), str(input_root)],
            capture_output=True, text=True,
            env={"BLINK_ROOT": str(blink_root), "PATH": "/usr/bin:/bin"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing iSH framework executable", result.stderr)
        self.assertFalse((blink_root / "Frameworks" / "Ish.framework").exists())

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
