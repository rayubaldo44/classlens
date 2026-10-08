# P0 Demo Completion Plan

## Goal
Complete the unchecked P0 tasks in `TASKS.md` in dependency order, preserving the verified local golden path and recording any external blocker honestly.

## Phases
- [complete] Recheck the live Vercel/Render deployment after the documented capacity failure: health, CORS, direct routes, and one ordinary-upload analysis.
- [blocked] Run the complete hosted browser golden path and reload-recovery checks. Blocked because ordinary analysis still returns an empty 502; the latest attempt failed after 121.6 seconds.
- [complete] Restore a runner-owned local stack and warm the embedding/material paths.
- [complete] Run an automated timed local golden-path rehearsal and capture checkpoints/failures. The second full run completed the ordinary upload-to-results path in 79.2 seconds and all direct-route reload checks in 98.1 seconds.
- [complete] Prepare an honestly labeled fallback artifact because the hosted provider path remains blocked.
- [complete] Update `STATUS.md`, `TASKS.md`, `docs/DEMO.md`, and append `SESSION_PROGRESS.md` after each verified milestone.

## Guardrails
- Work only on P0 until its demo gates pass or an external billing/configuration dependency blocks further progress.
- Preserve all existing uncommitted files and never include secrets in output, source, logs, or frontend configuration.
- Use ordinary upload endpoints for the golden-path proof; demo endpoints may warm/check infrastructure but do not close the hosted acceptance criterion.
- Keep teacher approval explicit and preserve exact uploaded evidence and retrieved text.
- Do not claim a hosted pass from health/CORS checks alone.

## Current Blocker Hypothesis
The active Render service may still use a 512 MB compute plan. Three analysis-time process restarts and a measured 1.11 GB local peak strongly indicate memory-limit termination. A successful ordinary-upload analysis is the stop/go test.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| Vercel workflow deep links returned 404 | 1 | Added and deployed `frontend/vercel.json` catch-all rewrite in commit `593e475`; direct routes now return 200. |
| Hosted analysis returned 502 and Render restarted | 2 | Diagnosed likely memory-limit termination; requires at least the 2 GB `1c-2g` plan before retry can pass. |
| Hosted analysis still returned empty 502 after 121.6 seconds on recheck | 3 | Stop repeating the same request until the Render compute plan changes; continue independent local P0 work. |
| `./scripts/demo.sh reset` could not bind local ports in sandbox | 1 | Rerun with local-port permission. |
| Runner found port 5173 occupied by an untracked Vite process | 1 | Preserve the user process; reconcile processes before starting a runner-owned stack. |
| Persisted retrieval returned HTTP 200 but did not render on `/misconception`; `/analysis` also showed an empty state after reload | 1 | Passed restored analysis/retrieval into the route components via keyed initial state; focused and full browser regression checks pass. |
| First prop-sync implementation failed `react-hooks/set-state-in-effect` lint | 1 | Replaced synchronous effects with keyed remounts and direct state initialization. |

## Completion Criteria
- Production completes ordinary upload through results and survives direct-route reloads, or the exact external blocker is documented with a working local demo and fallback.
- Two timed human-operated rehearsals remain a user/judging-machine gate and must not be marked complete from automation alone.
