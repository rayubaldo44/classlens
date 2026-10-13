# Decision Log

This log records decisions explicitly supplied for ClassLens and the choices still unresolved. It does not treat proposed details in other documents as accepted.

## Accepted decisions

### D-027 — Bound and idempotently retry remediation generation

- **Status:** Accepted and implemented on 2026-10-13
- **Decision:** Limit Gemini remediation generation to 60 seconds total across the initial provider call, retry delay, and one retry, while retaining the 45-second per-attempt transport timeout. Abort the browser request after 70 seconds and reuse a session-scoped `generation_request_id` on manual retry. Derive the remediation ID from that identifier plus canonical analysis/group/material/chunk identifiers, check persistence, and serialize identical requests within the API process.
- **Reason:** Two independent 45-second attempts could exceed the teacher's expected wait, while aborting only in the browser can leave a successful server-side save whose blind retry creates another draft. A stable request identity gives both layers a clear time bound and makes retries safe.
- **Consequence:** Timed-out requests keep the selected evidence visible and offer manual retry. An identical retry returns the existing persisted draft and does not call Gemini again in the current process. The deterministic database ID prevents duplicate rows across processes, although separate processes could still perform the same provider work concurrently before one upsert wins.

### D-026 — Bound CSV intake before pairwise grouping

- **Status:** Accepted and implemented on 2026-10-13
- **Decision:** Accept at most 500 response rows per CSV and at most 100 eligible answered-incorrect responses per question. Reject either overage atomically before embedding or persistence with a structured HTTP 413 error containing actual and configured counts; the per-question error also identifies the question.
- **Reason:** Complete-link grouping compares response pairs within each question. A 100-response question has at most 4,950 pairs, giving the synchronous MVP an explicit workload ceiling while preserving the 45-row demo fixture unchanged.
- **Consequence:** Correct and blank responses still contribute to assessment summaries but do not consume the grouping limit. Teachers must reduce or split larger uploads before analysis.

### D-023 — Pin and warm the existing embedding model

