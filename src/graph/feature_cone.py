"""Feature Cone extraction: Louvain communities (V3) and surface cones (V4).

V3 algorithm: Louvain partitioning on weighted dependency graph, followed by
infrastructure identification, test-file separation, and semantic renaming.

V4 additions (r004, L2 structural layer): the public surface of a package is
extracted deterministically from its AST, each surface entry is resolved to the
file that *defines* it, and a forward reachability closure is computed per
defining file.  V4 lives beside V3 rather than replacing it -- callers choose.

Why V3 alone produces one giant bucket: Louvain maximizes modularity, i.e. the
ratio of intra-community to inter-community edge density.  A utility shared by
every feature has an edge to every feature, so it is "close" to all of them and
the whole graph collapses into one community (measured: flask 82.7%, httpx
88.7%).  Connectivity is not function.  V4 answers this by asking *which*
entries reach a file rather than merely *whether* it is shared.
"""
from __future__ import annotations

import ast
import logging
import posixpath
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import networkx as nx

from src.graph.semantic_hints import classify_file, is_reexport_facade, directory_affinity_score
from src.parser.codebase import CodebaseSnapshot

logger = logging.getLogger(__name__)

_EXTRA_INFRA_STEMS = frozenset({
    "abc", "log", "logging", "compat", "_compat",
    "globals", "types", "base", "registry",
})
"""Additional file stems that indicate infrastructure when combined
with above-median in-degree."""


@dataclass(frozen=True)
class FeatureCone:
    """A cohesive feature group: exclusive files + shared infrastructure deps."""

    cone_id: str
    entry_point: str
    exclusive_files: tuple[str, ...]
    shared_deps: tuple[str, ...]
    layer: int = 0
    token_count: int = 0


# ---------------------------------------------------------------------------
# Core pipeline helpers
# ---------------------------------------------------------------------------


def _louvain_communities(dag: nx.DiGraph) -> list[set[str]]:
    """Louvain community detection on undirected graph (preserving weights)."""
    from networkx.algorithms.community import louvain_communities as _louvain

    if dag.number_of_nodes() == 0:
        return []

    udag = dag.to_undirected()
    communities = _louvain(udag, weight="weight", resolution=1.0, seed=42)
    return [set(c) for c in communities]


def _merge_small_communities(
    communities: list[set[str]],
    dag: nx.DiGraph,
    min_size: int = 3,
) -> list[set[str]]:
    """Merge communities smaller than *min_size* into their best neighbour."""
    if not communities:
        return communities

    node_to_comm: dict[str, int] = {}
    for idx, comm in enumerate(communities):
        for node in comm:
            node_to_comm[node] = idx

    small_indices: list[int] = []
    large_indices: list[int] = []
    for idx, comm in enumerate(communities):
        (small_indices if len(comm) < min_size else large_indices).append(idx)

    if not large_indices:
        return communities

    merged = {i: set(communities[i]) for i in large_indices}
    for si in small_indices:
        small_files = communities[si]
        edge_counts: dict[int, int] = defaultdict(int)
        for f in small_files:
            for neighbor in list(dag.predecessors(f)) + list(dag.successors(f)):
                ni = node_to_comm.get(neighbor)
                if ni is not None and ni in merged:
                    edge_counts[ni] += 1

        if edge_counts:
            max_edges = max(edge_counts.values())
            best_target = None
            best_score = -1.0
            for target_idx, edges in edge_counts.items():
                # Calculate average directory affinity between small and target communities
                target_files = merged[target_idx]
                if target_files and small_files:
                    total_affinity = sum(
                        directory_affinity_score(sf, tf)
                        for sf in small_files
                        for tf in list(target_files)[:20]  # Cap to avoid O(n^2) explosion
                    )
                    avg_affinity = total_affinity / (len(small_files) * min(len(target_files), 20))
                else:
                    avg_affinity = 0.0
                score = edges + avg_affinity * max_edges
                if score > best_score:
                    best_score = score
                    best_target = target_idx
        else:
            best_target = large_indices[0]
            small_dirs = {posixpath.dirname(f) for f in small_files}
            for li in large_indices:
                large_dirs = {posixpath.dirname(f) for f in merged[li]}
                if small_dirs & large_dirs:
                    best_target = li
                    break

        merged[best_target].update(small_files)
        for f in small_files:
            node_to_comm[f] = best_target

    return list(merged.values())


