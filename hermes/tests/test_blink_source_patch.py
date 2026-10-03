# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Checks that CI reconstructs the pinned Blink app from its integration patch."""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / "hermes" / "blink" / "UPSTREAM_REVISION"
PATCH_DIR = ROOT / "hermes" / "blink" / "patches"
OVERLAY = ROOT / "hermes" / "blink" / "overlay"
PREPARE_SCRIPT = ROOT / "hermes" / "build" / "prepare-blink-source.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "build.yml"


class BlinkSourcePatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.revision = PIN.read_text(encoding="ascii").strip()
        cls.patches = sorted(PATCH_DIR.glob("*.patch"))
        cls.script = PREPARE_SCRIPT.read_text(encoding="utf-8")
        cls.workflow_text = WORKFLOW.read_text(encoding="utf-8")
        cls.workflow = yaml.safe_load(cls.workflow_text)

    def test_upstream_revision_is_immutable_and_patches_are_small_per_file(self) -> None:
        self.assertRegex(self.revision, re.compile(r"^[0-9a-f]{40}$"))
        self.assertGreaterEqual(len(self.patches), 20)
        for patch in self.patches:
            text = patch.read_text(encoding="utf-8")
            with self.subTest(patch=patch.name):
                self.assertLess(patch.stat().st_size, 32 * 1024)
                self.assertEqual(text.count("diff --git "), 1)
                self.assertNotIn("GIT binary patch", text)

    def test_new_app_glue_and_binary_assets_live_in_the_overlay(self) -> None:
        for path in (
            "Blink/Commands/hermes.m",
            "Blink/Commands/ish.m",
            "Blink/Commands/ishfs.m",
            "Resources/blinkCommandsDictionary.plist",
            "Settings/ISHRootfsSettingsView.swift",
            "template_setup.xcconfig",
            "DarkAppIcon/dark-app-iphone-60pt@2x.png",
            "Media.xcassets/AppIcon.appiconset/Icon-1024@1x.png",
        ):
            with self.subTest(path=path):
                self.assertTrue((OVERLAY / path).is_file())

    def test_blink_app_sources_are_not_tracked_in_this_repository(self) -> None:
        tracked = subprocess.check_output(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
        ).decode("utf-8").split("\0")
        source_roots = (
            "Blink",
            "Blink.xcodeproj",
            "BlinkConfig",
            "DarkAppIcon",
            "Media.xcassets",
            "Resources",
            "Sessions",
            "Settings",
        )
        retained = [
            path for path in tracked
            if any(path == root or path.startswith(root + "/") for root in source_roots)
        ]
        self.assertEqual(retained, [])

    def test_preparation_script_checks_revision_and_applies_patch_before_staging(self) -> None:
        self.assertIn("rev-parse HEAD", self.script)
        self.assertIn("git -C \"$source_root\" apply --check \"$patch_file\"", self.script)
        self.assertIn("git -C \"$source_root\" apply \"$patch_file\"", self.script)
        self.assertIn("rsync -a", self.script)
        for excluded_path in (".git", ".github", ".gitignore", "README.md", "BUILD.md", "Frameworks"):
            with self.subTest(path=excluded_path):
                self.assertIn(f"--exclude='/{excluded_path}'", self.script)

    def test_app_and_e2e_jobs_checkout_and_patch_pinned_blink_first(self) -> None:
        for job_name, build_step in (
            ("build-app", "Build unsigned device archive"),
            ("simulator-e2e", "Build HermesLink simulator app"),
        ):
            with self.subTest(job=job_name):
                steps = self.workflow["jobs"][job_name]["steps"]
                revision_step = next(step for step in steps if step.get("id") == "blink_revision")
                source_checkout = next(
                    step for step in steps
                    if step.get("uses") == "actions/checkout@v7"
                    and step.get("with", {}).get("repository") == "blinksh/blink"
                )
                prepare = next(step for step in steps if step.get("name") == "Apply Blink integration and stage app sources")
                build = next(step for step in steps if step.get("name") == build_step)
                self.assertIn("hermes/blink/UPSTREAM_REVISION", revision_step["run"])
                self.assertEqual(source_checkout["with"]["ref"], "${{ steps.blink_revision.outputs.sha }}")
                self.assertEqual(source_checkout["with"]["path"], ".blink-upstream")
                self.assertLess(steps.index(source_checkout), steps.index(prepare))
                self.assertLess(steps.index(prepare), steps.index(build))

    def test_app_cache_and_path_filter_include_blink_integration_inputs(self) -> None:
        self.assertIn("hermes/blink/*", self.workflow_text)
        self.assertIn("hermes/blink/**", self.workflow_text)
        self.assertIn("hermes/build/prepare-blink-source.sh", self.workflow_text)


if __name__ == "__main__":
    unittest.main()
