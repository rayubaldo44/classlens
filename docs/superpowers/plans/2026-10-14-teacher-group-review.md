# Teacher Group Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent teacher rename, merge, dismiss, and restore actions for misconception groups while preserving immutable detected evidence and append-only review history.

**Architecture:** Keep `AnalysisResponse` immutable and build reviewed groups through a `GroupReviewService` over an original analysis plus a persisted materialized review state. Persist every change as an append-only event in the same transaction, then make retrieval, remediation, results, and the frontend resolve reviewed group IDs through this service.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, psycopg/PostgreSQL, React 19, strict TypeScript, Playwright Chromium.

**Spec:** `docs/superpowers/specs/2026-10-14-teacher-group-review-design.md`

## Global Constraints

- Do not mutate `analysis_runs.result_json`, `misconception_groups`, `misconception_members`, or source responses.
- Merge only active groups from the same analysis and question; never fabricate coherence or representative evidence.
- Lock affected review actions after any linked remediation exists.
- Preserve the existing ordinary-upload golden path, structured error envelope, and teacher authority.
- Add no dependency unless the existing standard library and project stack cannot implement the requirement.
- Implement with failing tests first and use migration `002_teacher_group_reviews.sql` additively.

## Review Focus

- Cross-question/cross-analysis group IDs: reject with HTTP 409 and leave state/history unchanged (Task 2 tests).
- Concurrent or stale review actions: serialize per analysis, reject stale source state, and do not record an event for a rejected action (Tasks 2–3 tests).
- Review after remediation exists: reject rename/merge/dismiss/restore for affected evidence (Task 4 tests).
- Merged evidence semantics: union members exactly once, retain source IDs, copy only original representative text, and return null coherence (Task 2 tests).
- Reload with stale reviewed group ID: show recovery UI and retain the last valid analysis rather than selecting another group (Task 5 tests).

---

### Task 1: Review schemas, store protocol, and additive migration

**Files:**
- Create: `database/migrations/002_teacher_group_reviews.sql`
- Create: `backend/app/schemas/group_reviews.py`
- Create: `backend/app/providers/group_review_store.py`
- Modify: `backend/app/providers/postgres.py`
- Test: `backend/tests/test_group_reviews.py`
- Test: `backend/tests/test_postgres_integration.py`

**Interfaces:**
- Produces: `GroupReviewActionRequest`, `ReviewedMisconceptionGroup`, `GroupReviewEvent`, `GroupReviewResponse`.
- Produces: `GroupReviewStore.get(analysis_id)`, `GroupReviewStore.save(analysis_id, previous_state, next_state, event)` with in-memory and PostgreSQL implementations.

- [ ] Write failing schema/store tests for defaults, immutable event copies, ordered history, and transactional state/event persistence.
- [ ] Run `.venv/bin/python -m pytest tests/test_group_reviews.py -v` from `backend/`; expect failures for missing modules.
- [ ] Add the two tables, foreign keys, action/status checks, timestamps, indexes, and RLS enablement in migration 002.
- [ ] Implement Pydantic schemas and the store protocol/test double; keep JSON state validation at the provider boundary.
- [ ] Implement PostgreSQL reads and one-transaction state/event writes without modifying analysis rows.
- [ ] Extend the opt-in PostgreSQL integration test to apply migration 002 and verify rollback plus restart reads.
- [ ] Run the focused unit tests and database integration test; expect passes.
- [ ] Commit: `feat: add persistent group review records`.

### Task 2: Deterministic review service

**Files:**
- Create: `backend/app/services/group_reviews.py`
- Modify: `backend/app/schemas/group_reviews.py`
- Test: `backend/tests/test_group_reviews.py`

**Interfaces:**
- Consumes: immutable `AnalysisSnapshot` and `GroupReviewStore` from Task 1.
- Produces: `get_group_reviews(analysis_id, analysis_store, review_store) -> GroupReviewResponse`.
- Produces: `apply_group_review(analysis_id, request, analysis_store, review_store, remediation_store) -> GroupReviewResponse`.
- Produces: `resolve_reviewed_group(analysis_id, reviewed_group_id, analysis_store, review_store) -> ReviewedMisconceptionGroup`.

- [ ] Write failing tests for initial overlay, rename, dismiss/restore, same-question merge, deterministic merged ID, exact member union, copied representatives, null merged coherence, and ordered events.
- [ ] Add failure tests for unknown, duplicate, cross-question, already dismissed/merged, stale, and malformed actions; assert state and event count remain unchanged.
- [ ] Run the focused tests; expect service/import failures.
- [ ] Implement pure overlay construction and action validation before any store write.
- [ ] Generate event/reviewed IDs from analysis ID, action, sorted sources, and next event sequence; never use label text as evidence identity.
- [ ] Serialize in-process writes per analysis in the store/service boundary and use expected previous state for database conflict detection.
- [ ] Run `tests/test_group_reviews.py`; expect passes.
- [ ] Commit: `feat: implement teacher group review actions`.

### Task 3: Group review API

**Files:**
- Create: `backend/app/api/routes/group_reviews.py`
- Modify: `backend/app/main.py`
- Modify: `docs/API.md`
- Test: `backend/tests/test_group_reviews.py`

**Interfaces:**
- Consumes: Task 2 service functions.
- Produces: GET/POST `/api/v1/assessments/analyses/{analysis_id}/group-reviews`.

