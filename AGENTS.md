# ClassLens Agent Guide

ClassLens is an AI-powered education hackathon MVP: **From grades to understanding.** It helps teachers identify recurring, evidence-backed misconceptions in free-text responses and approve grounded remediation. The demo deadline is tomorrow.

## Start every task

1. Read [STATUS.md](STATUS.md) for verified repository state.
2. Read [TASKS.md](TASKS.md) for priorities and dependencies.
3. Read only the documents relevant to the task:
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
- The planned backend is Python with FastAPI; add it only when the active task authorizes backend implementation.
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

## Definition of done

A task is done when its acceptance criteria are met, relevant error states are handled, appropriate checks pass, no secrets or invented evidence are introduced, and STATUS/TASKS plus any affected authoritative document reflect the verified result.
