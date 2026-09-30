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
                "def get_static_root() -> Path:\n"
                '    return REPO_ROOT / "static"\n'
                "def _discover_agent_dir() -> Path:\n"
                "    return Path(__file__).parent\n",
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
