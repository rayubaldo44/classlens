# Golden Path Reliability Findings

## Teacher Group Review Findings — 2026-10-23

- Detected analysis groups remain immutable; teacher decisions are stored as a revisioned overlay and append-only events.
- Same-question merges union exact original source-group IDs and student members. Because response vectors are not persisted or recomputed, merged coherence is intentionally `null`.
- Retrieval, remediation, and comparison resolve the active reviewed identity server-side while preserving original source-group provenance.
- Review actions affecting evidence already used by a remediation fail with `group_review_locked`, preventing silent downstream retargeting.
- Migration 002 enables RLS on both review tables and keeps React behind the FastAPI/psycopg boundary with no browser database policies.
- The first Playwright launch failed only because the sandbox denied the local test-server port; the unchanged full suite passed with local-port permission.
- Verified totals: backend `105 passed, 1 skipped`; opt-in PostgreSQL integration `1 passed`; frontend unit suites, lint, build, and Playwright `5 passed`.
- Fresh review reproduced seven Important edge cases. The fix pass now rejects stale/no-op actions, closes the generation/review race, prevents incomplete merged-result claims, restores legacy provenance, removes the retrieval bypass, scopes locks per group, and makes restored review reads retryable.
- Minor deferred: show saved review notes and reviewed/source-provenance indicators in additional UI locations; current history and merged analysis controls retain the underlying data.

## Current P0 Findings — 2026-10-08

- Vercel SPA routing is deployed from commit `593e475`; production `/dashboard`, `/upload`, and `/analysis` return HTTP 200.
- Production preview and CORS pass, but ordinary analysis previously returned empty 502 responses after about 80–81 seconds and restarted Uvicorn three times during Hugging Face model loading.
- The local Python 3.11 model load plus a 29-response encode peaked at 1,113,784 KB RSS. Render's 512 MB plans are below this measured requirement; `1c-2g` is the smallest current web-service plan with sufficient nominal memory.
- The missing `HF_TOKEN` warning can affect Hub download rate limits but does not explain or solve the model's memory requirement.
- The local runner only owns processes it starts. An independently started Vite process on port 5173 prevents `demo.sh reset` from taking ownership; do not kill it without first resolving its origin.
- A fresh production recheck on 2026-10-08 still failed: health and Vercel direct routes passed, while ordinary analysis returned an empty HTTP 502 after 121.6 seconds. Do not repeat hosted analysis until the Render compute plan changes.
- After identifying both manual process groups as ClassLens Vite/FastAPI, they were stopped and `./scripts/demo.sh reset` established clean runner ownership of ports 5173 and 8000.
- The first local full browser run completed upload through results in 82.1 seconds, then exposed missing frontend handoff of restored analysis/retrieval state. Backend logs showed every restore request returned HTTP 200.
- `Analysis` and `Misconception` now initialize from persisted parent records and remount when those records arrive. A focused browser check passed `/analysis`, `/misconception`, `/intervention`, and `/results` reload recovery.
- The second ordinary-upload local run reached results in 79.2 seconds and completed all reload checks in 98.1 seconds. It reproduced 4 groups and the expected 9/43 before, 3/43 after, 13.9 percentage-point reduction.
- `docs/DEMO_FALLBACK.md` now provides the P0 provider fallback as a clearly labeled artifact from that verified run. It retains the actual evidence, provider/model, source references, teacher-approved intervention, and observed results while requiring the real provider failure to remain visible.

## Starting State
- Worktree was clean at campaign start.
- Current docs claim 58 passing backend tests, frontend lint/build success, real embeddings/RAG/Gemini behavior, PostgreSQL adapters, and an isolated PostgreSQL 16 persistence integration pass.
- Live Supabase migration/restart durability and a complete browser click rehearsal remain explicitly unverified.
- Existing planning files described the prior persistence milestone and were refreshed for this campaign.

