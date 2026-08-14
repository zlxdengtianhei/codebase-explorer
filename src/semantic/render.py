"""Deterministically project a semantic ledger into four-level Markdown docs."""

from __future__ import annotations

import hashlib
import re
import shutil
import tempfile
import unicodedata
import uuid
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from src.doc.mermaid import MermaidGenerator
from src.semantic.models import SemanticLedger, SemanticSymbolKind, SemanticSymbolRecord


DOCS_RELDIR = Path(".codebase-docs")
DETAIL_FILENAME = "DETAIL.md"
_GENERATED_HEADER = "<!-- generated:codebase-explorer-semantic-docs -->"
_NON_SLUG = re.compile(r"[^a-z0-9]+")


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


def _symbol_anchor(symbol_id: str) -> str:
    digest = hashlib.sha256(symbol_id.encode("utf-8")).hexdigest()[:16]
    return f"symbol-{digest}"


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


def _render_index(repo_root: Path, ledger: SemanticLedger, projection: _Projection) -> str:
    modules = sorted(projection.files_by_module)
    module_edges = _module_dependency_edges(ledger, projection)
    mermaid = MermaidGenerator().generate_module_diagram(modules, module_edges)
    lines = [
        _GENERATED_HEADER,
        f"# {repo_root.name} 代码语义索引",
        "",
        "这份项目级入口由 semantic ledger 确定性派生。沿模块链接进入文件目录，再读取每个 fresh 函数、方法或类的可寻址解释块。",
        "",
        "## 项目概览",
        "",
        f"- 源码文件：{len(ledger.files)}",
        f"- 符号总数：{ledger.totals.symbols}",
        f"- Fresh 解释：{ledger.totals.explained}",
        f"- Stale 解释：{ledger.totals.stale}",
        f"- 未覆盖符号：{ledger.totals.uncovered}",
        f"- 残差：{ledger.totals.residual}",
        f"- 覆盖率：{ledger.coverage_percent}%",
        "",
        "## 模块",
        "",
    ]
    for module in modules:
        total, fresh, stale = _module_stats(ledger, projection, module)
        display = projection.display_by_module[module]
        summary = _module_summary(ledger, projection, module)
        lines.append(
            f"- [{display}]({module}/{DETAIL_FILENAME})：{len(projection.files_by_module[module])} 个文件，"
            f"{fresh}/{total} fresh，{stale} stale。{summary}"
        )
    lines.extend(["", "## 模块依赖图", "", "```mermaid", mermaid, "```", ""])
    lines.extend(_render_project_gaps(ledger))
    lines.extend(
        [
            "",
            "## 可复算状态",
            "",
            f"- Ledger schema：`{ledger.schema}`",
            f"- Source revision：`{ledger.source_revision}`",
            "- 上层文字只折叠 fresh 函数事实；stale 与 residual 不生成伪解释。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_project_gaps(ledger: SemanticLedger) -> list[str]:
    lines = ["## 未覆盖、stale 与 residual", ""]
    residuals = {item.symbol_id: item.reason for item in ledger.residuals}
    if not ledger.uncovered_symbols:
        return [*lines, "无。当前每个符号都有 fresh 解释。"]
    for symbol_id in ledger.uncovered_symbols:
        record = ledger.symbols[symbol_id]
        status = "stale" if record.is_explained else "uncovered"
        reason = residuals.get(symbol_id) or record.invalidation_reason or "未提供原因"
        lines.append(f"- `{symbol_id}`：{status}；{reason}")
    return lines


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


def _citation_text(
    cited_ids: tuple[str, ...],
    ledger: SemanticLedger,
    projection: _Projection,
    current_module: str,
) -> str:
    if not cited_ids:
        return "无 ledger 内符号引用"
    modules = _symbol_modules(ledger, projection)
    links: list[str] = []
    for cited in cited_ids:
        target_module = modules[cited]
        prefix = "" if target_module == current_module else f"../{target_module}/DETAIL.md"
        links.append(f"[`{cited}`]({prefix}#{_symbol_anchor(cited)})")
    return "、".join(links)


def _render_symbol_block(
    symbol_id: str,
    ledger: SemanticLedger,
    projection: _Projection,
    module: str,
) -> list[str]:
    record = ledger.symbols[symbol_id]
    explanation = record.explanation
    if explanation is None or not record.is_fresh:
        raise ValueError(f"cannot render non-fresh symbol block: {symbol_id}")
    cycle_peers = "、".join(f"`{peer}`" for peer in record.cycle_peer_ids) or "无"
    return [
        f"<!-- symbol:{symbol_id} -->",
        f'<a id="{_symbol_anchor(symbol_id)}"></a>',
        f"### `{record.qualified_name}`",
        "",
        f"- Symbol id：`{symbol_id}`",
        f"- 类型：`{record.kind.value}`；源码：`{record.path}:{record.span[0]}-{record.span[1]}`",
        f"- SCC：`{record.scc_id or '未提供'}`；环内同伴：{cycle_peers}",
        f"- 被依赖事实：{_citation_text(explanation.cited_symbol_ids, ledger, projection, module)}",
        "",
        explanation.text.strip(),
        "",
        f"<!-- end:symbol:{symbol_id} -->",
        "",
    ]


def _render_file_section(
    path: str,
    module: str,
    ledger: SemanticLedger,
    projection: _Projection,
) -> list[str]:
    all_ids = sorted(symbol_id for symbol_id, item in ledger.symbols.items() if item.path == path)
    fresh_ids = [item for item in projection.ordered_fresh_ids if item in set(all_ids)]
    residuals = {item.symbol_id: item.reason for item in ledger.residuals}
    lines = [f"## `{path}`", ""]
    if not all_ids:
        lines.extend(["该文件没有可枚举的函数、方法或类符号。", ""])
    elif fresh_ids:
        lines.extend(["### 文件语义目录", ""])
        for symbol_id in fresh_ids:
            record = ledger.symbols[symbol_id]
            sentence = _first_sentence(record.explanation.text)  # type: ignore[union-attr]
            lines.append(f"- [`{record.qualified_name}`](#{_symbol_anchor(symbol_id)})：{sentence}")
        lines.append("")
    uncovered = [symbol_id for symbol_id in all_ids if not ledger.symbols[symbol_id].is_fresh]
    if uncovered or ledger.files[path].status.value == "residual":
        lines.extend(["### 未覆盖与 stale 状态", ""])
        if ledger.files[path].reason:
            lines.append(f"- 文件状态：`{ledger.files[path].status.value}`；{ledger.files[path].reason}")
        for symbol_id in uncovered:
            record = ledger.symbols[symbol_id]
            status = "stale" if record.is_explained else "uncovered"
            reason = residuals.get(symbol_id) or record.invalidation_reason or "未提供原因"
            lines.append(f"- `{symbol_id}`：{status}；{reason}")
        lines.append("")
    conflict = projection.conflicts_by_file.get(path)
    if conflict:
        lines.extend(
            [
                "### 模块归属诊断",
                "",
                f"- 文件内符号提交了多个 module_id：{', '.join(f'`{item}`' for item in conflict)}。"
                f"本投影确定性选择 `{projection.display_by_module[module]}`，文件仍只渲染一次。",
                "",
            ]
        )
    for symbol_id in fresh_ids:
        lines.extend(_render_symbol_block(symbol_id, ledger, projection, module))
    return lines


def _render_detail(module: str, ledger: SemanticLedger, projection: _Projection) -> str:
    files = projection.files_by_module[module]
    total, fresh, stale = _module_stats(ledger, projection, module)
    uncovered = total - fresh
    coverage = round(100.0 * fresh / total, 4) if total else 0.0
    display = projection.display_by_module[module]
    file_edges = _file_dependency_edges(ledger, projection, module)
    mermaid = MermaidGenerator().generate_dependency_mermaid(file_edges, scope="module")
    lines = [
        _GENERATED_HEADER,
        f"# {display} 模块语义详情",
        "",
        "## 模块概览",
        "",
        _module_summary(ledger, projection, module),
        "",
        f"本模块包含 {len(files)} 个文件、{total} 个符号；{fresh} 个 fresh、{stale} 个 stale、"
        f"{uncovered} 个未覆盖，模块覆盖率 {coverage}%。",
        "",
        "## 文件依赖图",
        "",
        "```mermaid",
        mermaid,
        "```",
        "",
    ]
    for path in files:
        lines.extend(_render_file_section(path, module, ledger, projection))
    return "\n".join(lines).rstrip() + "\n"


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
) -> dict[str, object]:
    """Write byte-stable project/module/file/function docs and return their paths."""

    root = Path(repo_root).expanduser().resolve()
    model = _coerce_ledger(ledger)
    if not root.is_dir():
        raise ValueError(f"repo_root is not a directory: {root}")
    if root != Path(model.repo_root).resolve():
        raise ValueError("repo_root does not match ledger.repo_root")
    projection = _build_projection(model, graph)
    documents: dict[Path, str] = {Path("INDEX.md"): _render_index(root, model, projection)}
    for module in sorted(projection.files_by_module):
        documents[Path(module) / DETAIL_FILENAME] = _render_detail(module, model, projection)
    _replace_docs_tree(root, documents)
    detail_paths = [
        (root / DOCS_RELDIR / module / DETAIL_FILENAME).as_posix()
        for module in sorted(projection.files_by_module)
    ]
    return {
        "index_path": (root / DOCS_RELDIR / "INDEX.md").as_posix(),
        "detail_paths": detail_paths,
        "module_count": len(detail_paths),
        "fresh_symbol_count": model.totals.explained,
        "stale_symbol_count": model.totals.stale,
        "uncovered_symbol_count": model.totals.uncovered,
    }
