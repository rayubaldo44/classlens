# Open-source release preparation

[ClassLens v0.1.0](https://github.com/rayubaldo44/classlens/releases/tag/v0.1.0) was published from commit `c705d31ba58d625475f3dd1983e5aa00db4cacff` with existing history and third-party notices preserved. All five checks passed on main. Anonymous tag lookup and source download succeeded. The sections below record the preparation and review history.

## Publication audit — 2026-11-25

- The maintainer selected MIT and confirmed rights to the original code, mascot,
  hero image, and demo learning material. Original and third-party terms are
  distinguished in [the notices](../THIRD_PARTY_NOTICES.md).
- Gitleaks **8.30.1**, downloaded from its official release and checked against
  its published SHA-256 manifest, scanned all locally available refs using
  `gitleaks git --log-opts=--all --redact`: **50 commits, no findings**. The two
  remote branches are `main` and `marodysis`; there are no remote tags at audit time.
- At the initial audit, GitHub had one PR (#1), two Vercel bot comments, no inline comments/reviews,
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

## Committed source and GitHub verification — 2026-11-25

Preparation commit [`8edbd4d519478c7b42d877fcbf76b9130a7400f3`](https://github.com/rayubaldo44/classlens/commit/8edbd4d519478c7b42d877fcbf76b9130a7400f3)
was pushed normally to `main`, including seven existing local misconception-label
commits that preceded it. No remote history was overwritten. The
[exact-commit CI run](https://github.com/rayubaldo44/classlens/actions/runs/45547139136)
completed successfully: **Frontend, Backend, Browser smoke, and PostgreSQL integration**.
Fresh local checks also passed backend 136 tests, four frontend unit-test files,
lint/build, and six Chromium scenarios.

The preparation commit's source archive was inspected and excludes runtime
environment files, virtual environments, dependencies, model caches, and generated
test reports. Gitleaks scanned all 51 available commits after committing the
preparation and reported no findings. Upstream font-license line endings and
trailing spaces were normalized before commit; license wording is unchanged.

This verification does not authorize public visibility or a release tag. GitHub
confirmed the repository is still private. Follow the remaining publication gate
below and ensure the exact commit selected for a tag has passing CI, including
any subsequent documentation-only verification record.

## Maintainer publication gate

The previous preparation-only gate is superseded by the five gates in the
[revised plan](superpowers/plans/2026-11-25-open-source-release.md):

1. Contain the reachable hosted workflow and verify deployment/credential boundaries.
2. Resolve dependency advisories and installation provenance with fresh evidence.
3. Fix the reproduced grounding, request/edit-boundary, and admission weaknesses.
4. Review metadata/rights exposure and strengthen repository/tooling controls.
5. Verify the exact fixed candidate, obtain publication approval, and only then
   change visibility and tag/publish the [source-only notes](releases/v0.1.0.md).

The review refreshed the scan to 52 commits, six CI log archives, and current PR
discussion with no secret findings. It also found unresolved dependency advisories
and reproduced application gaps. All four CI jobs passed again on verification
record commit `1107ea7a9f0db604b3ac73ced1d53cb882a6ed28` in
[run 45547489379](https://github.com/rayubaldo44/classlens/actions/runs/45547489379);
these functional checks do not waive the new risk gates.

The default remains a local, single-user, single-process synthetic demo. No hosting
purchase, provider migration, package-registry publication, history rewrite, or
operational security change is authorized by this documentation update. Shared
hosted and real-student use require the separate safeguards in the revised plan.
