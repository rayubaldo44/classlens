# Demo Guide

**Implementation status:** The complete local workflow was verified on 2026-10-02 through ordinary upload endpoints with real embeddings, Supabase persistence, source-backed retrieval, live Gemini generation, explicit teacher approval, real follow-up analysis, and calculated results. A Vercel frontend and Render backend are provisioned, and Render health passes; their cross-origin golden path remains unverified until the committed branch and matching production environment values redeploy.

## Scenario and files

ClassLens demonstrates a Grade 7 photosynthesis assessment for 45 synthetic students. The teacher investigates a recurring pattern that treats sunlight as plant food, grounds an intervention in teacher-selected notes, approves an edited draft, and measures a synthetic follow-up.

Use these exact versioned inputs:

- Initial assessment: `data/demo/photosynthesis_responses.csv`
- Teacher material: `data/demo/learning_materials/photosynthesis_grade7.txt`
- Follow-up assessment: `data/demo/photosynthesis_follow_up_responses.csv`

The requested conceptual names `photosynthesis_initial_assessment.csv`, `photosynthesis_teacher_material.txt`, and `photosynthesis_followup_assessment.csv` correspond to the three repository files above. Do not rename or regenerate them immediately before judging.

All student identifiers and responses are synthetic. The inputs are deterministic; detected groups, retrieval, Gemini output, and comparison metrics are produced by the real pipeline.

## Services and environment

Required services:

- Supabase PostgreSQL reachable through a direct server-side connection string.
- FastAPI running under the verified Python 3.11 environment.
- React/Vite.
- Google Gemini API access for live remediation generation.
- The local Hugging Face embedding model cache. Internet access is needed on first download if it is not already warm.

Required values belong in ignored `backend/.env` configuration:

```dotenv
SUPABASE_DB_URL=postgresql://...
GEMINI_API_KEY=...
CLASSLENS_LLM_MODEL=gemini-3.1-flash-lite
CLASSLENS_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

`SUPABASE_URL` and `SUPABASE_SECRET_KEY` may exist for project administration but are not used by the browser or the direct PostgreSQL workflow. `HF_TOKEN` is optional for the public embedding model. Never put database or provider secrets in `VITE_*` variables.

Apply the idempotent migration once for a new Supabase database:

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f database/migrations/001_golden_path_persistence.sql
```

From the repository root, validate and start the local stack:

```bash
./scripts/demo.sh check
./scripts/demo.sh reset
./scripts/demo.sh status
```

Open `http://127.0.0.1:5173`. The runner also permits `http://localhost:5173`. For occupied ports:

```bash
CLASSLENS_BACKEND_PORT=8010 CLASSLENS_FRONTEND_PORT=4179 ./scripts/demo.sh reset
```

The runner injects the matching public API URL and local CORS origins; no undocumented shell exports are required.

## Hosted deployment wiring

The provisioned production topology is:

- Vercel frontend: `https://class-lens-one.vercel.app`
- Render FastAPI service: `https://classlens-t6xn.onrender.com`
- Supabase PostgreSQL through the server-side transaction-pooler connection string

Vercel must define only the public build-time API location:

```dotenv
VITE_API_URL=https://classlens-t6xn.onrender.com
```

Render holds all server-side values:

```dotenv
PYTHON_VERSION=3.11.11
GEMINI_API_KEY=...
SUPABASE_DB_URL=postgresql://...
CLASSLENS_LLM_MODEL=gemini-3.1-flash-lite
CLASSLENS_CORS_ORIGINS=https://class-lens-one.vercel.app
```

The Render `/health` endpoint returned the expected HTTP 200 contract on 2026-10-02. A live CORS probe from `https://class-lens-one.vercel.app` currently returns HTTP 400 `Disallowed CORS origin`; the deployed frontend bundle already targets Render. Set the exact production origin in the plural `CLASSLENS_CORS_ORIGINS` Render variable and restart the service. Do not call the hosted workflow verified until a browser run confirms CORS and the complete assessment-to-results path.

## Safe demo reset

There is deliberately no destructive reset endpoint. Persistent IDs are content-derived and repeated fixture submissions safely upsert/reuse deterministic records, so old Supabase rows do not change the demonstrated calculations.

Before each judging run:

1. Run `./scripts/demo.sh reset` to restart only runner-owned local processes. This preserves Supabase records and model caches.
2. Open a new private browser window, or clear only the ClassLens workflow pointer in DevTools:

   ```js
   localStorage.removeItem('classlens.workflow.v1'); location.assign('/');
   ```

3. Confirm the sidebar says **API connected**.
4. Use the three versioned files listed above.

Starting a new assessment from the Upload screen also clears stale downstream browser pointers. Do not truncate Supabase tables before a normal demo.

## Exact three-minute walkthrough

### 0:00–0:30 — Validate the class

1. On the dashboard choose **Load photosynthesis demo**.
2. Under **Choose response file**, select `data/demo/photosynthesis_responses.csv` and choose **Validate selected CSV**.
3. Confirm **Validated preview** shows 45 students, 45 accepted responses, 29 incorrect, 14 correct, and 2 blank.
4. Choose **Analyze learning gaps**. A cold analysis can take roughly 15–45 seconds because embedding and remote persistence are synchronous.

### 0:30–1:05 — Inspect real evidence

