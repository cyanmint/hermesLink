import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATCH_PATH = ROOT / "hermes" / "overlay" / "patches" / "patch-ios-stability.py"


class IosToolDiscoveryTests(unittest.TestCase):
    def test_discovers_self_registering_modules_from_runtime_zip(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("ios_stability_patch_test", PATCH_PATH)
        patcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(patcher)

        registry_source = '''import ast
import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Registry:
    def __init__(self):
        self.registered = []
    def register(self, name):
        self.registered.append(name)

registry = Registry()

def _is_registry_register_call(node):
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "register"
        and isinstance(node.value.func.value, ast.Name)
        and node.value.func.value.id == "registry"
    )

def discover_builtin_tools(tools_dir=None):
    tools_path = Path(__file__).resolve().parent
    imported = [path.stem for path in tools_path.glob("*.py")]
    return imported


def _discovery_cache_path():
    return None
'''
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "hermesrt.zip"
            registry_path = Path(directory) / "registry.py"
            registry_path.write_text(registry_source, encoding="utf-8")

            script = (
                "import json, sys; "
                "sys.path.insert(0, sys.argv[1] + '/hermes'); "
                "from tools.registry import discover_builtin_tools, registry; "
                "print(json.dumps([discover_builtin_tools(), registry.registered]))"
            )

            def run_discovery(source):
                with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
                    archive.writestr("hermes/tools/__init__.py", "")
                    archive.writestr("hermes/tools/registry.py", source)
                    for filename, tool_name in (
                        ("file_tools.py", "read_file"),
                        ("ish_tool.py", "ish"),
                        ("terminal_tool.py", "terminal"),
                    ):
                        archive.writestr(
                            f"hermes/tools/{filename}",
                            f"from tools.registry import registry\nregistry.register({tool_name!r})\n",
                        )
                    archive.writestr(
                        "hermes/tools/helper.py",
                        "from tools.registry import registry\n"
                        "def register_later():\n    registry.register('not-a-tool')\n",
                    )
                result = subprocess.run(
                    [sys.executable, "-c", script, str(archive_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return json.loads(result.stdout)

            self.assertEqual(run_discovery(registry_source), [[], []])

            patcher.patch_zip_tool_discovery(registry_path)
            patched_source = registry_path.read_text(encoding="utf-8")
            patcher.patch_zip_tool_discovery(registry_path)
            self.assertEqual(registry_path.read_text(encoding="utf-8"), patched_source)
            result = run_discovery(patched_source)

        self.assertEqual(
            result,
            [
                ["tools.file_tools", "tools.ish_tool", "tools.terminal_tool"],
                ["read_file", "ish", "terminal"],
            ],
        )


if __name__ == "__main__":
    unittest.main()
