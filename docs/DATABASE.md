# Proposed Database Design

**Implementation status:** Proposed. No database schema or migration exists as of 2026-10-01.

This document defines a minimal relational design for Supabase PostgreSQL. Names and fields should be finalized with the API contract before migrations are created. Use UUID primary keys and timezone-aware timestamps unless implementation evidence supports another choice.

## Design principles

- Keep source responses and teacher-provided passages traceable and immutable enough for audit.
- Version analysis/generation results rather than overwriting evidence after a rerun.
- Store only data needed for the golden path.
- Use synthetic student identifiers for the demo and avoid names or other unnecessary personal data.
- Add vector storage only when persistence is justified.

## Core tables

### `assessments`

| Field | Purpose |
|---|---|
| `id` | Primary key. |
| `title` | Teacher-facing assessment name. |
| `subject`, `grade_level`, `topic` | Context for display and prompts. |
| `source_kind` | For example `upload` or `demo_seed`. |
| `status` | Proposed lifecycle such as `draft`, `ready`, `analysis_pending`, `analyzed`, `failed`. |
| `created_at`, `updated_at` | Audit timestamps. |

### `questions`

| Field | Purpose |
|---|---|
| `id` | Primary key. |
| `assessment_id` | Foreign key to `assessments`. |
| `external_key` | Stable ID used by the import file. |
| `position` | Display order. |
| `prompt` | Exact question text. |
| `expected_answer` | Expected concept/answer for scoring and interpretation. |
| `rubric` | Optional structured or text rubric. |

Unique index: `(assessment_id, external_key)`.

### `student_responses`

| Field | Purpose |
|---|---|
| `id` | Primary key. |
| `question_id` | Foreign key to `questions`. |
| `student_key` | Privacy-safe identifier stable across baseline/follow-up. |
| `response_text` | Exact submitted text, including an explicit empty representation policy. |
| `normalized_text` | Optional derived value for processing; never replaces source text. |
| `response_status` | Proposed enum: `valid`, `blank`, `invalid`. |
| `is_correct` | Nullable result; null means unknown/unscored. |
| `score` | Optional transparent numeric result. |
| `scoring_source` | For example `imported`, `rule`, `teacher`. |
| `created_at` | Audit timestamp. |

Unique index: `(question_id, student_key)` for the initial one-response-per-student/question contract. Index `question_id` plus `is_correct` for analysis selection.

### `analysis_runs`

Needed to make reruns reproducible rather than silently overwriting groups.

| Field | Purpose |
|---|---|
| `id` | Primary key. |
| `assessment_id` | Foreign key to `assessments`. |
| `status` | `queued`, `running`, `completed`, `failed`, or `insufficient_data`. |
| `embedding_model` | Exact model/revision when known. |
| `algorithm_config` | JSON containing grouping metric/threshold/minimum support and preprocessing version. |
| `error_code`, `error_detail` | Sanitized failure information. |
| `started_at`, `completed_at` | Run timing. |

Index `(assessment_id, created_at desc)`.

### `misconception_groups`

| Field | Purpose |
|---|---|
| `id` | Primary key. |
| `analysis_run_id` | Foreign key to `analysis_runs`. |
| `question_id` | Foreign key to `questions`. |
| `title`, `description` | LLM-drafted potential misconception interpretation; nullable on LLM failure. |
| `support_count` | Stored summary verified against memberships. |
| `coherence_score` | Optional algorithm-specific evidence, not universal probability. |
| `confidence_label` | Cautious presentation such as `low`, `moderate`; definition must be documented. |
| `interpretation_status` | `pending`, `available`, or `failed`. |
| `teacher_status` | Optional review: `unreviewed`, `accepted`, `dismissed`. |
| `model_metadata` | JSON for LLM/model/prompt version without secrets. |
| `created_at` | Audit timestamp. |

Indexes: `analysis_run_id`, `question_id`.

### `misconception_group_memberships`

| Field | Purpose |
|---|---|
| `group_id` | Foreign key to `misconception_groups`. |
| `response_id` | Foreign key to `student_responses`. |
| `similarity_or_distance` | Algorithm-specific membership evidence. |
| `is_representative` | Whether selected for the summary view. |
| `representative_rank` | Optional display order. |

Primary/unique key: `(group_id, response_id)`. Index `response_id` for reverse lookup. The service must ensure group and response belong to the same question/run context.

