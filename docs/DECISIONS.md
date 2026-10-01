# Decision Log

This log records decisions explicitly supplied for ClassLens and the choices still unresolved. It does not treat proposed details in other documents as accepted.

## Accepted decisions

### D-001 — React, TypeScript, and Vite frontend

- **Status:** Accepted; scaffold present
- **Decision:** Build the frontend with React, TypeScript, and Vite.
- **Reason:** The application is already scaffolded in `frontend/`, and the stack supports rapid typed UI development.
- **Consequence:** Extend the existing app; do not recreate it.

### D-002 — Python and FastAPI backend

- **Status:** Accepted; not implemented
- **Decision:** Use Python with FastAPI for the backend.
- **Reason:** It fits the AI/data workload and provides explicit HTTP contracts.
- **Consequence:** Keep provider calls and secrets behind FastAPI.

### D-003 — Supabase PostgreSQL

- **Status:** Accepted; not configured
- **Decision:** Use Supabase PostgreSQL for relational persistence.
- **Reason:** It provides managed PostgreSQL suitable for the hackathon schedule.
- **Consequence:** Use pgvector only if persistent vector retrieval is justified; no migration exists yet.

### D-004 — Embeddings support misconception grouping

- **Status:** Accepted at responsibility level; model and algorithm unresolved
- **Decision:** Represent response meaning with embeddings and use semantic patterns to propose recurring groups among incorrect responses.
- **Reason:** Similar underlying ideas can be expressed with different wording.
- **Consequence:** Similarity alone does not prove a misconception. Question context, answer keys, representative responses, minimum support, and teacher review are required.

### D-005 — RAG grounds remediation

- **Status:** Accepted; not implemented
- **Decision:** Retrieve relevant passages from teacher-provided learning materials for remediation generation.
- **Reason:** The intervention should be grounded in material selected by the teacher.
- **Consequence:** RAG is not the primary misconception-detection mechanism, and no sufficiently relevant passage means no claim of grounded generation.

### D-006 — Teacher in the loop

- **Status:** Accepted; not implemented
- **Decision:** The teacher is the final authority over educational interpretation and intervention approval.
- **Reason:** AI output is a fallible proposal and educational context matters.
- **Consequence:** Show evidence and require explicit edit/approve/reject controls.

### D-007 — Focused MVP, not a full LMS

- **Status:** Accepted
- **Decision:** Build only the assessment-to-remediation golden path for the hackathon MVP.
- **Reason:** Reliability and a complete end-to-end demonstration are more valuable than feature breadth.
- **Consequence:** Defer the features in [TASKS.md](../TASKS.md#do-not-build-for-the-mvp).

### D-008 — Deployment direction

- **Status:** Partially accepted; not configured
- **Decision:** Deploy the frontend to Vercel and use Supabase for the database. Backend hosting remains TBD.
- **Consequence:** Deployment work must preserve server-side secrets and verify cross-origin configuration.

## Unresolved decisions

| ID | Decision needed | Why it matters | Owner/trigger |
|---|---|---|---|
| U-001 | Exact Hugging Face embedding model and local vs hosted inference | Determines dimensions, latency, license, caching, and grouping quality. | Resolve before embedding implementation. |
| U-002 | LLM provider and model | Determines SDK, structured output, rate limits, cost, and secret configuration. | Resolve before interpretation/remediation implementation. |
| U-003 | Initial grouping algorithm, distance metric, thresholds, and minimum support | Determines stability, noise handling, and confidence language for small question-level datasets. | Evaluate on the synthetic demo fixture. |
| U-004 | Incorrect-response scoring method | Determines which answers enter analysis and how explainable the baseline is. | Resolve with the assessment/CSV contract. |
| U-005 | Supported teacher-material formats and extraction library | Determines upload validation and source-location quality. | Resolve from the actual demo document. |
| U-006 | pgvector persistence vs an in-memory demo index | Affects database setup, reproducibility across restarts, and complexity. | Resolve after fixture size and hosting are known. |
| U-007 | Backend deployment provider | Affects cold starts, CORS, secrets, logs, and demo reliability. | Resolve before deployment work. |
| U-008 | API execution model for slow AI work | Synchronous calls are simpler; polling jobs are safer for longer latency. | Measure selected providers first. |
| U-009 | Explicit Node version policy | Needed for repeatable setup and CI with Vite 8. | Resolve before shared deployment/CI. |

When a decision is made, add a dated accepted entry with its rationale and update [TECH_STACK.md](TECH_STACK.md), [ARCHITECTURE.md](ARCHITECTURE.md), or [AI_PIPELINE.md](AI_PIPELINE.md) only where the decision changes their authority.
