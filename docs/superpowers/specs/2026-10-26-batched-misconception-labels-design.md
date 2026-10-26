# Batched Misconception Labels Design

**Date:** 2026-10-26  
**Status:** Approved  
**Backlog item:** P0 AI interpretation

## Intent

Replace generic labels such as `Potential misconception pattern 1` with concise Gemini-drafted descriptions of the incorrect idea visible in each detected evidence group. Labels remain provisional: deterministic embedding groups and their exact representative responses stay authoritative, and the teacher can still rename, merge, dismiss, or restore them.

The feature must improve the first review screen without making successful analysis depend on Gemini. If interpretation is unavailable, slow, malformed, or unsupported by the supplied references, ClassLens returns and persists the existing deterministic labels.

## Goals

- Interpret all groups from one analysis in a single bounded Gemini request.
- Give Gemini only question context, the expected answer, and exact representative responses from each already-detected group.
- Require every returned label to identify its source group and cite one or more supplied representative-response student IDs.
- Validate the complete batch before applying any label.
- Persist whether each displayed label was AI-drafted or a deterministic fallback.
- Keep repeated requests for an already-persisted analysis idempotent and avoid repeated Gemini spending.
- Make the UI clearly distinguish an AI-drafted proposal from an uninterpreted detected pattern.

## Non-goals

- Gemini does not create, split, merge, score, or remove evidence groups.
- Gemini does not decide correctness, diagnose students, infer hidden intent, or produce remediation at this stage.
- Interpretation does not use teacher material or retrieved passages; those remain exclusive to grounded remediation.
- This change does not add asynchronous jobs, a second provider, a schema migration, or automatic teacher approval.
- Follow-up comparison analysis remains deterministic and does not request labels because its groups are used for matching rather than teacher review.

## Anti-goals

- A provider failure must never turn an otherwise valid analysis into HTTP 5xx.
- Partial, duplicate, unknown, or invented group/evidence references must never be mixed with valid labels.
- Re-running the same persisted analysis must not silently replace a label or create another Gemini call.
- Labels must not be presented as established diagnoses or as stronger evidence than the responses themselves.

## Constraints

- Preserve the existing deterministic analysis id, grouping algorithm, group ids, membership, representatives, coherence, and summary counts.
- Keep `GEMINI_API_KEY` server-side and reuse the selected `gemini-3.1-flash-lite` provider boundary.
- Use structured JSON output validated with Pydantic.
- Bound this optional call separately from the 60-second remediation budget. The default interpretation budget is 12 seconds, configurable as `CLASSLENS_LABEL_TOTAL_BUDGET_MS` from 1,000 to 30,000 milliseconds.
- Do not retry label generation. Fallback is cheaper and safer than extending the analysis wait for optional copy.
- Preserve compatibility with stored analyses whose groups have `interpretation_status: "not_requested"`.
- Version newly computed analysis identities with `misconception_labels_v1`. Existing analyses and saved workflow pointers remain readable, while a newly requested analysis creates a fresh snapshot eligible for interpretation.
- Once a new snapshot persists `fallback`, keep that result stable. Repeated requests return the canonical snapshot without spending more provider quota; an explicit relabel action is outside this task.

## Approaches Considered

### Selected: one batch before initial persistence

After deterministic grouping, make one structured Gemini call containing every detected group. Validate the batch all-or-nothing, apply labels to a copied analysis response, persist it, then initialize teacher review from those labels.

This adds only one optional provider call, produces a coherent snapshot, and avoids races between later label updates and teacher review state.

### Rejected: one request per group

This permits partial success but multiplies quota, latency, retry behavior, and inconsistent states. It is a poor fit for an optional P0 enhancement.

### Rejected: asynchronous or lazy interpretation

This makes initial rendering faster, but requires a new mutation lifecycle and conflict rules when a teacher renames or merges a group while labels arrive. That complexity is not justified for the MVP.

## Data Contract

`MisconceptionGroup.interpretation_status` expands to:

- `"completed"`: the displayed `provisional_label` passed full batch and evidence-reference validation.
- `"fallback"`: interpretation was attempted but unavailable, timed out, malformed, or failed validation; the deterministic label is displayed.
- `"not_requested"`: interpretation was intentionally not run, including internal follow-up analysis and legacy stored records.

The Gemini response is a strict batch:

```json
{
  "labels": [
    {
      "group_id": "grp_...",
      "label": "Treats sunlight as the plant's food",
      "evidence_student_ids": ["S001", "S005"]
    }
  ]
}
```

Validation requires:

