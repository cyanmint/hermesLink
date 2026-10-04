# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Checks that CI reconstructs the pinned Blink app from glue and patch scripts."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / "blink" / "UPSTREAM_REVISION"
PATCH_DIR = ROOT / "blink" / "patches"
OVERLAY = ROOT / "blink" / "overlay"
PREPARE_SCRIPT = ROOT / "scripts" / "blink" / "prepare-blink-source.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "build.yml"


class BlinkSourcePatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.revision = PIN.read_text(encoding="ascii").strip()
        cls.patches = sorted(PATCH_DIR.glob("patch-*.py"))
        cls.script = PREPARE_SCRIPT.read_text(encoding="utf-8")
        cls.workflow_text = WORKFLOW.read_text(encoding="utf-8")
        cls.workflow = yaml.safe_load(cls.workflow_text)

    def test_upstream_revision_is_fixed_and_source_patches_are_small_python_scripts(self) -> None:
        self.assertRegex(self.revision, re.compile(r"^[0-9a-f]{40}$"))
        self.assertGreaterEqual(len(self.patches), 30)
        self.assertEqual(list(PATCH_DIR.glob("*.patch")), [])
        for patch in self.patches:
            text = patch.read_text(encoding="utf-8")
            tree = ast.parse(text)
            target_assignments = [
                node for node in tree.body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "TARGET" for target in node.targets)
            ]
            with self.subTest(patch=patch.name):
                self.assertLess(patch.stat().st_size, 20 * 1024)
                self.assertIn("from _patch_utils import apply_file", text)
                self.assertEqual(len(target_assignments), 1)

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

    def test_app_and_session_default_workspace_is_documents(self) -> None:
        for patch_name in (
            "patch-blink-appdelegate-m.py",
            "patch-sessions-mcpsession-m.py",
        ):
            tree = ast.parse((PATCH_DIR / patch_name).read_text(encoding="utf-8"))
            replacements = next(
                node.value
                for node in tree.body
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "REPLACEMENTS"
                    for target in node.targets
                )
            )
            patched_source = "\n".join(
                replacement[2] for replacement in ast.literal_eval(replacements)
            )
            with self.subTest(patch=patch_name):
                self.assertIn(
                    'setenv("HERMES_WEBUI_DEFAULT_WORKSPACE", documentsPath.UTF8String, 1);',
                    patched_source,
                )
                self.assertIn('chdir(documentsPath.UTF8String);', patched_source)
                self.assertNotIn('stringByAppendingPathComponent:@"workspace"', patched_source)

    def test_app_version_is_bumped_and_build_number_defaults_to_zero(self) -> None:
        version_patches = "\n".join(
            (PATCH_DIR / patch_name).read_text(encoding="utf-8")
            for patch_name in (
                "patch-blink-xcodeproj-project-pbxproj-08.py",
                "patch-blink-xcodeproj-project-pbxproj-09.py",
                "patch-blink-xcodeproj-project-pbxproj-10.py",
            )
        )
        self.assertEqual(version_patches.count("MARKETING_VERSION = 18.8.0;"), 4)
        self.assertEqual(version_patches.count("CURRENT_PROJECT_VERSION = 0;"), 2)
        self.assertNotIn("MARKETING_VERSION = 18.7.0;", version_patches)
        self.assertNotIn("CURRENT_PROJECT_VERSION = 1098;", version_patches)

    def test_workflow_uses_run_number_for_app_build_number(self) -> None:
        build_app = self.workflow["jobs"]["build-app"]
        simulator = self.workflow["jobs"]["simulator-e2e"]
        self.assertEqual(
            self.workflow["env"]["HERMESLINK_BUILD_NUMBER"],
            "${{ github.run_number }}",
        )
        archive = next(
            step for step in build_app["steps"]
            if step.get("name") == "Build unsigned device archive"
        )
        simulator_build = next(
            step for step in simulator["steps"]
            if step.get("name") == "Build HermesLink simulator app"
        )
        self.assertIn('CURRENT_PROJECT_VERSION="$HERMESLINK_BUILD_NUMBER"', archive["run"])
        self.assertIn('CURRENT_PROJECT_VERSION="$HERMESLINK_BUILD_NUMBER"', simulator_build["run"])
        app_cache = next(
            step for step in build_app["steps"]
            if step.get("name") == "Cache unsigned app archive"
        )
        self.assertIn("${{ github.run_number }}", app_cache["with"]["key"])

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
            "Frameworks",
            "Media.xcassets",
            "Resources",
            "Sessions",
            "Settings",
            ".gitmodules",
        )
        retained = [
            path for path in tracked
            if any(path == root or path.startswith(root + "/") for root in source_roots)
        ]
        self.assertEqual(retained, [])

    def test_root_attribution_and_license_files_are_hermeslink_specific(self) -> None:
        authors = (ROOT / "AUTHORS").read_text(encoding="utf-8")
        copying = (ROOT / "COPYING.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("HermesLink authorship", authors)
        self.assertIn("generated with", authors)
        self.assertIn("https://www.gnu.org/licenses/gpl-3.0.html", copying)
        self.assertFalse((ROOT / "LICENSES").exists())
        self.assertIn("HermesLink", readme)
        self.assertNotIn("Do Blink!", readme)

    def test_preparation_script_checks_revision_and_runs_patch_scripts_before_staging(self) -> None:
        self.assertIn("rev-parse HEAD", self.script)
        self.assertIn("apply-patches.py", self.script)
        self.assertIn("rsync -a \"$integration_root/blink/overlay/\"", self.script)
        self.assertIn('rsync -a "$integration_root/ishbridge/" "$source_root/ISHBridge/"', self.script)
        utility = (PATCH_DIR / "_patch_utils.py").read_text(encoding="utf-8")
        self.assertIn("ambiguous source anchors", utility)
        self.assertIn("source anchor not found", utility)
        self.assertIn("rsync -a", self.script)
        for excluded_path in (
            ".git", ".github", ".gitignore", ".gitmodules", "AUTHORS",
            "COPYING", "COPYING.md", "README.md", "BUILD.md", "DEVELOP.md",
        ):
            with self.subTest(path=excluded_path):
                exclude = f"--exclude='{excluded_path if excluded_path == '.git' else '/' + excluded_path}'"
                self.assertIn(exclude, self.script)
        self.assertNotIn("--exclude='/Frameworks'", self.script)

    def test_unavailable_icloud_container_does_not_create_a_nil_directory(self) -> None:
        patch = PATCH_DIR / "patch-blinkconfig-blinkpaths-m.py"
        source = (
            "  return __documentsPath;\n"
            "}\n\n"
            "+ (NSString *)groupContainerPath {\n"
            "  if (__groupContainerPath == nil) {\n\n"
            "\n"
            "    NSFileManager *fm = [NSFileManager defaultManager];\n"
            "    NSString *path = [fm containerURLForSecurityApplicationGroupIdentifier:groupID].path;\n"
            "    __groupContainerPath = path;\n"
            "  }\n"
            "  return __groupContainerPath;\n"
            "\n"
            "+ (void)_linkAtPath:(NSString *)path destinationPath:(NSString *)destinationPath {\n"
            "  NSFileManager *fm = [NSFileManager defaultManager];\n"
            "  \n"
            "  // Don't use fileExists as that would traverse the symlink.\n"
            "  if ([fm attributesOfItemAtPath:path error:nil]) {\n"
            "+ (void)_ensureFolderAtPath:(NSString *)path {\n"
            "  BOOL isDir = NO;\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            source_root = Path(temporary)
            blink_paths = source_root / "BlinkConfig" / "BlinkPaths.m"
            blink_paths.parent.mkdir()
            blink_paths.write_text(source, encoding="utf-8")

            subprocess.run([sys.executable, str(patch), str(source_root)], check=True)
            patched = blink_paths.read_text(encoding="utf-8")
            self.assertIn('if (path.length == 0) {', patched)
            self.assertIn('Skipping folder creation for unavailable path', patched)

            subprocess.run([sys.executable, str(patch), str(source_root)], check=True)
            self.assertEqual(blink_paths.read_text(encoding="utf-8"), patched)

    def test_about_page_lists_every_named_component_with_license_links(self) -> None:
        copying = (ROOT / "COPYING.md").read_text(encoding="utf-8")
        about_patch = (PATCH_DIR / "patch-settings-viewcontrollers-about-about-html.py").read_text(encoding="utf-8")
        for component in (
            "Hermes Agent", "Hermes WebUI", "Blink Shell", "a-Shell",
            "CPython", "iSH", "ios_system",
        ):
            with self.subTest(component=component):
                self.assertIn(component, copying)
                self.assertIn(f">{component}</a>", about_patch)
        for license_name in (
            "MIT License", "GNU GPL version 3", "BSD 3-Clause License",
            "Python Software Foundation License Version 2",
        ):
            with self.subTest(license=license_name):
                self.assertIn(license_name, copying)
                self.assertIn(license_name, about_patch)
        self.assertIn("HermesLink components and licenses", about_patch)
        self.assertNotIn("Blink Shell upstream acknowledgments", about_patch)
        for dependency in (
            "Mosh", "HTerm", "OpenSSL Toolkit", "Eric Young", "Libssh2",
            "UICKeyChainStore", "MBProgressHUD", "Protobuf", "React",
            "Replxx", "network_ios", "Source Code Pro Font", "DejaVu Sans Mono",
            "Roboto Mono", "Entypo pictograms",
        ):
            with self.subTest(dependency=dependency):
                self.assertIn(dependency, about_patch)
        self.assertIn("HermesLink makes use of and would like to thank the following open source projects", about_patch)

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
                self.assertIn("blink/UPSTREAM_REVISION", revision_step["run"])
                self.assertEqual(source_checkout["with"]["ref"], "${{ steps.blink_revision.outputs.sha }}")
                self.assertEqual(source_checkout["with"]["path"], ".blink-upstream")
                self.assertEqual(source_checkout["with"]["submodules"], "recursive")
                self.assertLess(steps.index(source_checkout), steps.index(prepare))
                self.assertLess(steps.index(prepare), steps.index(build))

    def test_app_cache_and_path_filter_include_blink_integration_inputs(self) -> None:
        self.assertIn("blink/*", self.workflow_text)
        self.assertIn("blink/**", self.workflow_text)
        self.assertIn("scripts/blink/prepare-blink-source.sh", self.workflow_text)


if __name__ == "__main__":
    unittest.main()
