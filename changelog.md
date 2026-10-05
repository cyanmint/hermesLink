# Changelog

## v18.8.0.522

### Added
- Integrate iSH, providing an Alpine Linux guest with a real Linux kernel and userland for Linux-specific tools and packages.
- Add persistent iSH rootfs profiles and profile management in Settings and through `ishfs`.
- Add the `ish` command for running guest commands, and manage guest command sessions with clearer startup errors and output handling.
- Add an optional host-backed Documents mount for sharing files with the iSH guest, plus app-managed guest DNS configuration.

### Improved
- Keep iSH guest files and rootfs data intact when paths or profiles are migrated; validate rootfs state and guard against stale metadata.
- Build and package pinned iSH/Alpine runtime inputs as part of the iOS app pipeline, with simulator coverage and improved build-stage isolation.
- Improve iSH kernel startup and filesystem stability, including PTY readiness, transient device retries, and safe handling of filesystem paths.

[Full changelog](https://github.com/cyanmint/hermesLink/compare/v18.7.0.1098...v18.8.0.522)

## v18.7.0.1098

### Added
- Run foreground local shell commands through iOS `ios_system`, including piped input and asynchronous, cancellable execution.
- Hot-swap the embedded Hermes runtime ZIP at app launch and expose runtime files in the Files app under the shared Documents directory.
- Add simulator end-to-end coverage for the uploaded iOS build.

### Fixed
- Bundle SSL and subprocess support in the embedded Python runtime, and fix ZIP imports required by the OpenAI SDK.
- Improve runtime upgrades, native module registration, visible workspace handling, and error reporting for unsupported local terminal commands.
- Emit output-item events for legacy Responses API streams.

[Full changelog](https://github.com/cyanmint/hermesLink/compare/v18.7.0.1097...v18.7.0.1098)

## v18.7.0.1097

This release carries HermesLink changes from the Blink Shell raw-branch baseline at [`a90b442`](https://github.com/cyanmint/hermesLink/commit/a90b442).

### Added
- Rebrand the app as HermesLink and embed the Hermes Agent runtime in the iOS app.
- Launch and reuse Hermes WebUI from the terminal, including gesture controls and configurable automatic startup, listen host, and port.
- Add the `hermes` command and embedded Python support, routing runtime and command output to the terminal.
- Add app diagnostics controls, terminal Settings gestures, and Hermes-aware workspace and state locations in Documents.
- Support IPA and TrollStore TIPA packaging, with CI publishing the app and its Hermes runtime.

### Fixed
- Restore Blink terminal gestures, layout, keyboard controls, and terminal input switching while integrating Hermes.
- Improve runtime framework linking, Python module registration, app launchability, package layout, and TrollStore signing.

[Full changelog](https://github.com/cyanmint/hermesLink/compare/a90b442...v18.7.0.1097)
