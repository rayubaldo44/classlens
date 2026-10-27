# Batched Misconception Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draft concise, evidence-referenced labels for all baseline misconception groups in one bounded Gemini call while persisting deterministic fallback labels whenever interpretation fails.

**Architecture:** Keep embedding/grouping pure and deterministic, version its analysis identity for the new interpretation contract, then run an optional batch-interpreter before first persistence. Validate the entire structured batch against exact group and representative-response IDs, save one canonical snapshot, and derive UI label provenance without changing review-state storage.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, Google Gen AI SDK, psycopg/PostgreSQL, React 19, TypeScript, Node test runner, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-26-batched-misconception-labels-design.md`

## Global Constraints

- Gemini must not create, split, merge, score, or remove deterministic evidence groups.
- One batch covers every group; any provider or validation failure falls back for the whole batch.
- Label generation gets one attempt, a default 12,000 ms total budget, temperature `0.1`, and `1,024` output tokens.
- Existing `not_requested` records remain readable; new analysis IDs include `misconception_labels_v1`.
- Persisted `fallback` snapshots are stable and do not automatically spend Gemini quota again.
- Database failures keep their existing structured failure behavior and must not be absorbed as label fallback.
- No new runtime dependency or SQL migration.

## Review Focus

- Prompt-injection text inside a representative answer must remain data and must not alter the requested schema or instructions; pin this in Task 1 prompt tests.
- Duplicate, missing, extra, or cross-group evidence IDs must reject the whole batch; pin these in Task 1 service tests.
- Empty, whitespace-padded, multiline, too-short, and overlong labels must fail validation rather than leak into persisted/UI state; pin these in Task 1 schema tests.
- Repeated and concurrent identical analyses must return the canonical stored wording and avoid repeat calls once stored; pin this in Task 3 route tests.
- Renamed or merged groups must not retain an AI-drafted badge after teacher intervention; pin this in Task 4 browser tests.

---

### Task 1: Structured interpretation contract, prompt, and all-or-nothing service

**Files:**
- Create: `backend/app/schemas/interpretation.py`
- Create: `backend/app/prompts/misconception_labels.py`
- Create: `backend/app/services/misconception_interpretation.py`
- Create: `backend/tests/test_misconception_interpretation.py`
- Modify: `backend/app/schemas/analysis.py`

**Interfaces:**
- Produces: `GroupLabelDraft(group_id: str, label: str, evidence_student_ids: list[str])`
- Produces: `GroupLabelBatch(labels: list[GroupLabelDraft])`
- Produces: `build_misconception_labels_prompt(result: AnalysisResponse) -> str`
- Produces: `async interpret_misconception_groups(result: AnalysisResponse, llm_service: LLMService) -> AnalysisResponse`
- `interpret_misconception_groups` returns a deep copy with every group `completed` or every group `fallback`; it never mutates evidence fields.

- [x] **Step 1: Write failing schema and prompt tests**

Add focused tests proving strict extra-field rejection; trimmed single-line 5–120 character labels; one-to-three unique evidence IDs; exact question/correct-answer/group/representative content; the `misconception_labels_v1` instruction; and explicit treatment of student answers as untrusted data.

- [x] **Step 2: Run the focused tests and confirm RED**

Run: `cd backend && .venv/bin/python -m pytest tests/test_misconception_interpretation.py -q`

Expected: collection/import failures because the contract, prompt, and service do not exist.

- [x] **Step 3: Implement strict schemas and prompt construction**

Use Pydantic `extra="forbid"` and field/model validators. Serialize a packet containing only analysis/group context required by the spec; do not include non-representative member answers.

- [x] **Step 4: Add failing all-or-nothing service tests**

Cover valid reordered output, missing group, duplicate group, unknown group, cross-group representative ID, duplicate evidence ID, malformed label, provider-not-configured, provider timeout, and proof that group IDs/members/responses/scores/counts are unchanged.

- [x] **Step 5: Implement the interpretation service minimally**

Validate exact group coverage and per-group representative references after the provider returns. Catch only `LLMProviderError` and interpretation-output validation errors; log sanitized codes and convert all source groups to fallback. Let unrelated programming and database errors propagate.

- [x] **Step 6: Run focused tests and confirm GREEN**

Run: `cd backend && .venv/bin/python -m pytest tests/test_misconception_interpretation.py -q`

- [x] **Step 7: Commit Task 1**

```bash
git add backend/app/schemas/analysis.py backend/app/schemas/interpretation.py backend/app/prompts/misconception_labels.py backend/app/services/misconception_interpretation.py backend/tests/test_misconception_interpretation.py
git commit -m "feat: validate batched misconception labels"
```

### Task 2: Bounded Gemini batch generation

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Modify: `backend/app/providers/llm/base.py`
- Modify: `backend/app/providers/llm/gemini.py`
- Modify: `backend/tests/test_remediation.py`
- Modify: `backend/tests/test_misconception_interpretation.py`

**Interfaces:**
- `LLMSettings.label_total_budget_ms: int`
- `LLMService.generate_group_labels(prompt: str) -> GroupLabelBatch`
- `GeminiLLMService(..., label_total_budget_ms: int = 12_000)`

- [x] **Step 1: Write failing config and provider tests**

Assert the default and 1,000–30,000 ms bounds; one Gemini SDK call; `GroupLabelBatch` response schema; temperature `0.1`; max output `1_024`; outer timeout; no retry on transient errors; malformed output normalization to `LLMProviderError`; and unchanged remediation retry/budget behavior.

- [x] **Step 2: Run the focused tests and confirm RED**

Run: `cd backend && .venv/bin/python -m pytest tests/test_misconception_interpretation.py tests/test_remediation.py -q`

- [x] **Step 3: Implement the provider method and minimal shared helpers**

Share client initialization and unsupported-schema-field cleanup. Keep remediation generation on its existing two-attempt path; the label method uses a separate one-attempt path under `asyncio.timeout(label_total_budget_ms / 1000)`.

- [x] **Step 4: Run focused tests and confirm GREEN**

Run: `cd backend && .venv/bin/python -m pytest tests/test_misconception_interpretation.py tests/test_remediation.py -q`

- [x] **Step 5: Commit Task 2**

```bash
git add backend/app/config.py backend/.env.example backend/app/providers/llm/base.py backend/app/providers/llm/gemini.py backend/tests/test_remediation.py backend/tests/test_misconception_interpretation.py
git commit -m "feat: generate misconception labels with Gemini"
```

### Task 3: Versioned baseline orchestration and canonical persistence

**Files:**
- Modify: `backend/app/services/misconception_analysis.py`
- Modify: `backend/app/api/routes/analysis.py`
- Modify: `backend/app/providers/analysis_store.py`
- Modify: `backend/tests/test_misconception_analysis.py`
- Modify: `backend/tests/test_concurrency.py`
- Modify: `backend/tests/test_persistence.py`
- Modify: `backend/tests/test_postgres_integration.py`

**Interfaces:**
- `ANALYSIS_CONTRACT_VERSION = "misconception_labels_v1"` participates in `_analysis_id` only; group IDs remain unchanged.
- Both baseline routes depend on `get_llm_service` and share one private async orchestration helper.
- `InMemoryAnalysisStore.save` preserves create-if-absent behavior to match PostgreSQL for canonical-winner tests.

- [x] **Step 1: Write failing identity and route tests**

Assert the version changes the analysis ID but not group IDs/evidence; no-group analysis skips Gemini; existing canonical analysis skips Gemini; valid output persists `completed`; provider failure persists and returns `fallback`; and post-save reload returns the canonical winner.

- [x] **Step 2: Run the focused tests and confirm RED**

Run: `cd backend && .venv/bin/python -m pytest tests/test_misconception_analysis.py tests/test_concurrency.py tests/test_persistence.py -q`

- [x] **Step 3: Implement shared baseline orchestration**

Keep parse/embedding/grouping in the worker pool, perform canonical lookup outside the optional-fallback boundary, call interpretation only for non-empty new baseline analyses, save, reload, and fail closed if persistence unexpectedly cannot reload.

- [x] **Step 4: Add and pass concurrent/repeated canonical tests**

Use a create-if-absent in-memory fake with two different valid label batches. Assert both responses converge on the stored winner and later requests do not invoke the provider.

- [x] **Step 5: Run backend persistence coverage**

Run: `cd backend && .venv/bin/python -m pytest tests/test_misconception_analysis.py tests/test_concurrency.py tests/test_persistence.py -q`

If `CLASSLENS_TEST_DATABASE_URL` is configured, also run: `cd backend && CLASSLENS_RUN_DB_TESTS=1 .venv/bin/python -m pytest tests/test_postgres_integration.py -q`

- [x] **Step 6: Commit Task 3**

```bash
git add backend/app/services/misconception_analysis.py backend/app/api/routes/analysis.py backend/app/providers/analysis_store.py backend/tests/test_misconception_analysis.py backend/tests/test_concurrency.py backend/tests/test_persistence.py backend/tests/test_postgres_integration.py
git commit -m "feat: persist canonical interpreted analyses"
```

### Task 4: Frontend contracts and honest label provenance

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/contracts.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/tests/contracts.test.ts`
- Modify: `frontend/tests/e2e/golden-path.spec.ts`
- Modify: `frontend/tests/e2e/group-review.spec.ts`

