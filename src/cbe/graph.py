"""Standard ``cbe-graph/1`` analyzer: build and query source-linked code graphs.

This module owns the public graph contract consumed by the generation pipeline
and the ``cbe graph`` CLI.  It selects open-source backends, merges their
fragments into one node/edge graph keyed by repo-relative POSIX paths, and
exposes a pure query over an already-built graph.

Design rules:

* It never re-implements a language analyzer.  Joern provides call, control
  flow, native REACHING_DEF definition-use edges and import declarations;
  dependency-cruiser and Grimp resolve JS/TS and Python imports to
  files/modules.
* A missing or failed backend is an explicit capability/diagnostic, never a
  silent empty success: if nothing could run, ``analyze_graph`` raises.
* Every node/edge that anchors real source carries a repo-relative ``path`` and
  a resolution ``status`` from ``resolved|ambiguous|unresolved|external|
  unsupported``.  Unresolved targets keep the raw expression; ambiguous calls
  keep their candidate list.
* Provenance binds the analyzed source and the relevant build/resolution
  configuration.  If either changes during the build the graph is marked
  unstable so a downstream consumer can refuse it.
* Coordinates and provenance come from the analyzer.  Joern reports 1-based
  lines and 1-based UTF-16 columns; this module stores lines as given and
  leaves byte/char mapping to the chunk layer.  Raw analyzer ids are kept on
  ``analyzer_id``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone

from cbe.graph_backends._paths import canonical_repo_path

SCHEMA_GRAPH = "cbe-graph/1"

#: Build/module-resolution files that change what an analyzer sees.
GRAPH_CONFIG_NAMES = frozenset({
    "compile_commands.json", "CMakeLists.txt", "Makefile", "tsconfig.json",
    "package.json", "pyproject.toml", "go.mod", "go.sum", "pom.xml",
    "build.gradle", "settings.gradle", "Cargo.toml", "composer.json",
    "Gemfile", "Package.swift", "setup.py", "setup.cfg", "compile_flags.txt",
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.lock", "composer.lock", "Gemfile.lock", "Package.resolved",
    "gradle.properties", "gradle.lockfile", "CMakePresets.json", "CMakeUserPresets.json",
})
GRAPH_CONFIG_SUFFIXES = (".csproj", ".sln", ".gemspec", ".cmake", ".mk")

GRAPH_KINDS = frozenset({"import", "call", "cfg", "dataflow"})
_CAPABILITY_RANK = {"resolved": 6, "partial": 5, "empty": 4, "unsupported": 3,
                    "failed": 2, "unavailable": 1}


class GraphError(ValueError):
    """Raised when no graph could be produced or an input is invalid."""


def _excluded_dir_names() -> frozenset[str]:
    from cbe.source_context import DEFAULT_EXCLUDE_DIR_NAMES  # noqa: PLC0415

    return DEFAULT_EXCLUDE_DIR_NAMES


def graph_suffixes() -> dict[str, str]:
    """Return suffix -> language from the source-context grammar registry (one table for both layers)."""

    from cbe.source_context import _all_specs  # noqa: PLC0415

    return {suffix.lower(): spec.name for spec in _all_specs() for suffix in spec.suffixes}


def discover_sources(repo, languages: list[str] | None = None) -> list[dict]:
    """Return ``[{path, language, sha256}]`` for source files under ``repo``."""

    suffix_map = graph_suffixes()
    wanted = set(languages) if languages else None
    excluded = _excluded_dir_names()
    manifest: list[dict] = []
    repo = repo.resolve()
    for dirpath, dirnames, filenames in os.walk(repo, topdown=True, followlinks=False):
        dirnames.sort()
        dirnames[:] = [name for name in dirnames if name not in excluded]
        for filename in sorted(filenames):
            full = os.path.join(dirpath, filename)
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            language = suffix_map.get(os.path.splitext(filename)[1].lower())
            if language is None or (wanted is not None and language not in wanted):
                continue
            rel = os.path.relpath(full, repo).replace(os.sep, "/")
            with open(full, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
            manifest.append({"path": rel, "language": language, "sha256": digest})
    manifest.sort(key=lambda entry: entry["path"])
    return manifest


def discover_config(repo) -> list[dict]:
    """Return ``[{path, sha256}]`` for build/module-resolution files."""

    excluded = _excluded_dir_names()
    repo = os.path.abspath(str(repo))
    found: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(repo, topdown=True, followlinks=False):
        dirnames.sort()
        dirnames[:] = [name for name in dirnames if name not in excluded]
        for filename in sorted(filenames):
            if filename not in GRAPH_CONFIG_NAMES and not filename.endswith(GRAPH_CONFIG_SUFFIXES) \
                    and not (filename.startswith("tsconfig.") and filename.endswith(".json")):
                continue
            full = os.path.join(dirpath, filename)
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            rel = os.path.relpath(full, repo).replace(os.sep, "/")
            with open(full, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
            found.append({"path": rel, "sha256": digest})
    found.sort(key=lambda entry: entry["path"])
    return found


def validate_graph_provenance(repo, graph: dict) -> None:
    """Reject stale analysis inputs before a graph enters a reading task.

    External graphs without provenance retain their source-manifest contract;
    their configuration identity is unknown. Our builds additionally bind the
    complete set of registered source files and recognized configuration files.
    """
    from pathlib import Path

    provenance = graph.get("provenance")
    if provenance is None:
        return
    if not isinstance(provenance, dict):
        raise GraphError("graph provenance must be an object")
    for flag in ("source_stable", "config_stable"):
        if flag in provenance and provenance[flag] is not True:
            raise GraphError(f"graph build was unstable or malformed ({flag}); rebuild the graph")
    repo = Path(repo).resolve()

    def identities(entries, label: str) -> dict[str, str]:
        if not isinstance(entries, list):
            raise GraphError(f"graph {label} must be a manifest list")
        result = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise GraphError(f"malformed graph {label} entry")
            path, digest = entry.get("path"), entry.get("sha256")
            if not isinstance(path, str) or canonical_repo_path(path) != path \
                    or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise GraphError(f"malformed graph {label} identity")
            if path in result:
                raise GraphError(f"duplicate graph {label} path: {path}")
            result[path] = digest
        return result

    checks = []
    if "config_manifest" in provenance:
        checks.append(("configuration", provenance["config_manifest"], discover_config(repo)))
    if provenance.get("source_manifest_scope") == "registered_sources":
        checks.append(("source", graph.get("source_manifest"), discover_sources(repo)))
    for label, expected_entries, actual_entries in checks:
        expected, actual = identities(expected_entries, label), identities(actual_entries, label)
        if expected != actual:
            changed = sorted(path for path in expected.keys() | actual.keys()
                             if expected.get(path) != actual.get(path))
            raise GraphError(f"graph {label} drift: {', '.join(changed[:10])}; rebuild the graph")


def analyze_graph(
    repo,
    output,
    *,
    backend: str = "auto",
    languages: list[str] | None = None,
    joern_home=None,
    depcruise_bin=None,
    timeout: int = 300,
    max_methods: int = 200,
    max_reaching_defs: int = 50000,
    dataflow_path_methods: list[str] | None = None,
    max_paths_per_method: int = 5,
) -> dict:
    """Build a ``cbe-graph/1`` graph and write it to ``output``.

    ``backend`` is ``auto``, ``joern``, or ``imports``.  Runtime artifacts (CPG,
    export JSON, script) stay in a sibling run directory next to ``output``;
    nothing is written into the source tree.
    """

    from pathlib import Path

    from cbe import graph_backends as backends  # noqa: PLC0415

    for name, value in (("timeout", timeout), ("max_methods", max_methods),
                        ("max_reaching_defs", max_reaching_defs),
                        ("max_paths_per_method", max_paths_per_method)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise GraphError(f"{name} must be a positive integer")
    repo = Path(repo).expanduser().resolve()
    if not repo.is_dir():
        raise GraphError(f"repository root is not a directory: {repo}")
    output = Path(output).expanduser()
    # Frontends can read sibling languages (for example C/C++ headers or
    # JS/TS imports). Bind every registered source even for a language filter.
    manifest = discover_sources(repo)
    config_manifest = discover_config(repo)
    detected = sorted({entry["language"] for entry in manifest})
    requested = sorted(set(languages)) if languages else detected
    run_dir = output.parent / (output.stem + ".run")
    run_dir.mkdir(parents=True, exist_ok=True)

    fragments: list[dict] = []
    diagnostics: list[dict] = []
    components: list[dict] = []
    extra_capabilities: list[dict] = []
    ran = False

    use_joern = backend in ("auto", "joern")
    use_imports = backend in ("auto", "imports")

    if use_joern:
        joern = backends.find_joern(joern_home)
        if joern is None:
            if backend == "joern":
                raise GraphError("joern backend requested but the Joern CLI was not found")
            diagnostics.append({"path": None, "code": "backend_unavailable",
                                "message": "Joern CLI not found; call/cfg/dataflow skipped"})
            extra_capabilities.extend(_unavailable("joern", requested, ("call", "cfg", "dataflow")))
        else:
            try:
                fragment = backends.build_with_joern(
                    repo, run_dir / "joern", requested, joern, timeout,
                    max_reaching_defs=max_reaching_defs,
                    dataflow_path_methods=dataflow_path_methods,
                    max_paths_per_method=max_paths_per_method)
            except backends.JoernError as exc:
                diagnostics.append({"path": None, "code": "backend_error", "message": str(exc)})
                extra_capabilities.extend(_unavailable("joern", requested, ("call", "cfg", "dataflow")))
            else:
                fragments.append(fragment)
                components.append(fragment["backend"])
                diagnostics.extend(fragment["diagnostics"])
                ran = ran or bool(fragment["raw"])

    if use_imports:
        depcruise = backends.find_depcruise(depcruise_bin)
        import_languages = [lang for lang in requested if lang in backends.DEPCRUISE_LANGUAGES]
        if depcruise is None:
            diagnostics.append({"path": None, "code": "backend_unavailable",
                                "message": "dependency-cruiser not found; JS/TS import graph skipped"})
            extra_capabilities.extend(_unavailable("dependency-cruiser", import_languages, ("import",)))
        elif import_languages:
            fragment = backends.build_with_depcruise(repo, run_dir / "depcruise", depcruise,
                                                     timeout, import_languages)
            if fragment["nodes"] or not fragment["diagnostics"]:
                components.append({"name": "dependency-cruiser",
                                   "version": _depcruise_version(depcruise, timeout)})
                ran = True
            fragments.append(fragment)
            diagnostics.extend(fragment["diagnostics"])
        if "python" in requested:
            fragment = backends.build_with_grimp(repo, requested)
            if fragment["nodes"]:
                components.append({"name": "grimp", "version": _grimp_version()})
                ran = True
            fragments.append(fragment)
            diagnostics.extend(fragment["diagnostics"])

    if not fragments:
        raise GraphError("no graph backend was available for the requested languages")

    nodes, edges = _merge(fragments)
    edges = _prefer_resolved_imports(edges)
    capabilities = _merge_capabilities(fragments, requested, extra_capabilities)

    if not ran:
        diagnostics.append({"path": None, "code": "no_backend_completed",
                            "message": "no backend completed; graph is empty and not authoritative"})

    source_stable = discover_sources(repo) == manifest
    config_stable = discover_config(repo) == config_manifest
    if not source_stable:
        diagnostics.append({"path": None, "code": "source_changed_during_build",
                            "message": "source bytes changed while the analyzers ran; "
                                       "the graph no longer matches the current source"})
    if not config_stable:
        diagnostics.append({"path": None, "code": "config_changed_during_build",
                            "message": "build/module-resolution configuration changed while the "
                                       "analyzers ran; the graph's coverage conditions are stale"})
    provenance = {
        "source_stable": source_stable,
        "config_stable": config_stable,
        "config_manifest": config_manifest,
        "source_manifest_scope": "registered_sources",
        "analyzed_languages": requested,
        "backend_components": components,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": _fingerprint(manifest, config_manifest, components),
    }

    graph = {
        "schema": SCHEMA_GRAPH,
        "source_manifest": manifest,
        "backend": _backend_record(components),
        "provenance": provenance,
        "nodes": nodes,
        "edges": edges,
        "capabilities": capabilities,
        "diagnostics": diagnostics,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return graph


def query_graph(
    graph: dict,
    *,
    paths: list[str] | None = None,
    kind: str | None = None,
    direction: str = "both",
    node_id: str | None = None,
) -> dict:
    """Select a local slice of an already-built graph.  Pure; reads no source.

    Paths are canonical repo-relative POSIX paths.  If none of the requested
    paths exist the result is an explicitly partial, empty slice (with the
    unmatched paths listed), never the whole graph.
    """

    if not isinstance(graph, dict) or graph.get("schema") != SCHEMA_GRAPH:
        raise GraphError("expected a cbe-graph/1 payload")
    if kind is not None and kind not in GRAPH_KINDS:
        raise GraphError(f"unknown graph kind {kind!r}; expected one of {sorted(GRAPH_KINDS)}")
    if direction not in ("both", "in", "out"):
        raise GraphError(f"unknown direction {direction!r}")

    nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]
    by_id = {node.get("id"): node for node in nodes}

    canonical_paths: list[str] = []
    invalid_paths: list[str] = []
    for raw in paths or []:
        canonical = canonical_repo_path(raw)
        if canonical is None:
            invalid_paths.append(str(raw))
        else:
            canonical_paths.append(canonical)

    selected: set[str] = set()
    unmatched: list[str] = []
    if node_id is not None:
        if node_id not in by_id:
            raise GraphError(f"node {node_id!r} is not in this graph")
        selected.add(node_id)
    if canonical_paths:
        present = {node.get("path") for node in nodes}
        selected |= {node["id"] for node in nodes if node.get("path") in set(canonical_paths)}
        unmatched = sorted({path for path in canonical_paths if path not in present})

    if kind is not None:
        edges = [edge for edge in edges if edge.get("kind") == kind]

    def incident(edge: dict) -> bool:
        source, target = edge.get("source"), edge.get("target")
        if direction in ("both", "out") and source in selected:
            return True
        if direction in ("both", "in") and target in selected:
            return True
        return False

    filtered = bool(paths or kind or node_id or invalid_paths)
    selection_requested = bool(paths or node_id or invalid_paths)
    if selected:
        kept_edges = [edge for edge in edges if incident(edge)]
        kept_ids = set(selected) if kind is None else ({node_id} if node_id else set())
        for edge in kept_edges:
            if edge.get("source") is not None:
                kept_ids.add(edge["source"])
            if edge.get("target") is not None:
                kept_ids.add(edge["target"])
        kept_nodes = [node for node in nodes if node.get("id") in kept_ids]
    elif selection_requested:
        # A node selection was requested but matched nothing: respect the empty scope.
        kept_edges = []
        kept_nodes = []
    else:
        kept_edges = edges
        endpoint_ids = {edge.get(endpoint) for edge in edges for endpoint in ("source", "target")}
        kept_nodes = nodes if kind is None else [node for node in nodes if node.get("id") in endpoint_ids]

    diagnostics = list(graph.get("diagnostics", []))
    if unmatched:
        diagnostics.append({"path": None, "code": "query_paths_not_found",
                            "message": "no graph node matches the requested path(s): "
                                       + ", ".join(unmatched[:10])})
    if invalid_paths:
        diagnostics.append({"path": None, "code": "query_paths_invalid",
                            "message": "query paths must be repo-relative POSIX paths: "
                                       + ", ".join(invalid_paths[:10])})

    return {
        "schema": SCHEMA_GRAPH,
        "backend": graph.get("backend"),
        "provenance": graph.get("provenance"),
        "source_manifest": list(graph.get("source_manifest", [])),
        "nodes": kept_nodes,
        "edges": kept_edges,
        "capabilities": graph.get("capabilities", []),
        "diagnostics": diagnostics,
        "scope": {
            "paths": canonical_paths or None,
            "kind": kind,
            "direction": direction,
            "node_id": node_id,
            "partial": filtered,
            "edge_filter": ("incident_to_selection" if selected else "empty_selection")
                           if selection_requested else ("kind_only" if kind else "none"),
            "unmatched_paths": unmatched or None,
            "invalid_paths": invalid_paths or None,
        },
    }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _merge(fragments: list[dict]) -> tuple[list[dict], list[dict]]:
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_nodes: set[str] = set()
    seen_edges: set[tuple] = set()
    for fragment in fragments:
        for node in fragment.get("nodes", []):
            if node["id"] in seen_nodes:
                continue
            seen_nodes.add(node["id"])
            nodes.append(node)
        for edge in fragment.get("edges", []):
            key = (edge.get("id"), edge.get("source"), edge.get("target"), edge.get("kind"))
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append(edge)
    return nodes, edges


_IMPORT_INCLUDE = re.compile(r'#\s*include\s*(.+?)\s*$')
_IMPORT_JS = re.compile(r"""(?:require|from)\s*\(?\s*(.+?)\s*[)\s]*$""")
_IMPORT_FROM = re.compile(r"^from\s+([.\w]+)\s+import")
_IMPORT_PY = re.compile(r"^import\s+([\w.]+)")
_IMPORT_GO = re.compile(r"import\s+(?:\w+\s+)?(.+)$")


def _import_token(expression: object) -> str | None:
    if not expression:
        return None
    text = str(expression).strip()
    if not text:
        return None
    for pattern in (_IMPORT_INCLUDE, _IMPORT_JS, _IMPORT_FROM, _IMPORT_PY, _IMPORT_GO):
        match = pattern.search(text)
        if match:
            return _clean_import_token(match.group(1))
    # A bare module specifier (dependency-cruiser / Grimp `expression`).
    if " " not in text and "#" not in text and len(text) < 300:
        return _clean_import_token(text)
    return None


def _clean_import_token(token: str) -> str | None:
    cleaned = token.strip().strip("\"'<>").strip().lower().lstrip("./")
    return cleaned or None


def _prefer_resolved_imports(edges: list[dict]) -> list[dict]:
    """Drop an unresolved import only when a resolved import matches it.

    Matching requires the same file *and* the same declared target token, so a
    resolved ``from good import ok`` can never erase an unrelated
    ``import missing_dependency``.  Unmatched unresolved imports are retained
    with their backend evidence.
    """

    resolved = [(edge.get("path"), _import_token(edge.get("expression")))
                for edge in edges
                if edge.get("kind") == "import" and edge.get("status") == "resolved"]
    resolved_set = {(path, token) for path, token in resolved if token}
    kept: list[dict] = []
    for edge in edges:
        if edge.get("kind") == "import" and edge.get("status") == "unresolved":
            token = _import_token(edge.get("expression"))
            if token and (edge.get("path"), token) in resolved_set:
                continue
        kept.append(edge)
    return kept


def _unavailable(backend: str, languages: list[str], kinds: tuple[str, ...]) -> list[dict]:
    return [{"language": language, "graph": kind, "backend": backend,
             "status": "unavailable", "limitations": f"{backend} was not found"}
            for language in languages for kind in kinds]


def _merge_capabilities(fragments: list[dict], requested: list[str],
                        extra: list[dict] | None = None) -> list[dict]:
    merged: dict[tuple, dict] = {}
    for capability in [item for fragment in fragments for item in fragment.get("capabilities", [])] + list(extra or []):
        key = (capability.get("language"), capability.get("graph"))
        current = merged.get(key)
        if current is None or _CAPABILITY_RANK.get(capability.get("status"), 0) > _CAPABILITY_RANK.get(current.get("status"), 0):
            merged[key] = capability
    for language in requested:
        for kind in ("import", "call", "cfg", "dataflow"):
            merged.setdefault((language, kind), {
                "language": language, "graph": kind, "status": "unsupported",
                "backend": None, "limitations": "no backend reported this language/kind",
            })
    return sorted(merged.values(), key=lambda item: (item.get("language") or "", item.get("graph") or ""))


def _backend_record(components: list[dict]) -> dict:
    if not components:
        return {"name": "none", "version": None, "components": []}
    if len(components) == 1:
        return {"name": components[0]["name"], "version": components[0].get("version"),
                "components": components}
    names = "+".join(component["name"] for component in components)
    return {"name": names, "version": None, "components": components}


def _fingerprint(manifest: list[dict], config_manifest: list[dict], components: list[dict]) -> str:
    payload = json.dumps({"source": manifest, "config": config_manifest, "components": components},
                         sort_keys=True, separators=(",", ":"))
    return "gp_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _depcruise_version(binary, timeout: int) -> str:
    import subprocess  # noqa: PLC0415

    try:
        completed = subprocess.run([str(binary), "--version"], check=False, capture_output=True,
                                   text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    text = (completed.stdout or completed.stderr).strip()
    return text.splitlines()[0] if text else "unknown"


def _grimp_version() -> str:
    try:
        from importlib.metadata import version  # noqa: PLC0415

        return version("grimp")
    except Exception:
        return "unknown"
