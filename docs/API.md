# ClassLens API

**Implementation status:** The complete API path has PostgreSQL-backed runtime repositories. Local contracts pass; live Supabase migration/restart verification awaits `SUPABASE_DB_URL`.

Implemented endpoints are marked and describe the current frontend/backend contract. Other sections remain proposed until implemented. Base path for implemented versioned routes: `/api/v1`.

## Conventions

- JSON uses `snake_case` to align with proposed Python models; the frontend should map through typed API contracts.
- Resource IDs are opaque strings. Assessment, analysis, group, material, and comparison public IDs use deterministic content-derived prefixes; internal relational rows may use UUIDs. Imported `question_id`/`student_id` values remain validated external identifiers.
- Timestamps are UTC ISO 8601 strings.
- File endpoints use `multipart/form-data`; other endpoints use JSON.
- Long analysis/generation operations may return `202 Accepted` and a pollable resource.
- Retried mutation requests that can duplicate work should accept an `Idempotency-Key` header.
- Provider/model internals and secrets never appear in client errors.

## Error contract

Every non-2xx response should use one envelope:

```json
{
  "error": {
    "code": "csv_missing_columns",
    "message": "The response file is missing required columns.",
    "details": {
      "missing_columns": ["question_id", "response_text"]
    },
    "retryable": false,
    "request_id": "req_01J..."
  }
}
```

Proposed mappings:

| Status | Use |
|---|---|
| `400` | Malformed request, CSV, or unsupported transition. |
| `404` | Resource does not exist or is inaccessible. |
| `409` | Duplicate/idempotency conflict or stale state. |
| `413` | File or row limit exceeded. |
| `415` | Unsupported media/document type. |
| `422` | Structurally valid request with field/row validation errors. |
| `429` | Rate limit; retry guidance may be supplied. |
| `502` | Upstream embedding/LLM/extraction provider failure. |
| `503` | Backend dependency unavailable or timed out. |

Expected domain outcomes such as `insufficient_data` or `insufficient_relevant_context` should usually be successful resource states, not fabricated successes or generic server errors.

## Health

### `GET /health` — implemented

Verified minimal readiness response:

```json
{
  "status": "ok",
  "service": "classlens-api"
}
```

Do not report external AI providers healthy unless the endpoint actually checks them; keep expensive provider diagnostics separate.

## Assessment intake — implemented preview contract

### CSV contract

The MVP intake uses one UTF-8 CSV with these required columns:

```csv
assessment_title,subject,grade_level,topic,student_id,question_id,question,answer,correct_answer,is_correct
```

- Every field except `answer` must contain a non-whitespace value.
- `is_correct` must be the literal `true` or `false` (case-insensitive). A blank answer cannot be marked correct.
- Blank answers are accepted, preserved, marked `blank`, and counted separately.
- Student identifiers are synthetic/stable for the demo; names and unnecessary personal data are excluded.
- Each `student_id`/`question_id` pair must be unique.
- Assessment metadata must be consistent across rows. A `question_id` must always use the same question and correct answer.
- Source answer text is preserved; trimming is used only to determine whether it is blank.
- Files must use a `.csv` extension, UTF-8 encoding, and be no larger than 1 MB.
- Intake does not infer scores or persist data. The explicit correctness value is the deterministic MVP scoring boundary.

### `POST /api/v1/assessments/preview`

Accepts multipart field `file` and optional `data_label` (`teacher_upload` by default or `synthetic_demo`). The import is atomic: one invalid row rejects the preview.

`200 OK` returns assessment metadata, transparent counts, and up to five normalized sample responses:

```json
{
  "status": "validated",
  "data_label": "teacher_upload",
  "filename": "photosynthesis_responses.csv",
  "assessment": {
    "title": "Photosynthesis Free-Response Check",
    "subject": "Science",
    "grade_level": "7",
    "topic": "Photosynthesis"
  },
  "summary": {
    "response_count": 45,
    "answered_count": 43,
    "blank_count": 2,
    "correct_count": 14,
    "incorrect_count": 29,
    "student_count": 45,
    "question_count": 1
  },
  "sample_responses": [
    {
      "row_number": 2,
      "student_id": "S001",
      "question_id": "Q1",
      "question": "Explain how plants make food during photosynthesis.",
      "answer": "Plants eat sunlight and that becomes their food.",
      "correct_answer": "Plants use light energy to convert carbon dioxide and water into glucose and oxygen.",
      "answer_status": "answered",
      "is_correct": false
    }
  ]
}
```

### `GET /api/v1/assessments/demo/photosynthesis/preview`

