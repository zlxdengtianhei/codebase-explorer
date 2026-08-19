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
from dataclasses import dataclass, replace
from pathlib import Path

import networkx as nx

from src.doc.mermaid import MermaidGenerator
from src.graph.reverse_edges import (
    ReverseIndex,
    ReversePayloadV3,
    ReverseResolution,
    build_reverse_index,
    validate_reverse_payload,
)
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

GROUPING_L2 = "l2_partition"
GROUPING_CONE = "feature_cone_module_id"
DIRSEED_HUMAN = "公共面到不了，按目录回退"
LEVEL_ARCHITECTURE = "整体架构"
LEVEL_MODULE = "功能模块"
LEVEL_CODE = "具体代码"
_PARTITION_RELATIVE = (
    Path(".codebase-analysis") / "partition.json",
    Path("partition.json"),
)


@dataclass(frozen=True)
class _ClusterPageMeta:
    cluster_id: str
    seed_kind: str
    kind: str
    fallback_reason: str | None
    reason_codes: tuple[tuple[str, str], ...]
    member_paths: tuple[str, ...]

    @property
    def is_dirseed(self) -> bool:
        return (
            self.seed_kind == "directory"
            or self.kind == "directory_fallback"
            or self.cluster_id.startswith("dirseed--")
            or bool(self.fallback_reason)
        )


@dataclass(frozen=True)
class _Projection:
    module_by_file: Mapping[str, str]
    display_by_module: Mapping[str, str]
    files_by_module: Mapping[str, tuple[str, ...]]
    conflicts_by_file: Mapping[str, tuple[str, ...]]
    ordered_fresh_ids: tuple[str, ...]
    dependency_edges: tuple[tuple[str, str], ...]
    grouping_mode: str = GROUPING_CONE
    grouping_reason: str = ""
    cluster_meta_by_module: Mapping[str, _ClusterPageMeta] | None = None


def discover_partition_path(repo_root: str | Path) -> Path | None:
    """Return the first existing production partition.json under repo_root."""

    root = Path(repo_root)
    for relative in _PARTITION_RELATIVE:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return None


def discover_names_path(
    repo_root: str | Path,
    partition_path: Path | None = None,
) -> Path | None:
    """Optional L2 name map sitting next to partition.json."""

    candidates: list[Path] = []
    if partition_path is not None:
        candidates.append(partition_path.with_name("l2_result.json"))
        name = partition_path.name
        if name.startswith("partition_") and name.endswith(".json"):
            candidates.append(
                partition_path.with_name("l2_result_" + name[len("partition_") :])
            )
    candidates.append(Path(repo_root) / ".codebase-analysis" / "l2_result.json")
    for path in candidates:
        if path.is_file():
            return path
    return None


def resolve_partition_source(
    repo_root: Path,
    *,
    partition_path: str | Path | None,
    consume_partition: bool,
) -> tuple[Path | None, str, str]:
    """Pick L2 vs feature-cone grouping. Fallback is an explicit named branch."""

    if not consume_partition:
        reason = (
            "模块划分来源：feature-cone `module_id`。"
            "这是显式回退分支：消费开关 `consume_partition=false`，本树不读 L2 分区。"
        )
        return None, GROUPING_CONE, reason
    explicit = Path(partition_path) if partition_path is not None else None
    if explicit is not None:
        if explicit.is_file():
            reason = (
                "模块划分来源：L2 共享签名分区。"
                f"本树已消费 `{explicit.name}`，页面按簇组织，不再按 feature-cone `module_id`。"
            )
            return explicit, GROUPING_L2, reason
        reason = (
            "模块划分来源：feature-cone `module_id`。"
            "这是显式回退分支：调用方指定了 partition_path，但该路径不是可读文件。"
        )
        return None, GROUPING_CONE, reason
    discovered = discover_partition_path(repo_root)
    if discovered is not None:
        reason = (
            "模块划分来源：L2 共享签名分区。"
            f"本树已消费 `{discovered.as_posix()}`，页面按簇组织，不再按 feature-cone `module_id`。"
        )
        return discovered, GROUPING_L2, reason
    reason = (
        "模块划分来源：feature-cone `module_id`。"
        "这是显式回退分支：仓库内没有 partition.json，未消费 L2 分区。"
    )
    return None, GROUPING_CONE, reason


