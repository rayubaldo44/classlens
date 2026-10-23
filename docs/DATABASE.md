# Implemented Database Design

**Implementation status:** The golden-path PostgreSQL schema and repository adapters are implemented in `database/migrations/001_golden_path_persistence.sql`; the teacher group-review overlay and downstream reviewed-group provenance are added by `database/migrations/002_teacher_group_reviews.sql`. Both migrations and the database-gated integration test were verified against disposable PostgreSQL 17 on 2026-10-23. The original migration, full workflow, and restart recovery were also verified against configured Supabase PostgreSQL on 2026-10-02.

## Connection and security

FastAPI connects directly to Supabase PostgreSQL through `SUPABASE_DB_URL` using psycopg transactions. The pool disables automatic prepared statements (`prepare_threshold=None`) because the configured Supabase transaction pooler cannot safely retain session-scoped prepared-statement names. The value belongs only in ignored backend configuration and must never use a `VITE_*` name. All application tables have row-level security enabled with no browser policies; React accesses data only through FastAPI.

Apply the migration from the repository root:

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f database/migrations/001_golden_path_persistence.sql
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f database/migrations/002_teacher_group_reviews.sql
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
| `analysis_group_review_states` | Current revisioned reviewed-group overlay for an analysis; detected groups remain unchanged. |
| `analysis_group_review_events` | Append-only rename, merge, dismiss, and restore history with before/after state snapshots and optional teacher notes. |
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
                                      └─ review state + ordered review events

learning material ─ document chunks ─ intervention sources
analysis/reviewed group + original source groups ─ intervention ─ approved review state

baseline assessment ─ follow-up assessment ─ follow-up analysis
baseline analysis/reviewed group/source groups + approved intervention + follow-up analysis ─ comparison
```

- Foreign keys use restrictive deletion to avoid silently removing evidence or provenance.
- Imported student/question uniqueness is enforced per question/assessment.
- Analysis, material, and comparison IDs are deterministic, making safe retries idempotent.
- Lifecycle/status columns use checks; blank answers cannot be marked correct.
- Assessment/analysis/group/member writes and material/chunk writes use transactions.
- A review write locks the current state row, compares the expected state, and atomically updates the revisioned overlay plus one event. Stale concurrent actions fail without a partial history entry.
- Original detected group/member rows are immutable. Same-question merges materialize a new reviewed identity from the exact union of source groups and student members and record `coherence: null` because vectors are not recomputed.
- Interventions and comparisons store both the reviewed group identity and original source-group IDs. Any review action affecting evidence already used by a remediation is rejected.
- When pre-migration comparison JSON lacks `baseline_source_group_ids`, boundary validation restores the legacy single detected `baseline_group_id` as its sole source. This keeps existing saved comparisons valid after migration 002 without rewriting historical JSON.
- Teacher review updates preserve immutable generated content and reject changes after approval/rejection.
- Before generation, the application reloads the analysis/group and material/chunks through their PostgreSQL-backed repositories. Browser snapshot fields must match those records before Gemini is called; saved intervention source text, identifiers, indexes, and offsets are rebuilt from the canonical chunks.

## Analysis-write batching

The analysis save keeps one PostgreSQL transaction around the assessment, questions, responses, analysis run, groups, and members. Student-response inserts and misconception-member inserts use Psycopg `executemany()` within that transaction; the response `ON CONFLICT (question_id, student_key) DO NOTHING` rule and the existing analysis-run retry guard are unchanged. Psycopg 3.1 and later pipeline `executemany()` calls internally, reducing request/response round trips while preserving execution order and transaction handling ([Psycopg pipeline documentation](https://www.psycopg.org/psycopg3/docs/advanced/pipeline.html)).

A rollback-only benchmark against the configured Supabase instance used the synthetic 45-response result (4 groups, 18 members). The old per-row writer took 22.4 seconds in one trial. The batched writer took 4.02, 3.77, and 3.70 seconds across three trials (3.77-second median), an 83% reduction relative to that baseline. Each trial explicitly rolled back and a follow-up query found zero assessment rows for the generated benchmark ID. These are workload/network observations, not service-level latency guarantees.

## Vector decision

pgvector is intentionally not enabled. Material metadata and exact chunks persist in PostgreSQL, while normalized 384-dimensional embeddings remain a process-memory cache. After restart, the material adapter reloads chunks and the existing local embedding service rebuilds their vectors before exact cosine retrieval. The stored model identifier and dimension protect against incompatible indexes. This preserves restart behavior without replacing the verified retrieval algorithm or adding vector-schema risk for the tiny demo corpus.

## Failure behavior

- Missing `SUPABASE_DB_URL` returns `database_not_configured` instead of claiming a save.
- Connection/write failures return sanitized retryable database errors.
- Database constraints reject invalid relationships and duplicate incompatible records.
- Invalid CSVs fail before persistence.
- Generation/provider failures save no intervention.
- A comparison is never stored unless its baseline, follow-up analysis, group, and approved intervention exist.
