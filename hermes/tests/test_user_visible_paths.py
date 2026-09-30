import importlib
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
        self.assertIn('NSString *workspacePath = [BlinkPaths documentsPath];', mcp_session)
        self.assertIn('NSString *hermesHomePath = [BlinkPaths hermesHomePath];', mcp_session)
        self.assertIn('setenv("HERMES_HOME", hermesHomePath.UTF8String, 1);', mcp_session)
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

    def test_hermes_webui_uses_the_files_visible_documents_workspace(self):
        command = (ROOT / "Blink" / "Commands" / "hermes.m").read_text(encoding="utf-8")
        build_script = (ROOT / "hermes" / "build" / "build-hermesrt-zip.sh").read_text(encoding="utf-8")
        patch_script = (ROOT / "hermes" / "overlay" / "patches" / "patch-webui-zip.py").read_text(encoding="utf-8")

        self.assertIn('setenv("HERMES_IOS_HOME_ROOT", BlinkPaths.homePath.UTF8String, 1);', command)
        self.assertIn('setenv("HERMES_IOS_DOCUMENTS_ROOT", documentsPath.UTF8String, 1);', command)
        self.assertIn('stringByAppendingPathComponent:@"workspace"', command)
        self.assertIn('setenv("HERMES_WEBUI_DEFAULT_WORKSPACE", workspacePath.UTF8String, 1);', command)
        self.assertIn('setenv("HOME", documentsPath.UTF8String, 1) != 0', command)
        self.assertIn('setenv("HOME", previousHome, 1);', command)
        self.assertIn('unsetenv("HOME");', command)
        self.assertIn('"$STAGE/hermes-webui/api/workspace.py"', build_script)
        self.assertIn('"$STAGE/hermes-webui/static/onboarding.js"', build_script)
        self.assertIn('ios_default_workspace = os.environ.get("HERMES_WEBUI_DEFAULT_WORKSPACE")', patch_script)
        self.assertIn("if _is_blocked_workspace_path(candidate, raw):", patch_script)
        self.assertIn("if _is_blocked_workspace_path(p, path):", patch_script)
        self.assertIn('if resolved_candidate == documents_root or documents_root in resolved_candidate.parents:', patch_script)
        self.assertIn("setupProvider&&setupProvider.default_model", patch_script)

    def test_zip_agent_and_webui_assets_extract_to_visible_named_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "config.py"
            config.write_text(
                "import os\n"
                "import sys\n"
                "from pathlib import Path\n"
                "REPO_ROOT = Path(__file__).parent.parent\n"
                'HOST = os.getenv("HERMES_WEBUI_HOST", "127.0.0.1")\n'
                'PORT = int(os.getenv("HERMES_WEBUI_PORT", "8787"))\n'
                "def _workspace_candidates(raw: str | Path | None = None) -> list[Path]:\n"
                '    """Return ordered candidate workspace paths, de-duplicated."""\n'
                "    candidates: list[Path] = []\n"
                "    if raw:\n"
                "        candidates.append(Path(raw))\n"
                "    candidates.append(Path.home() / 'workspace')\n"
                "    return candidates\n"
                "def resolve_default_workspace(raw: str | Path | None = None) -> Path:\n"
                "    return _workspace_candidates(raw)[0]\n"
                "DEFAULT_WORKSPACE = resolve_default_workspace()\n"
                "def get_static_root() -> Path:\n"
                '    return REPO_ROOT / "static"\n'
                "def _discover_agent_dir() -> Path:\n"
                "    return Path(__file__).parent\n",
                encoding="utf-8",
                newline="\n",
            )
            workspace = root / "workspace.py"
            onboarding = root / "onboarding.js"
            onboarding.write_text(
                "async function _saveOnboardingProviderSetup(){\n"
                "  const provider=(ONBOARDING.form.provider||'').trim();\n"
                "  const model=(ONBOARDING.form.model||'').trim();\n"
                "  const body={provider,model};\n"
                "}\n",
                encoding="utf-8",
                newline="\n",
            )
            workspace.write_text(
                "import os\n"
                "from pathlib import Path\n"
                "def _resolve_path(candidate):\n"
                "    return Path(candidate).resolve()\n"
                "def _profile_default_workspace() -> str:\n"
                "    return '/app-support/home/workspace'\n"
                "def _last_workspace_file():\n"
                "    return Path(__file__).with_name('last_workspace.txt')\n"
                "def get_last_workspace() -> str:\n"
                "    if _last_workspace_file().exists():\n"
                "        return _last_workspace_file().read_text()\n"
                "    return os.path.join(os.environ['HOME'], 'workspace')\n"
                "def get_profile_default_workspace() -> str:\n"
                "    def _valid(raw):\n"
                "        if Path(raw).is_dir():\n"
                "            return raw\n"
                "        return None\n"
                "    return _valid(os.path.join(os.environ['HOME'], 'workspace')) or _profile_default_workspace()\n"
                "def load_workspaces() -> list:\n"
                "    return [{'path': os.environ['HOME'] + '/workspace', 'name': 'Old'}]\n"
                "def save_workspaces(workspaces: list) -> None:\n"
                "    global SAVED_WORKSPACES\n"
                "    SAVED_WORKSPACES = workspaces\n"
                "def set_last_workspace(path: str) -> None:\n"
                "    global SAVED_LAST_WORKSPACE\n"
                "    SAVED_LAST_WORKSPACE = path\n"
                'def list_workspace_suggestions(prefix: str = "", limit: int = 12) -> list[str]:\n'
                "    return [prefix]\n"
                "def validate_workspace_to_add(path: str) -> Path:\n"
                "    return _resolve_path(path)\n"
                "def _workspace_access_error(candidate):\n"
                "    return None if candidate.is_dir() else f'Path does not exist: {candidate}'\n"
                "def resolve_trusted_workspace(path: str | Path | None = None) -> Path:\n"
                "    candidate = _resolve_path(path)\n"
                "\n"
                "    access_error = _workspace_access_error(candidate)\n"
                "    if access_error:\n"
                "        raise ValueError(access_error)\n"
                "    if _is_blocked_workspace_path(candidate, path):\n"
                "        raise ValueError(f'Path points to a system directory: {candidate}')\n"
                "    return candidate\n"
                "def _clean_workspace_list(workspaces):\n"
                "    result = []\n"
                "    for w in workspaces:\n"
                "        path = w.get('path', '')\n"
                "        p = Path(path).resolve()\n"
                "        # Skip paths inside a DIFFERENT profile's directory\n"
                "        result.append({'path': str(p), 'name': w.get('name', '')})\n"
                "    return result\n"
                "def _is_blocked_workspace_path(candidate, raw_path=None):\n"
                '    """Reject blocked OS paths."""\n'
                "    raw = None\n"
                '    if raw_path not in (None, ""):\n'
                "        raw = Path(raw_path)\n"
                "    return candidate == Path('/etc') or str(candidate).startswith(os.environ.get('HERMES_IOS_HOME_ROOT', '/never'))\n",
                encoding="utf-8",
                newline="\n",
            )
            subprocess.run(
                [sys.executable, str(PATCH_PATH), str(config), str(workspace), str(onboarding)],
                check=True,
            )
            patched_onboarding = onboarding.read_text(encoding="utf-8")
            self.assertIn(
                "ONBOARDING.form.model||(_getOnboardingCurrentSetup()||{}).model",
                patched_onboarding,
            )
            self.assertIn("if(!model) throw new Error", patched_onboarding)
            spec = importlib.util.spec_from_file_location("patched_workspace", workspace)
            patched_workspace = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(patched_workspace)
            old_documents_root = os.environ.get("HERMES_IOS_DOCUMENTS_ROOT")
            old_ios_home_root = os.environ.get("HERMES_IOS_HOME_ROOT")
            old_default_workspace = os.environ.get("HERMES_WEBUI_DEFAULT_WORKSPACE")
            old_home = os.environ.get("HOME")
            documents = root / "Documents"
            documents_workspace = documents / "workspace"
            hidden_home = root / "AppGroup" / "home"
            documents_workspace.mkdir(parents=True)
            (documents_workspace / "nested").mkdir()
            hidden_workspace = hidden_home / "workspace"
            (hidden_workspace / "nested").mkdir(parents=True)
            (workspace.parent / "last_workspace.txt").write_text(str(hidden_workspace))
            os.environ["HOME"] = str(hidden_home)
            os.environ["HERMES_IOS_HOME_ROOT"] = str(hidden_home)
            os.environ["HERMES_IOS_DOCUMENTS_ROOT"] = str(documents)
            os.environ["HERMES_WEBUI_DEFAULT_WORKSPACE"] = str(hidden_workspace)
            try:
                subprocess.run(
                    [sys.executable, str(PATCH_PATH), str(config), str(workspace), str(onboarding)],
                    check=True,
                )
                spec = importlib.util.spec_from_file_location("patched_config", config)
                patched_config = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(patched_config)
                self.assertEqual(
                    patched_config.DEFAULT_WORKSPACE, documents_workspace.resolve()
                )
                self.assertEqual(
                    patched_config.resolve_default_workspace(Path("/etc")),
                    documents_workspace.resolve(),
                )
                self.assertEqual(
                    patched_workspace._profile_default_workspace(), str(documents_workspace.resolve())
                )
                self.assertEqual(
                    patched_workspace.get_last_workspace(), str(documents_workspace.resolve())
                )
                self.assertEqual(
                    patched_workspace.get_profile_default_workspace(), str(documents_workspace.resolve())
                )
                self.assertEqual(
                    patched_workspace.load_workspaces(),
                    [{"path": str(documents_workspace.resolve()), "name": "Home"}],
                )
                patched_workspace.save_workspaces([{"path": "/etc", "name": "System"}])
                self.assertEqual(
                    patched_workspace.SAVED_WORKSPACES,
                    [{"path": str(documents_workspace.resolve()), "name": "Home"}],
                )
                patched_workspace.set_last_workspace("/usr")
                self.assertEqual(
                    patched_workspace.SAVED_LAST_WORKSPACE, str(documents_workspace.resolve())
                )
                self.assertEqual(
                    patched_workspace.list_workspace_suggestions("/etc"),
                    [str(documents_workspace.resolve())],
                )
                self.assertEqual(
                    patched_workspace.validate_workspace_to_add("/etc"),
                    documents_workspace.resolve(),
                )
                self.assertEqual(
                    patched_workspace.resolve_trusted_workspace("/etc"),
                    documents_workspace.resolve(),
                )
                self.assertEqual(
                    patched_workspace.resolve_trusted_workspace(hidden_workspace / "nested"),
                    documents_workspace.resolve(),
                )
                self.assertTrue(
                    patched_workspace._is_blocked_workspace_path(hidden_workspace.resolve())
                )
                cleaned = patched_workspace._clean_workspace_list(
                    [
                        {"path": str(hidden_workspace), "name": "Home"},
                        {"path": str(documents), "name": "Documents"},
                    ]
                )
                self.assertEqual(
                    cleaned, [{"path": str(documents.resolve()), "name": "Documents"}]
                )
                self.assertFalse(patched_workspace._is_blocked_workspace_path(documents_workspace))
                self.assertTrue(patched_workspace._is_blocked_workspace_path(Path("/etc")))
            finally:
                if old_documents_root is None:
                    os.environ.pop("HERMES_IOS_DOCUMENTS_ROOT", None)
                else:
                    os.environ["HERMES_IOS_DOCUMENTS_ROOT"] = old_documents_root
                if old_ios_home_root is None:
                    os.environ.pop("HERMES_IOS_HOME_ROOT", None)
                else:
                    os.environ["HERMES_IOS_HOME_ROOT"] = old_ios_home_root
                if old_default_workspace is None:
                    os.environ.pop("HERMES_WEBUI_DEFAULT_WORKSPACE", None)
                else:
                    os.environ["HERMES_WEBUI_DEFAULT_WORKSPACE"] = old_default_workspace
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home

            archive = root / "hermesrt.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.write(config, "hermes_webui/api/config.py")
                bundle.writestr("hermes_webui/api/__init__.py", "")
                bundle.writestr("hermes_webui/__init__.py", "")
                bundle.writestr("hermes_webui/static/index.html", "visible webui assets")
                bundle.writestr("hermes/hermes_cli/main.py", "# visible agent source\n")

            visible_home = root / "Files" / "HermesHome"
            visible_home.mkdir(parents=True)
            sys.path.insert(0, str(archive))
            old_home = os.environ.get("HERMES_HOME")
            os.environ["HERMES_HOME"] = str(visible_home)
            try:
                module = importlib.import_module("hermes_webui.api.config")
                static_root = module.get_static_root()
                agent_root = module._discover_agent_dir()
                self.assertEqual(static_root, visible_home / "WebUIStatic")
                self.assertEqual((static_root / "index.html").read_text(encoding="utf-8"), "visible webui assets")
                self.assertEqual(agent_root, visible_home / "HermesAgent")
                self.assertTrue((agent_root / "hermes_cli" / "main.py").is_file())
                self.assertFalse(static_root.name.startswith("."))
                self.assertFalse(agent_root.name.startswith("."))
            finally:
                sys.path.remove(str(archive))
                sys.modules.pop("hermes_webui.api.config", None)
                sys.modules.pop("hermes_webui.api", None)
                sys.modules.pop("hermes_webui", None)
                if old_home is None:
                    os.environ.pop("HERMES_HOME", None)
                else:
                    os.environ["HERMES_HOME"] = old_home


if __name__ == "__main__":
    unittest.main()
