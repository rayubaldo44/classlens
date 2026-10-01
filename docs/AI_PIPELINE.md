# AI Pipeline

**Implementation status:** Proposed. No analysis, embedding, grouping, LLM, document extraction, retrieval, or remediation code exists in the repository as of 2026-10-01.

This document is the authority for the proposed AI workflow and its failure behavior. Product requirements and safeguards are in [PRODUCT.md](PRODUCT.md); selected and pending technologies are in [TECH_STACK.md](TECH_STACK.md).

## Pipeline contract

The pipeline must maintain a trace from every conclusion back to submitted data:

```text
assessment + answer key + exact response
  → eligibility/correctness decision
  → embedding + question-specific grouping
  → representative response evidence
  → bounded LLM interpretation
  → teacher review
  → retrieved teacher passages
  → grounded remediation draft
  → teacher edit and approval
  → follow-up measurement
```

Embeddings find potentially related answer patterns. They do not diagnose a misconception by themselves. RAG grounds the intervention rather than detecting the learning gap.

## 1. CSV validation and preprocessing

The exact import schema is a pending decision. The initial proposed minimum is one row per student/question response with:

- `student_id`: stable synthetic or privacy-safe identifier
- `question_id`: identifier matching an assessment question
- `response_text`: the original free-text answer
- `is_correct`: optional explicit boolean for a deterministic demo, depending on the chosen scoring approach

Assessment input must separately provide each question's prompt and expected answer or rubric. Before any AI call:

1. Validate file type and configured byte/row limits.
2. Decode using the supported encoding and parse with proper CSV quoting rules.
3. Normalize column names only according to the frozen contract; reject ambiguous mappings.
4. Validate required columns, unique response identity, known question identifiers, and valid boolean values.
5. Trim surrounding whitespace only for eligibility checks. Preserve the exact submitted response for display and evidence.
6. Mark null or whitespace-only answers as `blank`; do not embed them.
7. Produce a teacher-visible preview with total, valid, blank, rejected, and per-question counts.

Do not silently drop malformed rows. Either reject the import atomically for the MVP or return explicit row errors under a documented partial-import policy.

## 2. Question-specific analysis

Partition eligible responses by `question_id`. Each analysis unit includes:

- question prompt and learning objective, if supplied;
- expected answer or rubric;
- exact student response;
- correctness/eligibility result;
- stable response identifier.

Never compare or group responses from different questions in the initial MVP. Similar wording across questions can carry different educational meaning.

## 3. Incorrect-response identification

The scoring method is unresolved. Acceptable initial paths are:

- a validated `is_correct` field supplied with the deterministic demo data; or
- a transparent rubric/answer-key scoring step whose output can be inspected and corrected.

Correct and blank responses should contribute to baseline counts but should not enter misconception grouping. If correctness is uncertain, represent that uncertainty rather than treating the response as definitely wrong.

## 4. Embedding generation

**Proposed:** Embed only eligible incorrect responses, with question context included only if evaluation shows it improves separation. Record:

- exact model identifier and revision when available;
- preprocessing/template version;
- vector dimension;
- generation timestamp and analysis run;
- provider/request failure metadata without secrets.

Batch calls within provider limits, apply a timeout, and validate response count and vector dimensions. A partial or malformed embedding batch must fail the affected analysis rather than inventing or zero-filling vectors.

The exact Hugging Face model and hosted-versus-local execution mode remain TBD.

## 5. Similarity and grouping

**Proposed; algorithm TBD:** Normalize vectors if required by the chosen similarity metric, calculate within-question similarity, then use a grouping method that can leave noise unassigned. Candidate approaches may include hierarchical clustering with a distance cutoff, density-based clustering, or a small graph of similarity-connected responses.

The selected strategy must be evaluated on short response text and small per-question samples. Store the algorithm name, distance metric, threshold(s), minimum group size, and software/model versions with each run.

### Restraint with small groups

- Require a minimum support count or class proportion before describing a pattern as recurring.
- Treat pairs and tiny clusters as weak signals unless the class size and evidence justify them.
- Permit `insufficient_data` when too few eligible responses exist.
- Permit outliers instead of assigning every response to the nearest cluster.
- Measure group coherence; low-coherence groups should be withheld or explicitly caveated.
- Use careful labels such as “potential misconception” and “responses suggest.”

Thresholds must be calibrated against the versioned demo fixture, then checked with perturbations or alternate seeds to avoid a one-off result.

## 6. Representative evidence

For each proposed group, return evidence before interpretation:

- membership count and denominator for the question;
- exact member response identifiers;
- a small set of unedited representative responses;
- selection method (for example, responses nearest the group medoid plus a diversity check);
- within-group similarity/coherence summary;
- nearest outliers or contrasting responses when useful;
- question prompt and expected answer/rubric.

Representation must not become cherry-picking. Keep full group membership available to the detail view even if only a few examples appear initially.

## 7. LLM misconception interpretation

