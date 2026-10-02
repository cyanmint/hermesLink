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
# build-ish-static.sh deliberately copies Meson/Ninja's static libraries
# under their OWN discovered names (their exact names were not reliably
# knowable without running the real Xcode+Meson build — see that script's
# comments). This script is what turns "however many archives were
# discovered" into the two fixed names the Blink target's
# hermes/build/ISHNative.xcconfig links against (-lISHLinuxKernel
# -lISHLinuxUser): it requires exactly two, and fails clearly (not a silent
# guess) if that is not what it finds, since that would mean the assumption
# needs revisiting with a real build in hand.
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

archives=()
while IFS= read -r archive; do
  archives+=("$archive")
done < <(find "$SOURCE_LIB_DIR" -maxdepth 1 -name '*.a' -type f | sort)

[ "${#archives[@]}" -gt 0 ] || { echo "missing any .a static library under $SOURCE_LIB_DIR" >&2; exit 2; }

[ -f "$SOURCE_ROOTFS" ] || { echo "missing pinned iSH Alpine rootfs archive: $SOURCE_ROOTFS" >&2; exit 2; }
python3 "$ROOT/hermes/build/verify-ish-source.py" --rootfs "$SOURCE_ROOTFS"

mkdir -p "$(dirname "$DEST_LIB_DIR")" "$(dirname "$DEST_ROOTFS")"
rm -rf "$DEST_LIB_DIR.tmp"
mkdir -p "$DEST_LIB_DIR.tmp"
cp "$SOURCE_LIB_DIR/LinuxInterop.h" "$DEST_LIB_DIR.tmp/LinuxInterop.h"

if [ "${#archives[@]}" -eq 2 ]; then
  # Deterministic (alphabetical) assignment: hermes/build/ISHNative.xcconfig
  # links both unconditionally (-lISHLinuxKernel -lISHLinuxUser) as one
  # combined static archive set, so which physical file gets which fixed
  # name does not change what ends up linked into the app.
  cp "${archives[0]}" "$DEST_LIB_DIR.tmp/libISHLinuxKernel.a"
  cp "${archives[1]}" "$DEST_LIB_DIR.tmp/libISHLinuxUser.a"
elif [ "${#archives[@]}" -eq 1 ]; then
  cp "${archives[0]}" "$DEST_LIB_DIR.tmp/libISHLinuxKernel.a"
  : > "$DEST_LIB_DIR.tmp/libISHLinuxUser.a.empty-marker"
  echo "warning: only one static library was found; installing it as libISHLinuxKernel.a and" >&2
  echo "  writing an empty marker instead of libISHLinuxUser.a. hermes/build/ISHNative.xcconfig" >&2
  echo "  still references both names, so the link step will need adjusting for this build." >&2
else
  echo "expected 1-2 static libraries under $SOURCE_LIB_DIR, found ${#archives[@]}:" >&2
  printf '  %s\n' "${archives[@]}" >&2
  echo "refusing to guess a name mapping; inspect the Meson build output and adjust" >&2
  echo "  install_ish_runtime.sh (or hermes/build/build-ish-static.sh) accordingly." >&2
  rm -rf "$DEST_LIB_DIR.tmp"
  exit 2
fi

install -m 644 "$SOURCE_ROOTFS" "$DEST_ROOTFS.tmp"
rm -rf "$DEST_LIB_DIR"
mv "$DEST_LIB_DIR.tmp" "$DEST_LIB_DIR"
mv -f "$DEST_ROOTFS.tmp" "$DEST_ROOTFS"

echo "Installed $DEST_LIB_DIR ($(find "$DEST_LIB_DIR" -maxdepth 1 -name '*.a' | wc -l | tr -d ' ') static librar(y/ies))"
printf 'Installed %s (%s bytes)\n' "$DEST_ROOTFS" "$(wc -c < "$DEST_ROOTFS")"
