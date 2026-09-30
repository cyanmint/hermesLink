import importlib.util
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