- **Status:** Accepted and implemented locally on 2026-10-08; hosted warm-up deferred
- **Decision:** Keep the selected Sentence Transformers model and pin it to the already verified Hugging Face commit `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. Warm it during local FastAPI startup before health responds. Permit hosted startup warming only when the service has enough memory for the model.
- **Reason:** A mutable `main` model reference could change embeddings, while first-request loading delays the teacher workflow. Measured local peak RSS is about 1.11 GB; the current 512 MB Render plan cannot safely warm the model.
- **Consequence:** The local runner sets `CLASSLENS_WARM_EMBEDDING_MODEL=1`. Keep hosted warming disabled until capacity is sufficient; `/ready` reports model/database state independently of `/health` and does not call Gemini.

### D-022 — Pin the verified local runtimes and backend resolution

- **Status:** Accepted and implemented on 2026-10-08
- **Decision:** Use Node `>=22.12 <23` with verified release `22.23.1`, Python `3.11.16`, CPU-only PyTorch `2.7.1`, and the exact dependency versions in `backend/requirements.lock` for reproducible local setup.
- **Reason:** Vite 8 requires a modern Node runtime, and unconstrained Python resolution can change the large embedding stack or install unnecessary CUDA packages.
- **Consequence:** Install the lock, which explicitly selects the PyTorch CPU index and `torch==2.7.1+cpu`. Keep the short requirement manifests as the maintained inputs and regenerate/reverify the lock only during intentional dependency updates.

### D-021 — Use the verified local runner until hosted capacity is affordable

- **Status:** Accepted on 2026-10-08
- **Decision:** Defer the paid Render `1c-2g` upgrade and use `./scripts/demo.sh reset` plus the local frontend for the hackathon demo.
- **Reason:** The current budget does not allow the required hosted compute plan, while the complete local workflow and reload recovery already pass.
- **Consequence:** Keep hosted analysis tasks open, do not repeatedly retry the known 512 MB failure, and complete the remaining rehearsals on the presentation machine using the documented local runner and fallback artifact.

### D-019 — Motion for the public landing page

- **Status:** Accepted and implemented on 2026-10-02
- **Decision:** Use Motion for React for the landing page's brief entrance, section reveal, and button gestures. Respect the device's reduced-motion preference and keep primary content visible throughout the entrance.
- **Reason:** The user specifically requested the Motion library. The landing page benefits from a small amount of movement without affecting the teacher workflow.
- **Consequence:** `motion` is a frontend dependency; animation remains limited to the public landing page.

### D-020 — Supplied mascot as the ClassLens mark

- **Status:** Accepted and implemented on 2026-10-02
- **Decision:** Use the user-supplied mascot image as the visible ClassLens mark in the landing header, workspace sidebar, and favicon.
- **Reason:** The user provided the intended logo artwork.
- **Consequence:** The original image is stored as a public frontend asset and displayed within a white rounded frame that suits its opaque background.

### D-001 — React, TypeScript, and Vite frontend

- **Status:** Accepted; scaffold present
- **Decision:** Build the frontend with React, TypeScript, and Vite.
- **Reason:** The application is already scaffolded in `frontend/`, and the stack supports rapid typed UI development.
- **Consequence:** Extend the existing app; do not recreate it.

### D-002 — Python and FastAPI backend

- **Status:** Accepted; health foundation implemented
- **Decision:** Use Python with FastAPI for the backend.
- **Reason:** It fits the AI/data workload and provides explicit HTTP contracts.
- **Consequence:** Keep provider calls and secrets behind FastAPI.

### D-009 — Minimal backend runtime and local connection configuration

- **Status:** Accepted and implemented on 2026-10-01
- **Decision:** Use Uvicorn as the local ASGI runtime, configure allowed browser origins through `CLASSLENS_CORS_ORIGINS`, and configure the browser-visible API base URL through `VITE_API_URL`.
- **Reason:** This establishes the smallest explicit React-to-FastAPI boundary without selecting deployment infrastructure or adding secret-bearing frontend configuration.
- **Consequence:** Production deployment must set both values explicitly; `VITE_*` values remain public and must never contain secrets.

### D-016 — The demo runner extends configured origins instead of replacing them

- **Status:** Accepted and implemented on 2026-10-02
- **Decision:** `scripts/demo.sh` exports `CLASSLENS_CORS_ORIGINS` as the resolved frontend URL plus `http://localhost:${FRONTEND_PORT}`, so a local demo run always permits both the `127.0.0.1` and `localhost` spellings of the Vite origin. The runner must never replace the operator's configured origins with a single value. `get_cors_origins()` keeps its explicit-config-wins behavior.
- **Reason:** `load_dotenv(..., override=False)` makes an exported shell value beat `backend/.env`, so a single-origin export silently narrowed the allow-list. Opening the app at `http://localhost:5173` while the backend allowed only `http://127.0.0.1:5173` produced a browser-blocked CORS response that surfaced as a generic connection failure even though FastAPI was healthy. Changing the backend default instead would have contradicted D-009 by permitting localhost origins in production.
- **Consequence:** Local demo runs are reachable under either loopback spelling, including a custom port. `get_cors_origins()` is unchanged, so deployment must still set origins explicitly. Frontend connection failures state that the API may be stopped or blocked by CORS instead of instructing the operator to start an already-running backend. See [DEMO.md](DEMO.md) for the run instructions.

### D-010 — Single-file assessment and explicit correctness contract

- **Status:** Accepted and implemented on 2026-10-01
- **Decision:** The MVP uses one UTF-8 CSV containing assessment metadata, question context, stable student identifiers, answers, correct answers, and a required explicit `is_correct` boolean. Intake validates and normalizes a non-persistent preview; it does not infer correctness.
- **Reason:** A single deterministic file is faster to inspect and demo while still carrying the context required by the later scoring and misconception pipeline.
- **Consequence:** Repeated assessment/question metadata must remain consistent across rows. Blank answers cannot be marked correct. A later persistence milestone may split normalized data into relational entities without changing the source fixture.

### D-003 — Supabase PostgreSQL

- **Status:** Accepted and live-verified on 2026-10-02
- **Decision:** Use Supabase PostgreSQL for relational persistence.
- **Reason:** It provides managed PostgreSQL suitable for the hackathon schedule.
- **Consequence:** D-015 implements relational persistence without pgvector and adds the initial migration.

### D-004 — Embeddings support misconception grouping

