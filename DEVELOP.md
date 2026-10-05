# Developing HermesLink

This repository contains component-specific integration code, not the upstream
Blink, Hermes Agent, Hermes WebUI, CPython, or iSH source trees. Keep project
customizations in the component directory that owns them:

- `blink/overlay/` holds new Blink-side files and resources.
- `blink/patches/` holds small, per-file Python patch scripts for upstream
  Blink files. `blink/UPSTREAM_REVISION` pins the tested base.
- `ishbridge/` holds the iSH-to-iOS bridge and its Xcode configuration.
- `hermes/overlay/` holds Hermes and CPython overlays and patch scripts.
- `scripts/` holds source preparation, build, and packaging scripts.
- `tests/` holds repository tests. Keep documentation at the repository root.

Do not commit downloaded upstream source, submodules, frameworks, or compiler
outputs. `.gitignore` excludes the materialized Blink checkout and generated
build products.

## Branch and history

The `default` branch contains HermesLink glue and integration code, the iOS
bridge, and customization patches; it does not contain the original Blink
source tree. The original commit history through `v18.8.0.522` (inclusive) is
no longer part of the `default` branch's ancestry. To inspect that earlier
history, see the [commit timeline for tag `v18.8.0.522`](https://github.com/cyanmint/hermesLink/commits/v18.8.0.522/).
Development after `v18.8.0.522` continues on `default`.

## Preparing Blink

The Blink preparation script verifies the pinned revision, applies the overlay
and every Python patch script, and stages the result in the repository root for
Xcode. The iSH bridge is staged under Blink's expected `ISHBridge/` project
path; its maintained source remains in this repository's lowercase
`ishbridge/`.

On macOS with Git, Xcode, and the upstream Blink dependencies installed:

```sh
git clone https://github.com/blinksh/blink.git .blink-upstream
git -C .blink-upstream checkout "$(tr -d '\r\n' < blink/UPSTREAM_REVISION)"
git -C .blink-upstream submodule update --init --recursive
bash scripts/blink/prepare-blink-source.sh .blink-upstream "$PWD"
bash get_frameworks.sh
bash get_resources.sh
cp template_setup.xcconfig developer_setup.xcconfig
```

Open the generated `Blink.xcodeproj`, then build the `Blink` scheme. The
generated checkout and staged Blink files are build inputs only; do not commit
them.

## Build and test

The GitHub Actions workflow is the canonical complete build. It decides which
components need rebuilding, prepares the shared release, then builds these
branches in parallel:

1. `hermesrt.zip`, the pure-Python runtime.
2. `HermesRuntime.framework`, the native CPython runtime.
3. Blink app without runtime frameworks.
4. iSH Linux cross-compile followed by the macOS host-interop framework.

IPA assembly waits for all requested branches to succeed or be skipped.
Simulator and Copilot E2E tests are optional workflow inputs and run after IPA
assembly. The workflow's `workflow_dispatch` inputs can request individual
component rebuilds; leave `run_tests` disabled unless simulator testing is
needed and its required credentials are available.

Run the host-side tests from the repository root:

```sh
python3 -m unittest discover -s tests/hermes -v
```

The C bridge harness requires a host C compiler and zlib/SQLite development
headers. Tests that need fetched third-party build sources or a materialized
Blink tree are skipped when those inputs are absent.

## Runtime build inputs

Hermes source pins and CPython configuration are in
`scripts/hermes/build/fetch-sources.sh` and the build scripts. To fetch the
pinned iSH checkout and root filesystem:

```sh
bash scripts/hermes/build/fetch-ish-source.sh
```

This writes build-time inputs under `hermes/build/external/ish`. The
`build-ish-static.sh --meson-only` stage cross-compiles iSH's Linux archives;
the macOS `--xcode-only` stage consumes that output to build the host interop
libraries. `package-ish-framework.sh` links those archives with `ishbridge/`.
Do not edit fetched trees as maintained source: the build scripts apply
temporary patches and restore the pinned inputs.

The native CPython build links the ios_system compatibility framework as
required by the iOS shim. Resolve Blink's xcfs/framework dependencies before
building or packaging the native Hermes framework.

## Developing patch scripts

Prefer an overlay for a new upstream-owned file, and a focused Python patch
script for a modification to an existing file. Keep each patch specific to one
upstream target, validate its expected source context, fail rather than silently
skipping when context is absent or ambiguous, and make it safe to run more than
once. Avoid monolithic patch files.

Test Blink changes against a clean checkout at `blink/UPSTREAM_REVISION`:

```sh
python3 blink/apply-patches.py .blink-upstream
```

Then run the preparation script to verify staging and build inputs. Update
`tests/` when behavior or patch expectations change, and update this document
when the source/build workflow changes.