### `learning_materials`

| Field | Purpose |
|---|---|
| `id` | Primary key. |
| `assessment_id` | Optional foreign key when material is assessment-specific. |
| `display_name`, `storage_path` | Safe metadata and private object-storage location. |
| `mime_type`, `byte_size`, `content_hash` | Validation, deduplication, and provenance. |
| `status` | `uploaded`, `processing`, `ready`, or `failed`. |
| `extraction_metadata`, `error_code` | Extractor/version details or sanitized failure. |
| `created_at` | Audit timestamp. |

Do not store uploaded binary documents in ordinary table columns unless a later decision justifies it; private Supabase Storage is a proposed fit.

### `document_chunks`

| Field | Purpose |
|---|---|
| `id` | Primary key. |
| `material_id` | Foreign key to `learning_materials`. |
| `ordinal` | Stable order within the extracted material. |
| `content` | Exact chunk text supplied to retrieval/generation. |
| `source_locator` | JSON with page, section, and offsets when available. |
| `content_hash` | Provenance/deduplication. |
| `embedding` | Optional pgvector column if persistent retrieval is selected. |
| `embedding_model` | Required when an embedding is stored. |
| `created_at` | Audit timestamp. |

Unique index `(material_id, ordinal)`. Add a vector index only after model dimension, distance operator, dataset size, and query pattern are fixed. For a tiny corpus, exact search may be simpler and more reliable than an approximate index.

### `interventions`

| Field | Purpose |
|---|---|
| `id` | Primary key. |
| `group_id` | Foreign key to `misconception_groups`. |
| `status` | `generating`, `draft`, `approved`, `rejected`, or `generation_failed`; generation never starts as approved. |
| `generated_content` | Original structured LLM draft. |
| `edited_content` | Teacher-edited structured content. |
| `generation_metadata` | LLM/model/prompt and retrieval configuration without secrets. |
| `review_notes` | Optional teacher notes. |
| `reviewed_at` | Explicit review timestamp. |
| `created_at`, `updated_at` | Audit timestamps. |

If multiple generation attempts must remain visible, add an `intervention_versions` table rather than overwriting `generated_content`. For the MVP, preserving one current intervention plus immutable metadata may be sufficient if the contract limits regeneration.

### `intervention_sources`

Join table connecting an intervention to the exact retrieved chunks used.

| Field | Purpose |
|---|---|
| `intervention_id` | Foreign key to `interventions`. |
| `chunk_id` | Foreign key to `document_chunks`. |
| `retrieval_rank`, `relevance_score` | Retrieval evidence. |

Primary key: `(intervention_id, chunk_id)`.

### `follow_up_results`

| Field | Purpose |
|---|---|
| `id` | Primary key. |
| `assessment_id` | Foreign key to `assessments`. |
| `question_id` | Foreign key to `questions`. |
| `student_key` | Matches the privacy-safe baseline identifier. |
| `response_text` | Optional exact follow-up answer. |
| `is_correct`, `score` | Transparent follow-up measure; nullable when missing. |
| `source_kind` | `recorded`, `upload`, or `demo_seed`. |
| `created_at` | Audit timestamp. |

Unique index `(assessment_id, question_id, student_key)` for one follow-up attempt in the initial MVP. If attempts are later needed, introduce attempt identity rather than weakening provenance.

## Relationships

```text
assessment 1─* questions 1─* student_responses
assessment 1─* analysis_runs 1─* misconception_groups
question 1─* misconception_groups
misconception_groups *─* student_responses (memberships)
assessment 1─* learning_materials 1─* document_chunks
misconception_group 1─* interventions *─* document_chunks (sources)
assessment/question 1─* follow_up_results
```

Use foreign-key delete behavior deliberately. For the MVP, application-controlled deletion or restrictive defaults are safer than broad cascades that could erase provenance unexpectedly.

## pgvector decision

Use pgvector only if document or response embeddings must persist across restarts or be queried through PostgreSQL. If the live demo uses one small material and can deterministically rebuild an in-memory index, pgvector may add setup without meaningful benefit. If selected:

- fix embedding dimensions per column/model;
- use the distance operator supported by the model's training and normalization;
- store the model identifier beside vectors;
- isolate incompatible model versions;
- verify exact retrieval before adding an approximate index.

No vector schema or index should be created until [DECISIONS.md](DECISIONS.md#unresolved-decisions) records this choice.
