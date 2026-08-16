"""Deterministic reverse edges over the canonical Python IR.

This is an L0 projection, not a second call resolver.  The Python adapter has
already produced ``Symbol`` and ``Relation`` objects; this module only maps
resolved ``call``/``import`` relations from ``callee -> caller`` and preserves
ambiguous candidates as explicitly weak evidence.

The distinction matters.  Re-parsing source here would create a second
resolver with a second answer about the same code.  A reverse index must be a
view of the IR that the rest of the pipeline consumes.  Dynamic dispatch,
framework registration, string-keyed callbacks, and unresolved adapter facts
remain outside the index and are carried in its coverage boundary.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from src.ir import Relation, ResolutionStatus, Symbol


MODULE_SCOPE_SUFFIX = "<module>"
# Keep weak evidence useful to a reader.  Beyond eight candidates the list is
# a search result rather than an actionable caller answer; the unresolved
# record still preserves the count and the coverage boundary names the gap.
AMBIGUITY_FANOUT_LIMIT = 8
_TARGET_MARKER_RE = re.compile(r":(?P<target>[^:]+)$")


class ReverseEdgeError(ValueError):
    """Raised when reverse-edge construction receives unusable input."""


class EdgeKind(StrEnum):
    CALL = "call"
    IMPORT = "import"


class Resolution(StrEnum):
    """Strength of the target evidence attached to a reverse edge."""

    EXACT = "exact"
    BY_NAME = "by_name"
    AMBIGUOUS = "ambiguous"


class UnresolvedReason(StrEnum):
    """Why a relation did not become an exact reverse edge."""

    EXTERNAL_OR_BUILTIN = "external_or_builtin"
    DYNAMIC_DISPATCH = "dynamic_dispatch"
    AMBIGUOUS_FANOUT = "ambiguous_fanout"
    AMBIGUOUS_TARGET = "ambiguous_target"
    UNRESOLVED_RELATION = "unresolved_relation"
    TARGET_OUTSIDE_UNIVERSE = "target_outside_universe"


def is_module_scope(symbol_id: str) -> bool:
    """Return whether *symbol_id* is a file-body pseudo caller."""

    return symbol_id.endswith(f"::{MODULE_SCOPE_SUFFIX}")


def symbol_path(symbol_id: str) -> str:
    """Return the repository-relative path portion of a canonical ID."""

    return symbol_id.split("::", 1)[0]


@dataclass(frozen=True)
class SymbolDef:
    """A stable display identity, keyed as ``path::lexical qualified name``."""

    symbol_id: str
    path: str
    qualified_name: str
    local_name: str
    kind: str
    span: tuple[int, int]
    owner_class: str | None = None
    decorators: tuple[str, ...] = ()
    ir_symbol_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReverseEdge:
    """One IR relation projected with the callee first."""

    callee_id: str
    caller_id: str
    kind: EdgeKind
    resolution: Resolution
    line: int
    via: str
    candidates: tuple[str, ...] = ()

    def sort_key(self) -> tuple[str, ...]:
        return (
            self.callee_id,
            self.caller_id,
            self.kind.value,
            self.resolution.value,
            f"{self.line:09d}",
            self.via,
            ",".join(self.candidates),
        )


@dataclass(frozen=True)
class UnresolvedSite:
    """A call relation kept as a gap instead of silently discarded."""

    caller_id: str
    line: int
    name: str
    reason: UnresolvedReason
    status: str
    candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReverseIndexReadings:
    """Mechanical readings for the exact and weak portions of the index."""

    total_symbols: int
    total_paths: int
    ir_symbols: int
    ir_relations: int
    edges_exact: int
    edges_by_name: int
    edges_ambiguous: int
    call_sites_total: int
    call_sites_resolved: int
    call_sites_weak: int
    call_sites_unresolved: int
    unresolved_by_reason: Mapping[str, int]
    symbols_with_in_edges: int
    in_degree_median: int
    in_degree_p95: int
    in_degree_max: int
    zero_in_edge_symbols: int
    invisible_lower_bound_decorated: int
    invisible_lower_bound_string_named: int
    invisible_lower_bound_union: int
    dynamic_marker_sites: int
    duplicate_ir_symbol_definitions: int
    unmapped_ir_symbols: int

    def as_dict(self) -> dict[str, object]:
        return {
            "total_symbols": self.total_symbols,
            "total_paths": self.total_paths,
            "ir_symbols": self.ir_symbols,
            "ir_relations": self.ir_relations,
            "edges_exact": self.edges_exact,
            "edges_by_name": self.edges_by_name,
            "edges_ambiguous": self.edges_ambiguous,
            "call_sites_total": self.call_sites_total,
            "call_sites_resolved": self.call_sites_resolved,
            "call_sites_weak": self.call_sites_weak,
            "call_sites_unresolved": self.call_sites_unresolved,
            "call_site_resolution_rate": (
                round(self.call_sites_resolved / self.call_sites_total, 4)
                if self.call_sites_total
                else None
            ),
            "unresolved_by_reason": dict(sorted(self.unresolved_by_reason.items())),
            "in_edge_basis": "exact_only",
            "symbols_with_in_edges": self.symbols_with_in_edges,
            "symbols_with_in_edges_share": (
                round(self.symbols_with_in_edges / self.total_symbols, 4)
                if self.total_symbols
                else None
            ),
            "in_degree_median": self.in_degree_median,
            "in_degree_p95": self.in_degree_p95,
            "in_degree_max": self.in_degree_max,
            "zero_in_edge_symbols": self.zero_in_edge_symbols,
            "invisible_lower_bound_decorated": self.invisible_lower_bound_decorated,
            "invisible_lower_bound_string_named": self.invisible_lower_bound_string_named,
            "invisible_lower_bound_union": self.invisible_lower_bound_union,
            "dynamic_marker_sites": self.dynamic_marker_sites,
            "duplicate_ir_symbol_definitions": self.duplicate_ir_symbol_definitions,
            "unmapped_ir_symbols": self.unmapped_ir_symbols,
        }


@dataclass(frozen=True)
class CallerAnswer:
    """A symbol-specific answer with weak candidates kept separate."""

    callee_id: str
    exact: tuple[ReverseEdge, ...]
    by_name: tuple[ReverseEdge, ...]
    ambiguous: tuple[ReverseEdge, ...]
    coverage_note: str


@dataclass(frozen=True)
class ReverseIndex:
    """The symbol- and file-granularity reverse projection."""

    repo: str
    symbols: Mapping[str, SymbolDef]
    edges: tuple[ReverseEdge, ...]
    unresolved: tuple[UnresolvedSite, ...]
    readings: ReverseIndexReadings
    coverage_boundary: tuple[str, ...]
    _by_callee: Mapping[str, tuple[ReverseEdge, ...]] = field(default_factory=dict)
    _by_callee_path: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def callers_of(self, callee_id: str) -> CallerAnswer:
        """Return callers for one canonical symbol, never for a bare name."""

        hits = self._by_callee.get(callee_id, ())
        return CallerAnswer(
            callee_id=callee_id,
            exact=tuple(e for e in hits if e.resolution is Resolution.EXACT),
            by_name=tuple(e for e in hits if e.resolution is Resolution.BY_NAME),
            ambiguous=tuple(
                e for e in hits if e.resolution is Resolution.AMBIGUOUS
            ),
            coverage_note=self.coverage_boundary[0] if self.coverage_boundary else "",
        )

    def caller_paths_of(self, path: str) -> tuple[str, ...]:
        """Return caller files for a callee file path."""

        return self._by_callee_path.get(path, ())

    def to_payload(self) -> dict[str, object]:
        """Return the deterministic sidecar payload consumed by rendering."""

        by_callee: dict[str, list[dict[str, object]]] = defaultdict(list)
        for edge in self.edges:
            row: dict[str, object] = {
                "caller_id": edge.caller_id,
                "kind": edge.kind.value,
                "resolution": edge.resolution.value,
                "line": edge.line,
                "via": edge.via,
            }
            if edge.candidates:
                row["candidates"] = list(edge.candidates)
            by_callee[edge.callee_id].append(row)
        return {
            "schema": "cbe-reverse-edges/2",
            "source": "cbe-ir/2 Relation(kind=call|import)",
            "repo": self.repo,
            "coverage_boundary": list(self.coverage_boundary),
            "readings": self.readings.as_dict(),
            "symbols": {
                key: {
                    "path": value.path,
                    "qualified_name": value.qualified_name,
                    "local_name": value.local_name,
                    "kind": value.kind,
                    "ir_symbol_ids": list(value.ir_symbol_ids),
                }
                for key, value in sorted(self.symbols.items())
            },
            "by_callee_symbol": {
                key: by_callee[key] for key in sorted(by_callee)
            },
            "by_callee_path": {
                key: list(self._by_callee_path[key])
                for key in sorted(self._by_callee_path)
            },
            "unresolved_sites": [
                {
                    "caller_id": item.caller_id,
                    "line": item.line,
                    "name": item.name,
                    "reason": item.reason.value,
                    "status": item.status,
                    "candidates": list(item.candidates),
                }
                for item in self.unresolved
            ],
        }


def _module_name(path: str) -> str:
    stem = path[:-3] if path.endswith(".py") else path
    name = stem.replace("/", ".")
    return name[:-9] if name.endswith(".__init__") else name


def _lexical_name(symbol: Symbol) -> str:
    """Convert adapter-qualified names into stable file-relative names."""

    prefix = _module_name(symbol.path)
    if prefix and symbol.qualified_name.startswith(f"{prefix}."):
        return symbol.qualified_name[len(prefix) + 1 :]
    return symbol.qualified_name


def _canonical_id(symbol: Symbol) -> str:
    return f"{symbol.path}::{_lexical_name(symbol)}"


def _is_decorated(symbol: Symbol) -> bool:
    attrs = dict(symbol.language_attributes)
    start = attrs.get("definition_start_line")
    return isinstance(start, int) and start < symbol.definition.start_line


def _span(symbols: Sequence[Symbol]) -> tuple[int, int]:
    if not symbols:
        return (0, 0)
    chosen = min(symbols, key=lambda item: (item.definition.start_line, item.id))
    return chosen.definition.start_line, chosen.definition.end_line


def _symbol_defs(
    ir_symbols: Sequence[Symbol],
    ledger_symbol_ids: Iterable[str] | None,
) -> tuple[
    dict[str, SymbolDef],
    dict[str, str],
    dict[str, set[str]],
    int,
    int,
]:
    grouped: dict[str, list[Symbol]] = defaultdict(list)
    for symbol in ir_symbols:
        grouped[_canonical_id(symbol)].append(symbol)

    wanted = set(ledger_symbol_ids) if ledger_symbol_ids is not None else None
    defs: dict[str, SymbolDef] = {}
    ir_to_canonical: dict[str, str] = {}
    qualified_to_canonical: dict[str, set[str]] = defaultdict(set)
    for canonical, group in sorted(grouped.items()):
        if wanted is not None and canonical not in wanted:
            continue
        chosen = min(group, key=lambda item: item.id)
        defs[canonical] = SymbolDef(
            symbol_id=canonical,
            path=chosen.path,
            qualified_name=_lexical_name(chosen),
            local_name=chosen.local_name,
            kind=chosen.kind,
            span=_span(group),
            decorators=("<decorated>",) if any(_is_decorated(item) for item in group) else (),
            ir_symbol_ids=tuple(sorted(item.id for item in group)),
        )
        for item in group:
            ir_to_canonical[item.id] = canonical
            qualified_to_canonical[item.qualified_name].add(canonical)
            qualified_to_canonical[_lexical_name(item)].add(canonical)

    if wanted is not None:
        # Keep the frozen denominator even if a future adapter omits one symbol.
        # The placeholder is a visible mapping gap, not a fabricated edge target.
        for canonical in sorted(wanted - defs.keys()):
            path, separator, qualified = canonical.partition("::")
            if not separator or not path or not qualified:
                raise ReverseEdgeError(f"invalid ledger symbol id: {canonical!r}")
            defs[canonical] = SymbolDef(
                symbol_id=canonical,
                path=path,
                qualified_name=qualified,
                local_name=qualified.rsplit(".", 1)[-1],
                kind="unknown",
                span=(0, 0),
            )

    duplicate_count = sum(max(0, len(group) - 1) for group in grouped.values())
    unmapped_count = sum(
        1 for canonical in grouped if wanted is not None and canonical not in wanted
    )
    return defs, ir_to_canonical, qualified_to_canonical, duplicate_count, unmapped_count


def _target_from_locator(
    relation: Relation,
    qualified_to_canonical: Mapping[str, set[str]],
) -> str | None:
    """Repair only the adapter's unique package-prefix mismatch.

    Python IR relations in the scale fixtures may say
    ``celery.utils.time.get_exponential_backoff_interval`` while the symbol
    itself is qualified as ``utils.time.get_exponential_backoff_interval``.
    The target ref is still marked resolved, so dropping it would hide a
    static edge.  A unique qualified-name suffix is safe; a bare-name match is
    deliberately not attempted, which protects polymorphic methods.
    """

    match = _TARGET_MARKER_RE.search(relation.locator)
    if match is None:
        return None
    raw = match.group("target")
    if raw in {"", "?"} or raw.startswith("builtins."):
        return None
    exact = qualified_to_canonical.get(raw, set())
    if len(exact) == 1:
        return next(iter(exact))
    suffixes = {
        canonical
        for qualified, candidates in qualified_to_canonical.items()
        if "." in qualified and raw.endswith(f".{qualified}")
        for canonical in candidates
    }
    return next(iter(suffixes)) if len(suffixes) == 1 else None


def _relation_caller(
    relation: Relation,
    ir_to_canonical: Mapping[str, str],
) -> str:
    caller = ir_to_canonical.get(relation.source.id)
    return caller if caller is not None else f"{relation.path}::{MODULE_SCOPE_SUFFIX}"


def _reason_for(
    relation: Relation,
    *,
    candidate_count: int = 0,
    target_missing: bool = False,
) -> UnresolvedReason:
    text = relation.reason.lower()
    if any(marker in text for marker in ("dynamic", "getattr", "callback", "registry")):
        return UnresolvedReason.DYNAMIC_DISPATCH
    if relation.resolution_status is ResolutionStatus.EXTERNAL:
        return UnresolvedReason.EXTERNAL_OR_BUILTIN
    if candidate_count > AMBIGUITY_FANOUT_LIMIT:
        return UnresolvedReason.AMBIGUOUS_FANOUT
    if relation.resolution_status is ResolutionStatus.AMBIGUOUS:
        return UnresolvedReason.AMBIGUOUS_TARGET
    if target_missing:
        return UnresolvedReason.TARGET_OUTSIDE_UNIVERSE
    return UnresolvedReason.UNRESOLVED_RELATION


def _percentile(values: Sequence[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(fraction * (len(ordered) - 1) + 0.5))
    return ordered[index]


def _coverage_boundary(
    *,
    readings: ReverseIndexReadings,
    ledger_symbol_ids: Iterable[str] | None,
    index_symbols: Mapping[str, SymbolDef],
    ir_symbols: Sequence[Symbol],
    target_repairs: int,
) -> tuple[str, ...]:
    lines = [
        "STATIC IR ONLY: this sidecar is a projection of resolved/ambiguous "
        "cbe-ir/2 call and import relations; it is not a complete runtime call graph.",
        "Dynamic dispatch, getattr lookups, string-keyed registries, decorator "
        "registration, and framework callbacks may have no static Relation and "
        "are absent from every caller list. An empty list means no indexed "
        "static caller, never no runtime caller.",
        f"call-site accounting: {readings.call_sites_resolved} exact, "
        f"{readings.call_sites_weak} ambiguous, "
        f"{readings.call_sites_unresolved} unresolved of "
        f"{readings.call_sites_total}; "
        f"{dict(sorted(readings.unresolved_by_reason.items()))}",
        f"statically invisible lower bound: "
        f"{readings.invisible_lower_bound_union} zero-in-edge symbols are "
        f"decorated ({readings.invisible_lower_bound_decorated}); the IR does "
        "not carry a string-literal registration fact, so that part is not "
        "counted as evidence.",
        f"ambiguous candidate edges are kept out of exact answers: "
        f"{readings.edges_ambiguous}; bare-name guessing is never promoted.",
        f"IR symbol definitions: {readings.ir_symbols}; canonical index symbols: "
        f"{len(index_symbols)}; duplicate IR definitions collapsed: "
        f"{readings.duplicate_ir_symbol_definitions}; unmapped IR symbols: "
        f"{readings.unmapped_ir_symbols}; target refs repaired by unique "
        f"qualified-name suffix: {target_repairs}.",
    ]
    if ledger_symbol_ids is not None:
        ledger = set(ledger_symbol_ids)
        indexed = set(index_symbols)
        only_ledger = sorted(ledger - indexed)
        only_index = sorted(indexed - ledger)
        lines.append(
            f"symbol denominator: index {len(indexed)} vs ledger {len(ledger)}; "
            f"ledger-only {len(only_ledger)}, index-only {len(only_index)}"
        )
        if only_ledger:
            lines.append(f"ledger-only sample: {only_ledger[:10]}")
        if only_index:
            lines.append(f"index-only sample: {only_index[:10]}")
    return tuple(lines)


def build_reverse_index_from_ir(
    symbols: Iterable[Symbol],
    relations: Iterable[Relation],
    *,
    repo: str,
    paths: Iterable[str] = (),
    ledger_symbol_ids: Iterable[str] | None = None,
) -> ReverseIndex:
    """Build a reverse index from canonical IR objects only.

    ``ledger_symbol_ids`` is a display/denominator constraint, not a second
    source of edges.  It keeps the frozen flask/httpx denominator stable while
    the IR IDs remain the canonical relation identity internally.
    """

    ir_symbols = tuple(sorted(symbols, key=lambda item: item.id))
    ir_relations = tuple(sorted(relations, key=lambda item: item.id))
    if not repo:
        raise ReverseEdgeError("reverse index requires a non-empty repo name")
    if not ir_symbols:
        raise ReverseEdgeError("reverse index needs at least one IR symbol")

    frozen_ledger = (
        tuple(sorted(set(ledger_symbol_ids)))
        if ledger_symbol_ids is not None
        else None
    )
    defs, ir_to_canonical, qualified_to_canonical, duplicate_count, unmapped_count = (
        _symbol_defs(ir_symbols, frozen_ledger)
    )
    universe_paths = set(paths)
    universe_paths.update(symbol.path for symbol in ir_symbols)
    universe_paths.update(relation.path for relation in ir_relations)

    edges: list[ReverseEdge] = []
    unresolved: list[UnresolvedSite] = []
    exact_keys: set[tuple[object, ...]] = set()
    call_total = call_resolved = call_weak = call_unresolved = 0
    unresolved_counts: Counter[str] = Counter()
    dynamic_marker_sites = 0
    target_repairs = 0

    for relation in ir_relations:
        if relation.kind not in {EdgeKind.CALL.value, EdgeKind.IMPORT.value}:
            continue
        kind = EdgeKind(relation.kind)
        is_call = kind is EdgeKind.CALL
        if is_call:
            call_total += 1
        caller = _relation_caller(relation, ir_to_canonical)
        line = relation.evidence[0].start_line if relation.evidence else 0
        via = f"ir:{relation.resolution_method.value}:{relation.locator}"

        target = ir_to_canonical.get(relation.target.id) if relation.target else None
        if target is None and relation.resolution_status is ResolutionStatus.RESOLVED:
            target = _target_from_locator(relation, qualified_to_canonical)
            if target is not None:
                target_repairs += 1

        if relation.resolution_status is ResolutionStatus.RESOLVED and target in defs:
            edge = ReverseEdge(
                callee_id=target,
                caller_id=caller,
                kind=kind,
                resolution=Resolution.EXACT,
                line=line,
                via=via,
            )
            key = (
                edge.callee_id,
                edge.caller_id,
                edge.kind.value,
                edge.resolution.value,
                edge.line,
                edge.via,
            )
            if key not in exact_keys:
                exact_keys.add(key)
                edges.append(edge)
            if is_call:
                call_resolved += 1
            continue

        candidate_ids = tuple(
            sorted(
                {
                    ir_to_canonical[candidate.id]
                    for candidate in relation.candidates
                    if candidate.id in ir_to_canonical
                    and ir_to_canonical[candidate.id] in defs
                }
            )
        )
        if relation.resolution_status is ResolutionStatus.AMBIGUOUS and candidate_ids:
            if len(candidate_ids) <= AMBIGUITY_FANOUT_LIMIT:
                for candidate in candidate_ids:
                    edge = ReverseEdge(
                        callee_id=candidate,
                        caller_id=caller,
                        kind=kind,
                        resolution=Resolution.AMBIGUOUS,
                        line=line,
                        via=via,
                        candidates=candidate_ids,
                    )
                    key = (
                        edge.callee_id,
                        edge.caller_id,
                        edge.kind.value,
                        edge.resolution.value,
                        edge.line,
                        edge.via,
                        edge.candidates,
                    )
                    if key not in exact_keys:
                        exact_keys.add(key)
                        edges.append(edge)
                if is_call:
                    call_weak += 1
                continue

        reason = _reason_for(
            relation,
            candidate_count=len(relation.candidates),
            target_missing=(
                relation.resolution_status is ResolutionStatus.RESOLVED
                and target is None
            ),
        )
        unresolved_counts[reason.value] += 1 if is_call else 0
        if is_call:
            call_unresolved += 1
            unresolved.append(
                UnresolvedSite(
                    caller_id=caller,
                    line=line,
                    name=relation.locator.rsplit(":", 1)[-1],
                    reason=reason,
                    status=relation.resolution_status.value,
                    candidates=candidate_ids,
                )
            )
        if reason is UnresolvedReason.DYNAMIC_DISPATCH:
            dynamic_marker_sites += 1

    edges = sorted(edges, key=ReverseEdge.sort_key)
    unresolved = sorted(
        set(unresolved),
        key=lambda item: (
            item.caller_id,
            item.line,
            item.name,
            item.reason.value,
            item.status,
            item.candidates,
        ),
    )

    by_callee: dict[str, list[ReverseEdge]] = defaultdict(list)
    by_callee_path: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        by_callee[edge.callee_id].append(edge)
        by_callee_path[symbol_path(edge.callee_id)].add(symbol_path(edge.caller_id))

    exact_in: Counter[str] = Counter(
        edge.callee_id for edge in edges if edge.resolution is Resolution.EXACT
    )
    in_degrees = [exact_in.get(symbol_id, 0) for symbol_id in defs]
    zero = [symbol_id for symbol_id in defs if exact_in.get(symbol_id, 0) == 0]
    decorated_zero = [
        symbol_id for symbol_id in zero if defs[symbol_id].decorators
    ]
    readings = ReverseIndexReadings(
        total_symbols=len(defs),
        total_paths=len(universe_paths),
        ir_symbols=len(ir_symbols),
        ir_relations=len(ir_relations),
        edges_exact=sum(1 for edge in edges if edge.resolution is Resolution.EXACT),
        edges_by_name=sum(1 for edge in edges if edge.resolution is Resolution.BY_NAME),
        edges_ambiguous=sum(
            1 for edge in edges if edge.resolution is Resolution.AMBIGUOUS
        ),
        call_sites_total=call_total,
        call_sites_resolved=call_resolved,
        call_sites_weak=call_weak,
        call_sites_unresolved=call_unresolved,
        unresolved_by_reason=dict(unresolved_counts),
        symbols_with_in_edges=len(defs) - len(zero),
        in_degree_median=_percentile(in_degrees, 0.5),
        in_degree_p95=_percentile(in_degrees, 0.95),
        in_degree_max=max(in_degrees, default=0),
        zero_in_edge_symbols=len(zero),
        invisible_lower_bound_decorated=len(decorated_zero),
        invisible_lower_bound_string_named=0,
        invisible_lower_bound_union=len(decorated_zero),
        dynamic_marker_sites=dynamic_marker_sites,
        duplicate_ir_symbol_definitions=duplicate_count,
        unmapped_ir_symbols=unmapped_count,
    )
    boundary = _coverage_boundary(
        readings=readings,
        ledger_symbol_ids=frozen_ledger,
        index_symbols=defs,
        ir_symbols=ir_symbols,
        target_repairs=target_repairs,
    )
    return ReverseIndex(
        repo=repo,
        symbols=dict(sorted(defs.items())),
        edges=tuple(edges),
        unresolved=tuple(unresolved),
        readings=readings,
        coverage_boundary=boundary,
        _by_callee={key: tuple(by_callee[key]) for key in sorted(by_callee)},
        _by_callee_path={
            key: tuple(sorted(by_callee_path[key]))
            for key in sorted(by_callee_path)
        },
    )


def build_reverse_index(
    root_path: str,
    universe: Iterable[str],
    *,
    repo: str,
    package_name: str | None = None,
    ledger_symbol_ids: Iterable[str] | None = None,
) -> ReverseIndex:
    """Load the product's cached Python IR and build its reverse projection."""

    del package_name  # Kept for compatibility with the earlier graph API.
    root = Path(root_path)
    if not root.is_dir():
        raise ReverseEdgeError(f"package root is not a directory: {root_path}")
    paths = tuple(sorted(set(universe)))
    if not paths:
        raise ReverseEdgeError("reverse index needs a non-empty file universe")
    try:
        from src.semantic.inventory import enumerate_semantic_inventory
        from src.server import _python_semantic_ir_cached

        inventory = enumerate_semantic_inventory(root)
        symbols, relations = _python_semantic_ir_cached(
            root.as_posix(), inventory.source_revision
        )
    except Exception as exc:  # pragma: no cover - reports a boundary failure
        raise ReverseEdgeError(f"cannot load canonical Python IR: {exc}") from exc
    return build_reverse_index_from_ir(
        symbols,
        relations,
        repo=repo,
        paths=paths,
        ledger_symbol_ids=ledger_symbol_ids,
    )


def write_sidecar(index: ReverseIndex, destination: Path) -> Path:
    """Write a stable JSON sidecar; no timestamps or unordered values enter it."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(index.to_payload(), ensure_ascii=False, indent=1, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return destination


def load_sidecar(source: Path) -> dict[str, object]:
    """Load and minimally validate a reverse-edge sidecar."""

    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("schema") != "cbe-reverse-edges/2":
        raise ReverseEdgeError(f"unexpected reverse-edge schema in {source}")
    if payload.get("source") != "cbe-ir/2 Relation(kind=call|import)":
        raise ReverseEdgeError(f"reverse-edge source marker missing in {source}")
    return payload
