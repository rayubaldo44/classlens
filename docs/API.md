# Proposed API

**Implementation status:** Proposed. No FastAPI application or endpoint exists as of 2026-10-01.

All paths, payloads, and status codes below are a versioned starting contract for the frontend and backend. Finalize the CSV/scoring and execution-model decisions before implementation. Base path: `/api/v1`.

## Conventions

- JSON uses `snake_case` to align with proposed Python models; the frontend should map through typed API contracts.
- Top-level persisted resource IDs are UUID strings. Imported `question_id`/`student_id` values and evidence display keys are validated external identifiers; implementation should name internal versus external identifiers unambiguously.
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

Expected domain outcomes such as `insufficient_data` or `no_relevant_material` should usually be successful resource states, not fabricated successes or generic server errors.

## Health

### `GET /health`

Proposed minimal readiness response:

```json
{
  "status": "ok",
  "service": "classlens-api"
}
```

Do not report external AI providers healthy unless the endpoint actually checks them; keep expensive provider diagnostics separate.

## Assessment upload

### `POST /assessments`

Creates a validated assessment snapshot from an assessment JSON part and a CSV file part. This first contract uses an atomic import: any invalid row rejects the import.

Multipart parts:

- `assessment`: JSON file or JSON string
- `responses`: CSV file

Proposed assessment JSON:

```json
{
  "title": "Photosynthesis Check",
  "subject": "Science",
  "grade_level": "7",
  "topic": "Photosynthesis",
  "questions": [
    {
      "question_id": "q1",
      "prompt": "How do plants use sunlight to make food?",
      "expected_answer": "Sunlight provides energy that plants use to make glucose from carbon dioxide and water."
    }
  ]
}
```

Proposed CSV header:

```csv
student_id,question_id,response_text,is_correct
S001,q1,Plants eat sunlight.,false
```

`is_correct` remains dependent on the unresolved scoring decision. It is shown here as the deterministic demo option.

`201 Created`:

```json
{
  "assessment_id": "9cb83ae7-8e28-4f0a-bf72-8314f838c6ac",
  "status": "ready",
  "summary": {
    "question_count": 1,
    "response_count": 45,
    "valid_count": 43,
    "blank_count": 2,
    "incorrect_count": 28
  },
  "questions": [
    {
      "question_id": "q1",
      "response_count": 45,
      "blank_count": 2,
      "incorrect_count": 28
    }
  ]
}
```

Common errors: `csv_parse_error`, `csv_missing_columns`, `unknown_question_id`, `duplicate_response`, `invalid_correctness_value`, `file_too_large`.

## Analysis

### `POST /assessments/{assessment_id}/analyses`

Starts analysis for a ready assessment.

```json
{
  "question_ids": ["q1"]
}
```

`202 Accepted`:

```json
{
  "analysis_id": "9cebf85e-ab22-477b-a97f-393b3c48b277",
  "status": "queued",
  "created_at": "2026-10-01T06:45:00Z"
}
```

### `GET /analyses/{analysis_id}`

Returns job state and group summaries. `status` is one of `queued`, `running`, `completed`, `failed`, or `insufficient_data`.

```json
{
  "analysis_id": "9cebf85e-ab22-477b-a97f-393b3c48b277",
  "assessment_id": "9cb83ae7-8e28-4f0a-bf72-8314f838c6ac",
  "status": "completed",
  "progress": {"stage": "complete", "completed_questions": 1, "total_questions": 1},
  "groups": [
    {
      "group_id": "c5ccbe27-bbcd-455c-80f2-943979a12e9c",
      "question_id": "q1",
      "title": "Sunlight treated as plant food",
      "support_count": 12,
      "eligible_response_count": 28,
      "confidence_label": "moderate",
      "interpretation_status": "available"
    }
  ],
  "outlier_count": 6
}
```

On provider failure, `status: "failed"` includes a sanitized `failure` object and no invented groups. An LLM-only interpretation failure may still return deterministic groups with `interpretation_status: "failed"`.

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

## Material upload

### `POST /assessments/{assessment_id}/materials`

Multipart parts:

- `file`: supported teacher material
- `display_name`: optional safe label

`202 Accepted`:

```json
{
  "material_id": "82fa50d6-0b92-48af-9652-6e6f797b6070",
  "status": "processing",
  "display_name": "Photosynthesis lesson notes.pdf"
}
```

