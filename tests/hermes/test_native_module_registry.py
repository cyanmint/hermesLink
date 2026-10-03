import importlib.util
import unittest
from pathlib import Path

import yaml


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "hermes" / "build" / "generate-native-module-registry.py"
SPEC = importlib.util.spec_from_file_location("native_module_registry", SCRIPT_PATH)
registry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry)

CONFIG_PATH = Path(__file__).resolve().parents[2] / "scripts" / "hermes" / "build" / "configure_native_modules.py"
CONFIG_SPEC = importlib.util.spec_from_file_location("native_module_config", CONFIG_PATH)
module_config = importlib.util.module_from_spec(CONFIG_SPEC)
CONFIG_SPEC.loader.exec_module(module_config)


class NativeModuleRegistryTests(unittest.TestCase):
    def test_native_build_explicitly_compiles_required_posix_subprocess_object(self):
        build_script = (Path(__file__).resolve().parents[2] / "scripts" / "hermes" / "build" / "build-native-ios.sh")
        self.assertIn("Modules/_posixsubprocess.o", build_script.read_text(encoding="utf-8"))

    def test_native_build_compiles_and_registers_ios_async_system_module(self):
        build_root = Path(__file__).resolve().parents[2] / "scripts" / "hermes" / "build"
        build_script = (build_root / "build-native-ios.sh").read_text(encoding="utf-8")
        self.assertIn("ios_async_system.c", build_script)
        self.assertIn(("_hermesios", "_hermesiosmodule.c"), module_config.REQUIRED_STATIC_MODULES)
        self.assertIn("_hermesios", registry.REQUIRED_NATIVE_MODULES)

    def test_native_build_archives_hacl_and_expat_for_native_runtime(self):
        build_script = (
            Path(__file__).resolve().parents[2] / "scripts" / "hermes" / "build" / "build-native-ios.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("--enable-framework", build_script)
        self.assertNotIn("--disable-framework", build_script)
        self.assertIn("-o Python.framework/Python", build_script)
        self.assertIn("NATIVE_NM=llvm-nm", build_script)
        self.assertIn('--nm "$NATIVE_NM"', build_script)
        self.assertIn(
            "make -o Makefile -o Modules/config.c -o Modules/config.h -o Python.framework/Python",
            build_script,
        )
        self.assertIn(
            "make -o Makefile -o Python.framework/Python -j",
            build_script,
        )
        self.assertIn("-lsqlite3 -lz", build_script)
        self.assertIn("Modules/_hacl/Hacl_Hash_SHA2.o", build_script)
        self.assertIn('find Modules/expat -maxdepth 1 -type f -name \'*.c\'', build_script)
        self.assertIn('"$LLVM_AR" rcs Modules/expat/libexpat.a', build_script)
        self.assertNotIn("Modules/_hacl/libHacl_Hash_SHA2.a Modules/expat/libexpat.a)", build_script)

    def test_native_build_keeps_setup_objects_missing_from_make_dry_run(self):
        configured = ["Modules/_hermesiosmodule.o", "Modules/_ssl.o"]
        discovered = ["Modules/getpath.o", "Modules/_ssl.o"]

        self.assertEqual(
            module_config.merge_native_module_objects(configured, discovered),
            ["Modules/_hermesiosmodule.o", "Modules/_ssl.o", "Modules/getpath.o"],
        )

    def test_ipa_assembly_waits_for_every_requested_build_component(self):
        workflow = (
            Path(__file__).resolve().parents[2] / ".github" / "workflows" / "build.yml"
        ).read_text(encoding="utf-8")

        for job in ("build-runtime-zip", "build-native-runtime"):
            self.assertIn(
                f"needs.{job}.result == 'success' || needs.{job}.result == 'skipped'",
                workflow,
            )
        self.assertIn("needs.build-app.result == 'success'", workflow)
        self.assertIn(
            "needs.build-app.result == 'skipped' && needs.decide.outputs.run_app != 'true'",
            workflow,
        )

    def test_native_runtime_cross_compiles_on_linux_and_uses_portable_zip(self):
        workflow_path = (
            Path(__file__).resolve().parents[2] / ".github" / "workflows" / "build.yml"
        )
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        job = workflow["jobs"]["build-native-runtime"]
        self.assertEqual(job["runs-on"], "ubuntu-latest")
        steps_text = str(job["steps"])
        self.assertIn("actions/setup-python@v7", steps_text)
        self.assertIn("clang lld llvm", steps_text)
        self.assertIn("zip -qry", steps_text)
        self.assertNotIn("ditto", steps_text)

    def test_ios_async_system_module_streams_output_and_cancels_native_thread(self):
        source_path = (
            Path(__file__).resolve().parents[2] / "hermes" / "overlay" / "cpython" / "ios_async_system.c"
        )
        source = source_path.read_text(encoding="utf-8")
        self.assertIn("pipe(fds)", source)
        self.assertIn('ios_symbol("ios_setStreams")', source)
        self.assertIn('ios_symbol("ios_getThreadId")', source)
        self.assertIn("pthread_cancel(command_thread)", source)
        self.assertIn("runner_session_id", source)
        self.assertNotIn('ios_symbol("ios_closeSession")', source)
        self.assertNotIn("mkstemp", source)

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

    def test_enables_required_extensions_when_configure_disables_them(self):
        setup_lines = [
            "*static*",
            "#_ssl _ssl.c",
            "#_hashlib _hashopenssl.c",
            "#_posixsubprocess _posixsubprocess.c",
        ]

        result = module_config.ensure_required_static_modules(setup_lines)

        self.assertEqual(
            result[-4:],
            [
                "_ssl _ssl.c",
                "_hashlib _hashopenssl.c",
                "_posixsubprocess _posixsubprocess.c",
                "_hermesios _hermesiosmodule.c",
            ],
        )

    def test_does_not_duplicate_required_extensions_already_enabled(self):
        setup_lines = [
            "*static*",
            "_ssl _ssl.c",
            "_hashlib _hashopenssl.c",
            "_posixsubprocess _posixsubprocess.c",
            "_hermesios _hermesiosmodule.c",
        ]

        self.assertEqual(module_config.ensure_required_static_modules(setup_lines), setup_lines)

    def test_marks_stdlib_extensions_static_before_configure(self):
        setup_template = Path("Setup.stdlib.in")
        setup_template.write_text(
            "*@MODULE_BUILDTYPE@*\n_static_module _static.c\n*shared*\n_ssl _ssl.c\n",
            encoding="utf-8",
        )
        try:
            module_config.configure_static_module_template(setup_template)
            self.assertEqual(
                setup_template.read_text(encoding="utf-8").splitlines(),
                ["*static*", "_static_module _static.c", "*shared*", "_ssl _ssl.c"],
            )
        finally:
            setup_template.unlink()


    def test_fails_build_validation_if_posixsubprocess_initializer_is_missing(self):
        with self.assertRaisesRegex(RuntimeError, "_posixsubprocess"):
            registry.require_native_modules(["_ssl", "_hashlib"])

    def test_fails_build_validation_if_ios_async_system_initializer_is_missing(self):
        with self.assertRaisesRegex(RuntimeError, "_hermesios"):
            registry.require_native_modules(["_ssl", "_hashlib", "_posixsubprocess"])

    def test_accepts_required_native_initializers(self):
        registry.require_native_modules(["_ssl", "_hashlib", "_posixsubprocess", "_hermesios"])

    def test_ios_async_system_module_owns_async_pipe_and_cancel_api(self):
        source = (Path(__file__).resolve().parents[2] / "hermes" / "overlay" / "cpython" / "ios_async_system.c").read_text(
            encoding="utf-8"
        )
        for symbol in ("PyInit__hermesios", "pthread_create", "pthread_cancel", "ios_setStreams", "pipe(fds)"):
            self.assertIn(symbol, source)
        self.assertNotIn("ios_killpid", source)
        self.assertNotIn("mkstemp", source)

    def test_ios_async_runner_separates_pipe_stream_ownership_and_pid_startup(self):
        source = (Path(__file__).resolve().parents[2] / "hermes" / "overlay" / "cpython" / "ios_async_system.c").read_text(
            encoding="utf-8"
        )
        self.assertIn('"ios_getThreadId"', source)
        self.assertIn('"ios_releaseThreadId"', source)
        self.assertIn("ios_symbol(required_symbols[index]) == NULL", source)
        self.assertIn("int command_fd = dup(fileno(task->writer));", source)
        self.assertIn('command_writer = fdopen(command_fd, "w")', source)
        self.assertIn("set_streams(saved_stdin, command_writer, command_writer)", source)
        self.assertIn("if ((intptr_t)command_thread > 0)", source)
        self.assertIn("task->starting = 1", source)
        self.assertIn("task->ios_pid = pid", source)
        self.assertNotIn("set_streams(saved_stdin, task->writer, task->writer)", source)


if __name__ == "__main__":
    unittest.main()
