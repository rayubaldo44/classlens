# Graphify and Obsidian Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible, local-only Graphify workflow that produces a queryable ClassLens code graph plus isolated HTML and Obsidian visualizations.

**Architecture:** A strict Bash wrapper owns destination validation and delegates structural extraction, refresh, query, and export to a pinned Graphify CLI. Generated repository output and machine-local vault configuration stay ignored; the official project-scoped Codex skill is committed, while generated Obsidian notes live under the existing vault's isolated `ClassLens/Graphify/` subtree.

**Tech Stack:** Bash, Graphify `graphifyy==0.9.77`, `uv` tool management, JSON metadata checks, Codex Agent Skills, Obsidian Markdown and Canvas

**Spec:** `docs/superpowers/specs/2026-10-16-graphify-obsidian-design.md`

## Global Constraints

- Run extraction with `--code-only`; never configure or auto-detect a semantic backend.
- Keep application source, tests, SQL migrations, and shell automation eligible for structural indexing.
- Never index `.env` files, dependency trees, virtual environments, caches, browser output, local worktrees, demo/evaluation data, or Graphify's generated output.
- Never commit `graphify-out/`, `.graphify-obsidian-dir`, or generated Obsidian node exports.
- Do not install Graphify Git hooks or watch mode.
- Preserve all existing ClassLens instructions, authoritative documents, Obsidian prose/frontmatter, Kanban settings, Context notes, and `.obsidian/` configuration.
- The external export target must be the dedicated `/home/rayubaldo44/obsidian-developer-vault/Vault-EN/02_Projects/ClassLens/Graphify` leaf, never the hand-maintained `ClassLens` directory.
- The repository documents and wrapper must pin and verify `graphifyy==0.9.77`.
- Do not change ClassLens application behavior, APIs, persistence, production dependencies, or the rehearsed demo path.

## Review Focus

- Explicit empty, relative, root, repository-root, and hand-maintained ClassLens destinations must be rejected before an external write; Task 1 pins each case.
- A configured external destination whose parent vault folder is missing must fall back to `graphify-out/obsidian`, report the skipped external export, and return nonzero; Task 1 pins this degraded path.
- Extraction/update failure must prevent both exporters from running and leave prior generated markers untouched; Task 1 pins command order and failure behavior.
- `check` must reject a missing graph, malformed JSON, absent schema/version metadata, or an installed version other than `0.9.77`; Task 1 pins each diagnostic.
- `query` must reject an empty question and preserve a multi-word question as one CLI argument; Task 1 pins argument handling.

---

### Task 1: Safe Graphify wrapper and repository exclusions

**Files:**
- Create: `.graphifyignore`
- Create: `scripts/graphify.sh`
- Create: `scripts/tests/graphify_test.sh`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `graphify` CLI commands `extract`, `update`, `export html`, `export obsidian`, and `query`; optional `CLASSLENS_GRAPHIFY_BIN` and `CLASSLENS_OBSIDIAN_GRAPH_DIR`; optional ignored `.graphify-obsidian-dir`.
- Produces: `./scripts/graphify.sh <build|update|check|query QUESTION>`; ignored `graphify-out/`; validated Obsidian destination selection.

- [ ] **Step 1: Write the failing shell contract tests**

Create executable `scripts/tests/graphify_test.sh` with a temporary fake `graphify` binary and named cases asserting:

- `build` calls `extract . --code-only`, then `export html`, then `export obsidian --dir <resolved-dir>` in order;
- destination precedence is environment, config file, then `graphify-out/obsidian`;
- an explicitly empty environment destination, a relative path, `/`, the repository root, and the ClassLens vault root each exit nonzero without invoking the fake CLI;
- a missing external parent runs extraction and HTML export, writes the Obsidian export to `graphify-out/obsidian`, reports the configured parent problem, and exits nonzero;
- failed extraction/update invokes no exporter and retains an existing marker created by the fixture;
- `check` rejects a wrong CLI version, missing graph, invalid JSON, missing `schema_version`, and missing `graphify_version`, then accepts a graph containing both fields with version `0.9.77`;
- `query` rejects no question and logs one intact `what connects analysis to remediation?` argument.

