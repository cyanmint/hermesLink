#!/usr/bin/env bash
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
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
VERIFY="$ROOT/build/verify-ish-source.py"
ISH_COMMIT=83348361fe65311f6e87ad2e1cbb0ac38d123f69
ROOTFS_URL=https://github.com/ish-app/roots/releases/download/g00712ff0a54b2839c5aa1a8ed758003ca65357dc/appstore-apk.tar.gz
trap 'rm -f "$ROOTFS_PARTIAL"' EXIT

mkdir -p "$DEST"
if [ "$MODE" = all ]; then
  if [ ! -d "$SOURCE/.git" ]; then
    if [ -e "$SOURCE" ]; then
      echo "refusing to replace non-git iSH source path: $SOURCE" >&2
      exit 2
    fi
    git clone --filter=blob:none --no-checkout https://github.com/ish-app/ish.git "$SOURCE"
  fi

  git -C "$SOURCE" fetch --depth=1 origin "$ISH_COMMIT"
  git -C "$SOURCE" checkout --detach "$ISH_COMMIT"
  git -C "$SOURCE" submodule sync --recursive
  git -C "$SOURCE" submodule update --init --recursive
  # The upstream .gitmodules intentionally sets update=none for its Linux fork.
  git -C "$SOURCE" submodule update --init --recursive --checkout -- deps/linux
  python3 "$VERIFY" --source "$SOURCE"
fi

if [ ! -f "$ROOTFS" ] || ! python3 "$VERIFY" --rootfs "$ROOTFS"; then
  rm -f "$ROOTFS_PARTIAL"
  curl --fail --location --silent --show-error --retry 3 \
    "$ROOTFS_URL" --output "$ROOTFS_PARTIAL"
  python3 "$VERIFY" --rootfs "$ROOTFS_PARTIAL"
  mv "$ROOTFS_PARTIAL" "$ROOTFS"
fi

if [ "$MODE" = all ]; then
  python3 "$VERIFY" --source "$SOURCE" --rootfs "$ROOTFS"
else
  python3 "$VERIFY" --rootfs "$ROOTFS"
fi
echo "Pinned iSH source and Alpine rootfs verified in $DEST."
echo "These are build-time inputs only; HermesLink does not yet embed or launch iSH."