**Interfaces:**
- `MisconceptionGroup.interpretation_status: 'not_requested' | 'completed' | 'fallback'`
- Add a pure label-provenance helper local to `App.tsx` or a focused module if tests require direct import.

- [x] **Step 1: Write failing contract tests**

Accept all three known statuses, reject unknown statuses, and retain recursive validation of group content.

- [x] **Step 2: Write failing browser assertions**

Verify `completed` renders `AI-drafted label · teacher review needed`, `fallback` renders `Detected pattern · AI label unavailable`, legacy `not_requested` remains honest, and rename/merge renders `Teacher-reviewed label` rather than AI provenance.

- [x] **Step 3: Run frontend focused tests and confirm RED**

Run: `cd frontend && npm test`

Run the narrow Playwright specs with the repository's existing command/filter.

- [x] **Step 4: Implement status guards and provenance rendering**

For a reviewed group, classify as teacher-reviewed when it merges multiple sources or its display label differs from its sole immutable source label. Otherwise map the immutable source's `interpretation_status` to the corresponding badge.

- [x] **Step 5: Run focused frontend tests and confirm GREEN**

Run: `cd frontend && npm test`

Run: `cd frontend && npx playwright test tests/e2e/golden-path.spec.ts tests/e2e/group-review.spec.ts --project=chromium`

