# ClassLens Backlog

Checkboxes represent verified repository state as of 2026-10-01. Tasks are ordered by dependency. Complete P0 before optional work.

## P0 — demo critical

### Frontend milestone — clickable golden-path skeleton

- [x] Build a typed, mock-data UI skeleton covering dashboard, assessment upload, analysis, misconception detail, intervention review, and results.
- [x] Make the documented photosynthesis path clickable end to end with reusable loading, empty, and error-state patterns.

**Scope:** frontend-only navigation and explicitly labeled demo content; no backend, AI, authentication, or production dataset implementation.

### 0. Foundation

- [x] Establish authoritative product, architecture, AI, database, API, demo, decision, status, and backlog documentation.
- [x] Verify that the existing frontend scaffold starts, lints, and builds.
- [ ] Resolve the minimum blocking decisions: LLM provider, exact embedding model, initial grouping method, teacher-material formats/extractor, backend host, and whether vectors must persist for the demo.
- [ ] Initialize a minimal FastAPI backend with configuration loading, health endpoint, structured error responses, and test setup.

**Verification:** backend starts locally; health endpoint returns a stable response; missing secrets fail clearly at startup or provider-call time; automated backend checks pass.

### 1. Validated assessment intake

Depends on: Foundation.

- [ ] Freeze a minimal assessment and CSV contract for the photosynthesis demo.
- [ ] Create a reproducible, versioned demo assessment and response dataset for approximately 40–50 synthetic students; label it as synthetic.
- [ ] Implement CSV upload, size/type checks, required-column validation, encoding/parsing errors, blank-response handling, and normalized preview output.
- [ ] Build a minimal teacher upload/preview screen with loading, success, and actionable error states.
- [ ] Preserve stable synthetic student identifiers without collecting names or unnecessary personal data.

**Verification:** a valid fixture produces the expected row counts and normalized preview; malformed files, missing columns, duplicate identifiers, and empty responses produce specific errors; frontend and API agree on the contract.

### 2. Baseline scoring and analysis input

Depends on: Validated assessment intake.

- [ ] Store or carry forward assessment, question, answer-key/rubric, response, and correctness data.
- [ ] Implement question-specific scoring or a deterministic demo-safe correctness input.
- [ ] Exclude blank and correct responses from misconception grouping while preserving counts for the teacher.
- [ ] Make reruns idempotent or explicitly version analysis runs.

**Verification:** known fixtures yield deterministic correct/incorrect/blank counts per question, and the exact responses sent to analysis are inspectable.

### 3. Evidence-backed misconception detection

Depends on: Baseline scoring and the embedding/grouping decisions.

- [ ] Generate embeddings for eligible responses with batching, timeouts, and provider/model metadata.
- [ ] Group responses within each question using the selected proposed strategy and calibrated minimum-support rules.
- [ ] Retain outliers and insufficient-data outcomes instead of forcing every response into a group.
- [ ] Select representative responses and compute evidence fields without altering student text.
- [ ] Use the LLM to draft concise potential-misconception labels from question context, expected answer, and supplied evidence.
- [ ] Build an analysis overview and group-detail view with membership count, confidence/caveat language, and representative responses.

**Verification:** the demo fixture reproducibly surfaces the “sunlight as food” pattern; every description is traceable to stored evidence; small or incoherent samples are labeled insufficient/low confidence; embedding or LLM failure never produces fabricated results.

### 4. Teacher-material retrieval

Depends on: Foundation provider choices; can begin after the intake contract stabilizes.

- [ ] Upload supported teacher material with type/size validation.
- [ ] Extract text, preserve source/page or section metadata where available, and show extraction failures.
- [ ] Chunk and embed extracted material using a recorded strategy.
- [ ] Retrieve passages for a selected misconception and apply an explicit relevance threshold.
- [ ] Show retrieved passages and source metadata to the teacher.

**Verification:** a known demo document returns the expected photosynthesis passage; unrelated material produces a “no sufficiently relevant material” state; displayed source references resolve to stored text.

### 5. Grounded remediation and teacher review

Depends on: Evidence-backed groups and successful retrieval.

- [ ] Generate a targeted explanation/activity and follow-up questions using only the selected group evidence and retrieved passages.
- [ ] Persist prompt/model/retrieval provenance needed to inspect the result.
- [ ] Require teacher edit plus approve/reject controls; never auto-approve.
- [ ] Prevent or clearly reject generation when grounding is insufficient.
- [ ] Build clear retry/error behavior for LLM and network failures.

**Verification:** generated claims can be traced to displayed passages; unsupported citations are absent; approval state and edits persist; failure paths keep the prior valid state and never fabricate content.

### 6. Results and end-to-end demo

Depends on: Approved intervention and stable demo identifiers.

- [ ] Record or load clearly labeled synthetic follow-up results.
- [ ] Compare baseline and follow-up by question/group using transparent counts and percentages.
- [ ] Show missing follow-up data as unavailable, not zero or inferred.
- [ ] Complete the documented three-minute click path with loading and meaningful empty/error states.
- [ ] Add a deterministic demo reset/seed procedure and honest fallback assets.
- [ ] Deploy the frontend to Vercel and the backend to the selected host; configure Supabase and secrets.
- [ ] Run the pre-demo checklist in [docs/DEMO.md](docs/DEMO.md#pre-demo-checklist).

**Verification:** a clean demo run completes upload → evidence → material retrieval → remediation review → results without manual database edits; a second run is repeatable; deployed URLs pass smoke checks.

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
