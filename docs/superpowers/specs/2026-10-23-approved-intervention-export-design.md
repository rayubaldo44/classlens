# Approved Intervention Export Design

**Date:** 2026-10-23
**Status:** Proposed for approval

## Intent

Give a teacher a portable, readable record of an explicitly approved ClassLens intervention and the evidence that supported it. The artifact should be useful for printing, saving as PDF, or sharing with another educator while preserving the distinction between detected evidence, teacher-provided sources, AI-generated assistance, and the teacher's final approval.

## Goals

- Add a download action that is available only for an approved remediation.
- Produce one self-contained HTML file that opens offline and prints cleanly to PDF or paper.
- Export the current teacher-approved content, not the immutable original generation.
- Preserve auditable analysis, reviewed-group, source-group, remediation, prompt, source-chunk, and timestamp identifiers.
- Include exact representative response text and exact cited teacher-source snapshots without exposing student IDs.
- Make the artifact's limits explicit: the group is a potential misconception supported by observed responses, not a diagnosis, and the export does not claim that an intervention caused later outcomes.

## Non-goals

- No server-side PDF renderer, email/share workflow, cloud storage, or export history.
- No backend endpoint, database migration, or new dependency.
- No follow-up comparison metrics; this artifact records the approved intervention and its supporting evidence at the approval checkpoint.
- No export for generated-but-unapproved or rejected drafts.
- No original Gemini draft diff. The database continues to preserve that record, but the teacher-facing artifact presents the approved version.

## Constraints and safety

- Build the artifact only from the already runtime-validated assessment, reviewed group, and remediation record held by the intervention screen.
- Require `remediation.status === "approved"` and matching analysis/reviewed-group provenance before enabling export.
- Escape every dynamic value before inserting it into HTML. The downloaded file contains no scripts, remote fonts, remote images, or network requests.
- Omit `student_id` and the full member-student list. Retain representative answer text, group support/denominator counts, reviewed-group ID, and original source-group IDs so the educational evidence and audit chain remain visible without adding student identifiers to the portable file.
- Label synthetic-demo data when the assessment record carries that label.
- Use a filesystem-safe filename derived from subject/topic plus the remediation ID; fall back to the remediation ID when descriptive fields sanitize to an empty value.

## Selected approach

### Self-contained printable HTML generated in the browser

Add a small pure TypeScript export module that accepts the validated assessment metadata, active reviewed group, approved remediation, and an explicit export timestamp. It returns the complete HTML string and safe filename. The intervention screen creates a UTF-8 `Blob`, triggers a browser download, and immediately revokes the object URL.

This approach was selected because it provides a presentation-ready artifact and browser-native Print to PDF without adding PDF tooling or a new server trust boundary.

### Alternatives considered

- **Markdown download:** smallest implementation and easy to inspect, but weaker print layout and less suitable for a teacher-facing handoff.
- **Backend-generated PDF:** stronger control over final rendering, but adds rendering dependencies, deployment work, and another failure path that the MVP does not need.

## Artifact contents

The document is ordered to make the evidence chain inspectable:

1. **Header and status** — ClassLens, “Teacher-approved intervention,” export time, data label, and assessment title/subject/grade/topic.
2. **Potential misconception evidence** — teacher-reviewed label, question, expected answer, support count and eligible-response denominator, exact representative answers without student IDs, reviewed-group ID, and source-group IDs.
3. **Approved intervention** — misconception summary, learning objective, corrected concept, teacher explanation, activity, optional analogy, and every follow-up question with its expected answer.
4. **Teacher review** — approval status, optional review notes, and remediation update time.
5. **Grounding sources** — each persisted source snapshot used by the remediation, including material title, filename, chunk ID/index, character offsets, exact passage text, and an indication of whether the chunk appears in the approved content's validated source references.
6. **Audit details and limits** — analysis ID, remediation ID, provider/model, prompt version, created/updated timestamps, and concise evidence/causality disclaimers.

## User experience

- After approval, the existing approved-state panel shows a secondary **Download evidence summary** button beside **Continue to results**.
- The button is absent for pending and rejected records.
- Activating it downloads the file directly; it does not navigate away or mutate workflow state.
- The HTML uses embedded accessible semantic structure and print styles. Screen and print layouts remain legible without ClassLens application CSS.

## Implementation boundaries

- Add `frontend/src/interventionExport.ts` for escaping, filename normalization, and deterministic document generation.
- Integrate the action only in the approved branch of `Intervention` in `frontend/src/App.tsx`.
- Add focused unit tests for approval gating inputs, content/provenance inclusion, student-ID omission, optional fields, filename safety, and hostile HTML escaping.
- Add a Playwright assertion that an approved intervention downloads one HTML file containing the expected approved content and evidence while excluding student IDs.
- Update product behavior, backlog/status, and session history only after implementation and verification succeed.

## Acceptance criteria

- An approved remediation exports a valid, self-contained `.html` document from the intervention screen.
- Pending or rejected records expose no export action.
- The artifact contains the exact approved intervention, representative answer text, cited source passages, and audit provenance from validated state.
- The artifact contains no student IDs, active scripts, remote resources, or unescaped dynamic HTML.
- The download does not alter the saved workflow or prevent continuing to results.
- Focused tests plus the affected frontend unit, lint, build, and browser suites pass.
