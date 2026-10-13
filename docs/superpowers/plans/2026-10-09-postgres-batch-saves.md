# PostgreSQL Save Batching Plan

**Goal:** Reduce measured network latency in PostgreSQL analysis saves without changing transaction boundaries, persisted evidence, or retry/idempotency behavior.

**Baseline:** A rollback-only benchmark of the 45-response, 4-group, 18-member synthetic analysis took 22.4 seconds against Supabase. The historical direct timing was 28.7 seconds. The current writer issues one SQL execution per response and per misconception member.

**Implementation:** Use psycopg 3 `executemany()` for student-response and misconception-member inserts. Keep both batches inside the existing `connection.transaction()` block. Leave assessment/question/group inserts and the dependency-ordered reads unchanged. Preserve each conflict clause exactly.

## Steps

- [x] Add focused store tests that prove response/member rows are sent as batches and retain conflict semantics.
- [x] Implement the two batches with no schema, API, or transaction changes.
- [x] Run focused and full backend tests (`66 passed, 1 opt-in database test skipped`). Added an idempotent retry assertion to the database-gated integration test.
- [x] Re-run the same rollback-only Supabase benchmark: 3.77-second median versus 22.38 seconds before, with zero residual assessment rows.
- [x] Update `TASKS.md`, `STATUS.md`, `docs/DATABASE.md`, `docs/DECISIONS.md`, and append a `SESSION_PROGRESS.md` milestone after final verification.
- [x] Run `git diff --check`.

## Constraints

- Do not commit benchmark rows; force a transaction rollback after the timed save.
- Do not batch across transaction boundaries or alter `ON CONFLICT` behavior.
- Do not print database URLs, credentials, student text, or full result payloads.
- Do not change Render's compute plan.
