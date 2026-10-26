# Architecture

This document defines system boundaries and data flow. The detailed AI algorithms belong in [AI_PIPELINE.md](AI_PIPELINE.md), database fields in [DATABASE.md](DATABASE.md), and endpoint payloads in [API.md](API.md). The React/FastAPI boundary, Supabase PostgreSQL repositories, and restart recovery were live-verified on 2026-10-02.

## Interactive repository diagrams

Generated with Archify on 2026-10-06 from committed revision `5fb327fd05973018c5dc3debb5c5dc826ccddd82`:

- [System architecture](../backend/.archify/architecture-classlens-20261006-095348/classlens-architecture.html) — browser, API, workflow services, local embeddings, Gemini, PostgreSQL adapters, durable records and ephemeral material vectors.
- [Assessment-to-results data flow](../backend/.archify/dataflow-classlens-20261006-095348/classlens-dataflow.html) — baseline intake, evidence, teacher-material retrieval, draft review and approval-gated follow-up comparison.

Both standalone HTML artifacts contain source links, explanatory notes, light/dark themes and export controls. Their finalization receipts passed showcase validation, strict artifact/provenance checks and real Chromium browser checks with no diagnostics. Light/dark screenshots were captured at 1440×900 and 2048×1320; manual inspection covered architecture at 1440 light/2048 dark and data flow at 1440 light/dark. The architecture uses vertical page scrolling at the smaller viewport.

Evidence is pinned to committed bytes. Existing uncommitted workspace UI, environment-example and documentation edits are noted in the artifacts, not represented as committed source. Reported Vercel/Render hosting remains documentation context; no live deployment verification was performed in this diagram task.

Implementation details that qualify the conceptual sections below: preview does not persist; analysis persists after successful grouping; correctness comes from validated CSV `is_correct`; document extraction currently accepts UTF-8 `.txt` only. Before Gemini generation, grounding reloads and compares canonical analysis/group/material/chunk evidence with the browser snapshot. In-memory stores are test doubles; runtime dependencies choose PostgreSQL adapters, and only material vectors remain ephemeral.

## High-level design

```mermaid
flowchart LR
    T[Teacher browser] --> F[React + TypeScript frontend]
    F -->|HTTPS / JSON and file uploads| A[FastAPI application]
    A --> D[(Supabase PostgreSQL)]
    A --> E[Local embedding model]
    A --> I[MaterialIndex protocol]
    I --> D
    I --> IM[(Process-local vector cache)]
    A --> L[Gemini API]
    A --> X[UTF-8 text ingestion]
    X --> A
```

The MVP remains one frontend and one modular backend. FastAPI services use repository/index protocols backed by PostgreSQL at runtime; in-memory implementations remain deterministic test doubles. Only material vectors are process-local and are rebuilt from persistent chunks after restart.

## Responsibilities and boundaries

### React frontend

- Collect files and teacher actions.
- Show upload previews, analysis progress, reviewable evidence groups and history, retrieved passages, remediation drafts, review controls, and results.
- Render structured errors and preserve safe unsent edits.
- Never hold provider or database service-role secrets.
- Avoid making educational conclusions independently of backend evidence.

### FastAPI application

- Validate all input regardless of client-side checks.
- Coordinate assessment ingestion, scoring, analysis, teacher group review, retrieval, generation, and intervention review state.
- Enforce question-specific analysis and evidence provenance.
- Keep detected groups immutable while validating revisioned rename, same-question merge, dismiss, and restore actions; lock affected actions once remediation exists.
- Isolate model/provider calls behind adapters with timeouts and explicit failures.
- Return stable API resources and structured errors.
- Make retries idempotent where duplicate work or records would be harmful.

### PostgreSQL/Supabase

- Stores assessments, questions, source responses, immutable analysis results, reviewed-group state/events, material metadata/chunks, intervention revisions/state, and results.
- Enforce relationships and uniqueness needed for reproducible runs.
- Do not store vectors for the tiny MVP corpus; rebuild the per-process cache from durable chunks.
- Apply the checked-in SQL migration with `psql` and keep future schema changes additive and reproducible.
- Disable psycopg automatic prepared statements for compatibility with the configured Supabase transaction pooler.

### AI and material adapters

