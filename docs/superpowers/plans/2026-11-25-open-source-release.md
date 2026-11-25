# ClassLens open-source release preparation

Approved scope: runnable synthetic-data demo, MIT for original work, existing
repository and history. No visibility change or publication until reviewed.

- [x] Inspect current setup, CI, migrations, data provenance, and release gaps.
- [x] Add MIT license/package metadata and preserve third-party terms.
- [x] Add concise contributor/security guidance and issue/PR templates.
- [x] Correct portable setup and both migrations; replace template documentation.
- [x] Add a clearly labeled synthetic screenshot and unpublished v0.1.0 notes.
- [x] Scan all available refs and release-source files; review remote discussion/logs.
- [x] Install both locks independently and run automated gates on fresh source.
- [x] Verify PostgreSQL 17 migrations and repository restart persistence.
- [x] Download and warm the pinned embedding model from an empty cache.
- [x] Complete live synthetic upload → analysis → retrieval → Gemini → teacher approval → follow-up → results/reload.
- [x] Complete final review, documentation consistency, and final source scan.
- [x] Update STATUS/TASKS and append the verified milestone to SESSION_PROGRESS.

Publication, exact-commit CI, external deployment access review, and GitHub
security settings are tracked separately in [the release gate](../../OPEN_SOURCE_RELEASE.md).

Implementation rulings: use a fresh source snapshot and independent dependency
installs under `/tmp` so existing credentials, databases, and demo processes stay
untouched. Remove only the three unused template SVG assets after confirming
there are no imports; preserve them and all development logs in Git history.
