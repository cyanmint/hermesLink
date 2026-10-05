# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Build sources must come from pinned, recursively initialized submodules."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SUBMODULES = {
    "modules/blink": "https://github.com/blinksh/blink.git",
    "modules/hermes-agent": "https://github.com/NousResearch/hermes-agent.git",
    "modules/hermes-webui": "https://github.com/nesquena/hermes-webui.git",
    "modules/cpython": "https://github.com/python/cpython.git",
    "modules/ish": "https://github.com/ish-app/ish.git",
    "modules/openssl": "https://github.com/openssl/openssl.git",
}


class BuildSourceSubmoduleTests(unittest.TestCase):
    def test_gitmodules_registers_all_build_source_repositories(self) -> None:
        result = subprocess.run(
            ["git", "config", "-f", str(ROOT / ".gitmodules"), "--get-regexp", r"^submodule\..*\.url$"],
            capture_output=True,
            text=True,
            check=True,
        )
        actual = {}
        for line in result.stdout.splitlines():
            key, url = line.split(maxsplit=1)
            path = key.removeprefix("submodule.").removesuffix(".url")
            actual[path] = url
        self.assertEqual(actual, EXPECTED_SUBMODULES)

    def test_build_scripts_use_modules_without_cloning_source(self) -> None:
        scripts = {
            "scripts/blink/prepare-blink-source.sh": "modules/blink",
            "scripts/hermes/build/fetch-sources.sh": "modules/hermes-agent",
            "scripts/hermes/build/fetch-ish-source.sh": "modules/ish",
            "scripts/hermes/build/build-ish-static.sh": "modules/ish",
        }
        for relative_path, module_path in scripts.items():
            with self.subTest(script=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn(module_path, source)
                self.assertNotIn("github.com/ish-app/ish.git", source)
                self.assertNotIn("github.com/blinksh/blink.git", source)
                if relative_path in {
                    "scripts/hermes/build/fetch-sources.sh",
                    "scripts/hermes/build/fetch-ish-source.sh",
                }:
                    self.assertNotRegex(source, r"\bgit\s+(?:clone|fetch)\b")

    def test_runtime_builds_use_pinned_source_submodules(self) -> None:
        zip_build = (ROOT / "scripts/hermes/build/build-hermesrt-zip.sh").read_text(encoding="utf-8")
        native_build = (ROOT / "scripts/hermes/build/build-native-ios.sh").read_text(encoding="utf-8")
        for module in ("modules/hermes-agent", "modules/hermes-webui", "modules/cpython"):
            with self.subTest(module=module):
                self.assertIn(module, zip_build)
        for module in ("modules/cpython", "modules/openssl"):
            with self.subTest(module=module):
                self.assertIn(module, native_build)
        self.assertIn('"$CPYTHON_ROOT/configure"', native_build)
        self.assertNotIn('"$CPYTHON_ROOT/Configure"', native_build)
        self.assertNotRegex(zip_build, r"\bgit\s+(?:clone|fetch)\b")
        self.assertNotIn("https://github.com/python/cpython.git", native_build)
        self.assertNotIn("https://github.com/openssl/openssl.git", native_build)

    def test_ci_initializes_each_source_submodule_recursively(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
        for module in EXPECTED_SUBMODULES:
            with self.subTest(module=module):
                self.assertIn(module, workflow)
        self.assertIn("git submodule update --init --recursive --checkout --depth 1 -- modules/ish", workflow)
        self.assertIn("git submodule update --init --recursive --depth 1 -- modules/blink", workflow)
        self.assertIn("git submodule update --init --depth 1 -- modules/cpython modules/hermes-agent modules/hermes-webui", workflow)
        self.assertIn("git submodule update --init --depth 1 -- modules/cpython modules/openssl", workflow)

    def test_developer_setup_uses_recursive_clone(self) -> None:
        develop = (ROOT / "DEVELOP.md").read_text(encoding="utf-8")
        self.assertIn("git clone --recurse-submodules --shallow-submodules", develop)
        self.assertIn("git submodule update --init --recursive --depth 1", develop)
        self.assertIn("git -C modules/ish submodule update --init --recursive --checkout --depth 1", develop)

    def test_gitmodules_is_not_ignored(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("/.gitmodules", gitignore.splitlines())

    def test_submodule_pins_match_the_build_source_pins(self) -> None:
        pins = {
            "modules/blink": "a90b4423c8b7a86770c24a7eaa6c13b0a5904b18",
            "modules/hermes-agent": "2246c245f51e03eb6a151d19119009156e84659a",
            "modules/hermes-webui": "e36f77389191fe9d81cd3a7416772e2f7b022e19",
            "modules/cpython": "8183fa5e3f78ca6ab862de7fb8b14f3d929421e0",
            "modules/ish": "83348361fe65311f6e87ad2e1cbb0ac38d123f69",
            "modules/openssl": "fb7fab9fa6f4869eaa8fbb97e0d593159f03ffe4",
        }
        staged = subprocess.run(
            ["git", "ls-files", "--stage", "--", *pins],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        ).stdout
        actual = {}
        for line in staged.splitlines():
            metadata, path = line.split("\t", 1)
            mode, commit, _stage = metadata.split()
            self.assertEqual(mode, "160000", path)
            actual[path] = commit
        for module, expected in pins.items():
            with self.subTest(module=module):
                self.assertEqual(actual.get(module), expected)


if __name__ == "__main__":
    unittest.main()
