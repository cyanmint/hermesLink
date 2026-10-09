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
        self.assertEqual(commands["clang"], ["MAIN", "clang_main", "", "no"])
        self.assertEqual(commands["python3"], ["MAIN", "python_main", "", "no"])
        self.assertEqual(commands["python"], commands["python3"])
        self.assertEqual(commands["export"], ["shell.framework/shell", "export_main", "", "no"])
        self.assertEqual(commands["setenv"][1], "setenv_main")
        self.assertEqual(commands["unsetenv"][1], "unsetenv_main")
        self.assertEqual(commands["printenv"][1], "printenv_main")
        self.assertEqual(commands["sh"], ["SELF", "sh_main", "c:h:", "file"])

    def test_skill_documents_every_registered_host_command_and_common_ios_utilities(self):
        commands = plistlib.loads(
            (ROOT / "blink/overlay/Resources/blinkCommandsDictionary.plist").read_bytes()
        )
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        for name in commands:
            with self.subTest(command=name):
                self.assertIn(f"`{name}`", skill)
        ios_system_commands = (
            "alias", "awk", "bc", "cat", "cd", "chflags", "cksum", "chmod", "compress",
            "cp", "curl", "date", "dc", "diff", "dig", "du", "echo", "ed", "egrep",
            "env", "fgrep", "find", "grep", "gunzip", "gzip", "head", "host", "ifconfig",
            "link", "ln", "ls", "md5", "mkdir", "mv", "nc", "nslookup", "pbcopy",
            "pbpaste", "ping", "pwd", "readlink", "rlogin", "rm", "rmdir", "sort",
            "stat", "sum", "tail", "tar", "tee", "telnet", "touch", "tr", "unalias",
            "uname", "unlink", "uniq", "uncompress", "uptime", "wc", "whoami", "whois",
            "xargs", "wol",
        )
        for name in ios_system_commands:
            with self.subTest(command=name):
                self.assertIn(f"`{name}`", skill)

    def test_runtime_uses_webkit_wasi_and_keeps_installed_programs_in_documents_bin(self):
        command = (ROOT / "blink/overlay/Blink/Commands/wasm.m").read_text(encoding="utf-8")
        page = (ROOT / "blink/overlay/Resources/WasmRuntime/index.html").read_text(encoding="utf-8")
        wasi_bundle = (ROOT / "blink/overlay/Resources/WasmRuntime/wasmer-wasi.js").read_text(
            encoding="utf-8"
        )
        wasmfs_bundle = (ROOT / "blink/overlay/Resources/WasmRuntime/wasmer-wasmfs.js").read_text(
            encoding="utf-8"
        )

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
        for token in (
            "new WASI.WASI(",
            "new WasmFs.WasmFs()",
            "WebAssembly.Module",
            "preopens:",
            "hermesWasm",
        ):
            with self.subTest(token=token):
                self.assertIn(token, page)
        self.assertTrue(wasi_bundle.startswith("/*"))
        self.assertTrue(wasmfs_bundle.startswith("/*"))
        self.assertIn("Y.WASI=ec", wasi_bundle)
        self.assertIn("Ya.WasmFs=Xc", wasmfs_bundle)

    def test_wasm_uses_a_shell_style_preopens_without_copying_host_directory_trees(self):
        command = (ROOT / "blink/overlay/Blink/Commands/wasm.m").read_text(encoding="utf-8")
        page = (ROOT / "blink/overlay/Resources/WasmRuntime/index.html").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("current working directory is unavailable", command)
        self.assertIn('"cwd": currentDirectory', command)
        self.assertNotIn("HermesWasmFileTree", command)
        self.assertNotIn("HermesApplyWasmFiles", command)
        self.assertNotIn("working directory must be inside Documents", command)
        self.assertNotIn('HermesPathIsInside(resolved, documents)', command)
        self.assertIn("ensureDirectory(fs, input.cwd);", page)
        self.assertIn('preopens: { ".": input.cwd, "/": "/" }', page)
        self.assertNotIn("collectFiles", page)
        self.assertNotIn("input.directories", page)
        self.assertNotIn("input.files", page)
        self.assertIn("does not recursively", readme)

    def test_user_installed_clang_wasm_is_registered_as_a_shell_command(self):
        command = (ROOT / "blink/overlay/Blink/Commands/wasm.m").read_text(encoding="utf-8")

        self.assertIn("int clang_main(int argc, char **argv)", command)
        self.assertIn("pkg install llvm-22", command)
        self.assertIn('stringByAppendingPathComponent:@"clang.wasm"', command)
        self.assertIn("static int HermesInstallLLVM22(void)", command)
        self.assertIn("llvm-22.tar.gz", command)
        self.assertIn("CC_SHA256", command)
        self.assertIn('fputs("  llvm-22 (LLVM/clang C SDK)\\n", thread_stdout);', command)
        self.assertIn('[filename.pathExtension isEqualToString:@"wasm"]', command)
        self.assertIn('stringByDeletingPathExtension', command)
        self.assertIn('commands[name] = @[@"MAIN", @"wasm_main", @"", @"no"]', command)
        self.assertIn('stringByAppendingPathExtension:@"wasm"', command)

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
