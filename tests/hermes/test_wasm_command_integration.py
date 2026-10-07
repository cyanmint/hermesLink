import plistlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class WasmCommandIntegrationTests(unittest.TestCase):
    def test_shell_registers_wasm_pkg_python3_environment_and_nested_shell_commands(self):
        commands = plistlib.loads(
            (ROOT / "blink/overlay/Resources/blinkCommandsDictionary.plist").read_bytes()
        )

        self.assertEqual(commands["wasm"], ["MAIN", "wasm_main", "", "no"])
        self.assertEqual(commands["pkg"], ["MAIN", "pkg_main", "", "no"])
        self.assertEqual(commands["python3"], ["MAIN", "python_main", "", "no"])
        self.assertEqual(commands["python"], commands["python3"])
        self.assertEqual(commands["export"], ["shell.framework/shell", "export_main", "", "no"])
        self.assertEqual(commands["setenv"][1], "setenv_main")
        self.assertEqual(commands["unsetenv"][1], "unsetenv_main")
        self.assertEqual(commands["printenv"][1], "printenv_main")
        self.assertEqual(commands["sh"], ["SELF", "sh_main", "c:h:", "file"])

    def test_runtime_uses_webkit_wasi_and_keeps_installed_programs_in_documents_bin(self):
        command = (ROOT / "blink/overlay/Blink/Commands/wasm.m").read_text(encoding="utf-8")
        page = (ROOT / "blink/overlay/Resources/WasmRuntime/index.html").read_text(encoding="utf-8")

        for token in (
            "WKWebView",
            "WKScriptMessageHandler",
            "HermesLinkRegisterWasmCommands",
            "a-Shell-commands/releases/download/0.1/",
            "Documents",
            "32 * 1024 * 1024",
            "HermesWasmCommandCatalog",
        ):
            with self.subTest(token=token):
                self.assertIn(token, command)
        for token in ("new WASI(", "new WasmFs()", "WebAssembly.Module", "preopens:", "hermesWasm"):
            with self.subTest(token=token):
                self.assertIn(token, page)

    def test_blink_patch_registers_user_bin_after_profile_environment_setup(self):
        patch = (ROOT / "blink/patches/patch-blink-appdelegate-m.py").read_text(encoding="utf-8")

        self.assertIn('stringByAppendingPathComponent:@"bin"', patch)
        self.assertIn('setenv("PATH", [[components componentsJoinedByString:@":"] UTF8String], 1);', patch)
        self.assertIn("HermesLinkConfigureUserBinPath();", patch)
        self.assertIn("HermesLinkRegisterWasmCommands();", patch)
        self.assertLess(patch.index("__setupProcessEnv();"), patch.index("HermesLinkConfigureUserBinPath();"))
        self.assertLess(patch.index("[AppDelegate _loadProfileVars];"), patch.index("HermesLinkRegisterWasmCommands();"))

    def test_xcode_patch_compiles_command_and_bundles_wasi_assets(self):
        patches = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "blink/patches").glob("patch-blink-xcodeproj-project-pbxproj-*.py"))
        )

        for token in ("wasm.m in Sources", "WasmRuntime in Resources", "path = WasmRuntime"):
            with self.subTest(token=token):
                self.assertIn(token, patches)

    def test_wasi_bundles_preserve_licenses_and_wasm_programs_are_not_bundled(self):
        notices = (ROOT / "blink/overlay/Resources/WasmRuntime/THIRD_PARTY_NOTICES.txt").read_text(
            encoding="utf-8"
        )
        wasm_directory = ROOT / "blink/overlay/Resources/WasmRuntime"

        self.assertIn("@wasmer/wasi 0.10.2", notices)
        self.assertIn("@wasmer/wasmfs 0.10.2", notices)
        self.assertFalse(any(path.suffix == ".wasm" for path in wasm_directory.iterdir()))


if __name__ == "__main__":
    unittest.main()
