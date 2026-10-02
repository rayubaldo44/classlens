# Decision Log

This log records decisions explicitly supplied for ClassLens and the choices still unresolved. It does not treat proposed details in other documents as accepted.

## Accepted decisions

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

## Unresolved decisions

| ID | Decision needed | Why it matters | Owner/trigger |
|---|---|---|---|
| U-009 | Explicit Node version policy | Needed for repeatable setup and CI with Vite 8. | Resolve before shared deployment/CI. |

When a decision is made, add a dated accepted entry with its rationale and update [TECH_STACK.md](TECH_STACK.md), [ARCHITECTURE.md](ARCHITECTURE.md), or [AI_PIPELINE.md](AI_PIPELINE.md) only where the decision changes their authority.