- [ ] **Step 2: Run the contract tests to verify they fail**

Run: `bash scripts/tests/graphify_test.sh`

Expected: FAIL because `scripts/graphify.sh` and the repository configuration do not exist.

- [ ] **Step 3: Add the Graphify-specific ignore contract**

Create `.graphifyignore` with explicit patterns for `.git/`, `.worktrees/`, `graphify-out/`, `frontend/node_modules/`, frontend build/test artifacts, Python virtual environments/caches, `.env*` except no negated examples, `data/demo/`, and `backend/evaluation/`. Append `graphify-out/` and `.graphify-obsidian-dir` to `.gitignore`.

- [ ] **Step 4: Implement the wrapper command surface**

Create executable `scripts/graphify.sh` in the style of `scripts/demo.sh` with:

- constant `EXPECTED_GRAPHIFY_VERSION="0.9.77"`;
- `PROJECT_ROOT` derived from the script location and `GRAPHIFY_BIN="${CLASSLENS_GRAPHIFY_BIN:-graphify}"`;
- functions `usage()`, `fail(message)`, `require_graphify()`, `resolve_obsidian_dir()`, `validate_obsidian_dir(path)`, `export_graph()`, `build_graph()`, `update_graph()`, `check_graph()`, and `query_graph(question)`;
- explicit detection of a set-but-empty `CLASSLENS_OBSIDIAN_GRAPH_DIR`;
- absolute-path validation for configured external targets and exact rejection of `/`, `PROJECT_ROOT`, and `/home/rayubaldo44/obsidian-developer-vault/Vault-EN/02_Projects/ClassLens`;
- external targets restricted to a final path component named `Graphify`; the repository-local fallback `graphify-out/obsidian` is the only exception;
- `build` running from `PROJECT_ROOT` with `extract . --code-only`, `update` with `update .`, and exports only after success;
- `check` parsing `graphify-out/graph.json` with an available `python3` or `python`, asserting non-empty `graph.schema_version` and `graph.graphify_version`, and comparing installed version to `0.9.77`;
- `query` forwarding the joined non-empty question as one quoted CLI argument.

- [ ] **Step 5: Run focused wrapper verification**

Run: `bash -n scripts/graphify.sh scripts/tests/graphify_test.sh && bash scripts/tests/graphify_test.sh`

Expected: syntax checks exit `0`; all named wrapper cases print PASS and the test script exits `0`.

- [ ] **Step 6: Commit the safe wrapper**

```bash
git add .gitignore .graphifyignore scripts/graphify.sh scripts/tests/graphify_test.sh
git commit -m "feat: add safe Graphify workflow"
```

### Task 2: Pinned Graphify CLI and project-scoped Codex skill

**Files:**
- Create: `.agents/skills/graphify/SKILL.md`
- Create: `.agents/skills/graphify/references/*` (exact installer-owned files)
- Modify: `AGENTS.md` only if the official installer adds a bounded Graphify query-first block

**Interfaces:**
- Consumes: `uv 0.12.7+`, network access to official PyPI package `graphifyy==0.9.77`, Task 1 wrapper.
- Produces: `graphify` CLI version `0.9.77`; reviewable project-local `$graphify` skill; ClassLens instructions that preserve the existing start-of-task document reads.

- [ ] **Step 1: Install the exact CLI release in an isolated tool environment**

Run: `uv tool install graphifyy==0.9.77`

Expected: installation succeeds and `graphify --version` reports `0.9.77`. If another version is already installed, use `uv tool install --force graphifyy==0.9.77`; do not install similarly named PyPI packages.

- [ ] **Step 2: Register the official project-scoped Codex skill**

Run from the repository root: `graphify install --platform codex --project`

Expected: installer reports project-local skill/instruction files under `.agents/skills/graphify/` and, if applicable, a bounded addition to `AGENTS.md`; it must not install hooks.

- [ ] **Step 3: Audit installer output before keeping it**

Run: `git status --short && rg -n "graphify|hook|cloud|mcp|semantic|AGENTS" .agents/skills/graphify AGENTS.md`

