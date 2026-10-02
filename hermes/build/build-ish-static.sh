#!/usr/bin/env bash
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
#
# Builds the pinned upstream iSH kernel. Linux cross-compiles the Meson/Ninja
# archives; macOS builds the Xcode host-interop libraries and assembles them.
#
# Linux Meson builds require Clang/LLD, Meson/Ninja, and the Theos iOS SDK.
# The Xcode host-interop stage requires macOS, Xcode, and Homebrew LLVM/LLD.
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
BUILD_MODE=${1:-all}

fail() {
  echo "build-ish-static.sh: $*" >&2
  exit 2
}

case "$BUILD_MODE" in
  all|--meson-only|--xcode-only) ;;
  *) fail "unknown build mode: $BUILD_MODE" ;;
esac

[ -d "$ISH_SOURCE" ] || fail "pinned iSH source not found at $ISH_SOURCE; run hermes/build/fetch-ish-source.sh first"
python3 "$ROOT/build/verify-ish-source.py" --source "$ISH_SOURCE" || fail "pinned iSH source failed integrity verification"

command -v meson >/dev/null 2>&1 || fail "requires Meson (https://mesonbuild.com); 'meson' not found on PATH"
command -v ninja >/dev/null 2>&1 || fail "requires Ninja; 'ninja' not found on PATH"
TOOLCHAIN_BIN="$BUILD_ROOT/ios-toolchain"
mkdir -p "$TOOLCHAIN_BIN"
HOST_OS=$(uname -s)
if [ "$BUILD_MODE" = "--xcode-only" ] && [ "$HOST_OS" != Darwin ]; then
  [ -x "$TOOLCHAIN_BIN/clang" ] && [ -x "$TOOLCHAIN_BIN/xcrun" ] || fail "missing Linux Meson toolchain artifact"
elif [ "$HOST_OS" = Darwin ]; then
  command -v xcrun >/dev/null 2>&1 || fail "requires Xcode command line tools: 'xcrun' not found"
  if [ "$BUILD_MODE" != "--meson-only" ]; then
    command -v xcodebuild >/dev/null 2>&1 || fail "requires Xcode command line tools: 'xcodebuild' not found"
  fi
  xcrun --sdk iphoneos --find clang >/dev/null 2>&1 || fail "requires an installed iphoneos SDK (xcrun --sdk iphoneos --find clang failed)"
  command -v brew >/dev/null 2>&1 || fail "requires Homebrew to locate LLVM/LLD"
  LLVM_BIN="$(brew --prefix llvm)/bin"
  LLD_BIN="$(brew --prefix lld)/bin"
  [ -x "$LLVM_BIN/clang" ] && [ -x "$LLD_BIN/ld.lld" ] || fail "requires Homebrew LLVM and LLD (brew install llvm lld)"
  SDKROOT=${SDKROOT:-$(xcrun --sdk iphoneos --show-sdk-path)}
  HOST_CLANG="$LLVM_BIN/clang"
  export PATH="$LLVM_BIN:$LLD_BIN:$PATH"
