import plistlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class IosShellRegistrationTests(unittest.TestCase):
    def test_sh_is_registered_to_ios_system_shell_handler(self):
        plist_path = ROOT / "Resources" / "blinkCommandsDictionary.plist"
        commands = plistlib.loads(plist_path.read_bytes())

        self.assertEqual(commands["sh"], ["SELF", "sh_main", "c:h:", "file"])

    def test_app_commands_are_loaded_before_embedded_runtime_startup(self):
        app_delegate = (ROOT / "Blink" / "AppDelegate.m").read_text(encoding="utf-8")

        environment_init = app_delegate.index("initializeEnvironment();")
        command_registration = app_delegate.index("addCommandList(")
        runtime_start = app_delegate.index("InstallBundledHermesRuntime();")

        self.assertLess(environment_init, command_registration)
        self.assertLess(command_registration, runtime_start)


if __name__ == "__main__":
    unittest.main()
