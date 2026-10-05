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
XCBUILD_PATCH = ROOT / "scripts" / "blink" / "patch-xcbuild-linux.py"
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
        self.assertEqual(version_patches.count("MARKETING_VERSION = 18.8.0;"), 2)
        self.assertEqual(version_patches.count("MARKETING_VERSION = 18.7.0;"), 2)
        self.assertEqual(version_patches.count("CURRENT_PROJECT_VERSION = 0;"), 2)
        self.assertNotIn("CURRENT_PROJECT_VERSION = 1098;", version_patches)

    def test_workflow_assigns_build_number_only_during_ipa_assembly(self) -> None:
        build_app = self.workflow["jobs"]["build-app"]
        simulator = self.workflow["jobs"]["simulator-e2e"]
        app_build = next(
            step for step in build_app["steps"]
            if step.get("name") == "Cross-compile Blink Xcode project on Linux"
        )
        simulator_build = next(
            step for step in simulator["steps"]
            if step.get("name") == "Build HermesLink simulator app"
        )
        self.assertNotIn("CURRENT_PROJECT_VERSION=", app_build["run"])
        self.assertIn("ARCHS=arm64", app_build["run"])
        self.assertIn("VALID_ARCHS=arm64", app_build["run"])
        self.assertNotIn("CURRENT_PROJECT_VERSION=", simulator_build["run"])
        self.assertNotIn("${{ github.run_number }}", str(build_app["steps"]))
        assembly_steps = self.workflow["jobs"]["assemble-ipa"]["steps"]
        set_version = next(step for step in assembly_steps if step.get("name") == "Set IPA build number")
        self.assertEqual(set_version["env"]["HERMESLINK_BUILD_NUMBER"], "${{ github.run_number }}")
        self.assertIn("set-ipa-build-number.py", set_version["run"])
        self.assertLess(
            assembly_steps.index(set_version),
            next(i for i, step in enumerate(assembly_steps) if step.get("name") == "Sign and package IPA"),
        )

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

    def test_linux_xcbuild_patch_skips_swiftpm_package_product_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resolver = root / "Libraries/pbxbuild/Sources/Build/DependencyResolver.cpp"
            resolver.parent.mkdir(parents=True)
            resolver.write_text(
                "        for (pbxproj::PBX::BuildFile::shared_ptr const &file : buildPhase->files()) {\n"
                "            switch (file->fileRef()->type()) {",
                encoding="utf-8",
            )
            symlink_resolver = root / "Libraries/pbxbuild/Sources/Tool/SymlinkResolver.cpp"
            symlink_resolver.parent.mkdir(parents=True)
            symlink_resolver.write_text(
                'invocation.arguments() = { "-sfh", targetPath, symlinkPath };\n',
                encoding="utf-8",
            )
            product_type_resolver = root / "Libraries/pbxbuild/Sources/Phase/ProductTypeResolver.cpp"
            product_type_resolver.parent.mkdir(parents=True)
            product_type_resolver.write_text(
                "    if (Tool::SymlinkResolver const *symlinkResolver = phaseContext->symlinkResolver(phaseEnvironment)) {\n"
                '        std::string versions = environment.resolve("VERSIONS_FOLDER_PATH");\n',
                encoding="utf-8",
            )
            build_rules = root / "Libraries/pbxbuild/Sources/Target/BuildRules.cpp"
            build_rules.parent.mkdir(parents=True, exist_ok=True)
            build_rules.write_text(
                "                if (std::find(fileTypes.begin(), fileTypes.end(), FT) != fileTypes.end()) {\n"
                "                    return buildRule;\n"
                "                }\n",
                encoding="utf-8",
            )
            clang_spec = root / "Specifications/Compiler/com.apple.compilers.llvm.clang.1_0.xcspec"
            clang_spec.parent.mkdir(parents=True, exist_ok=True)
            clang_spec.write_text(
                "    Identifier = com.apple.compilers.llvm.clang.1_0;\n"
                '    Name = "LLVM Clang";\n',
                encoding="utf-8",
            )
            clang_dispatch = root / "Libraries/pbxbuild/Sources/Phase/Context.cpp"
            clang_dispatch.parent.mkdir(parents=True, exist_ok=True)
            clang_dispatch.write_text(
                "} else if (toolIdentifier == Tool::ClangResolver::ToolIdentifier()) {\n",
                encoding="utf-8",
            )

            subprocess.run([sys.executable, str(XCBUILD_PATCH), str(root)], check=True)
            patched = resolver.read_text(encoding="utf-8")
            self.assertIn("file->fileRef() == nullptr", patched)
            patched_symlink_resolver = symlink_resolver.read_text(encoding="utf-8")
            self.assertIn('"-sfn"', patched_symlink_resolver)
            patched_product_type_resolver = product_type_resolver.read_text(encoding="utf-8")
            self.assertIn('platformName == "iphoneos"', patched_product_type_resolver)
            self.assertIn('platformName == "iphonesimulator"', patched_product_type_resolver)
            patched_build_rules = build_rules.read_text(encoding="utf-8")
            self.assertIn("ruleFileType->identifier() == FT->identifier()", patched_build_rules)
            patched_clang_spec = clang_spec.read_text(encoding="utf-8")
            self.assertIn("SynthesizeBuildRule = YES;", patched_clang_spec)
            patched_clang_dispatch = clang_dispatch.read_text(encoding="utf-8")
            self.assertIn('toolIdentifier == "com.apple.compilers.llvm.clang.1_0"', patched_clang_dispatch)
            product_types = root / "Specifications/HermesLink-iOS-ProductTypes.xcspec"
            specifications = product_types.read_text(encoding="utf-8")
            self.assertIn("com.apple.product-type.application", specifications)
            self.assertIn("com.apple.product-type.app-extension", specifications)
            self.assertIn("com.apple.product-type.framework", specifications)
            self.assertIn('PUBLIC_HEADERS_FOLDER_PATH = "$(WRAPPER_NAME)/Headers";', specifications)
            self.assertIn('MODULES_FOLDER_PATH = "$(WRAPPER_NAME)/Modules";', specifications)

            subprocess.run([sys.executable, str(XCBUILD_PATCH), str(root)], check=True)
            self.assertEqual(resolver.read_text(encoding="utf-8"), patched)
            self.assertEqual(symlink_resolver.read_text(encoding="utf-8"), patched_symlink_resolver)
            self.assertEqual(product_type_resolver.read_text(encoding="utf-8"), patched_product_type_resolver)
            self.assertEqual(build_rules.read_text(encoding="utf-8"), patched_build_rules)
            self.assertEqual(clang_spec.read_text(encoding="utf-8"), patched_clang_spec)
            self.assertEqual(clang_dispatch.read_text(encoding="utf-8"), patched_clang_dispatch)
            self.assertEqual(product_types.read_text(encoding="utf-8"), specifications)

    def test_linux_xcbuild_patch_fails_closed_when_upstream_anchor_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resolver = root / "Libraries/pbxbuild/Sources/Build/DependencyResolver.cpp"
            resolver.parent.mkdir(parents=True)
            resolver.write_text("upstream changed\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(XCBUILD_PATCH), str(root)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("expected one DependencyResolver patch anchor", result.stderr)

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
        self.assertIn(
            '<p>HermesLink is distributed under the '
            '<a href="https://www.gnu.org/licenses/gpl-3.0.html">GNU GPL version 3 (GPLv3)</a>.</p>',
            about_patch,
        )
        self.assertNotIn("About HermesLink</h4>", about_patch)
        self.assertNotIn("HermesLink makes use of and would like to thank", about_patch)
        self.assertNotIn(
            '<a href="https://github.com/blinksh/blink/blob/a90b4423c8b7a86770c24a7eaa6c13b0a5904b18">'
            "Blink Shell</a>",
            about_patch.split("HermesLink components and licenses", 1)[0],
        )
        components = about_patch.split("HermesLink components and licenses", 1)[1]
        self.assertLess(
            components.index(
                '<a href="https://github.com/cyanmint/hermesLink">'
                "HermesLink glue and bridge code and magical mod patches</a>"
            ),
            components.index(
                '<a href="https://github.com/NousResearch/hermes-agent/'
            ),
        )
        self.assertIn(
            "— AI generated content by the agent of @cyanmint; "
            "not applicable to copyright protection.",
            components,
        )
        for dependency in (
            "Mosh", "HTerm", "OpenSSL Toolkit", "Eric Young", "Libssh2",
            "UICKeyChainStore", "MBProgressHUD", "Protobuf", "React",
            "Replxx", "network_ios", "Source Code Pro Font", "DejaVu Sans Mono",
            "Roboto Mono", "Entypo pictograms",
        ):
            with self.subTest(dependency=dependency):
                self.assertIn(dependency, about_patch)
        self.assertEqual(
            about_patch.count(
                '<a href="https://github.com/blinksh/blink/blob/a90b4423c8b7a86770c24a7eaa6c13b0a5904b18/COPYING">'
                "Blink Shell</a>"
            ),
            1,
        )

    def test_app_and_e2e_jobs_initialize_and_patch_pinned_blink_first(self) -> None:
        app_steps = self.workflow["jobs"]["build-app"]["steps"]
        app_stage = next(step for step in app_steps if step.get("name") == "Initialize and stage Blink source")
        app_build = next(
            step for step in app_steps
            if step.get("name") == "Cross-compile Blink Xcode project on Linux"
        )
        self.assertIn("--recursive", app_stage["run"])
        self.assertIn("modules/blink", app_stage["run"])
        self.assertIn("prepare-blink-source.sh", app_stage["run"])
        self.assertLess(app_steps.index(app_stage), app_steps.index(app_build))

        simulator_steps = self.workflow["jobs"]["simulator-e2e"]["steps"]
        source_init = next(
            step for step in simulator_steps
            if step.get("name") == "Initialize pinned Blink source tree"
        )
        prepare = next(
            step for step in simulator_steps
            if step.get("name") == "Apply Blink integration and stage app sources"
        )
        simulator_build = next(
            step for step in simulator_steps
            if step.get("name") == "Build HermesLink simulator app"
        )
        self.assertIn("--recursive", source_init["run"])
        self.assertIn("modules/blink", source_init["run"])
        self.assertLess(simulator_steps.index(source_init), simulator_steps.index(prepare))
        self.assertLess(simulator_steps.index(prepare), simulator_steps.index(simulator_build))

    def test_app_path_filter_includes_blink_integration_inputs(self) -> None:
        self.assertIn("blink/*", self.workflow_text)
        self.assertIn("scripts/blink/prepare-blink-source.sh", self.workflow_text)

    def test_linux_xcbuild_patch_runs_before_incremental_toolchain_build(self) -> None:
        steps = self.workflow["jobs"]["build-app"]["steps"]
        build_tool = next(step for step in steps if step.get("name") == "Build xcbuild on Linux")
        restore_cache = next(
            step for step in steps if step.get("name") == "Restore Linux xcbuild toolchain cache"
        )
        save_cache = next(
            step for step in steps if step.get("name") == "Save Linux xcbuild toolchain cache"
        )
        self.assertIn("patch-xcbuild-linux.py", build_tool["run"])
        self.assertIn("make -C", build_tool["run"])
        self.assertNotIn("if [ ! -x", build_tool["run"])
        self.assertIn(
            "hashFiles('scripts/blink/patch-xcbuild-linux.py', 'scripts/blink/linux-ios-product-types.xcspec')",
            restore_cache["with"]["key"],
        )
        self.assertEqual(restore_cache["with"]["key"], save_cache["with"]["key"])


if __name__ == "__main__":
    unittest.main()
