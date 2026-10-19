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
    '  build   Rebuild code only from recoverably archived inputs, validate, and export.' \
    '  update  Rebuild code only with --force, validate, and export.' \
    '  check   Verify the pinned CLI/skill, graph structure, and allowed source scope.' \
    '  query   Ask one question of the existing graph.'
}

fail() {
  printf 'ClassLens Graphify: %s\n' "$1" >&2
  exit 1
}

validate_generated() {
  local python_bin
  python_bin="$(command -v python3 || command -v python)" || fail 'python3 or python is required for Graphify safety checks.'
  "$python_bin" "${PROJECT_ROOT}/scripts/graphify_validate.py" "$@"
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
  local line
  if [[ "${CLASSLENS_OBSIDIAN_GRAPH_DIR+x}" == x ]]; then
    [[ -n "$CLASSLENS_OBSIDIAN_GRAPH_DIR" ]] || fail 'CLASSLENS_OBSIDIAN_GRAPH_DIR is set but empty.'
    path="$CLASSLENS_OBSIDIAN_GRAPH_DIR"
  elif [[ -f "${PROJECT_ROOT}/.graphify-obsidian-dir" ]]; then
    path=''
    while IFS= read -r line || [[ -n "$line" ]]; do
      if [[ -n "${line//[[:space:]]/}" ]]; then
        path="$line"
        break
      fi
    done < "${PROJECT_ROOT}/.graphify-obsidian-dir"
    [[ -n "$path" ]] || fail '.graphify-obsidian-dir has no non-empty destination line.'
  fi
  validate_obsidian_dir "$path"
}

export_graph() {
  local destination="$1"
  local missing_parent=''
  local vault_root python_bin
  if [[ "$destination" != "$LOCAL_OBSIDIAN_DIR" && ! -d "${destination%/*}" ]]; then
    missing_parent="${destination%/*}"
    printf 'ClassLens Graphify: configured Obsidian parent is missing: %s; exporting locally to %s.\n' \
      "$missing_parent" "$LOCAL_OBSIDIAN_DIR" >&2
    destination="$LOCAL_OBSIDIAN_DIR"
  fi
  vault_root="$destination"
  if [[ "$destination" != "$LOCAL_OBSIDIAN_DIR" ]]; then
    # Start above Graphify's own generated .obsidian directory.
    vault_root="${destination%/*}"
    while [[ ! -d "${vault_root}/.obsidian" ]]; do
      [[ "$vault_root" != / ]] || fail "Could not find a containing Obsidian vault for ${destination}."
      vault_root="$(dirname -- "$vault_root")"
    done
  fi
  # Upstream exporters write through child symlinks. Inspect both destinations
  # before either exporter; Canvas validation after writing cannot protect them.
  validate_generated symlinks "${PROJECT_ROOT}/graphify-out" "$destination"
  "$GRAPHIFY_BIN" export html
  "$GRAPHIFY_BIN" export obsidian --dir "$destination"
  python_bin="$(command -v python3 || command -v python)" || fail 'python3 or python is required to validate Canvas paths.'
  "$python_bin" - "$destination" "$vault_root" <<'PY'
import json
import sys
from pathlib import Path

try:
    destination, vault_root = (Path(path).resolve() for path in sys.argv[1:])
    prefix = destination.relative_to(vault_root)
    canvas_path = destination / "graph.canvas"
    canvas = json.loads(canvas_path.read_text(encoding="utf-8"))
    changed = False
    for node in canvas["nodes"]:
        if node.get("type") != "file":
            continue
        relative = Path(node["file"])
        if relative.is_absolute():
            raise ValueError(f"Canvas file target must be relative: {relative}")
        if not relative.is_relative_to(prefix):
            relative = prefix / relative
        target = (vault_root / relative).resolve()
        if not target.is_relative_to(destination) or not target.is_file():
            raise ValueError(f"Canvas file target must exist inside {destination}: {relative}")
        if node["file"] != relative.as_posix():
            node["file"] = relative.as_posix()
            changed = True
    if changed:
        canvas_path.write_text(json.dumps(canvas, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
    print(f"ClassLens Graphify: invalid Canvas paths: {error}", file=sys.stderr)
    sys.exit(1)
print(f"Canvas file targets verified relative to vault: {vault_root}")
PY
  [[ -z "$missing_parent" ]] || fail "Configured Obsidian parent is missing: ${missing_parent}. Local exports were preserved."
}

build_graph() {
  local destination
  destination="$(resolve_obsidian_dir)" || return 1
  require_graphify
  validate_generated symlinks "${PROJECT_ROOT}/graphify-out" "$destination"
  validate_generated prepare
  "$GRAPHIFY_BIN" extract . --code-only
  check_graph
  "$GRAPHIFY_BIN" cluster-only . --no-label
  check_graph
  validate_generated report
  export_graph "$destination"
}

update_graph() {
  local destination
  destination="$(resolve_obsidian_dir)" || return 1
  require_graphify
  validate_generated symlinks "${PROJECT_ROOT}/graphify-out" "$destination"
  validate_generated prepare
  "$GRAPHIFY_BIN" extract . --code-only --force
  check_graph
  "$GRAPHIFY_BIN" cluster-only . --no-label
  check_graph
  validate_generated report
  export_graph "$destination"
}

check_graph() {
  local python_bin
  require_graphify
  [[ -f graphify-out/graph.json ]] || fail 'Missing graphify-out/graph.json. Run build first.'
  python_bin="$(command -v python3 || command -v python)" || fail 'python3 or python is required to validate graph JSON.'
  "$python_bin" - "$EXPECTED_GRAPHIFY_VERSION" <<'PY'
import json
import sys
from pathlib import Path

try:
    version_file = Path(".agents/skills/graphify/.graphify_version")
    if not version_file.is_file():
        raise ValueError("Missing Graphify skill version file: .agents/skills/graphify/.graphify_version")
    if version_file.read_text(encoding="utf-8").strip() != sys.argv[1]:
        raise ValueError(f"Graphify skill version must match {sys.argv[1]}")
    with open("graphify-out/graph.json", encoding="utf-8") as source:
        graph = json.load(source)
    if not isinstance(graph, dict) or not isinstance(graph.get("graph"), dict):
        raise ValueError("graph must be an object")
    if not isinstance(graph.get("nodes"), list) or not graph["nodes"]:
        raise ValueError("nodes must be a non-empty array")
    if not isinstance(graph.get("links"), list):
        raise ValueError("links must be an array")
    if not isinstance(graph.get("built_at_commit"), str) or not graph["built_at_commit"].strip():
        raise ValueError("built_at_commit must be a non-empty string")
except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
    print(f"ClassLens Graphify: invalid graph metadata: {error}", file=sys.stderr)
    sys.exit(1)
print("Graphify CLI, skill version, and graph structure verified.")
PY
  validate_generated sources
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
