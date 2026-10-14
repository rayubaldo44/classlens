# Teacher Group Review Design

**Status:** Approved direction, planned for a later implementation session

## Goal

Let a teacher rename, merge, dismiss, or restore detected misconception groups without mutating the original model output, losing student evidence, or breaking remediation and follow-up provenance.

## Product behavior

- Every detected group remains an immutable part of its original `AnalysisResponse`.
- The teacher works with a reviewed overlay whose current groups may carry a teacher label, dismissal state, or same-question merge.
- Rename changes only the reviewed display label. The original `provisional_label` remains available in history.
- Dismiss hides a group from the actionable list and prevents retrieval/generation from it. A dismissed group remains visible in a “Dismissed” section and can be restored.
- Merge accepts at least two active groups from the same analysis and question. It creates a reviewed group whose evidence is the union of the source groups and records every source group ID.
- A merge never invents a new coherence score or medoid. The reviewed group reports `coherence: null` and explains that coherence was not recalculated after teacher review.
- Review actions become unavailable for any affected source/reviewed group after a remediation record exists. This prevents a reviewed evidence definition from changing underneath generated or approved work.
- Every accepted action records an append-only event with action, source IDs, previous state, resulting state, optional teacher note, and timestamp.

## Data model

Add migration `002_teacher_group_reviews.sql` with:

- `analysis_group_review_states`: one materialized JSON state per `analysis_id`, updated transactionally for fast reads.
- `analysis_group_review_events`: append-only events with a unique public event ID, analysis ID, action, source group IDs, resulting reviewed group ID, previous/next state snapshots, optional note, and creation time.

The original `analysis_runs.result_json`, `misconception_groups`, and `misconception_members` rows remain unchanged. PostgreSQL and the in-memory test double expose the same `GroupReviewStore` protocol.

## API contract

Add:

- `GET /api/v1/assessments/analyses/{analysis_id}/group-reviews`
- `POST /api/v1/assessments/analyses/{analysis_id}/group-reviews`

The POST body is:

```json
{
  "action": "rename | merge | dismiss | restore",
  "group_ids": ["grp_..."],
  "label": "Teacher-reviewed label or null",
  "review_note": "Optional note or null"
}
```

Validation rules:

- rename: exactly one active group and a trimmed label of 1–120 characters;
- merge: at least two distinct active groups from the same question and a trimmed label of 1–120 characters;
- dismiss/restore: exactly one applicable group and no label;
- every ID must belong to the requested analysis;
- affected groups with an existing remediation return HTTP 409;
- repeated or stale actions return a structured 409 rather than silently rewriting state.

The response contains active groups, dismissed groups, and ordered review events. Each reviewed group carries `reviewed_group_id`, `display_label`, `status`, `source_group_ids`, exact unioned member IDs, representative responses copied from source evidence, question context, support/eligible counts, and nullable coherence.

## Downstream evidence

Retrieval, remediation generation, and follow-up comparison resolve `reviewed_group_id` through the review service. The service reconstructs evidence from the immutable analysis plus review state. Canonical generation validation compares the browser snapshot with that reconstructed evidence. Results match follow-up members against the unioned baseline member set and preserve the reviewed group ID plus source group IDs in the trace.

## Frontend behavior

- Learning Gaps offers selection controls only when review mode is open.
- Rename uses a short inline form.
- Merge requires two or more selected active groups and shows the unioned affected-response count before confirmation.
- Dismiss asks for an optional note and moves the group into a collapsed Dismissed section; Restore reverses only the current visibility state and creates another history event.
- Misconception Detail shows a “Teacher reviewed” badge, source group IDs for merges, and “Coherence not recalculated” where applicable.
- The UI disables review controls after downstream remediation exists and explains why.
- Reload recovery fetches review state before resolving the selected group. Stale reviewed IDs show the existing recovery path rather than falling back to unrelated evidence.

## Non-goals

- Re-running embeddings or clustering after review.
- Moving individual students between groups.
- Merging groups across questions or analyses.
- Deleting original groups, responses, or review events.
- Editing an evidence definition after remediation generation.
- Adding authentication or multi-teacher attribution before the separate ownership task.

## Acceptance

- Rename, merge, dismiss, and restore survive reload and restart.
- Original analysis JSON and membership rows remain byte-for-byte unchanged.
- Every action appears in ordered history with before/after state.
- Invalid cross-question, stale, duplicate, and post-remediation actions fail with actionable structured errors.
- Retrieval, generation, and comparison use the reviewed evidence while preserving original source-group provenance.
- Frontend runtime guards, unit tests, backend tests, PostgreSQL integration, and Playwright coverage pass.