Expected: only the Graphify skill sidecar and an intentional instruction block are new; no Cloud/MCP connection, Git hook, generated graph, secret, or weakened ClassLens instruction is present. Remove any installer output outside that boundary with a targeted patch rather than a broad checkout/reset.

- [ ] **Step 4: Verify the pinned integration**

Run: `graphify --version && bash scripts/tests/graphify_test.sh`

Expected: version `0.9.77`; wrapper contract tests all pass.

- [ ] **Step 5: Commit the Codex integration**

```bash
git add AGENTS.md .agents/skills/graphify
git commit -m "chore: register Graphify for Codex"
```

Omit `AGENTS.md` from `git add` if the installer does not change it.

### Task 3: Build, query, and export the real ClassLens graph

**Files:**
- Create (ignored): `.graphify-obsidian-dir`
- Create (ignored): `graphify-out/*`
- Create (external, generated): `/home/rayubaldo44/obsidian-developer-vault/Vault-EN/02_Projects/ClassLens/Graphify/*`

**Interfaces:**
- Consumes: Task 1 wrapper, Task 2 pinned CLI/skill, existing ClassLens source tree, existing Obsidian ClassLens parent folder.
- Produces: local `graph.json`, `GRAPH_REPORT.md`, `graph.html`; external generated notes and `graph.canvas`; a successful scoped architecture query.

- [ ] **Step 1: Record the machine-local export destination**

Create ignored `.graphify-obsidian-dir` containing exactly `/home/rayubaldo44/obsidian-developer-vault/Vault-EN/02_Projects/ClassLens/Graphify` plus a trailing newline. Confirm `git check-ignore -v .graphify-obsidian-dir` identifies `.gitignore`.

- [ ] **Step 2: Snapshot user-owned Obsidian files before export**

Run SHA-256 checksums over `ClassLens.md`, `ClassLens-Kanban.md`, every `Context/*.md`, and any `.obsidian` configuration under the vault root, saving the checksum list under `/tmp` rather than the repository or vault.

Expected: the snapshot includes every existing user-owned file and no secrets or generated Graphify files.

- [ ] **Step 3: Build and export the graph**

Run: `./scripts/graphify.sh build`

Expected: structural extraction explicitly reports code-only/local behavior; `graphify-out/graph.json`, `GRAPH_REPORT.md`, and `graph.html` exist; the dedicated external `Graphify/` directory contains generated Markdown notes and `graph.canvas`.

- [ ] **Step 4: Validate graph content and privacy boundary**

Run `./scripts/graphify.sh check`, then inspect graph metadata and node sources with a read-only JSON query.

Expected: schema/version metadata is present, Python nodes from `backend/app/` and TypeScript nodes from `frontend/src/` are present, and no node source references `.env`, `data/demo`, `backend/evaluation`, `node_modules`, `.venv`, `.worktrees`, or `graphify-out`.

- [ ] **Step 5: Verify graph-backed querying and incremental refresh**

Run: `./scripts/graphify.sh query "what connects assessment intake to misconception analysis?"` and then `./scripts/graphify.sh update`.

Expected: the query returns scoped graph context with source relationships; the no-op update succeeds and both local and Obsidian visual exports remain readable.

- [ ] **Step 6: Prove user-owned vault files were preserved**

Recompute the Task 3 Step 2 checksums and compare them before any intentional dashboard edit.

Expected: no user-owned project note, Kanban, Context note, or `.obsidian` configuration changed; all new files are confined to `ClassLens/Graphify/`.

### Task 4: Authoritative documentation and repository milestone

**Files:**
- Modify: `README.md`
- Modify: `docs/DECISIONS.md`
- Modify: `docs/superpowers/specs/2026-10-16-graphify-obsidian-design.md`
- Modify: `STATUS.md`
- Modify: `TASKS.md`
- Modify: `SESSION_PROGRESS.md`
- Modify: `task_plan.md`
- Modify: `findings.md`
- Modify: `progress.md`

**Interfaces:**
- Consumes: verified commands, exact installed version, graph statistics/output paths, privacy inspection, and vault-preservation evidence from Tasks 1–3.
- Produces: reproducible setup/usage instructions and current project state that distinguish committed integration from ignored generated artifacts.

- [ ] **Step 1: Document setup and operations**

