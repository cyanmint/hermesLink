import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CPYTHON_REPOSITORY = "https://github.com/holzschu/cpython.git"
CPYTHON_REF = "0c3aa6418f2f8d874e1be62e45226af002bbcc8d"


class CPythonSourceTests(unittest.TestCase):
    def test_native_and_zip_builds_use_the_pinned_ashell_source(self):
        for script in (
            ROOT / "hermes" / "build" / "build-native-ios.sh",
            ROOT / "hermes" / "build" / "build-hermesrt-zip.sh",
        ):
            with self.subTest(script=script.name):
                source = script.read_text(encoding="utf-8")
                self.assertIn(f"CPYTHON_REPOSITORY=${{CPYTHON_REPOSITORY:-{CPYTHON_REPOSITORY}}}", source)
                self.assertIn(f"CPYTHON_REF=${{CPYTHON_REF:-{CPYTHON_REF}}}", source)
                self.assertIn("checkout --detach FETCH_HEAD", source)

    def test_native_runtime_build_uses_the_ios_system_shim(self):
        native_build = (ROOT / "hermes" / "build" / "build-native-ios.sh").read_text(
            encoding="utf-8"
        )
        package_build = (ROOT / "hermes" / "build" / "package-native-ios.sh").read_text(
            encoding="utf-8"
        )
        ios_error_header = (ROOT / "hermes" / "overlay" / "cpython" / "ios_error.h").read_text(
            encoding="utf-8"
        )
        package_manifest = (ROOT / "xcfs" / "Package.swift").read_text(encoding="utf-8")

        self.assertIn("ios_system.xcframework/ios-arm64/ios_system.framework", native_build)
        self.assertIn("-I$ROOT/overlay/cpython", native_build)
        self.assertIn("ios_full_waitpid", ios_error_header)
        self.assertIn('-framework ios_system', package_build)
        self.assertIn("releases/download/v3.0.6/ios_system.xcframework.zip", package_manifest)


if __name__ == "__main__":
    unittest.main()
