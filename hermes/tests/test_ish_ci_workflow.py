# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Validates the iSH runtime CI job and its integration into the app archive."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "build.yml"


class IshRuntimeWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW_PATH.read_text(encoding="utf-8")
        with WORKFLOW_PATH.open(encoding="utf-8") as handle:
            cls.workflow = yaml.safe_load(handle)

    def test_workflow_file_is_valid_yaml(self) -> None:
        self.assertIn("build-ish-runtime", self.workflow["jobs"])
        self.assertIn("build-ish-meson", self.workflow["jobs"])

    def test_decide_job_exposes_a_run_ish_runtime_output(self) -> None:
        outputs = self.workflow["jobs"]["decide"]["outputs"]
        self.assertIn("run_ish_runtime", outputs)

    def test_ish_runtime_job_runs_on_macos_and_is_blocking(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        self.assertEqual(job["runs-on"], "macos-latest")
        self.assertFalse(job.get("continue-on-error", False))
        self.assertIn("run_ish_runtime", str(job["if"]))

    def test_ish_meson_archives_are_cross_compiled_and_uploaded_on_linux(self) -> None:
        job = self.workflow["jobs"]["build-ish-meson"]
        self.assertEqual(job["runs-on"], "ubuntu-latest")
        steps_text = str(job["steps"])
        self.assertIn("build-ish-static.sh --meson-only", steps_text)
        self.assertIn("actions/upload-artifact@v7", steps_text)
        self.assertIn("include-hidden-files", steps_text)

    def test_macos_ish_job_downloads_linux_archives_and_builds_xcode_targets(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        self.assertIn("build-ish-meson", job["needs"])
        steps_text = str(job["steps"])
        self.assertIn("actions/download-artifact@v7", steps_text)
        self.assertIn("build-ish-static.sh --xcode-only", steps_text)

    def test_ish_runtime_job_is_required_for_app_archive_and_ipa(self) -> None:
        for job_name in ("build-app", "assemble-ipa"):
            with self.subTest(job=job_name):
                needs = self.workflow["jobs"][job_name].get("needs", [])
                self.assertIn("build-ish-runtime", needs)

    def test_ish_runtime_job_fetches_and_builds_via_the_authored_scripts(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        steps_text = str(job["steps"])
        self.assertIn("fetch-ish-source.sh", steps_text)
        self.assertIn("build-ish-static.sh", steps_text)
        self.assertIn("meson", steps_text.lower())
        self.assertIn("ninja", steps_text.lower())

    def test_ish_runtime_job_publishes_to_the_fixed_release(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        steps_text = str(job["steps"])
        self.assertIn("ISHLinuxNative.zip", steps_text)
        self.assertIn("gh release upload", steps_text)

    def test_decide_path_filter_covers_every_new_ish_build_input(self) -> None:
        for marker in (
            "ISHBridge/*", "hermes/build/build-ish-static.sh",
            "hermes/build/fetch-ish-source.sh", "hermes/build/verify-ish-source.py",
            "hermes/build/ISHNative.xcconfig", "install_ish_runtime.sh",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.text)

    def test_ish_bridge_changes_also_trigger_app_builds(self) -> None:
        self.assertGreaterEqual(self.text.count("ISHBridge/*"), 2)
        self.assertGreaterEqual(self.text.count("hermes/build/ISHNative.xcconfig"), 2)
        self.assertGreaterEqual(self.text.count("install_ish_runtime.sh"), 2)

    def test_app_installs_native_ish_and_enables_the_real_bridge(self) -> None:
        job = self.workflow["jobs"]["build-app"]
        steps_text = str(job["steps"])
        self.assertIn("ISHLinuxNative.zip", steps_text)
        self.assertIn("install_ish_runtime.sh", steps_text)
        self.assertIn("ISH_NATIVE_AVAILABLE = YES", steps_text)

    def test_ish_native_build_is_not_best_effort(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        self.assertFalse(job.get("continue-on-error", False))


if __name__ == "__main__":
    unittest.main()
