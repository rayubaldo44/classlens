# Bounded Backend Work Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the FastAPI event loop responsive while synchronous parsing, inference, retrieval, and database work run within bounded worker capacity.

**Architecture:** Use a dedicated `ThreadPoolExecutor(max_workers=5)` for synchronous work called by async routes. Protect Sentence Transformer loading/encoding and lazy psycopg pool creation with process-wide locks; preserve current service APIs, responses, and DB transactions.

**Tech Stack:** Python 3.11, FastAPI, `asyncio.run_in_executor`, `concurrent.futures.ThreadPoolExecutor`, `threading.Lock`, psycopg connection pool.

**Spec:** [2026-10-08-bounded-backend-work-design.md](../specs/2026-10-08-bounded-backend-work-design.md)

## Global Constraints

- Add no runtime dependencies.
- Keep dedicated synchronous worker capacity at exactly five, matching psycopg `max_size=5`.
- Allow only one process-local Sentence Transformer load/encode operation at once.
- Preserve API schemas, domain-error envelopes, model choice, and database transaction boundaries.
- Keep Gemini network requests asynchronous and the startup warmup before serving requests.
- Do not log student answers, prompts, provider payloads, credentials, or database URLs.
- The limit is per process; do not claim cross-process inference or connection coordination.
- Do not change Render's plan or require paid infrastructure.

## Review Focus

- Concurrent first embedding calls must load one model and never overlap `encode`; test with a fake model and synchronized worker threads.
- Concurrent first database access must construct only one pool; test with a fake `ConnectionPool` constructor and concurrent calls.
- Worker exceptions must still reach FastAPI's existing structured handlers; assert the existing JSON error envelope from an analysis failure raised in the worker.
- A slow analysis must not block `/health` or an independent read; block a fake embed operation and issue concurrent requests.
- Concurrent synchronous work must remain bounded at five workers.

## File map

- `backend/app/concurrency.py`: provide the bounded five-worker executor.
- `backend/app/database.py`: lock lazy psycopg pool initialization.
- `backend/app/providers/embeddings/sentence_transformer.py`: lock model load and encode.
- Backend route modules: offload synchronous endpoint work without changing request/response schemas.
- `backend/app/services/remediation.py`: offload its persistence call after async Gemini generation.
- `backend/tests/test_concurrency.py`: focused thread-safety and event-loop responsiveness checks.
- `docs/API.md`, `docs/DECISIONS.md`, `STATUS.md`, `TASKS.md`, `SESSION_PROGRESS.md`: record implemented, verified behavior.

### Task 1: Serialize shared model and pool initialization

**Files:**
- Modify: `backend/app/providers/embeddings/sentence_transformer.py`
- Modify: `backend/app/database.py`
- Create: `backend/tests/test_concurrency.py`

**Interfaces:**
- `SentenceTransformerEmbeddingService.embed(texts: list[str]) -> list[list[float]]` remains unchanged.
- `Database._get_pool()` remains unchanged to callers and returns one shared pool instance.

- [x] **Step 1: Add failing tests** `test_embedding_load_and_encode_are_serialized` and `test_database_pool_is_created_once_under_concurrency` in `backend/tests/test_concurrency.py`. Use fake loaders/model and fake pool constructor; use a `ThreadPoolExecutor` barrier to call each shared object concurrently. Assert one loader/pool construction and maximum active embedding count of one.
- [x] **Step 2: Run the two tests and confirm they fail**

Run from `backend/`: `pytest tests/test_concurrency.py -q`

Expected: both tests expose the currently unguarded concurrent initialization/inference behavior.

- [x] **Step 3: Add a module-level `threading.Lock` around model loading and `encode`**, holding it for both operations in `embed`; add a lock and double-check around psycopg `ConnectionPool` construction in `Database._get_pool`.
- [x] **Step 4: Run the focused tests and confirm they pass**

Run from `backend/`: `pytest tests/test_concurrency.py -q`

Expected: both pass, with one model load, serialized encodes, and one pool instance.

### Task 2: Offload synchronous route work with bounded worker capacity

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/routes/assessments.py`
- Modify: `backend/app/api/routes/analysis.py`
- Modify: `backend/app/api/routes/materials.py`
- Modify: `backend/app/api/routes/results.py`
- Modify: `backend/app/api/routes/remediations.py`
- Modify: `backend/app/services/remediation.py`
- Modify: `backend/tests/test_concurrency.py`

**Interfaces:**
- Route paths, request models, response models, and service function signatures remain unchanged.
- `run_in_worker` uses the bounded executor for synchronous callables; Gemini's async call remains directly awaited.

- [x] **Step 1: Add failing checks** for model-load/encode serialization and single database-pool initialization in `backend/tests/test_concurrency.py`.
- [x] **Step 2: Run the thread-safety checks and confirm they fail before the locks are added**

Run from `backend/`: `pytest tests/test_concurrency.py -q`

Expected: responsiveness fails, the worker error envelope or five-token lifecycle check fails on the current implementation.

- [x] **Step 3: Add the five-worker executor and offload synchronous route work** in the route modules listed above. In `generate_grounded_remediation`, await `run_in_worker(store.save, record)` after the asynchronous Gemini call.
- [x] **Step 4: Run automated route/error-envelope checks.** A short test-only event-loop heartbeat allows executor callbacks to run with the existing in-process ASGI tests; health, preview, analysis, and worker error responses pass.

Run from `backend/`: `pytest tests/test_concurrency.py tests/test_health.py tests/test_assessment_intake.py -q`

Expected: health and demo preview complete while analysis is blocked; worker error envelope is preserved and lifespan configures five tokens.

### Task 3: Verify the golden path and update project records

**Files:**
- Modify: `docs/API.md`
- Modify: `docs/DECISIONS.md`
- Modify: `STATUS.md`
- Modify: `TASKS.md`
- Modify: `SESSION_PROGRESS.md`

- [x] **Step 1: Run concurrency and affected backend coverage.** `pytest -q` passed: 65 passed, 1 opt-in database test skipped.

Run from `backend/`: `pytest -q`

Expected: all configured backend tests pass; the opt-in PostgreSQL test may skip only when `CLASSLENS_TEST_DATABASE_URL` is absent.

- [x] **Step 2: Run the local analysis smoke** using `./scripts/demo.sh reset`; confirmed the 45-response demo analysis returned four evidence groups and concurrent health remained responsive. Existing result-flow tests passed; the opt-in database test was skipped in this run.
- [x] **Step 3: Document the five-worker process-local bound and one-at-a-time model access** in `docs/API.md` and record the implementation decision in `docs/DECISIONS.md`. Update `STATUS.md`, keep the unfinished task unchecked in `TASKS.md`, and append the verified partial milestone to `SESSION_PROGRESS.md`.
- [x] **Step 4: Run `git diff --check`**

Expected: no whitespace errors; unrelated worktree changes remain untouched.