5. Confirm **4 recurring patterns to inspect**, 18 grouped responses, and 11 outliers.
6. Open the first **Potential misconception pattern** with 9 of 29 affected responses.
7. Point out the exact representative answers and the full member list. Say that the label is provisional and teacher review is required.

### 1:05–1:40 — Retrieve teacher material

8. Select `data/demo/learning_materials/photosynthesis_grade7.txt` under **Choose teaching material (.txt)**, then choose **Ingest selected text**.
9. Confirm 3 chunks with 384-dimensional embeddings, then choose **Find supporting passages**.
10. Confirm the top passage explains sunlight as energy and glucose as food/stored chemical energy. It should come from the uploaded file; verified relevance was 0.78. Choose **Continue to intervention review**.

### 1:40–2:20 — Generate, edit, and approve

11. Choose **Generate remediation**. Gemini receives the detected group and only the displayed passages. Typical warm generation is several seconds, but provider load varies.
12. Confirm the draft is labeled **AI-generated** and **Pending teacher review**. Check that its source badges refer only to retrieved chunks.
13. Make a small visible edit, optionally add a review note, check the teacher-review confirmation, and choose **Approve intervention**.
14. Confirm **Approved by teacher**, then choose **Continue to results**. Never skip the explicit approval.

### 2:20–2:55 — Analyze follow-up

15. Select `data/demo/photosynthesis_follow_up_responses.csv` under **Choose follow-up CSV**, then choose **Analyze selected follow-up**.
16. Confirm **Feedback loop complete** and show:
    - before: 9/43 affected, 20.9%;
    - after: 3/43 affected, 7.0%;
    - reduction: 13.9 percentage points;
    - correctness: 14/43 to 33/43, +44.1 percentage points;
    - missing follow-up: 2 (one blank and one absent);
    - transitions: 5 resolved, 1 changed but still incorrect, 3 still struggling.

### 2:55–3:00 — Close

“Grades tell teachers who is struggling. ClassLens helps explain why—and keeps the teacher in control of what happens next.”

The measured change is observational and comes from synthetic follow-up input; do not claim the intervention caused it.

## Verified checkpoints

- Baseline: 45 rows, 43 answered, 2 blank, 14 correct, 29 incorrect.
- Grouping: 4 groups, 18 grouped, 11 outliers; strongest group 9/29 with coherence 0.8454.
- Retrieval: 3 exact source chunks ranked 0.7840, 0.5693, and 0.5417. Every returned string was checked against the normalized uploaded material at its stored offsets.
- Gemini: real `gemini-3.1-flash-lite`, prompt `grounded_remediation_v1`, structured output parsed, chunks 1 and 2 cited, teacher edit and approval persisted.
- Follow-up: 44 rows, 43 answered, 1 blank, 1 baseline student absent, 33 correct, 10 incorrect.
- Results: 9/43 (20.9%) to 3/43 (7.0%), 13.9-point reduction; remaining students remain visible.
- Uninterrupted ordinary-upload API run: about 82 seconds on the verification machine. Allow roughly three minutes for narration and clicks.

## Recovery when a dependency fails

- **Gemini:** the adapter retries one timeout/transient 429 or 5xx failure. If it still fails, the UI displays **Remediation action failed**, no successful draft is stored, and **Try generation again** is available. Wait briefly and retry once. If judging time is short, show a clearly labeled screenshot/recording from a verified run; never describe it as live generation.
- **Supabase/database:** keep the page open, run `./scripts/demo.sh status`, verify `SUPABASE_DB_URL` and network reachability, then retry the failed action. Database errors are sanitized and retryable; the UI does not claim success.
- **Embedding model:** ensure the model cache is warm before presenting. A model load/download failure produces an analysis or retrieval error and no fabricated group/source.
- **Backend unavailable/CORS:** locally, confirm `./scripts/demo.sh status`. For production, check that Render has the plural `CLASSLENS_CORS_ORIGINS` variable containing the exact Vercel origin (no trailing slash), then restart Render and reload. The health endpoint can be healthy while browser requests are blocked by CORS.
- **Insufficient material:** choose the provided photosynthesis material and retrieve again. ClassLens blocks grounded generation when no passage clears the relevance threshold.
- **Saved-workflow restore:** choose **Start a new workflow** on the visible restore error, or perform the safe browser-pointer reset above. Persisted database records remain intact.

## Pre-demo checklist

### Required before leaving for judging

- [x] Fixtures, migration, server-side configuration names, and runner checks are documented.
- [x] Supabase migration and database-gated integration test passed.
- [x] Real baseline, grouping, retrieval, Gemini, review, follow-up, and results path passed.
- [x] FastAPI restart and frontend resource reload passed.
- [x] Empty/missing-column CSV, blank answers, backend unavailable, database failure, embedding/RAG/LLM failures, malformed LLM output, insufficient context, and follow-up mismatch have controlled handling through live checks and/or focused automated tests.
- [x] Desktop and mobile golden-path screens were checked for obvious overflow and stale restore state.
- [ ] Run two timed human-operated rehearsals on the actual presentation machine/network.
- [ ] Confirm Gemini quota and Supabase reachability immediately before presenting.
- [ ] Prearrange files/tabs, mute notifications, check projector zoom, and keep a clearly labeled backup recording available.

## Stop local services

After verification or the demo:

```bash
./scripts/demo.sh stop
```

This stops only runner-owned processes and does not delete persistent workflow records.
