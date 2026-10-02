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
# Requirements: Xcode command line tools (clang targeting arm64-apple-ios,
# `xcrun`, `xcodebuild`), Homebrew LLVM/LLD, Meson, and Ninja. This script
# preflight-checks for them and fails with a clear, actionable message
# instead of attempting a partial/likely-broken build when any are missing —
# it does not attempt the Linux-hosted clang
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
command -v xcodebuild >/dev/null 2>&1 || fail "requires Xcode command line tools: 'xcodebuild' not found"
xcrun --sdk iphoneos --find clang >/dev/null 2>&1 || fail "requires an installed iphoneos SDK (xcrun --sdk iphoneos --find clang failed)"
command -v meson >/dev/null 2>&1 || fail "requires Meson (https://mesonbuild.com); 'meson' not found on PATH"
command -v ninja >/dev/null 2>&1 || fail "requires Ninja; 'ninja' not found on PATH"
command -v brew >/dev/null 2>&1 || fail "requires Homebrew to locate LLVM/LLD"
LLVM_BIN="$(brew --prefix llvm)/bin"
LLD_BIN="$(brew --prefix lld)/bin"
[ -x "$LLVM_BIN/clang" ] && [ -x "$LLD_BIN/ld.lld" ] || fail "requires Homebrew LLVM and LLD (brew install llvm lld)"
export PATH="$LLVM_BIN:$LLD_BIN:$PATH"

SDKROOT=$(xcrun --sdk iphoneos --show-sdk-path)
export SDKROOT

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
export CFLAGS="${CFLAGS:+$CFLAGS }-isysroot $SDKROOT -miphoneos-version-min=$IPHONEOS_DEPLOYMENT_TARGET"
bash "$ISH_SOURCE/app/xcode-meson.sh"

echo "build-ish-static.sh: building (ninja) ..."
(cd "$MESON_BUILD_DIR" && bash "$ISH_SOURCE/app/xcode-ninja.sh")

# Build upstream's iOS host interop targets as well as its Meson kernel
# archive. The host library contains LinuxInterop.c and the PTY/rootfs glue
# referenced by ish_kernel_bridge.m; Meson alone does not produce it.
for target in libiSHLinux libiSHLinuxUser; do
  echo "build-ish-static.sh: building upstream Xcode target $target ..."
  xcodebuild \
    -project "$ISH_SOURCE/iSH.xcodeproj" \
    -target "$target" \
    -configuration "$CONFIGURATION" \
    -sdk iphoneos \
    -derivedDataPath "$BUILD_ROOT/xcode" \
    ARCHS="$ARCHS" \
    ONLY_ACTIVE_ARCH=YES \
    CODE_SIGNING_ALLOWED=NO \
    MESON_BUILD_DIR="$MESON_BUILD_DIR" \
    ISH_KERNEL=linux
done

PRODUCTS_DIR="$BUILD_ROOT/xcode/Build/Products/$CONFIGURATION-iphoneos"
for archive in \
  "$PRODUCTS_DIR/libiSHLinux.a" \
  "$PRODUCTS_DIR/libiSHLinuxUser.a" \
  "$MESON_BUILD_DIR/deps/liblinux.a"; do
  [ -s "$archive" ] || fail "required upstream iSH archive was not produced: $archive"
  cp "$archive" "$OUTPUT_DIR/"
  echo "build-ish-static.sh: collected $(basename "$archive")"
done

cp "$ISH_SOURCE/app/LinuxInterop.h" "$OUTPUT_DIR/LinuxInterop.h"

echo "build-ish-static.sh: wrote static libraries and LinuxInterop.h to $OUTPUT_DIR"
