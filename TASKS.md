# ClassLens Backlog

**Last reorganized:** 2026-10-08 (Asia/Manila)

Tasks are grouped by priority, then category. Within each category, work from top to bottom. Checked items reflect previously verified work in [STATUS.md](STATUS.md); this reorganization does not claim new application or hosted verification. Stack-review recommendations are unchecked proposed work, not completed capabilities or approved technology migrations.

## Priority guide

| Priority | Purpose | Start condition |
|---|---|---|
| P0 | Finish and rehearse the existing hackathon golden path | Work now; prioritize hosted verification and rehearsal |
| P1 | Reliability, testing, and optional product improvements | After the P0 demo gates pass |
| P2 | Real-school pilot safeguards and later product work | After the demo; safeguards must pass before real student data |

**Next action:** preserve the verified local presentation setup. Hosted analysis stays deferred until a 2 GB Render plan is affordable; after the demo, obtain educator review of the embedding regression cases before tuning grouping behavior.

## P0 — demo critical

### Deployment and hosted verification

Depends on: the implemented local workflow, provisioned Vercel/Render services, and configured PostgreSQL persistence.

- [ ] Finish deploying the intended frontend/backend revisions with server-side secrets and matching `VITE_API_URL` / `CLASSLENS_CORS_ORIGINS`; verify direct workflow-route loads on Vercel.
- [ ] Complete the hosted browser golden path: ordinary CSV upload → analysis/evidence → teacher-material upload/retrieval → live Gemini draft → teacher edit/approval → follow-up upload → results.
- [ ] Verify hosted reload recovery for analysis, review state, and results, plus actionable backend/database/provider failure states.
- [ ] Inspect the actual Render plan, memory usage, model cache behavior, and cold/warm latency. If idle shutdown or insufficient RAM prevents a reliable demo, select suitable always-on capacity before deploying a configuration change.

Current evidence (2026-10-08): Vercel direct workflow routes are fixed and live. Commit `5115e5d` also deployed the verified local reload-recovery revision; all six workflow routes return HTTP 200. The hosted browser reaches and validates the ordinary 45-row CSV, but analysis is blocked: direct analysis attempts returned empty 502 responses after about 80–122 seconds and temporarily left Render at 503 `hibernate-wake-error`. Render logs show three analysis-time process restarts shortly after the Hugging Face model request, with no completed analysis response. The same local model/encode path peaked at about 1.11 GB RSS. Inspect the active Render plan and memory graph in the dashboard and, with billing approval, use at least the 2 GB `1c-2g` web-service plan before rerunning the smoke. `HF_TOKEN` may improve model-download reliability but is not a substitute for sufficient RAM.

Funding decision (2026-10-08): the paid Render upgrade is deferred. Keep the hosted tasks open and use the verified local runner for the demo; do not spend time repeatedly exercising the known 512 MB failure.

**Acceptance:** the production frontend completes the workflow against Render/PostgreSQL; health and CORS probes alone do not close deployment. Use [docs/DEMO.md](docs/DEMO.md) for the authoritative procedure and expected results.

### Demo operations and fallback

Depends on: hosted verification for the hosted rehearsal; the existing local runner remains available for local rehearsal.

- [ ] Warm the embedding model and teacher-material retrieval on the judging machine and hosted service; verify Gemini configuration/quota and database reachability before presenting.
  - Local readiness refreshed 2026-10-14: `/ready` reported database and embedding model ready; two live Gemini evaluation calls passed in 5.145s and 8.700s. Hosted warming remains deferred with the unfunded Render upgrade.
- [x] Complete the documented three-minute click path twice on the judging machine/network, including loading and meaningful empty/error states; record timings and any failures. (2026-10-14)
  - Automated live-path evidence (2026-10-13): two independent local Chromium runs after runner resets completed in 40.0 and 38.3 seconds against Supabase and Gemini, including reload recovery. Human-operated rehearsals with narration remain required.
  - Human rehearsal evidence (2026-10-14): run 1 passed the intended pattern-1 path in 1:31. A separate 1:20 attempt selected pattern 2 and correctly ended with insufficient follow-up evidence.
  - Final human rehearsal evidence (2026-10-14): a second intended pattern-1 run passed in 1:22.4; the captured Results screen showed 9/43 before and 3/43 after with the API connected.
