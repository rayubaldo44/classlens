# ClassLens Agent Guide

ClassLens is an AI-powered education hackathon MVP: **From grades to understanding.** It helps teachers identify recurring, evidence-backed misconceptions in free-text responses and approve grounded remediation. The demo deadline is tomorrow.

## Start every task

1. Read [AGENTS.md](AGENTS.md) for repository instructions.
2. Read [STATUS.md](STATUS.md) for verified repository state.
3. Read [TASKS.md](TASKS.md) for priorities and dependencies.
4. Read the most recent entries in [SESSION_PROGRESS.md](SESSION_PROGRESS.md) for development history.
5. Read only the documents relevant to the task:
   - Product behavior: [docs/PRODUCT.md](docs/PRODUCT.md)
   - Technology choices: [docs/TECH_STACK.md](docs/TECH_STACK.md)
   - System boundaries: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
   - AI behavior: [docs/AI_PIPELINE.md](docs/AI_PIPELINE.md)
   - Data model: [docs/DATABASE.md](docs/DATABASE.md)
   - API contracts: [docs/API.md](docs/API.md)
   - Accepted and pending decisions: [docs/DECISIONS.md](docs/DECISIONS.md)
   - Demo flow: [docs/DEMO.md](docs/DEMO.md)

Inspect the current code before changing it. Treat proposed contracts and folder trees as plans until their implementation is verified.

## Priorities and scope

1. Reliability over complexity.
2. Complete the golden path before adding features.
3. Prefer functional, inspectable AI over decorative AI branding.
4. Show teacher-verifiable evidence for every detected group.
5. Keep the demo deterministic and label seeded data honestly.

Do not expand the MVP into a full LMS. The explicit exclusions are in [TASKS.md](TASKS.md#do-not-build-for-the-mvp). Do not silently select providers, models, libraries, or infrastructure marked TBD.

## Coding conventions

- Frontend code is React and TypeScript under `frontend/`; keep TypeScript strict and components focused.
- The implemented backend is Python with FastAPI under `backend/`; keep provider calls, persistence, and secrets behind that boundary.
- Validate data at system boundaries and return actionable, structured errors.
- Keep secrets server-side and out of source, fixtures, logs, and client bundles.
- Never fabricate student responses, evidence, analysis, retrieved passages, citations, or provider results.
- Preserve teacher review as the final authority for misconception labels and interventions.
- Prefer a simple modular application over premature services or abstractions.

## Testing and verification

- Run the narrowest relevant checks while iterating, then the affected package's lint/build/tests before handoff.
- Current frontend checks are `npm run lint` and `npm run build` from `frontend/`.
- Add tests for validation, AI failure paths, grounding, and critical golden-path behavior when those areas are implemented.
- Do not mark a task complete because a scaffold, mock, or static screen exists; verify the stated behavior end to end.

## Documentation rules

- Update [STATUS.md](STATUS.md) after any material implementation or verification change.
- Update checkbox state and dependencies in [TASKS.md](TASKS.md) when work starts or finishes.
- Record accepted or changed technical/product decisions in [docs/DECISIONS.md](docs/DECISIONS.md).
- Update the authoritative document for a concept and cross-link it elsewhere instead of copying it.
- Keep confirmed facts, proposed designs, and unresolved decisions visibly separate.

## Development Progress Logging

[SESSION_PROGRESS.md](SESSION_PROGRESS.md) is the persistent chronological development log.

During development:

1. At the START of every development session:
   - Read [AGENTS.md](AGENTS.md).
   - Read [STATUS.md](STATUS.md).
   - Read [TASKS.md](TASKS.md).
   - Read the most recent entries in [SESSION_PROGRESS.md](SESSION_PROGRESS.md).

2. After completing a meaningful development milestone:
   - Append an entry to [SESSION_PROGRESS.md](SESSION_PROGRESS.md).
   - Do NOT rewrite or delete previous entries.

3. Each entry should contain:
   - Date/time if available
   - Current milestone
   - What was attempted
   - Files created or significantly modified
   - What was completed
   - What was verified/tested
   - Problems encountered
   - Important decisions made
   - Remaining work
   - Recommended next step

4. Only record meaningful development milestones, such as:
   - UI skeleton completed
   - CSV ingestion completed
   - Misconception pipeline implemented
   - RAG integration blocked

   Do NOT create entries for individual implementation steps, routine commands, small edits, formatting changes, or typo fixes.

5. [STATUS.md](STATUS.md) remains the source of truth for CURRENT project state.

6. [TASKS.md](TASKS.md) remains the source of truth for remaining work.

7. [SESSION_PROGRESS.md](SESSION_PROGRESS.md) is the HISTORY of how development progressed.

8. When a meaningful development milestone is completed:
   - Verify it first.
   - Update [STATUS.md](STATUS.md).
   - Update [TASKS.md](TASKS.md).
   - Append the development result to [SESSION_PROGRESS.md](SESSION_PROGRESS.md).

9. Never mark functionality as complete unless it was actually implemented and verified.

10. If development stops because of an unresolved bug, document:
    - the symptoms
    - attempted fixes
    - suspected cause
    - relevant files
    - the recommended next debugging step

## Definition of done

A task is done when its acceptance criteria are met, relevant error states are handled, appropriate checks pass, no secrets or invented evidence are introduced, and STATUS/TASKS plus any affected authoritative document reflect the verified result.

## Graphify

After the required start-of-task document reads, use `./scripts/graphify.sh query "<question>"` first for codebase questions when `graphify-out/graph.json` exists, unless the graph is stale, the task concerns graph correctness, or the user asks to skip it. Confirm graph results against source code before making changes. The project skill is at `.agents/skills/graphify/SKILL.md`; use the pinned wrapper for ClassLens builds, updates, and exports.