def _load_partition_meta(partition_path: Path) -> dict[str, _ClusterPageMeta]:
    """Read seed_kind / fallback_reason / reason_code that Cluster does not carry."""

    data = json.loads(partition_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    absorbed: dict[str, tuple[str, str]] = {}
    for key in ("dirseed_absorbed", "unassigned_before_dirseed", "unassigned"):
        rows = data.get(key) or ()
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            path = str(row.get("path") or "").strip()
            if not path or path in absorbed:
                continue
            code = str(row.get("reason_code") or "").strip()
            human = str(row.get("reason") or "").strip()
            absorbed[path] = (code, human)
    out: dict[str, _ClusterPageMeta] = {}
    for raw in data.get("candidates") or ():
        if not isinstance(raw, dict):
            continue
        cluster_id = str(raw.get("cluster_id") or "").strip()
        files = tuple(
            str(item) for item in (raw.get("member_paths") or ()) if str(item).strip()
        )
        if not cluster_id or not files:
            continue
        codes: list[tuple[str, str]] = []
        seen: set[str] = set()
        for path in files:
            pair = absorbed.get(path)
            if pair is None or not pair[0] or pair[0] in seen:
                continue
            seen.add(pair[0])
            codes.append(pair)
        fallback = raw.get("fallback_reason")
        out[cluster_id] = _ClusterPageMeta(
            cluster_id=cluster_id,
            seed_kind=str(raw.get("seed_kind") or ""),
            kind=str(raw.get("kind") or ""),
            fallback_reason=str(fallback) if fallback else None,
            reason_codes=tuple(codes),
            member_paths=files,
        )
    return out


def _format_reason_codes(codes: Sequence[tuple[str, str]]) -> str:
    if not codes:
        return ""
    parts: list[str] = []
    for code, human in codes:
        if human:
            parts.append(f"`{code}`（{human}）")
        else:
            parts.append(f"`{code}`")
    return "reason_code：" + "；".join(parts)


def _dirseed_sentence(meta: _ClusterPageMeta) -> str:
    codes = _format_reason_codes(meta.reason_codes)
    if codes:
        return f"{DIRSEED_HUMAN}。{codes}。"
    return f"{DIRSEED_HUMAN}。"


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


def _projection_from_module_id(
    ledger: SemanticLedger,
    graph: nx.DiGraph | None,
    *,
    grouping_reason: str,
) -> _Projection:
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
        grouping_mode=GROUPING_CONE,
        grouping_reason=grouping_reason,
        cluster_meta_by_module={},
    )


