# ClassLens Status

**Last updated:** 2026-10-08

**Current phase:** Final P0 golden path verified locally; local demo selected while the paid Render upgrade is deferred

**Deadline context:** Hackathon MVP intended to be demo-ready tomorrow

## Verified working

- Repository-backed interactive architecture and data-flow diagrams were generated with Archify from commit `5fb327f` on 2026-10-06. Both passed showcase source/layout validation, strict artifact checks and Chromium browser checks with no diagnostics; selected light/dark captures were manually inspected. See [Architecture](docs/ARCHITECTURE.md#interactive-repository-diagrams). This verifies the diagrams, not a new application or hosted golden-path run.
- The public landing page is available at `/`, with a direct path to the teacher dashboard at `/dashboard` and a clearly labeled synthetic-demo path to `/upload`. The supplied mascot replaces the CL mark in the landing header, workspace sidebar, and favicon. Motion animates the landing entrance, section reveal, and button gestures; reduced-motion preferences suppress movement. Desktop and mobile Firefox captures, direct route loads, frontend lint, and production build passed locally.
- The teacher workspace now uses a compact, accessible step selector and visible API state on mobile. Shared headings, support text, buttons, and file-input focus styling received a small readability pass; desktop, 390px, and 320px Firefox captures, frontend lint/build, and the Impeccable detector passed locally. The landing page was unchanged.
- React 19, TypeScript, and Vite provide the teacher workflow at `/dashboard`, `/upload`, `/analysis`, `/misconception`, `/intervention`, and `/results`. FastAPI exposes the versioned workflow API and health endpoint.
- `scripts/demo.sh` validates configuration, selects the verified Python 3.11 runtime, starts or resets runner-owned FastAPI/Vite processes, configures matching API/CORS origins, records logs/PIDs, and checks service health.
- The versioned synthetic photosynthesis baseline contains 45 responses: 43 answered, 2 blank, 14 correct, and 29 incorrect. Real upload preview and normalization reproduced those values.
- CSV intake rejects empty files, missing/duplicate columns, inconsistent metadata, duplicate student/question pairs, invalid booleans, invalid encodings, unsupported files, and oversized input with structured errors. Blank answers remain visible but are excluded from grouping.
- Local `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` embeddings and deterministic complete-link cosine grouping run on real response text. With the configured `0.70` threshold and minimum support `3`, the baseline produced 4 groups, 18 grouped responses, and 11 outliers.
- The strongest group contained 9 of 29 eligible incorrect responses (students S001, S005, S009, S017, S021, S025, S033, S037, and S045). Representative responses are exact uploaded answers; unrelated answers remain separate or outliers.
- UTF-8 teacher material ingestion validates, normalizes, chunks, embeds, and persists the material. The verified photosynthesis text produced 3 chunks. Retrieval ranked exact source slices at cosine scores `0.7840`, `0.5693`, and `0.5417`; unrelated tectonics material returned `insufficient_relevant_context` with no fabricated source.
- Gemini `gemini-3.1-flash-lite` receives the detected group plus retrieved teacher passages through prompt `grounded_remediation_v1`. Structured output and chunk references are validated. One bounded retry is attempted for timeouts and transient 429/5xx responses; continued failure returns a controlled error and stores no draft.
- A real Gemini draft accurately distinguished sunlight energy from glucose food and cited only retrieved chunks 1 and 2. Teacher edits persisted separately from the original. One intervention was explicitly approved and another explicitly rejected; generated content was never auto-approved.
- The synthetic follow-up reuses the production CSV parser and analysis pipeline. It contains 44 rows: 43 answered, 1 blank, 1 baseline student absent, 33 correct, and 10 incorrect.
- Real comparison results were 9/43 affected before (`20.9%`) and 3/43 after (`7.0%`), a `13.9` percentage-point reduction. Correctness rose from 14/43 (`32.6%`) to 33/43 (`76.7%`), or `44.1` percentage points. Five original members resolved correctly, one changed but remained incorrect, and three remained in the recurring pattern.
- Supabase migration `database/migrations/001_golden_path_persistence.sql` applied successfully. The database-gated integration test passed against the configured Supabase PostgreSQL instance.
- A FastAPI restart and frontend reload recovered assessments, responses, misconception groups/evidence, material metadata/chunks, approved teacher edits, rejected state, follow-up analysis, and comparison results. Material vectors are intentionally ephemeral and rebuild from persisted chunks on first retrieval after restart.
- Browser verification covered dashboard navigation, API status, real preview/analysis rendering, restored approval/results after reload, backend-unavailable messaging, and 1440×1000 plus 390×844 layouts without page-level overflow.
- The final uninterrupted API run used the ordinary upload endpoints—not demo-output shortcuts—and completed baseline upload → analysis → teacher-material upload/retrieval → live Gemini generation → teacher edit/approval → follow-up upload/analysis → results in about 82 seconds.
- Final automated checks: backend `60 passed, 1 skipped` (the skipped test is the opt-in database integration, run separately and passed), frontend lint passed, frontend production build passed, and `git diff --check` passed before documentation updates.
- The frontend is provisioned at `https://class-lens-one.vercel.app`, and its deployed bundle targets `https://classlens-t6xn.onrender.com`. On 2026-10-02 at 03:48 UTC, live probes with the Vercel production origin verified HTTP 200 and matching `Access-Control-Allow-Origin` on Render health, synthetic photosynthesis preview, and upload POST preflight. Preview counts matched the expected 45 responses, 43 answered, 2 blank, 14 correct, and 29 incorrect.
- Earlier Render probes rejected the Vercel production origin; the latest live responses now allow it. No application code change was needed. A production browser reload and complete hosted golden-path smoke remain unverified; preview deployment origins were not checked in this verification.
- Vercel commit `593e475` added the documented SPA rewrite and deployed successfully on 2026-10-08. Direct production loads of `/dashboard`, `/upload`, and `/analysis` now return the application shell with HTTP 200; frontend lint and production build passed before deployment.
- A fresh local ordinary-upload browser run on 2026-10-08 completed upload through calculated results in 79.2 seconds. Direct reloads then recovered the analysis groups, retrieved teacher passages, approved intervention, and results; the full run and reload checks finished in 98.1 seconds. `Analysis` and `Misconception` now initialize from restored persisted records rather than showing empty state after the parent restore succeeds.
- [`docs/DEMO_FALLBACK.md`](docs/DEMO_FALLBACK.md) preserves an explicitly labeled, previously generated artifact from that verified local run for Gemini downtime. It includes real evidence, provider/model provenance, teacher-approved content, and calculated synthetic follow-up results, and instructs the presenter to keep the live provider failure visible.
- Commit `5115e5d` deployed the reload recovery and workspace polish to Vercel on 2026-10-08. The live bundle contains the new workflow-step selector/styles, and `/dashboard`, `/upload`, `/analysis`, `/misconception`, `/intervention`, and `/results` each return HTTP 200. Hosted state recovery remains unverified end to end because Render analysis still exits before creating the required persisted workflow.

## Remaining work outside this milestone

- The backlog was reorganized on 2026-10-08 into priority/category groups, retaining completed milestones and adding proposed stack-review hardening and pilot gates. See [TASKS.md](TASKS.md). Application behavior and hosted verification are unchanged.

- The paid Render upgrade is deferred for budget reasons. Use the verified local runner for the demo. Hosted analysis and reload verification remain open until a 2 GB plan is affordable.
- LLM-authored misconception labels are not implemented; labels remain deliberately generic and provisional.
- No seeded remediation is substituted into the application when Gemini fails. The separate, clearly labeled verified-run artifact is available for presentation continuity while the real provider failure remains visible.
- A timed human-operated three-minute stage rehearsal on the judging machine is still required. Browser automation verified the important screens/states but its full click-through was interrupted by brittle text synchronization and was not counted as a pass.

## Known issues and constraints

- Gemini and Supabase are network dependencies. Gemini produced intermittent transient 503 responses during verification; the bounded retry reduced but cannot eliminate that risk.
- Analysis, retrieval, generation, and database writes are synchronous. First embedding-model use and first post-restart material retrieval are slower because vectors are loaded/rebuilt.
- One cold live analysis request stalled beyond 180 seconds, while direct timing measured about 12.5 seconds for analysis and 28.7 seconds for its remote save. A later uninterrupted run passed; cold-start/network latency remains a judging risk.
- Hosted analysis is currently blocked by repeatable Render process termination. On 2026-10-08, two ordinary-upload analysis requests returned empty HTTP 502 responses after 80.4 and 81.4 seconds; each was followed by HTTP 503 `x-render-routing: hibernate-wake-error` until the service recovered. Render logs show the analysis reaching the unauthenticated Hugging Face model request, followed 14–42 seconds later by a fresh `uvicorn` start with a new PID and no completed analysis access log; this sequence occurred three times. A local Python 3.11 measurement of the same model plus a 29-response encode peaked at 1,113,784 KB RSS (about 1.11 GB), which exceeds Render's 512 MB Free and `0.5c-512mb` plans. The evidence strongly indicates memory-limit termination, although the active plan and memory graph still require dashboard inspection.
- The normal frontend passes retrieved text directly from the retrieval response. The generation service validates referenced chunk IDs and PostgreSQL relationships but does not independently re-read and compare every supplied chunk snapshot before the Gemini call. This is an API trust-boundary hardening opportunity, not an observed golden-path data-integrity failure.
- Material vectors are per-process by design; exact normalized source text, offsets, metadata, and all workflow records are durable.
- Python 3.11 with CPU-only PyTorch 2.7.1 is the verified backend runtime. The workspace Python 3.14 default is not supported by that stack.
- The local embedding model may contact Hugging Face on first download and warns when no `HF_TOKEN` is supplied. A token can improve Hub rate limits and download reliability, but it does not reduce the measured model memory requirement; the token remains optional for this public model.
- No destructive production reset endpoint exists. See [docs/DEMO.md](docs/DEMO.md#safe-demo-reset) for the safe deterministic reset procedure.
- Unused mock question, misconception, and response/evidence examples were removed from the frontend; `mockData.ts` now contains only scenario metadata used by the UI and route navigation definitions.

## Golden-path readiness

| Capability | Verified state |
|---|---|
| Initial CSV validation/normalization | Pass |
| Assessment and response persistence | Pass against Supabase |
| Real embedding/grouping and evidence | Pass |
| Teacher-material ingestion and real RAG | Pass |
| Grounded Gemini structured generation | Pass, with explicit controlled failure behavior |
| Teacher edit/approve/reject | Pass; never auto-approved |
| Follow-up validation/linkage/analysis | Pass |
| Before/after calculations and remaining students | Pass; manually checked |
| FastAPI restart and React reload | Pass, including analysis, retrieval, intervention, and results direct routes |
| Frontend lint/build and backend suite | Pass |
| Deployment | Partial: Vercel direct routes, production health, preview, and CORS pass; Render analysis repeatedly exits with 502/503 before the hosted browser golden path can continue |

**Overall:** the local ClassLens golden path is a verified PASS with real embeddings, Supabase persistence, source-backed retrieval, live Gemini generation, and direct-route recovery. Vercel routing and CORS are verified, but the hosted workflow cannot pass until Render has enough memory to load the embedding runtime. External-service capacity and two human-operated rehearsals on the presentation machine remain the principal operational risks.
