#!/usr/bin/env bash
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/../../../hermes" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
MODE=all
if [ "${1:-}" = "--rootfs-only" ]; then
  MODE=rootfs-only
  ROOTFS=${2:-"$ROOT/build/external/ish/rootfs.tar.gz"}
  DEST=$(dirname "$ROOTFS")
else
  DEST=${1:-"$ROOT/build/external/ish"}
  ROOTFS="$DEST/rootfs.tar.gz"
fi
SOURCE="$DEST/source"
ROOTFS_PARTIAL="$ROOTFS.partial"
VERIFY="$SCRIPT_DIR/verify-ish-source.py"
ISH_MODULE_SOURCE=${ISH_MODULE_SOURCE:-$REPO_ROOT/modules/ish}
ROOTFS_URL=https://github.com/ish-app/roots/releases/download/g00712ff0a54b2839c5aa1a8ed758003ca65357dc/appstore-apk.tar.gz
trap 'rm -f "$ROOTFS_PARTIAL"' EXIT

mkdir -p "$DEST"
if [ "$MODE" = all ]; then
  [ -f "$ISH_MODULE_SOURCE/.git" ] || [ -d "$ISH_MODULE_SOURCE/.git" ] || {
    echo "missing initialized iSH submodule at $ISH_MODULE_SOURCE; clone with --recurse-submodules" >&2
    exit 2
  }
  git -C "$ISH_MODULE_SOURCE" -c submodule.deps/linux.update=checkout \
    submodule update --init --checkout --depth 1 -- deps/linux
  python3 "$VERIFY" --source "$ISH_MODULE_SOURCE"
  if [ -e "$SOURCE" ] && [ ! -f "$SOURCE/.hermeslink-source-revision" ]; then
    echo "refusing to replace non-generated iSH source path: $SOURCE" >&2
    exit 2
  fi
  rm -rf "$SOURCE"
  mkdir -p "$SOURCE"
  rsync -a --exclude='.git' "$ISH_MODULE_SOURCE/" "$SOURCE/"
  printf '%s\n' "$(git -C "$ISH_MODULE_SOURCE" rev-parse HEAD)" > "$SOURCE/.hermeslink-source-revision"
fi

if [ ! -f "$ROOTFS" ] || ! python3 "$VERIFY" --rootfs "$ROOTFS"; then
  rm -f "$ROOTFS_PARTIAL"
  curl --fail --location --silent --show-error --retry 3 \
    "$ROOTFS_URL" --output "$ROOTFS_PARTIAL"
  python3 "$VERIFY" --rootfs "$ROOTFS_PARTIAL"
  mv "$ROOTFS_PARTIAL" "$ROOTFS"
fi

if [ "$MODE" = all ]; then
  python3 "$VERIFY" --source "$ISH_MODULE_SOURCE" --rootfs "$ROOTFS"
else
  python3 "$VERIFY" --rootfs "$ROOTFS"
fi
echo "Pinned iSH submodule source and Alpine rootfs verified in $DEST."
echo "These are build-time inputs only; HermesLink does not yet embed or launch iSH."