def _projection_from_partition(
    ledger: SemanticLedger,
    graph: nx.DiGraph | None,
    *,
    partition_path: Path,
    names_path: Path | None,
    grouping_reason: str,
) -> _Projection:
    from src.synthesis.variant_b.clusters import build_clusters

    edges = set(_dependency_edges(ledger, graph))
    clusters = build_clusters(
        ledger,
        edges,
        partition_path=partition_path,
        names_path=names_path,
    )
    meta_by_id = _load_partition_meta(partition_path)
    module_by_file: dict[str, str] = {}
    display_by_module: dict[str, str] = {}
    files_by_module: dict[str, tuple[str, ...]] = {}
    cluster_meta_by_module: dict[str, _ClusterPageMeta] = {}
    for cluster in clusters:
        slug = cluster.slug
        display_by_module[slug] = cluster.display
        files_by_module[slug] = tuple(cluster.files)
        loaded = meta_by_id.get(cluster.cluster_id)
        cluster_meta_by_module[slug] = loaded or _ClusterPageMeta(
            cluster_id=cluster.cluster_id,
            seed_kind="",
            kind="",
            fallback_reason=None,
            reason_codes=(),
            member_paths=tuple(cluster.files),
        )
        for path in cluster.files:
            module_by_file.setdefault(path, slug)
    for path in ledger.files:
        module_by_file.setdefault(path, "unclassified")
    if any(owner == "unclassified" for owner in module_by_file.values()):
        leftovers = tuple(
            sorted(path for path, owner in module_by_file.items() if owner == "unclassified")
        )
        files_by_module.setdefault("unclassified", leftovers)
        display_by_module.setdefault("unclassified", "unclassified")
    return _Projection(
        module_by_file=module_by_file,
        display_by_module=display_by_module,
        files_by_module=files_by_module,
        conflicts_by_file={},
        ordered_fresh_ids=_ordered_fresh_ids(ledger),
        dependency_edges=_dependency_edges(ledger, graph),
        grouping_mode=GROUPING_L2,
        grouping_reason=grouping_reason,
        cluster_meta_by_module=cluster_meta_by_module,
    )


def _build_projection(
    ledger: SemanticLedger,
    graph: nx.DiGraph | None,
    *,
    partition_path: Path | None,
    names_path: Path | None,
    grouping_mode: str,
    grouping_reason: str,
) -> _Projection:
    if grouping_mode == GROUPING_L2 and partition_path is not None:
        return _projection_from_partition(
            ledger,
            graph,
            partition_path=partition_path,
            names_path=names_path,
            grouping_reason=grouping_reason,
        )
    return _projection_from_module_id(ledger, graph, grouping_reason=grouping_reason)


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
            lines=_index_intro_lines(projection),
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
        meta = (projection.cluster_meta_by_module or {}).get(module)
        if meta is not None and meta.is_dirseed:
            summary = _dirseed_sentence(meta) + summary
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
    runtime_exact: Mapping[str, tuple[_CallerHit, ...]]
    lexical_base: Mapping[str, tuple[_CallerHit, ...]]
    override_candidates: Mapping[str, tuple[_CallerHit, ...]]
    decorated: Mapping[str, tuple[str, ...]]
    known_ids: frozenset[str]

    def runtime_exact_of(self, symbol_id: str) -> tuple[_CallerHit, ...]:
        return self.runtime_exact.get(symbol_id, ())

    def lexical_base_of(self, symbol_id: str) -> tuple[_CallerHit, ...]:
        return self.lexical_base.get(symbol_id, ())

    def override_of(self, symbol_id: str) -> tuple[_CallerHit, ...]:
        return self.override_candidates.get(symbol_id, ())

    def decorators_of(self, symbol_id: str) -> tuple[str, ...]:
        return self.decorated.get(symbol_id, ())

    def file_exact(self, path: str, symbol_ids: Sequence[str]) -> tuple[str, ...]:
        seen: list[str] = []
        for symbol_id in symbol_ids:
            for hit in self.runtime_exact_of(symbol_id):
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


def _hits_from_rows(rows: Sequence[object], resolution: ReverseResolution) -> tuple[_CallerHit, ...]:
    hits: list[_CallerHit] = []
    for row in rows:
        if not hasattr(row, "resolution") or row.resolution is not resolution:
            continue
        caller = str(row.caller_id or "")
        if not caller:
            continue
        candidates = tuple(str(item) for item in row.candidate_target_ids)
        hits.append(
            _CallerHit(
                caller_id=caller,
                kind="call",
                line=row.line,
                candidates=candidates,
            )
        )
    return _unique_hits(hits)


