# Supabase Persistence Findings

## Active Findings
- `InMemoryAnalysisStore` holds normalized baseline/follow-up inputs and completed analysis snapshots.
- `InMemoryMaterialIndex` holds learning-material metadata, exact chunks, and vectors.
- `InMemoryRemediationStore` holds generated content, teacher edits, review state, and source snapshots.
- `InMemoryResultsStore` holds comparison records; all four stores are erased on FastAPI restart.
- No migration exists. Direct transactional persistence requires a new server-only `SUPABASE_DB_URL`; `psql` is installed but the Supabase CLI is not.
- React keeps all workflow objects and IDs in component state, so browser reload loses its pointers.
- The CSV has no class identity; follow-up responses should be a linked assessment; intervention source snapshots remove the need for a retrieval-events table.
- Baseline checks pass: 55 backend tests, frontend lint, and frontend build.

## Prior Milestone Findings

# Demo Hardening Findings

## Confirmed State
- All eleven local golden-path capabilities are implemented and the service chain was live-verified in one backend process.
- Analysis, materials, remediation, and results state is process-local and disappears when that backend process exits.
- `docs/DEMO.md` is stale at the top and still describes implemented fixtures/UI as planned.
- Remaining P0 items are the repeatable reset/start procedure, browser rehearsal, deployment, and the pre-demo checklist.
- Backend hosting and durable Supabase/pgvector persistence remain unresolved and are out of scope for this continuation.

## Constraints
- Python 3.11 is the verified backend runtime; the system Python 3.14 is incompatible with the embedding stack.
- Gemini free-tier availability can vary. Failures must remain explicit and cannot be replaced silently.
- The procedure must keep `GEMINI_API_KEY` server-side and must not print it.

## Audit Findings
- `scripts/` has no existing implementation; root and backend READMEs do not provide a whole-stack start/reset command.
- `frontend/node_modules` is present and Firefox 156 is installed, but Playwright, Puppeteer, Selenium, and `geckodriver` are absent.
- The frontend defaults to `http://localhost:8000`; the reset runner should set `VITE_API_URL` explicitly to match its backend bind address.
- All four mutable state boundaries are process-local singletons. Restarting the owned backend process is a complete safe state reset; no data deletion endpoint is needed.
- The attempt to inspect `backend/app/providers/material_index.py` failed because the implementation is a package at `backend/app/providers/material_index/`; subsequent inspection must use the package files.
- Port 5173 has a pre-existing user Vite process. The runner's collision protection left it untouched; the isolated rehearsal can use port 4179 with matching generated CORS.
- The first real headless Firefox run verified dashboard navigation and the backend-backed intake preview (45 students, 29 incorrect, 2 blank). Its only failure was browser-driver interaction with a below-fold control, not an application/API error.
- Three WebElement/DOM interaction strategies all stalled on the below-fold transition despite the enabled control appearing in captured HTML. Browser automation cannot verify the rest of the click path in this environment; manual browser rehearsal remains required.