Runs the versioned synthetic fixture through the same parser and returns the preview with `data_label: "synthetic_demo"`.

Implemented error codes include `unsupported_file_type`, `file_too_large`, `csv_empty`, `csv_encoding_error`, `csv_malformed`, `csv_duplicate_columns`, `csv_missing_columns`, `csv_blank_required_value`, `csv_invalid_correctness`, `csv_inconsistent_assessment`, `csv_inconsistent_question`, and `csv_duplicate_response`.

## Analysis — implemented synchronous MVP contract

### `POST /api/v1/assessments/analyze`

Accepts the same multipart `file` CSV as preview. The endpoint revalidates and analyzes the complete file, then atomically persists the normalized assessment, questions, responses, run, groups, and memberships before returning. Preview endpoints remain non-persistent.

### `GET /api/v1/assessments/demo/photosynthesis/analysis`

Runs the versioned synthetic fixture through the same parser and analysis service. This is not cached output.

Both endpoints return `200 OK` with a stable `assessment_id` plus the existing analysis payload:

```json
{
  "assessment_id": "assessment_1234567890abcdef",
  "analysis_id": "analysis_1a191d0a7331cb82",
  "status": "completed",
  "data_label": "synthetic_demo",
  "filename": "photosynthesis_responses.csv",
  "assessment": {
    "title": "Photosynthesis Free-Response Check",
    "subject": "Science",
    "grade_level": "7",
    "topic": "Photosynthesis"
  },
  "summary": {
    "response_count": 45,
    "answered_count": 43,
    "blank_count": 2,
    "correct_count": 14,
    "eligible_incorrect_count": 29,
    "grouped_response_count": 18,
    "outlier_count": 11,
    "question_count": 1,
    "group_count": 4
  },
  "embedding": {
    "model_id": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "dimension": 384,
    "preprocessing": "answer_only_v1"
  },
  "grouping": {
    "algorithm": "complete_link_cosine_v1",
    "similarity_threshold": 0.7,
    "minimum_support": 3
  },
  "groups": [
    {
      "group_id": "grp_704762a85fd8",
      "provisional_label": "Potential misconception pattern 1",
      "interpretation_status": "not_requested",
      "question_id": "Q1",
      "question": "Explain how plants make food during photosynthesis.",
      "correct_answer": "Plants use light energy to convert carbon dioxide and water into glucose and oxygen.",
      "support_count": 9,
      "eligible_response_count": 29,
      "member_student_ids": ["S001", "S005", "S009"],
      "representative_responses": [
        {
          "student_id": "S033",
          "answer": "The leaves absorb sunlight as food for the plant.",
          "similarity_to_medoid": 1.0
        }
      ],
      "coherence": 0.8454
    }
  ],
  "message": null
}
```

### `GET /api/v1/assessments/analyses/{analysis_id}`

Reconstructs a persisted analysis response and its evidence groups. Missing IDs return `404 initial_assessment_not_found`.

The member list above is abbreviated only in this documentation example. Runtime responses contain every member identifier. When no group has at least the configured support, the endpoint returns `status: "insufficient_data"`, an empty `groups` list, and an explanatory `message`. Embedding failures return the standard error envelope with `503`, a safe `embedding_failed` or `embedding_invalid_response` code, and no fabricated group.

## Misconception details

### `GET /misconception-groups/{group_id}`

```json
{
  "group_id": "c5ccbe27-bbcd-455c-80f2-943979a12e9c",
  "question": {
    "question_id": "q1",
    "prompt": "How do plants use sunlight to make food?",
    "expected_answer": "Sunlight provides energy that plants use to make glucose from carbon dioxide and water."
  },
  "interpretation": {
    "title": "Sunlight treated as plant food",
    "description": "These responses may confuse the energy source for photosynthesis with the glucose produced.",
    "caveat": "This is a potential shared pattern for teacher review.",
    "evidence_response_ids": ["r-001", "r-007", "r-019"]
  },
  "support_count": 12,
  "eligible_response_count": 28,
  "representative_responses": [
    {"response_id": "r-001", "student_id": "S001", "response_text": "Plants eat sunlight."},
    {"response_id": "r-007", "student_id": "S007", "response_text": "Sunlight is the food of plants."},
    {"response_id": "r-019", "student_id": "S019", "response_text": "Plants consume sunlight to grow."}
  ]
}
```

Pagination or explicit limits should be added before returning full membership for larger datasets.

## Learning-material ingestion and retrieval — implemented MVP contract

Supported upload format is UTF-8 plain text (`.txt`), up to 1 MB. Metadata and exact chunks persist in PostgreSQL. Embeddings remain a rebuildable memory cache.

