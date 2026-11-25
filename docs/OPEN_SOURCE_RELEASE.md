# Open-source release preparation

Target: `v0.1.0` runnable synthetic-data demo, MIT for original work, preserving
`rayubaldo44/classlens` and its history. **Not published.** Repository visibility,
tags, GitHub settings, and remote content have not been changed by this preparation.

## Publication audit — 2026-11-25

- The maintainer selected MIT and confirmed rights to the original code, mascot,
  hero image, and demo learning material. Original and third-party terms are
  distinguished in [the notices](../THIRD_PARTY_NOTICES.md).
- Gitleaks **8.30.1**, downloaded from its official release and checked against
  its published SHA-256 manifest, scanned all locally available refs using
  `gitleaks git --log-opts=--all --redact`: **50 commits, no findings**. The two
  remote branches are `main` and `marodysis`; there are no remote tags at audit time.
- GitHub has one PR (#1), two Vercel bot comments, no inline comments/reviews,
  four completed successful Actions runs, and no uploaded Actions artifacts.
  All four log archives and the discussion payloads were downloaded to `/tmp`
  and scanned with Gitleaks: **no findings**. This is detection evidence, not a
  guarantee that every possible secret or personal detail has been recognized.
- The versioned CSVs/manifests and learning material explicitly identify
  synthetic content. The historical fallback is labeled as previously generated
  output and links only to repository fixtures; it is not presented as live AI.
- Contributor names/emails remain in commit history. Historical plans, diagram
  verification artifacts, and the Graphify safety tooling retain local machine
  paths. The active README now uses a generic configuration example. No history
  was rewritten and no chronological development-log entries were removed.
- PR #1's bot comments contain Vercel team identifiers, deployment links, and an
  access-request URL. These are not credential findings, but become publicly
  inspectable along with the PR. Review the linked deployments' access settings
  before publication; source visibility does not secure a running API.
- The private-vulnerability-reporting endpoint returned 404 on the private
  repository; availability/enabling is a publication step, not a verified feature.

Audit scope excludes deleted or inaccessible remote content, service dashboards,
credentials outside the repository, and external deployment contents. Repeat
the scan if any release content, refs, discussions, or logs change.

## Reproduction and verification

Verification uses a fresh source snapshot in `/tmp/classlens-oss-clean`, with
independently installed dependencies, no copied environment files, and a new
disposable PostgreSQL 17 container. Secrets and raw audit logs are kept outside
the release tree. The existing application environment is preserved.

- [x] Fresh Python 3.11 virtual environment installs `backend/requirements.lock`.
- [x] Fresh Node 22 installation of frontend dependencies with `npm ci`.
- [x] Backend unit suite: **136 passed**, without a model cache or hosted credentials.
- [x] Frontend: **four unit-test files passed**, lint and production build passed.
- [x] Both migrations apply in order to a new PostgreSQL 17 database.
- [x] Fresh-installed PostgreSQL persistence/reload integration test: **1 passed**.
- [x] Chromium smoke: **6 passed**; the separate sandbox attempt could not start
  its local server, so verification ran with local-port permission.
- [x] Missing `backend/.env` and an unset Gemini key each produce actionable
  demo-runner setup guidance. The temporary keyless configuration was removed.
- [x] Synthetic screenshot captured from the existing contract-fixture smoke
  and visually inspected; no live-provider claim is attached to it.
- [x] Empty-cache download and startup warming of the pinned model succeeded
  (approximately 458 MB cache). The live ordinary-upload browser workflow passed
  real embeddings → four groups → teacher-material retrieval → live Gemini draft
  → teacher edit/approval → follow-up → results and reload recovery. The selected
  group measured **9/43 before, 3/43 after**. A temporary verifier initially waited
  for an incorrect endpoint after a successful generation; its endpoint was
  corrected and the complete rehearsal then passed. No application fix was needed.
- [x] Independent final review found no Important or Critical issues; notices
  were checked against the installed pinned Graphify distribution.
- [x] Relative documentation links and package-license metadata validate; the
  release-source snapshot has no Gitleaks findings. Re-scan the exact committed
  release and publication refs before making them public.

Fresh Python `pip check` reports no broken requirements. The isolated demo
processes and PostgreSQL container were stopped after verification, and the
temporary server credential file was removed. No live verification records were
written to the existing hosted database.

The browser smoke uses intercepted APIs. The PostgreSQL integration uses test
embeddings. Neither substitutes for the live rehearsal checked separately above.

## Maintainer publication gate

After reviewing the final diff and verification results:

1. Confirm that publishing contributor identities, historical local paths, and
   Vercel bot metadata is acceptable. Review external deployment access controls.
2. Resolve remaining verification items above; do not claim hosted readiness.
3. Merge the reviewed preparation and verify CI on that exact release commit.
   Re-run the history scan on the exact refs being exposed and confirm the
   source archive excludes environment files, caches, dependencies, and raw logs.
4. Approve changing the existing repository to public. Enable GitHub private
   vulnerability reporting and secret scanning/push protection where available;
   verify that the Security tab's reporting action works.
5. Tag the reviewed commit `v0.1.0` and publish the [draft notes](releases/v0.1.0.md),
   describing local synthetic-data verification and the remaining pilot gates.

No auth implementation, hosting purchase, provider migration, or package-registry
publication is part of this source release.
