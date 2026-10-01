# Supabase Persistence Progress

## 2026-10-02
- Read the required repository guidance and authoritative persistence/API/AI documents.
- Audited backend stores, services, routes, schemas, identifiers, frontend state, environment names, and migration directory.
- Confirmed four process-local persistence boundaries and the browser-reload pointer gap.
- Chose direct PostgreSQL, a lazy in-memory vector cache backed by persistent chunks, and local browser resume IDs.
- Re-ran the verified baseline: 55 backend tests, frontend lint, and frontend build pass.
- Added the 11-table PostgreSQL migration, direct psycopg connection boundary, PostgreSQL store/index adapters, structured database errors, and server-only configuration.
- Added stable assessment linkage, persisted analysis reads, remediation-to-analysis linkage, follow-up assessment traces, and browser reload recovery through resource IDs.
- Preserved exact cosine retrieval with a vector cache that re-embeds persisted chunks after restart.
- Expanded the suite to 58 passing backend tests; frontend lint and build continue to pass.
- Live Supabase migration/restart verification remains blocked because `SUPABASE_DB_URL` is not configured.
- Downloaded an isolated PostgreSQL 16 image, applied the migration successfully, and passed a gated integration workflow across fresh repository instances; the temporary container was removed afterward.

## Prior Milestone Progress

# Demo Reset + Browser Rehearsal Progress

## 2026-10-02
- Re-read the required repository state, backlog, latest milestone, demo guide, architecture, decisions, and planning-with-files instructions.
- Scoped this continuation to deterministic local reset/start and browser rehearsal; deployment and Supabase work remain separate decisions.
- Audited setup documentation, runtime dependencies, local browser availability, frontend API configuration, and process-local stores.
- Confirmed Firefox is available but browser automation dependencies/driver are not installed.
- Added `scripts/demo.sh` with safe runtime validation, owned-process start/reset/stop, readiness checks, status reporting, hidden-secret confirmation, and explicit fixture checks.
- Started a clean isolated stack on backend port 8000 and frontend port 4179; both readiness and runner status checks passed.
- Installed Selenium only in `/tmp` and ran headless Firefox. The first rehearsal reached and captured the real validated intake before a below-fold click timeout; the retry harness now has scroll and diagnostics.
- Exhausted three distinct Firefox activation strategies at the same enabled control. Preserved the successful intake screenshot plus failure DOM under `/tmp/classlens-demo-rehearsal`; browser completion remains explicitly unverified.
- Proved reset semantics with real state: material retrieval returned HTTP 200 before runner reset and HTTP 404 `material_not_found` afterward.
- Replaced the stale root README with current architecture, verified demo result, setup, reset/start commands, Supabase status, and verification instructions.
- Clarified three stale UI labels without changing layout or behavior; the required one-time Impeccable detector returned no findings.
- Final backend regression suite passed all 55 tests; frontend lint and production build passed; runner syntax/runtime check passed.
- Frontend secret scan, configured-origin CORS preflight, and final whitespace checks passed.
- Updated DEMO, STATUS, TASKS, backend setup, and SESSION_PROGRESS with verified reset behavior and the explicit browser-automation limitation.
