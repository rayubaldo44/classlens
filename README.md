# ClassLens

**From grades to understanding.**

ClassLens is an AI-powered education hackathon MVP that helps teachers move from seeing *who* struggled to understanding *why*. It analyzes free-text student responses for recurring semantic patterns, presents representative evidence for teacher review, retrieves relevant passages from teacher-provided learning materials, and drafts targeted remediation grounded in those passages.

> Grades tell teachers who is struggling. ClassLens helps explain why.

## How it works

The planned MVP flow is:

1. A teacher uploads an assessment and a student-response CSV.
2. The system validates responses and identifies which answers need analysis.
3. Embeddings support question-specific grouping of semantically similar incorrect responses.
4. An LLM describes each potential misconception using the question, answer key, and representative responses.
5. The teacher inspects the evidence and selects or uploads instructional material.
6. Retrieval finds relevant passages; an LLM drafts a grounded activity and follow-up questions.
7. The teacher edits and approves or rejects the intervention.
8. Baseline and follow-up results are compared.

The teacher remains the final authority. Semantic similarity is a signal for investigation, not proof of a misconception. See the authoritative [product requirements](docs/PRODUCT.md) and [AI pipeline](docs/AI_PIPELINE.md).

## Technology

| Area | Choice | State |
|---|---|---|
| Frontend | React, TypeScript, Vite | Scaffold present; product UI not implemented |
| Backend | Python, FastAPI | Selected; not initialized |
| Database | Supabase PostgreSQL | Selected; not configured |
| Vector storage | pgvector, only if persistent retrieval is needed | Conditional proposal |
| Embeddings | Hugging Face model | Provider family selected; exact model TBD |
| LLM | Provider TBD | Unresolved |
| Deployment | Vercel frontend; backend host TBD | Planned; not configured |

Dependency details and open choices live in [docs/TECH_STACK.md](docs/TECH_STACK.md).

## Repository structure

```text
classlens/
├── frontend/           # Existing React + TypeScript + Vite scaffold
├── backend/            # Existing empty placeholder; FastAPI not initialized
├── data/demo/          # Existing empty demo-data placeholders
├── database/migrations/ # Existing empty migration placeholder
├── scripts/            # Existing empty placeholder
├── docs/               # Product, technical, AI, data, API, and demo specifications
├── AGENTS.md           # Stable instructions for future coding agents
├── README.md           # Project introduction and verified setup
├── STATUS.md           # Current verified repository state
└── TASKS.md            # Prioritized, dependency-aware backlog
```

No backend implementation, migration, demo fixture, or project script exists yet. The empty placeholders above do not count as initialized components.

## Verified frontend setup

The current workspace was verified on 2026-10-01 with Node `v22.23.1`, npm `10.9.8`, and the already-present dependencies. No dependency-install command has been verified during this documentation pass.

Start the existing Vite scaffold:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 4179
```

Run the verified checks:

```bash
cd frontend
npm run lint
npm run build -- --outDir /tmp/classlens-frontend-build
```

These commands validate the generated starter only. They do not demonstrate ClassLens features. For current readiness, see [STATUS.md](STATUS.md).

## Documentation

- [Product requirements](docs/PRODUCT.md) — vision, users, requirements, safeguards, and MVP boundaries
- [Technology stack](docs/TECH_STACK.md) — confirmed choices, proposed dependencies, and open selections
- [Architecture](docs/ARCHITECTURE.md) — system boundaries, data flow, proposed structure, and secrets
- [AI pipeline](docs/AI_PIPELINE.md) — proposed analysis, retrieval, grounding, evaluation, and failure behavior
- [Database](docs/DATABASE.md) — proposed minimal relational and vector model
- [API](docs/API.md) — proposed FastAPI contracts and error envelope
- [Decisions](docs/DECISIONS.md) — accepted and unresolved decisions
- [Demo guide](docs/DEMO.md) — reproducible photosynthesis scenario and three-minute flow
- [Status](STATUS.md) — verified present state and next priority
- [Tasks](TASKS.md) — implementation backlog and acceptance checks
