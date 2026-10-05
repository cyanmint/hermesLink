#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
module_root="$(cd "${1:-$repository_root/modules/blink}" && pwd)"
integration_root="$(cd "${2:-$repository_root}" && pwd)"
target_root="$(cd "${3:-$integration_root}" && pwd)"
revision="$(tr -d '\r\n' < "$integration_root/blink/UPSTREAM_REVISION")"
actual_revision="$(git -C "$module_root" rev-parse HEAD)"

if [[ ! "$revision" =~ ^[0-9a-f]{40}$ ]]; then
  echo "invalid pinned Blink revision: $revision" >&2
  exit 1
fi
if [[ "$actual_revision" != "$revision" ]]; then
  echo "Blink checkout is $actual_revision; expected $revision" >&2
  exit 1
fi

source_root=$(mktemp -d "${TMPDIR:-/tmp}/hermeslink-blink-source.XXXXXX")
trap 'rm -rf "$source_root"' EXIT
rsync -a --exclude='.git' "$module_root/" "$source_root/"
rsync -a "$integration_root/blink/overlay/" "$source_root/"
python3 "$integration_root/blink/apply-patches.py" "$source_root"

test -s "$source_root/Blink.xcodeproj/project.pbxproj"
rsync -a "$integration_root/ishbridge/" "$source_root/ISHBridge/"
rsync -a \
  --exclude='.git' \
  --exclude='/.github' \
  --exclude='/.gitignore' \
  --exclude='/.gitmodules' \
  --exclude='/AUTHORS' \
  --exclude='/COPYING' \
  --exclude='/COPYING.md' \
  --exclude='/README.md' \
  --exclude='/BUILD.md' \
  --exclude='/DEVELOP.md' \
  "$source_root/" "$target_root/"
