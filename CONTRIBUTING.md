# Contributing to ClassLens

ClassLens is a focused education demo. Start with the [README](README.md),
[current status](STATUS.md), and [backlog](TASKS.md). Discuss substantial changes
in an issue before implementing them; small fixes can go directly to a pull request.

## Local development

Follow the [backend setup](backend/README.md) and [frontend setup](frontend/README.md).
The Linux/WSL demo runner needs your own Gemini key and a dedicated PostgreSQL
database. Unit and fixture-backed browser tests do not need hosted credentials.

Run the affected checks before submitting:

```bash
cd backend
.venv/bin/python -m pytest -q --ignore=tests/test_postgres_integration.py
cd ../frontend
npm test
npm run lint
npm run build
npm run test:e2e
```

Install Chromium first with `npx playwright install chromium` from `frontend/`.
Database changes must pass the [disposable database integration check](backend/README.md#database-integration-test).
CI runs these checks independently without production credentials.

## Pull requests

- Explain the problem, resulting behavior, and verification performed.
- Keep changes focused. Preserve exact evidence, source grounding, and explicit
  teacher approval; never substitute invented provider output after failures.
- Use synthetic examples only. Do not submit student records, school materials
  without publication rights, credentials, environment files, or sensitive logs.
- Add meaningful tests for changed validation, grounding, failure handling, or
  critical workflow behavior. Keep strict TypeScript and server-side secrets.
- Update authoritative documentation when behavior changes. Agent-assisted work
  must also follow [AGENTS.md](AGENTS.md).

Original contributions are submitted under the project's [MIT license](LICENSE).
Preserve third-party notices and identify any new dependency or asset license.
Maintainer review is required before merge; no response-time commitment is made.

Report vulnerabilities privately using [SECURITY.md](SECURITY.md), not public issues.