elif [ "$HOST_OS" = Linux ]; then
  [ "$BUILD_MODE" = "--meson-only" ] || fail "the iSH Xcode targets require macOS; use --meson-only for the Linux cross-build stage"
  command -v clang >/dev/null 2>&1 || fail "requires Clang (install clang)"
  command -v llvm-ar >/dev/null 2>&1 || fail "requires LLVM archiver (install llvm)"
  command -v llvm-ranlib >/dev/null 2>&1 || fail "requires LLVM ranlib (install llvm)"
  command -v llvm-nm >/dev/null 2>&1 || fail "requires LLVM nm (install llvm)"
  command -v ld.lld >/dev/null 2>&1 || fail "requires LLD (install lld)"
  HOST_CLANG=$(command -v clang)
  LLVM_BIN=$(dirname "$HOST_CLANG")
  LLD_BIN=$(dirname "$(command -v ld.lld)")
  SDK_VERSION=${IOS_SDK_VERSION:-16.5}
  SDK_REPO=${IOS_SDK_REPOSITORY:-https://github.com/theos/sdks.git}
  SDK_REPO_DIR="$BUILD_ROOT/sdks"
  SDKROOT=${IOS_SDK_ROOT:-$SDK_REPO_DIR/iPhoneOS${SDK_VERSION}.sdk}
  if [ ! -d "$SDKROOT/usr/include" ]; then
    if [ ! -d "$SDK_REPO_DIR/.git" ]; then
      git clone --filter=blob:none --sparse --depth=1 "$SDK_REPO" "$SDK_REPO_DIR"
    fi
    git -C "$SDK_REPO_DIR" sparse-checkout set "iPhoneOS${SDK_VERSION}.sdk"
  fi
  [ -d "$SDKROOT/usr/include" ] || fail "missing iOS SDK at $SDKROOT"
  export PATH="$LLVM_BIN:$LLD_BIN:$PATH"
else
  fail "unsupported build host: $HOST_OS"
fi
export SDKROOT

if [ "$HOST_OS" = Darwin ]; then
  cat > "$TOOLCHAIN_BIN/clang" <<EOF
#!/bin/sh
exec "$LLVM_BIN/clang" -isysroot "$SDKROOT" -miphoneos-version-min="$IPHONEOS_DEPLOYMENT_TARGET" "\$@"
EOF
else
  cat > "$TOOLCHAIN_BIN/clang" <<EOF
#!/bin/sh
for arg in "\$@"; do
  if [ "\$arg" = i386-linux ]; then exec "$HOST_CLANG" "\$@"; fi
done
exec "$HOST_CLANG" --target=arm64-apple-ios${IPHONEOS_DEPLOYMENT_TARGET} -isysroot "$SDKROOT" -miphoneos-version-min="$IPHONEOS_DEPLOYMENT_TARGET" -fuse-ld=lld "\$@"
EOF
  cat > "$TOOLCHAIN_BIN/xcrun" <<EOF
#!/bin/sh
if [ "\${1:-}" = clang ]; then
  shift
  exec "$HOST_CLANG" "\$@"
fi
echo "unsupported Linux xcrun invocation: \$*" >&2
exit 2
EOF
  cat > "$TOOLCHAIN_BIN/nm" <<EOF
#!/bin/sh
exec "$(command -v llvm-nm)" "\$@"
EOF
fi
chmod +x "$TOOLCHAIN_BIN/clang"
if [ "$HOST_OS" = Linux ]; then chmod +x "$TOOLCHAIN_BIN/xcrun" "$TOOLCHAIN_BIN/nm"; fi
export PATH="$TOOLCHAIN_BIN:$PATH"

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
PRODUCTS_DIR="$BUILD_ROOT/xcode/Build/Products/$CONFIGURATION-iphoneos"
MESON_ARCHIVES=(deps/liblinux.a libfakefs.a libish_emu.a)
MESON_NINJA_TARGETS="${MESON_ARCHIVES[*]}"
if [ "$BUILD_MODE" = "--xcode-only" ]; then
  export NINJA_TARGETS="$MESON_NINJA_TARGETS"
fi

if [ "$BUILD_MODE" != "--xcode-only" ]; then
  echo "build-ish-static.sh: configuring (meson) ..."
  bash "$ISH_SOURCE/app/xcode-meson.sh"

  echo "build-ish-static.sh: building Meson archives ..."
  (cd "$MESON_BUILD_DIR" && bash "$ISH_SOURCE/app/xcode-ninja.sh" "${MESON_ARCHIVES[@]}")
  if [ "$HOST_OS" = Linux ]; then
    for archive in "${MESON_ARCHIVES[@]}"; do
      llvm-ranlib "$MESON_BUILD_DIR/$archive"
    done
  fi
fi

if [ "$BUILD_MODE" = "--meson-only" ]; then
  for archive in "${MESON_ARCHIVES[@]}"; do
    archive="$MESON_BUILD_DIR/$archive"
    [ -s "$archive" ] || fail "required Meson iSH archive was not produced: $archive"
  done
  echo "build-ish-static.sh: Linux Meson stage produced the kernel, fakefs, and emulator archives"
  exit 0
fi

[ "$HOST_OS" = Darwin ] || fail "Xcode static-library targets require macOS"
[ -f "$MESON_BUILD_DIR/build.ninja" ] || fail "Meson build directory is missing: $MESON_BUILD_DIR"

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
    ARCHS="$ARCHS" \
    ONLY_ACTIVE_ARCH=YES \
    CODE_SIGNING_ALLOWED=NO \
    CONFIGURATION_BUILD_DIR="$PRODUCTS_DIR" \
    NINJA_TARGETS="$NINJA_TARGETS" \
    MESON_BUILD_DIR="$MESON_BUILD_DIR" \
    ISH_KERNEL=linux
done

for archive in \
  "$PRODUCTS_DIR/libiSHLinux.a" \
  "$PRODUCTS_DIR/libiSHLinuxUser.a" \
  "$MESON_BUILD_DIR/deps/liblinux.a" \
  "$MESON_BUILD_DIR/libfakefs.a" \
  "$MESON_BUILD_DIR/libish_emu.a"; do
  [ -s "$archive" ] || fail "required upstream iSH archive was not produced: $archive"
done

rm -f "$OUTPUT_DIR"/*.a "$OUTPUT_DIR/LinuxInterop.h"
for archive in \
  "$PRODUCTS_DIR/libiSHLinux.a" \
  "$PRODUCTS_DIR/libiSHLinuxUser.a" \
  "$MESON_BUILD_DIR/deps/liblinux.a" \
  "$MESON_BUILD_DIR/libfakefs.a" \
  "$MESON_BUILD_DIR/libish_emu.a"; do
  cp "$archive" "$OUTPUT_DIR/"
  echo "build-ish-static.sh: collected $(basename "$archive")"
done

cp "$ISH_SOURCE/app/LinuxInterop.h" "$OUTPUT_DIR/LinuxInterop.h"

echo "build-ish-static.sh: wrote static libraries and LinuxInterop.h to $OUTPUT_DIR"
