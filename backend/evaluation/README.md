# Real-embedding regression evaluation

This offline check runs the pinned production embedding model through the production assessment, grouping, material-ingestion, and retrieval services. It reports pairwise group precision/recall/F1, outlier precision/recall, expected-passage retrieval, run time, and exact repeat-run stability.

The bundled cases are synthetic candidates and remain marked `pending_teacher_review`. Their metrics are diagnostic only. An educator should inspect every response, expected group, expected outlier, retrieval expectation, and quality gate, then add their name/date and change the case status to `approved`. The command exits with status 2 until every case is approved so CI or project documentation cannot accidentally present unreviewed expectations as a completed benchmark. After approval, status 1 means an accepted quality gate regressed and status 0 means all gates passed.

Run from `backend/`:

```bash
PYTHONPATH=. .venv/bin/python -m evaluation.embedding_regression \
  --output evaluation/latest-report.json
```

`latest-report.json` is ignored because timings and measurements are environment-specific. Commit reviewed case definitions; record the reviewed aggregate results and known limitations in `docs/AI_PIPELINE.md`.

## Grounded generation

`generation_evaluation.py` performs two small live Gemini checks using synthetic evidence: ordinary grounding and prompt injection embedded in untrusted student/source text. It records latency and provider token telemetry, validates the structured schema and cited IDs, checks that injection canaries do not appear, and verifies the no-key provider-unavailable error. It does not equate valid citation IDs with supported educational claims; every generated draft remains `pending_human_review` for claim-level source review.

```bash
PYTHONPATH=. .venv/bin/python -m evaluation.generation_evaluation \
  --output evaluation/latest-generation-report.json
```
