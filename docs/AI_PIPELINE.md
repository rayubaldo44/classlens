# AI Pipeline

**Implementation status:** The complete golden-path AI pipeline and its PostgreSQL adapters were live-verified against Supabase, including restart recovery, batched misconception-label interpretation, and grounded remediation generation. The label path was live-verified with real Gemini on 2026-10-27.

This document is the authority for the implemented AI workflow and its failure behavior. Product requirements and safeguards are in [PRODUCT.md](PRODUCT.md); selected and pending technologies are in [TECH_STACK.md](TECH_STACK.md).

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

The implemented import schema is documented in [API.md](API.md). Each row includes:

- `student_id`: stable synthetic or privacy-safe identifier
- `question_id`: identifier matching an assessment question
- `answer`: the original free-text answer
- `is_correct`: required explicit `true`/`false` for deterministic MVP eligibility

Assessment input must separately provide each question's prompt and expected answer or rubric. Before any AI call:

1. Validate file type and the implemented 1 MB/500-row limits.
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

The MVP uses a validated `is_correct` field supplied with each row. ClassLens does not infer correctness in this milestone. This makes the grouping input deterministic and inspectable; future rubric-assisted scoring remains a separate concern.

Correct and blank responses should contribute to baseline counts but should not enter misconception grouping. If correctness is uncertain, represent that uncertainty rather than treating the response as definitely wrong.

Intake rejects any question with more than 100 eligible incorrect responses before embedding or persistence. This bounds complete-link grouping to at most 4,950 response pairs per question while leaving correct and blank rows available for baseline counts.

## 4. Embedding generation — implemented

The backend embeds only eligible incorrect answer text using local `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. The model adapter is isolated under `backend/app/providers/embeddings/`; analysis code depends on its typed protocol, not the package directly. The current preprocessing version is `answer_only_v1`; original answers remain unchanged for evidence. The response records:

- exact model identifier; the immutable artifact revision is pinned in runtime configuration;
- preprocessing/template version;
- vector dimension;
- stable analysis run identifier;
- provider/request failure metadata without secrets.

Batch calls within provider limits, apply a timeout, and validate response count and vector dimensions. A partial or malformed embedding batch must fail the affected analysis rather than inventing or zero-filling vectors.

Vectors are batched, normalized, and validated for count, consistent dimensions, finite values, and non-zero magnitude. Provider or malformed-vector failures return a retryable structured error and no groups. The selected model is pinned to Hugging Face revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` using `CLASSLENS_EMBEDDING_REVISION`; the immutable revision keeps the downloaded files stable. Python 3.11 and a CPU-only PyTorch wheel are the verified development setup. The local runner warms the model before the API reports health; on a hosted service, startup warming must wait until the memory limit can hold the loaded model.

### Operational logging

The API logs request route templates and elapsed time, plus stage durations for CSV parsing, response/material embeddings, grouping, retrieval, Gemini calls, and persistence. Error records contain stable error codes and exception class names only; Gemini records token counts when the provider returns usage metadata. Logs must not include request bodies, prompts, student response text, provider response text, credentials, or raw URLs containing record identifiers. Counts, model IDs, stage names, and persistence operation names are safe operational fields.

## 5. Similarity and grouping — implemented

The service partitions eligible responses by `question_id`, calculates cosine similarity, and applies deterministic agglomerative complete-link clustering. Two clusters merge only when every cross-cluster response pair meets the configured similarity threshold. This conservative rule prevents bridge responses from chaining otherwise dissimilar ideas together. Clusters below minimum support remain outliers.

Current environment-configurable defaults:

- `CLASSLENS_SIMILARITY_THRESHOLD=0.70`
- `CLASSLENS_MIN_GROUP_SIZE=3`
- algorithm identifier `complete_link_cosine_v1`

The selected strategy must be evaluated on short response text and small per-question samples. Store the algorithm name, distance metric, threshold(s), minimum group size, and software/model versions with each run.

### Restraint with small groups

- Require a minimum support count or class proportion before describing a pattern as recurring.
- Treat pairs and tiny clusters as weak signals unless the class size and evidence justify them.
- Permit `insufficient_data` when too few eligible responses exist.
- Permit outliers instead of assigning every response to the nearest cluster.
- Measure group coherence; low-coherence groups should be withheld or explicitly caveated.
- Use careful labels such as “potential misconception” and “responses suggest.”

The initial threshold was evaluated against the versioned fixture without phrase rules: 29 eligible incorrect responses produced 4 groups containing 18 responses and 11 outliers. The strongest group contained 9 differently worded sunlight-as-food responses. Soil-food and two semantically distinct carbon-dioxide error groups also met support. This is hackathon calibration, not a claim of general educational validity.