def _identify_infrastructure(
    dag: nx.DiGraph,
    communities: list[set[str]],
    root_path: str | None = None,
) -> set[str]:
    """Identify infra nodes via semantic classification + in-degree analysis.

    Criteria (any one sufficient):
    1. classify_file returns config/utils/exceptions AND above-median in-degree
    2. File stem in _EXTRA_INFRA_STEMS AND above-median in-degree
    3. __init__.py that is a re-export facade (via is_reexport_facade)
    """
    infra_categories = {"config", "utils", "exceptions"}

    in_degrees = dict(dag.in_degree())
    if not in_degrees:
        return set()

    median_indeg = sorted(in_degrees.values())[len(in_degrees) // 2]
    high_indeg_threshold = max(2, median_indeg)

    # Build file -> community index
    f2comm: dict[str, int] = {}
    for i, comm in enumerate(communities):
        for f in comm:
            f2comm[f] = i

    n_communities = len(communities)
    cross_cut_threshold = max(2, int(n_communities * 0.4))

    infra: set[str] = set()
    for node in dag.nodes():
        classification = classify_file(node)
        has_high_indegree = in_degrees.get(node, 0) >= high_indeg_threshold

        # Criterion 1: semantic infra type + above-median in-degree
        if classification in infra_categories and has_high_indegree:
            infra.add(node)
            continue

        # Criterion 2: extra infra stems + above-median in-degree
        stem = posixpath.splitext(posixpath.basename(node))[0].lower()
        if stem in _EXTRA_INFRA_STEMS and has_high_indegree:
            infra.add(node)
            continue

        # Criterion 3: __init__.py re-export facade (no in-degree requirement)
        if root_path and node.endswith("__init__.py"):
            try:
                if is_reexport_facade(node, root_path):
                    infra.add(node)
                    continue
            except Exception:  # noqa: BLE001
                pass

        # Criterion 4: imported by files in >= 40% of communities
        importer_communities: set[int] = set()
        for pred in dag.predecessors(node):
            ci = f2comm.get(pred)
            if ci is not None:
                importer_communities.add(ci)

        if len(importer_communities) >= cross_cut_threshold:
            infra.add(node)

    return infra


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def extract_feature_cones(
    dag: nx.DiGraph,
    snapshot: CodebaseSnapshot,
    shared_threshold: int | None = None,
) -> tuple[dict[str, FeatureCone], frozenset[str]]:
    """Extract feature cones from the dependency DAG using Louvain communities.

    Args:
        dag: Weighted dependency DAG.
        snapshot: Codebase snapshot for metadata.
        shared_threshold: Legacy parameter (ignored). Kept for API compat.

    Returns:
        (cone_dict, infrastructure_frozenset)

    Raises:
        ValueError: If the DAG has no nodes.
    """
    if dag.number_of_nodes() == 0:
        raise ValueError("Cannot extract feature cones from an empty DAG")

    communities = _louvain_communities(dag)
    communities = _merge_small_communities(communities, dag, min_size=3)
    infrastructure_nodes = _identify_infrastructure(
        dag, communities, root_path=snapshot.root_path,
    )

    # Build FeatureCone objects from communities
    cones: dict[str, FeatureCone] = {}

    for comm in communities:
        # Remove infra files from this community's exclusive files
        exclusive = sorted(f for f in comm if f not in infrastructure_nodes)
        if not exclusive:
            continue

        # Entry point: the file with highest out-degree in this community
        entry = max(exclusive, key=lambda f: dag.out_degree(f))
        shared_refs = sorted(f for f in comm if f in infrastructure_nodes)

        cone_id = entry  # Will be renamed later
        cones[cone_id] = FeatureCone(
            cone_id=cone_id,
            entry_point=entry,
            exclusive_files=tuple(exclusive),
            shared_deps=tuple(shared_refs),
        )

    # Post-processing: separate tests, then rename
    cone_list = _separate_testing_files(list(cones.values()))
    cone_list = _rename_cones(cone_list)
    return {c.cone_id: c for c in cone_list}, frozenset(infrastructure_nodes)


# ---------------------------------------------------------------------------
# Post-processing helpers
# ---------------------------------------------------------------------------


def _parent_dir(filepath: str) -> str:
    """Parent directory of *filepath* (posixpath; ``""`` for root-level)."""
    return posixpath.dirname(filepath)


def _separate_testing_files(cones: list[FeatureCone]) -> list[FeatureCone]:
    """Split testing files out of mixed cones into their own sub-cones."""
    result: list[FeatureCone] = []
    for cone in cones:
        if len(cone.exclusive_files) < 2:
            result.append(cone)
            continue

        testing = [f for f in cone.exclusive_files if classify_file(f) == "testing"]
        runtime = [f for f in cone.exclusive_files if classify_file(f) != "testing"]

        if not testing or not runtime:
            result.append(cone)
            continue

        result.append(FeatureCone(
            cone.cone_id, cone.entry_point, tuple(sorted(runtime)),
            tuple(cone.shared_deps), cone.layer, 0,
        ))
        result.append(FeatureCone(
            f"{cone.cone_id}::testing", cone.entry_point, tuple(sorted(testing)),
            tuple(cone.shared_deps), cone.layer, 0,
        ))
        logger.info(
            "[REBALANCE] separated %d testing files from cone '%s'",
            len(testing), cone.cone_id,
        )
    return result


def _generate_cone_name(files: Sequence[str]) -> str:
    """Derive a human-readable cone name from its files' semantic categories."""
    if not files:
        return "empty"

    categories = [classify_file(f) for f in files]
    known = {k: v for k, v in Counter(categories).items() if k != "unknown"}
    if known:
        dominant = max(known, key=known.__getitem__)  # type: ignore[arg-type]
        if known[dominant] / len(files) >= 0.4:
            return dominant

    # Fallback: use common directory prefix
    dirs = [_parent_dir(f) for f in files]
    unique_dirs = set(dirs)
    if len(unique_dirs) == 1:
        d = unique_dirs.pop()
        if d:
            return posixpath.basename(d)

    # Fallback: use deepest common directory across all files
    if unique_dirs:
        all_dirs = sorted(unique_dirs)
        if all_dirs:
            common = posixpath.commonpath(all_dirs) if len(all_dirs) > 1 else all_dirs[0]
            if common:
                return posixpath.basename(common)

    # Fallback: use "core" for root-level files, or first file stem
    if all(not _parent_dir(f) for f in files):
        return "core-runtime"

    # Use first file's stem, but replace __init__ with parent dir name
    stem = posixpath.splitext(posixpath.basename(files[0]))[0]
    if stem == "__init__":
        parent = _parent_dir(files[0])
        if parent:
            return posixpath.basename(parent)
    return stem


def _semantic_suffix(files: Sequence[str]) -> str:
    """Short semantic suffix from most-common file stem (excluding __init__)."""
    stems = [
        posixpath.splitext(posixpath.basename(f))[0]
        for f in files
        if posixpath.splitext(posixpath.basename(f))[0] != "__init__"
    ]
    if stems:
        counts = Counter(stems)
        return counts.most_common(1)[0][0]
    # All files are __init__.py -- use deepest dir
    dirs = [_parent_dir(f) for f in files if _parent_dir(f)]
    if dirs:
        return posixpath.basename(dirs[0])
    return "misc"


def _rename_cones(cones: list[FeatureCone]) -> list[FeatureCone]:
    """Rename cones with semantic names; disambiguate duplicates via suffixes."""
    # Generate candidate names
    candidates: list[tuple[FeatureCone, str]] = []
    for cone in cones:
        base_name = _generate_cone_name(cone.exclusive_files)
        candidates.append((cone, base_name))

    # Count duplicates
    name_counts: dict[str, int] = defaultdict(int)
    for _, name in candidates:
        name_counts[name] += 1

    # Track used suffixes per name to avoid clashes
    name_used_suffixes: dict[str, set[str]] = defaultdict(set)
    name_numeric: dict[str, int] = defaultdict(int)
    result: list[FeatureCone] = []

    for cone, name in candidates:
        if name_counts[name] > 1:
            suffix = _semantic_suffix(cone.exclusive_files)
            # If this suffix was already used for this name, add numeric
            if suffix in name_used_suffixes[name]:
                name_numeric[name] += 1
                final_name = f"{name}-{suffix}-{name_numeric[name]}"
            else:
                name_used_suffixes[name].add(suffix)
                final_name = f"{name}-{suffix}"
        else:
            final_name = name

        result.append(
            FeatureCone(
                cone_id=final_name,
                entry_point=cone.entry_point,
                exclusive_files=tuple(cone.exclusive_files),
                shared_deps=tuple(cone.shared_deps),
                layer=cone.layer,
                token_count=cone.token_count,
            )
        )

    return result


# ---------------------------------------------------------------------------
# V4: public-surface cones (r004 L2 structural layer)
# ---------------------------------------------------------------------------


_MAX_REEXPORT_CHASE = 8
"""Depth cap when following a re-export chain to the defining module."""

_SURFACE_ORIGINS = (
    "reexport",
    "dunder_all",
    "module_binding",
    "cli_entry",
    "decorator_registry",
)


class SurfaceExtractionError(ValueError):
    """Raised when public-surface extraction is asked for an unusable input."""


@dataclass(frozen=True)
class PublicSurfaceEntry:
    """One externally observable capability of a package.

    ``defining_path`` is what feeds reachability: a name re-exported by
    ``__init__.py`` is *declared* there but *implemented* elsewhere, and the
    cone has to start at the implementation.  Starting at the declaring file
    instead makes every entry reach the whole repository, because a package
    facade imports everything it re-exports.
    """

    name: str
    origin: str
    declared_in: str
    defining_path: str
    defining_name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise SurfaceExtractionError("surface entry requires a name")
        if self.origin not in _SURFACE_ORIGINS:
            raise SurfaceExtractionError(
                f"unknown surface origin {self.origin!r}; "
                f"expected one of {_SURFACE_ORIGINS}"
            )
        if not self.defining_path:
            raise SurfaceExtractionError(
                f"surface entry {self.name!r} requires a defining path"
            )


@dataclass(frozen=True)
class _Binding:
    """A module-level name bound by an import statement."""

    target_path: str | None
    target_name: str | None
    is_module: bool


@dataclass(frozen=True)
class _ModuleFacts:
    """Deterministic AST facts about a single module."""

    path: str
    bindings: Mapping[str, _Binding]
    definitions: frozenset[str]
    assignments: frozenset[str]
    dunder_all: tuple[str, ...] | None
    decorated_registrations: tuple[tuple[str, str], ...]
    star_imports: tuple[str, ...] = ()
    runtime_imports: frozenset[str] = frozenset()
    parse_error: str | None = None


def _module_candidates(parts: Sequence[str]) -> tuple[str, str]:
    """Return the ``(module.py, package/__init__.py)`` candidates for *parts*."""
    joined = "/".join(parts)
    return f"{joined}.py", f"{joined}/__init__.py"


def _resolve_module_path(
    current_path: str,
    module: str | None,
    level: int,
    universe: frozenset[str],
    package_name: str,
) -> tuple[str | None, bool]:
    """Resolve an import target to a repository-relative path.

    Returns ``(path, is_module)``.  ``path`` is ``None`` when the target lives
    outside the analysed universe (stdlib, third party, or an unresolvable
    relative escape) -- an explicit miss, never a silent substitution.
    """
    current_parts = current_path.split("/")
    package_parts = current_parts[:-1]

    if level > 0:
        ascend = level - 1
        if ascend > len(package_parts):
            return None, False
        base = package_parts[: len(package_parts) - ascend] if ascend else package_parts
    else:
        if not module:
            return None, False
        head = module.split(".")[0]
        if head != package_name:
            return None, False
        base = []
        module = ".".join(module.split(".")[1:])

    target_parts = list(base) + ([p for p in module.split(".") if p] if module else [])
    if not target_parts:
        # ``from . import x`` at package root: the package itself.
        init = "/".join(list(base) + ["__init__.py"]) if base else "__init__.py"
        return (init, True) if init in universe else (None, False)

    as_module, as_package = _module_candidates(target_parts)
    if as_module in universe:
        return as_module, False
    if as_package in universe:
        return as_package, True
    return None, False


def _collect_module_facts(
    path: str,
    root_path: str,
    universe: frozenset[str],
    package_name: str,
) -> _ModuleFacts:
    """Parse one module and record the facts the surface extractor needs."""
    full = Path(root_path) / path
    try:
        tree = ast.parse(full.read_text(encoding="utf-8"), filename=path)
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        # A file we cannot read is a visible gap, not an empty module.
        return _ModuleFacts(
            path=path,
            bindings={},
            definitions=frozenset(),
            assignments=frozenset(),
            dunder_all=None,
            decorated_registrations=(),
            parse_error=f"{type(exc).__name__}: {exc}",
        )

    bindings: dict[str, _Binding] = {}
    definitions: set[str] = set()
    assignments: set[str] = set()
    dunder_all: tuple[str, ...] | None = None
    registrations: list[tuple[str, str]] = []
    star_imports: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            target_path, is_module = _resolve_module_path(
                path, node.module, node.level, universe, package_name
            )
            for alias in node.names:
                if alias.name == "*":
                    if target_path is not None:
                        star_imports.append(target_path)
                    continue
                local = alias.asname or alias.name
                if is_module and target_path is not None:
                    sub_path, sub_is_module = _resolve_module_path(
                        path,
                        f"{node.module}.{alias.name}" if node.module else alias.name,
                        node.level,
                        universe,
                        package_name,
                    )
                    if sub_path is not None:
                        bindings[local] = _Binding(sub_path, None, sub_is_module)
                        continue
                bindings[local] = _Binding(target_path, alias.name, False)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                target_path, is_module = _resolve_module_path(
                    path, alias.name, 0, universe, package_name
                )
                bindings[local] = _Binding(target_path, None, is_module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.add(node.name)
            for decorator in node.decorator_list:
                name = _decorator_root_name(decorator)
                if name is not None:
                    registrations.append((node.name, name))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.add(target.id)
                    if target.id == "__all__":
                        dunder_all = _literal_string_tuple(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assignments.add(node.target.id)
            if node.target.id == "__all__" and node.value is not None:
                dunder_all = _literal_string_tuple(node.value)

    return _ModuleFacts(
        path=path,
        bindings=bindings,
        definitions=frozenset(definitions),
        assignments=frozenset(assignments),
        dunder_all=dunder_all,
        decorated_registrations=tuple(registrations),
        star_imports=tuple(star_imports),
        runtime_imports=_runtime_import_targets(
            tree, path, universe, package_name
        ),
    )


def _is_type_checking_guard(test: ast.expr) -> bool:
    """Whether an ``if`` test is a ``TYPE_CHECKING`` guard.

    Accepts the bare name, any dotted form (``t.TYPE_CHECKING``,
    ``typing.TYPE_CHECKING``), and the literal ``False`` that some packages use
    for the same purpose.
    """
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    if isinstance(test, ast.Constant) and test.value is False:
        return True
    return False


def _is_enclosing_package_facade(importer: str, target: str) -> bool:
    """Whether *target* is the ``__init__.py`` of a package enclosing *importer*.

    ``from . import typing`` inside ``app.py`` executes the package facade, so
    it looks like a dependency, but the design dependency is on the named
    member (``typing.py``), which is recorded separately.  Admitting the facade
    edge points every module at the facade while the facade points back at
    every module, so the whole package becomes one strongly connected
    component: measured on flask, 12 of 24 files, which pins the largest
    cluster at 83% no matter how the seeds are chosen.
    """
    if not target.endswith("__init__.py"):
        return False
    package_prefix = target[: -len("__init__.py")]
    return importer != target and importer.startswith(package_prefix)


def _runtime_import_targets(
    tree: ast.Module,
    path: str,
    universe: frozenset[str],
    package_name: str,
) -> frozenset[str]:
    """In-repo files this module imports *at runtime*.

    Imports guarded by ``if TYPE_CHECKING:`` are annotation-only and carry no
    runtime dependency, so they are excluded.  Counting them inverts real
    dependency direction -- flask's ``globals.py`` "imports" ``app.py`` solely
    to annotate types, and admitting that edge welds 19 of 24 files into one
    strongly connected component, which makes every forward closure identical
    and destroys the partition.  Function-local (deferred) imports are kept:
    those do execute.
    """
    targets: set[str] = set()

    def record(target: str | None) -> None:
        if target is None or target == path:
            return
        if _is_enclosing_package_facade(path, target):
            return
        targets.add(target)

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If) and _is_type_checking_guard(child.test):
                for orelse in child.orelse:
                    visit(orelse)
                continue
            if isinstance(child, ast.ImportFrom):
                resolved, _ = _resolve_module_path(
                    path, child.module, child.level, universe, package_name
                )
                record(resolved)
                for alias in child.names:
                    if alias.name == "*":
                        continue
                    sub, _ = _resolve_module_path(
                        path,
                        f"{child.module}.{alias.name}" if child.module else alias.name,
                        child.level,
                        universe,
                        package_name,
                    )
                    record(sub)
            elif isinstance(child, ast.Import):
                for alias in child.names:
                    resolved, _ = _resolve_module_path(
                        path, alias.name, 0, universe, package_name
                    )
                    record(resolved)
            visit(child)

    visit(tree)
    return frozenset(targets)


def _expand_star_imports(
    facts: Mapping[str, _ModuleFacts],
) -> dict[str, _ModuleFacts]:
    """Bind the names a ``from .x import *`` actually brings into scope.

    Without this, a package whose facade is built entirely from star imports
    (httpx) resolves every public name back to ``__init__.py`` itself, so all
    seeds collapse onto the facade and the partition degenerates.
    """
    expanded = dict(facts)
    for _ in range(_MAX_REEXPORT_CHASE):
        changed = False
        for path, module_facts in list(expanded.items()):
            if not module_facts.star_imports:
                continue
            bindings = dict(module_facts.bindings)
            for target_path in module_facts.star_imports:
                target = expanded.get(target_path)
                if target is None:
                    continue
                for name in sorted(_exported_names(target)):
                    if name in bindings:
                        continue
                    bindings[name] = _Binding(target_path, name, False)
                    changed = True
            if len(bindings) != len(module_facts.bindings):
                expanded[path] = replace(module_facts, bindings=bindings)
        if not changed:
            break
    return expanded


def _literal_string_tuple(value: ast.expr) -> tuple[str, ...] | None:
    """Return the string members of a literal list/tuple, else ``None``.

    A computed ``__all__`` returns ``None`` rather than a partial guess: an
    under-reported surface silently shrinks every cone downstream.
    """
    if not isinstance(value, (ast.List, ast.Tuple)):
        return None
    names: list[str] = []
    for item in value.elts:
        if not (isinstance(item, ast.Constant) and isinstance(item.value, str)):
            return None
        names.append(item.value)
    return tuple(names)


def _decorator_root_name(node: ast.expr) -> str | None:
    """Return the leftmost identifier of a decorator expression."""
    current: ast.expr = node
    while True:
        if isinstance(current, ast.Call):
            current = current.func
        elif isinstance(current, ast.Attribute):
            current = current.value
        elif isinstance(current, ast.Name):
            return current.id
        else:
            return None


def _chase_definition(
    path: str,
    name: str,
    facts: Mapping[str, _ModuleFacts],
) -> tuple[str, str]:
    """Follow a re-export chain to the module that actually defines *name*."""
    seen: set[tuple[str, str]] = set()
    for _ in range(_MAX_REEXPORT_CHASE):
        if (path, name) in seen:
            break
        seen.add((path, name))
        module = facts.get(path)
        if module is None:
            break
        if name in module.definitions or name in module.assignments:
            return path, name
        binding = module.bindings.get(name)
        if binding is None or binding.target_path is None:
            break
        if binding.is_module:
            return binding.target_path, "__module__"
        path, name = binding.target_path, binding.target_name or name
    return path, name


def extract_public_surface(
    root_path: str,
    universe: Iterable[str],
    *,
    package_name: str | None = None,
) -> tuple[tuple[PublicSurfaceEntry, ...], tuple[str, ...]]:
    """Extract the externally observable surface of a package.

    A feature is anchored on what callers outside the package can reach, not on
    internal structure, so the seed set is the public surface: ``__init__.py``
    re-exports, ``__all__`` members, module-level public bindings, CLI entry
    modules, and module-level decorator registrations.

    Args:
        root_path: Absolute path to the package root.
        universe: Repository-relative POSIX paths to consider (the analysed
            file set; anything outside it resolves to a miss, not a guess).
        package_name: Distribution/package name used to recognise absolute
            self-imports.  Defaults to the root directory name.

    Returns:
        ``(entries, diagnostics)``.  Diagnostics name every file that could not
        be parsed and every surface name that could not be resolved to a
        defining file, so an under-reported surface stays visible.

    Raises:
        SurfaceExtractionError: If *root_path* is not a directory.
    """
    root = Path(root_path)
    if not root.is_dir():
        raise SurfaceExtractionError(f"package root is not a directory: {root_path}")

    paths = frozenset(universe)
    if not paths:
        raise SurfaceExtractionError("public-surface extraction needs a non-empty universe")

    facts, diagnostics_seed = _build_module_facts(root_path, paths, package_name)
    diagnostics: list[str] = list(diagnostics_seed)

    entries: dict[tuple[str, str], PublicSurfaceEntry] = {}
    declarers = _surface_declarers(paths, facts)

    for declarer, exported_prefix in declarers:
        module_facts = facts.get(declarer)
        if module_facts is None:
            continue
        for name, origin in _declared_public_names(module_facts):
            defining_path, defining_name = _chase_definition(declarer, name, facts)
            if defining_path not in paths:
                diagnostics.append(f"unresolved_surface:{declarer}:{name}")
                continue
            qualified = f"{exported_prefix}{name}" if exported_prefix else name
            key = (qualified, defining_path)
            if key in entries:
                continue
            entries[key] = PublicSurfaceEntry(
                name=qualified,
                origin=origin,
                declared_in=declarer,
                defining_path=defining_path,
                defining_name=defining_name,
            )

    for entry in _cli_entries(paths, facts):
        entries.setdefault((entry.name, entry.defining_path), entry)

    for entry in _registration_entries(paths, facts):
        entries.setdefault((entry.name, entry.defining_path), entry)

    ordered = tuple(sorted(entries.values(), key=lambda e: (e.name, e.defining_path)))
    logger.info(
        "Extracted public surface: %d entries over %d defining files (%d diagnostics)",
        len(ordered),
        len({e.defining_path for e in ordered}),
        len(diagnostics),
    )
    return ordered, tuple(diagnostics)


def _build_module_facts(
    root_path: str,
    paths: frozenset[str],
    package_name: str | None,
) -> tuple[dict[str, _ModuleFacts], tuple[str, ...]]:
    """Parse every module once and expand star imports."""
    resolved_package = package_name or Path(root_path).name
    facts: dict[str, _ModuleFacts] = {}
    diagnostics: list[str] = []
    for path in sorted(paths):
        if not path.endswith(".py"):
            continue
        module_facts = _collect_module_facts(path, root_path, paths, resolved_package)
        facts[path] = module_facts
        if module_facts.parse_error is not None:
            diagnostics.append(f"unparsed:{path}:{module_facts.parse_error}")
    return _expand_star_imports(facts), tuple(diagnostics)


def build_runtime_import_graph(
    root_path: str,
    universe: Iterable[str],
    *,
    package_name: str | None = None,
) -> nx.DiGraph:
    """Build the file graph the surface cones traverse.

    An edge ``A -> B`` means A imports B at runtime.  This differs from
    :func:`~src.graph.dependency.build_dependency_graph` on one point that
    decides whether the partition works at all: ``TYPE_CHECKING``-guarded
    imports are excluded (see :func:`_runtime_import_targets`).

    Raises:
        SurfaceExtractionError: If *root_path* is not a directory or the
            universe is empty.
    """
    root = Path(root_path)
    if not root.is_dir():
        raise SurfaceExtractionError(f"package root is not a directory: {root_path}")
    paths = frozenset(universe)
    if not paths:
        raise SurfaceExtractionError("runtime import graph needs a non-empty universe")

    facts, _ = _build_module_facts(root_path, paths, package_name)
    graph = nx.DiGraph()
    for path in sorted(paths):
        graph.add_node(path, file_path=path)
    for path, module_facts in sorted(facts.items()):
        for target in sorted(module_facts.runtime_imports):
            if target in paths:
                graph.add_edge(path, target, edge_type="runtime_import")
    logger.info(
        "Runtime import graph: %d nodes, %d edges",
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )
    return graph


def _surface_declarers(
    paths: frozenset[str],
    facts: Mapping[str, _ModuleFacts],
) -> tuple[tuple[str, str], ...]:
    """Return ``(declaring module, exported name prefix)`` pairs.

    The root ``__init__.py`` is the primary declarer.  A sub-package that the
    root re-exports as a module (``from . import json``) is externally visible
    too, so its own public names join the surface under a dotted prefix.  A
    repository with no root ``__init__.py`` falls back to every module that
    declares ``__all__`` -- recorded as a fallback, never silently assumed.
    """
    root_init = "__init__.py"
    if root_init not in paths:
        fallback = tuple(
            (path, "")
            for path in sorted(paths)
            if facts.get(path) is not None and facts[path].dunder_all is not None
        )
        if fallback:
            logger.info(
                "No root __init__.py; falling back to %d __all__-declaring modules",
                len(fallback),
            )
        return fallback

    declarers: list[tuple[str, str]] = [(root_init, "")]
    seen: set[str] = {root_init}
    queue: list[tuple[str, str]] = [(root_init, "")]
    while queue:
        current, prefix = queue.pop(0)
        module_facts = facts.get(current)
        if module_facts is None:
            continue
        exported = _exported_names(module_facts)
        for name in sorted(exported):
            binding = module_facts.bindings.get(name)
            if binding is None or not binding.is_module or binding.target_path is None:
                continue
            if binding.target_path in seen:
                continue
            seen.add(binding.target_path)
            child_prefix = f"{prefix}{name}."
            declarers.append((binding.target_path, child_prefix))
            queue.append((binding.target_path, child_prefix))
    return tuple(declarers)


def _exported_names(module_facts: _ModuleFacts) -> frozenset[str]:
    """Names a module makes public: ``__all__`` when literal, else public binds."""
    if module_facts.dunder_all is not None:
        return frozenset(module_facts.dunder_all)
    public = {
        name
        for name in (
            set(module_facts.bindings)
            | set(module_facts.definitions)
            | set(module_facts.assignments)
        )
        if not name.startswith("_")
    }
    return frozenset(public)


def _declared_public_names(
    module_facts: _ModuleFacts,
) -> tuple[tuple[str, str], ...]:
    """Return ``(name, origin)`` for every public name a module declares."""
    result: list[tuple[str, str]] = []
    for name in sorted(_exported_names(module_facts)):
        if module_facts.dunder_all is not None and name in module_facts.dunder_all:
            origin = "dunder_all"
        elif name in module_facts.bindings:
            origin = "reexport"
        else:
            origin = "module_binding"
        result.append((name, origin))
    return tuple(result)


def _cli_entries(
    paths: frozenset[str],
    facts: Mapping[str, _ModuleFacts],
) -> tuple[PublicSurfaceEntry, ...]:
    """Surface entries for ``__main__.py`` modules (console entry points)."""
    entries: list[PublicSurfaceEntry] = []
    for path in sorted(p for p in paths if posixpath.basename(p) == "__main__.py"):
        module_facts = facts.get(path)
        if module_facts is None:
            continue
        defining_path, defining_name = path, "__main__"
        for candidate in ("main", "cli", "app"):
            if candidate in module_facts.bindings:
                chased_path, chased_name = _chase_definition(path, candidate, facts)
                if chased_path in paths:
                    defining_path, defining_name = chased_path, chased_name
                    break
        entries.append(
            PublicSurfaceEntry(
                name=path,
                origin="cli_entry",
                declared_in=path,
                defining_path=defining_path,
                defining_name=defining_name,
            )
        )
    return tuple(entries)


def _registration_entries(
    paths: frozenset[str],
    facts: Mapping[str, _ModuleFacts],
) -> tuple[PublicSurfaceEntry, ...]:
    """Surface entries for module-level definitions registered via a local decorator.

    A decorator that resolves inside the repository is a registration point: it
    wires the decorated definition into a registry that outside callers reach
    without importing the definition by name.
    """
    entries: list[PublicSurfaceEntry] = []
    for path in sorted(paths):
        module_facts = facts.get(path)
        if module_facts is None:
            continue
        for defined, decorator in module_facts.decorated_registrations:
            binding = module_facts.bindings.get(decorator)
            local = decorator in module_facts.definitions
            if binding is None and not local:
                continue
            if binding is not None and binding.target_path is None:
                continue
            entries.append(
                PublicSurfaceEntry(
                    name=f"{path}::{defined}",
                    origin="decorator_registry",
                    declared_in=path,
                    defining_path=path,
                    defining_name=defined,
                )
            )
    return tuple(entries)


@dataclass(frozen=True)
class SurfaceReachability:
    """Forward reachability of every public-surface seed over the file graph.

    ``signatures`` is the inversion that the L2 partition consumes: for a file
    it names *which* seeds reach it.  "Shared by the HTTP client and the HTTP
    server" and "shared by auth and caching" are different groups; asking only
    whether a file is shared collapses them into one bucket.
    """

    seed_paths: tuple[str, ...]
    closures: Mapping[str, frozenset[str]]
    signatures: Mapping[str, frozenset[str]]
    unreached: tuple[str, ...]

    def signature_of(self, path: str) -> frozenset[str]:
        """Return the seed set reaching *path* (empty when unreached)."""
        return self.signatures.get(path, frozenset())


def compute_surface_reachability(
    graph: nx.DiGraph,
    surface: Sequence[PublicSurfaceEntry],
    universe: Iterable[str],
) -> SurfaceReachability:
    """Compute ``R(e)`` per seed and invert it into per-file shared signatures.

    Seeds are deduplicated by defining file: two entries defined in the same
    file have identical closures, so keeping both would double-count without
    changing any partition.

    Args:
        graph: File-level dependency graph; an edge ``A -> B`` means A imports B.
        surface: Public-surface entries from :func:`extract_public_surface`.
        universe: The analysed file set; files outside the graph still appear in
            ``unreached`` rather than vanishing.

    Raises:
        SurfaceExtractionError: If the universe is empty.
    """
    paths = frozenset(universe)
    if not paths:
        raise SurfaceExtractionError("reachability needs a non-empty universe")

    seed_paths = tuple(sorted({e.defining_path for e in surface if e.defining_path in paths}))
    closures: dict[str, frozenset[str]] = {}
    signatures: dict[str, set[str]] = defaultdict(set)

    for seed in seed_paths:
        if seed in graph:
            reachable = (nx.descendants(graph, seed) | {seed}) & paths
        else:
            reachable = {seed}
        closures[seed] = frozenset(reachable)
        for path in reachable:
            signatures[path].add(seed)

    unreached = tuple(sorted(paths - set(signatures)))
    logger.info(
        "Surface reachability: %d seeds, %d distinct signatures, %d unreached files",
        len(seed_paths),
        len({frozenset(v) for v in signatures.values()}),
        len(unreached),
    )
    return SurfaceReachability(
        seed_paths=seed_paths,
        closures=closures,
        signatures={k: frozenset(v) for k, v in signatures.items()},
        unreached=unreached,
    )
