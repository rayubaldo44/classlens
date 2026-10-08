# ClassLens backend

Use Python 3.11 for the AI runtime. `backend/.python-version` records the verified local patch release. The current workspace default, Python 3.14, is not supported by the verified PyTorch stack.

For the verified CPU-only local setup:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.lock
```

`requirements.lock` reproduces the exact verified development/test resolution and directs `torch==2.7.1+cpu` to PyTorch's CPU wheel index. `requirements.txt` and `requirements-dev.txt` remain the short dependency manifests to edit when intentionally updating packages; regenerate and verify the lock after such a change.

Copy `.env.example` to `.env` and keep real secrets only in the ignored `.env`. Set `GEMINI_API_KEY` and the direct PostgreSQL `SUPABASE_DB_URL`; never place either in Vite configuration or `.env.example`. Apply the migration before starting the complete workflow:

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f ../database/migrations/001_golden_path_persistence.sql
```

The local embedding model downloads from Hugging Face on first use and is cached locally. Material vectors are rebuilt from persistent chunks after a process restart.

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
