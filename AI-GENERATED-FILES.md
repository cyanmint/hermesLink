# AI-generated HermesLink glue files

The following files are HermesLink glue code created by cyanmint's coding agent. A coding agent was used to create the complete contents of these files; they are not copied from Blink or from the upstream Hermes projects.

This inventory intentionally excludes `AI-GENERATED-FILES.md` itself; it is attribution documentation, not a glue file.

Under the project's stated attribution policy, AI-generated content has no copyright holder and is not subject to copyright. These files are therefore provided as non-copyrightable glue code. This statement does not remove or alter the licenses and copyright notices of Blink, Hermes Agent, Hermes WebUI, CPython, or any other third-party material incorporated by the build.

## Files

- `.github/workflows/build.yml`
- `Blink/Commands/hermes.m`
- `Blink/Commands/ish.m`
- `ISHBridge/ish_exit_protocol.c`
- `ISHBridge/ish_exit_protocol.h`
- `ISHBridge/ish_kernel_bridge.h`
- `ISHBridge/ish_kernel_bridge.m`
- `ISHBridge/ish_kernel_bridge_stub.m`
- `ISHBridge/ish_path_safety.c`
- `ISHBridge/ish_path_safety.h`
- `ISHBridge/ish_rootfs.c`
- `ISHBridge/ish_rootfs.h`
- `hermes/build/ISHNative.xcconfig`
- `hermes/build/build-hermesrt-zip.sh`
- `hermes/build/build-ish-static.sh`
- `hermes/build/build-native-ios.sh`
- `hermes/build/configure_native_modules.py`
- `hermes/build/fetch-sources.sh`
- `hermes/build/fetch-ish-source.sh`
- `hermes/build/verify-ish-source.py`
- `hermes/build/generate-native-module-registry.py`
- `hermes/build/package-native-ios.sh`
- `hermes/build/validate-runtime-zip.py`
- `hermes/overlay/cpython/Programs/hermes_main.c`
- `hermes/overlay/cpython/ios_async_system.c`
- `hermes/overlay/cpython/ios_system_bridge.h`
- `hermes/overlay/hermes/agent/legacy_responses.py`
- `hermes/overlay/hermes/hermes_cli/doctor_state.py`
- `hermes/overlay/hermes/hermes_cli/upgrade.py`
- `hermes/overlay/hermes/tools/ish_tool.py`
- `hermes/overlay/patches/patch-agent-sdk-compat.py`
- `hermes/overlay/patches/patch-cpython-ios-system.py`
- `hermes/overlay/patches/patch-ios-stability.py`
- `hermes/overlay/patches/patch-ish-tool.py`
- `hermes/overlay/patches/patch-webui-zip.py`
- `hermes/overlay/python/sitecustomize.py`
- `hermes/tests/ci_simulator_copilot_e2e.py`
- `hermes/tests/ish_bridge/ish_bridge_test_main.c`
- `hermes/tests/test_ci_simulator_copilot_e2e.py`
- `hermes/tests/test_cpython_ios_system_patch.py`
- `hermes/tests/test_ios_shell_registration.py`
- `hermes/tests/test_ios_terminal_patch.py`
- `hermes/tests/test_ish_bridge_c.py`
- `hermes/tests/test_ish_ci_workflow.py`
- `hermes/tests/test_ish_ai_generated_files_inventory.py`
- `hermes/tests/test_ish_native_build_scripts.py`
- `hermes/tests/test_ish_source.py`
- `hermes/tests/test_ish_tool_registration.py`
- `hermes/tests/test_ish_xcode_project_wiring.py`
- `hermes/tests/test_legacy_responses.py`
- `hermes/tests/test_native_module_registry.py`
- `hermes/tests/test_upgrade_runtime.py`
- `hermes/tests/test_user_visible_paths.py`
- `hermes/tests/test_validate_runtime_zip.py`
- `install_hermes_runtime.sh`
- `install_ish_runtime.sh`

## Project license

HermesLink as a whole is distributed under the GNU General Public License, version 3 (GPLv3), subject to the rights and obligations of the third-party components whose notices and licenses remain applicable. The full GPLv3 text is in [`COPYING`](COPYING).

## Bundled Hermes components

- **Hermes Agent** — MIT License, Copyright © 2025 Nous Research.
- **Hermes WebUI** — MIT License, Copyright © 2025 Hermes Web UI Contributors.
- **Blink** — GPLv3 with Blink's additional terms under GPLv3 section 7; Blink is a dependency of HermesLink, not the project name.
