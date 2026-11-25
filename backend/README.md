# ClassLens backend

Run the commands on this page from `backend/` unless stated otherwise.

Use Python 3.11 for the AI runtime. `backend/.python-version` records the verified local patch release. The current workspace default, Python 3.14, is not supported by the verified PyTorch stack.

For the verified CPU-only local setup:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip --isolated install --require-hashes -r requirements.lock
```

The lock targets CPython 3.11 on x86-64 Linux/WSL with glibc 2.28 or newer.
It verifies SHA-256 hashes for every wheel. PyPI supplies the ordinary packages
and the CPU Torch 2.13.0 wheel uses an explicit PyTorch URL. Update the dependency
manifests and reverify the lock when changing packages.

Copy `.env.example` to `.env` and edit it with your own values:

```bash
cp .env.example .env
```

Keep secrets only in this ignored file. Set `GEMINI_API_KEY` and `SUPABASE_DB_URL`;
never put either in Vite configuration or commit them. Despite its historical
name, `SUPABASE_DB_URL` accepts a standard PostgreSQL connection string. Use a
dedicated database for synthetic demos, not a school or production database.

For a local PostgreSQL 17 installation, create a database and role you control.
For Docker, this optional example binds only to localhost and uses a deliberately
public, local-only password (change the port if occupied):

```bash
docker run --name classlens-demo-postgres --detach \
  --publish 127.0.0.1:55439:5432 \
  --env POSTGRES_USER=classlens \
  --env POSTGRES_PASSWORD=classlens_local_demo \
  --env POSTGRES_DB=classlens_demo postgres:17-alpine
```

Use `postgresql://classlens:classlens_local_demo@127.0.0.1:55439/classlens_demo`
for that example only. Supabase users should supply their own PostgreSQL
connection string, including the appropriate SSL parameters.

The API loads `backend/.env` automatically, but `psql` does not. Apply **both**
migrations in order with the same connection string without sourcing the file
as shell code or printing its contents:

```bash
.venv/bin/python - <<'PY'
import os
import subprocess
from dotenv import load_dotenv
load_dotenv('.env')
for filename in ('001_golden_path_persistence.sql', '002_teacher_group_reviews.sql'):
    subprocess.run(
        ['psql', os.environ['SUPABASE_DB_URL'], '-v', 'ON_ERROR_STOP=1',
         '-f', '../database/migrations/' + filename],
        check=True,
    )
PY
```

Alternatively, if `SUPABASE_DB_URL` is already exported in your shell:

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f ../database/migrations/001_golden_path_persistence.sql
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f ../database/migrations/002_teacher_group_reviews.sql
```

Gemini uses `CLASSLENS_LLM_TIMEOUT_MS=45000` as its per-attempt transport timeout and `CLASSLENS_LLM_TOTAL_BUDGET_MS=60000` as the total budget across the initial request, retry delay, and one retry.

The embedding model uses a pinned Hugging Face revision and is cached locally. `./scripts/demo.sh reset` loads and warms it before `/health` responds, so a first download happens during startup rather than on a teacher request. `/ready` reports PostgreSQL and model readiness without calling Gemini. Material vectors are rebuilt from persistent chunks after a process restart.

Run the API and tests from `backend/`:

```bash
.venv/bin/uvicorn app.main:app --reload
.venv/bin/python -m pytest -q
```

For the complete local demo, return to the repository root and use the owned-process runner:

```bash
./scripts/demo.sh check
./scripts/demo.sh reset
```

The runner requires this Python 3.11 environment by default. To use another verified Python 3.11 environment without modifying the repository, set `CLASSLENS_BACKEND_PYTHON=/absolute/path/to/python` for `check` or `reset`. It never prints `GEMINI_API_KEY`; it reports only whether the key is configured.

## Database integration test

Use only a disposable database with both migrations applied. The test writes
synthetic records; never point it at production or shared student data.
Export `CLASSLENS_TEST_DATABASE_URL` explicitly; it is separate from application
configuration.

```bash
CLASSLENS_TEST_DATABASE_URL=postgresql://classlens:classlens_local_demo@127.0.0.1:55439/classlens_demo \
  .venv/bin/python -m pytest -q tests/test_postgres_integration.py
```

Unit tests with `--ignore=tests/test_postgres_integration.py` need no database,
Gemini key, or model download. The live demo requires all three. Missing Gemini
configuration fails visibly; no successful remediation is fabricated.

The shared demo runner supports Linux/WSL and requires `curl`, `setsid`, and `ss`.
Manual Uvicorn/Vite startup on other operating systems has not been verified.
