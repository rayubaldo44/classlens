# Technology Stack

This document is the authority for selected technologies, proposed dependencies, and unresolved technical selections. Package presence does not imply product capability; see [STATUS.md](../STATUS.md) for verified implementation state.

## Status labels

- **Confirmed:** explicitly selected for the project or already present in the repository.
- **Proposed:** a design direction that still needs implementation or validation.
- **TBD:** a decision is required before implementation should depend on it.

## Selected stack

| Layer | Choice | Status | Reason |
|---|---|---|---|
| Frontend | React + TypeScript + Vite | Confirmed; golden path implemented | Fast iteration and a strict typed UI. |
| Styling | Plain CSS | Confirmed and implemented | The current interface needs no styling framework. |
| Frontend motion | Motion for React (`motion`) | Confirmed; landing page implemented | Short entrance and interaction animations with reduced-motion support. |
| Backend | Python + FastAPI | Confirmed; golden path implemented | Fits AI/data tooling and provides typed HTTP contracts with OpenAPI. |
| Database | Supabase PostgreSQL via psycopg | Confirmed; live workflow and restart recovery verified | Direct transactions keep golden-path writes atomic and server-side. |
| Vector extension | None for MVP | Confirmed | Exact chunks persist; the tiny corpus is re-embedded into a process cache after restart. |
| Response embeddings | Local Sentence Transformers using `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Confirmed and verified | Lightweight 384-dimensional multilingual embeddings, no hosted inference secret, and adequate semantic separation on the demo fixture. |
| LLM | Google Gemini API using `gemini-3.1-flash-lite` | Confirmed; remediation adapter and live demo path verified | Stable free-tier model with structured JSON output, suitable demo latency, and an official Python SDK. |
| Retrieval corpus | Teacher-provided materials | Confirmed requirement | Keeps intervention grounding within teacher-selected sources. |
| Frontend deployment | Vercel | Confirmed; deployed with direct-route rewrites | Direct fit for the Vite frontend. |
| Backend deployment | Render Web Service | Confirmed; liveness/preview verified, analysis blocked by 512 MB RAM | Supports Python 3.11, but the current plan cannot hold the measured embedding runtime. |
| Continuous integration | GitHub Actions | Confirmed; workflow implemented and locally mirrored | Runs frontend and backend checks with a separate ephemeral PostgreSQL integration job. |
| Browser testing | Playwright + Chromium | Confirmed; deterministic golden-path smoke implemented | Exercises the connected React workflow in CI with contract-valid local API fixtures and no hosted-service or provider dependency. |

## Dependencies verified in the repository

`frontend/package.json` and the lockfile currently contain:

- React `^19.2.8` and React DOM `^19.2.8`
- Motion `^13.5.0` for landing-page animation
- Vite `^8.3.0` with `@vitejs/plugin-react`
- TypeScript `~6.0.2`
- ESLint 10 with TypeScript and React Hooks/Refresh plugins
- Playwright for the deterministic Chromium golden-path smoke

`backend/requirements.txt` and `backend/requirements-dev.txt` declare the maintained dependency ranges; `backend/requirements.lock` records the exact verified Python 3.11 development/test resolution:

- FastAPI `>=0.115,<1`, Uvicorn `>=0.30,<1`, and python-multipart `>=0.0.20,<1` for CSV uploads
- sentence-transformers `5.7.0` with the `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` model for local answer embeddings
- Google Gen AI SDK `>=1,<2` for Gemini structured remediation output and python-dotenv `>=1,<2` for ignored local backend configuration
- psycopg `>=3.2,<4` with binary and pool extras for direct server-side PostgreSQL access
- HTTPX `>=0.27,<1` and pytest `>=8,<9` for backend contract tests

Material ingestion and retrieval add no new runtime dependency: UTF-8 text decoding, chunking, the existing embedding service, and a PostgreSQL-backed `MaterialIndex` with a rebuildable in-memory vector cache use the current stack.

The frontend declares Node `>=22.12 <23` in `package.json`; `.nvmrc` records the verified `22.23.1` release. The installed npm version was `10.9.8`.

The AI runtime was verified with Python `3.11.16` and CPU-only PyTorch `2.13.0`; `backend/.python-version` records that Python patch release. Install the [hash-checked lock](../backend/README.md), which pins the official CPU wheel separately from the PyPI packages. The selected embedding model is pinned to Hugging Face commit `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`; the local runner warms it before health responds. No Supabase browser client, document-extraction, external clustering, or pgvector dependency is present.

## Dependency boundary

The implemented MVP uses the dependencies listed above plus Python's standard-library CSV parser and in-repository cosine/grouping code. Additional document extractors remain unselected; do not add them until an actual PDF/DOCX requirement is accepted and source-location preservation is designed.

## Unresolved decisions

| Decision | Needed before | Selection criteria |
|---|---|---|
| Additional material formats and extractors | Supporting PDF/DOCX beyond `.txt` | Demo document needs, source-location preservation, predictable extraction, and minimal dependencies. |

## Constraints

- Do not train a custom model for the MVP.
- Do not add microservices, Kubernetes, a separate vector database, or elaborate MLOps.
- Keep provider calls behind backend boundaries so secrets never enter the browser.
- Prefer deterministic fixtures, cached demo-safe outputs only when honestly labeled, and graceful provider failure.
