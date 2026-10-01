# Technology Stack

This document is the authority for selected technologies, proposed dependencies, and unresolved technical selections. Package presence does not imply product capability; see [STATUS.md](../STATUS.md) for verified implementation state.

## Status labels

- **Confirmed:** explicitly selected for the project or already present in the repository.
- **Proposed:** a design direction that still needs implementation or validation.
- **TBD:** a decision is required before implementation should depend on it.

## Selected stack

| Layer | Choice | Status | Reason |
|---|---|---|---|
| Frontend | React + TypeScript + Vite | Confirmed; scaffold present | Fast iteration, typed UI, and an existing scaffold. |
| Styling | CSS; Tailwind only if needed | Confirmed constraint; library choice open | Avoid adding a styling dependency without a concrete need. |
| Backend | Python + FastAPI | Confirmed; not initialized | Fits AI/data tooling and provides typed HTTP contracts with OpenAPI. |
| Database | Supabase PostgreSQL | Confirmed; not configured | Managed relational storage suitable for the hackathon. |
| Vector extension | pgvector | Proposed only if persistent retrieval is needed | Keeps vectors near relational metadata but adds setup that may be unnecessary for a small deterministic demo. |
| Response embeddings | Hugging Face embedding model | Confirmed provider family; exact model TBD | Supports semantic comparison without custom training. |
| LLM | Provider/model TBD | TBD | Must meet availability, latency, cost, structured-output, and grounding needs. |
| Retrieval corpus | Teacher-provided materials | Confirmed requirement | Keeps intervention grounding within teacher-selected sources. |
| Frontend deployment | Vercel | Confirmed; not configured | Direct fit for the Vite frontend. |
| Backend deployment | TBD | TBD | Select based on FastAPI support, cold-start behavior, setup time, and secret management. |

## Dependencies verified in the repository

`frontend/package.json` and the lockfile currently contain:

- React `^19.2.8` and React DOM `^19.2.8`
- Vite `^8.3.0` with `@vitejs/plugin-react`
- TypeScript `~6.0.2`
- ESLint 10 with TypeScript and React Hooks/Refresh plugins

The installed workspace was observed using Node `v22.23.1` and npm `10.9.8`. Vite's locked dependency metadata requires a compatible modern Node release; the project has not yet declared an explicit Node version policy.

No backend, Supabase, AI, document-extraction, clustering, or test dependency is confirmed by repository code yet.

## Proposed dependency categories

Select the smallest set after the related decisions are made:

- FastAPI server and ASGI runtime
- Request/settings validation compatible with the selected FastAPI version
- PostgreSQL/Supabase client and migration tool, if direct persistence is used
- CSV parsing from the Python standard library or a data library, based on schema complexity
- Hugging Face-compatible embedding inference client or local inference package
- Numerical/grouping library for the chosen algorithm
- LLM SDK with structured output support
- Extractors for only the teacher-material formats supported in the demo
- Backend testing and HTTP contract testing

These are categories, not approved packages. Record an accepted selection in [DECISIONS.md](DECISIONS.md) before treating it as fixed.

## Unresolved decisions

| Decision | Needed before | Selection criteria |
|---|---|---|
| Exact Hugging Face embedding model and execution mode | Misconception grouping and document embeddings | Semantic quality on short Grade 7 answers, latency, dimensionality, license, offline/cache behavior, and cost. |
| LLM provider/model | Group interpretation and remediation | Reliability, structured output, latency, cost, context size, rate limits, and key availability. |
| Grouping algorithm and thresholds | Analysis implementation | Works on small per-question samples, supports noise/outliers, produces stable demo results, and exposes meaningful support. |
| Scoring approach for free-text responses | Incorrect-response filtering | Deterministic enough for the demo, transparent, and compatible with answer keys/rubrics. |
| Supported material formats and extractor | Material upload | Demo document format, source-location preservation, predictable extraction, and minimal dependencies. |
| Persistent vectors vs in-memory demo index | Retrieval implementation | Dataset size, restart/reuse needs, Supabase readiness, and time remaining. |
| Backend host | Deployment | FastAPI support, cold starts, logs, environment secrets, time to deploy, and cost. |
| Node version policy | Shared setup/CI | Compatibility with locked Vite version and deployment environment. |

## Constraints

- Do not train a custom model for the MVP.
- Do not add microservices, Kubernetes, a separate vector database, or elaborate MLOps.
- Keep provider calls behind backend boundaries so secrets never enter the browser.
- Prefer deterministic fixtures, cached demo-safe outputs only when honestly labeled, and graceful provider failure.