- [x] **Step 6: Commit Task 4**

```bash
git add frontend/src/api/client.ts frontend/src/api/contracts.ts frontend/src/App.tsx frontend/tests/contracts.test.ts frontend/tests/e2e/golden-path.spec.ts frontend/tests/e2e/group-review.spec.ts
git commit -m "feat: show misconception label provenance"
```

### Task 5: Authoritative documentation and final verification

**Files:**
- Modify: `docs/AI_PIPELINE.md`
- Modify: `docs/API.md`
- Modify: `docs/PRODUCT.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/DECISIONS.md`
- Modify: `STATUS.md`
- Modify: `TASKS.md`
- Modify: `SESSION_PROGRESS.md`
- Modify: `docs/superpowers/plans/2026-10-26-batched-misconception-labels.md`

**Interfaces:** None; documentation must describe only verified behavior.

- [x] **Step 1: Run the complete affected verification gate**

Run:

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm test
cd frontend && npm run lint
cd frontend && npm run build
cd frontend && npx playwright test --project=chromium
git diff --check
```

Run the PostgreSQL integration separately when its disposable/configured URL is available. Do not use production data for destructive tests.

- [x] **Step 2: Perform one live local analysis check**

With the restored server-side configuration, reset the runner, verify `/ready`, request the synthetic baseline, confirm all four groups are either a fully valid `completed` batch or a fully deterministic `fallback` batch, reload group reviews, and confirm exact evidence remains unchanged. Record provider behavior honestly; do not require live Gemini success for deterministic-path correctness.

- [x] **Step 3: Update authoritative documentation**

Record prompt version, one-call boundary, structured evidence-reference validation, 12-second no-retry budget, stable fallback, identity version, statuses, UI provenance, and verified checks. Add an accepted decision and check the P0 backlog item only after all acceptance criteria pass.

- [x] **Step 4: Append one milestone entry**

Append—not rewrite—a `SESSION_PROGRESS.md` entry containing attempts, significant files, completed behavior, verification, problems, decisions, remaining work, and recommended next step.

- [x] **Step 5: Commit Task 5**

```bash
git add docs/AI_PIPELINE.md docs/API.md docs/PRODUCT.md docs/ARCHITECTURE.md docs/DECISIONS.md STATUS.md TASKS.md SESSION_PROGRESS.md docs/superpowers/specs/2026-10-26-batched-misconception-labels-design.md docs/superpowers/plans/2026-10-26-batched-misconception-labels.md
git commit -m "docs: record batched misconception labels"
```

- [x] **Step 6: Request final code review and address Important findings**

Review the complete feature diff against this spec, rerun affected checks after any correction, and do not merge or claim completion with unresolved Important findings.