- [ ] Write failing ASGI tests for initial GET, every action, event history, unknown analysis/group, invalid body, stale state, and structured 404/409 errors.
- [ ] Run the focused tests; expect route-not-found failures.
- [ ] Add the router and exception mapping without changing existing analysis endpoints.
- [ ] Document exact request/response/error contracts and the immutable-analysis boundary.
- [ ] Run the focused tests and `tests/test_health.py`; expect passes.
- [ ] Commit: `feat: expose group review API`.

### Task 4: Canonical downstream use of reviewed groups

**Files:**
- Modify: `backend/app/schemas/materials.py`
- Modify: `backend/app/schemas/remediations.py`
- Modify: `backend/app/schemas/results.py`
- Modify: `backend/app/services/material_retrieval.py`
- Modify: `backend/app/services/remediation.py`
- Modify: `backend/app/services/results.py`
- Modify: `backend/app/providers/postgres.py`
- Modify: `database/migrations/002_teacher_group_reviews.sql`
- Test: `backend/tests/test_material_retrieval.py`
- Test: `backend/tests/test_remediation.py`
- Test: `backend/tests/test_results.py`
- Test: `backend/tests/test_group_reviews.py`

**Interfaces:**
- Consumes: `resolve_reviewed_group` from Task 2.
- Produces: canonical retrieval/generation/comparison context keyed by `reviewed_group_id` and preserving `source_group_ids` in saved provenance/trace.

- [ ] Write failing tests proving renamed labels reach prompts, merged evidence is the exact source union, dismissed groups are rejected, and post-remediation review actions return 409.
- [ ] Write result tests proving member-overlap comparison uses the merged baseline union and records reviewed/source IDs without altering original groups.
- [ ] Run the four focused test files; expect contract failures.
- [ ] Extend retrieval, remediation, intervention source provenance, and comparison schemas with reviewed/source identifiers.
- [ ] Resolve reviewed evidence server-side before retrieval/generation/results; compare browser data only as an assertion.
- [ ] Reject group-review changes once any affected remediation exists.
- [ ] Run the focused tests; expect passes.
- [ ] Commit: `feat: preserve reviewed group provenance downstream`.

### Task 5: Frontend contracts, recovery, and review state

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/contracts.ts`
- Modify: `frontend/src/workflowStorage.ts`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/tests/contracts.test.ts`
- Test: `frontend/tests/workflowStorage.test.ts`

**Interfaces:**
- Consumes: Task 3 API and Task 4 reviewed group identifiers.
- Produces: `getGroupReviews`, `applyGroupReview`, strict runtime guards, and restored reviewed-group selection.

- [ ] Write failing contract tests for reviewed groups/events, nullable coherence, malformed source IDs, and invalid histories.
- [ ] Write failing recovery tests for valid reviewed IDs and stale/dismissed reviewed IDs.
- [ ] Run `npm test`; expect failures.
- [ ] Add client types, guards, API calls, and workflow pointer validation.
- [ ] Fetch group review state after analysis load/restore before resolving the selected group; route stale selections through existing visible recovery behavior.
- [ ] Run `npm test`; expect passes.
- [ ] Commit: `feat: load reviewed misconception groups`.

### Task 6: Teacher review controls and browser coverage

**Files:**
- Create: `frontend/src/GroupReviewPanel.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/WorkspacePolish.css`
- Modify: `frontend/tests/e2e/golden-path.spec.ts`
- Create: `frontend/tests/e2e/group-review.spec.ts`

**Interfaces:**
- Consumes: Task 5 client functions and reviewed group types.
- Produces: accessible rename/merge/dismiss/restore controls and history display.

- [ ] Write a failing Playwright test covering rename → reload, two-group merge with exact union count, dismiss/restore, history order, and locked controls after generation.
- [ ] Add a failure-path test for a controlled 409 that preserves the current visible state and shows an actionable message.
- [ ] Run the focused Playwright spec; expect failures before UI implementation.
- [ ] Implement the review panel with native form controls, explicit confirmation copy, keyboard operation, and a collapsed dismissed section.
- [ ] Show source group IDs and “Coherence not recalculated” on merged group details; never display a derived numeric coherence.
- [ ] Update the existing golden path to select the reviewed active group without changing the ordinary no-review path.
- [ ] Run focused Playwright, unit tests, lint, and build; expect passes.
- [ ] Commit: `feat: add teacher misconception review controls`.

### Task 7: Full verification and authoritative documentation

**Files:**
- Modify: `docs/PRODUCT.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/AI_PIPELINE.md`
- Modify: `docs/DATABASE.md`
- Modify: `docs/DECISIONS.md`
- Modify: `STATUS.md`
- Modify: `TASKS.md`
- Modify: `SESSION_PROGRESS.md`

**Interfaces:**
- Consumes: completed Tasks 1–6.
- Produces: verified current-state documentation and final task closure.

- [ ] Apply migrations 001 and 002 to an ephemeral PostgreSQL instance and run the opt-in database integration test.
- [ ] Run `.venv/bin/python -m pytest` from `backend/`; require zero failures.
- [ ] Run `npm test`, `npm run lint`, `npm run build`, and `npm run test:e2e` from `frontend/`; require zero failures.
- [ ] Run `git diff --check` and the documentation relative-link check.
- [ ] Update authoritative docs with the final verified behavior, limits, migration, API, and evidence/provenance semantics.
- [ ] Mark the task complete only after restart/reload and post-remediation locking pass end to end; append the milestone to `SESSION_PROGRESS.md` and sync Obsidian.
- [ ] Commit: `docs: record teacher group review workflow`.
