#!/usr/bin/env bash

set -euo pipefail

# This executable doubles as the external CLI; all assertions exercise the wrapper.
if [[ "${BASH_SOURCE[0]##*/}" == 'fake-graphify' ]]; then
  printf '%s\n' "$PWD" >> "$FAKE_ALL_CALLS"
  if [[ "${1:-}" == '--version' ]]; then
    printf 'graphify %s\n' "${FAKE_VERSION:-0.9.77}"
    exit 0
  fi
  printf '%s' "${1:-}" >> "$FAKE_LOG"
  if (( $# > 1 )); then
    printf '<%s>' "${@:2}" >> "$FAKE_LOG"
  fi
  printf '\n' >> "$FAKE_LOG"
  [[ "${1:-}" != "${FAKE_FAIL:-}" ]] || exit 9
  if [[ "${1:-}" == export && "${2:-}" == obsidian ]]; then
    destination="$4"
    mkdir -p "${destination}/.obsidian"
    if [[ "${FAKE_MISSING_CANVAS_TARGET:-}" != 1 ]]; then
      printf 'Generated note\n' > "${destination}/Example note.md"
    fi
    if [[ "${FAKE_KEEP_CANVAS:-}" != 1 || ! -f "${destination}/graph.canvas" ]]; then
      printf '%s\n' '{"nodes":[{"id":"note","type":"file","file":"Example note.md","x":0,"y":0,"width":200,"height":100},{"id":"group","type":"group","file":"keep-group-field.md","x":0,"y":0,"width":300,"height":200}],"edges":[]}' > "${destination}/graph.canvas"
    fi
  fi
  exit 0
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mkdir -p "${PROJECT_ROOT}/graphify-out"
TEST_ROOT="$(mktemp -d "${PROJECT_ROOT}/graphify-out/.contract-test.XXXXXX")"
trap 'rm -rf -- "$TEST_ROOT"' EXIT
passed=0
failed=0

fixture() {
  CASE_ROOT="${TEST_ROOT}/$1"
  mkdir -p "${CASE_ROOT}/scripts" "${CASE_ROOT}/graphify-out" "${CASE_ROOT}/vault with spaces/.obsidian" "${CASE_ROOT}/.agents/skills/graphify"
  printf '0.9.77\n' > "${CASE_ROOT}/.agents/skills/graphify/.graphify_version"
  cp "${BASH_SOURCE[0]}" "${CASE_ROOT}/fake-graphify"
  chmod +x "${CASE_ROOT}/fake-graphify"
  if [[ -f "${PROJECT_ROOT}/scripts/graphify.sh" ]]; then
    cp "${PROJECT_ROOT}/scripts/graphify.sh" "${CASE_ROOT}/scripts/graphify.sh"
  fi
  export CLASSLENS_GRAPHIFY_BIN="${CASE_ROOT}/fake-graphify"
  export FAKE_LOG="${CASE_ROOT}/calls.log"
  export FAKE_ALL_CALLS="${CASE_ROOT}/all-calls.log"
  unset CLASSLENS_OBSIDIAN_GRAPH_DIR FAKE_FAIL FAKE_VERSION FAKE_KEEP_CANVAS FAKE_MISSING_CANVAS_TARGET
  : > "$FAKE_LOG"
  : > "$FAKE_ALL_CALLS"
}

run_wrapper() {
  local result=0
  [[ -f "${CASE_ROOT}/scripts/graphify.sh" ]] || { printf 'Missing scripts/graphify.sh\n'; exit 1; }
  (cd "$TEST_ROOT" && bash "${CASE_ROOT}/scripts/graphify.sh" "$@") > "${CASE_ROOT}/output.log" 2>&1 || result=$?
  RESULT="$result"
}

assert_success() { [[ "$RESULT" == 0 ]] || { cat "${CASE_ROOT}/output.log"; return 1; }; }
assert_failure() { [[ "$RESULT" != 0 ]]; }
assert_calls() { [[ "$(< "$FAKE_LOG")" == "$1" ]]; }
assert_no_cli() { [[ ! -s "$FAKE_ALL_CALLS" ]]; }
assert_diagnostic() { grep -Fq -- "$1" "${CASE_ROOT}/output.log"; }

run_case() {
  fixture "$1"
  # A subshell preserves errexit within each case, so a failed assertion cannot
  # be masked by a later successful cleanup or assertion.
  set +e
  (set -e; "$2")
  local result=$?
  set -e
  if [[ "$result" == 0 ]]; then
    printf 'PASS %s\n' "$1"
    passed=$((passed + 1))
  else
    printf 'FAIL %s\n' "$1"
    failed=$((failed + 1))
  fi
}

build_default() {
  run_wrapper build
  assert_success
  assert_calls $'extract<.><--code-only>\ncluster-only<.><--no-label>\nexport<html>\nexport<obsidian><--dir><'"${CASE_ROOT}/graphify-out/obsidian>"
  [[ "$(sort -u "$FAKE_ALL_CALLS")" == "$CASE_ROOT" ]]
}

env_precedence() {
  printf '%s\n' "${CASE_ROOT}/other/Graphify" > "${CASE_ROOT}/.graphify-obsidian-dir"
  export CLASSLENS_OBSIDIAN_GRAPH_DIR="${CASE_ROOT}/vault with spaces/Graphify"
  run_wrapper build
  assert_success
  assert_calls $'extract<.><--code-only>\ncluster-only<.><--no-label>\nexport<html>\nexport<obsidian><--dir><'"${CLASSLENS_OBSIDIAN_GRAPH_DIR}>"
}

config_precedence() {
  printf '%s\n' "${CASE_ROOT}/vault with spaces/Graphify" > "${CASE_ROOT}/.graphify-obsidian-dir"
  run_wrapper build
  assert_success
  assert_calls $'extract<.><--code-only>\ncluster-only<.><--no-label>\nexport<html>\nexport<obsidian><--dir><'"${CASE_ROOT}/vault with spaces/Graphify>"
}

config_first_nonempty() {
  printf '\n   \n%s\n%s\n' "${CASE_ROOT}/vault with spaces/Graphify" "${CASE_ROOT}/ignored/Graphify" > "${CASE_ROOT}/.graphify-obsidian-dir"
  run_wrapper build
  assert_success
  assert_calls $'extract<.><--code-only>\ncluster-only<.><--no-label>\nexport<html>\nexport<obsidian><--dir><'"${CASE_ROOT}/vault with spaces/Graphify>"
}
config_without_final_newline() {
  printf '\n%s' "${CASE_ROOT}/vault with spaces/Graphify" > "${CASE_ROOT}/.graphify-obsidian-dir"
  run_wrapper build
  assert_success
  assert_calls $'extract<.><--code-only>\ncluster-only<.><--no-label>\nexport<html>\nexport<obsidian><--dir><'"${CASE_ROOT}/vault with spaces/Graphify>"
}
blank_config() { printf '\n \t\n\n' > "${CASE_ROOT}/.graphify-obsidian-dir"; reject_destination; }

reject_destination() {
  run_wrapper build
  assert_failure
  assert_no_cli
}
empty_env() { export CLASSLENS_OBSIDIAN_GRAPH_DIR=''; reject_destination; }
relative_dir() { export CLASSLENS_OBSIDIAN_GRAPH_DIR='relative/Graphify'; reject_destination; }
filesystem_root() { export CLASSLENS_OBSIDIAN_GRAPH_DIR='/'; reject_destination; }
repository_root() { export CLASSLENS_OBSIDIAN_GRAPH_DIR="$CASE_ROOT"; reject_destination; }
vault_root() { export CLASSLENS_OBSIDIAN_GRAPH_DIR='/home/rayubaldo44/obsidian-developer-vault/Vault-EN/02_Projects/ClassLens'; reject_destination; }
wrong_leaf() { export CLASSLENS_OBSIDIAN_GRAPH_DIR="${CASE_ROOT}/vault with spaces/Notes"; reject_destination; }
alias_vault_root() { export CLASSLENS_OBSIDIAN_GRAPH_DIR='/home/rayubaldo44/obsidian-developer-vault/Vault-EN/02_Projects/ClassLens/Graphify/..'; reject_destination; }
empty_config() { : > "${CASE_ROOT}/.graphify-obsidian-dir"; reject_destination; }
symlink_destination() { ln -s "$CASE_ROOT" "${CASE_ROOT}/vault with spaces/Graphify"; export CLASSLENS_OBSIDIAN_GRAPH_DIR="${CASE_ROOT}/vault with spaces/Graphify"; reject_destination; }

missing_parent() {
  export CLASSLENS_OBSIDIAN_GRAPH_DIR="${CASE_ROOT}/missing/Graphify"
  run_wrapper build
  assert_failure
  assert_calls $'extract<.><--code-only>\ncluster-only<.><--no-label>\nexport<html>\nexport<obsidian><--dir><'"${CASE_ROOT}/graphify-out/obsidian>"
  grep -Fiq 'parent' "${CASE_ROOT}/output.log"
  grep -Fq "${CASE_ROOT}/missing" "${CASE_ROOT}/output.log"
  [[ ! -e "${CASE_ROOT}/missing" ]]
}

failed_extract() {
  export FAKE_FAIL=extract
  printf 'keep\n' > "${CASE_ROOT}/graphify-out/marker"
  run_wrapper build
  assert_failure
  assert_calls 'extract<.><--code-only>'
  [[ "$(< "${CASE_ROOT}/graphify-out/marker")" == keep ]]
}
failed_update() {
  export FAKE_FAIL=extract
  printf 'keep\n' > "${CASE_ROOT}/graphify-out/marker"
  run_wrapper update
  assert_failure
  assert_calls 'extract<.><--code-only><--force>'
  [[ "$(< "${CASE_ROOT}/graphify-out/marker")" == keep ]]
}
successful_update() {
  run_wrapper update
  assert_success
  assert_calls $'extract<.><--code-only><--force>\ncluster-only<.><--no-label>\nexport<html>\nexport<obsidian><--dir><'"${CASE_ROOT}/graphify-out/obsidian>"
}

failed_build_clustering() {
  export FAKE_FAIL=cluster-only
  printf 'keep\n' > "${CASE_ROOT}/graphify-out/marker"
  run_wrapper build
  assert_failure
  assert_calls $'extract<.><--code-only>\ncluster-only<.><--no-label>'
  [[ "$(< "${CASE_ROOT}/graphify-out/marker")" == keep ]]
}
failed_update_clustering() {
  export FAKE_FAIL=cluster-only
  run_wrapper update
  assert_failure
  assert_calls $'extract<.><--code-only><--force>\ncluster-only<.><--no-label>'
}

graph_fixture() { printf '%s\n' "$1" > "${CASE_ROOT}/graphify-out/graph.json"; }
valid_graph() { graph_fixture '{"directed":false,"multigraph":false,"graph":{},"nodes":[{"id":"example"}],"links":[],"built_at_commit":"abc123"}'; }
wrong_version() { valid_graph; export FAKE_VERSION=0.9.76; run_wrapper check; assert_failure; assert_calls ''; }
missing_graph() { run_wrapper check; assert_failure; assert_calls ''; }
invalid_json() { graph_fixture '{broken'; run_wrapper check; assert_failure; }
wrong_skill_version() { valid_graph; printf '0.9.76\n' > "${CASE_ROOT}/.agents/skills/graphify/.graphify_version"; run_wrapper check; assert_failure; assert_diagnostic 'Graphify skill version'; }
missing_skill_version() { valid_graph; mv "${CASE_ROOT}/.agents/skills/graphify/.graphify_version" "${CASE_ROOT}/version.backup"; run_wrapper check; assert_failure; assert_diagnostic 'Graphify skill version'; }
blank_skill_version() { valid_graph; printf ' \n' > "${CASE_ROOT}/.agents/skills/graphify/.graphify_version"; run_wrapper check; assert_failure; assert_diagnostic 'Graphify skill version'; }
graph_not_object() { graph_fixture '{"graph":[],"nodes":[{"id":"example"}],"links":[],"built_at_commit":"abc123"}'; run_wrapper check; assert_failure; assert_diagnostic 'graph must be an object'; }
missing_graph_object() { graph_fixture '{"nodes":[{"id":"example"}],"links":[],"built_at_commit":"abc123"}'; run_wrapper check; assert_failure; assert_diagnostic 'graph must be an object'; }
nodes_not_array() { graph_fixture '{"graph":{},"nodes":{},"links":[],"built_at_commit":"abc123"}'; run_wrapper check; assert_failure; assert_diagnostic 'nodes must be a non-empty array'; }
empty_nodes() { graph_fixture '{"graph":{},"nodes":[],"links":[],"built_at_commit":"abc123"}'; run_wrapper check; assert_failure; assert_diagnostic 'nodes must be a non-empty array'; }
links_not_array() { graph_fixture '{"graph":{},"nodes":[{"id":"example"}],"links":{},"built_at_commit":"abc123"}'; run_wrapper check; assert_failure; assert_diagnostic 'links must be an array'; }
missing_commit() { graph_fixture '{"graph":{},"nodes":[{"id":"example"}],"links":[]}'; run_wrapper check; assert_failure; assert_diagnostic 'built_at_commit must be a non-empty string'; }
empty_commit() { graph_fixture '{"graph":{},"nodes":[{"id":"example"}],"links":[],"built_at_commit":"  "}'; run_wrapper check; assert_failure; assert_diagnostic 'built_at_commit must be a non-empty string'; }
nonstring_commit() { graph_fixture '{"graph":{},"nodes":[{"id":"example"}],"links":[],"built_at_commit":123}'; run_wrapper check; assert_failure; assert_diagnostic 'built_at_commit must be a non-empty string'; }
reject_old_metadata_only() { graph_fixture '{"graph":{"schema_version":"1","graphify_version":"0.9.77"}}'; run_wrapper check; assert_failure; }
valid_check() { valid_graph; local before; before="$(< "${CASE_ROOT}/graphify-out/graph.json")"; run_wrapper check; assert_success; assert_calls ''; [[ "$(< "${CASE_ROOT}/graphify-out/graph.json")" == "$before" ]]; }
archify_excluded() {
  mkdir -p "${CASE_ROOT}/ignore-test"
  git init -q "${CASE_ROOT}/ignore-test"
  git -C "${CASE_ROOT}/ignore-test" -c core.excludesFile="${PROJECT_ROOT}/.graphifyignore" check-ignore --no-index .archify/index.html docs/.archify/generated.svg >/dev/null
}
query_without_question() { run_wrapper query; assert_failure; assert_no_cli; }
query_blank_question() { run_wrapper query '   '; assert_failure; assert_no_cli; }
query_intact() { run_wrapper query what connects analysis to 'remediation?'; assert_success; assert_calls 'query<what connects analysis to remediation?>'; }

assert_canvas_file() {
  python3 - "$1" "$2" "$3" <<'PY'
import json
import sys
from pathlib import Path

canvas = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
note, group = canvas["nodes"]
assert note["file"] == sys.argv[2], note["file"]
assert (Path(sys.argv[3]) / note["file"]).is_file()
assert group["file"] == "keep-group-field.md"
assert canvas["edges"] == []
PY
}

external_canvas() {
  mkdir -p "${CASE_ROOT}/vault with spaces/projects/ClassLens/Graphify/.obsidian"
  export CLASSLENS_OBSIDIAN_GRAPH_DIR="${CASE_ROOT}/vault with spaces/projects/ClassLens/Graphify"
  run_wrapper build
  assert_success
  assert_canvas_file "${CLASSLENS_OBSIDIAN_GRAPH_DIR}/graph.canvas" 'projects/ClassLens/Graphify/Example note.md' "${CASE_ROOT}/vault with spaces"
}

external_canvas_without_vault() {
  rmdir "${CASE_ROOT}/vault with spaces/.obsidian"
  export CLASSLENS_OBSIDIAN_GRAPH_DIR="${CASE_ROOT}/vault with spaces/Graphify"
  run_wrapper build
  assert_failure
  assert_diagnostic 'containing Obsidian vault'
  [[ ! -e "${CLASSLENS_OBSIDIAN_GRAPH_DIR}/graph.canvas" ]]
}

external_canvas_idempotent() {
  mkdir -p "${CASE_ROOT}/vault with spaces/projects/ClassLens"
  export CLASSLENS_OBSIDIAN_GRAPH_DIR="${CASE_ROOT}/vault with spaces/projects/ClassLens/Graphify"
  export FAKE_KEEP_CANVAS=1
  run_wrapper build
  assert_success
  run_wrapper update
  assert_success
  assert_canvas_file "${CLASSLENS_OBSIDIAN_GRAPH_DIR}/graph.canvas" 'projects/ClassLens/Graphify/Example note.md' "${CASE_ROOT}/vault with spaces"
}

local_canvas() {
  run_wrapper build
  assert_success
  assert_canvas_file "${CASE_ROOT}/graphify-out/obsidian/graph.canvas" 'Example note.md' "${CASE_ROOT}/graphify-out/obsidian"
}

fallback_canvas() {
  export CLASSLENS_OBSIDIAN_GRAPH_DIR="${CASE_ROOT}/missing/Graphify"
  run_wrapper build
  assert_failure
  assert_canvas_file "${CASE_ROOT}/graphify-out/obsidian/graph.canvas" 'Example note.md' "${CASE_ROOT}/graphify-out/obsidian"
}

missing_canvas_target() {
  export CLASSLENS_OBSIDIAN_GRAPH_DIR="${CASE_ROOT}/vault with spaces/Graphify"
  export FAKE_MISSING_CANVAS_TARGET=1
  run_wrapper build
  assert_failure
  assert_diagnostic 'Canvas file target'
}

run_case build_default_order_and_root build_default
run_case environment_overrides_config env_precedence
run_case config_overrides_local_default config_precedence
run_case config_uses_first_nonempty_line config_first_nonempty
run_case config_accepts_line_without_final_newline config_without_final_newline
run_case config_rejects_blank_lines_only blank_config
run_case reject_explicit_empty_environment empty_env
run_case reject_relative_destination relative_dir
run_case reject_filesystem_root filesystem_root
run_case reject_repository_root repository_root
run_case reject_classlens_vault_root vault_root
run_case reject_non_graphify_leaf wrong_leaf
run_case reject_vault_alias alias_vault_root
run_case reject_empty_config empty_config
run_case reject_symlink_to_repository symlink_destination
run_case missing_parent_falls_back_and_fails missing_parent
run_case failed_extract_preserves_outputs failed_extract
run_case failed_update_preserves_outputs failed_update
run_case update_exports_after_success successful_update
run_case failed_build_clustering_prevents_exports failed_build_clustering
run_case failed_update_clustering_prevents_exports failed_update_clustering
run_case check_rejects_wrong_cli_version wrong_version
run_case check_rejects_missing_graph missing_graph
run_case check_rejects_invalid_json invalid_json
run_case check_rejects_wrong_skill_version wrong_skill_version
run_case check_rejects_missing_skill_version missing_skill_version
run_case check_rejects_blank_skill_version blank_skill_version
run_case check_rejects_nonobject_graph graph_not_object
run_case check_rejects_missing_graph_object missing_graph_object
run_case check_rejects_nonarray_nodes nodes_not_array
run_case check_rejects_empty_nodes empty_nodes
run_case check_rejects_nonarray_links links_not_array
run_case check_rejects_missing_commit missing_commit
run_case check_rejects_empty_commit empty_commit
run_case check_rejects_nonstring_commit nonstring_commit
run_case check_rejects_old_metadata_only reject_old_metadata_only
run_case check_accepts_vendor_graph_without_inventing_metadata valid_check
run_case archify_generated_directories_excluded archify_excluded
run_case query_rejects_missing_question query_without_question
run_case query_rejects_blank_question query_blank_question
run_case query_passes_one_intact_argument query_intact
run_case external_canvas_uses_containing_vault_paths external_canvas
run_case external_canvas_rejects_missing_containing_vault external_canvas_without_vault
run_case external_canvas_rewrite_is_idempotent external_canvas_idempotent
run_case local_canvas_keeps_standalone_paths local_canvas
run_case missing_parent_canvas_keeps_standalone_paths fallback_canvas
run_case canvas_rejects_missing_file_target missing_canvas_target

printf '%s passed, %s failed\n' "$passed" "$failed"
[[ "$failed" == 0 ]]
