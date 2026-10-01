import importlib.util
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "hermes" / "overlay" / "hermes" / "hermes_cli" / "upgrade.py"
SPEC = importlib.util.spec_from_file_location("hermes_upgrade_test", MODULE_PATH)
upgrade = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(upgrade)


class RuntimeUpgradeTests(unittest.TestCase):
    def test_upgrade_archive_includes_patched_python_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_path = root / "hermesrt.zip"
            runtime_root = root / "runtime"
            python_root = runtime_root / "python"
            patch_dir = runtime_root / "overlay" / "patches"
            for directory in ("hermes", "hermes-webui", "python"):
                (runtime_root / directory).mkdir(parents=True, exist_ok=True)
            patch_dir.mkdir(parents=True)
            shutil.copyfile(
                ROOT / "hermes" / "overlay" / "patches" / "patch-cpython-ios-system.py",
                patch_dir / "patch-cpython-ios-system.py",
            )
            subprocess_source = (
                '_can_fork_exec = sys.platform not in {"emscripten", "wasi", "tvos", "watchos"}\n'
                "# HERMESLINK_IOS_SYSTEM_BRIDGE_V1: iOS uses ios_system virtual processes, never libc fork/exec.\n"
                'if sys.platform == "ios":\n'
                "    # Route iOS Popen through the patched _posixsubprocess bridge.\n"
                "    _USE_POSIX_SPAWN = False\n"
                "if not _can_fork_exec:\n    raise NotImplementedError()\n"
            )
            (python_root / "subprocess.py").write_text(subprocess_source, encoding="utf-8", newline="\n")
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("timestamp.txt", "1000\n")
                archive.writestr("python/subprocess.py", subprocess_source)
                archive.writestr("python/encodings/__init__.py", "preserved stdlib\n")

            upgrade._apply_cpython_subprocess_patch(runtime_root)
            upgrade._write_archive(archive_path, runtime_root, archive_path)

            with zipfile.ZipFile(archive_path) as archive:
                archived_subprocess = archive.read("python/subprocess.py").decode("utf-8")
                self.assertIn('sys.platform not in {"emscripten", "wasi", "ios", "tvos", "watchos"}', archived_subprocess)
                self.assertNotIn("iOS uses ios_system virtual processes", archived_subprocess)
                self.assertEqual(archive.read("python/encodings/__init__.py"), b"preserved stdlib\n")

    def test_runtime_upgrade_restores_the_ios_subprocess_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            patch_dir = root / "overlay" / "patches"
            python_dir = root / "python"
            patch_dir.mkdir(parents=True)
            python_dir.mkdir()
            shutil.copyfile(
                ROOT / "hermes" / "overlay" / "patches" / "patch-cpython-ios-system.py",
                patch_dir / "patch-cpython-ios-system.py",
            )
            (python_dir / "subprocess.py").write_text(
                '_can_fork_exec = sys.platform not in {"emscripten", "wasi", "tvos", "watchos"}\n'
                "# HERMESLINK_IOS_SYSTEM_BRIDGE_V1: iOS uses ios_system virtual processes, never libc fork/exec.\n"
                "if not _can_fork_exec:\n    raise NotImplementedError()\n",
                encoding="utf-8",
                newline="\n",
            )

            upgrade._apply_cpython_subprocess_patch(root)

            patched = (python_dir / "subprocess.py").read_text(encoding="utf-8")
            self.assertIn('_can_fork_exec = sys.platform not in {"emscripten", "wasi", "ios", "tvos", "watchos"}', patched)
            self.assertNotIn("iOS uses ios_system virtual processes", patched)

    def test_upgrade_rewrites_archive_timestamp_and_preserves_python_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_path = root / "hermesrt.zip"
            runtime_root = root / "runtime"
            for directory in ("hermes", "hermes-webui", "overlay"):
                (runtime_root / directory).mkdir(parents=True)
            (runtime_root / "hermes" / "main.py").write_text("upgraded\n", encoding="utf-8")
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("timestamp.txt", "1000\n")
                archive.writestr("python/encodings/__init__.py", "stdlib\n")

            with patch.object(upgrade.time, "time_ns", return_value=2_000_000_000):
                upgrade._write_archive(archive_path, runtime_root, archive_path)

            with zipfile.ZipFile(archive_path) as archive:
                self.assertEqual(archive.read("timestamp.txt"), b"2000\n")
                self.assertEqual(archive.read("python/encodings/__init__.py"), b"stdlib\n")
                self.assertEqual(archive.getinfo("timestamp.txt").compress_type, zipfile.ZIP_STORED)
                self.assertEqual(
                    sum(info.filename == "timestamp.txt" for info in archive.infolist()),
                    1,
                )
                self.assertTrue(all(info.compress_type == zipfile.ZIP_STORED for info in archive.infolist()))
                self.assertIsNone(archive.testzip())

    def test_runtime_archive_prefers_runtime_root_over_working_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            external = root / "HermesHome" / "hermesrt.zip"
            working = root / "hermesrt.zip"
            external.parent.mkdir()
            external.touch()
            working.touch()

            with patch.dict(
                "os.environ",
                {"HERMES_RUNTIME_ROOT": str(external.parent), "HERMES_HOME": str(root / "other-home")},
            ):
                self.assertEqual(upgrade._runtime_archive(), external)

    def test_runtime_archive_uses_hermes_home_when_no_runtime_root_is_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            home_archive = Path(temporary) / "HermesHome" / "hermesrt.zip"
            home_archive.parent.mkdir()
            home_archive.touch()

            with patch.dict("os.environ", {"HERMES_HOME": str(home_archive.parent)}, clear=True):
                self.assertEqual(upgrade._runtime_archive(), home_archive)


if __name__ == "__main__":
    unittest.main()
