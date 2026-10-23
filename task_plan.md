# P0 Demo Completion Plan

## Active planning session — Graphify + Obsidian

- [complete] Approve and commit the local-first integration design.
- [complete] Write and self-review the implementation plan.
- [complete] Obtain execution-method approval (subagent-driven work in `feature/graphify-obsidian`).
- [complete] Implement and verify the pinned wrapper, official project skill, code-only graph, and isolated Obsidian export (Tasks 1–3).
- [complete] Document the verified integration (Task 4); relative Markdown links, whitespace, ignored artifacts, and current Canvas targets verified.
- [complete] Synchronize the dashboard and Kanban; verify the Canvas link and read back both notes (Task 5).
- [complete] Complete whole-branch review (Task 5): independent scoped review found one important nested-hyperedge provenance gap; the TDD fix and final clean refresh are verified.
- [complete] Implement and verify final review fixes: recoverable clean rebuilds, complete source-scope checks, safe generated report guidance, and recursive symlink rejection (78 wrapper tests; real fixture and external refresh).
- [complete] Scoped re-review of final fixes; no critical findings, one important nested-hyperedge finding fixed, and one optional real-CLI test recommendation retained as non-blocking future hardening.

The approved design is `docs/superpowers/specs/2026-10-16-graphify-obsidian-design.md`. The plan-only stage ended with user approval; implementation evidence and deviations follow below. Earlier P0 campaign history remains unchanged.

## Graphify final-review fixes — verified 2026-10-19

- Clean rebuilds archive prior inputs/cache under ignored `graphify-out/recovery/`, because forced code-only extraction still merges old document nodes. Validation gates clustering and exports, including explicit node/link/hyperedge source paths and narrowly proven upstream reference stubs.
- Recursive symlink preflight protects HTML, notes, Canvas, manifests, and generated configuration before upstream writes. Generated report guidance now uses the wrapper.
- Current graph: 982 nodes / 2,983 links / 53 communities; 1,035 notes; 982/982 Canvas targets resolve. Earlier graph/counts below are historical. Final changes add indexed tooling/tests.
- Fresh regression checks pass: 80 wrapper cases; backend 86 passed / 1 opt-in integration skipped and three frontend test files plus lint/build remain passing from the preceding tooling cycle. A separate real-CLI contaminated graph recovered cleanly. All 140 vault files outside the generated subtree remained unchanged during the final refresh; earlier missing-baseline limitations are not rewritten.
- Dashboard sync and final scoped re-review are complete.

## Graphify implementation update — verified 2026-10-18, documented 2026-10-19

- [complete] Safe wrapper/exclusions and 47 passing contract tests; pinned CLI/project skill 0.9.77.
- [complete] Real build and explicit full code-only refresh: 929 nodes / 2,828 links / 53 communities, no LLM; local JSON/report/HTML and 982 external notes plus Canvas.
- [complete] Source-backed queries, excluded-source inspection, and 929/929 Canvas file targets resolving from Vault-EN.
- [complete] Task 5 dashboard link/status sync and final integration checks.
- [complete] Task 5 whole-branch review and verified review fixes.

### Graphify errors and resolutions

| Error | Resolution |
|---|---|
| `codex` project installer added a hook | Removed that output; used the official `agents` installer and bounded `AGENTS.md` guidance. |
| Native `update .` indexed Markdown | Use explicit full `extract . --code-only --force`; accept full-scan cost and shrinkage. |
| Extraction omitted report and advertised metadata fields | Generate report with `cluster-only . --no-label`; validate pinned CLI/skill and actual JSON shape without fabricated fields. |
| External Canvas basenames resolved only from Graphify/ | Rewrite/validate file targets relative to the containing vault root. |
| Sandbox denied external export writes | Narrowly authorized wrapper build/update succeeded. |
| Temporary checksum baseline disappeared before final approved refresh comparison | Record earlier 108-file preservation checks honestly; no final byte-identity claim. |
| Task 4 `graphify uninstall --help` was rejected as an unknown option | Used the top-level documented help; no uninstall was performed. |
| Task 4 first documentation patch named STATUS.md twice | Patch validation rejected it without edits; consolidated the file update and reapplied. |
| Task 4 commit could not create the shared worktree index lock in the sandbox | Narrowly approved Git staging/commit completed successfully. |
| Final review found forced code-only extraction preserves old document nodes | Archive prior graph inputs/cache and validate the complete clean graph before clustering/export. |
| Final review found child symlinks reach upstream exporters | Reject all symlinks recursively in generated destinations before writers run. |
| Generated report recommended unsafe native refresh | Replace freshness guidance with `./scripts/graphify.sh update`. |
| Scoped re-review found nested `graph.hyperedges` bypassed provenance checks | Added failing nested-only and dual-slot cases; validate both supported hyperedge slots and their shapes (80 wrapper tests pass). |
| Server restart interrupted final re-review handoff | Recovered the tracked diff and planning state before continuing; no completed action was repeated. |

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
