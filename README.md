# HermesLink

HermesLink combines the upstream Blink iOS terminal with the Hermes Agent
runtime and an optional native iSH Linux environment. This repository contains
HermesLink integration code, build tooling, and app customization—not Blink's
application source or its framework dependencies.

## Source model

- `hermes/blink/UPSTREAM_REVISION` pins the Blink source revision.
- `hermes/blink/overlay/` contains HermesLink-specific app glue and resources.
- `hermes/blink/patches/` contains small, source-anchored Python scripts for
  modifying existing Blink files. They stop with an error when the expected
  source context is missing or ambiguous.
- `hermes/` and `ISHBridge/` contain the Hermes and iSH build/runtime
  integration.

The CI workflow checks out the pinned Blink revision and its submodules,
applies the overlay and Python scripts, then builds the app. The upstream
`Frameworks` tree, project files, and Blink attribution files are not stored in
this repository. See [BUILD.md](BUILD.md) for local source preparation and build
instructions.

## Hermes data

Hermes state and its default workspace use the app's Files-visible `Documents`
directory. `HERMES_HOME` is `Documents/HermesHome`; the default workspace is
`Documents`. Hermes Agent and WebUI assets are extracted under
`Documents/HermesHome`. The app keeps an independently upgraded runtime
archive unless a newer bundled archive is installed.

## iSH

The iSH bridge runs commands in a persistent Alpine guest, stores profiles
under `Documents/iSH/`, and exposes profile management through the app and the
Hermes Agent tool interface. [BUILD.md](BUILD.md) describes the runtime build
and profile layout.

## Licensing and attribution

HermesLink integration code is distributed under GPL-3.0; the complete license
text is in [`LICENSES/GPL-3.0.txt`](LICENSES/GPL-3.0.txt). Blink and other
third-party components retain their own licenses, copyright notices, and
attribution. The pinned Blink checkout supplies Blink's original attribution
and license files during a build.