- Embedding adapter: batch text inputs and return model/version metadata or an explicit failure.
- LLM adapter: accept constrained structured prompts and validate structured output.
- Text ingestion: validate and normalize UTF-8 `.txt` material while preserving exact chunk offsets. Rich document extraction remains unimplemented.
- Retrieval module: rank teacher-provided chunks and apply a relevance threshold.

### Teacher

- Reviews whether a proposed group represents a useful educational misconception.
- Selects source material and assesses retrieved evidence.
- Edits and explicitly approves or rejects each intervention.

## Assessment-to-remediation flow

1. The frontend sends the assessment and CSV to FastAPI.
2. FastAPI validates, normalizes, and creates an assessment snapshot or preview.
3. After confirmation, the backend identifies eligible incorrect responses per question using the explicit validated correctness field.
4. The analysis module embeds and groups those responses synchronously and derives the versioned deterministic analysis identity.
5. For a new non-empty baseline analysis, the LLM adapter receives all groups in one bounded request containing only question context, expected answers, and exact representative responses. The interpreter accepts only a complete schema-valid batch whose group and evidence identifiers match the supplied packet. A provider or validation failure converts the whole batch to deterministic fallback labels; database failures remain explicit.
6. The backend saves one canonical analysis snapshot containing the immutable evidence and either completed or fallback labels, then reloads that winner. Repeated or concurrent identical requests return the persisted wording without another label call.
7. The frontend loads the reviewed-group overlay. Before its first action, that view is derived from the immutable detected groups at revision zero.
8. The teacher may rename, dismiss, restore, or merge active same-question groups. FastAPI atomically saves the next overlay revision and an append-only before/after event; merges union exact source groups and members and expose no fabricated coherence value.
9. The teacher opens an active reviewed group. Its reviewed identity and original source-group IDs become downstream provenance, and review actions affecting that evidence lock after remediation exists.
10. A teacher uploads a `.txt` material or selects the synthetic demo notes; the backend cleans, chunks, embeds, and indexes it through `MaterialIndex`.
11. Retrieval queries only that material, ranks chunks by cosine similarity, filters by the configured threshold, and returns exact source text or an explicit insufficient-context result.
12. Before generation, the remediation service reloads the analysis, reviewed group, and material/chunks from PostgreSQL, rejects browser snapshots that do not match, and rebuilds the prompt from canonical evidence.
13. The Gemini adapter drafts schema-validated remediation and follow-up questions constrained by those passages; unknown passage references reject the complete draft.
14. PostgreSQL preserves both original generation and teacher-edited content; the teacher explicitly saves, approves, or rejects it.
15. Each completed analysis is already persisted with its normalized input and detected evidence groups; stable IDs make fixture reruns safe.
16. The teacher submits a follow-up CSV through the same validation pipeline and links it to the reviewed group and approved remediation.
17. The existing analysis pipeline re-evaluates follow-up responses. A dedicated comparison service validates the linkage, matches recurring group membership for the same question, and calculates deterministic counts and percentages.
18. The Results screen shows before/after values, transition counts, missing follow-up data, and the assessment → reviewed misconception/source evidence → intervention → follow-up trace without claiming causation.

Long provider operations currently use a simple synchronous request/response path. Remediation generation retries one transient timeout/429/5xx response; label generation uses one attempt within its separate 12-second default budget and degrades to persisted fallback labels. If latency later requires job polling, add a small persisted job state within the FastAPI application rather than a new service.

## Implemented repository layout

```text
classlens/
├── frontend/
│   └── src/
│       ├── api/           # Typed HTTP client, guards, and request reliability
│       ├── App.tsx        # Implemented golden-path screens and workflow state
│       └── components.tsx # Shared presentational controls
├── backend/               # Implemented modular FastAPI application
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── services/      # Analysis, retrieval, remediation orchestration
│   │   ├── providers/     # Database, embedding, LLM, and material adapters
│   │   ├── schemas/       # Pydantic API/domain boundary models
│   │   ├── config.py      # Environment configuration
│   │   └── main.py
│   ├── evaluation/        # Offline/live AI evaluation harnesses and cases
│   └── tests/
├── data/
│   └── demo/              # Deterministic assessment and synthetic teaching material
├── database/
│   └── migrations/        # Reproducible PostgreSQL migrations
├── scripts/               # Validated local demo runner
└── docs/
```

This describes the current high-level layout; source code remains authoritative for individual files.

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
