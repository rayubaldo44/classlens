#!/usr/bin/env bash

set -euo pipefail

EXPECTED_GRAPHIFY_VERSION="0.9.77"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
GRAPHIFY_BIN="${CLASSLENS_GRAPHIFY_BIN:-graphify}"
LOCAL_OBSIDIAN_DIR="${PROJECT_ROOT}/graphify-out/obsidian"
CLASSLENS_VAULT_ROOT='/home/rayubaldo44/obsidian-developer-vault/Vault-EN/02_Projects/ClassLens'

usage() {
  printf '%s\n' \
    'Usage: ./scripts/graphify.sh <build|update|check|query QUESTION>' \
    '' \
    '  build   Extract code only, then export HTML and Obsidian notes.' \
    '  update  Update the existing graph, then export HTML and Obsidian notes.' \
    '  check   Verify the pinned CLI and graph metadata.' \
    '  query   Ask one question of the existing graph.'
}

fail() {
  printf 'ClassLens Graphify: %s\n' "$1" >&2
  exit 1
}

require_graphify() {
  local installed_version
  command -v "$GRAPHIFY_BIN" >/dev/null 2>&1 \
    || fail "Graphify is unavailable. Install graphifyy==${EXPECTED_GRAPHIFY_VERSION} separately or set CLASSLENS_GRAPHIFY_BIN."
  installed_version="$("$GRAPHIFY_BIN" --version)" || fail 'Could not read the Graphify CLI version.'
  installed_version="${installed_version##* }"
  installed_version="${installed_version#v}"
  [[ "$installed_version" == "$EXPECTED_GRAPHIFY_VERSION" ]] \
    || fail "Expected Graphify ${EXPECTED_GRAPHIFY_VERSION}; found ${installed_version}."
}

validate_obsidian_dir() {
  local path="$1"
  [[ "$path" == /* ]] || fail 'Obsidian destination must be a non-empty absolute path.'
  path="$(realpath -m -- "$path")" || fail 'Could not resolve the Obsidian destination.'
  case "$path" in
    /|"$PROJECT_ROOT"|"$CLASSLENS_VAULT_ROOT")
      fail "Unsafe Obsidian destination: ${path}"
      ;;
  esac
  [[ "$path" == "$LOCAL_OBSIDIAN_DIR" || "${path##*/}" == Graphify ]] \
    || fail 'External Obsidian destinations must end in a dedicated Graphify directory.'
  printf '%s\n' "$path"
}

resolve_obsidian_dir() {
  local path="$LOCAL_OBSIDIAN_DIR"
  if [[ "${CLASSLENS_OBSIDIAN_GRAPH_DIR+x}" == x ]]; then
    [[ -n "$CLASSLENS_OBSIDIAN_GRAPH_DIR" ]] || fail 'CLASSLENS_OBSIDIAN_GRAPH_DIR is set but empty.'
    path="$CLASSLENS_OBSIDIAN_GRAPH_DIR"
  elif [[ -f "${PROJECT_ROOT}/.graphify-obsidian-dir" ]]; then
    path="$(< "${PROJECT_ROOT}/.graphify-obsidian-dir")"
  fi
  validate_obsidian_dir "$path"
}

export_graph() {
  local destination="$1"
  local missing_parent=''
  "$GRAPHIFY_BIN" export html
  if [[ "$destination" != "$LOCAL_OBSIDIAN_DIR" && ! -d "${destination%/*}" ]]; then
    missing_parent="${destination%/*}"
    printf 'ClassLens Graphify: configured Obsidian parent is missing: %s; exporting locally to %s.\n' \
      "$missing_parent" "$LOCAL_OBSIDIAN_DIR" >&2
    destination="$LOCAL_OBSIDIAN_DIR"
  fi
  "$GRAPHIFY_BIN" export obsidian --dir "$destination"
  [[ -z "$missing_parent" ]] || fail "Configured Obsidian parent is missing: ${missing_parent}. Local exports were preserved."
}

build_graph() {
  local destination
  destination="$(resolve_obsidian_dir)" || return 1
  require_graphify
  "$GRAPHIFY_BIN" extract . --code-only
  export_graph "$destination"
}

update_graph() {
  local destination
  destination="$(resolve_obsidian_dir)" || return 1
  require_graphify
  "$GRAPHIFY_BIN" update .
  export_graph "$destination"
}

check_graph() {
  local python_bin
  require_graphify
  [[ -f graphify-out/graph.json ]] || fail 'Missing graphify-out/graph.json. Run build first.'
  python_bin="$(command -v python3 || command -v python)" || fail 'python3 or python is required to validate graph JSON.'
  "$python_bin" - <<'PY'
import json
import sys

try:
    with open("graphify-out/graph.json", encoding="utf-8") as source:
        graph = json.load(source)["graph"]
    for field in ("schema_version", "graphify_version"):
        if not graph.get(field):
            raise ValueError(f"Missing non-empty graph.{field}")
except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
    print(f"ClassLens Graphify: invalid graph metadata: {error}", file=sys.stderr)
    sys.exit(1)
print("Graphify CLI and graph metadata verified.")
PY
}

query_graph() {
  local question="$1"
  [[ -n "${question//[[:space:]]/}" ]] || fail 'Supply a non-empty query question.'
  require_graphify
  "$GRAPHIFY_BIN" query "$question"
}

cd "$PROJECT_ROOT"
case "${1:-}" in
  build) build_graph ;;
  update) update_graph ;;
  check) check_graph ;;
  query) shift; query_graph "$*" ;;
  -h|--help|help) usage ;;
  *) usage >&2; exit 2 ;;
esac
