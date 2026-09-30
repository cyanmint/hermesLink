#!/usr/bin/env bash
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
set -euo pipefail

# Build-time sources. These are deliberately not Git submodules.
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DEST=${1:-"$ROOT/build/external"}
AGENT_COMMIT=${HERMES_AGENT_COMMIT:-2246c245f51e03eb6a151d19119009156e84659a}
WEBUI_COMMIT=${HERMES_WEBUI_COMMIT:-e36f77389191fe9d81cd3a7416772e2f7b022e19}

mkdir -p "$DEST"
retry_git() {
  local attempt
  for attempt in 1 2 3 4 5; do
    if "$@"; then
      return 0
    fi
    if [ "$attempt" -lt 5 ]; then
      echo "Git operation failed (attempt $attempt/5); retrying in $((attempt * 5))s" >&2
      sleep "$((attempt * 5))"
    fi
  done
  return 1
}

fetch() {
  local name=$1 url=$2 commit=$3
  local dir="$DEST/$name"
  if [ ! -d "$dir/.git" ]; then
    retry_git git clone --filter=blob:none --no-checkout --depth=1 "$url" "$dir" || {
      rm -rf "$dir"
      return 1
    }
  fi
  retry_git git -C "$dir" fetch --depth=1 origin "$commit"
  git -C "$dir" checkout --detach "$commit"
}

fetch hermes-agent https://github.com/NousResearch/hermes-agent.git "$AGENT_COMMIT"
fetch hermes-webui https://github.com/nesquena/hermes-webui.git "$WEBUI_COMMIT"
printf 'hermes-agent=%s\nhermes-webui=%s\n' "$AGENT_COMMIT" "$WEBUI_COMMIT" > "$DEST/SOURCES"
