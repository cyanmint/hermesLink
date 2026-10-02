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

    def test_app_build_failures_emit_raw_xcode_linker_diagnostics(self) -> None:
        app_steps = self.workflow["jobs"]["build-app"]["steps"]
        diagnostic_step = next(
            step for step in app_steps if step["name"] == "Show raw Xcode linker diagnostics"
        )
        self.assertEqual(diagnostic_step["if"], "failure()")
        for marker in (
            "Undefined symbols for architecture",
            "symbol(s) not found for architecture",
            "ld: error:",
        ):
            self.assertIn(marker, diagnostic_step["run"])

    def test_decide_job_exposes_a_run_ish_runtime_output(self) -> None:
        outputs = self.workflow["jobs"]["decide"]["outputs"]
        self.assertIn("run_ish_meson", outputs)
        self.assertIn("run_ish_runtime", outputs)
        self.assertIn("has_asset ISHMesonBuild.tar.gz", self.text)

    def test_unchanged_ish_assets_skip_both_native_build_stages(self) -> None:
        outputs = self.workflow["jobs"]["decide"]["outputs"]
        self.assertIn("run_ish_meson", outputs)
        meson_job = self.workflow["jobs"]["build-ish-meson"]
        xcode_job = self.workflow["jobs"]["build-ish-runtime"]
        self.assertEqual(meson_job["if"], "needs.decide.outputs.run_ish_meson == 'true'")
        self.assertIn("needs.decide.outputs.run_ish_runtime == 'true'", xcode_job["if"])
        self.assertIn("needs.decide.outputs.run_ish_meson != 'true'", xcode_job["if"])
        ish_case = self.text.split('case "$path" in')[3].split("esac", 1)[0]
        self.assertNotIn("ISHBridge/*", ish_case)

    def test_ish_runtime_job_runs_on_macos_and_is_blocking(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        self.assertEqual(job["runs-on"], "macos-latest")
        self.assertFalse(job.get("continue-on-error", False))
        self.assertIn("run_ish_runtime", str(job["if"]))

    def test_ish_meson_archives_are_cross_compiled_and_uploaded_on_linux(self) -> None:
        job = self.workflow["jobs"]["build-ish-meson"]
        self.assertEqual(job["runs-on"], "ubuntu-latest")
        self.assertEqual(job["permissions"]["contents"], "write")
        steps_text = str(job["steps"])
        self.assertIn("build-ish-static.sh --meson-only", steps_text)
        self.assertIn("ISHMesonBuild.tar.gz", steps_text)
        self.assertIn("gh release upload", steps_text)
        self.assertIn("build/ios-toolchain", steps_text)
        self.assertIn("source", steps_text)

    def test_macos_ish_job_downloads_linux_release_and_builds_xcode_targets(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        self.assertIn("build-ish-meson", job["needs"])
        steps_text = str(job["steps"])
        self.assertIn("gh release download", steps_text)
        self.assertIn("ISHMesonBuild.tar.gz", steps_text)
        self.assertIn("tar -xzf", steps_text)
        self.assertNotIn("actions/download-artifact@v7", steps_text)
        self.assertIn("build-ish-static.sh --xcode-only", steps_text)
        self.assertNotIn("Adapt Linux Meson build metadata for macOS", steps_text)

    def test_ish_runtime_job_is_required_for_app_archive_and_ipa(self) -> None:
        for job_name in ("build-app", "assemble-ipa"):
            with self.subTest(job=job_name):
                needs = self.workflow["jobs"][job_name].get("needs", [])
                self.assertIn("build-ish-runtime", needs)
        self.assertRegex(
            self.text,
            r'if \[ "\$run_ish_runtime" = true \]; then\n\s+app_changed=true\n\s+fi',
        )

    def test_requested_ish_build_cannot_be_treated_as_a_skipped_optional_stage(self) -> None:
        app_condition = self.workflow["jobs"]["build-app"]["if"]
        ipa_condition = self.workflow["jobs"]["assemble-ipa"]["if"]
        self.assertIn("needs.decide.outputs.run_ish_runtime != 'true'", app_condition)
        self.assertIn("needs.decide.outputs.run_ish_runtime != 'true'", ipa_condition)
        self.assertIn("build-ish-meson", self.workflow["jobs"]["assemble-ipa"]["needs"])

    def test_workflow_only_changes_do_not_force_runtime_rebuilds(self) -> None:
        self.assertIn('if [[ "$path" == .github/workflows/build.yml ]]; then', self.text)
        self.assertIn("app_changed=true", self.text)
        self.assertNotIn("ish_meson_changed=true\n              app_changed=true", self.text)

    def test_linux_stage_fetches_source_and_macos_builds_via_the_authored_scripts(self) -> None:
        linux_steps = str(self.workflow["jobs"]["build-ish-meson"]["steps"])
        self.assertIn("fetch-ish-source.sh", linux_steps)
        job = self.workflow["jobs"]["build-ish-runtime"]
        steps_text = str(job["steps"])
        self.assertIn("ISHMesonBuild.tar.gz", steps_text)
        self.assertIn("build-ish-static.sh", steps_text)
        build_script = (ROOT / "hermes" / "build" / "build-ish-static.sh").read_text()
        self.assertIn("repack-ish-meson-archives.py", build_script)
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
            "hermes/build/prepare-ish-xcode-project.py",
            "hermes/build/repack-ish-meson-archives.py",
            "hermes/build/ISHNative.xcconfig", "install_ish_runtime.sh",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.text)

    def test_ish_bridge_changes_also_trigger_app_builds(self) -> None:
        self.assertEqual(self.text.count("ISHBridge/*"), 1)
        self.assertGreaterEqual(self.text.count("hermes/build/ISHNative.xcconfig"), 1)
        self.assertGreaterEqual(self.text.count("install_ish_runtime.sh"), 1)

    def test_app_installs_native_ish_and_enables_the_real_bridge(self) -> None:
        job = self.workflow["jobs"]["build-app"]
        steps_text = str(job["steps"])
        self.assertIn("ISHLinuxNative.zip", steps_text)
        self.assertIn("install_ish_runtime.sh", steps_text)
        self.assertIn("ISH_NATIVE_AVAILABLE = YES", steps_text)

    def test_macos_ish_build_compiles_upstream_section_anchors_for_app_link(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        steps = job["steps"]
        compile_step = next(step for step in steps if step["name"] == "Compile iSH Mach-O section anchors")
        self.assertIn("arch/ish/kernel/sections.S", compile_step["run"])
        self.assertIn("ish-sections.o", compile_step["run"])
        self.assertLess(
            steps.index(compile_step),
            next(i for i, step in enumerate(steps) if step["name"] == "Package iSH native build output"),
        )

    def test_ish_linker_configuration_changes_only_the_macos_ish_stage(self) -> None:
        case = self.text.split('case "$path" in')[4].split("esac", 1)[0]
        self.assertIn("hermes/build/ISHNative.xcconfig", case)
        meson_case = self.text.split('case "$path" in')[3].split("esac", 1)[0]
        self.assertNotIn("ISHNative.xcconfig", meson_case)

    def test_ish_native_build_is_not_best_effort(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        self.assertFalse(job.get("continue-on-error", False))


if __name__ == "__main__":
    unittest.main()
