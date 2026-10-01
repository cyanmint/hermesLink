import importlib
import json
import os
import plistlib
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATCH_PATH = ROOT / "hermes" / "overlay" / "patches" / "patch-webui-zip.py"


class UserVisiblePathTests(unittest.TestCase):
    def test_app_uses_actual_shared_documents_directory_for_hermes_home(self):
        app_delegate = (ROOT / "Blink" / "AppDelegate.m").read_text(encoding="utf-8")
        mcp_session = (ROOT / "Sessions" / "MCPSession.m").read_text(encoding="utf-8")
        blink_paths = (ROOT / "BlinkConfig" / "BlinkPaths.m").read_text(encoding="utf-8")

        self.assertIn('NSString *hermesHomePath = [BlinkPaths hermesHomePath];', app_delegate)
        self.assertIn('setenv("HERMES_HOME", hermesHomePath.UTF8String, 1);', app_delegate)
        self.assertIn('setenv("HERMES_RUNTIME_ROOT", hermesHomePath.UTF8String, 1);', app_delegate)
        self.assertIn('NSString *workspacePath = [documentsPath stringByAppendingPathComponent:@"workspace"];', app_delegate)
        self.assertIn('setenv("HERMES_WEBUI_DEFAULT_WORKSPACE", workspacePath.UTF8String, 1);', app_delegate)
        self.assertIn('setenv("TERMINAL_CWD", workspacePath.UTF8String, 1);', app_delegate)
        self.assertIn('NSString *documentsPath = [BlinkPaths documentsPath];', mcp_session)
        self.assertIn('NSString *workspacePath = [documentsPath stringByAppendingPathComponent:@"workspace"];', mcp_session)
        self.assertIn('NSString *hermesHomePath = [BlinkPaths hermesHomePath];', mcp_session)
        self.assertIn('setenv("HERMES_HOME", hermesHomePath.UTF8String, 1);', mcp_session)
        self.assertIn('setenv("HERMES_WEBUI_DEFAULT_WORKSPACE", workspacePath.UTF8String, 1);', mcp_session)
        self.assertIn('setenv("TERMINAL_CWD", workspacePath.UTF8String, 1);', mcp_session)
        self.assertIn('setenv("PWD", workspacePath.UTF8String, 1);', mcp_session)
        self.assertNotIn('stringByAppendingPathComponent:@"Documents"', mcp_session)
        self.assertIn('[[self documentsPath] stringByAppendingPathComponent:@"HermesHome"]', blink_paths)

    def test_app_documents_are_enabled_for_files_and_file_sharing(self):
        with (ROOT / "Blink" / "Info.plist").open("rb") as stream:
            info = plistlib.load(stream)

        self.assertIs(info["UIFileSharingEnabled"], True)
        self.assertIs(info["LSSupportsOpeningDocumentsInPlace"], True)

    def test_app_installs_embedded_runtime_only_when_newer_and_loads_external_zip(self):
        app_delegate = (ROOT / "Blink" / "AppDelegate.m").read_text(encoding="utf-8")
        command = (ROOT / "Blink" / "Commands" / "hermes.m").read_text(encoding="utf-8")

        self.assertIn('InstallBundledHermesRuntime();', app_delegate)
        self.assertIn('installedTimestamp >= bundledTimestamp', app_delegate)
        self.assertIn('HermesRuntimeTimestamp(installedPath, YES)', app_delegate)
        self.assertIn('localNameLength > localHeaderRemainder', app_delegate)
        self.assertIn('compressedSize > centralOffset - dataOffset', app_delegate)
        self.assertIn('HermesCRCMatches(bytes + dataOffset, uncompressedSize, crc)', app_delegate)
        self.assertIn('rename(temporaryPath.fileSystemRepresentation, installedPath.fileSystemRepresentation)', app_delegate)
        self.assertIn('stringByAppendingPathComponent:@"hermesrt.zip"', command)
        self.assertIn('setenv("HERMES_RUNTIME_ROOT", [BlinkPaths hermesHomePath].UTF8String, 1);', command)
        self.assertNotIn('bundle pathForResource:@"hermesrt"', command)

    def test_ios_documents_workspace_is_exempt_from_private_var_blocklist(self):
        with tempfile.TemporaryDirectory() as temporary:
            api_dir = Path(temporary) / "api"
            api_dir.mkdir()
            config_path = api_dir / "config.py"
            config_path.write_text(
                "import os\n"
                "from pathlib import Path\n"
                'HOST = os.getenv("HERMES_WEBUI_HOST", "127.0.0.1")\n'
                'PORT = int(os.getenv("HERMES_WEBUI_PORT", "8787"))\n'
                "def get_static_root() -> Path:\n"
                '    return REPO_ROOT / "static"\n'
                "def _discover_agent_dir() -> Path:\n"
                '    """Locate the agent checkout.\n'
                '    """\n'
                '    return Path("agent")\n'
                'LAST_WORKSPACE_FILE = STATE_DIR / "last_workspace.txt"\n',
                encoding="utf-8",
                newline="\n",
            )
            workspace_path = api_dir / "workspace.py"
            workspace_path.write_text(
                "from pathlib import Path, PurePosixPath\n"
                '_BOOT_DEFAULT_WORKSPACE = PurePosixPath("/private/var/mobile/Containers/Data/Application/01234567-89ab-cdef-0123-456789abcdef/Documents/workspace")\n'
                "def _is_blocked_posix_workspace_path(path):\n"
                '    value = PurePosixPath(str(path))\n'
                '    return value == PurePosixPath("/private/var") or value.is_relative_to(PurePosixPath("/private/var"))\n'
                "def _is_blocked_workspace_path(candidate: Path, raw_path: str | Path | None = None) -> bool:\n"
                '    """Return True when candidate points at a known OS/system directory.\n'
                '    Compare raw and resolved paths.\n'
                '    """\n'
                "    posix_probe = raw_path if raw_path is not None else candidate.as_posix()\n"
                "    if _is_blocked_posix_workspace_path(posix_probe):\n"
                "        return True\n"
                "    return False\n",
                encoding="utf-8",
                newline="\n",
            )
            subprocess.run([sys.executable, str(PATCH_PATH), str(config_path)], check=True)
            subprocess.run([sys.executable, str(PATCH_PATH), str(config_path)], check=True)

            patched_workspace = workspace_path.read_text(encoding="utf-8")
            self.assertEqual(patched_workspace.count("def _hermes_ios_documents_workspace("), 1)
            self.assertEqual(patched_workspace.count("if _hermes_ios_documents_workspace(candidate):"), 1)
            namespace = {}
            exec(compile(patched_workspace, str(workspace_path), "exec"), namespace)
            default_workspace = namespace["_BOOT_DEFAULT_WORKSPACE"]
            self.assertFalse(namespace["_is_blocked_workspace_path"](default_workspace, default_workspace))
            self.assertFalse(
                namespace["_is_blocked_workspace_path"](
                    default_workspace / "project",
                    default_workspace / "project",
                )
            )
            self.assertTrue(
                namespace["_is_blocked_workspace_path"](
                    default_workspace.parent / "private-data",
                    default_workspace.parent / "private-data",
                )
            )
            namespace["_BOOT_DEFAULT_WORKSPACE"] = namespace["PurePosixPath"]("/private/var/db/workspace")
            self.assertTrue(
                namespace["_is_blocked_workspace_path"](
                    namespace["_BOOT_DEFAULT_WORKSPACE"],
                    namespace["_BOOT_DEFAULT_WORKSPACE"],
                )
            )

    def test_zip_agent_imports_directly_and_legacy_workspace_pointers_migrate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            visible_home = root / "Files" / "HermesHome"
            state_dir = visible_home / "webui"
            state_dir.mkdir(parents=True)
            legacy_home = root / "private" / "home"
            legacy_workspace = legacy_home / "workspace"
            preferred_workspace = root / "Files" / "workspace"
            settings_path = state_dir / "settings.json"
            workspaces_path = state_dir / "workspaces.json"
            last_workspace_path = state_dir / "last_workspace.txt"
            settings_path.write_text(
                json.dumps({"default_workspace": str(legacy_workspace), "theme": "dark"}),
                encoding="utf-8",
            )
            workspaces_path.write_text(
                json.dumps([{"path": str(legacy_workspace), "name": "Home"}]),
                encoding="utf-8",
            )
            last_workspace_path.write_text(str(legacy_workspace), encoding="utf-8")
            config = root / "config.py"
            config.write_text(
                "import json\n"
                "import os\n"
                "import sys\n"
                "import zipfile\n"
                "from pathlib import Path\n"
                'HOME = Path(os.environ["HERMES_TEST_HOME"])\n'
                'STATE_DIR = Path(os.environ["HERMES_WEBUI_STATE_DIR"])\n'
                'SETTINGS_FILE = STATE_DIR / "settings.json"\n'
                'WORKSPACES_FILE = STATE_DIR / "workspaces.json"\n'
                'LAST_WORKSPACE_FILE = STATE_DIR / "last_workspace.txt"\n'
                "REPO_ROOT = Path(__file__).parent.parent\n"
                'HOST = os.getenv("HERMES_WEBUI_HOST", "127.0.0.1")\n'
                'PORT = int(os.getenv("HERMES_WEBUI_PORT", "8787"))\n'
                "def get_static_root() -> Path:\n"
                '    return REPO_ROOT / "static"\n'
                "def _discover_agent_dir() -> Path:\n"
                "    return Path(__file__).parent\n",
                encoding="utf-8",
                newline="\n",
            )
            (root / "workspace.py").write_text(
                "from pathlib import Path, PurePosixPath\n"
                '_BOOT_DEFAULT_WORKSPACE = PurePosixPath("/workspace")\n'
                "def _is_blocked_workspace_path(candidate: Path, raw_path: str | Path | None = None) -> bool:\n"
                '    """Return True when candidate points at a known OS/system directory.\n'
                '    Compare raw and resolved paths.\n'
                '    """\n'
                "    posix_probe = raw_path if raw_path is not None else candidate.as_posix()\n"
                "    if _is_blocked_posix_workspace_path(posix_probe):\n"
                "        return True\n"
                "    return False\n",
                encoding="utf-8",
                newline="\n",
            )
            subprocess.run([sys.executable, str(PATCH_PATH), str(config)], check=True)

            archive = root / "hermesrt.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.write(config, "hermes_webui/api/config.py")
                bundle.writestr("hermes_webui/api/__init__.py", "")
                bundle.writestr("hermes_webui/__init__.py", "")
                bundle.writestr("hermes_webui/static/index.html", "visible webui assets")
                bundle.writestr("hermes/hermes_cli/__init__.py", "")
                bundle.writestr("hermes/hermes_cli/main.py", "# visible agent source\n")

            sys.path.insert(0, str(archive))
            env_names = ("HERMES_HOME", "HERMES_WEBUI_DEFAULT_WORKSPACE", "HERMES_TEST_HOME", "HERMES_WEBUI_STATE_DIR")
            old_env = {name: os.environ.get(name) for name in env_names}
            os.environ["HERMES_HOME"] = str(visible_home)
            os.environ["HERMES_WEBUI_DEFAULT_WORKSPACE"] = str(preferred_workspace)
            os.environ["HERMES_TEST_HOME"] = str(legacy_home)
            os.environ["HERMES_WEBUI_STATE_DIR"] = str(state_dir)
            try:
                module = importlib.import_module("hermes_webui.api.config")
                static_root = module.get_static_root()
                agent_root = module._discover_agent_dir()
                self.assertEqual(static_root, visible_home / "WebUIStatic")
                self.assertEqual((static_root / "index.html").read_text(encoding="utf-8"), "visible webui assets")
                self.assertEqual(agent_root, Path(str(archive.resolve()) + "/hermes"))
                self.assertFalse((visible_home / "HermesAgent").exists())
                sys.path.insert(0, str(agent_root))
                agent_module = importlib.import_module("hermes_cli.main")
                self.assertEqual(
                    Path(agent_module.__file__),
                    Path(str(archive.resolve()) + "/hermes/hermes_cli/main.py"),
                )
                migrated_settings = json.loads(settings_path.read_text(encoding="utf-8"))
                migrated_workspaces = json.loads(workspaces_path.read_text(encoding="utf-8"))
                preferred_path = str(preferred_workspace.resolve())
                self.assertEqual(migrated_settings["default_workspace"], preferred_path)
                self.assertEqual(migrated_workspaces[0]["path"], preferred_path)
                self.assertEqual(last_workspace_path.read_text(encoding="utf-8").strip(), preferred_path)
                self.assertFalse(static_root.name.startswith("."))
            finally:
                if "agent_root" in locals() and str(agent_root) in sys.path:
                    sys.path.remove(str(agent_root))
                sys.path.remove(str(archive))
                sys.modules.pop("hermes_cli.main", None)
                sys.modules.pop("hermes_cli", None)
                sys.modules.pop("hermes_webui.api.config", None)
                sys.modules.pop("hermes_webui.api", None)
                sys.modules.pop("hermes_webui", None)
                for name, value in old_env.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
