# ClassLens Status

**Last updated:** 2026-10-02
**Current phase:** Supabase persistence implemented locally; live migration and restart verification await `SUPABASE_DB_URL`
**Deadline context:** Hackathon MVP intended to be demo-ready tomorrow

## Verified working

- On 2026-10-02, an API-unavailable report was traced to a stopped backend while Vite was running on `localhost:5173`. Restarting Uvicorn on `127.0.0.1:8000` restored HTTP 200 health responses with CORS headers for both local origins and the synthetic assessment preview (45 students, 29 incorrect, 2 blank). The sidebar checks health on mount, so reload the page after recovery. This API was started directly, outside the demo runner's process tracking.
- A React 19 + TypeScript + Vite 8 scaffold exists in `frontend/`.
- The scaffold's Vite development server starts and serves HTML locally.
- A typed, responsive ClassLens UI skeleton covers Dashboard, Upload Assessment, Learning Gaps, Misconception Detail, Intervention Review, and Results.
- The documented photosynthesis UI path is clickable end to end using explicit demo/mock labels and no fabricated dataset counts, retrieved passages, or provider output.
- Reusable loading, empty, and error-state patterns are present; the upload screen demonstrates all three states.
- A minimal FastAPI application starts from `backend/` and exposes `GET /health` with the documented stable response.
- Backend CORS permits the configurable local Vite origins, and automated tests cover the health contract and local-origin response header.
- The demo runner now extends the configured origins instead of replacing them, so a local run permits both `http://127.0.0.1:5173` and `http://localhost:5173`. Verified on 2026-10-02: both origins return `access-control-allow-origin` for the demo preview GET and a `POST` preflight.
- Frontend connection failures now state that the API may be stopped or the origin blocked by CORS instead of instructing the operator to start a backend that may already be running.
- The frontend uses a typed, runtime-validating API client configured by `VITE_API_URL` and renders checking, connected, and unavailable health states.
- Live verification confirmed Uvicorn startup, Vite startup, the health response, Vite environment injection, and the CORS preflight between the configured local origins under both loopback spellings.
- Browser-history navigation exposes `/`, `/upload`, `/analysis`, `/misconception`, `/intervention`, and `/results`; all six returned HTTP 200 from the local Vite server on 2026-10-01.
- A documented single-file CSV contract carries assessment metadata, question context, stable student IDs, source answers, correct answers, and explicit correctness.
- A versioned 45-student synthetic photosynthesis fixture includes 43 answered, 2 blank, 14 correct, and 29 eligible incorrect responses plus an evaluation manifest.
- FastAPI validates file extension, 1 MB size limit, UTF-8 encoding, required/duplicate columns, row shape, required values, metadata consistency, question consistency, duplicate student/question responses, and explicit blank answers.
- `POST /api/v1/assessments/preview` returns a typed non-persistent normalized preview; `GET /api/v1/assessments/demo/photosynthesis/preview` exercises the same parser against the versioned fixture.
- The Upload Assessment screen uses the real API for both teacher-selected CSV files and the synthetic demo, with no-file, selected, uploading, success, validation-error, and network-error states.
- Correct and blank responses are preserved in counts but excluded from semantic grouping through the validated `is_correct` boundary.
- A provider-isolated local embedding service uses `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` and validates vector count, dimensions, finite values, and magnitude.
- `POST /api/v1/assessments/analyze` and `GET /api/v1/assessments/demo/photosynthesis/analysis` synchronously return typed question-specific evidence groups, outliers, model/grouping metadata, and safe insufficient/error outcomes.
- Deterministic complete-link cosine clustering uses configurable defaults of `0.70` similarity and minimum support `3`; no response phrase or photosynthesis misconception is hardcoded in detection.
- The Analysis and Misconception Detail screens use real backend results, show exact representative evidence and member identifiers, and retain teacher-review caveats. Loading, empty, and network/provider error states are implemented.
- Real-model verification produced 4 groups from 29 eligible incorrect responses: 18 grouped and 11 retained as outliers. The strongest 9-response group contains differently worded sunlight-as-food answers; soil-food and two distinct carbon-dioxide error groups also met support.
- A labeled synthetic Grade 7 photosynthesis teaching text is available under `data/demo/learning_materials/` with accurate content on sunlight as energy, glucose production, carbon dioxide/water inputs, and roots absorbing water/minerals.
- FastAPI accepts UTF-8 `.txt` learning material up to 1 MB, normalizes whitespace, chunks with configurable paragraph/sentence/word-aware 900-character windows and 120-character overlap, and keeps source offsets.
- Learning-material chunks reuse the existing local multilingual embedding adapter; no second embedding implementation or new runtime dependency was added.
- Material ingestion and retrieval remain behind `MaterialIndex`; runtime metadata/chunks use PostgreSQL while vectors are rebuilt into a process cache after restart. pgvector is intentionally not used.
- `POST /api/v1/learning-materials/ingest`, `POST /api/v1/learning-materials/demo/photosynthesis/ingest`, and `POST /api/v1/learning-materials/{material_id}/retrieve` return typed material/source data and structured errors.
- Retrieval ranks exact cosine similarity, defaults to top-k 3 and minimum score 0.42, and returns `insufficient_relevant_context` with no chunks when nothing meets the threshold.
- Real-model verification ingested the demo notes into 3 source-backed chunks. A real detected sunlight-as-food group retrieved relevant teaching content first at cosine 0.784; other returned chunks scored 0.5693 and 0.5417. An unrelated tectonic-plate query returned no context.
- The Misconception Detail UI lets teachers load demo notes or ingest a `.txt`, request supporting passages, inspect exact source text/filename/chunk/score/offsets, and distinguish Teaching Material from Student Evidence. Intervention Review carries the selected group and sources into grounded generation.
- A provider-isolated Gemini LLM service targets stable free-tier `gemini-3.1-flash-lite`, loads its key only from backend environment configuration, uses centralized prompt version `grounded_remediation_v1`, and validates structured output with Pydantic.
- `POST /api/v1/remediations`, `GET /api/v1/remediations/{id}`, and `PATCH /api/v1/remediations/{id}` use durable remediation/review records with analysis/group and source-chunk foreign keys.
- Generation fails closed when retrieval is insufficient, the provider is unavailable, output is malformed, or returned source IDs do not match supplied chunks. Original generated content, current teacher edits, exact source snapshots, provider/model/prompt metadata, notes, and timestamps remain separately inspectable.
- Intervention Review shows the complete reasoning chain—student evidence, exact teacher sources, AI-generated fields, and teacher decision—and implements loading, insufficient-context, provider/network error, pending-review, approved, and rejected states.
- Live verification with `gemini-3.1-flash-lite` generated an accurate intervention for the 9-response sunlight-as-food group, referenced only retrieved chunks 1 and 2, preserved a teacher edit, explicitly approved one record, and explicitly rejected a separate generated record.
- A clearly labeled synthetic follow-up fixture reuses the baseline 45-student cohort and existing CSV contract: 44 rows, 43 answered, 1 blank, 1 absent, 33 correct, and 10 incorrect. It includes corrected, partially improved, still-struggling, and correct responses.
- Completed analyses, normalized responses, follow-up assessments, and comparisons have PostgreSQL repository adapters. Persisted analyses can be recovered through `GET /api/v1/assessments/analyses/{analysis_id}`.
- The comparison service requires a matching approved intervention, reuses the production parser and misconception-analysis pipeline, validates question/cohort compatibility, and calculates metrics deterministically. Missing data is separate and unreliable re-identification returns `insufficient_data` without improvement metrics.
- The Results screen uses real backend data with upload/demo, loading, error, insufficient, and completed states; it shows numerical values, compact prevalence bars, student transitions, missingness, and the complete evidence chain.
- Live single-process verification completed initial analysis → RAG retrieval → Gemini remediation → teacher approval → follow-up analysis → results retrieval. The target pattern fell from 9/43 (20.9%) to 3/43 (7.0%), a 13.9 percentage-point reduction; 5 initially affected students resolved correctly, 1 changed but remained incorrect, and 3 still struggled.
- Backend suite passes locally with 58 tests and one database-gated integration test skipped when no test URL is set; the gated PostgreSQL workflow test also passed separately against PostgreSQL 16.
- `npm run lint` and `npm run build` pass after the results implementation; the one-time focused UI detector finding was corrected.
- `scripts/demo.sh` now provides validated `check`, clean `start`/`reset`, `status`, and scoped `stop` commands. It selects a verified Python 3.11 runtime, checks dependencies/fixtures/server-side Gemini configuration, rejects occupied ports, extends the CORS allow-list with the matching frontend origin and its `localhost` spelling, configures the API URL, records only its owned process groups, and waits for both HTTP services.
- The demo runner now requires hidden server-side PostgreSQL configuration and preserves persisted workflow state across reset.
- Headless Firefox verified dashboard navigation, live API connectivity, and the real synthetic preview values (45 students, 29 incorrect, 2 blank). Three driver interaction strategies could not activate the below-fold analysis control despite its enabled DOM state, so the complete browser click path remains explicitly unverified and requires manual rehearsal.
- Stale demo-skeleton wording was replaced with accurate live-workflow copy; the required focused UI detector returned no findings.
- The project documentation listed in the root README is populated and cross-linked.
- `database/migrations/001_golden_path_persistence.sql` defines 11 golden-path tables with constraints, indexes, and no-policy RLS.
- The migration applied successfully to an isolated PostgreSQL 16 database. A gated integration test persisted and reloaded assessment evidence, material chunks after an empty vector cache, approved remediation/source linkage, and follow-up comparison records through fresh repository instances.

