#!/usr/bin/env bash
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
#
# Installs the prebuilt Ish.framework and pinned Alpine rootfs into the
# HermesLink Xcode build tree, matching scripts/install_hermes_runtime.sh's role.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BLINK_ROOT=${BLINK_ROOT:-$ROOT}
INPUT_ROOT=${1:-${ISH_NATIVE_BUILD_ROOT:-$ROOT/hermes/build/external/ish}}
SOURCE_FRAMEWORK=${ISH_FRAMEWORK:-$INPUT_ROOT/Frameworks/Ish.framework}
if [ -n "${ISH_ROOTFS_ARCHIVE:-}" ]; then
  SOURCE_ROOTFS=$ISH_ROOTFS_ARCHIVE
elif [ -f "$INPUT_ROOT/Resources/ish-rootfs.tar.gz" ]; then
  SOURCE_ROOTFS="$INPUT_ROOT/Resources/ish-rootfs.tar.gz"
else
  SOURCE_ROOTFS="$INPUT_ROOT/rootfs.tar.gz"
fi
DEST_FRAMEWORK="$BLINK_ROOT/Frameworks/Ish.framework"
DEST_ROOTFS="$BLINK_ROOT/Resources/ish-rootfs.tar.gz"

[ -s "$SOURCE_FRAMEWORK/Ish" ] || { echo "missing iSH framework executable: $SOURCE_FRAMEWORK/Ish" >&2; exit 2; }
[ -f "$SOURCE_FRAMEWORK/Info.plist" ] || { echo "missing iSH framework Info.plist: $SOURCE_FRAMEWORK/Info.plist" >&2; exit 2; }
[ -f "$SOURCE_FRAMEWORK/Headers/ish_kernel_bridge.h" ] || { echo "missing iSH framework public header: $SOURCE_FRAMEWORK/Headers/ish_kernel_bridge.h" >&2; exit 2; }

[ -f "$SOURCE_ROOTFS" ] || { echo "missing pinned iSH Alpine rootfs archive: $SOURCE_ROOTFS" >&2; exit 2; }
python3 "$ROOT/scripts/hermes/build/verify-ish-source.py" --rootfs "$SOURCE_ROOTFS"

mkdir -p "$(dirname "$DEST_FRAMEWORK")" "$(dirname "$DEST_ROOTFS")"
rm -rf "$DEST_FRAMEWORK.tmp"
cp -a "$SOURCE_FRAMEWORK" "$DEST_FRAMEWORK.tmp"
install -m 644 "$SOURCE_ROOTFS" "$DEST_ROOTFS.tmp"
rm -rf "$DEST_FRAMEWORK"
mv "$DEST_FRAMEWORK.tmp" "$DEST_FRAMEWORK"
mv -f "$DEST_ROOTFS.tmp" "$DEST_ROOTFS"

echo "Installed $DEST_FRAMEWORK ($(wc -c < "$DEST_FRAMEWORK/Ish") bytes)"
printf 'Installed %s (%s bytes)\n' "$DEST_ROOTFS" "$(wc -c < "$DEST_ROOTFS")"