- [x] Prepare an explicit, honestly labeled recording or previously generated artifact for live Gemini unavailability. Keep live provider failure visible and never switch silently to fabricated output. See [the verified local-run fallback](docs/DEMO_FALLBACK.md).
- [x] Run the [pre-demo checklist](docs/DEMO.md#pre-demo-checklist) after the final deployment and rehearsal. (2026-10-14)
  - Dependencies and rehearsals passed. The upload screen, demo-file folder, and labeled fallback were opened; notification banners were disabled; and the presenter confirmed projector readability.

**Acceptance:** two repeatable timed rehearsals, an accessible labeled fallback, and a completed checklist. Preserve the existing safe, non-destructive reset procedure.

### AI interpretation

Depends on: persisted question-specific groups and exact representative evidence. Prioritize hosted verification and rehearsal before adding another provider-dependent step.

- [ ] Use the LLM to draft concise potential-misconception labels from question context, expected answer, and supplied evidence; validate evidence references and keep deterministic groups visible when interpretation fails.

**Acceptance:** labels remain provisional and teacher-verifiable; failures invent no evidence. Current generic provisional labels remain the verified implementation until this task passes. See [docs/AI_PIPELINE.md](docs/AI_PIPELINE.md).

## P1 — reliability and improvements after P0

### Runtime and deployment reproducibility

Depends on: a recorded baseline of the currently verified environment and latency.

- [x] Declare compatible Node and Python versions and lock the tested backend dependency resolution, including CPU-only PyTorch installation.
- [ ] Make embedding-model files available reproducibly during deployment and warm the model before readiness; avoid a first-user download dependency.
- [x] Add a readiness check that distinguishes application liveness from model/database readiness without exposing secrets or consuming Gemini quota on each probe.

Current evidence (2026-10-08): the existing embedding model is pinned to cached Hugging Face commit `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. The local demo runner warms it before health responds, and `/ready` checks PostgreSQL plus loaded-model state without calling Gemini. Hosted startup warming remains off because measured local peak RSS is about 1.11 GB and the current Render service is 512 MB; the hosting part of the model-cache task stays open until adequate memory is available.

**Acceptance:** a clean environment reproduces the verified runtime and serves a warm request; document any accepted configuration change in [docs/TECH_STACK.md](docs/TECH_STACK.md) and [docs/DECISIONS.md](docs/DECISIONS.md).

### API performance and workload limits

Depends on: stage timing measurements; benchmark before selecting an optimization.

- [x] Add structured request/stage timings for parsing, embedding, grouping, retrieval, database persistence, and Gemini calls. Record sanitized errors and token usage without student response text.
- [x] Offload bounded synchronous inference and database work from `async` route handlers; limit concurrent inference and verify cache/model thread safety and API responsiveness during analysis (2026-10-08).
- [x] Investigate slow database saves and replace individual inserts with transaction-preserving batches where measurements justify it; compare before/after timing and verify atomicity/idempotency (2026-10-09).
- [x] Add explicit CSV row and eligible-response-per-question limits, with actionable errors, to bound pairwise grouping work (2026-10-13).
- [x] Define a total generation/request time budget that includes provider retries; add frontend timeout/retry behavior that preserves valid state and avoids duplicate drafts (2026-10-13).

**Acceptance:** representative workloads stay within documented limits, concurrent health/read requests remain responsive, and optimization preserves evidence, transactions, and deterministic results.

### Evidence integrity and API contracts

Depends on: existing persisted analysis/groups and material chunks.

- [x] Load canonical question/group evidence and teacher passages server-side before generation; validate analysis/group/material/chunk relationships and reject altered or mismatched browser snapshots before calling Gemini (2026-10-13).
- [x] Strengthen frontend runtime validation of nested API responses and saved workflow pointers; show actionable errors for malformed data (2026-10-13).

**Acceptance:** tampered text or identifiers cannot become trusted generation context; existing valid workflows and immutable source snapshots remain recoverable. See [docs/API.md](docs/API.md) and [docs/DATABASE.md](docs/DATABASE.md).

### Testing and AI evaluation

Depends on: reproducible runtime; use an isolated test database for database integration.

- [x] Add CI for frontend tests/lint/build and backend tests, with a separately configured PostgreSQL integration job. (2026-10-13)
- [x] Add an automated browser golden-path smoke covering upload, evidence, retrieval, review/approval, results, reload recovery, and a controlled failure state. (2026-10-13)
- [ ] Add real-embedding regression evaluation across multiple teacher-reviewed examples; measure group quality, outliers, retrieval relevance, and stability beyond the photosynthesis fixture.

  In progress (2026-10-13): the production-path evaluator and two honestly labeled synthetic candidate cases are ready for educator review. Metrics remain diagnostic and this item stays open until a teacher approves the expected groups, outliers, and retrieval targets.
- [x] Evaluate grounded-generation faithfulness, invalid citations, prompt-injection examples, latency, token usage, and provider-unavailable behavior; distinguish valid citation IDs from supported educational claims. (2026-10-13)

**Acceptance:** automated checks protect the integrated workflow, and evaluations document limits rather than generalizing from one synthetic fixture. See [docs/AI_PIPELINE.md](docs/AI_PIPELINE.md#suggested-evaluation-checks).

### Frontend, accessibility, and cleanup

Depends on: P0 gates; preserve the implemented workflow.

- [x] Improve responsive layout and keyboard accessibility where testing identifies gaps. (2026-10-13)
- [x] Add richer progress indicators for long analysis and generation requests. (2026-10-13)
- [x] Allow teachers to rename, merge, dismiss, or restore proposed groups while preserving evidence and review history. (2026-10-23)
  - Implemented as immutable detected groups plus a persisted reviewed overlay and append-only events. Same-question merges union exact evidence, report no fabricated coherence, and lock affected review actions after remediation exists.
  - Spec: [`docs/superpowers/specs/2026-10-14-teacher-group-review-design.md`](docs/superpowers/specs/2026-10-14-teacher-group-review-design.md)
  - Execution plan: [`docs/superpowers/plans/2026-10-14-teacher-group-review.md`](docs/superpowers/plans/2026-10-14-teacher-group-review.md). PostgreSQL integration, backend/unit/frontend checks, and browser reload/lock coverage pass.
  - Fresh branch review hardening (2026-10-23): stale revisions/no-op renames, generation/review races, merged-result undercounting, legacy comparison provenance, retrieval bypass, per-group lock scope, and review-fetch retry recovery are covered.
- [ ] Export an approved intervention and evidence summary.
- [x] Remove unused response/evidence examples from `frontend/src/mockData.ts`; retain scenario metadata and navigation definitions.
- [x] Reconcile stale implementation wording in authoritative documentation with verified code/state; keep proposed features visibly separate. (2026-10-14)
- [ ] Add more robust document format support only if required by the actual demo/pilot material; select extractors before implementation and preserve source locations.

## P2 — real-school pilot and later product work

### Required before real student data

Depends on: verified workflow and evidence-integrity hardening. These are pilot gates even at low traffic, not optional scaling work.

- [ ] Add teacher authentication and API-side record ownership checks for assessments, materials, interventions, and results; test cross-teacher read/write denial. Select the auth approach before implementation.
- [ ] Review database-role privileges and RLS against the selected ownership model; do not treat database RLS or CORS as FastAPI caller authorization.
- [ ] Add generation access/rate limits and spend controls appropriate to the pilot.
- [ ] Define privacy, retention, deletion, consent, and institutional governance workflows for stored responses, sources, prompts, and generated content.
- [ ] Review Gemini service-tier data handling and institutional requirements before sending real student content; minimize prompt identifiers and sensitive free text.

**Acceptance:** authenticated teachers access only authorized records, abuse controls are verified, and the agreed data-handling requirements are documented and implemented.

### Product expansion

Depends on: pilot safeguards and validated teacher demand.

- [ ] Multi-class and multi-assessment history.
- [ ] More rigorous rubric-assisted scoring and longitudinal evaluation.
- [ ] Educator-configurable grouping and retrieval policies.
- [ ] LMS interoperability after the standalone workflow is proven.

### Infrastructure upgrades — measurement gated

These are evaluation tasks, not commitments to add services. The thresholds below are proposed starting points and should be revised from measured pilot workloads.

- [ ] Evaluate durable jobs only if request timeouts exceed 1% or warm p95 processing exceeds 30 seconds after simpler fixes.
- [ ] Evaluate persisted vectors/pgvector only if rebuilds exceed 5 seconds or multiple workers repeatedly rebuild the same corpus.
- [ ] Benchmark grouping at 100–500 eligible responses per question before increasing workload limits; optimize only when latency/memory exceeds the agreed budget.
- [ ] Evaluate more compute when peak RAM consistently exceeds 70% or CPU contention delays concurrent teachers.
- [ ] Add object storage only when retaining original files, supporting additional document formats, or downloadable artifacts requires it.

## Completed — previously verified milestones

The items below retain existing completion evidence. They are not new verification from this reorganization. The former open backend-host decision is corrected to the already documented Render selection; full hosted deployment remains unchecked in P0.

The initial mock UI was a frontend-only scaffold milestone. Its completion did not establish backend, AI, or production behavior; later milestones record those implemented capabilities.

### Frontend milestone — clickable golden-path skeleton

- [x] Build a typed, mock-data UI skeleton covering dashboard, assessment upload, analysis, misconception detail, intervention review, and results.
- [x] Make the documented photosynthesis path clickable end to end with reusable loading, empty, and error-state patterns.

### 0. Foundation

- [x] Establish authoritative product, architecture, AI, database, API, demo, decision, status, and backlog documentation.
- [x] Verify that the existing frontend scaffold starts, lints, and builds.
- [x] Initialize a minimal FastAPI backend with environment-configured local CORS, a typed health endpoint, and health/CORS tests.
- [x] Connect the frontend to `GET /health` through a typed client configured by `VITE_API_URL` and show connection states.
- [x] Select Render Web Service for the Python 3.11 backend; service provisioned and health verified. Full hosted deployment verification remains open below.
- [x] Add the structured API error envelope with the first endpoint that can return domain or validation errors.
- [x] Make the local demo reachable from both loopback spellings and stop reporting browser-blocked requests as a stopped backend. Recorded as D-016.
- [x] Diagnose the subsequent API-unavailable report and restore the stopped backend; verify health/CORS for both local origins and the synthetic preview (2026-10-02).
- [x] Verify hosted health, synthetic preview, and upload preflight permit the exact Vercel production origin (2026-10-02 03:48 UTC); hosted browser golden path remains pending.

### 1. Validated assessment intake

- [x] Freeze a minimal assessment and CSV contract for the photosynthesis demo.
- [x] Create a reproducible, versioned demo assessment and response dataset for approximately 40–50 synthetic students; label it as synthetic.
- [x] Implement CSV upload, size/type checks, required-column validation, encoding/parsing errors, blank-response handling, and normalized preview output.
- [x] Build a minimal teacher upload/preview screen with loading, success, and actionable error states.
- [x] Preserve stable synthetic student identifiers without collecting names or unnecessary personal data.

### 2. Baseline scoring and analysis input

- [x] Store or carry forward assessment, question, answer-key/rubric, response, and correctness data.
- [x] Implement question-specific scoring or a deterministic demo-safe correctness input.
- [x] Exclude blank and correct responses from misconception grouping while preserving counts for the teacher.
- [x] Make reruns idempotent or explicitly version analysis runs.

### 3. Evidence-backed misconception detection

- [x] Generate embeddings for eligible responses with batching and provider/model metadata; local execution has explicit malformed/provider failure handling rather than a network timeout.
- [x] Group responses within each question using the selected proposed strategy and calibrated minimum-support rules.
- [x] Retain outliers and insufficient-data outcomes instead of forcing every response into a group.
- [x] Select representative responses and compute evidence fields without altering student text.
- [x] Build an analysis overview and group-detail view with membership count, confidence/caveat language, and representative responses.

### 4. Teacher-material retrieval

- [x] Upload UTF-8 `.txt` teacher material with extension, size, encoding, null-byte, and empty-content validation.
- [x] Extract and normalize text while preserving chunk offsets; return actionable extraction/validation failures.
- [x] Chunk and embed extracted material using a recorded, configurable strategy and the existing embedding adapter.
- [x] Retrieve passages for a selected misconception using an explicit cosine relevance threshold and configurable top-k.
- [x] Show exact retrieved passages and source metadata separately from student evidence.

### 5. Grounded remediation and teacher review

- [x] Generate a targeted explanation/activity and follow-up questions using only the selected group evidence and retrieved passages.
- [x] Preserve prompt/model/retrieval provenance needed to inspect the persisted result.
- [x] Require teacher edit plus approve/reject controls; never auto-approve.
- [x] Prevent or clearly reject generation when grounding is insufficient.
- [x] Build clear retry/error behavior for LLM and network failures.

### 6. Results and end-to-end demo

- [x] Record or load clearly labeled synthetic follow-up results.
- [x] Compare baseline and follow-up by question/group using transparent counts and percentages.
- [x] Show missing follow-up data as unavailable, not zero or inferred.
- [x] Add a deterministic local demo check/start/reset/status/stop procedure that preserves persisted state.
- [x] Configure `SUPABASE_DB_URL`, apply the migration, and verify the complete workflow survives FastAPI restart and React reload.

### Frontend polish and architecture documentation

- [x] Generate source-backed interactive architecture and data-flow diagrams with Archify; pass showcase, strict artifact and real-browser gates, and inspect selected light/dark captures (2026-10-06). See [Architecture](docs/ARCHITECTURE.md#interactive-repository-diagrams).
- [x] Add a simple public landing page at `/` with routes to the teacher dashboard and labeled synthetic demo; preserve the golden path at `/dashboard` and `/upload` (2026-10-02).
- [x] Add restrained landing-page motion with the Motion React library and reduced-motion support (2026-10-02).
- [x] Replace the CL logo mark and favicon with the supplied ClassLens mascot (2026-10-02).
- [x] Polish shared teacher-workspace hierarchy and controls, including mobile step selection, API visibility, and file-input focus (2026-10-02).

## Do not build for the MVP

- Full learning management system
- Complex authentication or RBAC
- Parent portal or school administration
- Attendance or enrollment
- Payments
- Messaging or notifications
- Native mobile application
- Gamification
- Custom model training
- Microservices or Kubernetes
- Elaborate MLOps
- Redis, queues, event buses, GraphQL, or separate search/vector services without a measured requirement
- Framework or AI-provider rewrites for cosmetic reasons

Complete P0 demo gates before optional work. Real-school pilot safeguards belong after the hackathon and must pass before real student data. Technology alternatives from the stack review remain options to evaluate, not selected replacements.