“Working” includes the frontend, health boundary, assessment validation, local embeddings, deterministic grouping, source-backed retrieval, remediation/review, linked follow-up comparison, and locally tested persistence adapters. Live Supabase durability and deployment readiness remain unverified.

## In progress

- Run the complete three-minute path manually from `./scripts/demo.sh reset` and prepare an explicit labeled fallback for live Gemini failure.
- Apply the migration to Supabase and complete the stop/restart/React-reload persistence smoke.

## Not started

- LLM interpretation of potential misconception group labels
- Frontend and backend deployment

## Known issues and constraints

- Analysis is synchronous and CPU-bound and downloads the model on first use. Python 3.11 with CPU-only PyTorch 2.7.1 is the verified local runtime; the workspace's Python 3.14 default is not supported by that stack.
- Group labels are intentionally generic and provisional because LLM interpretation is not implemented. Semantic similarity can still group the wrong ideas; teacher review is required.
- The baseline photosynthesis fixture is synthetic and intended for deterministic demo/evaluation use; it is not real student data.
- `gemini-3.8-flash` and the full grounded prompt on `gemini-3.6-flash` returned Google's explicit transient `503 high demand` response. The verified stable free-tier fallback is `gemini-3.1-flash-lite`; ClassLens still returns a retryable error and stores no draft on provider failure.
- Live database connectivity, migration application, and restart persistence are unverified because `SUPABASE_DB_URL` is not configured. Material vectors remain per-process and are rebuilt from durable chunks. PDF and other formats and backend hosting remain unimplemented.
- The complete service chain was live-verified. Firefox and a temporary Selenium runtime reached the validated intake, but the driver could not activate the below-fold analysis control through XPath, WebElement scrolling, returned DOM nodes, or direct in-page click dispatch. The final manual three-minute click rehearsal remains open.
- No seeded Gemini-remediation fallback is implemented. Provider failure stays explicit and produces no draft; use a clearly labeled screenshot/recording until an explicit fallback is built.
- The backend dependency ranges are declared in `backend/requirements.txt` and `backend/requirements-dev.txt`; verification used a temporary virtual environment.
- A Supabase secret was found in `backend/.env.example` during this milestone and removed. The exposed key must be rotated/revoked in Supabase before any Supabase work.

## Next priority

Configure the direct Supabase PostgreSQL URL, apply the migration, and prove the complete workflow survives FastAPI restart and React reload.

## Golden-path readiness

| Golden-path capability | State |
|---|---|
| Load assessment and responses | Preview remains non-persistent; analyzed inputs have a PostgreSQL adapter |
| Validate and normalize input | Implemented |
| Identify incorrect responses | Implemented through explicit validated correctness |
| Generate embeddings | Implemented |
| Propose recurring misconception groups | Implemented with provisional generic labels |
| Show representative evidence | Implemented |
| Ingest and retrieve teacher material | Persistent chunks with rebuildable vector cache |
| Generate grounded remediation | Implemented, contract-tested, and live-verified with source-locked Gemini output |
| Teacher review and approval | PostgreSQL-backed implementation; live restart verification pending |
| Record or load labeled follow-up results | Implemented with shared validation and synthetic/upload paths |
| Compare baseline and follow-up | Implemented, contract-tested, and live-verified |

**Overall:** Persistence code and local contracts are implemented, but durable behavior is not marked live-verified until the migration/restart test runs against Supabase.
