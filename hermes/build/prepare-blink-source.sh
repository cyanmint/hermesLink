#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_root="$(cd "${1:?usage: prepare-blink-source.sh BLINK_CHECKOUT [INTEGRATION_ROOT [TARGET_ROOT]]}" && pwd)"
integration_root="$(cd "${2:-$repository_root}" && pwd)"
target_root="$(cd "${3:-$integration_root}" && pwd)"
revision="$(tr -d '\r\n' < "$integration_root/hermes/blink/UPSTREAM_REVISION")"
patch_dir="$integration_root/hermes/blink/patches"
actual_revision="$(git -C "$source_root" rev-parse HEAD)"

if [[ ! "$revision" =~ ^[0-9a-f]{40}$ ]]; then
  echo "invalid pinned Blink revision: $revision" >&2
  exit 1
fi
if [[ "$actual_revision" != "$revision" ]]; then
  echo "Blink checkout is $actual_revision; expected $revision" >&2
  exit 1
fi

rsync -a "$integration_root/hermes/blink/overlay/" "$source_root/"
for patch_file in "$patch_dir"/*.patch; do
  if ! git -C "$source_root" apply --reverse --check "$patch_file" >/dev/null 2>&1; then
    git -C "$source_root" apply --check "$patch_file"
    git -C "$source_root" apply "$patch_file"
  fi
done

test -s "$source_root/Blink.xcodeproj/project.pbxproj"
rsync -a \
  --exclude='/.git' \
  --exclude='/.github' \
  --exclude='/.gitignore' \
  --exclude='/README.md' \
  --exclude='/BUILD.md' \
  --exclude='/Frameworks' \
  "$source_root/" "$target_root/"
