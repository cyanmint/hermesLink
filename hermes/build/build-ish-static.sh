#!/usr/bin/env bash
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
#
# Builds the pinned upstream iSH Linux-kernel-as-library target
# (hermes/build/external/ish/source, fetched/verified by
# hermes/build/fetch-ish-source.sh) into static libraries HermesLink's
# Blink Xcode target links against (ISHBridge/*). This wraps the pinned
# source's OWN Meson/Ninja + Xcode build-phase scripts
# (app/xcode-meson.sh, app/xcode-ninja.sh) rather than re-implementing
# iSH's kernel build, so we stay byte-for-byte on upstream's own build
# logic for the actual Linux kernel compile.
#
# Requirements (genuinely unavailable in this repository's Linux
# dev/CI sandbox; see BUILD.md): Xcode command line tools (clang
# targeting arm64-apple-ios, `xcrun`), Meson, and Ninja. This script
# preflight-checks for all three and fails with a clear, actionable
# message instead of attempting a partial/likely-broken build when any
# are missing — it does not attempt the Linux-hosted clang
# cross-compile fallback that hermes/build/build-native-ios.sh uses for
# CPython, because iSH's kernel build (deps/linux via Meson custom
# targets) is far more tightly coupled to Xcode's own build environment
# variables than a plain CPython ./configure cross-build is.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ISH_SOURCE=${ISH_SOURCE:-$ROOT/build/external/ish/source}
BUILD_ROOT=${BUILD_ROOT:-$ROOT/build/ish-native}
MESON_BUILD_DIR=${MESON_BUILD_DIR:-$BUILD_ROOT/meson}
OUTPUT_DIR=${OUTPUT_DIR:-$ROOT/build/external/ish/lib}
ARCHS=${ARCHS:-arm64}
CONFIGURATION=${CONFIGURATION:-Release}
IPHONEOS_DEPLOYMENT_TARGET=${IPHONEOS_DEPLOYMENT_TARGET:-16.1}
ISH_LOG=${ISH_LOG:-}
ISH_LOGGER=${ISH_LOGGER:-nslog}

fail() {
  echo "build-ish-static.sh: $*" >&2
  exit 2
}

[ -d "$ISH_SOURCE" ] || fail "pinned iSH source not found at $ISH_SOURCE; run hermes/build/fetch-ish-source.sh first"
python3 "$ROOT/build/verify-ish-source.py" --source "$ISH_SOURCE" || fail "pinned iSH source failed integrity verification"

[ "$(uname -s)" = Darwin ] || fail "requires macOS + Xcode command line tools (arm64-apple-ios clang); this sandbox is $(uname -s), not Darwin"
command -v xcrun >/dev/null 2>&1 || fail "requires Xcode command line tools: 'xcrun' not found"
xcrun --sdk iphoneos --find clang >/dev/null 2>&1 || fail "requires an installed iphoneos SDK (xcrun --sdk iphoneos --find clang failed)"
command -v meson >/dev/null 2>&1 || fail "requires Meson (https://mesonbuild.com); 'meson' not found on PATH"
command -v ninja >/dev/null 2>&1 || fail "requires Ninja; 'ninja' not found on PATH"

mkdir -p "$MESON_BUILD_DIR" "$OUTPUT_DIR"

# app/xcode-meson.sh / app/xcode-ninja.sh are upstream's own Xcode
# "Run Build Tool" build-phase scripts (see iSH.xcodeproj/project.pbxproj's
# libiSHLinux / libiSHLinuxUser targets); they read these exact environment
# variable names because that is what Xcode itself sets for a Run Script /
# Run Build Tool phase. Driving them directly here keeps this script and an
# actual Xcode build doing the same thing.
export SRCROOT="$ISH_SOURCE"
export MESON_BUILD_DIR
export ARCHS
export CONFIGURATION
export ISH_LOG
export ISH_LOGGER
export ISH_KERNEL=linux

echo "build-ish-static.sh: configuring (meson) ..."
bash "$ISH_SOURCE/app/xcode-meson.sh"

echo "build-ish-static.sh: building (ninja) ..."
(cd "$MESON_BUILD_DIR" && bash "$ISH_SOURCE/app/xcode-ninja.sh")

# Discover whatever static libraries Meson/Ninja actually produced for the
# 'linux' kernel option, rather than assuming one exact name: the pinned
# meson.build's own `static_library('linux_modules', ...)` /
# `static_library('linux_user', ...)` declarations (as of the pinned
# commit) would normally produce liblinux_modules.a / liblinux_user.a, but
# Xcode's own build phases reference libiSHLinux.a / libiSHLinuxUser.a
# (likely via a per-target PRODUCT_NAME override this script cannot see
# without actually running inside Xcode) — so this copies every top-level
# .a Meson produced and lets the caller's link step (and
# install_ish_runtime.sh) match by content rather than a guessed name.
found_any=0
while IFS= read -r archive; do
  found_any=1
  cp "$archive" "$OUTPUT_DIR/"
  echo "build-ish-static.sh: collected $(basename "$archive")"
done < <(find "$MESON_BUILD_DIR" -maxdepth 2 -name '*.a' -type f)

[ "$found_any" = 1 ] || fail "ninja did not produce any static libraries under $MESON_BUILD_DIR"

cp "$ISH_SOURCE/app/LinuxInterop.h" "$OUTPUT_DIR/LinuxInterop.h"

echo "build-ish-static.sh: wrote static libraries and LinuxInterop.h to $OUTPUT_DIR"
