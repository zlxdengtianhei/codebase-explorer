"""Deterministically project a semantic ledger into four-level Markdown docs."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import unicodedata
import uuid
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from src.doc.mermaid import MermaidGenerator
from src.graph.reverse_edges import ReverseIndex, build_reverse_index
from src.semantic.layering import (
    DEFAULT_DETAIL_MAX_BLOCKS,
    DEFAULT_DETAIL_MAX_LINES,
    DEFAULT_INDEX_MAX_LINES,
    DETAIL_LEAF_NAME,
    LayerBudget,
    Page,
    PageUnit,
    assign_dag_layers,
    finalize_pages,
    hops_payload,
    measure_symbol_hops,
    split_until_fit,
    symbol_anchor,
)
from src.semantic.models import SemanticLedger, SemanticSymbolKind, SemanticSymbolRecord


DOCS_RELDIR = Path(".codebase-docs")
_GENERATED_HEADER = "<!-- generated:codebase-explorer-semantic-docs -->"
_NON_SLUG = re.compile(r"[^a-z0-9]+")
_symbol_anchor = symbol_anchor


@dataclass(frozen=True)
class _Projection:
    module_by_file: Mapping[str, str]
    display_by_module: Mapping[str, str]
    files_by_module: Mapping[str, tuple[str, ...]]
    conflicts_by_file: Mapping[str, tuple[str, ...]]
    ordered_fresh_ids: tuple[str, ...]
    dependency_edges: tuple[tuple[str, str], ...]


def _coerce_ledger(ledger: SemanticLedger | Mapping[str, object]) -> SemanticLedger:
    if isinstance(ledger, SemanticLedger):
        return ledger
    if isinstance(ledger, Mapping):
        return SemanticLedger.model_validate(ledger)
    raise TypeError("ledger must be a SemanticLedger or JSON-compatible mapping")


def _slug_base(raw: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode()
    slug = _NON_SLUG.sub("-", ascii_value.lower()).strip("-")
    return slug or "module"


def _module_slugs(raw_module_ids: set[str]) -> dict[str, str]:
    by_base: dict[str, list[str]] = {}
    for raw in sorted(raw_module_ids):
        by_base.setdefault(_slug_base(raw), []).append(raw)
    result: dict[str, str] = {}
    for base, raw_ids in sorted(by_base.items()):
        for raw in raw_ids:
            suffix = ""
            if len(raw_ids) > 1:
                suffix = "-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
            result[raw] = base + suffix
    return result


def _file_module_assignments(
    ledger: SemanticLedger,
) -> tuple[dict[str, str], dict[str, tuple[str, ...]], dict[str, str]]:
    symbols_by_file: dict[str, list[SemanticSymbolRecord]] = {
        path: [] for path in ledger.files
    }
    for symbol in ledger.symbols.values():
        symbols_by_file[symbol.path].append(symbol)
    raw_by_file: dict[str, str] = {}
    conflicts: dict[str, tuple[str, ...]] = {}
    for path in sorted(ledger.files):
        candidates = [item.module_id for item in symbols_by_file[path] if item.module_id]
        counts = Counter(candidates)
        if counts:
            chosen = min(counts, key=lambda item: (-counts[item], item))
            raw_by_file[path] = chosen
            if len(counts) > 1:
                conflicts[path] = tuple(sorted(counts))
        else:
            raw_by_file[path] = "unclassified"
    slug_by_raw = _module_slugs(set(raw_by_file.values()))
    return (
        {path: slug_by_raw[raw] for path, raw in raw_by_file.items()},
        conflicts,
        {slug_by_raw[raw]: raw for raw in sorted(slug_by_raw)},
    )


def _ordered_fresh_ids(ledger: SemanticLedger) -> tuple[str, ...]:
    fresh = {symbol_id for symbol_id, record in ledger.symbols.items() if record.is_fresh}
    projected = [symbol_id for symbol_id in ledger.order if symbol_id in fresh]
    projected.extend(sorted(fresh - set(projected)))
    return tuple(projected)


def _dependency_edges(
    ledger: SemanticLedger,
    graph: nx.DiGraph | None,
) -> tuple[tuple[str, str], ...]:
    known = set(ledger.symbols)
    if graph is not None:
        edges = {
            (str(source), str(target))
            for source, target in graph.edges()
            if str(source) in known and str(target) in known and source != target
        }
    else:
        edges = {
            (symbol_id, cited)
            for symbol_id, record in ledger.symbols.items()
            for cited in (record.explanation.cited_symbol_ids if record.explanation else ())
            if cited in known and cited != symbol_id
        }
    return tuple(sorted(edges))


def _build_projection(ledger: SemanticLedger, graph: nx.DiGraph | None) -> _Projection:
    module_by_file, conflicts, display_by_module = _file_module_assignments(ledger)
    files_by_module = {
        module: tuple(sorted(path for path, owner in module_by_file.items() if owner == module))
        for module in sorted(set(module_by_file.values()))
    }
    return _Projection(
        module_by_file=module_by_file,
        display_by_module=display_by_module,
        files_by_module=files_by_module,
        conflicts_by_file=conflicts,
        ordered_fresh_ids=_ordered_fresh_ids(ledger),
        dependency_edges=_dependency_edges(ledger, graph),
    )


_SENTENCE_END_CN = frozenset("。！？")
_SENTENCE_END_EN = frozenset(".!?")
_IDENT_CONTINUE = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
_KIND_ORDER = (
    (SemanticSymbolKind.CLASS, "类"),
    (SemanticSymbolKind.FUNCTION, "函数"),
    (SemanticSymbolKind.METHOD, "方法"),
)
_SUMMARY_NAME_CAP = 6
_SUMMARY_CHAR_CAP = 240


def _clip_visible_prefix(text: str, limit: int = _SUMMARY_CHAR_CAP) -> str:
    if len(text) <= limit:
        return text
    clipped = text[: limit - 1].rstrip()
    if clipped.count("`") % 2 == 1:
        clipped = clipped.rsplit("`", 1)[0].rstrip()
    return clipped + "…"


def _first_sentence(text: str) -> str:
    """Cut at a real sentence end, not a qualifier dot or inline-code fragment."""
    normalized = " ".join(text.split())
    in_backtick = False
    cut: int | None = None
    for index, char in enumerate(normalized):
        if char == "`":
            in_backtick = not in_backtick
            continue
        if in_backtick:
            continue
        if char in _SENTENCE_END_CN:
            cut = index + 1
            break
        if char not in _SENTENCE_END_EN:
            continue
        nxt = normalized[index + 1] if index + 1 < len(normalized) else ""
        if char == "." and nxt in _IDENT_CONTINUE:
            continue
        cut = index + 1
        break
    summary = normalized if cut is None else normalized[:cut]
    return _clip_visible_prefix(summary)


def _backticked_list(names: tuple[str, ...]) -> str:
    return "、".join(f"`{name.replace('`', '')}`" for name in names if name)


def _ranked_class_names(records: list[SemanticSymbolRecord]) -> list[str]:
    class_names = {record.qualified_name for record in records if record.kind is SemanticSymbolKind.CLASS}
    method_counts: Counter[str] = Counter()
    for record in records:
        if record.kind is SemanticSymbolKind.METHOD and "." in record.qualified_name:
            owner = record.qualified_name.rsplit(".", 1)[0]
            if owner in class_names:
                method_counts[owner] += 1
    return sorted(class_names, key=lambda name: (-method_counts[name], name))


def _ranked_function_names(records: list[SemanticSymbolRecord]) -> list[str]:
    return sorted(
        record.qualified_name
        for record in records
        if record.kind is SemanticSymbolKind.FUNCTION and "." not in record.qualified_name
    )


def _method_root_names(records: list[SemanticSymbolRecord]) -> list[str]:
    return sorted({record.qualified_name.split(".", 1)[0] for record in records})


def _kind_inventory(records: list[SemanticSymbolRecord]) -> str:
    counts = Counter(record.kind for record in records)
    parts = [f"{counts[kind]} 个{label}" for kind, label in _KIND_ORDER if counts[kind]]
    return "、".join(parts) if parts else f"{len(records)} 个符号"


def _module_neighbor_names(
    ledger: SemanticLedger,
    projection: _Projection,
    module: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    edges = _module_dependency_edges(ledger, projection)
    outbound = tuple(
        sorted({projection.display_by_module[target] for source, target in edges if source == module})
    )
    inbound = tuple(
        sorted({projection.display_by_module[source] for source, target in edges if target == module})
    )
    return outbound, inbound


def _symbol_modules(ledger: SemanticLedger, projection: _Projection) -> dict[str, str]:
    return {
        symbol_id: projection.module_by_file[record.path]
        for symbol_id, record in ledger.symbols.items()
    }


def _module_dependency_edges(
    ledger: SemanticLedger,
    projection: _Projection,
) -> list[tuple[str, str]]:
    modules = _symbol_modules(ledger, projection)
    return sorted(
        {
            (modules[caller], modules[callee])
            for caller, callee in projection.dependency_edges
            if modules[caller] != modules[callee]
        }
    )


def _module_stats(
    ledger: SemanticLedger,
    projection: _Projection,
    module: str,
) -> tuple[int, int, int]:
    records = [
        record
        for record in ledger.symbols.values()
        if projection.module_by_file[record.path] == module
    ]
    fresh = sum(record.is_fresh for record in records)
    stale = sum(record.is_explained and not record.is_fresh for record in records)
    return len(records), fresh, stale


def _module_summary(ledger: SemanticLedger, projection: _Projection, module: str) -> str:
    records = [
        ledger.symbols[symbol_id]
        for symbol_id in projection.ordered_fresh_ids
        if projection.module_by_file[ledger.symbols[symbol_id].path] == module
    ]
    if not records:
        return "当前没有 fresh 函数语义；详情页显式列出文件状态与残差。"
    class_names = _ranked_class_names(records)
    function_names = _ranked_function_names(records)
    if class_names:
        label, pool = "类", class_names
    elif function_names:
        label, pool = "函数", function_names
    else:
        label, pool = "符号根", _method_root_names(records)
    inventory = _kind_inventory(records)
    outbound, inbound = _module_neighbor_names(ledger, projection, module)
    dep_bits: list[str] = []
    if outbound:
        dep_bits.append(f"依赖 {_backticked_list(outbound)}")
    if inbound:
        dep_bits.append(f"被 {_backticked_list(inbound)} 引用")
    dep_clause = "；".join(dep_bits)
    name_cap = min(_SUMMARY_NAME_CAP, len(pool))
    include_deps = bool(dep_clause)
    while True:
        shown = tuple(pool[:name_cap])
        name_bit = _backticked_list(shown)
        if len(pool) > name_cap:
            name_bit += f" 等 {len(pool)} 个"
        core = f"fresh 表面：{inventory}；{label} {name_bit}。"
        summary = f"{core}{dep_clause}。" if include_deps else core
        if len(summary) <= _SUMMARY_CHAR_CAP:
            return summary
        if name_cap > 1:
            name_cap -= 1
            continue
        if include_deps:
            include_deps = False
            name_cap = min(_SUMMARY_NAME_CAP, len(pool))
            continue
        return _clip_visible_prefix(core)


def _public_surface_ids(ledger: SemanticLedger, projection: _Projection) -> tuple[str, ...]:
    found: list[str] = []
    for symbol_id in projection.ordered_fresh_ids:
        path = ledger.symbols[symbol_id].path
        if path == "__init__.py" or path.endswith("/__init__.py"):
            found.append(symbol_id)
    return tuple(found)


def _build_index_page(
    repo_root: Path,
    ledger: SemanticLedger,
    projection: _Projection,
    dups: _DuplicateIndex,
) -> Page:
    modules = sorted(projection.files_by_module)
    module_edges = _module_dependency_edges(ledger, projection)
    mermaid = MermaidGenerator().generate_module_diagram(modules, module_edges)
    units: list[PageUnit] = [
        PageUnit(
            unit_id="intro",
            kind="fixed",
            group_key="fixed",
            name="intro",
            one_liner="",
            lines=(
                "这份项目级入口由 semantic ledger 确定性派生。沿模块链接进入文件目录，再读取每个 fresh 函数、方法或类的可寻址解释块。",
            ),
        ),
        PageUnit(
            unit_id="overview",
            kind="fixed",
            group_key="fixed",
            name="overview",
            one_liner="",
            lines=(
                "## 项目概览",
                "",
                f"- 源码文件：{len(ledger.files)}",
                f"- 符号总数：{ledger.totals.symbols}",
                f"- Fresh 解释：{ledger.totals.explained}",
                f"- Stale 解释：{ledger.totals.stale}",
                f"- 未覆盖符号：{ledger.totals.uncovered}",
                f"- 残差：{ledger.totals.residual}",
                f"- 覆盖率：{ledger.coverage_percent}%",
            ),
        ),
        PageUnit(
            unit_id="heading:module",
            kind="heading",
            group_key="module",
            name="模块",
            one_liner="",
            lines=("## 模块", ""),
        ),
    ]
    for module in modules:
        total, fresh, stale = _module_stats(ledger, projection, module)
        display = projection.display_by_module[module]
        summary = _module_summary(ledger, projection, module)
        target = f"{module}/{DETAIL_LEAF_NAME}"
        units.append(
            PageUnit(
                unit_id=f"module:{module}",
                kind="entry",
                group_key="module",
                name=display,
                one_liner=summary,
                lines=(
                    f"- [{display}](@@PAGE:{target}@@)：{len(projection.files_by_module[module])} 个文件，"
                    f"{fresh}/{total} fresh，{stale} stale。{summary}",
                ),
                nav_target=target,
            )
        )
    surface_ids = _public_surface_ids(ledger, projection)
    if surface_ids:
        units.append(
            PageUnit(
                unit_id="heading:surface",
                kind="heading",
                group_key="surface",
                name="公共面",
                one_liner="",
                lines=("## 公共面", ""),
            )
        )
        for symbol_id in surface_ids:
            record = ledger.symbols[symbol_id]
            sentence = _first_sentence(record.explanation.text)  # type: ignore[union-attr]
            units.append(
                PageUnit(
                    unit_id=f"surface:{symbol_id}",
                    kind="entry",
                    group_key="surface",
                    name=record.qualified_name,
                    one_liner=sentence,
                    lines=(f"- [`{record.qualified_name}`](@@SYM:{symbol_id}@@)：{sentence}",),
                )
            )
    units.extend(_dup_index_units(dups))
    units.extend(
        [
            PageUnit(
                unit_id="heading:diagram",
                kind="heading",
                group_key="diagram",
                name="模块依赖图",
                one_liner="",
                lines=("## 模块依赖图", ""),
            ),
            PageUnit(
                unit_id="diagram",
                kind="entry",
                group_key="diagram",
                name="模块依赖图",
                one_liner="模块依赖图完整保留，无删减。",
                lines=("```mermaid", mermaid, "```"),
            ),
            PageUnit(
                unit_id="heading:residual",
                kind="heading",
                group_key="residual",
                name="未覆盖、stale 与 residual",
                one_liner="",
                lines=("## 未覆盖、stale 与 residual", ""),
            ),
        ]
    )
    residuals = {item.symbol_id: item.reason for item in ledger.residuals}
    if not ledger.uncovered_symbols:
        units.append(
            PageUnit(
                unit_id="residual:empty",
                kind="entry",
                group_key="residual",
                name="无残差",
                one_liner="当前每个符号都有 fresh 解释。",
                lines=("无。当前每个符号都有 fresh 解释。",),
            )
        )
    else:
        for symbol_id in ledger.uncovered_symbols:
            record = ledger.symbols[symbol_id]
            status = "stale" if record.is_explained else "uncovered"
            reason = residuals.get(symbol_id) or record.invalidation_reason or "未提供原因"
            units.append(
                PageUnit(
                    unit_id=f"residual:{symbol_id}",
                    kind="entry",
                    group_key="residual",
                    name=symbol_id,
                    one_liner=f"{status}；{reason}",
                    lines=(
                        f"- <!-- symbol:{symbol_id} --><a id=\"{_symbol_anchor(symbol_id)}\"></a>"
                        f"`{symbol_id}`（{record.path}:{record.span[0]}-{record.span[1]}）："
                        f"{status}；{reason}",
                    ),
                    symbol_ids=(symbol_id,),
                )
            )
    units.append(
        PageUnit(
            unit_id="status",
            kind="fixed",
            group_key="fixed",
            name="status",
            one_liner="",
            lines=(
                "## 可复算状态",
                "",
                f"- Ledger schema：`{ledger.schema}`",
                f"- Source revision：`{ledger.source_revision}`",
                "- 上层文字只折叠 fresh 函数事实；stale 与 residual 不生成伪解释。",
            ),
        )
    )
    return Page(
        relpath="INDEX.md",
        kind="index",
        title=f"{repo_root.name} 代码语义索引",
        parent_relpath=None,
        parent_title="",
        units=tuple(units),
    )


def _file_dependency_edges(
    ledger: SemanticLedger,
    projection: _Projection,
    module: str,
) -> list[tuple[str, str]]:
    modules = _symbol_modules(ledger, projection)
    edges: set[tuple[str, str]] = set()
    for caller, callee in projection.dependency_edges:
        if module not in (modules[caller], modules[callee]):
            continue
        caller_label = f"{modules[caller]}:{ledger.symbols[caller].path}"
        callee_label = f"{modules[callee]}:{ledger.symbols[callee].path}"
        if caller_label != callee_label:
            edges.add((caller_label, callee_label))
    return sorted(edges)


def _citation_text(cited_ids: tuple[str, ...]) -> str:
    if not cited_ids:
        return "无 ledger 内符号引用"
    return "、".join(f"[`{cited}`](@@SYM:{cited}@@)" for cited in cited_ids)


_EXACT_SHOW = 3
_AMBIG_SHOW = 3
_INBOUND_EMPTY_NOTE = "空列表 ≠ 无运行时调用方"
_DUNDER_LOCAL = frozenset(
    {
        "__init__",
        "__str__",
        "__repr__",
        "__eq__",
        "__ne__",
        "__hash__",
        "__iter__",
        "__len__",
        "__enter__",
        "__exit__",
        "__call__",
        "__getattr__",
        "__setattr__",
        "__getitem__",
        "__setitem__",
        "__contains__",
        "__new__",
        "__del__",
    }
)


@dataclass(frozen=True)
class _CallerHit:
    caller_id: str
    kind: str
    line: int
    candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class _InboundView:
    exact: Mapping[str, tuple[_CallerHit, ...]]
    ambiguous: Mapping[str, tuple[_CallerHit, ...]]
    decorated: Mapping[str, tuple[str, ...]]
    known_ids: frozenset[str]

    def exact_of(self, symbol_id: str) -> tuple[_CallerHit, ...]:
        return self.exact.get(symbol_id, ())

    def ambig_of(self, symbol_id: str) -> tuple[_CallerHit, ...]:
        return self.ambiguous.get(symbol_id, ())

    def decorators_of(self, symbol_id: str) -> tuple[str, ...]:
        return self.decorated.get(symbol_id, ())

    def file_exact(self, path: str, symbol_ids: Sequence[str]) -> tuple[str, ...]:
        seen: list[str] = []
        for symbol_id in symbol_ids:
            for hit in self.exact_of(symbol_id):
                if hit.caller_id not in seen:
                    seen.append(hit.caller_id)
        return tuple(seen)


def _unique_hits(rows: Sequence[_CallerHit]) -> tuple[_CallerHit, ...]:
    seen: set[str] = set()
    out: list[_CallerHit] = []
    for hit in rows:
        if hit.caller_id in seen:
            continue
        seen.add(hit.caller_id)
        out.append(hit)
    return tuple(out)


def _hits_from_rows(rows: Sequence[Mapping[str, object]], resolution: str) -> tuple[_CallerHit, ...]:
    hits: list[_CallerHit] = []
    for row in rows:
        if str(row.get("resolution") or "") != resolution:
            continue
        caller = str(row.get("caller_id") or "")
        if not caller:
            continue
        raw_cands = row.get("candidates") or ()
        candidates = tuple(str(item) for item in raw_cands) if isinstance(raw_cands, (list, tuple)) else ()
        line = row.get("line")
        hits.append(
            _CallerHit(
                caller_id=caller,
                kind=str(row.get("kind") or "call"),
                line=int(line) if isinstance(line, int) else 0,
                candidates=candidates,
            )
        )
    return _unique_hits(hits)


def inbound_view_from_reverse_index(index: ReverseIndex) -> _InboundView:
    exact: dict[str, tuple[_CallerHit, ...]] = {}
    ambiguous: dict[str, tuple[_CallerHit, ...]] = {}
    decorated: dict[str, tuple[str, ...]] = {}
    for symbol_id, defn in index.symbols.items():
        answer = index.callers_of(symbol_id)
        exact[symbol_id] = _unique_hits(
            tuple(
                _CallerHit(edge.caller_id, edge.kind.value, edge.line, edge.candidates)
                for edge in answer.exact
            )
        )
        ambiguous[symbol_id] = _unique_hits(
            tuple(
                _CallerHit(edge.caller_id, edge.kind.value, edge.line, edge.candidates)
                for edge in answer.ambiguous
            )
        )
        if defn.decorators:
            decorated[symbol_id] = tuple(defn.decorators)
    return _InboundView(
        exact=exact,
        ambiguous=ambiguous,
        decorated=decorated,
        known_ids=frozenset(index.symbols),
    )


def inbound_view_from_payload(payload: Mapping[str, object]) -> _InboundView:
    by_callee = payload.get("by_callee_symbol") or {}
    if not isinstance(by_callee, Mapping):
        by_callee = {}
    symbols = payload.get("symbols") or {}
    if not isinstance(symbols, Mapping):
        symbols = {}
    exact: dict[str, tuple[_CallerHit, ...]] = {}
    ambiguous: dict[str, tuple[_CallerHit, ...]] = {}
    decorated: dict[str, tuple[str, ...]] = {}
    known = set(str(key) for key in symbols)
    for symbol_id, rows in by_callee.items():
        sid = str(symbol_id)
        known.add(sid)
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
            continue
        typed = [row for row in rows if isinstance(row, Mapping)]
        exact[sid] = _hits_from_rows(typed, "exact")
        ambiguous[sid] = _hits_from_rows(typed, "ambiguous")
        extra = next((row.get("decorators") for row in typed if isinstance(row, Mapping) and row.get("decorators")), None)
        if extra:
            decorated[sid] = tuple(str(item) for item in extra)
    for symbol_id, body in symbols.items():
        if not isinstance(body, Mapping):
            continue
        decos = body.get("decorators")
        if decos:
            decorated[str(symbol_id)] = tuple(str(item) for item in decos)
    return _InboundView(
        exact=exact,
        ambiguous=ambiguous,
        decorated=decorated,
        known_ids=frozenset(known),
    )


def _empty_inbound() -> _InboundView:
    return _InboundView(exact={}, ambiguous={}, decorated={}, known_ids=frozenset())


def resolve_inbound_view(
    repo_root: Path,
    ledger: SemanticLedger,
    supplied: ReverseIndex | Mapping[str, object] | None,
) -> _InboundView:
    if isinstance(supplied, ReverseIndex):
        return inbound_view_from_reverse_index(supplied)
    if isinstance(supplied, Mapping):
        return inbound_view_from_payload(supplied)
    try:
        index = build_reverse_index(
            str(repo_root),
            list(ledger.files),
            repo=repo_root.name,
            ledger_symbol_ids=list(ledger.symbols),
        )
    except Exception:
        return _empty_inbound()
    return inbound_view_from_reverse_index(index)


def _local_name(record: SemanticSymbolRecord) -> str:
    return record.qualified_name.rsplit(".", 1)[-1]


def _owner_class(record: SemanticSymbolRecord) -> str | None:
    if "." not in record.qualified_name:
        return None
    return record.qualified_name.rsplit(".", 1)[0]


def _is_override_pair(left: SemanticSymbolRecord, right: SemanticSymbolRecord) -> bool:
    left_owner, right_owner = _owner_class(left), _owner_class(right)
    if left_owner is not None and right_owner is not None and left_owner != right_owner:
        return True
    kinds = {left.kind, right.kind}
    if SemanticSymbolKind.FUNCTION in kinds and SemanticSymbolKind.METHOD in kinds:
        return True
    if (left_owner is None) != (right_owner is None):
        return True
    return False


def _file_digest_map(repo_root: Path, ledger: SemanticLedger) -> dict[str, str]:
    digests: dict[str, str] = {}
    for path in ledger.files:
        source = repo_root / path
        if source.is_file():
            digests[path] = hashlib.sha256(source.read_bytes()).hexdigest()
            continue
        revision = (ledger.file_revisions or {}).get(path)
        if revision:
            digests[path] = revision.split(":", 1)[-1]
    return digests


def _source_def_line(repo_root: Path, record: SemanticSymbolRecord) -> str:
    source = repo_root / record.path
    if not source.is_file():
        return ""
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return ""
    start, end = record.span
    for index in range(max(0, start - 1), min(end, len(lines))):
        stripped = lines[index].strip()
        if stripped.startswith(("def ", "async def ", "class ")):
            return stripped.rstrip(":")
    return ""


def _source_decorators(repo_root: Path, record: SemanticSymbolRecord) -> tuple[str, ...]:
    source = repo_root / record.path
    if not source.is_file():
        return ()
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return ()
    start, _end = record.span
    found: list[str] = []
    index = start - 2
    while index >= 0:
        stripped = lines[index].strip()
        if stripped.startswith("@"):
            found.append(stripped)
            index -= 1
            continue
        if not stripped:
            index -= 1
            continue
        break
    return tuple(reversed(found))


@dataclass(frozen=True)
class _DuplicateIndex:
    byte_groups: tuple[tuple[str, ...], ...]
    name_groups: Mapping[str, tuple[str, ...]]
    byte_mates: Mapping[str, tuple[str, ...]]
    dead_copy_ids: frozenset[str]
    dead_copy_paths: frozenset[str]
    signatures: Mapping[str, str]

    def file_labels(self, path: str) -> list[str]:
        lines: list[str] = []
        mates = self.byte_mates.get(path, ())
        if mates:
            shown = " · ".join(f"`{item}`" for item in mates)
            lines.append(f"- 重复能力（字节相同）：{shown}")
        names: list[str] = []
        for local, sids in self.name_groups.items():
            paths = {item.split("::", 1)[0] for item in sids}
            if path in paths and len(paths) > 1:
                others = sorted(p for p in paths if p != path)
                sigs = []
                for sid in sids:
                    if sid.startswith(f"{path}::") and self.signatures.get(sid):
                        sigs.append(f"`{self.signatures[sid]}`")
                extra = f"（{sigs[0]}）" if sigs else ""
                names.append(f"`{local}` → " + " · ".join(f"`{item}`" for item in others[:4]) + extra)
        if names:
            lines.append("- 同名/近重实现：" + "；".join(names[:4]))
        if path in self.dead_copy_paths:
            lines.append("- 零静态调用方副本")
        return lines

    def symbol_labels(self, symbol_id: str, path: str) -> list[str]:
        lines: list[str] = []
        if self.byte_mates.get(path):
            shown = " · ".join(f"`{item}`" for item in self.byte_mates[path])
            lines.append(f"- 重复能力（字节相同）：{shown}")
        local = symbol_id.rsplit("::", 1)[-1].rsplit(".", 1)[-1]
        peers = [sid for sid in self.name_groups.get(local, ()) if sid != symbol_id]
        if peers:
            bits: list[str] = []
            for peer in peers[:4]:
                sig = self.signatures.get(peer)
                bits.append(f"`{peer}`" + (f"（`{sig}`）" if sig else ""))
            more = f" +{len(peers) - 4} more" if len(peers) > 4 else ""
            lines.append("- 同名/近重实现：" + " · ".join(bits) + more)
        if symbol_id in self.dead_copy_ids:
            lines.append("- 零静态调用方副本")
        return lines


def build_duplicate_index(
    repo_root: Path,
    ledger: SemanticLedger,
    inbound: _InboundView,
) -> _DuplicateIndex:
    digests = _file_digest_map(repo_root, ledger)
    by_hash: dict[str, list[str]] = {}
    for path, digest in sorted(digests.items()):
        by_hash.setdefault(digest, []).append(path)
    byte_groups = tuple(tuple(paths) for paths in by_hash.values() if len(paths) >= 2)
    byte_mates: dict[str, tuple[str, ...]] = {}
    for group in byte_groups:
        for path in group:
            byte_mates[path] = tuple(item for item in group if item != path)

    name_groups: dict[str, list[str]] = {}
    for symbol_id, record in ledger.symbols.items():
        local = _local_name(record)
        if local in _DUNDER_LOCAL:
            continue
        name_groups.setdefault(local, []).append(symbol_id)
    kept_names = {
        local: tuple(sorted(sids))
        for local, sids in name_groups.items()
        if len({sid.split("::", 1)[0] for sid in sids}) >= 2
    }

    signatures = {
        symbol_id: _source_def_line(repo_root, record)
        for symbol_id, record in ledger.symbols.items()
        if _local_name(record) in kept_names
    }

    dead_ids: set[str] = set()
    for _local, sids in kept_names.items():
        records = {sid: ledger.symbols[sid] for sid in sids if sid in ledger.symbols}
        for sid, record in records.items():
            if inbound.exact_of(sid):
                continue
            if inbound.decorators_of(sid) or _source_decorators(repo_root, record):
                continue
            live_sibling = False
            for other_id, other in records.items():
                if other_id == sid:
                    continue
                if not inbound.exact_of(other_id):
                    continue
                if _is_override_pair(record, other):
                    continue
                live_sibling = True
                break
            if live_sibling:
                dead_ids.add(sid)
    dead_paths = {sid.split("::", 1)[0] for sid in dead_ids}
    return _DuplicateIndex(
        byte_groups=byte_groups,
        name_groups=kept_names,
        byte_mates=byte_mates,
        dead_copy_ids=frozenset(dead_ids),
        dead_copy_paths=frozenset(dead_paths),
        signatures=signatures,
    )


def _caller_line(hit: _CallerHit, *, known_ids: frozenset[str], ambiguous: bool) -> str:
    mark = "~ " if ambiguous else ""
    if hit.caller_id in known_ids and "::" in hit.caller_id and not hit.caller_id.endswith("::<module>"):
        body = f"[`{hit.caller_id}`](@@SYM:{hit.caller_id}@@) {hit.kind}"
    else:
        body = f"`{hit.caller_id}` {hit.kind}"
    line = f"- {mark}{body}"
    if ambiguous and hit.candidates:
        shown = "、".join(f"`{item.rsplit('::', 1)[-1]}`" for item in hit.candidates[:8])
        line += f" · 候选 {{{shown}}}"
    return line


def _symbol_decorators(
    repo_root: Path,
    record: SemanticSymbolRecord,
    symbol_id: str,
    inbound: _InboundView,
) -> tuple[str, ...]:
    from_index = inbound.decorators_of(symbol_id)
    if from_index:
        return from_index
    return _source_decorators(repo_root, record)


def render_inbound_section(
    symbol_id: str,
    record: SemanticSymbolRecord,
    inbound: _InboundView,
    dups: _DuplicateIndex,
    *,
    repo_root: Path,
) -> list[str]:
    exact = inbound.exact_of(symbol_id)
    ambig = inbound.ambig_of(symbol_id)
    decos = _symbol_decorators(repo_root, record, symbol_id, inbound)
    lines = [
        "#### 入边（静态）",
        "",
        (
            f"- 精确 **{len(exact)}** · 歧义候选 **{len(ambig)}** · "
            f"装饰器注册 **{len(decos)}** · {_INBOUND_EMPTY_NOTE}"
        ),
        "",
        "**精确**",
    ]
    if not exact:
        lines.append("- 零静态调用方")
    else:
        lines.extend(_caller_line(hit, known_ids=inbound.known_ids, ambiguous=False) for hit in exact[:_EXACT_SHOW])
        extra = len(exact) - _EXACT_SHOW
        if extra > 0:
            lines.append(f"- +{extra} more")
    lines.extend(["", "**歧义候选（非答案）**"])
    if not ambig:
        lines.append("- （无）")
    else:
        lines.extend(_caller_line(hit, known_ids=inbound.known_ids, ambiguous=True) for hit in ambig[:_AMBIG_SHOW])
        extra = len(ambig) - _AMBIG_SHOW
        if extra > 0:
            lines.append(f"- +{extra} more")
    lines.extend(["", "**静态盲区**"])
    if exact:
        lines.append("- 否（本符号有精确入边）")
    elif decos:
        shown = "、".join(f"`+ {item}`" for item in decos[:3])
        lines.append(f"- ! 精确入度 0 且带装饰器。已扫到注册：{shown}。不是「无调用方」。")
    else:
        lines.append("- 精确入度 0。空列表 ≠ 无运行时调用方")
    near = dups.symbol_labels(symbol_id, record.path)
    if near:
        lines.extend(["", "**近亲 / 重复**", *near])
    lines.append("")
    return lines


def _file_inbound_lines(
    path: str,
    symbol_ids: Sequence[str],
    inbound: _InboundView,
    dups: _DuplicateIndex,
    *,
    has_fresh_blocks: bool,
) -> list[str]:
    lines = dups.file_labels(path)
    # Fresh blocks already carry the full inbound subsection. File-level
    # caller counts stay on uncovered-only files so zero-caller copies remain readable.
    if not has_fresh_blocks:
        callers = inbound.file_exact(path, symbol_ids)
        if callers:
            extra = f" +{len(callers) - _EXACT_SHOW} more" if len(callers) > _EXACT_SHOW else ""
            shown = " · ".join(f"`{item}`" for item in callers[:_EXACT_SHOW])
            lines.append(f"- 入边（文件）：精确 **{len(callers)}** · {shown}{extra}")
        else:
            lines.append("- 入边（文件）：精确 **0** · 零静态调用方")
    return lines


def _dup_index_units(dups: _DuplicateIndex) -> list[PageUnit]:
    rows: list[tuple[str, str, str]] = []
    for index, group in enumerate(dups.byte_groups):
        shown = " · ".join(f"`{path}`" for path in group[:6])
        extra = f" +{len(group) - 6} more" if len(group) > 6 else ""
        rows.append(
            (
                f"dup:byte:{index}",
                "重复能力（字节相同）",
                f"- 重复能力（字节相同）：{shown}{extra}",
            )
        )
    for local, sids in sorted(dups.name_groups.items()):
        paths = sorted({sid.split("::", 1)[0] for sid in sids})
        shown = " · ".join(f"`{path}`" for path in paths[:4])
        extra = f" +{len(paths) - 4} more" if len(paths) > 4 else ""
        rows.append(
            (
                f"dup:name:{local}",
                f"同名/近重实现 {local}",
                f"- 同名/近重实现 `{local}`：{shown}{extra}",
            )
        )
    if not rows:
        return []
    units = [
        PageUnit(
            unit_id="heading:dup",
            kind="heading",
            group_key="dup",
            name="重复能力",
            one_liner="",
            lines=("## 重复能力", ""),
        )
    ]
    for unit_id, name, line in rows:
        units.append(
            PageUnit(
                unit_id=unit_id,
                kind="entry",
                group_key="dup",
                name=name,
                one_liner="并列可见，不合并、不择优。",
                lines=(line,),
            )
        )
    return units


def _render_symbol_block(
    symbol_id: str,
    ledger: SemanticLedger,
    inbound: _InboundView,
    dups: _DuplicateIndex,
    *,
    repo_root: Path,
) -> list[str]:
    record = ledger.symbols[symbol_id]
    explanation = record.explanation
    if explanation is None or not record.is_fresh:
        raise ValueError(f"cannot render non-fresh symbol block: {symbol_id}")
    cycle_peers = "、".join(f"`{peer}`" for peer in record.cycle_peer_ids) or "无"
    inbound_lines = render_inbound_section(
        symbol_id, record, inbound, dups, repo_root=repo_root
    )
    return [
        f"<!-- symbol:{symbol_id} -->",
        f'<a id="{_symbol_anchor(symbol_id)}"></a>',
        f"### `{record.qualified_name}`",
        "",
        f"- Symbol id：`{symbol_id}`",
        f"- 类型：`{record.kind.value}`；源码：`{record.path}:{record.span[0]}-{record.span[1]}`",
        f"- SCC：`{record.scc_id or '未提供'}`；环内同伴：{cycle_peers}",
        f"- 被依赖事实：{_citation_text(explanation.cited_symbol_ids)}",
        "",
        *inbound_lines,
        explanation.text.strip(),
        "",
        f"<!-- end:symbol:{symbol_id} -->",
        "",
    ]


def _build_file_unit(
    path: str,
    module: str,
    ledger: SemanticLedger,
    projection: _Projection,
    layers: Mapping[str, int],
    inbound: _InboundView,
    dups: _DuplicateIndex,
    *,
    repo_root: Path,
) -> PageUnit:
    all_ids = sorted(symbol_id for symbol_id, item in ledger.symbols.items() if item.path == path)
    fresh_ids = [item for item in projection.ordered_fresh_ids if item in set(all_ids)]
    residuals = {item.symbol_id: item.reason for item in ledger.residuals}
    header = [f"## `{path}`", ""]
    file_meta = _file_inbound_lines(
        path, all_ids, inbound, dups, has_fresh_blocks=bool(fresh_ids)
    )
    if file_meta:
        header.extend(file_meta)
        header.append("")
    children: list[PageUnit] = []
    if not all_ids:
        header.extend(["该文件没有可枚举的函数、方法或类符号。", ""])
    elif fresh_ids:
        header.extend(["### 文件语义目录", ""])
        for symbol_id in fresh_ids:
            record = ledger.symbols[symbol_id]
            sentence = _first_sentence(record.explanation.text)  # type: ignore[union-attr]
            header.append(f"- [`{record.qualified_name}`](@@SYM:{symbol_id}@@)：{sentence}")
            children.append(
                PageUnit(
                    unit_id=f"sym:{symbol_id}",
                    kind="symbol",
                    group_key=f"layer:{layers.get(symbol_id, 0)}",
                    name=record.qualified_name,
                    one_liner=sentence,
                    lines=tuple(
                        _render_symbol_block(
                            symbol_id, ledger, inbound, dups, repo_root=repo_root
                        )
                    ),
                    symbol_ids=(symbol_id,),
                    block_count=1,
                )
            )
        header.append("")
    suffix: list[str] = []
    uncovered = [symbol_id for symbol_id in all_ids if not ledger.symbols[symbol_id].is_fresh]
    if uncovered or ledger.files[path].status.value == "residual":
        suffix.extend(["### 未覆盖与 stale 状态", ""])
        if ledger.files[path].reason:
            suffix.append(f"- 文件状态：`{ledger.files[path].status.value}`；{ledger.files[path].reason}")
        for symbol_id in uncovered:
            record = ledger.symbols[symbol_id]
            status = "stale" if record.is_explained else "uncovered"
            reason = residuals.get(symbol_id) or record.invalidation_reason or "未提供原因"
            suffix.append(f"- `{symbol_id}`：{status}；{reason}")
        suffix.append("")
    conflict = projection.conflicts_by_file.get(path)
    if conflict:
        suffix.extend(
            [
                "### 模块归属诊断",
                "",
                f"- 文件内符号提交了多个 module_id：{', '.join(f'`{item}`' for item in conflict)}。"
                f"本投影确定性选择 `{projection.display_by_module[module]}`，文件仍只渲染一次。",
                "",
            ]
        )
    file_layer = min((layers.get(symbol_id, 0) for symbol_id in fresh_ids), default=0)
    return PageUnit(
        unit_id=f"file:{path}",
        kind="file",
        group_key=f"layer:{file_layer}",
        name=path,
        one_liner=f"{len(fresh_ids)} 个 fresh 符号",
        lines=tuple(header),
        children=tuple(children),
        suffix_lines=tuple(suffix),
        symbol_ids=tuple(fresh_ids),
        block_count=len(fresh_ids),
    )


def _build_detail_page(
    module: str,
    ledger: SemanticLedger,
    projection: _Projection,
    layers: Mapping[str, int],
    inbound: _InboundView,
    dups: _DuplicateIndex,
    *,
    parent_title: str,
    repo_root: Path,
) -> Page:
    files = projection.files_by_module[module]
    total, fresh, stale = _module_stats(ledger, projection, module)
    uncovered = total - fresh
    coverage = round(100.0 * fresh / total, 4) if total else 0.0
    display = projection.display_by_module[module]
    file_edges = _file_dependency_edges(ledger, projection, module)
    mermaid = MermaidGenerator().generate_dependency_mermaid(file_edges, scope="module")
    units: list[PageUnit] = [
        PageUnit(
            unit_id=f"{module}:overview",
            kind="fixed",
            group_key="overview",
            name="overview",
            one_liner="",
            lines=(
                "## 模块概览",
                "",
                _module_summary(ledger, projection, module),
                "",
                f"本模块包含 {len(files)} 个文件、{total} 个符号；{fresh} 个 fresh、{stale} 个 stale、"
                f"{uncovered} 个未覆盖，模块覆盖率 {coverage}%。",
            ),
        ),
        PageUnit(
            unit_id=f"{module}:diagram-heading",
            kind="heading",
            group_key="diagram",
            name="文件依赖图",
            one_liner="",
            lines=("## 文件依赖图", ""),
        ),
        PageUnit(
            unit_id=f"{module}:diagram",
            kind="entry",
            group_key="diagram",
            name="文件依赖图",
            one_liner="文件依赖图完整保留，无删减。",
            lines=("```mermaid", mermaid, "```"),
        ),
    ]
    for path in files:
        units.append(
            _build_file_unit(
                path,
                module,
                ledger,
                projection,
                layers,
                inbound,
                dups,
                repo_root=repo_root,
            )
        )
    return Page(
        relpath=f"{module}/{DETAIL_LEAF_NAME}",
        kind="detail",
        title=f"{display} 模块语义详情",
        parent_relpath="INDEX.md",
        parent_title=parent_title,
        units=tuple(units),
    )


def _replace_docs_tree(repo_root: Path, documents: Mapping[Path, str]) -> None:
    target = repo_root / DOCS_RELDIR
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise ValueError(f"{target} must be a real directory when it already exists")
    stage = Path(tempfile.mkdtemp(prefix=".codebase-docs-stage-", dir=repo_root))
    backup = repo_root / f".codebase-docs-backup-{uuid.uuid4().hex}"
    old_moved = False
    try:
        for relative, content in sorted(documents.items(), key=lambda item: item[0].as_posix()):
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")
        if target.exists():
            target.replace(backup)
            old_moved = True
        stage.replace(target)
    except Exception:
        if old_moved and not target.exists() and backup.exists():
            backup.replace(target)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    if backup.exists():
        shutil.rmtree(backup)


def render_semantic_docs(
    repo_root: str | Path,
    ledger: SemanticLedger | Mapping[str, object],
    *,
    graph: nx.DiGraph | None = None,
    budget: LayerBudget | None = None,
    index_max_lines: int | None = None,
    detail_max_lines: int | None = None,
    detail_max_blocks: int | None = None,
    reverse_index: ReverseIndex | Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Write a recursively layered doc tree and return its paths plus hop stats."""

    root = Path(repo_root).expanduser().resolve()
    model = _coerce_ledger(ledger)
    if not root.is_dir():
        raise ValueError(f"repo_root is not a directory: {root}")
    if root != Path(model.repo_root).resolve():
        raise ValueError("repo_root does not match ledger.repo_root")
    if budget is None:
        budget = LayerBudget(
            index_max_lines=index_max_lines if index_max_lines is not None else DEFAULT_INDEX_MAX_LINES,
            detail_max_lines=detail_max_lines if detail_max_lines is not None else DEFAULT_DETAIL_MAX_LINES,
            detail_max_blocks=detail_max_blocks if detail_max_blocks is not None else DEFAULT_DETAIL_MAX_BLOCKS,
        )
    elif any(value is not None for value in (index_max_lines, detail_max_lines, detail_max_blocks)):
        budget = LayerBudget(
            index_max_lines=index_max_lines if index_max_lines is not None else budget.index_max_lines,
            detail_max_lines=detail_max_lines if detail_max_lines is not None else budget.detail_max_lines,
            detail_max_blocks=detail_max_blocks if detail_max_blocks is not None else budget.detail_max_blocks,
            max_nav_ratio=budget.max_nav_ratio,
        )
    inbound = resolve_inbound_view(root, model, reverse_index)
    dups = build_duplicate_index(root, model, inbound)
    projection = _build_projection(model, graph)
    index_page = _build_index_page(root, model, projection, dups)
    layers = assign_dag_layers(tuple(model.symbols), projection.dependency_edges)
    pages = {index_page.relpath: index_page}
    for module in sorted(projection.files_by_module):
        detail = _build_detail_page(
            module,
            model,
            projection,
            layers,
            inbound,
            dups,
            parent_title=index_page.title,
            repo_root=root,
        )
        pages[detail.relpath] = detail
    layered = split_until_fit(pages, budget)
    rendered = finalize_pages(layered, budget)
    hops = measure_symbol_hops(rendered, sorted(model.symbols))
    payload = hops_payload(
        root.name,
        hops,
        docs_root=(root / DOCS_RELDIR).as_posix(),
        ledger=None,
    )
    rendered["HOPS.json"] = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _replace_docs_tree(root, {Path(relpath): text for relpath, text in rendered.items()})
    detail_paths = [
        (root / DOCS_RELDIR / module / DETAIL_LEAF_NAME).as_posix()
        for module in sorted(projection.files_by_module)
        if f"{module}/{DETAIL_LEAF_NAME}" in layered
    ]
    return {
        "index_path": (root / DOCS_RELDIR / "INDEX.md").as_posix(),
        "detail_paths": detail_paths,
        "module_count": len(detail_paths),
        "fresh_symbol_count": model.totals.explained,
        "stale_symbol_count": model.totals.stale,
        "uncovered_symbol_count": model.totals.uncovered,
        "hops_path": (root / DOCS_RELDIR / "HOPS.json").as_posix(),
        "page_count": sum(1 for relpath in rendered if relpath.endswith(".md")),
        "max_page_hops": hops["max_page_hops"],
        "rate_le_3": hops["rate_le_3"],
    }