### `POST /api/v1/learning-materials/ingest`

Accepts multipart `file` and optional `title`. Validation, cleanup, chunking, embedding, and transactional persistence complete synchronously. Re-ingesting identical normalized content is idempotent.

`200 OK`:

```json
{
  "status": "ready",
  "material": {
    "material_id": "mat_d4181909edbae023",
    "title": "Grade 7 Photosynthesis Learning Notes",
    "filename": "photosynthesis_grade7.txt",
    "source_kind": "teacher_upload",
    "content_hash": "d4181909edbae0234efd5b5cdf400659f85f700ccbfa23db7b90e6e44455fa74",
    "chunk_count": 3,
    "chunk_size_chars": 900,
    "chunk_overlap_chars": 120,
    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "embedding_dimension": 384
  },
  "message": "Material is ready with 3 persisted chunks."
}
```

### `POST /api/v1/learning-materials/demo/photosynthesis/ingest`

Ingests `data/demo/learning_materials/photosynthesis_grade7.txt` through the same validation, chunking, embedding, and indexing service. Returns `source_kind: "synthetic_demo"`.

### `POST /api/v1/learning-materials/{material_id}/retrieve`

Accepts a detected group context:

```json
{
  "group_id": "grp_704762a85fd8",
  "question_id": "Q1",
  "question": "Explain how plants make food during photosynthesis.",
  "correct_answer": "Plants use light energy to convert carbon dioxide and water into glucose and oxygen.",
  "representative_answers": [
    "The leaves absorb sunlight as food for the plant.",
    "Sunlight is the food that plants absorb through their leaves.",
    "Leaves eat light from the sun as their source of food."
  ]
}
```

The API embeds the question, exact representative answers, and reference answer as a semantic query. It searches only chunks belonging to the requested material ID, ranks by exact cosine similarity, returns up to `CLASSLENS_RETRIEVAL_TOP_K=3`, and filters below `CLASSLENS_RETRIEVAL_MIN_SCORE=0.42`. Both values are configurable. The chunk strategy is configurable through `CLASSLENS_MATERIAL_CHUNK_SIZE_CHARS=900` and `CLASSLENS_MATERIAL_CHUNK_OVERLAP_CHARS=120`.

`200 OK` returns `status: "retrieved"` with source metadata and exact chunk text, or `status: "insufficient_relevant_context"` with an empty `results` array. The latter explicitly blocks grounded-remediation claims. Results include material/document ID, title, filename, content hash, chunk ID/index, cosine score, and offsets into the cleaned text.

Implemented material errors include `unsupported_material_type` (415), `material_too_large` (413), `material_empty`, `material_encoding_error`, `material_invalid_text`, `no_chunks_generated`, `material_embedding_failed`, `material_embedding_invalid_response`, `material_index_failed`, `material_not_found` (404), `embedding_model_mismatch`, and `material_retrieval_failed`. Provider/index errors use the shared structured error envelope and never return fabricated sources.

## Grounded remediation and teacher review — implemented synchronous demo contract

Remediation records persist in PostgreSQL. The API preserves the original Gemini generation separately from teacher-edited current content. Nothing starts approved.

### `POST /api/v1/remediations`

Accepts required `analysis_id`, the selected detected group, class context, and complete typed retrieval response. The database verifies the intervention's analysis/group and material/chunk relationships.

Abbreviated request shape:

```json
{
  "analysis_id": "analysis_1a191d0a7331cb82",
  "grade_level": "7",
  "subject": "Science",
  "topic": "Photosynthesis",
  "misconception": {
    "group_id": "grp_704762a85fd8",
    "provisional_label": "Potential misconception pattern 1",
    "question_id": "Q1",
    "question": "Explain how plants make food during photosynthesis.",
    "correct_answer": "Plants use light energy to convert carbon dioxide and water into glucose and oxygen.",
    "support_count": 9,
    "eligible_response_count": 29,
    "representative_responses": [
      {"student_id": "S033", "answer": "The leaves absorb sunlight as food for the plant.", "similarity_to_medoid": 1.0}
    ]
  },
  "retrieval": {
    "status": "retrieved",
    "group_id": "grp_704762a85fd8",
    "material": {"material_id": "mat_d4181909edbae023", "title": "Grade 7 Photosynthesis Learning Notes"},
    "results": [{"chunk_id": "chunk_001", "text": "Exact retrieved text...", "similarity": 0.784}]
  }
}
```

The runtime request must include every required `material`, retrieval-metadata, chunk-index, and offset field from the retrieval contract; the example is abbreviated for readability.

