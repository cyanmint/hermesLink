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
                self.assertIn("git checkout --detach FETCH_HEAD", source)


if __name__ == "__main__":
    unittest.main()
