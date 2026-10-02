# Vercel Deployment Plan

## Goal
Deploy the ClassLens frontend to Vercel with a correctly configured public API boundary, without exposing Gemini or Supabase secrets or pretending the current heavyweight FastAPI/embedding runtime is suitable for Vercel serverless without verification.

## Phases
- [complete] Inspect current frontend/backend deployment boundaries, repository state, Vercel tooling/authentication, and current official platform constraints.
- [complete] Decide and document the deployable topology: Vercel frontend plus a reachable Render FastAPI host.
- [complete] Add the minimum production environment documentation for the manually configured Vercel and Render services.
- [complete] Run local backend/frontend checks and verify the public Render health endpoint.
- [blocked_on_external_config] Complete the user-managed Render CORS environment configuration and restart the backend. Live API is healthy, but currently rejects the Vercel origin.
- [pending] Smoke-test production CORS and the hosted golden path after Render applies `CLASSLENS_CORS_ORIGINS=https://class-lens-one.vercel.app`.

## Guardrails
- Never put `GEMINI_API_KEY`, `SUPABASE_DB_URL`, or Supabase secret keys in frontend or `VITE_*` variables.
- Do not deploy a frontend that silently points to localhost.
- Do not claim the full app is deployed until the public frontend can reach a public backend and complete a smoke check.
- Preserve the user’s existing uncommitted golden-path changes.
- Do not select or deploy a non-Vercel backend provider without the user’s direction.

## Known Constraints
- The backend loads sentence-transformers and CPU PyTorch, performs synchronous analysis, and keeps a rebuildable per-process vector cache.
- Local cold analysis and remote database persistence can exceed ordinary serverless request expectations.
- The worktree contains the completed golden-path hardening changes and must not be discarded.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| None yet | 0 | — |
| Official Vercel CLI authentication check was interrupted | 1 | Switched to diagnosing the user-confirmed existing deployment; request the live URL instead of relinking or redeploying. |
| Combined deployment-documentation patch missed the exact unresolved-decision table context | 1 | Re-read the affected sections and apply smaller targeted patches instead of repeating the batch. |
| `git add` could not create `.git/index.lock` inside the managed read-only Git metadata mount | 1 | Re-run scoped Git staging/commit operations with repository metadata write approval. |
