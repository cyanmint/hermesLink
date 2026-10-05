# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Tests assigning the CI build number while assembling an IPA."""

from __future__ import annotations

import plistlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "hermes" / "build" / "set-ipa-build-number.py"
WORKFLOW = ROOT / ".github" / "workflows" / "build.yml"


class IpaBuildNumberTests(unittest.TestCase):
    def test_sets_bundle_version_without_changing_marketing_version(self) -> None:
        for plist_format in (plistlib.FMT_XML, plistlib.FMT_BINARY):
            with self.subTest(plist_format=plist_format), tempfile.TemporaryDirectory() as directory:
                info_plist = Path(directory) / "Info.plist"
                original = {
                    "CFBundleShortVersionString": "18.8.0",
                    "CFBundleVersion": "0",
                    "CFBundleIdentifier": "com.example.hermeslink",
                }
                with info_plist.open("wb") as stream:
                    plistlib.dump(original, stream, fmt=plist_format)

                subprocess.run(
                    [sys.executable, str(SCRIPT), str(info_plist), "1234"],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                with info_plist.open("rb") as stream:
                    updated = plistlib.load(stream)
                self.assertEqual(updated["CFBundleVersion"], "1234")
                self.assertEqual(updated["CFBundleShortVersionString"], "18.8.0")
                self.assertEqual(updated["CFBundleIdentifier"], "com.example.hermeslink")

    def test_rejects_invalid_build_numbers_without_mutating_the_plist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            info_plist = Path(directory) / "Info.plist"
            original = {"CFBundleVersion": "0"}
            info_plist.write_bytes(plistlib.dumps(original))
            before = info_plist.read_bytes()

            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(info_plist), "12.3"],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(info_plist.read_bytes(), before)

    def test_workflow_changes_build_version_only_during_ipa_assembly(self) -> None:
        import yaml

        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        jobs = workflow["jobs"]
        app_build = jobs["build-app"]
        simulator = jobs["simulator-e2e"]
        assembly = jobs["assemble-ipa"]

        for job, step_name in (
            (app_build, "Cross-compile Blink Xcode project on Linux"),
            (simulator, "Build HermesLink simulator app"),
        ):
            step = next(step for step in job["steps"] if step["name"] == step_name)
            self.assertNotIn("CURRENT_PROJECT_VERSION=", step["run"])

        self.assertNotIn("${{ github.run_number }}", str(app_build["steps"]))

        assembly_steps = assembly["steps"]
        set_version = next(
            step for step in assembly_steps
            if step.get("name") == "Set IPA build number"
        )
        signing = next(step for step in assembly_steps if step.get("name") == "Sign and package IPA")
        self.assertIn("set-ipa-build-number.py", set_version["run"])
        self.assertIn("$HERMESLINK_BUILD_NUMBER", set_version["run"])
        self.assertIn("unzip -p", signing["run"])
        self.assertIn("$EXPECTED_IPA_BUILD_NUMBER", signing["run"])
        self.assertLess(assembly_steps.index(set_version), assembly_steps.index(signing))


if __name__ == "__main__":
    unittest.main()
