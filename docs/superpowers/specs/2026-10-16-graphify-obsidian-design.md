# Graphify and Obsidian Integration Design

**Status:** Approved on 2026-10-18; code graph/export, dashboard synchronization, final safety fixes, and scoped re-review implemented and verified by 2026-10-23.

**Implementation evidence:** 80 wrapper contract tests; successful real clean refresh with Graphify 0.9.77; 982 nodes / 2,983 links / 53 communities; 1,035 generated Markdown notes; all 982 Canvas file targets resolve from the containing Vault-EN root; saved-graph source checks and source-backed queries pass. A separate real-CLI document-contamination fixture rebuilt cleanly while preserving the prior graph in recovery. The final scoped review additionally verified both supported hyperedge provenance slots. See [current state](../../../STATUS.md) and [D-032](../../DECISIONS.md#d-032--local-code-graph-with-isolated-obsidian-export). The following behavior is reconciled with the pinned release rather than the original implementation-plan assumptions.

## Goal

Give ClassLens a reproducible, local-first code knowledge graph that Codex can query and that the existing Obsidian vault can browse without mixing generated graph notes with the hand-maintained project dashboard.

Success means a developer can build or refresh the graph with one repository command, query the saved graph locally, and open the generated notes and Canvas inside the existing ClassLens area of the Obsidian vault. The integration must not send repository documentation, student data, secrets, or provider output to an external semantic model.

## Selected approach

Use the official `graphifyy` package and its project-scoped Codex integration. Run Graphify in `--code-only` mode, retain its queryable working output under the ignored repository-local `graphify-out/` directory, and export generated Obsidian artifacts into an isolated `ClassLens/Graphify/` subtree.

This is preferred over exporting into the ClassLens project-note directory because generated symbol names could collide with personal notes. It is preferred over a separate vault because the user should be able to navigate from the existing ClassLens dashboard to the generated code graph.

## Components

### Tool installation and Codex integration

- Install the official PyPI package `graphifyy` as an isolated `uv` tool. The executable remains `graphify`.
- Register Graphify for Codex with a project-scoped installation so its skill and query-first guidance are reviewable with the repository.
- Use `graphify install --platform agents --project` for `.agents/skills/graphify/`. The 0.9.77 `codex` installer also created a hook; that output was removed and is not part of the integration.
- Inspect every installer-created change before retaining it. Existing ClassLens instructions remain authoritative, including the required status/task/history workflow.
- Pin the installed Graphify version in repository documentation and expose it through the verification command. The repository will not vendor Graphify's Python environment.

### Repository configuration

- Add `.graphifyignore` for documentation, dependency trees, virtual environments, caches, build output, browser artifacts, local worktrees, generated Graphify output, hidden environment files, and demo/evaluation data that should not become graph nodes.
- Keep application source, tests, migrations, and shell automation eligible for structural indexing. Markdown and other documents are skipped by the explicit code-only extraction mode.
- Add `graphify-out/` to `.gitignore`. It is a reproducible local artifact rather than an authoritative project document.
- Do not add Git hooks or watch mode in the initial integration. Refreshes remain explicit so commits cannot unexpectedly mutate the graph or external vault.

### Repository command

Add `scripts/graphify.sh` with these operations:

- `build`: verify prerequisites and reject symlinks in generated destinations; move prior graph inputs/cache into ignored `graphify-out/recovery/before-rebuild-*/`; run `graphify extract . --code-only` from that clean baseline; validate source scope before clustering; run `cluster-only . --no-label`; validate again and repair the report's refresh guidance; export HTML and Obsidian notes after another symlink check.
- `update`: use the same clean rebuild sequence with `graphify extract . --code-only --force`. Both native `update .` and forced code-only extraction can preserve document nodes in 0.9.77, so clean inputs and source validation are required.
- `check`: verify CLI/skill version `0.9.77`, actual saved JSON shape (graph object, non-empty nodes array, links array, non-empty `built_at_commit`), and every node/link/hyperedge source without rebuilding. Explicit sources must exist inside the repository, traverse no symlinks, use the ClassLens code/config allowlist, and pass Git plus Graphify exclusions. Only explicit AST/external-import reference stubs with validated incident code edges may have an empty source; missing, isolated, or ambiguous provenance fails. Upstream schema/version metadata fields are absent; none are fabricated. Destination validation occurs on build/update; `check` does not validate destination or freshness.
- `query <question>`: delegate to `graphify query` against the saved local graph.

The script resolves the Obsidian destination in this order:

1. `CLASSLENS_OBSIDIAN_GRAPH_DIR` for a one-command override;
2. the first non-empty line of ignored `.graphify-obsidian-dir` for machine-local persistence;
3. `graphify-out/obsidian` as a safe repository-local fallback.

The configured ClassLens machine-local value will be:

`/home/rayubaldo44/obsidian-developer-vault/Vault-EN/02_Projects/ClassLens/Graphify`

The script refuses an empty destination, the repository root, the filesystem root, or the hand-maintained `ClassLens` directory itself. It creates only the dedicated `Graphify` destination and relies on Graphify's ownership manifest to distinguish generated files from user files.

### Obsidian integration

- Export one generated note per graph node, generated community notes, and `graph.canvas` under `02_Projects/ClassLens/Graphify/`.
- Rewrite external Canvas file targets relative to the existing containing vault root, ignore the exporter's nested `.obsidian` when finding that root, and verify each target exists inside the dedicated generated folder.
- Preserve `ClassLens.md`, `ClassLens-Kanban.md`, the `Context/` notes, personal prose, frontmatter, plugin settings, and `.obsidian/` configuration.
- Add a concise link from the hand-maintained ClassLens project note to the generated `graph.canvas` and label it as generated, rebuildable code structure.
- Do not copy raw student responses, environment values, provider payloads, or evaluation reports into the vault.

## Data flow

1. The wrapper validates the Graphify executable and destination.
2. Graphify reads eligible repository code while honoring `.gitignore` and `.graphifyignore`.
3. Prior graph inputs/cache are recoverably archived; local structural extraction produces the saved graph under `graphify-out/`. Complete source-scope checks gate clustering and export; no-label clustering produces the report without selecting a semantic backend. Report guidance is repaired to use `./scripts/graphify.sh update`. Community names remain placeholders.
4. The HTML exporter regenerates the local interactive view from the saved graph.
5. The Obsidian exporter writes only Graphify-owned artifacts into the isolated external destination.
6. Codex queries the saved local graph with `graphify query`, `path`, or `explain`; Obsidian renders the generated wiki links and Canvas.

## Failure handling

- A missing `graphify` executable or unsupported version fails with an installation command and a nonzero exit status.
- A missing external vault is not created implicitly beyond the configured dedicated `Graphify` leaf. The script reports the expected parent and leaves the local export available.
- Extraction, source validation, or clustering failure prevents explicit exporters; source validation also precedes the clustering command's internal HTML writer. Prior graph inputs/cache remain recoverable and existing visuals are retained until upstream writers run. Upstream changes are not transactionally rolled back.
- Export failure reports which output failed and does not claim the integration is current.
- Clean rebuilds accept a smaller replacement graph. Developers should inspect unexpected count changes and manually retire old ignored recovery archives when no longer needed.
- The script never prints secrets, reads backend `.env` files, or auto-detects a semantic provider.

## Documentation and project state

- Add a README section covering installation, configuration, build, update, query, generated paths, privacy boundaries, and removal.
- Update the repository map to include the Graphify helper/configuration.
- Record the accepted local-only/tooling decision in `docs/DECISIONS.md`.
- After verified implementation, update `STATUS.md` and `TASKS.md`, append one meaningful milestone to `SESSION_PROGRESS.md`, and synchronize the existing ClassLens Obsidian project note and Kanban without copying generated graph detail into the dashboard.

## Verification

The implementation is complete only when all of the following pass:

- `scripts/graphify.sh check` reports valid pinned CLI/skill versions and actual saved graph structure.
- A clean `build` creates `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`, and the interactive HTML export.
- CLI/skill version checks and actual JSON-shape checks pass, and the graph contains representative Python and TypeScript source nodes. The optional SQL parser is unavailable in this installation, so the migration is eligible but not extracted.
- A scoped query returns graph-backed context for a ClassLens architecture question.
- The Obsidian destination contains generated notes and `graph.canvas` while the existing project note, Kanban, Context notes, and vault configuration remain unchanged except for the intentional dashboard link/status sync.
- A no-op `update` succeeds and retains a queryable graph.
- `git status` does not include generated graph output or machine-local destination configuration.
- Shell syntax checks, `git diff --check`, and the repository's narrow documentation/link checks pass.

Protected-file checksums verified all 108 existing project/Context/configuration files unchanged through the corrected real build and failed sandboxed refresh. The temporary baseline was unavailable after the earlier pre-hardening final-approved successful refresh, so no byte-for-byte comparison is claimed for that historical refresh. The latest hardened refresh at `a625910` has fresh checksum evidence: all 108 protected files remained unchanged during generated refresh, and the other 107 remained unchanged during the intentional dashboard correction. Export confinement is also supported by wrapper verification and Canvas target checks. Artifacts are parseable and readable; GUI/Obsidian rendering has not been verified. Broad queries may truncate at the default budget.

## Non-goals

- Indexing Markdown, PDFs, images, demo CSVs, student records, or provider responses.
- Graphify Cloud, hosted MCP, Neo4j, FalkorDB, embeddings, or external semantic-model calls.
- Automatically rebuilding on every commit or filesystem change.
- Committing generated graph data or Obsidian node exports.
- Replacing the authoritative repository documents or the concise Obsidian project dashboard with generated content.
- Changing ClassLens application behavior, API contracts, persistence, or production dependencies.