- **Status:** Accepted and implemented at the detection layer
- **Decision:** Represent response meaning with embeddings and use semantic patterns to propose recurring groups among incorrect responses.
- **Reason:** Similar underlying ideas can be expressed with different wording.
- **Consequence:** Similarity alone does not prove a misconception. Question context, answer keys, representative responses, minimum support, and teacher review are required.

### D-011 — Local multilingual embeddings and conservative synchronous grouping

- **Status:** Accepted and implemented on 2026-10-01
- **Decision:** Embed eligible incorrect answer text locally with `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, then apply deterministic per-question complete-link cosine clustering with a default similarity threshold of `0.70` and minimum support of `3`. Run the small MVP analysis synchronously and keep the embedding adapter isolated.
- **Reason:** The 384-dimensional multilingual model is lightweight enough for the hackathon, avoids a hosted provider secret, and grouped paraphrased demo responses successfully. Complete-link clustering is understandable, prevents chaining through weak bridge responses, permits outliers, and needs no extra clustering library.
- **Consequence:** First use downloads model files; Python 3.11 with CPU-only PyTorch is the verified runtime. Results are provisional evidence groups, not diagnoses. The service returns generic deterministic labels until a separately approved LLM interpretation milestone. If latency grows beyond the small fixture, revisit job execution rather than adding it prematurely.

### D-012 — Plain-text learning material with replaceable retrieval index

- **Status:** Accepted and implemented on 2026-10-01
- **Decision:** Accept UTF-8 `.txt` learning material for the MVP. Clean and split it into configurable 900-character chunks with 120-character overlap, preferring paragraph/sentence/word boundaries. Reuse the current embedding adapter and exact cosine ranking through a `MaterialIndex` protocol. Use a process-local index with top-k `3` and minimum cosine score `0.42` for the current single-process demo.
- **Reason:** No PDF extractor, Supabase project, or database schema was ready. The user explicitly authorized an in-memory verification path while preserving a clean persistence boundary. Real demo evaluation returned relevant photosynthesis content at `0.784` and rejected an unrelated tectonic-plate query below threshold.
- **Consequence:** D-015 now persists document metadata/chunks while retaining vectors as a per-process rebuildable cache.

### D-005 — RAG grounds remediation

- **Status:** Accepted; retrieval and remediation grounding implemented
- **Decision:** Retrieve relevant passages from teacher-provided learning materials for remediation generation.
- **Reason:** The intervention should be grounded in material selected by the teacher.
- **Consequence:** RAG is not the primary misconception-detection mechanism, and no sufficiently relevant passage means no claim of grounded generation.

### D-006 — Teacher in the loop

- **Status:** Accepted; remediation review implemented with PostgreSQL persistence
- **Decision:** The teacher is the final authority over educational interpretation and intervention approval.
- **Reason:** AI output is a fallible proposal and educational context matters.
- **Consequence:** Show evidence and require explicit edit/approve/reject controls.

### D-013 — Gemini structured remediation with teacher review

- **Status:** Accepted and implemented on 2026-10-01
- **Decision:** Use the Google Gemini API with stable free-tier `gemini-3.1-flash-lite` behind an `LLMService` protocol. Generate against centralized prompt version `grounded_remediation_v1`, validate structured JSON with Pydantic, reject unknown chunk references, and persist generated/current review records through D-015.
- **Reason:** The user selected Gemini and relies on the free tier. `gemini-3.8-flash` and then `gemini-3.6-flash` returned explicit high-demand responses for the full grounded prompt; `gemini-3.1-flash-lite` supports the same structured output and passed the complete live generation and teacher-review workflow. The isolated adapter prevents application services from depending directly on Google SDK types.
- **Consequence:** `GEMINI_API_KEY` remains server-side. Provider failure saves no draft; successful drafts, edits, sources, and decisions persist.

### D-014 — Linked follow-up comparison

- **Status:** Accepted and implemented on 2026-10-01
- **Decision:** Reuse the complete assessment CSV parser and misconception-analysis pipeline for follow-up responses. Link each comparison to a saved baseline analysis, selected group, and explicitly approved remediation. Match the recurring follow-up pattern on the same question by greatest original-member overlap, requiring at least two overlapping members; otherwise return `insufficient_data` with no metrics. Calculate all counts and percentages deterministically over answered responses and report missing students separately.
- **Reason:** Follow-up group IDs and membership can change when students improve, while stable synthetic student IDs provide an inspectable comparison boundary. This closes the demo loop without a second parser, LLM-generated statistics, hardcoded percentages, or premature database infrastructure.
- **Consequence:** Results remain observational. D-015 now persists both analysis inputs and comparisons across backend processes.

### D-015 — Direct PostgreSQL persistence with rebuildable vector cache

- **Status:** Accepted, implemented, and live-verified against Supabase on 2026-10-02
- **Decision:** Access Supabase PostgreSQL only through FastAPI using server-side `SUPABASE_DB_URL` and psycopg transactions. Persist normalized assessments, analysis evidence, material chunks, interventions/review state, follow-up assessments, and comparisons. Keep document vectors as a process-memory cache rebuilt from persisted chunks.
- **Reason:** Direct transactions keep multi-table writes inspectable and atomic. The tiny demo corpus does not justify changing the verified exact-cosine retrieval path to pgvector.
- **Consequence:** React stores only resume IDs and reloads authoritative records from FastAPI. First retrieval after a backend restart re-embeds that material. Migration application, a fresh-repository integration test, FastAPI restart recovery, and React reload were verified against Supabase.

### D-017 — Supabase transaction-pooler compatibility

- **Status:** Accepted and implemented on 2026-10-02
- **Decision:** Configure psycopg pools with `prepare_threshold=None` for ClassLens database connections.
- **Reason:** A live follow-up write through the Supabase transaction pooler failed with `DuplicatePreparedStatement` because session-scoped automatic prepared statements can collide across pooled server sessions.
- **Consequence:** Queries remain parameterized but are not automatically promoted to named server-side prepared statements. A regression test protects the pool configuration.

### D-018 — One bounded Gemini retry

- **Status:** Accepted and implemented on 2026-10-02
- **Decision:** Make at most one delayed retry for Gemini timeouts and HTTP 429/500/502/503/504 responses; fail immediately for permanent errors and never synthesize fallback output.
- **Reason:** Live verification observed intermittent Gemini 503 responses while the same grounded request later succeeded. One bounded retry improves demo reliability without hiding prolonged provider failure or multiplying latency unpredictably.
- **Consequence:** A continued failure remains a retryable structured API/UI error and stores no remediation. A regression test verifies that one transient failure is retried exactly once.

### D-028 — Canonical server-side generation context

- **Status:** Accepted and implemented on 2026-10-13
- **Decision:** Keep the current typed browser generation request, but treat its class, group, material, and passage snapshots as assertions. Before calling Gemini, load the analysis/group and material/chunks from PostgreSQL, require all canonical-backed fields to match, and rebuild the prompt and saved source snapshots from those server records. Exclude the browser-provided retrieval similarity score from the prompt because retrieval-result scores are not persisted as canonical records.
- **Reason:** Browser state is useful for workflow continuity but cannot be the authority for student evidence or teacher-provided source text. Reusing the existing analysis and material stores closes that trust boundary without adding a retrieval-results table, another embedding pass, or a schema migration.
- **Consequence:** Missing canonical records return `404 remediation_context_not_found`; altered identifiers, evidence, metadata, chunk text, or offsets return `409 remediation_context_mismatch`. Both stop before Gemini and save nothing. Valid reload/retry requests keep the existing API shape and deterministic draft behavior.

### D-029 — Dependency-free frontend contract guards

- **Status:** Accepted and implemented on 2026-10-13
- **Decision:** Validate every nested workflow API response with small TypeScript type guards before rendering or storing it. Parse the local workflow pointer without casts, require its ordered identifier dependencies, and verify fetched restoration records still match the saved analysis/group/material/remediation chain.
- **Reason:** Static TypeScript types do not validate network JSON or local storage. The existing shallow checks could admit malformed nested evidence and stale cross-linked recovery state. The MVP contracts are small enough to validate without adding a schema library and its browser bundle/runtime surface.
- **Consequence:** Malformed success payloads become actionable `invalid_response` errors. Invalid saved pointers show a recovery panel, and stale downstream identifiers are trimmed to the last verified stage. Contract tests must change when an intentional API shape changes.

### D-030 — Secret-free PostgreSQL integration CI

- **Status:** Accepted and implemented on 2026-10-13
- **Decision:** Run frontend checks, backend unit tests, and PostgreSQL persistence integration as separate GitHub Actions jobs. The integration job starts an ephemeral PostgreSQL 17 service, applies the production migration, and uses disposable job-local credentials instead of Supabase secrets.
- **Reason:** Pull requests need database coverage without access to hosted credentials or data. Separating the job keeps ordinary backend failures distinct from migration and persistence failures.
- **Consequence:** Every push and pull request can verify the schema and persistence path without network access to production data. Failures appear under separate job names, and the ordinary backend job excludes the opt-in integration file to avoid duplicate coverage.

### D-031 — Contract-fixture browser smoke

- **Status:** Accepted and implemented on 2026-10-13
- **Decision:** Run the complete React golden path in Playwright Chromium against intercepted, recursively valid API responses. Use the real versioned upload files and UI controls, return one controlled generation failure before retry success, and restore the completed workflow through the normal persisted browser pointer and API reads.
- **Reason:** CI needs stable browser coverage of navigation and state transitions without consuming Gemini quota, loading the embedding model, or depending on Supabase and Render availability. Backend contracts and persistence retain their separate focused and PostgreSQL integration coverage.
- **Consequence:** The smoke proves frontend orchestration, review authority, error recovery, result rendering, and reload restoration. It does not replace a live provider/database end-to-end run or the human demo rehearsal.

### D-024 — Bounded process-local synchronous work

- **Status:** Accepted, implemented, and locally verified (2026-10-08)
- **Decision:** Run synchronous request work in a dedicated `ThreadPoolExecutor(max_workers=5)`, matching the configured PostgreSQL pool maximum. Serialize Sentence Transformer loading/encoding and lazy psycopg pool construction with process-local locks. Keep Gemini calls asynchronous.
- **Reason:** Analysis and other synchronous work must not block the ASGI event loop. The existing five-connection bound gives a conservative worker cap without adding a queue or dependency.
- **Consequence:** Each Uvicorn process owns its own executor, model lock, and pool lock. A local Uvicorn analysis completed in 19.3 seconds while `/health` responded in 1.3 ms. Backend verification passed with 65 tests and one opt-in database test skipped; the database integration had passed separately against Supabase. In-process ASGI tests keep a short event-loop heartbeat so executor completion callbacks are serviced in this environment.

### D-025 — Batch analysis response and group-member inserts

- **Status:** Accepted and implemented; measured against Supabase on 2026-10-09
- **Decision:** Use Psycopg `executemany()` for student-response and misconception-member rows within the existing analysis transaction. Keep statement order, response conflict handling, and the analysis-run retry guard unchanged.
- **Reason:** A 45-response, 4-group, 18-member analysis save took 22.4 seconds with per-row calls. Three rollback-only batched trials had a 3.77-second median.
- **Consequence:** The measured workload improved by about 83% versus the single pre-change trial. Three identical saves in one transaction yielded exactly one assessment, question set, response set, analysis, group set, and member set; rollback left zero assessment rows. This does not change the five-worker cap or database schema. The opt-in isolated-database integration remains skipped unless configured.

### D-007 — Focused MVP, not a full LMS

- **Status:** Accepted
- **Decision:** Build only the assessment-to-remediation golden path for the hackathon MVP.
- **Reason:** Reliability and a complete end-to-end demonstration are more valuable than feature breadth.
- **Consequence:** Defer the features in [TASKS.md](../TASKS.md#do-not-build-for-the-mvp).

### D-008 — Deployment direction

- **Status:** Accepted; services provisioned on 2026-10-02, hosted workflow verification pending
- **Decision:** Deploy the Vite frontend to Vercel, the persistent FastAPI service to Render, and relational data to Supabase PostgreSQL.
- **Reason:** Vercel fits the static Vite build. Render supports the verified Python 3.11 runtime and avoids forcing the PyTorch/sentence-transformer workload into an unverified serverless function lifecycle.
- **Consequence:** Gemini and database credentials remain only on Render. Vercel receives only the public `VITE_API_URL`; Render must explicitly allow the stable Vercel origin. Provisioning alone does not complete deployment—health, CORS, and the hosted golden path must pass after the committed branch redeploys.

When a decision is made, add a dated accepted entry with its rationale and update [TECH_STACK.md](TECH_STACK.md), [ARCHITECTURE.md](ARCHITECTURE.md), or [AI_PIPELINE.md](AI_PIPELINE.md) only where the decision changes their authority.
