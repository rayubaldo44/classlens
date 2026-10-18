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
  mkdir -p "${CASE_ROOT}/scripts" "${CASE_ROOT}/graphify-out" "${CASE_ROOT}/vault with spaces"
  cp "${BASH_SOURCE[0]}" "${CASE_ROOT}/fake-graphify"
  chmod +x "${CASE_ROOT}/fake-graphify"
  if [[ -f "${PROJECT_ROOT}/scripts/graphify.sh" ]]; then
    cp "${PROJECT_ROOT}/scripts/graphify.sh" "${CASE_ROOT}/scripts/graphify.sh"
  fi
  export CLASSLENS_GRAPHIFY_BIN="${CASE_ROOT}/fake-graphify"
  export FAKE_LOG="${CASE_ROOT}/calls.log"
  export FAKE_ALL_CALLS="${CASE_ROOT}/all-calls.log"
  unset CLASSLENS_OBSIDIAN_GRAPH_DIR FAKE_FAIL FAKE_VERSION
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
  assert_calls $'extract<.><--code-only>\nexport<html>\nexport<obsidian><--dir><'"${CASE_ROOT}/graphify-out/obsidian>"
  [[ "$(sort -u "$FAKE_ALL_CALLS")" == "$CASE_ROOT" ]]
}

env_precedence() {
  printf '%s\n' "${CASE_ROOT}/other/Graphify" > "${CASE_ROOT}/.graphify-obsidian-dir"
  export CLASSLENS_OBSIDIAN_GRAPH_DIR="${CASE_ROOT}/vault with spaces/Graphify"
  run_wrapper build
  assert_success
  assert_calls $'extract<.><--code-only>\nexport<html>\nexport<obsidian><--dir><'"${CLASSLENS_OBSIDIAN_GRAPH_DIR}>"
}

config_precedence() {
  printf '%s\n' "${CASE_ROOT}/vault with spaces/Graphify" > "${CASE_ROOT}/.graphify-obsidian-dir"
  run_wrapper build
  assert_success
  assert_calls $'extract<.><--code-only>\nexport<html>\nexport<obsidian><--dir><'"${CASE_ROOT}/vault with spaces/Graphify>"
}

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
  assert_calls $'extract<.><--code-only>\nexport<html>\nexport<obsidian><--dir><'"${CASE_ROOT}/graphify-out/obsidian>"
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
  export FAKE_FAIL=update
  printf 'keep\n' > "${CASE_ROOT}/graphify-out/marker"
  run_wrapper update
  assert_failure
  assert_calls 'update<.>'
  [[ "$(< "${CASE_ROOT}/graphify-out/marker")" == keep ]]
}
successful_update() {
  run_wrapper update
  assert_success
  assert_calls $'update<.>\nexport<html>\nexport<obsidian><--dir><'"${CASE_ROOT}/graphify-out/obsidian>"
}

graph_fixture() { printf '%s\n' "$1" > "${CASE_ROOT}/graphify-out/graph.json"; }
valid_graph() { graph_fixture '{"graph":{"schema_version":"1","graphify_version":"0.9.77"}}'; }
wrong_version() { valid_graph; export FAKE_VERSION=0.9.76; run_wrapper check; assert_failure; assert_calls ''; }
missing_graph() { run_wrapper check; assert_failure; assert_calls ''; }
invalid_json() { graph_fixture '{broken'; run_wrapper check; assert_failure; }
missing_schema() { graph_fixture '{"graph":{"graphify_version":"0.9.77"}}'; run_wrapper check; assert_failure; }
missing_graphify_version() { graph_fixture '{"graph":{"schema_version":"1"}}'; run_wrapper check; assert_failure; }
empty_metadata() { graph_fixture '{"graph":{"schema_version":"","graphify_version":""}}'; run_wrapper check; assert_failure; }
valid_check() { valid_graph; run_wrapper check; assert_success; assert_calls ''; }
query_without_question() { run_wrapper query; assert_failure; assert_no_cli; }
query_blank_question() { run_wrapper query '   '; assert_failure; assert_no_cli; }
query_intact() { run_wrapper query what connects analysis to 'remediation?'; assert_success; assert_calls 'query<what connects analysis to remediation?>'; }

run_case build_default_order_and_root build_default
run_case environment_overrides_config env_precedence
run_case config_overrides_local_default config_precedence
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
run_case check_rejects_wrong_cli_version wrong_version
run_case check_rejects_missing_graph missing_graph
run_case check_rejects_invalid_json invalid_json
run_case check_rejects_missing_schema_version missing_schema
run_case check_rejects_missing_graphify_version missing_graphify_version
run_case check_rejects_empty_metadata empty_metadata
run_case check_accepts_valid_metadata valid_check
run_case query_rejects_missing_question query_without_question
run_case query_rejects_blank_question query_blank_question
run_case query_passes_one_intact_argument query_intact

printf '%s passed, %s failed\n' "$passed" "$failed"
[[ "$failed" == 0 ]]
