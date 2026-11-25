# Open-source risk review — 2026-11-25

**Verdict: HOLD public publication.** Functional tests and CI passed, but that
evidence did not establish safe public operation or current dependency security.
Keep the repository private until the [revised release gates](superpowers/plans/2026-11-25-open-source-release.md)
pass. This review proposes mitigations; it does not implement them.

## Scope and evidence

Reviewed source commit `1107ea7a9f0db604b3ac73ced1d53cb882a6ed28`, all locally
available Git refs, dependency locks, release/archive boundaries, CI configuration,
GitHub settings, and documented frontend/backend origins. Three focused source
reviews were followed by offline synthetic probes and independent challenge of
the backend findings. No existing student/workflow records were read, no hosted
writes or real Gemini generation were performed, and no settings were changed.

Severity below describes potential impact under its stated conditions. A package
advisory match, an exposed health endpoint, and a reproduced application weakness
are different evidence classes. None establishes a breach.

Confirmed observations:

- The documented Vercel frontend returns HTTP 200; its deployed JavaScript still
  points to the documented Render backend. Render `/health` and `/openapi.json`
  returned HTTP 200 without credentials. OpenAPI declares no security schemes.
  A GET for a deliberately nonexistent remediation timed out; it did not prove
  either record access or isolation. No real record identifiers were probed.
- Gitleaks 8.30.1 reported no findings across **52 commits**, all **six** Actions
  log archives, and current PR discussion (one PR, two bot comments, no inline
  comments/reviews). GitHub reported no uploaded Actions artifacts.
- GitHub remains private. Actions allow all action sources and do not require
  SHA pins. Default workflow tokens are read-only and cannot approve PRs.
  Protection/ruleset queries returned plan-related 403 responses; private
  vulnerability reporting returned 404; public-fork approval settings were not
  applicable while private. These checks do not establish protected `main` or a
  working private report channel.
- Supabase advisor access was denied, and two bounded application-connection
  metadata attempts failed. Actual database role privileges, RLS bypass, grants,
  policies, network restrictions, and retained data remain **unverified**.
  Checked-in migrations enable RLS; that alone does not authorize FastAPI callers.

Raw audit data and synthetic probes remain outside the release tree. The summary
omits contributor email values, home-directory identities, credentials, and
service-internal identifiers.

## Findings and required treatment

### R1 — Access and provider spending are uncontrolled if the API is unrestricted

**HIGH, conditional on reachable workflow routes and configured data/provider.**
All workflow routes lack a caller identity and per-record ownership checks.
The offline ASGI probe read a synthetic analysis without credentials and approved
a synthetic intervention. Distinct valid generation request IDs caused three
fake-provider calls for the same evidence: request idempotency is not a global
quota. There is no aggregate rate/spend admission control.

Evidence: [route registration](../backend/app/main.py),
[remediation read/review routes](../backend/app/api/routes/remediations.py),
[generation service](../backend/app/services/remediation.py).
These are documented demo limitations; reachable health/OpenAPI plus the local
probe is not a demonstrated live data-access exploit.

**Release treatment:** suspend or enforce hosting-level access restrictions on
every connected API origin and preview before publication. Verify direct-origin
and alternate-host access independently of the frontend. Keep the source release
local, single-user, synthetic-only. Any operated shared demo must first add caller
authentication, record ownership, and aggregate provider admission/spend controls.
Review provider usage for unexpected activity; rotate affected credentials if
exposure or suspicious use is found. Do not equate CORS with authorization.

### R2 — Locked dependency versions have current security advisories

**HIGH release-priority; advisory severities and application reachability vary.**
`npm audit --json` reports **11 affected package entries: two high, nine moderate**.
These include transitive reports, not 11 independent exploits. Vite, Zod, and
minimatch are development dependencies; the static production frontend does not
run Vite's development server. A separate `npm audit --omit=dev --json` returned
**zero reported production-dependency matches**. Developers and CI still install
the affected toolchain; this result does not cover Python or prove exploit absence.

OSV queried all **70 exact Python lock entries**; Torch's CPU local version was
queried as upstream `2.7.1`. Six distributions matched advisories. Alias duplicates
must be folded before counting vulnerabilities. Relevant update candidates:

