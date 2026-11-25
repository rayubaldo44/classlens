# ClassLens risk-gated open-source release plan

**Current state: HOLD publication.** The [deep risk review](../../OPEN_SOURCE_RISK_REVIEW.md)
supersedes the original preparation-only release gate. Its reviewed source is
`1107ea7a9f0db604b3ac73ced1d53cb882a6ed28`. Passing functional CI is preserved
historical evidence, not security approval. The tasks below are **planned and
unimplemented**; this review does not authorize remote settings or access changes.

## Release defaults

- Release original work under the selected MIT license as a **local, single-user,
  single-process synthetic-data demo**. Keep Python 3.11, React/FastAPI/PostgreSQL,
  and the existing provider/model until compatible security updates are verified.
- Keep the existing-history publication target, subject to explicit metadata
  sign-off. Preserve the private repository and append-only logs. A fresh public
  snapshot is an alternative requiring a new maintainer decision, not an automatic
  cleanup or history rewrite.
- Do not operate a public workflow API as part of this source release. Full
  teacher authentication, ownership, privacy governance, aggregate spend policy,
  and multi-process operation remain separate hosted/pilot gates.
- Every gate below needs evidence on the exact candidate commit. No secret,
  existing student record, or production write is needed for verification.

## Gate 1 — Contain existing hosted exposure before publication

- [ ] Have the service owner suspend the documented Render workflow API or put
  hosting-level access controls in front of **all** workflow routes and direct
  origins. Check previews, alternate domains, and the frontend's compiled API URL.
  The default source-only release uses a stopped or inaccessible hosted backend.
- [ ] Verify from an unauthenticated external client that direct workflow routes
  cannot reach persistence or Gemini. Use known-nonexistent synthetic identifiers
  and local provider-call counters for tests; do not inspect live records or
  trigger production generation. Health/OpenAPI availability alone is not proof
  either way. A timeout is inconclusive and leaves this gate open.
- [ ] Review provider usage and hosted secret scopes; rotate credentials if
  suspicious use/exposure is found. Keep local demo keys separate from hosted
  credentials. A static public landing page may remain only with truthful
  availability text and no promised connected hosted workflow.
- [ ] For any retained hosted runtime, obtain a read-only database metadata review: actual app-role ownership,
  superuser/BYPASSRLS, grants/policies, anonymous/authenticated access, and network
  controls. Prefer a least-privilege runtime role separate from migration access.
  Current connector denial/connection failure leaves this unverified; do not
  assert that enabling RLS in migrations protects unauthenticated FastAPI calls.
  If the hosted runtime is fully retired and its database/provider credentials
  disconnected or revoked, document that containment as the source-release
  alternative; a live-role review remains mandatory before operated use resumes.

**Acceptance:** owner evidence plus external access checks establish containment;
service-specific credential/data boundaries are recorded without secret values.
These operational changes require separate authorization before execution.

## Gate 2 — Resolve dependency advisories and verify install provenance

- [ ] Resolve a compatible patched frontend lock, covering the reported Vite,
  Zod, minimatch, and transitive toolchain entries. Start from the advisory floors
  in the risk report; do not apply an unreviewed force-upgrade.
- [ ] Update the critical certifi trust bundle before recommending a new install.
  Triage all matches for pyasn1, filelock, OpenTelemetry, pytest, and CPU Torch.
  Account for the pytest `<9` manifest cap, CPU wheel availability, Python 3.11,
  model compatibility, and each advisory's actual affected function/platform.
- [ ] For every high/critical match, fix the affected version or record exact
  advisory ID, affected path, non-reachability evidence, compensating control,
  owner, and an expiry no later than 30 days. Scanner omissions are not waivers.
  Document moderate matches too; deduplicate GHSA/PYSEC aliases. Torch local
  `+cpu` normalization and untrusted-checkpoint assumptions must be explicit.
- [ ] Regenerate locks and the dependency-license inventory. Hash Python artifacts
  and isolate the CPU Torch artifact source rather than letting ordinary packages
  compete across indexes. Preserve npm integrity data and the pinned model
  revision; keep caches private and do not accept uploaded model/checkpoint files.
- [ ] Fresh-install the resulting candidate; run `pip check`, current npm/OSV
  advisory checks, backend/frontend/browser/PostgreSQL checks, and the live local
  synthetic golden path. Capture actual installed versions and platform limits.

**Acceptance:** no untriaged high/critical matches, a verified compatible lock,
and provenance that matches the documented clean install. Existing passing CI
does not satisfy this new gate without refreshed dependency evidence.

## Gate 3 — Close reproduced application boundary weaknesses

- [ ] **Server-derived grounding (R3):** keep the existing generation request
  shape for frontend compatibility, but treat its retrieval snapshot only as an
  assertion. Re-run retrieval using canonical stored group/material evidence and
  current server settings. Use only those server-selected passages/scores in the
  prompt, saved provenance, and export. An unexpected supplied chunk selection
  fails with structured 409 before Gemini; insufficient server context uses the
  existing insufficient-context response and makes zero provider calls. Never
  validate a supplied score against a supplied threshold as the fix.
