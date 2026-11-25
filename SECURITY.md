# Security policy

ClassLens is an experimental demo. Only the current default branch is maintained;
older snapshots have no security-support commitment.

Public release is currently on hold following the
[2026-11-25 risk review](docs/OPEN_SOURCE_RISK_REVIEW.md). The identified mitigations
are not yet implemented. Passing functional CI does not establish safe public
operation; the revised release plan requires verified hosted containment and
dependency/input/grounding hardening first.

## Report a vulnerability

Use GitHub's private **Report a vulnerability** action on this repository's
[Security tab](https://github.com/rayubaldo44/classlens/security).
If that action is unavailable, open an issue asking only for a private reporting
channel; do not include vulnerability details, exploit code, credentials, or data.

Include affected versions, a minimal synthetic reproduction, expected impact,
and suggested mitigations in the private report. Do not send real student data.
There is no guaranteed response time or bug bounty.

## Deployment boundary

The MVP has no teacher authentication, API record ownership checks, or complete
privacy/retention/deletion workflow. CORS is not authorization. Run it locally
with synthetic data and your own credentials; do not expose an unrestricted API
or use real student data. Pilot prerequisites are tracked in [TASKS.md](TASKS.md#required-before-real-student-data).

Gemini receives selected response evidence and teacher-provided source passages.
Its availability, billing, and data handling depend on your provider account.
Store keys only in ignored backend configuration, never `VITE_*` variables.
The model download and PostgreSQL service are additional runtime dependencies.