def inbound_view_from_reverse_index(index: ReverseIndex) -> _InboundView:
    runtime_exact: dict[str, tuple[_CallerHit, ...]] = {}
    lexical_base: dict[str, tuple[_CallerHit, ...]] = {}
    override_candidates: dict[str, tuple[_CallerHit, ...]] = {}
    decorated: dict[str, tuple[str, ...]] = {}
    for symbol_id, defn in index.symbols.items():
        answer = index.callers_of(symbol_id)
        runtime_exact[symbol_id] = _unique_hits(
            _hits_from_rows(answer.runtime_exact, ReverseResolution.RUNTIME_EXACT)
        )
        lexical_base[symbol_id] = _unique_hits(
            _hits_from_rows(answer.lexical_base, ReverseResolution.LEXICAL_BASE)
        )
        override_candidates[symbol_id] = _unique_hits(
            _hits_from_rows(answer.override_candidates, ReverseResolution.OVERRIDE_CANDIDATE)
        )
        if defn.decorators:
            decorated[symbol_id] = tuple(defn.decorators)
    return _InboundView(
        runtime_exact=runtime_exact,
        lexical_base=lexical_base,
        override_candidates=override_candidates,
        decorated=decorated,
        known_ids=frozenset(index.symbols),
    )


def inbound_view_from_payload(payload: Mapping[str, object]) -> _InboundView:
    model: ReversePayloadV3 = validate_reverse_payload(payload)
    runtime_exact: dict[str, tuple[_CallerHit, ...]] = {}
    lexical_base: dict[str, tuple[_CallerHit, ...]] = {}
    override_candidates: dict[str, tuple[_CallerHit, ...]] = {}
    decorated: dict[str, tuple[str, ...]] = {}
    for symbol_id, rows in model.by_callee_symbol.items():
        runtime_exact[symbol_id] = _unique_hits(
            _hits_from_rows(rows, ReverseResolution.RUNTIME_EXACT)
        )
        lexical_base[symbol_id] = _unique_hits(
            _hits_from_rows(rows, ReverseResolution.LEXICAL_BASE)
        )
        override_candidates[symbol_id] = _unique_hits(
            _hits_from_rows(rows, ReverseResolution.OVERRIDE_CANDIDATE)
        )
    for symbol_id, body in model.symbols.items():
        if body.decorators:
            decorated[symbol_id] = tuple(body.decorators)
    return _InboundView(
        runtime_exact=runtime_exact,
        lexical_base=lexical_base,
        override_candidates=override_candidates,
        decorated=decorated,
        known_ids=frozenset(model.symbols),
    )


