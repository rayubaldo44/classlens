# ClassLens Backlog

Checkboxes represent verified repository state as of 2026-10-02. Tasks are ordered by dependency. Complete P0 before optional work.

## P0 — demo critical

### Frontend milestone — clickable golden-path skeleton

- [x] Build a typed, mock-data UI skeleton covering dashboard, assessment upload, analysis, misconception detail, intervention review, and results.
- [x] Make the documented photosynthesis path clickable end to end with reusable loading, empty, and error-state patterns.

**Scope:** frontend-only navigation and explicitly labeled demo content; no backend, AI, authentication, or production dataset implementation.

### 0. Foundation

- [x] Establish authoritative product, architecture, AI, database, API, demo, decision, status, and backlog documentation.
- [x] Verify that the existing frontend scaffold starts, lints, and builds.
- [x] Initialize a minimal FastAPI backend with environment-configured local CORS, a typed health endpoint, and health/CORS tests.
- [x] Connect the frontend to `GET /health` through a typed client configured by `VITE_API_URL` and show connection states.
- [ ] Resolve the remaining backend-host decision. Relational persistence is implemented; vectors intentionally remain a rebuildable memory cache.
- [x] Add the structured API error envelope with the first endpoint that can return domain or validation errors.
- [x] Make the local demo reachable from both loopback spellings and stop reporting browser-blocked requests as a stopped backend. Recorded as D-016.
- [x] Diagnose the subsequent API-unavailable report and restore the stopped backend; verify health/CORS for both local origins and the synthetic preview (2026-10-02).

**Verification:** backend and frontend start locally; health endpoint and CORS return stable responses; the frontend reaches the configured backend; automated backend and frontend checks pass. Missing secrets and structured errors must be verified when the first dependent endpoint is added. On 2026-10-02 both `127.0.0.1:5173` and `localhost:5173` were confirmed to receive allow-origin headers for the demo preview GET and a POST preflight after `./scripts/demo.sh reset`.

### 1. Validated assessment intake

Depends on: Foundation.

- [x] Freeze a minimal assessment and CSV contract for the photosynthesis demo.
- [x] Create a reproducible, versioned demo assessment and response dataset for approximately 40–50 synthetic students; label it as synthetic.
- [x] Implement CSV upload, size/type checks, required-column validation, encoding/parsing errors, blank-response handling, and normalized preview output.
- [x] Build a minimal teacher upload/preview screen with loading, success, and actionable error states.
- [x] Preserve stable synthetic student identifiers without collecting names or unnecessary personal data.

**Verification:** a valid fixture produces the expected row counts and normalized preview; malformed files, missing columns, duplicate identifiers, and empty responses produce specific errors; frontend and API agree on the contract.

### 2. Baseline scoring and analysis input

Depends on: Validated assessment intake.

- [x] Store or carry forward assessment, question, answer-key/rubric, response, and correctness data.
- [x] Implement question-specific scoring or a deterministic demo-safe correctness input.
- [x] Exclude blank and correct responses from misconception grouping while preserving counts for the teacher.
- [x] Make reruns idempotent or explicitly version analysis runs.

**Verification:** known fixtures yield deterministic correct/incorrect/blank counts per question, and the exact responses sent to analysis are inspectable.

### 3. Evidence-backed misconception detection

Depends on: Baseline scoring and the embedding/grouping decisions.

- [x] Generate embeddings for eligible responses with batching and provider/model metadata; local execution has explicit malformed/provider failure handling rather than a network timeout.
- [x] Group responses within each question using the selected proposed strategy and calibrated minimum-support rules.
- [x] Retain outliers and insufficient-data outcomes instead of forcing every response into a group.
- [x] Select representative responses and compute evidence fields without altering student text.
- [ ] Use the LLM to draft concise potential-misconception labels from question context, expected answer, and supplied evidence.
- [x] Build an analysis overview and group-detail view with membership count, confidence/caveat language, and representative responses.

**Verification:** the demo fixture reproducibly surfaces the “sunlight as food” pattern; every description is traceable to stored evidence; small or incoherent samples are labeled insufficient/low confidence; embedding or LLM failure never produces fabricated results.

### 4. Teacher-material retrieval

Depends on: Foundation provider choices; can begin after the intake contract stabilizes.