### `GET /materials/{material_id}`

```json
{
  "material_id": "82fa50d6-0b92-48af-9652-6e6f797b6070",
  "status": "ready",
  "display_name": "Photosynthesis lesson notes.pdf",
  "chunk_count": 14
}
```

Common failed states/errors: `unsupported_material_type`, `material_too_large`, `extraction_failed`, `empty_extracted_text`.

## Remediation generation

### `POST /misconception-groups/{group_id}/remediations`

```json
{
  "material_ids": ["82fa50d6-0b92-48af-9652-6e6f797b6070"]
}
```

`202 Accepted`:

```json
{
  "intervention_id": "390f6d64-e040-4481-aa42-8d84a4a41f34",
  "status": "generating"
}
```

### `GET /interventions/{intervention_id}`

Returns `generating`, `draft`, `approved`, `rejected`, or `generation_failed` state. The client can poll this resource after a `202` response.

Completed resource example:

```json
{
  "intervention_id": "390f6d64-e040-4481-aa42-8d84a4a41f34",
  "status": "draft",
  "content": {
    "learning_objective": "Distinguish sunlight as an energy source from glucose as stored chemical energy.",
    "activity": "Use the supplied lesson diagram to trace energy from sunlight into glucose, then label what enters and what is produced.",
    "follow_up_questions": [
      {
        "prompt": "Is sunlight matter that a plant eats? Explain its role.",
        "expected_answer": "No. Sunlight supplies energy used to produce glucose."
      }
    ]
  },
  "sources": [
    {
      "passage_id": "chunk-04",
      "material_id": "82fa50d6-0b92-48af-9652-6e6f797b6070",
      "source_locator": {"page": 2, "section": "Energy and glucose"},
      "text": "Example placeholder for contract shape; implementation must return exact uploaded source text.",
      "relevance_score": 0.84
    }
  ]
}
```

The example source text above is explicitly a contract placeholder, not a claim that demo material or retrieval exists. If no passage meets the relevance rule, return a successful domain state such as:

```json
{
  "status": "no_relevant_material",
  "intervention_id": null,
  "message": "No passage in the selected material was relevant enough to ground remediation."
}
```

## Intervention review

### `PATCH /interventions/{intervention_id}`

Uses explicit review actions and optimistic concurrency.

```json
{
  "action": "approve",
  "expected_updated_at": "2026-10-01T07:10:00Z",
  "edited_content": {
    "learning_objective": "Distinguish sunlight as an energy source from glucose as stored chemical energy.",
    "activity": "Teacher-edited activity text.",
    "follow_up_questions": [
      {
        "prompt": "Teacher-edited question.",
        "expected_answer": "Teacher-edited expected answer."
      }
    ]
  },
  "review_notes": "Approved after aligning wording with the class lesson."
}
```

`action` is `save_draft`, `approve`, or `reject`. `200 OK` returns the updated intervention. Invalid transitions return `409 intervention_state_conflict`.

## Follow-up results and comparison

### `POST /assessments/{assessment_id}/follow-up-results`

Uploads a CSV with the frozen follow-up schema. For the proposed demo contract:

```csv
student_id,question_id,response_text,is_correct
S001,q1,Sunlight supplies energy used to make glucose.,true
```

`201 Created` returns imported, missing, rejected, and matched counts. Seeded results must use `source_kind: "demo_seed"`.

### `GET /assessments/{assessment_id}/results`

```json
{
  "assessment_id": "9cb83ae7-8e28-4f0a-bf72-8314f838c6ac",
  "source_labels": {"baseline": "demo_seed", "follow_up": "demo_seed"},
  "overall": {
    "baseline": {"correct": 17, "total_scored": 43, "percent": 39.5},
    "follow_up": {"correct": 31, "total_scored": 40, "percent": 77.5},
    "missing_follow_up": 3
  },
  "questions": [
    {
      "question_id": "q1",
      "baseline": {"correct": 17, "total_scored": 43, "percent": 39.5},
      "follow_up": {"correct": 31, "total_scored": 40, "percent": 77.5},
      "missing_follow_up": 3
    }
  ],
  "interpretation_note": "This before/after comparison does not by itself establish that the intervention caused the change."
}
```

These values illustrate response shape only and are not verified ClassLens results.
