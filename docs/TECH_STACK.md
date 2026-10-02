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
| Backend | Python + FastAPI | Confirmed; health foundation implemented | Fits AI/data tooling and provides typed HTTP contracts with OpenAPI. |
| Database | Supabase PostgreSQL via psycopg | Confirmed; live workflow and restart recovery verified | Direct transactions keep golden-path writes atomic and server-side. |
| Vector extension | None for MVP | Confirmed | Exact chunks persist; the tiny corpus is re-embedded into a process cache after restart. |
| Response embeddings | Local Sentence Transformers using `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Confirmed and verified | Lightweight 384-dimensional multilingual embeddings, no hosted inference secret, and adequate semantic separation on the demo fixture. |
| LLM | Google Gemini API using `gemini-3.1-flash-lite` | Confirmed; remediation adapter and live demo path verified | Stable free-tier model with structured JSON output, suitable demo latency, and an official Python SDK. |
| Retrieval corpus | Teacher-provided materials | Confirmed requirement | Keeps intervention grounding within teacher-selected sources. |
| Frontend deployment | Vercel | Confirmed; service provisioned, API wiring pending verification | Direct fit for the Vite frontend. |
| Backend deployment | Render Web Service | Confirmed; `/health` live, full workflow pending verification | Supports the verified Python 3.11 runtime and a persistent FastAPI process for the local embedding model. |

## Dependencies verified in the repository

`frontend/package.json` and the lockfile currently contain:

- React `^19.2.8` and React DOM `^19.2.8`
- Vite `^8.3.0` with `@vitejs/plugin-react`
- TypeScript `~6.0.2`
- ESLint 10 with TypeScript and React Hooks/Refresh plugins

`backend/requirements.txt` and `backend/requirements-dev.txt` now declare:

- FastAPI `>=0.115,<1`, Uvicorn `>=0.30,<1`, and python-multipart `>=0.0.20,<1` for CSV uploads
- sentence-transformers `5.7.0` with the `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` model for local answer embeddings
- Google Gen AI SDK `>=1,<2` for Gemini structured remediation output and python-dotenv `>=1,<2` for ignored local backend configuration
- psycopg `>=3.2,<4` with binary and pool extras for direct server-side PostgreSQL access
- HTTPX `>=0.27,<1` and pytest `>=8,<9` for backend contract tests

Material ingestion and retrieval add no new runtime dependency: UTF-8 text decoding, chunking, the existing embedding service, and a PostgreSQL-backed `MaterialIndex` with a rebuildable in-memory vector cache use the current stack.

The installed workspace was observed using Node `v22.23.1` and npm `10.9.8`. Vite's locked dependency metadata requires a compatible modern Node release; the project has not yet declared an explicit Node version policy.

The AI runtime was verified with Python 3.11 and CPU-only PyTorch 2.7.1. Install the CPU wheel first as documented in `backend/README.md`; otherwise a default Linux resolver may download unnecessary CUDA packages. No Supabase browser client, document-extraction, external clustering, or pgvector dependency is present.

## Proposed dependency categories

Select the smallest set after the related decisions are made:

- FastAPI server and ASGI runtime
- Request/settings validation compatible with the selected FastAPI version
- CSV parsing from the Python standard library or a data library, based on schema complexity
- Hugging Face-compatible embedding inference client or local inference package
- Numerical/grouping library for the chosen algorithm
- Extractors for only the teacher-material formats supported in the demo
- Backend testing and HTTP contract testing

These are categories, not approved packages. Record an accepted selection in [DECISIONS.md](DECISIONS.md) before treating it as fixed.

## Unresolved decisions

| Decision | Needed before | Selection criteria |
|---|---|---|
| Additional material formats and extractors | Supporting PDF/DOCX beyond `.txt` | Demo document needs, source-location preservation, predictable extraction, and minimal dependencies. |
| Node version policy | Shared setup/CI | Compatibility with locked Vite version and deployment environment. |

## Constraints

- Do not train a custom model for the MVP.
- Do not add microservices, Kubernetes, a separate vector database, or elaborate MLOps.
- Keep provider calls behind backend boundaries so secrets never enter the browser.
- Prefer deterministic fixtures, cached demo-safe outputs only when honestly labeled, and graceful provider failure.
