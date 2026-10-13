# Bounded backend work design

**Status:** Approved by user on 2026-10-08

## Goal

Keep the FastAPI event loop responsive while the existing synchronous CSV, embedding, grouping, retrieval, and PostgreSQL code runs. Bound worker concurrency to the existing database pool capacity, and serialize access to the process-wide Sentence Transformer model because its thread safety and memory headroom under concurrent inference have not been established.

## Current behavior

Several `async def` routes call synchronous services directly. Assessment parsing and analysis, material ingestion and retrieval, follow-up comparison, and several record reads or writes can therefore block the event loop. The Sentence Transformer instance is loaded through a one-entry `lru_cache`, but cache misses may execute the loader concurrently and `encode` has no shared lock. The psycopg pool has `max_size=5`, while its lazy `_pool` initialization has no lock. The in-memory analysis, material, remediation, and results stores already protect their dictionaries with `RLock`.

## Proposed design

Use a dedicated `ThreadPoolExecutor(max_workers=5)` for synchronous work called by async routes, matching the PostgreSQL pool's maximum connections. Offload parsing, inference, database calls, and CPU grouping so they do not run on the event loop. For remediation generation, keep the async Gemini request on the event loop and offload its synchronous persistence separately; offload remediation reads and reviews too. The implementation uses an explicit executor rather than Starlette's AnyIO pool so the five-worker bound is directly controlled by this application.

Add one process-wide `threading.Lock` around Sentence Transformer load and encode. This prevents duplicate cold model loads and overlapping inference while allowing the ASGI event loop and unrelated worker operations to continue. Add a lock around lazy psycopg pool creation so concurrent first requests cannot create multiple pools. Keep database transactions and service APIs unchanged. The existing in-memory stores retain their current locks.

Apply offloading to assessment preview/analysis/read, learning-material ingest/retrieve, follow-up result submit/read, and remediation generate-persist/read/review routes. Keep async upload reads and Gemini network calls asynchronous. The local runner's startup warmup remains synchronous during startup, before requests are served.

## Alternatives considered

- Convert route functions to synchronous FastAPI handlers. This automatically uses Starlette's thread pool, but mixed async upload/provider flows and explicit shared-worker capacity are less clear.
- Add a job queue or background-task API. This changes request/response behavior and adds operational complexity that the MVP does not need.

The selected design uses the current stack and preserves all API contracts.

## Limits and safety

- Five is a process-local worker bound chosen to match the configured database pool, not a throughput target.
- Only one embedding load/encode operation runs per process at once. Other inference requests wait in the bounded worker pool.
- This is not a cross-process limit; multiple Uvicorn workers each have their own model lock, executor, and database pool.
- No student answers, prompts, provider payloads, credentials, or database URLs are added to logs.
- No Render compute-plan change is required or implied.

## Acceptance and verification

- Analysis, material, results, and remediation routes await offloaded synchronous work without changing response schemas or domain-error behavior.
- Concurrent analysis calls serialize model load/encode, and concurrent first database use creates one pool.
- While a representative analysis is active, `/health` and a read request remain responsive.
- The existing local golden path still returns the same evidence and comparison output; database writes retain their current transaction boundaries.
- Run focused backend concurrency checks and the relevant local workflow; record stage timings and limitations in `STATUS.md` and `SESSION_PROGRESS.md`.

## Files expected to change

- `backend/app/concurrency.py`: provide the bounded executor helper.
- `backend/app/api/routes/assessments.py`, `analysis.py`, `materials.py`, `results.py`, and `remediations.py`: move synchronous operations to the worker pool.
- `backend/app/providers/embeddings/sentence_transformer.py`: serialize lazy load and inference.
- `backend/app/database.py`: serialize lazy pool initialization.
- Focused backend tests for model serialization, pool initialization, and event-loop responsiveness.
- `docs/API.md`, `docs/DECISIONS.md`, `STATUS.md`, `TASKS.md`, and `SESSION_PROGRESS.md`: record the selected concurrency behavior and verified outcome.
