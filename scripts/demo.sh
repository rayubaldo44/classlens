#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
RUNTIME_DIR="${CLASSLENS_DEMO_RUNTIME_DIR:-${TMPDIR:-/tmp}/classlens-demo-${UID}}"
BACKEND_HOST="${CLASSLENS_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${CLASSLENS_BACKEND_PORT:-8000}"
FRONTEND_HOST="${CLASSLENS_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${CLASSLENS_FRONTEND_PORT:-5173}"
API_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
APP_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}"

usage() {
  printf '%s\n' \
    'Usage: ./scripts/demo.sh <check|start|reset|status|stop>' \
    '' \
    '  check   Validate the local demo runtime without starting services.' \
    '  start   Stop only a previously tracked ClassLens demo, then start clean services.' \
    '  reset   Alias for start; persisted workflow records are preserved.' \
    '  status  Show owned process and HTTP health status.' \
    '  stop    Stop only the process groups recorded by this runner.'
}

fail() {
  printf 'ClassLens demo: %s\n' "$1" >&2
  exit 1
}

find_backend_python() {
  local candidate
  local candidates=()
  if [[ -n "${CLASSLENS_BACKEND_PYTHON:-}" ]]; then
    candidates+=("${CLASSLENS_BACKEND_PYTHON}")
  fi
  candidates+=("${BACKEND_DIR}/.venv/bin/python" "python3.11")

  for candidate in "${candidates[@]}"; do
    if command -v "${candidate}" >/dev/null 2>&1 \
      && "${candidate}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)' >/dev/null 2>&1 \
      && "${candidate}" -c 'import fastapi, google.genai, psycopg, sentence_transformers, uvicorn' >/dev/null 2>&1; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  return 1
}

require_fixture() {
  [[ -f "${PROJECT_ROOT}/$1" ]] || fail "Missing required fixture: $1"
}

check_runtime() {
  local backend_python
  backend_python="$(find_backend_python)" || fail 'Python 3.11 with backend dependencies was not found. Follow backend/README.md or set CLASSLENS_BACKEND_PYTHON.'
  command -v npm >/dev/null 2>&1 || fail 'npm is required to start the frontend.'
  command -v curl >/dev/null 2>&1 || fail 'curl is required for readiness checks.'
  command -v setsid >/dev/null 2>&1 || fail 'setsid is required to isolate the owned demo processes.'
  command -v ss >/dev/null 2>&1 || fail 'ss is required to verify that demo ports are available.'
  [[ -x "${FRONTEND_DIR}/node_modules/.bin/vite" ]] || fail 'Frontend dependencies are missing. Run npm install in frontend/.'
  [[ -f "${BACKEND_DIR}/.env" ]] || fail 'backend/.env is missing. Copy backend/.env.example and configure GEMINI_API_KEY.'
  grep -Eq '^GEMINI_API_KEY=[^[:space:]]+' "${BACKEND_DIR}/.env" \
    || fail 'GEMINI_API_KEY is not configured in backend/.env.'
  grep -Eq '^SUPABASE_DB_URL=[^[:space:]]+' "${BACKEND_DIR}/.env" \
    || fail 'SUPABASE_DB_URL is not configured in backend/.env.'

  require_fixture 'data/demo/photosynthesis_responses.csv'
  require_fixture 'data/demo/photosynthesis_follow_up_responses.csv'
  require_fixture 'data/demo/learning_materials/photosynthesis_grade7.txt'

  printf 'Runtime ready\n'
  printf 'Backend Python: %s\n' "${backend_python}"
  printf 'Frontend URL: %s\n' "${APP_URL}"
  printf 'Backend URL: %s\n' "${API_URL}"
  printf 'Gemini key: configured server-side (value hidden)\n'
  printf 'Supabase PostgreSQL: configured server-side (value hidden)\n'
}

pid_is_owned() {
  local pid="$1"
  local expected="$2"
  [[ "${pid}" =~ ^[0-9]+$ ]] || return 1
  kill -0 "${pid}" 2>/dev/null || return 1
  ps -p "${pid}" -o command= 2>/dev/null | grep -Fq -- "${expected}"
}

stop_owned_process() {
  local label="$1"
  local pid_file="$2"
  local expected="$3"
  local pid=''

  [[ -f "${pid_file}" ]] || return 0
  read -r pid < "${pid_file}" || true
  if pid_is_owned "${pid}" "${expected}"; then
    kill -TERM -- "-${pid}" 2>/dev/null || true
    for _ in {1..30}; do
      kill -0 "${pid}" 2>/dev/null || break
      sleep 0.1
    done
    if kill -0 "${pid}" 2>/dev/null; then
      printf 'ClassLens demo: %s did not stop cleanly; process %s was left running.\n' "${label}" "${pid}" >&2
      return 1
    fi
    printf 'Stopped %s\n' "${label}"
  elif [[ -n "${pid}" ]]; then
    printf 'Ignored stale %s PID %s because it is not an owned ClassLens command.\n' "${label}" "${pid}" >&2
  fi
  rm -f -- "${pid_file}"
}