def _empty_inbound() -> _InboundView:
    return _InboundView(
        runtime_exact={},
        lexical_base={},
        override_candidates={},
        decorated={},
        known_ids=frozenset(),
    )


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
            if inbound.runtime_exact_of(sid):
                continue
            if inbound.decorators_of(sid) or _source_decorators(repo_root, record):
                continue
            live_sibling = False
            for other_id, other in records.items():
                if other_id == sid:
                    continue
                if not inbound.runtime_exact_of(other_id):
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
    runtime_exact = inbound.runtime_exact_of(symbol_id)
    lexical_base = inbound.lexical_base_of(symbol_id)
    override_candidates = inbound.override_of(symbol_id)
    decos = _symbol_decorators(repo_root, record, symbol_id, inbound)
    lines = [
        "#### 入边（静态）",
        "",
        (
            f"- runtime exact **{len(runtime_exact)}** · lexical base **{len(lexical_base)}** · "
            f"override candidates **{len(override_candidates)}** · "
            f"装饰器注册 **{len(decos)}** · {_INBOUND_EMPTY_NOTE}"
        ),
        "",
        "**精确**",
    ]
    lines.append("**runtime exact**")
    if not runtime_exact:
        lines.append("- 零静态调用方")
    else:
        lines.extend(
            _caller_line(hit, known_ids=inbound.known_ids, ambiguous=False)
            for hit in runtime_exact[:_EXACT_SHOW]
        )
        extra = len(runtime_exact) - _EXACT_SHOW
        if extra > 0:
            lines.append(f"- +{extra} more")
    lines.extend(["", "**词法基类（非精确答案）**", "**lexical base**"])
    if not lexical_base:
        lines.append("- （无）")
    else:
        lines.extend(
            _caller_line(hit, known_ids=inbound.known_ids, ambiguous=True)
            for hit in lexical_base[:_AMBIG_SHOW]
        )
        extra = len(lexical_base) - _AMBIG_SHOW
        if extra > 0:
            lines.append(f"- +{extra} more")
    lines.extend(["", "**歧义候选（非答案）**", "**override candidates (non-answer)**"])
    if not override_candidates:
        lines.append("- （无）")
    else:
        lines.extend(
            _caller_line(hit, known_ids=inbound.known_ids, ambiguous=True)
            for hit in override_candidates[:_AMBIG_SHOW]
        )
        extra = len(override_candidates) - _AMBIG_SHOW
        if extra > 0:
            lines.append(f"- +{extra} more")
    lines.extend(["", "**静态盲区**", "**static blind spot**"])
    if runtime_exact:
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
    header = [
        f"## `{path}`",
        "",
        f"当前粒度：**{LEVEL_CODE}**。上级是本页的功能模块；再上一级是整体架构（根 INDEX）。",
        "",
    ]
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
    meta = (projection.cluster_meta_by_module or {}).get(module)
    overview_lines: list[str] = [
        "## 模块概览",
        "",
        _module_summary(ledger, projection, module),
        "",
        f"本模块包含 {len(files)} 个文件、{total} 个符号；{fresh} 个 fresh、{stale} 个 stale、"
        f"{uncovered} 个未覆盖，模块覆盖率 {coverage}%。",
    ]
    if meta is not None:
        overview_lines.extend(
            [
                "",
                f"<!-- cluster:{meta.cluster_id} -->",
                f"- 簇 id：`{meta.cluster_id}`",
            ]
        )
        if meta.is_dirseed:
            overview_lines.extend(
                [
                    "",
                    "## 为什么这些文件在一起",
                    "",
                    "这些文件不是按公共面可达闭包切出来的功能组。"
                    f"{DIRSEED_HUMAN}，所以它们才出现在同一页。",
                    f"- {_dirseed_sentence(meta)}",
                ]
            )
            if meta.fallback_reason:
                overview_lines.append(f"- 分区记录的回退说明：{meta.fallback_reason}")
    units: list[PageUnit] = [
        PageUnit(
            unit_id=f"{module}:overview",
            kind="fixed",
            group_key="overview",
            name="overview",
            one_liner="",
            lines=tuple(overview_lines),
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


def _index_intro_lines(projection: _Projection) -> tuple[str, ...]:
    lines = [
        "这份项目级入口由 semantic ledger 确定性派生。"
        "沿模块链接进入文件目录，再读取每个 fresh 函数、方法或类的可寻址解释块。"
        f"本页处在：**{LEVEL_ARCHITECTURE}**（分级：{LEVEL_CODE} / {LEVEL_MODULE} / {LEVEL_ARCHITECTURE}）。"
        f"上级：无。下级：{LEVEL_MODULE}页（下方模块入口）。再下一层是各模块页里的{LEVEL_CODE}。"
        f"{projection.grouping_reason}"
    ]
    if projection.grouping_mode == GROUPING_L2 and "unclassified" not in projection.files_by_module:
        lines.append(
            f"无未归类文件。{DIRSEED_HUMAN}；这些文件进了 dirseed 簇，原 reason_code 写在对应功能模块页。"
        )
    return tuple(lines)


def _hierarchy_unit(page: Page, child_relpaths: Sequence[str]) -> PageUnit:
    name = Path(page.relpath).name
    if page.parent_relpath is None:
        level = LEVEL_ARCHITECTURE
        parent_txt = (
            f"上级：无。本页是文档树根，处在「{LEVEL_CODE} → {LEVEL_MODULE} → {LEVEL_ARCHITECTURE}」的{LEVEL_ARCHITECTURE}。"
        )
        child_txt = (
            f"下级：{LEVEL_MODULE}页（本页「模块」列表中的链接）。再下一层是各模块页里的{LEVEL_CODE}（文件与符号块）。"
        )
    elif name.startswith("PART-"):
        level = LEVEL_CODE
        parent_txt = (
            f"上级：{LEVEL_MODULE}（[{page.parent_title}](@@PAGE:{page.parent_relpath}@@)）。"
            f"再上一级是{LEVEL_ARCHITECTURE}（根 INDEX）。"
        )
        child_txt = f"下级：本页内的{LEVEL_CODE}（文件标题与符号解释块）。没有更细的文档页。"
    elif page.kind == "detail" or name == DETAIL_LEAF_NAME:
        level = LEVEL_MODULE
        parent_txt = (
            f"上级：{LEVEL_ARCHITECTURE}（[{page.parent_title}](@@PAGE:{page.parent_relpath}@@)）。"
        )
        if child_relpaths:
            child_txt = (
                f"下级：分页后的{LEVEL_CODE}子页，以及本页内尚未下沉的{LEVEL_CODE}（文件与符号块）。"
            )
        else:
            child_txt = f"下级：本页内的{LEVEL_CODE}（各文件标题与符号解释块）。没有再下一层文档页。"
    else:
        level = LEVEL_MODULE
        parent_txt = (
            f"上级：[{page.parent_title}](@@PAGE:{page.parent_relpath}@@)"
            f"（{LEVEL_ARCHITECTURE}或其上一层索引）。"
        )
        child_txt = f"下级：{LEVEL_MODULE}详情页或更细的索引页。"
    lines = (
        "## 当前层级",
        "",
        f"本页处在：**{level}**（分级：{LEVEL_CODE} / {LEVEL_MODULE} / {LEVEL_ARCHITECTURE}）。",
        parent_txt,
        child_txt,
        "",
    )
    return PageUnit(
        unit_id=f"{page.relpath}:hierarchy",
        kind="fixed",
        group_key="fixed",
        name="hierarchy",
        one_liner="",
        lines=lines,
    )


def _annotate_hierarchy(pages: Mapping[str, Page]) -> dict[str, Page]:
    children: dict[str, list[str]] = {}
    for page in pages.values():
        if page.parent_relpath:
            children.setdefault(page.parent_relpath, []).append(page.relpath)
    for relpath in children:
        children[relpath].sort()
    out: dict[str, Page] = {}
    for relpath, page in pages.items():
        if any(unit.unit_id.endswith(":hierarchy") for unit in page.units):
            out[relpath] = page
            continue
        if page.parent_relpath is None:
            out[relpath] = page
            continue
        unit = _hierarchy_unit(page, children.get(relpath, ()))
        out[relpath] = replace(page, units=(unit, *page.units))
    return out


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
    partition_path: str | Path | None = None,
    names_path: str | Path | None = None,
    consume_partition: bool = True,
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
    chosen_partition, grouping_mode, grouping_reason = resolve_partition_source(
        root,
        partition_path=partition_path,
        consume_partition=consume_partition,
    )
    resolved_names = Path(names_path) if names_path is not None else discover_names_path(
        root, chosen_partition
    )
    projection = _build_projection(
        model,
        graph,
        partition_path=chosen_partition,
        names_path=resolved_names,
        grouping_mode=grouping_mode,
        grouping_reason=grouping_reason,
    )
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
    pages = _annotate_hierarchy(pages)
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
        "grouping_mode": projection.grouping_mode,
        "partition_consumed": projection.grouping_mode == GROUPING_L2,
        "grouping_reason": projection.grouping_reason,
    }
