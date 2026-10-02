#!/usr/bin/env bash
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
#
# Installs the iSH native build components (prebuilt static libraries +
# LinuxInterop.h from hermes/build/build-ish-static.sh, and the pinned
# Alpine rootfs archive from hermes/build/fetch-ish-source.sh) into
# HermesLink's Xcode build tree, mirroring install_hermes_runtime.sh's
# role for the Python runtime: this script places already-built artifacts
# where the Blink target expects them; it does not build anything itself.
#
# build-ish-static.sh exports the pinned upstream iSH host bridge,
# user-emulation, Linux kernel, fakefs, and emulator archives.
# Require this exact set so the Blink target cannot silently build with an
# incomplete or mismatched kernel runtime.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BLINK_ROOT=${BLINK_ROOT:-$ROOT}
INPUT_ROOT=${1:-${ISH_NATIVE_BUILD_ROOT:-$ROOT/hermes/build/external/ish}}
SOURCE_LIB_DIR=${ISH_LIB_DIR:-$INPUT_ROOT/lib}
SOURCE_ROOTFS=${ISH_ROOTFS_ARCHIVE:-$INPUT_ROOT/rootfs.tar.gz}
DEST_LIB_DIR="$BLINK_ROOT/Frameworks/ISHLinux"
DEST_ROOTFS="$BLINK_ROOT/Resources/ish-rootfs.tar.gz"

[ -d "$SOURCE_LIB_DIR" ] || { echo "missing iSH native build output directory: $SOURCE_LIB_DIR" >&2; exit 2; }
[ -f "$SOURCE_LIB_DIR/LinuxInterop.h" ] || { echo "missing $SOURCE_LIB_DIR/LinuxInterop.h" >&2; exit 2; }

for archive in libiSHLinux.a libiSHLinuxUser.a liblinux.a libfakefs.a libish_emu.a; do
  [ -s "$SOURCE_LIB_DIR/$archive" ] || {
    echo "missing required iSH archive: $SOURCE_LIB_DIR/$archive" >&2
    exit 2
  }
done

[ -f "$SOURCE_ROOTFS" ] || { echo "missing pinned iSH Alpine rootfs archive: $SOURCE_ROOTFS" >&2; exit 2; }
python3 "$ROOT/hermes/build/verify-ish-source.py" --rootfs "$SOURCE_ROOTFS"

mkdir -p "$(dirname "$DEST_LIB_DIR")" "$(dirname "$DEST_ROOTFS")"
rm -rf "$DEST_LIB_DIR.tmp"
mkdir -p "$DEST_LIB_DIR.tmp"
cp "$SOURCE_LIB_DIR/LinuxInterop.h" "$DEST_LIB_DIR.tmp/LinuxInterop.h"
cp "$SOURCE_LIB_DIR/libiSHLinux.a" "$DEST_LIB_DIR.tmp/"
cp "$SOURCE_LIB_DIR/libiSHLinuxUser.a" "$DEST_LIB_DIR.tmp/"
cp "$SOURCE_LIB_DIR/liblinux.a" "$DEST_LIB_DIR.tmp/"
cp "$SOURCE_LIB_DIR/libfakefs.a" "$DEST_LIB_DIR.tmp/"
cp "$SOURCE_LIB_DIR/libish_emu.a" "$DEST_LIB_DIR.tmp/"

install -m 644 "$SOURCE_ROOTFS" "$DEST_ROOTFS.tmp"
rm -rf "$DEST_LIB_DIR"
mv "$DEST_LIB_DIR.tmp" "$DEST_LIB_DIR"
mv -f "$DEST_ROOTFS.tmp" "$DEST_ROOTFS"

echo "Installed $DEST_LIB_DIR ($(find "$DEST_LIB_DIR" -maxdepth 1 -name '*.a' | wc -l | tr -d ' ') static librar(y/ies))"
printf 'Installed %s (%s bytes)\n' "$DEST_ROOTFS" "$(wc -c < "$DEST_ROOTFS")"