Provide the LLM only the question context, expected concept, aggregate evidence, and selected exact responses. Request structured output with:

- concise teacher-readable title;
- explanation of the possible conceptual gap;
- evidence references using supplied response IDs;
- uncertainty/caveat;
- optional teacher check to confirm the interpretation.

Validate output against a schema. Reject evidence IDs that were not supplied and descriptions that contain invented quotes. The UI should still display deterministic group evidence if the LLM fails; the interpretation should be marked unavailable.

## 8. Teacher-material extraction and chunking

**Proposed; formats and extractor TBD:**

1. Validate supported file type and size.
2. Extract text and source metadata such as filename, page, heading, and character offsets when available.
3. Normalize whitespace without changing educational content.
4. Surface unreadable/scanned or empty extraction rather than accepting it as useful material.
5. Split text into moderately overlapping semantic chunks, preferably respecting paragraph/section boundaries.
6. Store each chunk's exact text, ordinal, source locator, extraction version, and content hash.
7. Embed chunks using a model suitable for retrieval. Whether this is the same model as response grouping is an unresolved decision and must be evaluated rather than assumed.

Chunk size and overlap are configuration values that must be recorded with the material version.

## 9. Vector retrieval and relevance checks

Construct a retrieval query from the selected question, expected concept, teacher-reviewed misconception description, and representative evidence. Retrieve only chunks belonging to teacher-selected material.

**Proposed controls:**

- rank by the embedding model's supported similarity metric;
- use a small configurable `top_k`;
- remove duplicate or heavily overlapping chunks;
- apply a calibrated minimum relevance threshold;
- return score and source locator with each passage;
- allow the teacher to inspect passages before generation.

If no passage clears the threshold, return `no_relevant_material`. Do not pass unrelated text to generation or generate citations from general model knowledge.

## 10. Grounded remediation generation

The LLM receives the teacher-reviewed group context and an enumerated list of retrieved passages. Request structured fields such as:

- learning objective;
- short teacher-facing rationale;
- targeted explanation or activity;
- worked example if supported;
- follow-up questions;
- expected answers or rubric notes;
- passage IDs supporting each substantive element.

The prompt must instruct the model to use only supplied passages for source-dependent claims and to state when the sources are insufficient. Validate every cited passage ID. Preserve the exact retrieved text used for the generation so the teacher can audit it later.

## 11. Teacher review

Generation creates a `draft`, never an approved intervention. The teacher can:

- compare the draft with the potential misconception and passages;
- edit the activity and questions;
- approve or reject it;
- leave review notes if implemented.

Persist the generated draft separately from the teacher-edited content when feasible, along with the reviewer action and timestamp.

## Failure handling

| Failure | Pipeline behavior |
|---|---|
| Invalid CSV or missing columns | Stop before persistence/analysis or apply the documented atomic policy; return field/row errors. |
| Empty response | Mark blank, count it, and exclude it from embeddings/grouping. |
| Insufficient eligible responses | Complete with `insufficient_data`; show counts and do not call interpretation unnecessarily. |
| Embedding timeout/error/malformed vectors | Mark the analysis failed or retryable; preserve inputs; create no synthetic groups. |
| Unstable or low-coherence grouping | Return outliers/low-confidence or withhold the proposed group. |
| LLM interpretation failure | Keep evidence; mark description unavailable; allow retry. |
| Extraction failure or empty text | Mark material failed with a useful cause; do not index it. |
| No relevant passage | Return `no_relevant_material`; block claims of grounded remediation. |
| Remediation LLM failure or invalid citations | Keep selected passages and prior drafts; reject invalid output; allow retry. |
| Network/backend failure | Use idempotency where needed and let the client safely retry or poll. |
| Missing follow-up data | Report missing counts and omit unsupported comparisons. |

No provider failure may be replaced with fabricated analysis, passages, citations, or student text.

## Suggested evaluation checks

### Intake and scoring

- Valid, malformed, missing-column, duplicate-ID, blank, quoted-comma, and unexpected-question fixtures.
- Expected per-question correct/incorrect/blank counts.

### Grouping

- The known “sunlight is food” paraphrases group together in the photosynthesis fixture.
- Correct answers, unrelated errors, and blanks do not join that group.
- Repeat runs with fixed model/configuration are stable enough for the demo.
- Small samples return cautious or insufficient outcomes.
- Representative response IDs always belong to the group and text matches source exactly.

### Interpretation

- Every evidence reference exists in the supplied group.
- Human teacher review rates labels for faithfulness and usefulness.
- Adversarial response text cannot override system instructions or invent evidence.

### Retrieval and generation

- Expected source passages appear for known demo queries.
- Unrelated material stays below the relevance threshold.
- Every citation resolves to the exact stored passage.
- Generated activities contain no unsupported source claims.
- Provider timeouts and malformed output yield explicit failures.

### Outcomes

- Baseline/follow-up calculations use stable identifiers and correct denominators.
- Missing results remain missing.
- The UI does not imply that the intervention caused any observed change.
