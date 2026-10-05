# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Validates the iSH runtime CI job and its integration into the app archive."""

from __future__ import annotations

import fnmatch
import re
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
        self.assertIn("build-ish-simulator-runtime", self.workflow["jobs"])
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
        self.assertNotIn("ishbridge/*", ish_case)

    def test_ish_runtime_job_runs_on_linux_and_is_blocking(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        self.assertEqual(job["runs-on"], "ubuntu-latest")
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
        self.assertIn("clang lld llvm meson ninja-build curl rsync", steps_text)

    def test_linux_ish_job_builds_host_interop_and_framework_without_xcode(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        self.assertEqual(job["runs-on"], "ubuntu-latest")
        self.assertIn("build-ish-meson", job["needs"])
        steps_text = str(job["steps"])
        self.assertIn("gh release download", steps_text)
        self.assertIn("ISHMesonBuild.tar.gz", steps_text)
        self.assertIn("tar -xzf", steps_text)
        self.assertNotIn("actions/download-artifact@v7", steps_text)
        self.assertIn("build-ish-static.sh --framework-only", steps_text)
        self.assertIn("package-ish-framework.sh", steps_text)
        self.assertNotIn("xcodebuild", steps_text)
        self.assertNotIn("xcrun", steps_text)

    def test_linux_framework_job_installs_and_uses_apple_arm64_ld64(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        steps = job["steps"]
        linker_setup = next(step for step in steps if step["name"] == "Install Apple arm64 linker")
        self.assertEqual(linker_setup["uses"], "mamba-org/setup-micromamba@v3")
        self.assertEqual(linker_setup["with"]["environment-name"], "ish-linker")
        self.assertIn("cctools_osx-arm64=1030.6.3", linker_setup["with"]["create-args"])
        self.assertIn("ld64_osx-arm64=956.6", linker_setup["with"]["create-args"])

        package_step = next(step for step in steps if step["name"] == "Package iSH dynamic framework")
        self.assertEqual(package_step["shell"], "micromamba-shell {0}")
        self.assertIn("arm64-apple-darwin*-ld", package_step["run"])
        self.assertIn("LD64=", package_step["run"])
        package_script = (ROOT / "scripts/hermes/build/package-ish-framework.sh").read_text()
        self.assertIn("--darwin-format", package_script)

        verify_step = next(step for step in steps if step["name"] == "Verify Linux-linked iSH framework")
        self.assertIn("llvm-nm --undefined-only", verify_step["run"])
        self.assertIn("section\\$(start|end)\\$", verify_step["run"])
        self.assertIn("_ish_run_command", verify_step["run"])

    def test_simulator_e2e_builds_and_installs_a_simulator_native_ish_runtime(self) -> None:
        build_job = self.workflow["jobs"]["build-ish-simulator-runtime"]
        self.assertEqual(build_job["runs-on"], "macos-latest")
        self.assertIn("assemble-ipa", build_job["needs"])
        self.assertIn("inputs.run_tests == true", build_job["if"])
        build_steps = str(build_job["steps"])
        self.assertIn("fetch-ish-source.sh", build_steps)
        self.assertIn("build-ish-static.sh --simulator", build_steps)
        self.assertIn("iphonesimulator", build_steps)
        self.assertIn("Resources/ish-rootfs.tar.gz", build_steps)
        self.assertIn("actions/upload-artifact@v7", build_steps)

        simulator_job = self.workflow["jobs"]["simulator-e2e"]
        self.assertIn("assemble-ipa", simulator_job["needs"])
        self.assertIn("build-ish-simulator-runtime", simulator_job["needs"])
        self.assertIn("inputs.run_tests == true", simulator_job["if"])
        simulator_steps = str(simulator_job["steps"])
        self.assertIn("actions/download-artifact@v7", simulator_steps)
        self.assertIn("scripts/install_ish_runtime.sh", simulator_steps)
        self.assertIn("ISH_NATIVE_AVAILABLE = YES", simulator_steps)
        self.assertIn("Run HermesLink tests", simulator_steps)
        self.assertIn("ci_simulator_copilot_e2e.py", simulator_steps)

    def test_four_component_branches_follow_release_preparation(self) -> None:
        jobs = self.workflow["jobs"]
        self.assertIn("prepare-release", jobs["build-runtime-zip"]["needs"])
        self.assertIn("prepare-release", jobs["build-native-runtime"]["needs"])
        self.assertIn("prepare-release", jobs["build-app"]["needs"])
        self.assertIn("prepare-release", jobs["build-ish-meson"]["needs"])
        self.assertNotIn("build-ish-runtime", jobs["build-app"]["needs"])
        self.assertIn("build-ish-meson", jobs["build-ish-runtime"]["needs"])
        self.assertIn("build-app", jobs["assemble-ipa"]["needs"])
        self.assertIn("build-ish-runtime", jobs["assemble-ipa"]["needs"])
        self.assertRegex(
            self.text,
            r'if \[ "\$run_ish_runtime" = true \]; then\n\s+app_changed=true\n\s+fi',
        )

    def test_ipa_waits_for_every_component_success_or_intentional_skip(self) -> None:
        ipa_condition = self.workflow["jobs"]["assemble-ipa"]["if"]
        self.assertIn("build-runtime-zip.result == 'skipped'", ipa_condition)
        self.assertIn("build-native-runtime.result == 'skipped'", ipa_condition)
        self.assertIn("build-ish-meson.result == 'skipped'", ipa_condition)
        self.assertIn("build-ish-runtime.result == 'skipped'", ipa_condition)
        self.assertIn("build-app.result == 'skipped'", ipa_condition)
        self.assertIn("publish-app.result == 'skipped'", ipa_condition)
        self.assertIn("needs.decide.outputs.run_ish_runtime != 'true'", ipa_condition)

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
        build_script = (ROOT / "scripts" / "hermes" / "build" / "build-ish-static.sh").read_text()
        self.assertIn("repack-ish-meson-archives.py", build_script)
        self.assertIn("meson", steps_text.lower())
        self.assertIn("ninja", steps_text.lower())

    def test_ish_runtime_job_publishes_to_the_fixed_release(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        steps_text = str(job["steps"])
        self.assertIn("ISHLinuxNative.zip", steps_text)
        self.assertIn("gh release upload", steps_text)
        self.assertIn("/tmp/hermeslink-ish/source", steps_text)

    def test_decide_path_filter_covers_every_new_ish_build_input(self) -> None:
        for marker in (
            "ishbridge/*", "scripts/hermes/build/build-ish-static.sh",
            "scripts/hermes/build/fetch-ish-source.sh", "scripts/hermes/build/verify-ish-source.py",
            "scripts/hermes/build/patch-ish-pty.py", "scripts/hermes/build/patch-ish-documents-fs.py",
            "scripts/hermes/build/ish-documents-fs.c",
            "scripts/hermes/build/prepare-ish-xcode-project.py",
            "scripts/hermes/build/repack-ish-meson-archives.py",
            "scripts/hermes/build/package-ish-framework.sh",
            "ishbridge/ISHNative.xcconfig", "scripts/install_ish_runtime.sh",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.text)

    def test_ish_bridge_changes_also_trigger_app_builds(self) -> None:
        self.assertIn(
            "scripts/hermes/build/package-ish-framework.sh|ishbridge/ISHNative.xcconfig|ishbridge/*)",
            self.text,
        )
        self.assertIn(
            "blink/*|scripts/blink/*|modules/blink|ishbridge/ISHNative.xcconfig|ishbridge/*|",
            self.text,
        )
        self.assertGreaterEqual(self.text.count("ishbridge/ISHNative.xcconfig"), 1)
        self.assertGreaterEqual(self.text.count("scripts/install_ish_runtime.sh"), 1)

    def test_decide_maps_reorganized_component_paths_to_their_build_stages(self) -> None:
        decision = next(
            step["run"] for step in self.workflow["jobs"]["decide"]["steps"]
            if step.get("id") == "decision"
        )
        cases = [
            block.split("esac", 1)[0]
            for block in decision.split('case "$path" in')[1:]
        ]
        patterns = [
            re.search(r"^\s*([^\n]+)\)\s*$", block, re.MULTILINE).group(1).split("|")
            for block in cases
        ]

        def stages(path: str) -> set[str]:
            return {
                stage for stage, stage_patterns in zip(
                    ("python", "native", "ish-meson", "ish-xcode", "app"),
                    patterns,
                    strict=True,
                )
                if any(fnmatch.fnmatchcase(path, pattern) for pattern in stage_patterns)
            }

        expected = {
            "hermes/overlay/hermes/tools/ish_tool.py": {"python"},
            "hermes/overlay/python/sitecustomize.py": {"python"},
            "hermes/overlay/cpython/Programs/hermes_main.c": {"python", "native"},
            "hermes/overlay/patches/patch-cpython-ios-system.py": {"python", "native"},
            "scripts/hermes/build/build-native-ios.sh": {"native"},
            "scripts/hermes/build/patch-ish-documents-fs.py": {"ish-meson"},
            "modules/ish": {"ish-meson"},
            "scripts/hermes/build/prepare-ish-xcode-project.py": {"ish-xcode"},
            "ishbridge/ISHRootfsProfiles.m": {"ish-xcode", "app"},
            "ishbridge/ISHNative.xcconfig": {"ish-xcode", "app"},
            "blink/patches/patch-settings-viewcontrollers-about-about-html.py": {"app"},
            "scripts/blink/prepare-blink-source.sh": {"app"},
            "tests/hermes/test_ish_ci_workflow.py": set(),
        }
        for path, expected_stages in expected.items():
            with self.subTest(path=path):
                self.assertEqual(stages(path), expected_stages)

    def test_app_archive_excludes_runtime_frameworks_and_rootfs(self) -> None:
        build_steps = str(self.workflow["jobs"]["build-app"]["steps"])
        publish_steps = str(self.workflow["jobs"]["publish-app"]["steps"])
        self.assertNotIn("ISHLinuxNative.zip", build_steps)
        self.assertNotIn("scripts/install_ish_runtime.sh", build_steps)
        self.assertIn("ISH_NATIVE_AVAILABLE = YES", build_steps)
        self.assertIn("ish_kernel_bridge_stub.m", build_steps)
        self.assertIn("ish_rootfs.c", build_steps)
        self.assertIn("-D_DARWIN_C_SOURCE=1", build_steps)
        self.assertIn("@rpath/Ish.framework/Ish", build_steps)
        self.assertIn('test ! -e "$app/Frameworks/HermesRuntime.framework"', publish_steps)
        self.assertIn('test ! -e "$app/Frameworks/Ish.framework"', publish_steps)
        self.assertIn('test ! -e "$app/ish-rootfs.tar.gz"', publish_steps)

    def test_runtime_free_app_packaging_and_release_upload_run_on_linux(self) -> None:
        jobs = self.workflow["jobs"]
        build_app = jobs["build-app"]
        self.assertEqual(build_app["runs-on"], "macos-latest")
        build_steps = str(build_app["steps"])
        self.assertIn("HermesLink.app.tar.gz", build_steps)
        self.assertIn("actions/upload-artifact@v7", build_steps)

        publish_app = jobs["publish-app"]
        self.assertEqual(publish_app["runs-on"], "ubuntu-latest")
        self.assertIn("build-app", publish_app["needs"])
        publish_steps = str(publish_app["steps"])
        self.assertIn("actions/download-artifact@v7", publish_steps)
        self.assertIn("zip -q -r -X", publish_steps)
        self.assertIn("gh release upload", publish_steps)
        self.assertIn("HermesLink.app.zip", publish_steps)
        publish_command = next(
            step["run"] for step in publish_app["steps"]
            if step.get("name") == "Publish runtime-free app archive"
        )
        self.assertNotIn("\\ ", publish_command)
        self.assertIn("publish-app", jobs["assemble-ipa"]["needs"])

    def test_linux_app_cross_compile_is_an_explicit_ubuntu_xcbuild_experiment(self) -> None:
        job = self.workflow["jobs"]["experimental-build-app-linux"]
        self.assertEqual(job["runs-on"], "ubuntu-latest")
        self.assertIn("inputs.linux_app_experiment == true", job["if"])
        steps_text = str(job["steps"])
        self.assertIn("facebookarchive/xcbuild", steps_text)
        self.assertIn("Theos iPhoneOS SDK", steps_text)
        self.assertIn("xcbuild -project Blink.xcodeproj", steps_text)
        self.assertIn("archive 2>&1 | tee", steps_text)
        self.assertIn("CODE_SIGNING_ALLOWED=NO", steps_text)
        self.assertIn("Permissions.h", steps_text)
        self.assertIn("#include <cstdint>", steps_text)
        self.assertIn("Encoding.cpp", steps_text)
        self.assertIn("#include <cstdlib>", steps_text)
        self.assertIn("SWIFTPM_MAX_CONCURRENT_OPERATIONS", steps_text)

    def test_ipa_assembles_runtime_frameworks_and_rootfs_after_app_build(self) -> None:
        steps_text = str(self.workflow["jobs"]["assemble-ipa"]["steps"])
        self.assertIn("ISHLinuxNative.zip", steps_text)
        self.assertIn("Frameworks/Ish.framework", steps_text)
        self.assertIn("Ish.framework/Ish", steps_text)
        self.assertIn("ish-rootfs.tar.gz", steps_text)
        self.assertIn("verify-ish-source.py", steps_text)

    def test_all_e2e_jobs_follow_successful_ipa_assembly(self) -> None:
        jobs = self.workflow["jobs"]
        for name in ("build-ish-simulator-runtime", "simulator-e2e"):
            with self.subTest(job=name):
                self.assertIn("assemble-ipa", jobs[name]["needs"])
                self.assertIn("inputs.run_tests == true", jobs[name]["if"])
        e2e_steps = str(jobs["simulator-e2e"]["steps"])
        self.assertIn("Run HermesLink tests", e2e_steps)
        self.assertIn("ci_simulator_copilot_e2e.py", e2e_steps)

    def test_ish_release_contains_framework_and_pinned_rootfs(self) -> None:
        steps_text = str(self.workflow["jobs"]["build-ish-runtime"]["steps"])
        self.assertIn("Resources/ish-rootfs.tar.gz", steps_text)
        self.assertIn("Frameworks Resources", steps_text)
        decision_script = next(
            step["run"] for step in self.workflow["jobs"]["decide"]["steps"]
            if step.get("id") == "decision"
        )
        self.assertIn("ish-release-check/ISHLinuxNative.zip", decision_script)
        self.assertIn("grep -Fxq Resources/ish-rootfs.tar.gz", decision_script)

    def test_linux_ish_build_compiles_upstream_section_anchors_for_app_link(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        steps_text = str(job["steps"])
        helper = (ROOT / "scripts" / "hermes" / "build" / "build-ish-host-libs.sh").read_text()
        self.assertIn("arch/ish/kernel/sections.S", helper)
        self.assertIn("ish-sections.o", helper)
        self.assertIn("package-ish-framework.sh", steps_text)
        self.assertIn("Frameworks", steps_text)

    def test_ish_linker_configuration_changes_only_the_macos_ish_stage(self) -> None:
        case = self.text.split('case "$path" in')[4].split("esac", 1)[0]
        self.assertIn("ishbridge/ISHNative.xcconfig", case)
        meson_case = self.text.split('case "$path" in')[3].split("esac", 1)[0]
        self.assertNotIn("ISHNative.xcconfig", meson_case)

    def test_ish_native_build_is_not_best_effort(self) -> None:
        job = self.workflow["jobs"]["build-ish-runtime"]
        self.assertFalse(job.get("continue-on-error", False))


if __name__ == "__main__":
    unittest.main()