## Discoveries
- Production dependencies resolve to PostgreSQL stores/indexes; in-memory implementations are retained only for dependency-overridden tests.
- Demo assessment/material/follow-up endpoints load versioned synthetic inputs and call the same parser, embedding, grouping, retrieval, and comparison services as uploads. No hardcoded output percentages or fake delays exist in application code.
- `backend/.env` is present with hidden Gemini and direct PostgreSQL configuration; no root/frontend environment file is required by the runner. `./scripts/demo.sh check` passes with Python 3.11 and dependencies.
- The UI still labels persisted material as held only in backend memory; that wording is stale.
- Reload restoration fetches analysis, retrieval, remediation, and comparison into parent state, but the Intervention component does not receive/restage a restored remediation. Reloading `/intervention` therefore cannot display its persisted review state.
- The runner's `reset` restarts services but intentionally preserves PostgreSQL and browser localStorage. It is a runtime restart, not by itself a clean workflow reset.
- Remediation requests carry retrieval text from the client. PostgreSQL validates IDs/foreign keys at save time, but the service does not compare supplied source text/offsets with authoritative stored chunks before sending the prompt. The normal UI path is honest, but this boundary should be hardened if scope permits.
- Live Supabase follow-up initially failed with `DuplicatePreparedStatement`; the persistent psycopg pool must disable session-scoped automatic prepared statements when using Supabase's transaction pooler.
- Gemini is intermittently returning controlled provider failures. One real grounded draft succeeded; repeated second-draft attempts failed, motivating a single bounded retry for transient statuses.

## Verified Results
- Supabase migration applied idempotently and the gated fresh-repository integration test passed.
- Live baseline preview reproduced 45 responses/students, 43 answered, 2 blank, 14 correct, and 29 incorrect.
- Real embeddings reproduced 4 groups, 18 grouped responses, 11 outliers, and the strongest 9-member sunlight-as-food group.
- Real retrieval returned persisted chunks 1/3/2 at 0.7840/0.5693/0.5417; the top text is exact teacher material.
- A real Gemini draft addressed sunlight-as-food, cited only chunks 1 and 2, remained generated until a teacher edit was saved and explicitly approved, and preserved the immutable original.
- After FastAPI restart, analysis evidence, approved edited remediation, material metadata/chunks, and cold-cache retrieval reloaded successfully.

## Known Blockers
- No blocker remains for the local golden path. Deployment was intentionally not attempted.

## Final Observations
- A full ordinary-upload run completed in about 82 seconds with real providers and persisted every golden-path resource.
- FastAPI restart and browser reload recovered analyses, evidence, material chunks, approval/rejection state, follow-up analysis, and comparison results; only material vectors are intentionally rebuilt.
- Actual results were 9/43 affected before (20.9%) and 3/43 after (7.0%), a 13.9-point reduction, with three still-struggling students visible.
- Intermittent Gemini 503s and one cold analysis stall remain operational risks. The code now retries Gemini once but continues to fail closed.
- Full browser automation was inconclusive because of test-harness synchronization/interruption; focused browser state checks passed, and a timed human rehearsal remains the next operational step.

## Deployment Findings — 2026-10-02

- The repository is a monorepo with the deployable Vite app under `frontend/`; there is no existing `vercel.json` or `.vercel` project link.
- The frontend requires a build-time public `VITE_API_URL`. Its fallback is `http://localhost:8000`, which is invalid for a public deployment.
- The FastAPI runtime imports `sentence-transformers==5.7.0` and CPU PyTorch and was verified only on Python 3.11. Current Vercel Python Functions offer Python 3.12–3.14, so the backend cannot be called deployment-ready without a compatibility/build/cold-start test.
- Vercel officially supports FastAPI, but Python functions have bundle/runtime constraints. Large Functions may accommodate bigger AI dependencies on eligible Fluid Compute projects, yet model download/cache behavior and ClassLens cold analysis remain reliability risks.
- Safe topology for an immediate reliable deployment is Vercel for `frontend/` plus a separately reachable FastAPI deployment. Deploying only the frontend before a public backend URL exists would produce an API-unavailable application.
- Vercel CLI is not installed globally; `npx` is available. No local Vercel project link exists.
- The public deployment URL could not be discovered from search, and the configured GitHub remote is not publicly readable. The live URL is required to inspect the built `VITE_API_URL` target and browser CORS behavior.
- Render backend `https://classlens-t6xn.onrender.com` is live. Direct verification on 2026-10-02 returned HTTP 200 from `/health` with `{"status":"ok","service":"classlens-api"}` and identified Uvicorn as the origin server.
- Vercel HTML points to `/assets/index-Bsbt1XBe.js`; inspection of that public bundle confirmed the compiled API URL is `https://classlens-t6xn.onrender.com`.
- A live `GET /health` with `Origin: https://class-lens-one.vercel.app` returned HTTP 200 but omitted `Access-Control-Allow-Origin`; an `OPTIONS` preflight from the same origin returned HTTP 400 `Disallowed CORS origin`. The preview domain `https://class-lens-nsnrffho0-arthurs-projects-7a8a5ea6.vercel.app` was likewise not allowed.
- Root cause: Render's currently running FastAPI CORS configuration does not include the frontend origin, likely because the environment variable is missing, singularly named, or has not been applied by restart/redeploy. App code reads `CLASSLENS_CORS_ORIGINS` (plural).
