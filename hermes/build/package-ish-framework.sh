#!/usr/bin/env bash
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
LIB_DIR=${1:?directory containing the built iSH archives and section anchors}
OUTPUT_DIR=${2:?directory for the packaged Ish.framework}
FRAMEWORK="$OUTPUT_DIR/Ish.framework"
SDK_NAME=${SDK_NAME:-iphoneos}
DEPLOYMENT_TARGET=${IPHONEOS_DEPLOYMENT_TARGET:-16.1}
case "$SDK_NAME" in
  iphoneos)
    SDKROOT=$(xcrun --sdk iphoneos --show-sdk-path)
    TARGET=arm64-apple-ios"$DEPLOYMENT_TARGET"
    MIN_VERSION_FLAG=-miphoneos-version-min
    SUPPORTED_PLATFORM=iPhoneOS
    ;;
  iphonesimulator)
    SDKROOT=$(xcrun --sdk iphonesimulator --show-sdk-path)
    TARGET=arm64-apple-ios"$DEPLOYMENT_TARGET"-simulator
    MIN_VERSION_FLAG=-mios-simulator-version-min
    SUPPORTED_PLATFORM=iPhoneSimulator
    ;;
  *)
    echo "unsupported iSH framework SDK: $SDK_NAME" >&2
    exit 2
    ;;
esac
BUILD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ish-framework.XXXXXX")
trap 'rm -rf "$BUILD_DIR"' EXIT

for input in \
  "$LIB_DIR/ish-sections.o" \
  "$LIB_DIR/liblinux.a" \
  "$LIB_DIR/libiSHLinux.a" \
  "$LIB_DIR/libiSHLinuxUser.a" \
  "$LIB_DIR/libfakefs.a" \
  "$LIB_DIR/libish_emu.a" \
  "$LIB_DIR/LinuxInterop.h"; do
  [ -s "$input" ] || { echo "missing iSH framework input: $input" >&2; exit 2; }
done

mkdir -p "$FRAMEWORK/Headers" "$FRAMEWORK/Modules"
COMMON_FLAGS=(
  -target "$TARGET"
  -isysroot "$SDKROOT"
  "$MIN_VERSION_FLAG=$DEPLOYMENT_TARGET"
  -D_DARWIN_C_SOURCE=1
  -I"$ROOT/ISHBridge"
)

xcrun --sdk "$SDK_NAME" clang "${COMMON_FLAGS[@]}" -fobjc-arc -fblocks \
  -I"$LIB_DIR" -c "$ROOT/ISHBridge/ish_kernel_bridge.m" -o "$BUILD_DIR/ish_kernel_bridge.o"
for source in ish_rootfs ish_path_safety ish_exit_protocol; do
  xcrun --sdk "$SDK_NAME" clang "${COMMON_FLAGS[@]}" \
    -c "$ROOT/ISHBridge/$source.c" -o "$BUILD_DIR/$source.o"
done

xcrun --sdk "$SDK_NAME" clang "${COMMON_FLAGS[@]}" -dynamiclib \
  "$LIB_DIR/ish-sections.o" \
  "$BUILD_DIR/ish_kernel_bridge.o" \
  "$BUILD_DIR/ish_rootfs.o" \
  "$BUILD_DIR/ish_path_safety.o" \
  "$BUILD_DIR/ish_exit_protocol.o" \
  -Wl,-force_load,"$LIB_DIR/liblinux.a" \
  -Wl,-force_load,"$LIB_DIR/libiSHLinux.a" \
  "$LIB_DIR/libiSHLinuxUser.a" \
  "$LIB_DIR/libfakefs.a" \
  "$LIB_DIR/libish_emu.a" \
  -framework Foundation -lsqlite3 -lz \
  -Wl,-install_name,@rpath/Ish.framework/Ish \
  -Wl,-exported_symbol,_ish_configure \
  -Wl,-exported_symbol,_ish_kernel_ensure_booted \
  -Wl,-exported_symbol,_ish_run_command \
  -o "$FRAMEWORK/Ish"
chmod 755 "$FRAMEWORK/Ish"

cp "$ROOT/ISHBridge/ish_kernel_bridge.h" "$FRAMEWORK/Headers/ish_kernel_bridge.h"
cat > "$FRAMEWORK/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>Ish</string>
<key>CFBundleIdentifier</key><string>com.cyan.hermeslink.ish</string>
<key>CFBundlePackageType</key><string>FMWK</string>
<key>CFBundleSupportedPlatforms</key><array><string>$SUPPORTED_PLATFORM</string></array>
<key>CFBundleVersion</key><string>1</string>
<key>MinimumOSVersion</key><string>$DEPLOYMENT_TARGET</string>
</dict></plist>
PLIST
cat > "$FRAMEWORK/Modules/module.modulemap" <<'MODULEMAP'
framework module Ish {
  umbrella header "ish_kernel_bridge.h"
  export *
}
MODULEMAP

echo "Packaged $FRAMEWORK"
