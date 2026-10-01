# Architecture

This document defines proposed system boundaries and data flow. The detailed AI algorithms belong in [AI_PIPELINE.md](AI_PIPELINE.md), database fields in [DATABASE.md](DATABASE.md), and endpoint payloads in [API.md](API.md). Except for the existing frontend scaffold, this architecture is not implemented.

## High-level design

```mermaid
flowchart LR
    T[Teacher browser] --> F[React + TypeScript frontend]
    F -->|HTTPS / JSON and file uploads| A[FastAPI application]
    A --> D[(Supabase PostgreSQL)]
    A --> E[Embedding service or model]
    A --> L[LLM provider]
    A --> X[Document extraction]
    D -. optional persistent vectors .-> V[pgvector]
    X --> A
```

The MVP should be one frontend and one modular backend. AI provider adapters and storage code remain internal modules, not separate services.

## Responsibilities and boundaries

### React frontend

- Collect files and teacher actions.
- Show upload previews, analysis progress, evidence, retrieved passages, remediation drafts, review controls, and results.
- Render structured errors and preserve safe unsent edits.
- Never hold provider or database service-role secrets.
- Avoid making educational conclusions independently of backend evidence.

### FastAPI application

- Validate all input regardless of client-side checks.
- Coordinate assessment ingestion, scoring, analysis, retrieval, generation, and review state.
- Enforce question-specific analysis and evidence provenance.
- Isolate model/provider calls behind adapters with timeouts and explicit failures.
- Return stable API resources and structured errors.
- Make retries idempotent where duplicate work or records would be harmful.

### PostgreSQL/Supabase

- Store assessments, questions, source responses, analysis results, material metadata/chunks, intervention revisions/state, and results.
- Enforce relationships and uniqueness needed for reproducible runs.
- Store vector columns only if persistence is justified by the demo design.
- Keep migration history once implementation begins; no schema has been created yet.

### AI and extraction adapters

- Embedding adapter: batch text inputs and return model/version metadata or an explicit failure.
- LLM adapter: accept constrained structured prompts and validate structured output.
- Document extractor: produce source text plus page/section metadata when the input format supports it.
- Retrieval module: rank teacher-provided chunks and apply a relevance threshold.

### Teacher

- Reviews whether a proposed group represents a useful educational misconception.
- Selects source material and assesses retrieved evidence.
- Edits and explicitly approves or rejects each intervention.

## Assessment-to-remediation flow

1. The frontend sends the assessment and CSV to FastAPI.
2. FastAPI validates, normalizes, and creates an assessment snapshot or preview.
3. After confirmation, the backend identifies eligible incorrect responses per question.
4. The analysis module embeds and groups those responses, then stores group membership and evidence.
5. The LLM adapter drafts a potential-misconception description from bounded evidence.
6. The frontend displays groups and representative responses to the teacher.
7. A teacher uploads or selects a learning material; the backend extracts, chunks, and indexes it.
8. Retrieval returns source passages relevant to the selected group.
9. The LLM adapter drafts remediation and follow-up questions constrained by the passages.
10. The teacher edits and approves or rejects the intervention.
11. Follow-up results are imported or recorded and compared with the baseline.

Long provider operations may initially use a simple request/response path if latency is acceptable. If they require job polling, add a small persisted job state within the FastAPI application rather than a new service.

## Proposed folder structure

This is a target, not a request to create empty files or directories.

```text
classlens/
├── frontend/
│   └── src/
│       ├── api/           # Typed HTTP client and contracts
│       ├── components/    # Shared presentational controls
│       ├── features/      # Intake, analysis, materials, review, results
│       └── pages/         # Golden-path screens
├── backend/               # Empty placeholder exists; contents are proposed
│   ├── app/
│   │   ├── api/           # FastAPI routes and request/response models
│   │   ├── core/          # Configuration and structured errors
│   │   ├── domain/        # Educational entities and rules
│   │   ├── services/      # Analysis, retrieval, remediation orchestration
│   │   ├── providers/     # Database, embedding, LLM, extraction adapters
│   │   └── main.py
│   └── tests/
├── data/
│   └── demo/              # Empty placeholders exist; fixtures are proposed
├── database/
│   └── migrations/        # Empty placeholder exists; migrations are proposed
├── scripts/               # Empty placeholder exists; demo/setup scripts are proposed
└── docs/
```

Create only the folders needed by an authorized implementation milestone.

## Security and privacy

- Put secrets in backend environment variables. Commit only variable names and safe examples.
- Never expose Supabase service-role credentials or AI provider keys to Vite (`VITE_*` values are client-visible).
- Validate file type, size, encoding, row limits, and content; do not trust extensions alone.
- Sanitize filenames and avoid executing or serving uploaded content as active HTML.
- Treat teacher documents and student responses as untrusted prompt content; delimit them and constrain model instructions.
- Minimize student data. The demo should use synthetic identifiers and responses.
- Avoid logging raw student responses, full documents, secrets, or provider payloads unless a deliberate local debug mode makes that safe and obvious.
- Return opaque internal error details to clients while logging a correlation identifier server-side.
- If Supabase is accessed directly from the browser later, define and test row-level security first. The preferred MVP boundary is browser → FastAPI → data store.

## Reliability approach

- Save valid input before slow AI work so retries do not require re-upload.
- Record provider/model and algorithm configuration with each analysis/generation.
- Use timeouts and bounded retries for transient provider failures.
- Preserve prior valid state when a later stage fails.
- Never substitute seeded or cached output silently. Label any fallback in the UI and demo script.
- Provide deterministic fixtures and a repeatable reset/seed path for the live demo.