| Package in lock | Advisory / initial patched floor | Applicability and required follow-up |
|---|---|---|
| `certifi 2026.7.22` | [GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2), critical; `2026.10.18` | Bundled trust-root concern; relevant to outbound TLS trust. Prioritize update and verify all outbound connections. |
| `vite 8.3.1` | Multiple editor/file-serving advisories; `8.3.3` in the affected 8.3 line, including [GHSA-9jrq-w75r-8gcw](https://github.com/advisories/GHSA-9jrq-w75r-8gcw) | Some require Windows, particular editors, dev-server access, or custom middleware. Review each advisory; do not claim static-site compromise. |
| `zod 4.6.5` | [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5), high; `4.6.6` | Transitive toolchain dependency; public application request reachability not established. |
| `minimatch 10.2.6` | [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249), moderate | Resolve a patched compatible dependency graph and re-audit the actual lock. |
| `pyasn1 0.6.4` | Four high decoding-complexity matches; `0.6.5` | Untrusted ASN.1 decoding must be traced through upstream authentication dependencies; no direct application decoder found. |
| `opentelemetry-api 1.45.0` | Trace parsing advisories; `1.45.2` covers the observed patch floors | No direct application trace-header extraction found; inspect SDK instrumentation before claiming remote reachability. |
| `filelock 3.32.3` | Local lock-path/permission advisories; highest observed patch floor `4.2.1` | Shared writable filesystem and platform conditions matter. Model caches need private ownership; a major upgrade needs compatibility verification. |
| `pytest 8.4.2` | Temporary-directory handling; `9.0.3` | Test dependency; current manifest caps pytest below 9. Resolve the manifest constraint deliberately and verify tests. |
| `torch 2.7.1+cpu` | Multiple matches, including [untrusted-checkpoint RCE](https://github.com/advisories/GHSA-63cw-57p8-fm3p), fixed for that advisory in `2.10.0` | Other matches have different floors, up to `2.13.0`, or no fixed event. No checkpoint-upload API exists; the embedding repository/revision is pinned. Model-loader/deserialization applicability still needs review. |

These are advisory-derived candidate floors, **not tested replacement locks**.
Do not select one version as fixing every Torch/filelock issue. Resolve compatible
versions in isolation, inspect upstream affected paths, and regenerate the locks
and license inventory. Every unresolved high/critical match needs either a fix or
an explicit, narrowly evidenced non-reachability exception with owner and expiry;
the critical trust-root issue should be fixed before a new recommended install.

### R3 — Client retrieval metadata bypasses the server's relevance gate

**MEDIUM, reproduced offline.** Generation reloads exact stored chunks but copies
the browser's retrieval status, scores, and metadata. The probe's real retrieval
returned `insufficient_relevant_context` for an unrelated canonical passage;
generation accepted that same passage with a supplied score of `1.0` and reached
the fake provider. The service also lacks an enforced server-selected top-k bound
at this boundary.

Evidence: [canonicalization](../backend/app/services/remediation.py), especially
the construction of `canonical_results` / `canonical_retrieval`, and
[retrieval filtering](../backend/app/services/material_retrieval.py).

This preserves real source text: it does **not** prove invented citations or
harmful real-model output. **Fix before source release:** derive retrieval from
canonical evidence and server settings at generation time. Never accept supplied
scores/status as proof of relevance. Preserve fail-closed insufficient-context
behavior, server provenance, and teacher approval.

### R4 — File limits apply after multipart spooling

**MEDIUM, bounded local probe.** All upload handlers check their one-million-byte
file limit after FastAPI/Starlette parses multipart input. A **1,048,593-byte**
synthetic file returned 413 only after all bytes had been written and the spool
had rolled to disk. Installed FastAPI 0.142.2 / Starlette 1.7.0 match the lock;
the parser's part-size bound applies to ordinary fields rather than file content.

Evidence: [upload routes](../backend/app/api/routes/assessments.py),
[material upload](../backend/app/api/routes/materials.py), and
[middleware setup](../backend/app/main.py).

**Fix:** bound actual streamed request bytes before multipart parsing and cap
file/field counts. Content-Length checks alone are insufficient. Test chunked
and missing-length requests. This is a transient/concurrent disk and processing
risk; automatic file closure exists and no persistent tempfile leak was shown.
Unknown proxy limits may reduce deployed impact but are not an application bound.

### R5 — Some teacher-edit text fields are unbounded

**MEDIUM, reproduced with fake persistence.** A PATCH accepted and persisted
4,001 characters each in analogy, follow-up prompt, and expected answer (HTTP
200). A 4,001-character teacher explanation correctly failed (HTTP 400).
Evidence: [schemas](../backend/app/schemas/remediations.py) and
[`_validate_edit`](../backend/app/services/remediation.py).

**Fix:** impose consistent schema/service limits on every edited prose field and
the complete JSON body before persistence. Keep the existing 1–3 follow-up count
and source-lock checks. Saves overwrite records; repeated fixed-size saves were
not shown to cause cumulative record growth.

### R6 — Five workers do not bound pending jobs or retained process state

**MEDIUM, local queue probe plus static cache review.** With five workers held,
20 additional jobs were accepted into the executor queue. Embedding access is
serialized. Vector caches and per-identifier lock maps have no explicit eviction.
Evidence: [executor](../backend/app/concurrency.py),
[embedding lock](../backend/app/providers/embeddings/sentence_transformer.py),
[material repositories](../backend/app/providers/postgres.py), and generation/review services.

**Fix:** add finite fail-fast admission before enqueueing and a bounded vector
cache. Release lock-registry entries only when no holder or waiter can reference
them. The probe demonstrates missing admission capacity, not HTTP exhaustion;
cancellation and unknown hosting concurrency limits can change real impact.

### R7 — Review/generation locking is process-local

**MEDIUM conditional design concern; concurrent PostgreSQL reproduction pending.**
Separate worker processes do not share the Python lock registry, while review
updates and intervention insertion use separate database transactions. A fake
store injected an intervening review action, but its same-thread callback can
re-enter an `RLock`: it is **not a concurrency demonstration**.

Evidence: [generation save/recheck](../backend/app/services/remediation.py),
[review lock](../backend/app/services/group_reviews.py), and
[PostgreSQL transactions](../backend/app/providers/postgres.py).

**Treatment:** retain the documented single-process demo. Before multiple workers
or replicas, coordinate review revision checking and intervention insertion in a
shared transaction/lock, then pass a real two-process disposable-PostgreSQL race
test. Do not describe this as an exploited hosted race.

### R8 — Publishing existing history exposes personal and deployment metadata

**Privacy/reversibility gate; no credential finding.** Current tracked text has
home-path patterns in 23 files (160 occurrences). Main's 52-commit ancestry has
one non-noreply email identity; all available refs have two. Bot comments contain
team/deployment/access-request metadata. The earlier README path cleanup does
not remove historical copies.

**Treatment:** inventory each ref and exposure class, get the relevant publication
sign-off, and remove unnecessary current-machine paths. Preserve the append-only
development log. Keep the selected existing-history strategy only with that
sign-off; otherwise propose a separately sanitized public source snapshot while
retaining the original private history. Do not rewrite history automatically.
Copies and forks cannot reliably be recalled after publication.
[GitHub visibility guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)

### R9 — Supply-chain and maintainer controls need stronger evidence

**LOW hardening gaps, not compromised-dependency findings.** CI uses mutable
action major tags and a PostgreSQL image tag; checkout leaves credentials
persisted by default. Python versions are locked without artifact hashes and
share a secondary CPU-wheel index. Existing defenses include read-only tokens,
hosted ephemeral runners, credential-free tests, npm integrity hashes, and no
`pull_request_target` workflow.

**Treatment:** pin action commits and image digest, disable persisted checkout
credentials, isolate/hash Python artifact provenance, add dependency/secret checks,
and require reviewed changes to workflows/security controls. Configure and verify
public-fork workflow approvals, branch rules, secret protection, and private
reporting when available. Unavailable controls require a documented alternative,
not a claim that they are enabled. See [GitHub secure use](https://docs.github.com/en/actions/reference/security/secure-use)
and [pip secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/).

### R10 — Optional agent tooling contains a broader upstream workflow

**LOW, conditional; no demonstrated disclosure.** The bundled generic Graphify
skill documents unpinned installers/system overrides and semantic extraction
using ambient Gemini credentials. The project AGENTS rule and pinned wrapper
already require code-only local extraction. Directly following the generic
workflow would bypass that boundary.

**Treatment:** put a project-specific wrapper-only guard at the skill entry,
mark the local modification, preserve upstream notices, and verify project
instructions cannot route into automatic provider selection or system installs.
Keep actual Gemini credentials out of CI and developer-tool extraction.

## Existing defenses and residual risk

No obvious SQL injection, upload path traversal, or frontend/export HTML execution
sink was found in the inspected call chains. SQL parameters, fixed demo paths,
React text rendering, escaped script-free export, canonical chunk text/offset
checks, bounded provider duration/output/retry, and explicit teacher approval
remain useful defenses. That is review scope, not a universal absence claim.

Gemini instruction resistance and citation-ID validation do not establish that
every generated educational claim is supported; earlier live evaluation already
recorded an unsupported detail. Continue synthetic-only inputs and teacher review.
Real student use needs separate privacy, retention/deletion, institutional and
provider-account review, plus authentication/ownership. Actual DB role/RLS
privileges and external hosting controls must be verified before operated use.

MIT permits commercial reuse under its notice conditions; publishing cannot
prevent copying or guarantee attribution beyond license terms. The maintainer
confirmed original-work rights, but this audit is not independent verification
of that ownership. Preserve third-party terms. A source release avoids operating
a public school service; it does not eliminate dependency, privacy, or reuse risk.