stop_demo() {
  local failed=0
  stop_owned_process 'frontend' "${RUNTIME_DIR}/frontend.pid" 'npm run dev' || failed=1
  stop_owned_process 'backend' "${RUNTIME_DIR}/backend.pid" 'uvicorn app.main:app' || failed=1
  return "${failed}"
}

port_is_available() {
  local port="$1"
  [[ -z "$(ss -H -ltn "sport = :${port}" 2>/dev/null)" ]]
}

wait_for_url() {
  local label="$1"
  local url="$2"
  local attempts="${3:-120}"
  local attempt
  for ((attempt = 0; attempt < attempts; attempt++)); do
    if curl --fail --silent --show-error --max-time 1 "${url}" >/dev/null 2>&1; then
      printf '%s ready: %s\n' "${label}" "${url}"
      return 0
    fi
    sleep 0.25
  done
  return 1
}

start_demo() {
  local backend_python
  stop_demo || fail 'A previously tracked demo process could not be stopped safely.'
  check_runtime
  backend_python="$(find_backend_python)"
  port_is_available "${BACKEND_PORT}" \
    || fail "Port ${BACKEND_PORT} is already in use by an untracked process."
  port_is_available "${FRONTEND_PORT}" \
    || fail "Port ${FRONTEND_PORT} is already in use by an untracked process."

  mkdir -p -- "${RUNTIME_DIR}"
  (
    cd "${BACKEND_DIR}"
    export CLASSLENS_CORS_ORIGINS="${APP_URL},http://localhost:${FRONTEND_PORT}"
    export CLASSLENS_WARM_EMBEDDING_MODEL=1
    exec setsid "${backend_python}" -m uvicorn app.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}"
  ) >"${RUNTIME_DIR}/backend.log" 2>&1 &
  printf '%s\n' "$!" > "${RUNTIME_DIR}/backend.pid"

  (
    cd "${FRONTEND_DIR}"
    export VITE_API_URL="${API_URL}"
    exec setsid npm run dev -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}" --strictPort
  ) >"${RUNTIME_DIR}/frontend.log" 2>&1 &
  printf '%s\n' "$!" > "${RUNTIME_DIR}/frontend.pid"

  if ! wait_for_url 'Backend' "${API_URL}/health" 600; then
    stop_demo || true
    fail "Backend failed to become ready. Inspect ${RUNTIME_DIR}/backend.log."
  fi
  if ! wait_for_url 'Frontend' "${APP_URL}"; then
    stop_demo || true
    fail "Frontend failed to become ready. Inspect ${RUNTIME_DIR}/frontend.log."
  fi

  printf '\nClean ClassLens demo started.\n'
  printf 'Open: %s\n' "${APP_URL}"
  printf 'Logs: %s\n' "${RUNTIME_DIR}"
  printf 'Reset: ./scripts/demo.sh reset\n'
  printf 'Stop:  ./scripts/demo.sh stop\n'
}

show_status() {
  local backend_pid=''
  local frontend_pid=''
  [[ -f "${RUNTIME_DIR}/backend.pid" ]] && read -r backend_pid < "${RUNTIME_DIR}/backend.pid"
  [[ -f "${RUNTIME_DIR}/frontend.pid" ]] && read -r frontend_pid < "${RUNTIME_DIR}/frontend.pid"

  if pid_is_owned "${backend_pid}" 'uvicorn app.main:app'; then
    printf 'Backend process: running (PID %s)\n' "${backend_pid}"
  else
    printf 'Backend process: stopped\n'
  fi
  if curl --fail --silent --max-time 1 "${API_URL}/health" >/dev/null 2>&1; then
    printf 'Backend HTTP: healthy (%s)\n' "${API_URL}"
  else
    printf 'Backend HTTP: unavailable (%s)\n' "${API_URL}"
  fi

  if pid_is_owned "${frontend_pid}" 'npm run dev'; then
    printf 'Frontend process: running (PID %s)\n' "${frontend_pid}"
  else
    printf 'Frontend process: stopped\n'
  fi
  if curl --fail --silent --max-time 1 "${APP_URL}" >/dev/null 2>&1; then
    printf 'Frontend HTTP: healthy (%s)\n' "${APP_URL}"
  else
    printf 'Frontend HTTP: unavailable (%s)\n' "${APP_URL}"
  fi
}

case "${1:-}" in
  check)
    check_runtime
    ;;
  start|reset)
    start_demo
    ;;
  status)
    show_status
    ;;
  stop)
    stop_demo
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
