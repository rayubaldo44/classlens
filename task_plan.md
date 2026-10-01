# Supabase Persistence Plan

## Active Goal
Persist the existing ClassLens golden path in Supabase PostgreSQL while preserving its API-driven React/FastAPI behavior and current AI algorithms.

## Active Phases
- [x] Inspect documentation, volatile stores, current APIs, frontend state, database tooling, and baseline checks.
- [x] Add PostgreSQL configuration, migration, connection layer, and persistent repositories.
- [x] Wire assessment, material, remediation, and results services to durable storage with atomic failures.
- [x] Add browser reload recovery using persisted resource IDs and FastAPI reads.
- [x] Add persistence/failure tests and run backend/frontend verification.
- [ ] Apply the migration and run the restart-persistence smoke when a direct database URL is available.
- [x] Update authoritative documentation and milestone logs with verified results only.

## Active Decisions
- Use direct PostgreSQL through server-only `SUPABASE_DB_URL` and psycopg transactions.
- Persist relational source/evidence data; keep document vectors as a lazy process-memory cache rebuilt from stored chunks.
- Use localStorage only for non-authoritative workflow IDs; reload all records through FastAPI.
- Do not add classes, accounts, authentication, standalone follow-up-result rows, or unrelated LMS features.

## Prior Milestone (complete)

# Demo Reset + Browser Rehearsal Plan

## Goal
Make the completed ClassLens golden path repeatable from a clean local start, validate it through a real browser when tooling permits, and update only the verified pre-demo checklist items.

## Scope
- Add the smallest deterministic local start/reset procedure for the existing process-local architecture.
- Preserve live Gemini behavior and honest synthetic-data labels; no silent cached or fabricated fallback.
- Exercise dashboard → assessment → analysis → evidence → material → remediation → approval → follow-up → results.
- Do not select a backend host, configure Supabase, deploy, or begin unrelated P1 work.

## Phases
- [x] Re-read repository guidance, current state, backlog, latest milestone, demo guide, architecture, decisions, and planning skill.
- [x] Audit current local start commands, process-local stores, UI navigation, and available browser tooling.
- [x] Define and implement a safe deterministic demo start/reset workflow with validation.
- [x] Add focused automated coverage for reset/start behavior where practical.
- [x] Start the stack and rehearse the golden path in a browser or document a concrete tooling blocker after exhausting available options.
- [x] Run backend/frontend regression checks and verify secrets stay out of frontend/build output.
- [x] Update DEMO, STATUS, TASKS, and append SESSION_PROGRESS with verified facts only.

## Initial Decisions
- Reset means starting one fresh backend process, because all current state stores are process-local and have no delete API.
- A reset must not delete user files, fixtures, environment files, model caches, or secrets.
- The procedure should fail early with actionable messages when Python 3.11, frontend dependencies, or required configuration are unavailable.

## Errors Encountered
- The initial combined documentation read exceeded the output limit; required files were re-read in smaller targeted commands.
- The first attempt to replace planning files combined delete/add operations for one path in a single patch, which the patch tool rejected; files are replaced in separate operations.
- The first runner check referenced a proposed teacher-note filename rather than the implemented `photosynthesis_grade7.txt`; the fixture check was corrected before service startup.
- The first port probe attempted to create a socket and hit the managed sandbox's `PermissionError`, which the runner misclassified as a collision. It now uses read-only `ss` listener inspection; actual local binding is verified separately with permission.
- Default frontend port 5173 was already owned by a pre-existing Vite process. The runner correctly refused to stop it; rehearsal uses port 4179, and backend CORS now derives from the configured demo frontend URL.
- The first Selenium rehearsal reached the validated 45/29/2 intake state but timed out locating the below-fold analysis control. The retry scrolls controls into view and records step output plus failure DOM.
- The second rehearsal captured the analysis button as enabled in the DOM, but Firefox's XPath lookup still returned no element and FastAPI received no analysis request. The final retry switches button discovery to `document.querySelectorAll` rather than repeating XPath.
- Returning the below-fold DOM node through WebDriver also remained false under Firefox visibility heuristics. WebElement-based activation is exhausted; the browser harness now dispatches the native DOM click in-page and will stop with an explicit blocker if that distinct strategy fails.
- Direct in-page click dispatch also timed out at the same control after the real preview rendered. Automated Firefox rehearsal is now blocked by the local driver interaction; do not claim the click path passed. Preserve screenshots/DOM and request a manual rehearsal instead of retrying the same stage.
- The first README replacement command failed before editing because JavaScript template parsing treated Markdown backticks as delimiters. The replacement was reapplied with tilde code fences through `apply_patch`.
- The final whitespace check flagged Markdown line-break spaces on the newly changed STATUS date line; they were removed before the final check.
- On 2026-10-02 continuation recovery, the optional `planning-with-files` session replay helper was not installed alongside the skill (`scripts/session-catchup.py` was absent). Recovery instead used the project planning files, repository guidance, current status/backlog, milestone log, worktree diff, and hidden environment-key inventory.
