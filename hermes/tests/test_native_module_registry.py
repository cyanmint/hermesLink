import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "build" / "generate-native-module-registry.py"
SPEC = importlib.util.spec_from_file_location("native_module_registry", SCRIPT_PATH)
registry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry)

CONFIG_PATH = Path(__file__).resolve().parents[1] / "build" / "configure_native_modules.py"
CONFIG_SPEC = importlib.util.spec_from_file_location("native_module_config", CONFIG_PATH)
module_config = importlib.util.module_from_spec(CONFIG_SPEC)
CONFIG_SPEC.loader.exec_module(module_config)

RUNTIME_SOURCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "overlay"
    / "cpython"
    / "Programs"
    / "hermes_main.c"
)


class NativeModuleRegistryTests(unittest.TestCase):
    def test_discovers_only_defined_python_module_initializers(self):
        nm_output = """\
0000000000000000 T _PyInit__ssl
                 U _PyInit__asyncio
0000000000000010 T _PyInit_zlib
                 U PyInit_absent
"""

        self.assertEqual(registry.parse_defined_initializers(nm_output), ["_ssl", "zlib"])

    def test_emits_registry_only_for_discovered_initializers(self):
        source = registry.render_registry(["_ssl", "zlib"])

        self.assertIn("PyImport_AppendInittab(\"_ssl\", PyInit__ssl);", source)
        self.assertIn("PyImport_AppendInittab(\"zlib\", PyInit_zlib);", source)
        self.assertNotIn("PyInit__asyncio", source)

    def test_empty_initializer_set_still_emits_valid_function(self):
        source = registry.render_registry([])

        self.assertIn("int hermes_register_native_modules(void) {", source)
        self.assertIn("return 0;", source)

    def test_enables_ssl_extensions_when_configure_disables_them(self):
        setup_lines = ["*static*", "#_ssl _ssl.c", "#_hashlib _hashopenssl.c"]

        result = module_config.ensure_required_static_modules(setup_lines)

        self.assertEqual(result[-2:], ["_ssl _ssl.c", "_hashlib _hashopenssl.c"])

    def test_enables_runtime_extensions_when_configure_disables_them(self):
        setup_lines = ["*static*", "#_posixsubprocess _posixsubprocess.c", "#_blake2"]

        result = module_config.ensure_required_static_modules(setup_lines)

        self.assertIn("_posixsubprocess _posixsubprocess.c", result)
        self.assertIn(
            "_blake2 _blake2/blake2module.c _blake2/blake2b_impl.c "
            "_blake2/blake2s_impl.c",
            result,
        )

    def test_does_not_duplicate_ssl_extensions_already_enabled(self):
        setup_lines = ["*static*", "_ssl _ssl.c", "_hashlib _hashopenssl.c"]

        result = module_config.ensure_required_static_modules(setup_lines)

        self.assertEqual(result.count("_ssl _ssl.c"), 1)
        self.assertEqual(result.count("_hashlib _hashopenssl.c"), 1)

    def test_includes_objects_for_required_ssl_extensions(self):
        setup_lines = module_config.ensure_required_static_modules(
            ["*static*", "#_ssl _ssl.c", "#_hashlib _hashopenssl.c"]
        )

        objects = module_config.module_object_paths(setup_lines)

        self.assertIn("Modules/_hashopenssl.o", objects)
        self.assertIn("Modules/_ssl.o", objects)

    def test_includes_objects_for_required_runtime_extensions(self):
        setup_lines = module_config.ensure_required_static_modules(
            ["*static*", "#_posixsubprocess _posixsubprocess.c", "#_blake2"]
        )

        objects = module_config.module_object_paths(setup_lines)

        self.assertIn("Modules/_posixsubprocess.o", objects)
        self.assertIn("Modules/_blake2/blake2module.o", objects)
        self.assertIn("Modules/_blake2/blake2b_impl.o", objects)
        self.assertIn("Modules/_blake2/blake2s_impl.o", objects)


    def test_fails_build_validation_if_ssl_initializer_is_missing(self):
        with self.assertRaisesRegex(RuntimeError, "_ssl"):
            registry.require_native_modules(["_hashlib", "_blake2", "_posixsubprocess", "zlib"])

    def test_accepts_required_tls_initializers(self):
        registry.require_native_modules(list(registry.REQUIRED_NATIVE_MODULES))

    def test_rejects_missing_runtime_critical_initializers(self):
        with self.assertRaisesRegex(RuntimeError, "_socket"):
            registry.require_native_modules(
                [name for name in registry.REQUIRED_NATIVE_MODULES if name != "_socket"]
            )

    def test_runtime_reuses_initialized_python_for_subsequent_commands(self):
        source = RUNTIME_SOURCE_PATH.read_text(encoding="utf-8")
        guard = source.index("if (Py_IsInitialized())")
        gil_acquire = source.index("PyGILState_Ensure()", guard)
        registration = source.index("hermes_register_native_modules();")

        self.assertIn("pthread_mutex_lock(&runtime_entry_lock);", source)
        self.assertIn("PyGILState_Release(gil_state);", source)
        self.assertLess(guard, registration)
        self.assertLess(guard, gil_acquire)
        self.assertIn("PyEval_SaveThread();", source)
        self.assertNotIn("Py_FinalizeEx", source)

    def test_linux_runtime_build_is_static_and_pins_ashell_cpython(self):
        build_script = (
            Path(__file__).resolve().parents[1] / "build" / "build-native-linux.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("CPYTHON_REF=${CPYTHON_REF:-0c3aa6418f2f8d874e1be62e45226af002bbcc8d}", build_script)
        self.assertIn("--disable-shared", build_script)
        self.assertIn("  -static -lssl -lcrypto", build_script)

    def test_ios_terminal_environment_is_not_enabled_for_linux_runtime(self):
        source = RUNTIME_SOURCE_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "#ifdef __APPLE__\n    setenv(\"HERMES_IOS_TERMINAL\", \"1\", 1);\n#endif",
            source,
        )

    def test_linux_build_supplies_mach_boolean_compatibility_header(self):
        build_script = (
            Path(__file__).resolve().parents[1] / "build" / "build-native-linux.sh"
        ).read_text(encoding="utf-8")
        shim = (
            Path(__file__).resolve().parents[1]
            / "overlay"
            / "cpython"
            / "linux-shims"
            / "mach"
            / "boolean.h"
        ).read_text(encoding="utf-8")

        self.assertIn("linux-shims", build_script)
        self.assertIn("typedef int boolean_t;", shim)


if __name__ == "__main__":
    unittest.main()