## 6. Representative evidence — implemented

For each proposed group, return evidence before interpretation:

- membership count and denominator for the question;
- exact member response identifiers;
- a small set of unedited representative responses;
- selection method (for example, responses nearest the group medoid plus a diversity check);
- within-group similarity/coherence summary;
- nearest outliers or contrasting responses when useful;
- question prompt and expected answer/rubric.

The implementation returns every member student identifier plus up to three exact responses nearest the group medoid, their similarity to the medoid, and mean pairwise coherence. Representation must not become cherry-picking; the UI shows the full member list alongside the representative responses.

## 7. Teacher group review — implemented with PostgreSQL persistence

Detected groups, memberships, representative responses, and coherence remain immutable analysis evidence. The backend derives a revision-zero reviewed view from those groups, then persists teacher actions as a current overlay plus ordered, append-only events. The teacher can:

- rename one active reviewed group;
- merge two or more active groups only when they belong to the same question;
- dismiss one active group; or
- restore one dismissed group.

Every action retains the exact original source-group IDs, members, representative responses, counts, and question context. A merge unions source groups and student members, creates a stable reviewed-group identity, and sets coherence to `null`: it does not re-embed responses or invent a numeric claim about the merged evidence. Each event records before/after state, its source IDs, resulting reviewed ID, optional teacher note, timestamp, and monotonically increasing sequence.

The client submits its expected overlay revision. The PostgreSQL writer locks the current state row and rejects stale concurrent updates before atomically saving the next revision and event; identical renames create no event. Retrieval, remediation, and results use the active reviewed identity while preserving original source-group provenance. Once any remediation refers to an affected reviewed or source group, rename, merge, dismiss, and restore actions for that evidence return `group_review_locked`; unrelated groups remain reviewable. Generation revalidates the reviewed evidence and saves the draft while holding the same per-analysis review lock, so a concurrent dismissal wins before generation or is blocked after the draft exists—never leaving a draft attached to dismissed evidence.

## 8. Batched LLM misconception labels — implemented

For each new non-empty baseline analysis, prompt version `misconception_labels_v1` sends all deterministic groups to Gemini in one request. The packet contains only each group's identifier, question, correct answer, and exact representative responses with their student identifiers. Student answers are explicitly delimited as untrusted data. Full membership lists, non-representative answers, and provisional labels are not prompt input.

The response schema requires one concise 5–120 character single-line label per group and one to three unique evidence student identifiers. The service validates exact group coverage, rejects duplicate or unknown group IDs, and requires every evidence identifier to belong to that group's supplied representative responses. Missing, extra, malformed, or cross-group references reject the complete batch; interpretation never changes group IDs, members, responses, scores, support, or coherence.

Label generation uses `gemini-3.1-flash-lite`, temperature `0.1`, at most 1,024 output tokens, one attempt, and a total timeout from `CLASSLENS_LABEL_TOTAL_BUDGET_MS` (default 12 seconds, allowed 1–30 seconds). A valid whole batch is stored with `interpretation_status: "completed"`. Provider configuration, timeout, provider response, or interpretation-validation failures preserve the generic deterministic labels and store every group as `fallback`; no automatic retry occurs after that canonical snapshot is persisted. Empty group sets and legacy/follow-up paths remain `not_requested`.

The analysis identity includes contract version `misconception_labels_v1`, while stable group identities remain based on deterministic evidence. Baseline orchestration checks persistence before interpretation, saves create-if-absent, and reloads the canonical winner. Repeated and concurrent identical requests therefore return stable stored wording and do not automatically spend provider quota again. Database errors remain normal structured failures and are never converted to label fallback.

The UI marks unchanged completed labels as `AI-drafted label · teacher review needed`, fallback labels as `Detected pattern · AI label unavailable`, and legacy/not-requested labels as not yet interpreted. A teacher rename or merge always displays `Teacher-reviewed label`; the teacher remains the authority over the educational interpretation.

## 9. Teacher-material extraction and chunking — implemented

The MVP accepts UTF-8 `.txt` files up to 1 MB. It rejects unsupported extensions, decoding errors, null characters, empty content, and text that produces no chunks. PDF, DOCX, and scanned-page extraction are not implemented.

Text extraction decodes UTF-8 with an optional BOM. Cleaning normalizes CRLF/CR to LF, removes trailing whitespace per line, collapses runs of three or more newlines, and trims the document boundaries. Chunk text is an exact slice of this normalized source, with start/end character offsets. The original uploaded file is not modified or persisted.

