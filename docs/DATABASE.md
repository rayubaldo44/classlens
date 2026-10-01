# Implemented Database Design

**Implementation status:** The golden-path PostgreSQL schema and repository adapters are implemented in `database/migrations/001_golden_path_persistence.sql`. Local contract tests pass. Applying the migration to Supabase and proving restart persistence remain unverified until a server-side `SUPABASE_DB_URL` is configured.

## Connection and security

FastAPI connects directly to Supabase PostgreSQL through `SUPABASE_DB_URL` using psycopg transactions. The value belongs only in ignored backend configuration and must never use a `VITE_*` name. All application tables have row-level security enabled with no browser policies; React accesses data only through FastAPI.

Apply the migration from the repository root:

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f database/migrations/001_golden_path_persistence.sql
```

## Implemented tables

| Table | Golden-path purpose |
|---|---|
| `assessments` | Baseline or follow-up metadata, source label, preview snapshot, and optional baseline link. |
| `questions` | Stable imported question key, position, prompt, and correct answer for an assessment. |
| `student_responses` | Exact normalized response, stable student key, blank/answered state, and imported correctness. |
| `analysis_runs` | Existing public analysis ID, assessment link, model/grouping configuration, status, and response snapshot. |
| `misconception_groups` | Question-specific evidence group belonging to one analysis run. |
| `misconception_members` | Group-to-response membership and representative evidence metadata. |
| `learning_materials` | Content-derived material identity, source metadata, chunk settings, and embedding model metadata. |
| `document_chunks` | Exact normalized chunk text, stable chunk ID, order, offsets, and hash. |
| `interventions` | Analysis/group link, original generation, teacher-edited content, review state, and generation provenance. |
| `intervention_sources` | Ranked retrieved chunks plus immutable text/offset/score snapshots used for generation. |
| `assessment_comparisons` | Baseline/follow-up analyses, selected groups, approved intervention, method, metrics, and trace snapshot. |

The application does not create `classes` because the implemented intake contract has no class identity. Follow-up answers are a linked `assessments` row with ordinary questions and responses, so a separate `follow_up_results` table would duplicate source data. Retrieved evidence is preserved by `intervention_sources`; a standalone retrieval-events table is not needed for the MVP.

## Relationships and constraints

```text
baseline assessment ─┬─ questions ─ student responses
                     └─ analysis run ─ misconception groups ─ members

learning material ─ document chunks ─ intervention sources
analysis/group ─ intervention ─ approved review state

baseline assessment ─ follow-up assessment ─ follow-up analysis
baseline analysis/group + approved intervention + follow-up analysis ─ comparison
```

- Foreign keys use restrictive deletion to avoid silently removing evidence or provenance.
- Imported student/question uniqueness is enforced per question/assessment.
- Analysis, material, and comparison IDs are deterministic, making safe retries idempotent.
- Lifecycle/status columns use checks; blank answers cannot be marked correct.
- Assessment/analysis/group/member writes and material/chunk writes use transactions.
- Teacher review updates preserve immutable generated content and reject changes after approval/rejection.

## Vector decision

pgvector is intentionally not enabled. Material metadata and exact chunks persist in PostgreSQL, while normalized 384-dimensional embeddings remain a process-memory cache. After restart, the material adapter reloads chunks and the existing local embedding service rebuilds their vectors before exact cosine retrieval. The stored model identifier and dimension protect against incompatible indexes. This preserves restart behavior without replacing the verified retrieval algorithm or adding vector-schema risk for the tiny demo corpus.

## Failure behavior

- Missing `SUPABASE_DB_URL` returns `database_not_configured` instead of claiming a save.
- Connection/write failures return sanitized retryable database errors.
- Database constraints reject invalid relationships and duplicate incompatible records.
- Invalid CSVs fail before persistence.
- Generation/provider failures save no intervention.
- A comparison is never stored unless its baseline, follow-up analysis, group, and approved intervention exist.
