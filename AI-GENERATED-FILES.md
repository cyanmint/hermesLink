# AI-generated HermesLink glue files

The following files are HermesLink glue code created by cyanmint's coding agent. A coding agent was used to create the complete contents of these files; they are not copied from Blink or from the upstream Hermes projects.

This inventory intentionally excludes `AI-GENERATED-FILES.md` itself; it is attribution documentation, not a glue file.
Blink app glue and resources are carried under `blink/overlay/`; changes to existing upstream files use small per-file Python patch scripts under `blink/patches/`. They are materialized only in the build workspace.

Under the project's stated attribution policy, AI-generated content has no copyright holder and is not subject to copyright. These files are therefore provided as non-copyrightable glue code. This statement does not remove or alter the licenses and copyright notices of Blink, Hermes Agent, Hermes WebUI, CPython, or any other third-party material incorporated by the build.

## Files

- `.github/workflows/build.yml`
- `ishbridge/ISHRootfsProfiles.h`
- `ishbridge/ISHRootfsProfiles.m`
- `ishbridge/ish_exit_protocol.c`
- `ishbridge/ish_exit_protocol.h`
- `ishbridge/ish_kernel_bridge.h`
- `ishbridge/ish_kernel_bridge.m`
- `ishbridge/ish_kernel_bridge_stub.m`
- `ishbridge/ish_path_safety.c`
- `ishbridge/ish_path_safety.h`
- `ishbridge/ish_rootfs.c`
- `ishbridge/ish_rootfs.h`
- `blink/overlay/Blink/Commands/hermes.m`
- `blink/overlay/Blink/Commands/ish.m`
- `blink/overlay/Blink/Commands/ishfs.m`
- `blink/overlay/Settings/ISHRootfsSettingsView.swift`
- `blink/apply-patches.py`
- `blink/patches/_patch_utils.py`
- `blink/patches/patch-blink-appdelegate-m.py`
- `blink/patches/patch-blink-blink-bridge-h.py`
- `blink/patches/patch-blink-commands-help-m.py`
- `blink/patches/patch-blink-complete-swift.py`
- `blink/patches/patch-blink-info-plist.py`
- `blink/patches/patch-blink-migrator-1860migration-swift.py`
- `blink/patches/patch-blink-migrator-migrator-swift.py`
- `blink/patches/patch-blink-scenedelegate-swift.py`
- `blink/patches/patch-blink-smarterkeys-smarterterminput-swift.py`
- `blink/patches/patch-blink-spacecontroller-swift.py`
- `blink/patches/patch-blink-terminal-termcontroller-swift.py`
- `blink/patches/patch-blink-terminal-termview-h.py`
- `blink/patches/patch-blink-terminal-termview-m.py`
- `blink/patches/patch-blink-whatsnew-whatsnewinfo-swift.py`
- `blink/patches/patch-blink-xcodeproj-project-pbxproj-01.py`
- `blink/patches/patch-blink-xcodeproj-project-pbxproj-02.py`
- `blink/patches/patch-blink-xcodeproj-project-pbxproj-03.py`
- `blink/patches/patch-blink-xcodeproj-project-pbxproj-04.py`
- `blink/patches/patch-blink-xcodeproj-project-pbxproj-05.py`
- `blink/patches/patch-blink-xcodeproj-project-pbxproj-06.py`
- `blink/patches/patch-blink-xcodeproj-project-pbxproj-07.py`
- `blink/patches/patch-blink-xcodeproj-project-pbxproj-08.py`
- `blink/patches/patch-blink-xcodeproj-project-pbxproj-09.py`
- `blink/patches/patch-blink-xcodeproj-project-pbxproj-10.py`
- `blink/patches/patch-blinkconfig-blinkpaths-h.py`
- `blink/patches/patch-blinkconfig-blinkpaths-m.py`
- `blink/patches/patch-sessions-mcpsession-m.py`
- `blink/patches/patch-sessions-sessionparams-swift.py`
- `blink/patches/patch-settings-model-terminalstyle-swift.py`
- `blink/patches/patch-settings-settingsview-swift.py`
- `blink/patches/patch-settings-viewcontrollers-about-about-html.py`
- `blink/patches/patch-settings-viewcontrollers-appearance-stylecustomizationview-swift.py`
- `ishbridge/ISHNative.xcconfig`
- `scripts/hermes/build/build-hermesrt-zip.sh`
- `scripts/hermes/build/build-ish-static.sh`
- `scripts/hermes/build/build-native-ios.sh`
- `scripts/hermes/build/ish-documents-fs.c`
- `scripts/hermes/build/patch-ish-pty.py`
- `scripts/hermes/build/patch-ish-documents-fs.py`
- `scripts/hermes/build/configure_native_modules.py`
- `scripts/hermes/build/fetch-sources.sh`
- `scripts/hermes/build/fetch-ish-source.sh`
- `scripts/hermes/build/verify-ish-source.py`
- `scripts/hermes/build/generate-native-module-registry.py`
- `scripts/hermes/build/package-native-ios.sh`
- `scripts/hermes/build/package-ish-framework.sh`
- `scripts/blink/prepare-blink-source.sh`
- `scripts/hermes/build/prepare-ish-xcode-project.py`
- `scripts/hermes/build/repack-ish-meson-archives.py`
- `scripts/hermes/build/validate-runtime-zip.py`
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
- `tests/hermes/ci_simulator_copilot_e2e.py`
- `tests/hermes/test_blink_source_patch.py`
- `tests/hermes/ish_bridge/ish_bridge_test_main.c`
- `tests/hermes/test_ci_simulator_copilot_e2e.py`
- `tests/hermes/test_cpython_ios_system_patch.py`
- `tests/hermes/test_ios_shell_registration.py`
- `tests/hermes/test_ios_terminal_patch.py`
- `tests/hermes/test_ish_bridge_c.py`
- `tests/hermes/test_ish_ci_workflow.py`
- `tests/hermes/test_ish_ai_generated_files_inventory.py`
- `tests/hermes/test_ish_native_build_scripts.py`
- `tests/hermes/test_ish_source.py`
- `tests/hermes/test_ish_tool_registration.py`
- `tests/hermes/test_ish_xcode_project_wiring.py`
- `tests/hermes/test_legacy_responses.py`
- `tests/hermes/test_native_module_registry.py`
- `tests/hermes/test_upgrade_runtime.py`
- `tests/hermes/test_user_visible_paths.py`
- `tests/hermes/test_validate_runtime_zip.py`
- `scripts/install_hermes_runtime.sh`
- `scripts/install_ish_runtime.sh`

## Project license

HermesLink as a whole is distributed under the GNU General Public License, version 3 (GPLv3), subject to the rights and obligations of the third-party components whose notices and licenses remain applicable. The full GPLv3 text is in [`COPYING`](COPYING).

## Bundled Hermes components

- **Hermes Agent** — MIT License, Copyright © 2025 Nous Research.
- **Hermes WebUI** — MIT License, Copyright © 2025 Hermes Web UI Contributors.
- **Blink** — GPLv3 with Blink's additional terms under GPLv3 section 7; Blink is a dependency of HermesLink, not the project name.
