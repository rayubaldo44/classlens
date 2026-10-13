# ClassLens

**From grades to understanding.**

ClassLens is an AI-powered education hackathon MVP for finding recurring, evidence-backed misconceptions in free-text responses, grounding a remediation in teacher-provided material, preserving teacher approval, and comparing understanding before and after the intervention.

The local Grade 7 photosynthesis workflow is implemented:

1. Validate a synthetic or teacher-uploaded assessment CSV.
2. Group recurring incorrect-answer patterns with local embeddings.
3. Inspect exact student evidence.
4. Retrieve passages from teacher-provided material.
5. Generate a source-locked Gemini remediation.
6. Edit and explicitly approve or reject it.
7. Re-analyze a follow-up assessment and show transparent before/after results.

Semantic grouping is evidence for teacher review, not a diagnosis. Before/after results describe observed change, not causal proof.

## Local demo

The verified backend runtime is Python 3.11. Complete the one-time backend setup and migration in [backend/README.md](backend/README.md), keep `GEMINI_API_KEY` and `SUPABASE_DB_URL` only in ignored `backend/.env`, and install frontend dependencies under `frontend/`.

From the repository root:

~~~bash
./scripts/demo.sh check
./scripts/demo.sh reset
~~~

Open http://127.0.0.1:5173, then follow [the demo guide](docs/DEMO.md). Reset stops only processes owned by the runner; PostgreSQL workflow records are preserved.

Useful commands:

~~~bash
./scripts/demo.sh status
./scripts/demo.sh stop
~~~

If a default port is occupied, choose another explicitly:

~~~bash
CLASSLENS_FRONTEND_PORT=4179 ./scripts/demo.sh reset
~~~

The runner validates Python 3.11 dependencies, frontend dependencies, required fixtures, the server-side Gemini key, port availability, and HTTP readiness. It does not print secrets, delete fixtures, or modify environment files.

## Technology

| Area | Current implementation |
|---|---|
| Frontend | React 19, TypeScript, Vite 8 |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Embeddings | Local sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| Grouping | Deterministic complete-link cosine clustering |
| Retrieval | Persistent UTF-8 chunks with a rebuildable exact-cosine vector cache |
| Remediation | Gemini gemini-3.1-flash-lite with structured validation and one bounded transient retry |
| State | PostgreSQL repositories; material vectors are a rebuildable process cache |
| Database | Supabase PostgreSQL migration, adapters, integration test, and restart recovery live-verified |
| Deployment | Vercel frontend and Render backend provisioned; hosted cross-origin workflow verification pending |

## Verified demo result

The deterministic follow-up fixture produces:

- before: 9 of 43 answered students affected (20.9%);
- after: 3 of 43 affected (7.0%);
- observed reduction: 13.9 percentage points;
- transitions: 5 resolved correctly, 1 changed but remained incorrect, and 3 still struggled;
- missing follow-up: 1 blank and 1 absent student.

These values are calculated from the parsed assessment data and follow-up analysis, not hardcoded in the UI.

## Repository map

~~~text
classlens/
├── frontend/             # Connected React teacher workflow
├── backend/              # FastAPI services, providers, schemas, and tests
├── data/demo/            # Versioned synthetic assessment/material fixtures
├── scripts/demo.sh       # Safe local check/start/reset/status/stop runner
├── database/migrations/  # Reproducible golden-path PostgreSQL schema
├── docs/                 # Product, architecture, API, AI, data, and demo guides
├── STATUS.md             # Current verified state
└── TASKS.md              # Remaining prioritized work
~~~

## Verification

GitHub Actions runs these checks on pushes and pull requests. PostgreSQL integration runs in a separate job against an ephemeral database after applying the repository migration.

~~~bash
cd backend
.venv/bin/python -m pytest -q --ignore=tests/test_postgres_integration.py

cd ../frontend
npm test
npm run lint
npm run build
~~~

The opt-in local PostgreSQL test remains available with `CLASSLENS_TEST_DATABASE_URL` configured:

~~~bash
cd backend
CLASSLENS_TEST_DATABASE_URL=postgresql://... .venv/bin/python -m pytest -q tests/test_postgres_integration.py
~~~

Run the deterministic browser smoke after installing Playwright Chromium once:

~~~bash
cd frontend
npx playwright install chromium
npm run test:e2e
~~~

The browser smoke intercepts API calls with contract-valid fixtures. It exercises the complete UI workflow and recovery behavior without contacting Gemini, Supabase, or Render.

For exact current readiness and limitations, read [STATUS.md](STATUS.md). The authoritative product and technical documents are linked from [AGENTS.md](AGENTS.md).