Chunking uses configurable sliding character windows with defaults `CLASSLENS_MATERIAL_CHUNK_SIZE_CHARS=900` and `CLASSLENS_MATERIAL_CHUNK_OVERLAP_CHARS=120`. The end prefers a paragraph boundary, then a sentence boundary, then a word boundary; the overlap advances to a word boundary. Each chunk has a stable ordinal ID within its content-addressed material and offsets into the normalized text.

Chunks reuse the existing `EmbeddingService` and local `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` model. The adapter is shared with response analysis; no second provider implementation is added. Embeddings are normalized and checked before indexing.

## 10. Vector retrieval and relevance checks — implemented

Retrieval accepts a selected active reviewed group's question, correct answer, and exact representative answers. It embeds that context as one query and searches only the selected material. Display labels are excluded from the query regardless of whether they are deterministic, AI-drafted, or teacher-reviewed. The reviewed ID and original source-group IDs continue downstream as provenance.

The runtime `MaterialIndex` persists material metadata and exact chunks in PostgreSQL while retaining normalized vectors in a process-local cache. It ranks by the existing exact cosine implementation, returns the configured top-k (default `3`), and filters below the configured score (default `0.42`).

When the cache is empty after startup, stored chunks are re-embedded with their recorded compatible model before retrieval. When no chunk clears the threshold, the API returns `insufficient_relevant_context` and blocks grounded generation.

Ingestion and retrieval remain synchronous and CPU-bound. Chunks are durable and shared through PostgreSQL; each worker has its own rebuildable vector cache, so first retrieval per material/worker incurs embedding work.

## 11. Grounded remediation generation — implemented

The backend uses the isolated Gemini adapter with stable free-tier `gemini-3.1-flash-lite`. Central prompt version `grounded_remediation_v1` receives only the selected reviewed-group context and an enumerated list of retrieved passages, including:

- grade, subject, and topic;
- group/question identifiers and the current provisional label;
- exact question and correct concept;
- affected/eligible response counts and exact representative answers;
- exact material/document metadata, chunk IDs, and chunk text.

Before building the prompt, the service reloads the requested analysis, active reviewed group, and material/chunks from server-side persistence. It requires the browser's class context, reviewed identity, source-group provenance, group evidence, material metadata, chunk IDs, indexes, text, and offsets to match the canonical records exactly. Missing context returns `remediation_context_not_found`; altered or cross-linked context returns `remediation_context_mismatch`. Both stop before Gemini and save nothing. The prompt and saved source snapshots are rebuilt from the canonical records. Browser-supplied similarity scores remain provenance metadata and are excluded from the prompt.

The prompt explicitly says the group is already detected, treats student/source text as untrusted data, forbids unsupported claims, and requests concise age-appropriate teacher content. Gemini structured JSON is parsed into Pydantic fields:

- misconception summary;
- learning objective;
- teacher explanation and corrected concept;
- short activity and optional analogy;
- one to three follow-up questions with expected answers;
- one or more supporting chunk IDs.

Generation is synchronous for the demo, with temperature `0.2`, a 2,200-token output bound, a per-attempt transport timeout from `CLASSLENS_LLM_TIMEOUT_MS` (default 45 seconds), and a total `CLASSLENS_LLM_TOTAL_BUDGET_MS` budget (default 60 seconds). The total budget includes the initial provider call, the 0.75-second retry delay, and one retry for timeouts or HTTP 429/500/502/503/504 responses; the retry receives only the time still available. Permanent failures are not retried. If retrieval status is not `retrieved` or has no results, the service returns `insufficient_context` without calling Gemini. Every returned chunk ID must belong to the supplied retrieval result; unknown or empty references reject the whole draft. The record preserves exact source snapshots and generated content.

The browser aborts its generation request after 70 seconds and retains the selected group and source evidence. It keeps a pending `generation_request_id` in session storage until a valid response arrives. Manual retries reuse that identifier. The backend derives a deterministic remediation ID from the identifier plus canonical analysis/group/material/chunk IDs, checks persistence, and serializes identical in-process requests, preventing a timed-out retry from creating another persisted draft.

## 12. Intervention review — implemented with PostgreSQL persistence

Generation creates status `generated`, never `approved`. The teacher can:

- compare the draft with the potential misconception and passages;
- edit all pedagogical fields while source references remain locked;
- save changes while status remains `generated`;
- approve or reject it;
- leave review notes.

PostgreSQL preserves immutable `generated_content` separately from teacher-edited `content`, exact source snapshots, provider/model/prompt version, status, notes, and timestamps. Approval and rejection remain terminal.

## 13. Follow-up re-analysis and comparison — implemented

