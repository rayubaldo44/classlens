# Approved Intervention Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a teacher download a safe, self-contained, printable HTML record of an approved intervention and its exact supporting evidence.

**Architecture:** A pure frontend module converts already runtime-validated analysis, reviewed-group, and approved-remediation state into a deterministic `{ filename, html }` artifact. The intervention screen gates the action on approved, provenance-matched state and uses browser-native Blob download APIs; no backend contract, persistence model, dependency, or network request is added.

**Tech Stack:** React 19, strict TypeScript 6, Node test runner, Vite, Playwright Chromium, browser Blob/Object URL APIs

**Spec:** `docs/superpowers/specs/2026-10-23-approved-intervention-export-design.md`

## Global Constraints

- Export only `status: "approved"` remediation records whose analysis ID, reviewed group ID, and source-group provenance match the active validated workflow state.
- Include approved `content`, never substitute immutable `generated_content` for the teacher-approved text.
- Include exact representative answers and persisted remediation source snapshots, but omit every `student_id` and the member-student list.
- Escape all dynamic HTML and emit no scripts, remote assets, or network requests.
- Label `synthetic_demo` honestly and include the evidence/causality limitations from the design.
- Add no dependency, backend endpoint, database migration, export persistence, or follow-up metrics.
- Preserve the user's unrelated edit to `docs/superpowers/plans/2026-10-14-teacher-group-review.md`; never stage it.

## Review Focus

- Hostile `<script>`, entity, quote, and URL-like text in teacher/student/source fields must render as text and must not introduce executable markup; Task 1 pins this with a hostile-content test.
- A stale or mismatched analysis/group/source provenance chain must fail closed instead of exporting a misleading artifact; Task 1 pins each mismatch class.
- Source references missing from persisted remediation snapshots must fail closed instead of producing an incomplete evidence record; Task 1 pins this cross-reference case.
- Empty optional analogy/review notes and very long punctuation-heavy subject/topic values must still produce valid readable HTML and a bounded safe filename; Task 1 pins both cases.
- Downloading must leave the intervention screen and saved workflow untouched, and the action must remain absent before approval; Task 2 pins this in Chromium.

---

### Task 1: Pure approved-intervention artifact builder

**Files:**
- Create: `frontend/src/interventionExport.ts`
- Create: `frontend/tests/interventionExport.test.ts`

**Interfaces:**
- Consumes: `AssessmentPreview['assessment']`, `AnalysisResponse['data_label']`, `ReviewedMisconceptionGroup`, and `RemediationRecord` from `frontend/src/api/client.ts`.
- Produces: `buildApprovedInterventionExport(input: ApprovedInterventionExportInput): InterventionExportArtifact`, where the input contains `analysisId`, `dataLabel`, `assessment`, `group`, `remediation`, and ISO `exportedAt`; the artifact contains `filename` and `html` strings.
- Produces: `ApprovedInterventionExportInput` and `InterventionExportArtifact` exported types for the UI integration.

- [ ] **Step 1: Write the failing happy-path and privacy tests**

Create fixtures with teacher-edited approved content, one representative response carrying unique student ID `STUDENT-PRIVATE-42`, one cited source, review notes, and fixed export time `2026-10-23T08:00:00.000Z`. Assert:

- filename is `classlens-science-photosynthesis-remediation-approved.html`;
- HTML contains the assessment context, reviewed label, `9 of 29`, exact representative answer, every approved intervention field, teacher notes, source text/chunk/offsets, provenance IDs, model/prompt, timestamps, and both disclaimer concepts;
- HTML does not contain `STUDENT-PRIVATE-42`, member IDs, an uncited/generated-only content sentinel, `<script`, or remote asset URLs.

- [ ] **Step 2: Run the focused test to verify RED**

Run: `node --test tests/interventionExport.test.ts`

Expected: FAIL because `../src/interventionExport.ts` does not exist.

- [ ] **Step 3: Write failing safety and edge-case tests**

Add named tests asserting that the builder:

- throws for `generated` and `rejected` statuses;
- throws for analysis ID, reviewed-group ID, or source-group set mismatch;
- throws when an approved `source_references` ID has no matching persisted source snapshot;
- escapes `<script>alert("x")</script>`, `&`, `<`, `>`, `'`, and `"` in every content class while emitting no active script or remote resource attributes;
- omits empty analogy/review-note sections cleanly;
- produces an ASCII lowercase dash-separated `.html` filename of at most 120 characters for long punctuation-heavy metadata, with remediation ID fallback when descriptive slugs are empty;
- includes a visible `Synthetic demo data` label only for `synthetic_demo`.

- [ ] **Step 4: Implement the pure builder**

In `frontend/src/interventionExport.ts`, define the exact interfaces above and implement `buildApprovedInterventionExport`. Use local helpers for HTML escaping, equal source-group set comparison, ISO timestamp formatting, and bounded filename slugging. Render semantic standalone HTML with embedded screen/print CSS, no `<script>`, no external `src`, `href`, `url()`, or `@import`, and source rows marked `Cited by approved intervention` when referenced.

- [ ] **Step 5: Run focused tests to verify GREEN**

Run: `node --test tests/interventionExport.test.ts`

Expected: all export tests PASS.