- [ ] **Request bounds (R4/R5):** add a configurable streamed ASGI total-body bound
  before parsing, default **2 MiB**, while retaining the existing **1,000,000-byte**
  per-file contract. Reject over-limit actual bytes with structured 413, even
  without Content-Length or with chunked input; reject excess multipart file/field
  counts. Do not buffer an unbounded body to measure it.
- [ ] Bound analogy, follow-up prompt, and expected answer to **4,000 characters
  each**, matching the existing main prose-field ceiling; retain 1–3 follow-up
  questions and the 2,000-character review-note ceiling. Apply schema/service
  validation before persistence or provider calls. Preserve existing error
  semantics for field validation and document the 413 body-limit envelope.
- [ ] Enforce server retrieval top-k (default 3) and a **12,000-character combined
  source-passage budget** before Gemini. Valid default chunks fit comfortably;
  oversized configured contexts fail with a structured 413 rather than truncating
  evidence silently. Update API documentation only for these concrete bounds.
- [ ] **Admission and retained state (R6):** allow at most **10 running-plus-queued
  synchronous jobs** per process with the existing five workers; excess requests
  fail fast with retryable 503. An awaiting semaphore that accumulates unlimited
  request waiters is not an admission limit. Cancellation must not release a slot
  while its underlying work is still running. Bound the rebuildable material
  vector cache to **16 entries**, using LRU eviction; release idle lock-map entries
  only when no holders/waiters remain, preserving canonical serialization.

**Required regression cases:** forged high scores on irrelevant canonical text;
changed rank/threshold/status and excess passages; exact source text remains
immutable; missing/deleted/stale records; 2 MiB boundary and one-over streaming
requests; one-million-byte file behavior; too many file parts; each edited field
at 4,000/4,001; full queue/cancellation/recovery; cache eviction/rebuild and active
lock safety. Assert rejected requests persist nothing and call no provider.

**Acceptance:** each reproduced weakness has a failing-before/passing-after
regression, full affected-package gates pass, and the real synthetic workflow
retains teacher approval, accurate sources, and restart recovery.

## Gate 4 — Review public content, tooling, and repository controls

- [ ] Inventory exposure per ref: contributor identities, current/historical
  machine paths, architecture receipts, logs, PR/bot comments, deployment links,
  archives, and assets. Get publication sign-off from the relevant contributors.
  A forward edit does not sanitize history. Preserve original licenses/attribution
  and append-only logs; do not silently replace their historical content.
- [ ] Remove unnecessary current-machine paths from active setup/tooling without
  weakening Graphify destination safety. Mark a project-local, wrapper-only guard
  in the bundled skill; preserve its upstream notices and disallow direct generic
  installers, automatic provider selection, and semantic submission in the
  project workflow. Re-run the wrapper's safety tests after any such change.
- [ ] Pin CI actions to reviewed full commit SHAs and the PostgreSQL image to a
  reviewed digest; set checkout `persist-credentials: false`. Preserve read-only
  tokens and credential-free tests. Add pinned secret/dependency checks with
  scheduled rechecks; keep untrusted PR code away from deployment credentials.
- [ ] Define `.github/CODEOWNERS` coverage for workflows, dependency locks, agent
  instructions, release/security docs, and migrations. Verify applicable branch
  review/check rules, fork-run approvals for all outside collaborators, reporting,
  and secret protection when the account/repository supports them. Record denied
  or unavailable settings honestly and verify after the visibility transition.

**Acceptance:** a source archive and every exposed ref pass the final secret and
manual metadata/rights review. Relevant owners accept unavoidable public history
and MIT commercial-reuse/copying consequences. Security-setting evidence is
current; private-reporting instructions lead to a tested private channel.

## Gate 5 — Final release and separate hosted/pilot gates

- [ ] Review all findings with their fixes/containment or narrowly evidenced
  residual-risk decisions. Update STATUS/TASKS and authoritative docs, preserving
  prior verification history. Repeat all candidate-commit CI checks and scans.
- [ ] Obtain explicit approval for the exact visibility change and `v0.1.0` tag.
  Immediately verify required public-repository settings and reporting. If a
  required control is unavailable, pause release publication until the approved
  alternative is documented; do not assume making the repo private recalls copies.
- [ ] Publish the source-only notes from the exact passing commit. Keep hosted
  access contained, synthetic examples honest, and school-readiness claims absent.

Before any shared hosted operation: select authentication deliberately, enforce
ownership across every read/write, validate a least-privilege database role,
establish atomic provider usage/rate/spend admission, and verify privacy/retention
and deletion requirements. Before multiple processes/replicas (R7), add shared
transactional review/generation coordination and a real two-process PostgreSQL
race test. The injected fake-store ordering is not that test. These are separate
projects, not required LMS expansion for a contained source release.

## Original preparation completed — historical record

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