- [x] Upload UTF-8 `.txt` teacher material with extension, size, encoding, null-byte, and empty-content validation.
- [x] Extract and normalize text while preserving chunk offsets; return actionable extraction/validation failures.
- [x] Chunk and embed extracted material using a recorded, configurable strategy and the existing embedding adapter.
- [x] Retrieve passages for a selected misconception using an explicit cosine relevance threshold and configurable top-k.
- [x] Show exact retrieved passages and source metadata separately from student evidence.

**Verification:** a known demo document returns the expected photosynthesis passage; unrelated material produces a “no sufficiently relevant material” state; displayed source references resolve to stored text.

### 5. Grounded remediation and teacher review

Depends on: Evidence-backed groups and successful retrieval.

- [x] Generate a targeted explanation/activity and follow-up questions using only the selected group evidence and retrieved passages.
- [x] Preserve prompt/model/retrieval provenance needed to inspect the persisted result.
- [x] Require teacher edit plus approve/reject controls; never auto-approve.
- [x] Prevent or clearly reject generation when grounding is insufficient.
- [x] Build clear retry/error behavior for LLM and network failures.

The generation implementation, deterministic contract tests, and live `gemini-3.1-flash-lite` demo path are verified. The live smoke generated a source-backed intervention from the strongest detected group, preserved a teacher edit, approved one record, and rejected a separate record. Earlier `gemini-3.8-flash` and full-prompt `gemini-3.6-flash` attempts returned Google's transient high-demand response and correctly produced no draft.

**Verification:** generated claims can be traced to displayed passages; unsupported citations are absent; approval state and edits persist; failure paths keep the prior valid state and never fabricate content.

### 6. Results and end-to-end demo

Depends on: Approved intervention and stable demo identifiers.

- [x] Record or load clearly labeled synthetic follow-up results.
- [x] Compare baseline and follow-up by question/group using transparent counts and percentages.
- [x] Show missing follow-up data as unavailable, not zero or inferred.
- [ ] Complete the documented three-minute click path with loading and meaningful empty/error states.
- [x] Add a deterministic local demo check/start/reset/status/stop procedure that preserves persisted state.
- [ ] Add an explicit, honestly labeled fallback for live Gemini unavailability; never switch silently.
- [ ] Deploy the frontend to Vercel and the backend to the selected host; configure Supabase and secrets.
- [x] Configure `SUPABASE_DB_URL`, apply the migration, and verify the complete workflow survives FastAPI restart and React reload.
- [ ] Run the pre-demo checklist in [docs/DEMO.md](docs/DEMO.md#pre-demo-checklist).

**Verification:** a clean demo run completes upload → evidence → material retrieval → remediation review → results without manual database edits; a second run is repeatable; deployed URLs pass smoke checks.

The ordinary-upload API path is live-verified against Supabase through real Gemini generation, explicit teacher approval, and persisted results. The prepared follow-up produces 9/43 affected before (20.9%) and 3/43 after (7.0%), while preserving one blank, one absent student, one partially improved student, and three still-struggling students. FastAPI restart, cold material-vector rebuild, React reload, restored approval/results, desktop/mobile layout, and backend-unavailable messaging passed. Vercel and Render services now exist and Render health passes, but production CORS/API wiring and the hosted golden path remain unchecked; the deployment task therefore stays open.

## P1 — optional polish after P0

- [ ] Improve responsive layout and keyboard accessibility.
- [ ] Add richer progress indicators for long analysis and generation jobs.
- [ ] Allow teachers to rename, merge, or dismiss proposed groups.
- [ ] Export an approved intervention and evidence summary.
- [ ] Add lightweight demo telemetry that contains no student response text.
- [ ] Add more robust document format support if the demo material requires it.

## P2 — post-hackathon ideas

- [ ] Multi-class and multi-assessment history.
- [ ] Secure authentication and role-based access appropriate for real schools.
- [ ] More rigorous rubric-assisted scoring and longitudinal evaluation.
- [ ] Educator-configurable grouping and retrieval policies.
- [ ] Privacy, retention, consent, and institutional governance workflows.
- [ ] LMS interoperability after the standalone workflow is proven.

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

Any proposed work outside the P0 golden path should be deferred until every P0 verification criterion required for the live demo passes.