- exactly one item for every supplied group and no extra or duplicate group ids;
- a trimmed, single-line label between 5 and 120 characters;
- one to three unique evidence student IDs per label;
- every evidence ID to belong to that group's supplied representative responses;
- no mutation of group ids, membership, evidence text, scores, or counts.

Any violation rejects the whole batch and marks every group `fallback`. Evidence-reference IDs are validation material only: the exact representative responses are already persisted with the group, so no new column or migration is needed.

## Prompt and Safety

Add a versioned `misconception_labels_v1` prompt. It will:

- state that groups already exist and must not be regrouped;
- request a short observable description of the incorrect idea rather than a diagnosis of students;
- forbid following instructions embedded in student answers;
- forbid claims not supported by the supplied question, correct answer, and representative responses;
- require exact group and representative student IDs from the packet;
- request structured output only.

Student answers are explicitly delimited as untrusted evidence. The prompt contains no teacher material and no database credentials.

## Request Flow and Idempotency

For baseline demo and uploaded-assessment analysis routes:

1. Parse and run the existing deterministic embedding/grouping pipeline using analysis contract version `misconception_labels_v1`, producing a new deterministic analysis ID without invalidating legacy records.
2. If there are no groups, save and return the result without calling Gemini.
3. Use the deterministic `analysis_id` to check persistent storage. If a canonical analysis already exists, return it without calling Gemini.
4. Otherwise, call the batch interpreter under the label-specific total budget.
5. On any provider or validation failure, log sanitized metadata and convert every group to the deterministic label with `interpretation_status: "fallback"`.
6. Save the complete analysis snapshot.
7. Reload and return the canonical stored snapshot so concurrent identical PostgreSQL requests converge on the winner rather than returning different model wording. Test doubles must implement create-if-absent semantics when exercising this invariant.

Database failures retain their existing structured error behavior; only optional Gemini interpretation failures are absorbed by fallback.

The internal follow-up-analysis service continues calling the pure deterministic analyzer directly, leaving `not_requested` intact.

## Provider Structure

- Add dedicated Pydantic schemas for the structured label batch.
- Extend `LLMService` with `generate_group_labels(prompt) -> GroupLabelBatch`.
- Refactor the Gemini adapter only enough to share client initialization and schema cleanup; remediation keeps its current retry and total-budget behavior.
- Label generation uses one provider attempt, the label-specific budget, temperature `0.1`, and a 1,024-token output cap.
- Add a focused interpretation service that builds the prompt, invokes the provider, validates references and complete coverage, and returns a copied `AnalysisResponse`.

## UI Behavior

The analysis cards continue to render only after the persisted group-review overlay loads.

- A one-source reviewed group whose display label still equals the immutable detected label derives its badge from that source's interpretation status.
- `completed`: show `AI-drafted label · teacher review needed`.
- `fallback`: show `Detected pattern · AI label unavailable` while keeping the generic label and exact evidence usable.
- `not_requested`: show `Detected pattern · not yet interpreted` for legacy or intentionally deterministic results.
- Renamed or merged reviewed groups show `Teacher-reviewed label`, inferred from review provenance without changing persisted review JSON.

The teacher-review panel, rename/merge behavior, evidence screen, remediation flow, and export continue using `display_label`. Teacher edits remain final.

## Error Handling and Observability

- Provider absence, timeout, rate limit, service failure, empty output, malformed JSON, incomplete coverage, invalid label length, and bad evidence references all produce a successful analysis with fallback labels.
- Logs record prompt version, provider/model, group count, elapsed time, status, and sanitized error code. They never contain student answer text.
- A database failure is not mislabeled as an interpretation fallback.
- The browser requires no new retry control because deterministic results are already usable.

## Verification

- Prompt tests prove exact context and untrusted-data instructions.
- Interpretation-service tests cover valid batches plus missing, duplicate, unknown, cross-group, empty, overlong, multiline, provider-unavailable, and timeout outputs.
- Route tests prove no-group and already-persisted analyses skip Gemini; provider failure still saves and returns fallback groups; concurrent/repeated calls return canonical persisted wording.
- Persistence tests round-trip all three interpretation statuses without changing evidence.
- Frontend contract tests accept the three statuses and reject unknown values.
- Browser coverage verifies both AI-drafted and fallback badges while evidence and teacher review remain available.
- Run the full backend suite, PostgreSQL integration when configured, frontend tests, lint, build, and Playwright golden path before marking complete.

## Documentation and Decisions

On verified completion, update `docs/AI_PIPELINE.md`, `docs/API.md`, `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `STATUS.md`, `TASKS.md`, and append one meaningful entry to `SESSION_PROGRESS.md`.