Follow-up CSVs use the same schema, validation, normalization, correctness boundary, embedding adapter, and grouping service as baseline assessments. A comparison loads its baseline analysis, active reviewed-group provenance, and explicitly approved linked remediation from persistence.

The service validates that subject, grade level, topic, question ID, prompt, and correct answer still correspond. Follow-up student IDs must be members of the baseline cohort; absent and blank answers remain missing rather than becoming incorrect or resolved.

Because clustering IDs can change as answers improve, each original source group represented by the selected reviewed group is matched by:

1. the same question ID; and
2. the greatest overlap with that source group's original members, with at least two overlapping members required.

The recorded method is `same_question_member_overlap_v1`. A single-source reviewed group behaves as before. For a teacher merge, every constituent source pattern must be re-identified; matched follow-up memberships are then unioned exactly once. If any constituent is missing or ambiguous, the result is `insufficient_data` with no calculated improvement metrics rather than an incomplete improvement claim.

For a completed comparison, deterministic arithmetic reports:

- affected students and misconception prevalence before and after;
- correct students and correctness rate before and after;
- prevalence reduction and correctness change in percentage points;
- matched answered and missing follow-up counts; and
- original-group transitions: resolved correct, changed but still incorrect, still struggling, missing, and newly affected.

Prevalence denominators are answered students on the selected question for each assessment. Transition categories use stable student IDs and the original selected group. The result describes an observed before/after change and explicitly does not claim the approved intervention caused it.

The versioned photosynthesis fixtures produce 9 of 43 answered students affected before (20.9%) and 3 of 43 after (7.0%), a 13.9 percentage-point reduction. Of the 9 initially affected students, 5 answer correctly, 1 changes but remains incorrect, and 3 still show the recurring misconception. The broader question correctness count changes from 14 of 43 to 33 of 43; one follow-up answer is blank and one baseline student is absent.

## Failure handling

| Failure | Pipeline behavior |
|---|---|
| Invalid CSV or missing columns | Stop before persistence/analysis or apply the documented atomic policy; return field/row errors. |
| Empty response | Mark blank, count it, and exclude it from embeddings/grouping. |
| Insufficient eligible responses | Complete with `insufficient_data`; show counts and do not call interpretation unnecessarily. |
| Embedding timeout/error/malformed vectors | Mark the analysis failed or retryable; preserve inputs; create no synthetic groups. |
| Unstable or low-coherence grouping | Return outliers/low-confidence or withhold the proposed group. |
| LLM label provider or validation failure | Persist the complete deterministic evidence with every group marked `fallback`; do not retry automatically or fabricate prose. |
| Extraction failure or empty text | Mark material failed with a useful cause; do not index it. |
| No relevant passage | Return `insufficient_relevant_context` with no results; block claims of grounded remediation. |
| Material embedding, index, or retrieval failure | Return a structured retryable material error; do not return sources as if retrieval succeeded. |
| Remediation LLM missing configuration, timeout, high demand, or other provider failure | Retry one transient timeout/429/5xx response; otherwise return a sanitized structured error, keep source evidence, and save no fabricated draft. |
| Malformed structured output or invalid chunk references | Reject the complete generation and save no remediation. |
| Missing, altered, or cross-linked generation context | Reload canonical analysis and material records; return `remediation_context_not_found` or `remediation_context_mismatch` before Gemini and save nothing. |
| Network/backend failure | Keep evidence and pending request identity in the browser; allow a manual idempotent retry without creating another remediation draft. |
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

An offline production-path evaluator now lives in `backend/evaluation/`. Its two additional synthetic candidate cases remain pending educator review and therefore are not a validated benchmark. A 2026-10-13 diagnostic run with the pinned real model and production `0.70` threshold was exactly stable across two runs per case, and both expected retrieval passages were returned. Grouping pair F1 was `0.50` for fraction denominators and `0.00` for rectangle area/perimeter: only one of four candidate recurring patterns met the threshold. This is evidence that the photosynthesis calibration does not generalize reliably, not a reason to rewrite expected labels around model output. The task remains open until an educator reviews the cases and the accepted quality gates are evaluated.

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

The 2026-10-13 [grounded-generation evaluation](evaluations/2026-10-13-grounded-generation.md) ran two live synthetic cases against `gemini-3.1-flash-lite`. Both passed schema, citation-ID, and injection-canary checks in 3.686–5.362 seconds using 958–971 total tokens. Claim-level review still found one unsupported detail (“from the soil”) in a draft with a valid citation. This confirms that citation membership is enforced but does not prove claim entailment; teacher review remains necessary.

### Outcomes

- Baseline/follow-up calculations use stable identifiers and correct denominators.
- Missing results remain missing.
- The UI does not imply that the intervention caused any observed change.