- [ ] **Step 6: Run TypeScript lint/build checks**

Run: `npm run lint`

Then run: `npm run build`

Expected: ESLint exits 0 and Vite production build succeeds.

- [ ] **Step 7: Commit the pure export boundary**

```bash
git add frontend/src/interventionExport.ts frontend/tests/interventionExport.test.ts
git commit -m "feat: build approved intervention export"
```

### Task 2: Approved-state download action and browser coverage

**Files:**
- Modify: `frontend/src/App.tsx:345-478`
- Modify: `frontend/tests/e2e/golden-path.spec.ts`

**Interfaces:**
- Consumes: `buildApprovedInterventionExport(...)` and `InterventionExportArtifact` from Task 1.
- Produces: an approved-state **Download evidence summary** button that downloads the artifact through `Blob`, `URL.createObjectURL`, a temporary anchor, and `URL.revokeObjectURL` without changing navigation or workflow state.

- [ ] **Step 1: Extend the golden-path browser test for RED**

Before approval, assert **Download evidence summary** is absent. After the existing approval action, wait for Playwright's `download` event, activate the button, and assert:

- suggested filename equals `classlens-science-photosynthesis-remediation-approved.html`;
- downloaded text contains the teacher-approved intervention, exact representative answer, cited source passage, analysis/group/source/remediation IDs, and teacher notes;
- downloaded text excludes `S001` and other member IDs;
- the page remains on `/intervention`, **Approved by teacher** remains visible, and **Continue to results** still works afterward.

- [ ] **Step 2: Run the focused browser test to verify RED**

Run: `npx playwright test tests/e2e/golden-path.spec.ts --project=chromium`

Expected: FAIL because the download action does not exist.

- [ ] **Step 3: Integrate the approved download action**

Import the Task 1 builder in `frontend/src/App.tsx`. Pass `selectedAnalysis?.data_label ?? null` into `Intervention`, add the corresponding typed prop, and define an `exportApprovedIntervention` handler that returns early unless group, analysis ID, assessment, data label, and approved record are present. Build with `new Date().toISOString()`, download as `text/html;charset=utf-8`, remove the temporary anchor, and revoke the object URL in `finally`.

Render **Download evidence summary** as a secondary button only inside the existing approved decision state, beside **Continue to results**. Do not add the action to pending, saving, error, insufficient-context, or rejected states.

- [ ] **Step 4: Run the focused browser test to verify GREEN**

Run: `npx playwright test tests/e2e/golden-path.spec.ts --project=chromium`

Expected: the golden-path test PASSes, including download contents and unchanged continuation behavior.

- [ ] **Step 5: Run all frontend tests and checks**

Run, as separate commands:

```bash
npm test -- --run
npm run lint
npm run build
npm run test:e2e
```

Expected: all Node tests, ESLint, Vite build, and all Chromium scenarios PASS.

- [ ] **Step 6: Commit the UI integration**

```bash
git add frontend/src/App.tsx frontend/tests/e2e/golden-path.spec.ts
git commit -m "feat: download approved intervention summary"
```

### Task 3: Authoritative documentation and final verification

**Files:**
- Modify: `docs/PRODUCT.md`
- Modify: `docs/DECISIONS.md`
- Modify: `STATUS.md`
- Modify: `TASKS.md`
- Modify: `SESSION_PROGRESS.md`

**Interfaces:**
- Consumes: verified behavior and exact test totals from Tasks 1–2.
- Produces: current product/status/backlog/history records plus D-034 documenting client-side printable HTML, privacy omission, and the no-backend/no-dependency boundary.

- [ ] **Step 1: Update authoritative records after verification**

Add the approved export behavior to `docs/PRODUCT.md`; add D-034 to `docs/DECISIONS.md`; add one verified-working entry and exact test totals to `STATUS.md`; mark **Export an approved intervention and evidence summary** complete in `TASKS.md` with links to the spec and plan; append one meaningful milestone to `SESSION_PROGRESS.md` covering files, behavior, verification, decisions, problems, remaining work, and the next recommended task.

- [ ] **Step 2: Run the complete affected verification gate**

From `frontend/` run:

```bash
npm test -- --run
npm run lint
npm run build
npm run test:e2e
```

From the repository root run `git diff --check` and the existing relative-Markdown-link check over `AGENTS.md`, `STATUS.md`, `TASKS.md`, `SESSION_PROGRESS.md`, `README.md`, and `docs/**/*.md`.

Expected: every command exits 0; no link target is missing; the only unrelated unstaged change remains `docs/superpowers/plans/2026-10-14-teacher-group-review.md`.

- [ ] **Step 3: Review the complete implementation diff**

Compare the implementation against every design acceptance criterion. Confirm no student identifier appears in the downloaded fixture, no API/database/dependency file changed, and all dynamic artifact content flows through the escaping helper.

- [ ] **Step 4: Commit documentation**

```bash
git add docs/PRODUCT.md docs/DECISIONS.md STATUS.md TASKS.md SESSION_PROGRESS.md
git commit -m "docs: record intervention export milestone"
```

- [ ] **Step 5: Request final code review**

Run the repository's final review workflow against the complete implementation range, fix any Critical or Important findings with focused regressions, rerun the full affected gate, and report minor suggestions separately.