`200 OK` returns either `status: "generated"` with a remediation or the controlled state below without calling Gemini:

```json
{
  "status": "insufficient_context",
  "remediation": null,
  "message": "Insufficient teacher-provided material to generate grounded remediation."
}
```

A generated remediation has lifecycle status `generated` and includes:

- `generated_content`: immutable original Gemini structure;
- `content`: current teacher-editable structure;
- `sources`: exact retrieved source snapshots;
- provider/model/prompt version and timestamps.

Both content objects include `misconception_summary`, `learning_objective`, `teacher_explanation`, `corrected_concept`, `activity`, optional `analogy`, one to three `{prompt, expected_answer}` follow-up questions, and validated `source_references` containing only supplied chunk IDs.

### `GET /api/v1/remediations/{remediation_id}`

Returns the current typed remediation record. Missing IDs return `404 remediation_not_found`.

### `PATCH /api/v1/remediations/{remediation_id}`

Accepts `action: "save" | "approve" | "reject"`, optional teacher `review_notes`, and optional `edited_content`. Source references are not accepted from the edit form and remain locked to the validated generation.

```json
{
  "action": "approve",
  "edited_content": {
    "misconception_summary": "Teacher-reviewed summary.",
    "learning_objective": "Teacher-edited objective.",
    "teacher_explanation": "Teacher-edited explanation.",
    "corrected_concept": "Teacher-edited concept.",
    "activity": "Teacher-edited activity.",
    "analogy": null,
    "follow_up_questions": [
      {"prompt": "Teacher-edited question.", "expected_answer": "Teacher-edited expected answer."}
    ]
  },
  "review_notes": "Approved after aligning wording with the class lesson."
}
```

Saving keeps status `generated`; approval or rejection is terminal and returns status `approved` or `rejected`. A later mutation returns `409 remediation_invalid_transition`.

Generation errors include `llm_not_configured`, `llm_timeout`, `llm_provider_unavailable`, `llm_malformed_output`, `llm_ungrounded_output`, and `llm_generation_failed`. Provider/schema/citation failure saves no remediation and never returns fabricated content.

## Follow-up results and comparison — implemented

Comparison resources and normalized follow-up assessments persist in PostgreSQL. Their linkage includes baseline/follow-up assessment and analysis IDs, selected groups, and the approved remediation.

### `POST /api/v1/results`

Multipart request fields:

- `file`: follow-up CSV using the existing assessment CSV contract
- `baseline_analysis_id`: an analysis snapshot returned by an earlier analysis request
- `group_id`: the selected baseline misconception group
- `remediation_id`: the explicitly approved intervention for that group

The service rejects missing resources, unapproved or mismatched interventions, assessment context changes, question/answer-key changes, and unknown student identifiers. It re-runs the existing misconception analysis on the follow-up answers; the route does not calculate metrics itself.

### `POST /api/v1/results/demo/photosynthesis`

Accepts the same three linkage IDs as JSON and analyzes the versioned synthetic fixture at `data/demo/photosynthesis_follow_up_responses.csv` through the production CSV parser. This endpoint does not return precomputed percentages.

### `GET /api/v1/results/{comparison_id}`

Returns the stored typed comparison. The verified demo result is:

```json
{
  "status": "completed",
  "metrics": {
    "before": {"answered_students": 43, "correct_students": 14, "affected_students": 9, "misconception_prevalence_percent": 20.9},
    "after": {"answered_students": 43, "correct_students": 33, "affected_students": 3, "misconception_prevalence_percent": 7.0},
    "matched_answered_students": 43,
    "missing_follow_up_students": 2,
    "prevalence_percentage_point_reduction": 13.9,
    "correct_percentage_point_change": 44.1,
    "transitions": {
      "baseline_affected": 9,
      "resolved_correct": 5,
      "changed_but_still_incorrect": 1,
      "still_struggling": 3,
      "missing_from_baseline_group": 0,
      "new_affected": 0
    }
  }
}
```

The full response also includes comparison/follow-up analysis IDs, source kinds, the matched follow-up group and matching method, question context, timestamps, and a trace containing assessment, group, remediation, and follow-up identifiers. If recurring follow-up membership cannot be identified reliably, status is `insufficient_data` and `metrics` is null—no improvement is inferred.

Domain errors include `initial_assessment_not_found`, `misconception_not_found`, `intervention_not_found`, `intervention_not_approved`, `results_context_mismatch`, `follow_up_assessment_mismatch`, `follow_up_question_missing`, `follow_up_question_mismatch`, `follow_up_student_mismatch`, and `results_not_found`. CSV and analysis/provider failures retain their existing structured contracts.
