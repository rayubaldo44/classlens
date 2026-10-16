# Graphify and Obsidian Integration Design

**Status:** Approved direction; awaiting written-spec review

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
- Inspect every installer-created change before retaining it. Existing ClassLens instructions remain authoritative, including the required status/task/history workflow.
- Pin the installed Graphify version in repository documentation and expose it through the verification command. The repository will not vendor Graphify's Python environment.

### Repository configuration

- Add `.graphifyignore` for dependency trees, virtual environments, caches, build output, browser artifacts, local worktrees, generated Graphify output, hidden environment files, and demo/evaluation data that should not become graph nodes.
- Keep application source, tests, migrations, and shell automation eligible for structural indexing. Markdown and other documents are skipped by the explicit code-only extraction mode.
- Add `graphify-out/` to `.gitignore`. It is a reproducible local artifact rather than an authoritative project document.
- Do not add Git hooks or watch mode in the initial integration. Refreshes remain explicit so commits cannot unexpectedly mutate the graph or external vault.

### Repository command

Add `scripts/graphify.sh` with these operations:

- `build`: verify prerequisites, run `graphify extract . --code-only`, export the interactive HTML graph, and export Obsidian notes.
- `update`: run `graphify update .`, regenerate the HTML graph, and refresh the Obsidian export.
- `check`: verify the executable/version, required project integration files, saved graph schema metadata, and configured Obsidian destination without rebuilding.
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
- Preserve `ClassLens.md`, `ClassLens-Kanban.md`, the `Context/` notes, personal prose, frontmatter, plugin settings, and `.obsidian/` configuration.
- Add a concise link from the hand-maintained ClassLens project note to the generated `graph.canvas` and label it as generated, rebuildable code structure.
- Do not copy raw student responses, environment values, provider payloads, or evaluation reports into the vault.

## Data flow

1. The wrapper validates the Graphify executable and destination.
2. Graphify reads eligible repository code while honoring `.gitignore` and `.graphifyignore`.
3. Local tree-sitter extraction produces the saved graph and report under `graphify-out/`; no semantic backend is selected.
4. The HTML exporter regenerates the local interactive view from the saved graph.
5. The Obsidian exporter writes only Graphify-owned artifacts into the isolated external destination.
6. Codex queries the saved local graph with `graphify query`, `path`, or `explain`; Obsidian renders the generated wiki links and Canvas.

## Failure handling

- A missing `graphify` executable or unsupported version fails with an installation command and a nonzero exit status.
- A missing external vault is not created implicitly beyond the configured dedicated `Graphify` leaf. The script reports the expected parent and leaves the local export available.
- Extraction failure prevents both exports, preserving the previously generated graph and vault artifacts for inspection.
- Export failure reports which output failed and does not claim the integration is current.
- The smaller-graph safety guard is never bypassed automatically. After a deliberate large deletion, a developer must inspect the warning and invoke Graphify's force behavior explicitly.
- The script never prints secrets, reads backend `.env` files, or auto-detects a semantic provider.

## Documentation and project state

- Add a README section covering installation, configuration, build, update, query, generated paths, privacy boundaries, and removal.
- Update the repository map to include the Graphify helper/configuration.
- Record the accepted local-only/tooling decision in `docs/DECISIONS.md`.
- After verified implementation, update `STATUS.md` and `TASKS.md`, append one meaningful milestone to `SESSION_PROGRESS.md`, and synchronize the existing ClassLens Obsidian project note and Kanban without copying generated graph detail into the dashboard.

## Verification

The implementation is complete only when all of the following pass:

- `scripts/graphify.sh check` reports the pinned installed version and valid local configuration.
- A clean `build` creates `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`, and the interactive HTML export.
- The graph metadata includes schema and Graphify version fields, and the graph contains representative Python and TypeScript source nodes.
- A scoped query returns graph-backed context for a ClassLens architecture question.
- The Obsidian destination contains generated notes and `graph.canvas` while the existing project note, Kanban, Context notes, and vault configuration remain unchanged except for the intentional dashboard link/status sync.
- A no-op `update` succeeds and retains a queryable graph.
- `git status` does not include generated graph output or machine-local destination configuration.
- Shell syntax checks, `git diff --check`, and the repository's narrow documentation/link checks pass.

## Non-goals

- Indexing Markdown, PDFs, images, demo CSVs, student records, or provider responses.
- Graphify Cloud, hosted MCP, Neo4j, FalkorDB, embeddings, or external semantic-model calls.
- Automatically rebuilding on every commit or filesystem change.
- Committing generated graph data or Obsidian node exports.
- Replacing the authoritative repository documents or the concise Obsidian project dashboard with generated content.
- Changing ClassLens application behavior, API contracts, persistence, or production dependencies.
