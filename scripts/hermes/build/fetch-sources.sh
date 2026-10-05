#!/usr/bin/env bash
# HermesLink AI-generated glue code; created by cyanmint's coding agent.
# AI-generated content has no copyright holder and is not subject to copyright.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../hermes" && pwd)
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
DEST=${1:-"$ROOT/build/external"}
AGENT_COMMIT=2246c245f51e03eb6a151d19119009156e84659a
WEBUI_COMMIT=e36f77389191fe9d81cd3a7416772e2f7b022e19
AGENT_SOURCE=${HERMES_SOURCE:-$REPO_ROOT/modules/hermes-agent}
WEBUI_SOURCE=${WEBUI_SOURCE:-$REPO_ROOT/modules/hermes-webui}

mkdir -p "$DEST"
verify_source() {
  local name=$1 dir=$2 expected=$3
  [ -f "$dir/.git" ] || [ -d "$dir/.git" ] || {
    echo "missing initialized $name submodule at $dir; clone with --recurse-submodules" >&2
    exit 2
  }
  actual=$(git -C "$dir" rev-parse HEAD)
  [ "$actual" = "$expected" ] || {
    echo "$name submodule is at $actual; expected pinned revision $expected" >&2
    exit 2
  }
}

verify_source hermes-agent "$AGENT_SOURCE" "$AGENT_COMMIT"
verify_source hermes-webui "$WEBUI_SOURCE" "$WEBUI_COMMIT"
test -f "$AGENT_SOURCE/hermes_cli/main.py" || { echo "missing Hermes Agent source" >&2; exit 2; }
test -f "$WEBUI_SOURCE/api/config.py" || { echo "missing Hermes WebUI source" >&2; exit 2; }
printf 'hermes-agent=%s\nhermes-webui=%s\n' "$AGENT_COMMIT" "$WEBUI_COMMIT" > "$DEST/SOURCES"
