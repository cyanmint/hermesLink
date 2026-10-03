# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
"""Validates the `ish` Hermes Agent tool: its registration module, and the
patch that adds it to the shared core tool list / toolset catalog
(hermes/overlay/patches/patch-ish-tool.py), applied to the real pinned
hermes-agent toolsets.py when it has been fetched."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATCH_SCRIPT = ROOT / "hermes" / "overlay" / "patches" / "patch-ish-tool.py"
TOOL_MODULE = ROOT / "hermes" / "overlay" / "hermes" / "tools" / "ish_tool.py"
PINNED_TOOLSETS = ROOT / "hermes" / "build" / "external" / "hermes-agent" / "toolsets.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_patch(path: Path) -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(PATCH_SCRIPT), str(path)], capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AssertionError(f"patch-ish-tool.py failed: {result.stderr}")


class IshToolModuleTests(unittest.TestCase):
    def test_tool_module_registers_ish_alongside_terminal_semantics(self) -> None:
        source = TOOL_MODULE.read_text(encoding="utf-8")
        self.assertIn('name="ish"', source)
        self.assertIn("registry.register(", source)
        self.assertIn("_hermesios.spawn", source)
        self.assertIn("ish \" + shlex.quote(command)", source)

    def test_tool_description_distinguishes_guest_from_host_terminal(self) -> None:
        source = TOOL_MODULE.read_text(encoding="utf-8")
        self.assertIn("Alpine Linux guest", source)

    def test_check_fn_requires_ios_runtime_and_native_module(self) -> None:
        source = TOOL_MODULE.read_text(encoding="utf-8")
        self.assertIn("def check_ish_requirements", source)
        self.assertIn('sys.platform == "ios"', source)
        self.assertIn("import _hermesios", source)


class IshTogglePatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(tempfile.mkdtemp(prefix="ish-tool-patch-", dir=str(Path.home())))

    def tearDown(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def _minimal_toolsets_fixture(self) -> Path:
        fixture = self.work_dir / "toolsets.py"
        fixture.write_text(
            'def _ts(description, tools=(), includes=(), **extra):\n'
            '    return {"description": description, "tools": list(tools), '
            '"includes": list(includes), **extra}\n\n'
            '_HERMES_CORE_TOOLS = [\n'
            '    "web_search", "web_extract",\n'
            '    "terminal", "process_manage",\n'
            '    "read_file", "write_file",\n'
            ']\n\n'
            'TOOLSETS = {\n'
            '    "terminal": _ts("Terminal/command execution and process management tools", '
            '["terminal", "process_manage"]),\n'
            '    "debugging": _ts("Debugging and troubleshooting toolkit", '
            '["terminal", "process_manage"], includes=["web", "file"]),\n'
            '}\n',
            encoding="utf-8",
        )
        return fixture

    def test_patch_adds_ish_to_core_tools_and_toolsets_on_a_minimal_fixture(self) -> None:
        fixture = self._minimal_toolsets_fixture()
        _run_patch(fixture)
        module = _load_module(fixture, "toolsets_fixture_patched")
        self.assertIn("ish", module._HERMES_CORE_TOOLS)
        self.assertEqual(module.TOOLSETS["ish"]["tools"], ["ish"])
        self.assertIn("ish", module.TOOLSETS["debugging"]["tools"])

    def test_patch_is_idempotent(self) -> None:
        fixture = self._minimal_toolsets_fixture()
        _run_patch(fixture)
        first_pass = fixture.read_text(encoding="utf-8")
        _run_patch(fixture)
        second_pass = fixture.read_text(encoding="utf-8")
        self.assertEqual(first_pass, second_pass)

    def test_patch_does_not_duplicate_terminal_or_process_manage(self) -> None:
        fixture = self._minimal_toolsets_fixture()
        _run_patch(fixture)
        module = _load_module(fixture, "toolsets_fixture_dupcheck")
        self.assertEqual(module._HERMES_CORE_TOOLS.count("terminal"), 1)
        self.assertEqual(module._HERMES_CORE_TOOLS.count("process_manage"), 1)
        self.assertEqual(module._HERMES_CORE_TOOLS.count("ish"), 1)

    @unittest.skipUnless(PINNED_TOOLSETS.exists(), "pinned hermes-agent source has not been fetched")
    def test_patch_applies_cleanly_to_the_real_pinned_toolsets_module(self) -> None:
        staged = self.work_dir / "toolsets_real.py"
        staged.write_text(PINNED_TOOLSETS.read_text(encoding="utf-8"), encoding="utf-8")
        _run_patch(staged)
        module = _load_module(staged, "toolsets_real_patched")

        self.assertIn("ish", module._HERMES_CORE_TOOLS)
        self.assertIn("ish", module.TOOLSETS)
        # Every "hermes-*" bundle and the coding posture share
        # _HERMES_CORE_TOOLS, so they all pick up "ish" automatically, the
        # same way they already do for "terminal".
        for bundle_name in ("hermes-cli", "hermes-telegram", "hermes-discord", "coding"):
            with self.subTest(bundle=bundle_name):
                self.assertIn("ish", module.TOOLSETS[bundle_name]["tools"])
        self.assertIn("ish", module.TOOLSETS["debugging"]["tools"])

    @unittest.skipUnless(PINNED_TOOLSETS.exists(), "pinned hermes-agent source has not been fetched")
    def test_patch_applied_twice_on_the_real_module_is_idempotent(self) -> None:
        staged = self.work_dir / "toolsets_real.py"
        staged.write_text(PINNED_TOOLSETS.read_text(encoding="utf-8"), encoding="utf-8")
        _run_patch(staged)
        first_pass = staged.read_text(encoding="utf-8")
        _run_patch(staged)
        second_pass = staged.read_text(encoding="utf-8")
        self.assertEqual(first_pass, second_pass)


class IshBuildWiringTests(unittest.TestCase):
    def test_runtime_zip_build_applies_the_ish_tool_patch(self) -> None:
        build_script = (ROOT / "scripts" / "hermes" / "build" / "build-hermesrt-zip.sh").read_text(encoding="utf-8")
        self.assertIn("patch-ish-tool.py", build_script)
        self.assertIn('"$STAGE/hermes/toolsets.py"', build_script)

    def test_ish_tool_module_is_placed_under_the_overlay_tools_directory(self) -> None:
        # Mirrors legacy_responses.py's placement convention: new files live
        # under overlay/hermes/<package>/..., copied over the vendored
        # hermes-agent tree without editing any of its own files.
        self.assertTrue(TOOL_MODULE.is_file())
        self.assertEqual(TOOL_MODULE.parent.name, "tools")


if __name__ == "__main__":
    unittest.main()