Add a `## Code knowledge graph` section to `README.md` with exact pinned installation, project skill registration, `.graphify-obsidian-dir` setup, `build`, `update`, `check`, and `query` commands; describe `graph.html`, `GRAPH_REPORT.md`, and `graph.canvas`; state the local-only/code-only privacy boundary, ignored outputs, explicit refresh policy, and uninstall/removal commands. Update the repository map with `.graphifyignore` and `scripts/graphify.sh`.

- [ ] **Step 2: Record the accepted tooling decision**

Add the next numbered dated entry to `docs/DECISIONS.md`: official `graphifyy==0.9.77`, code-only extraction, explicit refreshes, ignored local graph, isolated Obsidian export, and no Cloud/MCP/hooks.

- [ ] **Step 3: Reconcile current state and history**

Mark the design status approved/implemented, add the verified Graphify integration to `STATUS.md`, move its task from planned to completed in `TASKS.md`, and append one 2026-10-18 milestone to `SESSION_PROGRESS.md` covering files, verification, problems, decisions, remaining limitations, and the next step. Update the root planning files with completed phases, exact outputs, and any errors encountered; do not rewrite their prior campaign history.

- [ ] **Step 4: Validate documentation and ignored artifacts**

Run a repository-relative Markdown link checker using the existing Python runtime, `git diff --check`, `git check-ignore -v graphify-out/ .graphify-obsidian-dir`, and `git status --short`.

Expected: every repository-relative Markdown link resolves; no whitespace errors; both generated paths are ignored; only intended source/documentation changes appear.

- [ ] **Step 5: Commit the verified repository milestone**

```bash
git add README.md docs/DECISIONS.md docs/superpowers/specs/2026-10-16-graphify-obsidian-design.md STATUS.md TASKS.md SESSION_PROGRESS.md task_plan.md findings.md progress.md
git commit -m "docs: record Graphify Obsidian integration"
```

### Task 5: Obsidian dashboard link, final verification, and review

**Files:**
- Modify (external): `/home/rayubaldo44/obsidian-developer-vault/Vault-EN/02_Projects/ClassLens/ClassLens.md`
- Modify (external only if task state changes): `/home/rayubaldo44/obsidian-developer-vault/Vault-EN/02_Projects/ClassLens/ClassLens-Kanban.md`

**Interfaces:**
- Consumes: verified repository milestone and generated external `Graphify/graph.canvas` from Tasks 3–4; `obsidian-project-sync` preservation rules.
- Produces: one dashboard link to the generated visual, concise synchronized project state, and final evidence that repository and vault integrations remain healthy.

- [ ] **Step 1: Synchronize the existing ClassLens notes**

Use the Obsidian project sync workflow to update `modified`, current verified tooling status, one concise milestone/progress entry, and the appropriate Kanban state. Add a clearly labeled link or embed to `[[02_Projects/ClassLens/Graphify/graph.canvas|Generated code graph]]`; preserve all unrelated frontmatter, prose, personal links, and Kanban plugin settings.

- [ ] **Step 2: Read back and validate the vault changes**

Confirm the dashboard link resolves to the generated Canvas, generated files remain confined to `ClassLens/Graphify/`, and no raw student response, secret, environment value, provider payload, or evaluation report appears in the changed notes.

- [ ] **Step 3: Run the complete final verification set**

Run:

```bash
bash -n scripts/graphify.sh scripts/tests/graphify_test.sh
bash scripts/tests/graphify_test.sh
./scripts/graphify.sh check
./scripts/graphify.sh query "what connects assessment intake to misconception analysis?"
git diff --check
git status --short
```

Expected: every command succeeds; the query is graph-backed; generated and machine-local files remain absent from Git status; external Canvas and HTML visuals exist.

- [ ] **Step 4: Request whole-change code review**

Use `superpowers:requesting-code-review` for the complete branch/diff, focusing on destination safety, no-semantic-backend guarantees, installer changes to `AGENTS.md`, ignored-data coverage, vault preservation, and reproducibility.

- [ ] **Step 5: Address review findings and commit only source fixes**

Apply verified findings, rerun the complete verification set, and commit any repository fixes with a focused message. Do not commit generated graph or vault output.
