"""Local safety checks around the pinned Graphify CLI; standard library only."""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def reject_symlinks(destination: Path) -> None:
    """Do this before upstream writers: checking Canvas after export is too late."""
    if destination.is_symlink():
        raise ValueError(f"generated destination contains a symlink: {destination}")
    if not destination.exists():
        return
    if not destination.is_dir():
        raise ValueError(f"generated destination must be a directory: {destination}")
    for directory, directories, files in os.walk(destination, followlinks=False):
        for name in directories + files:
            child = Path(directory) / name
            if child.is_symlink():
                raise ValueError(f"generated destination contains a symlink: {child}")


def prepare_graph() -> None:
    """Keep exports readable while removing all prior graph inputs from merge scope."""
    output = Path("graphify-out")
    reject_symlinks(output)
    inputs = [
        child for child in output.iterdir()
        if child.name in {"graph.json", "manifest.json", "cache"}
        or child.name.startswith(".graphify_")
    ] if output.exists() else []
    if inputs:
        recovery = output / "recovery"
        recovery.mkdir(exist_ok=True)
        archive = Path(tempfile.mkdtemp(prefix="before-rebuild-", dir=recovery))
        for child in inputs:
            child.rename(archive / child.name)
        print(f"Recoverable graph inputs: {archive.resolve()}")


def check_sources() -> None:
    graph = json.loads(Path("graphify-out/graph.json").read_text(encoding="utf-8"))
    root = Path.cwd().resolve()
    sources: set[str] = set()
    # ClassLens's code/config languages. Expanding this is a deliberate change.
    extensions = {".py", ".pyi", ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".sh", ".bash", ".sql", ".json"}

    def source_path(item: dict) -> str:
        source = item.get("source_file")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("missing source_file provenance")
        relative = Path(source)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"source must be repository-relative: {source}")
        resolved = (root / relative).resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise ValueError(f"source must be a file inside the repository: {source}")
        if any((root / parent).is_symlink() for parent in [relative, *relative.parents]):
            raise ValueError(f"source must not traverse a symlink: {source}")
        if relative.suffix.lower() not in extensions:
            raise ValueError(f"source is not an allowed code/config file: {source}")
        sources.add(relative.as_posix())
        return source

    nodes = {node["id"]: node for node in graph["nodes"]}
    if len(nodes) != len(graph["nodes"]):
        raise ValueError("duplicate node IDs")
    incident: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for edge in graph["links"]:
        source = source_path(edge)
        for endpoint in (edge["source"], edge["target"]):
            if endpoint not in nodes:
                raise ValueError(f"edge references an unknown node: {endpoint}")
            incident[endpoint].append(source)
    for node_id, node in nodes.items():
        if node.get("source_file") == "":
            # 0.9.77 emits source-empty callable/import reference stubs. They
            # are only admissible with an explicit stub shape and proven code
            # edges; missing/null source fields and isolated nodes fail closed.
            ast_stub = node.get("_origin") == "ast" and node.get("file_type") == "code"
            external_stub = node.get("external") is True and node.get("type") == "external" and node.get("file_type") == "concept"
            if not (ast_stub or external_stub) or not incident[node_id]:
                raise ValueError(f"source-empty node lacks code reference provenance: {node_id}")
        else:
            source_path(node)
    for hyperedge in graph.get("hyperedges", []):
        source_path(hyperedge)
    paths = sorted(sources)
    # Run the repository's actual ignore rules, including nested .gitignore,
    # independently of .graphifyignore so a Git negation cannot undo the latter.
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "-z", "--stdin"],
        input="\0".join(paths) + "\0", text=True, capture_output=True, check=False,
    )
    if ignored.returncode not in (0, 1):
        raise ValueError(f"could not evaluate Git exclusions: {ignored.stderr.strip()}")
    prohibited = subprocess.run(
        ["git", "--literal-pathspecs", "ls-files", "-z", "--cached", "--others", "--ignored", "--exclude-from=.graphifyignore", "--", *paths],
        text=True, capture_output=True, check=True,
    )
    excluded = (ignored.stdout + prohibited.stdout).strip("\0")
    if excluded:
        raise ValueError(f"excluded source path: {excluded.split(chr(0))[0]}")
    print(f"Graph source scope verified ({len(nodes)} nodes, {len(graph['links'])} links).")


def repair_report() -> None:
    report_path = Path("graphify-out/GRAPH_REPORT.md")
    report = report_path.read_text(encoding="utf-8")
    section = (
        "## Graph Freshness\n"
        "- Compare `built_at_commit` in `graphify-out/graph.json` with `git rev-parse HEAD`.\n"
        "- After code changes run `./scripts/graphify.sh update` for a clean, validated code-only rebuild and export.\n\n"
    )
    report = re.sub(r"^## Graph Freshness\n.*?(?=^## |\Z)", lambda _: section, report, flags=re.M | re.S)
    # Fail closed if this release changes its guidance format unexpectedly.
    if "./scripts/graphify.sh update" not in report or "graphify update" in report:
        raise ValueError("could not replace the upstream report refresh guidance")
    report_path.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    try:
        operation = sys.argv[1]
        if operation == "symlinks":
            for argument in sys.argv[2:]:
                reject_symlinks(Path(argument))
        elif operation == "prepare":
            prepare_graph()
        elif operation == "sources":
            check_sources()
        elif operation == "report":
            repair_report()
        else:
            raise ValueError(f"unknown validation operation: {operation}")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        label = "source scope" if sys.argv[1] == "sources" else "safety check"
        print(f"ClassLens Graphify: invalid {label}: {error}", file=sys.stderr)
        sys.exit(1)
