"""Markdown pages for the 0-call evidence map."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from src.doc.mermaid import FlowStep, MermaidGenerator
from src.semantic.models import SemanticLedger
from src.synthesis.variant_b.nest import ClusterLayout, detail_relpath
from src.synthesis.variant_b.surface import PublicSurface, SurfaceBinding
from src.synthesis.variant_b.text import behavior, clip_visible_prefix, one_liner, package_docstring, symbol_anchor, tail
from src.synthesis.variant_b.types import (
    DETAIL_LINE_LIMIT,
    FILE_LEVEL_NOTE,
    GENERATED_HEADER,
    INDEX_LINE_LIMIT,
    OVERLAY_DIR,
    OVERLAY_PER_PAGE,
    Cluster,
    FlowTraceSet,
    NamedTrace,
    href_token,
    target_close,
    target_open,
)


def md_link(label: str, kind: str, key: str) -> str:
    return f"[{label}]({href_token(kind, key)})"


def _page_wrap(relpath: str, lines: list[str]) -> list[str]:
    return [target_open("page", relpath), *lines, target_close("page", relpath)]


def _binding_key(item: SurfaceBinding) -> str:
    return f"{item.path}::{item.name}"


def overlay_binding_key(item: SurfaceBinding) -> str:
    host = item.origin_path or item.path
    return f"{host}::{item.name}"


def overlay_items(surface: PublicSurface) -> list[SurfaceBinding]:
    return [item for item in surface.index_rows() if not item.resolved_symbol_ids]


def overlay_keys(surface: PublicSurface) -> set[str]:
    return {overlay_binding_key(item) for item in overlay_items(surface)}


def resolve_surface_target(
    item: SurfaceBinding,
    surface: PublicSurface,
) -> tuple[str, str]:
    if item.resolved_symbol_ids:
        return "symbol", item.resolved_symbol_ids[0]
    return "binding", overlay_binding_key(item)


def surface_link_label(item: SurfaceBinding, kind: str) -> str:
    if kind == "symbol":
        return f"`{item.name}`"
    shown = Path(item.origin_path or item.path).name
    return f"`{item.name}` → {shown}"


def _needed_bindings(
    surface: PublicSurface,
    files: tuple[str, ...],
) -> list[SurfaceBinding]:
    wanted = set(files)
    skip = overlay_keys(surface)
    rows: dict[str, SurfaceBinding] = {}
    for item in surface.bindings:
        if item.name.startswith("_") or item.name == "*":
            continue
        if item.resolved_symbol_ids:
            continue
        key = _binding_key(item)
        overlay_key = overlay_binding_key(item)
        if key in skip or overlay_key in skip:
            continue
        host = item.origin_path or item.path
        if item.kind == "assign" and item.path in wanted:
            rows[key] = item
        elif host in wanted and item.kind != "assign":
            rows.setdefault(key, item)
        elif item.path in wanted and not item.resolved_symbol_ids:
            rows.setdefault(key, item)
    return [rows[key] for key in sorted(rows)]


def _trace_for(cluster_id: str, traces: FlowTraceSet) -> NamedTrace | None:
    for item in traces.traces:
        if item.cluster_id == cluster_id:
            return item
    return None


def _chain(trace: NamedTrace) -> str:
    if not trace.ordered_symbol_ids:
        return "（无调用迹）"
    return " → ".join(f"`{tail(symbol_id)}`" for symbol_id in trace.ordered_symbol_ids)


def _best_trace(traces: FlowTraceSet) -> NamedTrace | None:
    scored = [item for item in traces.traces if item.ordered_symbol_ids]
    if not scored:
        return None
    return max(
        scored,
        key=lambda item: (
            len(item.ordered_symbol_ids),
            item.selection.get("seed_pagerank", 0.0) if isinstance(item.selection, dict) else 0.0,
            item.trace_id,
        ),
    )


def render_root_index(
    repo_root: Path,
    ledger: SemanticLedger,
    surface: PublicSurface,
    layouts: tuple[ClusterLayout, ...],
    traces: FlowTraceSet,
) -> list[str]:
    rows = surface.index_rows()
    links = []
    for item in rows:
        kind, key = resolve_surface_target(item, surface)
        links.append(md_link(surface_link_label(item, kind), kind, key))
    surface_lines: list[str] = []
    for index in range(0, len(links), 6):
        surface_lines.append(" · ".join(links[index : index + 6]))
    if not surface_lines:
        surface_lines = ["（当前仓库没有从 `__init__.py` 抽到公共名。）"]

    docstring = package_docstring(repo_root)
    public_intro = ""
    repo_name = repo_root.name.lower()
    for item in surface.index_rows():
        if item.name.lower() != repo_name or not item.resolved_symbol_ids:
            continue
        record = ledger.symbols.get(item.resolved_symbol_ids[0])
        if record is not None and record.is_fresh:
            public_intro = one_liner(record)
            break
    if not public_intro:
        for item in surface.index_rows():
            if not item.resolved_symbol_ids:
                continue
            record = ledger.symbols.get(item.resolved_symbol_ids[0])
            if record is not None and record.kind.value == "class" and record.is_fresh:
                public_intro = one_liner(record)
                break
    identity = docstring or public_intro or "确定性证据地图：公共面 + 每簇一条命名迹 + 行区间锚点。"
    lines = [
        GENERATED_HEADER,
        f"# {repo_root.name}",
        "",
        identity,
        "",
        "综合层 0 次 LLM。名字链到实现行区间；迹沿调用边现算，节点带台账首句。",
        "",
        "## 公共面",
        "",
        "包导出名字。绑定不是符号分母。",
        "",
        *surface_lines,
        "",
        "## 功能",
        "",
    ]
    for layout in layouts:
        cluster = layout.cluster
        dest = layout.index_relpath or detail_relpath(layout, layout.buckets[0])
        trace = _trace_for(cluster.cluster_id, traces)
        chain = _chain(trace) if trace else "（无迹）"
        extra = ""
        if cluster.purpose:
            extra = " — " + clip_visible_prefix(cluster.purpose, 110)
        elif trace and trace.seed_symbol_id and trace.seed_symbol_id in ledger.symbols:
            extra = " — " + clip_visible_prefix(one_liner(ledger.symbols[trace.seed_symbol_id]), 110)
        lines.append(
            f"- {md_link(cluster.display, 'page', dest)}：{cluster.n_files} 文件 / "
            f"{cluster.n_symbols} 符号 · {chain}{extra}"
        )
    primary = _best_trace(traces)
    lines.extend(["", "## 主迹", ""])
    if primary is None:
        lines.extend(["（没有抽出命名迹。）", ""])
    else:
        lines.append(f"### {primary.title}")
        lines.append("")
        lines.append(_chain(primary))
        lines.append("")
        for symbol_id in primary.ordered_symbol_ids:
            record = ledger.symbols[symbol_id]
            sentence = one_liner(record) if record.is_fresh else "stale/uncovered"
            lines.append(
                f"- {md_link(f'`{record.qualified_name}`', 'symbol', symbol_id)}：{sentence}"
            )
        if primary.residual:
            lines.append(f"- residual：{primary.residual}")
        lines.append("")

    lines.extend(["## 残差", ""])
    residuals = [layout for layout in layouts if layout.cluster.unassigned_reason]
    if residuals:
        for layout in residuals:
            dest = layout.index_relpath or detail_relpath(layout, layout.buckets[0])
            lines.append(
                f"- {md_link(layout.cluster.display, 'page', dest)}："
                f"{layout.cluster.unassigned_reason}"
            )
    else:
        lines.append("无未归类文件。每个文件都进了一个簇。")
    if ledger.uncovered_symbols:
        lines.append("")
        for symbol_id in ledger.uncovered_symbols[:12]:
            record = ledger.symbols[symbol_id]
            lines.append(f"- `{symbol_id}`：未 fresh；{record.invalidation_reason or '见台账'}")
    lines.extend(
        [
            "",
            "## 可复算",
            "",
            f"- Ledger `{ledger.schema}` · revision `{ledger.source_revision[:18]}…`",
            f"- 簇 {len(layouts)} · 迹 {sum(1 for item in traces.traces if item.ordered_symbol_ids)}",
            "- 综合层 LLM 调用：0",
        ]
    )
    wrapped = _page_wrap("INDEX.md", lines)
    if len(wrapped) > INDEX_LINE_LIMIT:
        wrapped = _shrink_index(wrapped)
    return wrapped


def _shrink_index(lines: list[str]) -> list[str]:
    """Drop main-trace node bullets first so INDEX stays ≤150. Names stay."""

    body = list(lines)
    while len(body) > INDEX_LINE_LIMIT:
        drop_at = None
        in_main = False
        for index, line in enumerate(body):
            if line == "## 主迹":
                in_main = True
                continue
            if in_main and line.startswith("## "):
                in_main = False
            if in_main and line.startswith("- [`"):
                drop_at = index
        if drop_at is None:
            break
        del body[drop_at]
    return body[:INDEX_LINE_LIMIT]


def _trace_block(
    trace: NamedTrace,
    ledger: SemanticLedger,
    *,
    mermaid: bool,
) -> list[str]:
    lines = [
        f"### 主迹 · {trace.title}",
        "",
        _chain(trace),
        "",
    ]
    if mermaid and len(trace.ordered_symbol_ids) >= 2:
        steps: list[FlowStep] = []
        ordered = list(trace.ordered_symbol_ids)
        for index, symbol_id in enumerate(ordered):
            nxt: tuple[str, ...] = ()
            if index + 1 < len(ordered):
                nxt = (f"{index + 1}_{tail(ordered[index + 1])}",)
            steps.append(FlowStep(id=f"{index}_{tail(symbol_id)}", label=tail(symbol_id), next_ids=nxt))
        diagram = MermaidGenerator().generate_flow_diagram(steps)
        lines.extend(["```mermaid", diagram, "```", ""])
    for symbol_id in trace.ordered_symbol_ids:
        record = ledger.symbols[symbol_id]
        sentence = one_liner(record) if record.is_fresh else "stale/uncovered"
        lines.append(
            f"- {md_link(f'`{record.qualified_name}`', 'symbol', symbol_id)}：{sentence}"
        )
    if trace.residual:
        lines.append(f"- residual：{trace.residual}")
    lines.append("")
    return lines


def render_cluster_index(
    layout: ClusterLayout,
    ledger: SemanticLedger,
    traces: FlowTraceSet,
    parent: str = "INDEX.md",
) -> list[str]:
    cluster = layout.cluster
    relpath = layout.index_relpath or f"{cluster.slug}/INDEX.md"
    trace = _trace_for(cluster.cluster_id, traces)
    lines = [
        GENERATED_HEADER,
        f"# {cluster.display}",
        "",
        f"↑ {md_link('根 INDEX', 'page', parent)}",
        "",
        f"{cluster.n_files} 个文件，{cluster.n_symbols} 个符号，"
        f"{cluster.n_layers} 个 DAG 层。升深原因：{layout.reason}",
        "",
    ]
    if cluster.purpose:
        lines.extend([cluster.purpose, ""])
    if trace:
        lines.extend(_trace_block(trace, ledger, mermaid=len(trace.ordered_symbol_ids) >= 3))
    lines.extend(["## 下层", ""])
    for bucket in layout.buckets:
        dest = detail_relpath(layout, bucket)
        lines.append(
            f"- {md_link(bucket.name, 'page', dest)}："
            f"{len(bucket.files)} 文件 / {len(bucket.symbol_ids)} 符号"
        )
    lines.extend(["", "## 文件", ""])
    for path in cluster.files:
        lines.append(f"- `{path}`")
    if cluster.unassigned_reason:
        lines.extend(["", "## 残差", "", cluster.unassigned_reason, ""])
    wrapped = _page_wrap(relpath, lines)
    if len(wrapped) > INDEX_LINE_LIMIT:
        # Keep header + trace + 下层; drop the file roster.
        kept: list[str] = []
        skipping = False
        for line in wrapped:
            if line == "## 文件":
                skipping = True
                continue
            if skipping and line.startswith("## "):
                skipping = False
            if not skipping:
                kept.append(line)
        wrapped = kept[:INDEX_LINE_LIMIT]
    return wrapped


def _symbol_unit(symbol_id: str, ledger: SemanticLedger) -> list[str]:
    record = ledger.symbols[symbol_id]
    text = behavior(record) if record.is_fresh else "stale/uncovered"
    cited = ""
    if record.explanation and record.explanation.cited_symbol_ids:
        bits = [
            md_link(f"`{tail(cited_id)}`", "symbol", cited_id)
            for cited_id in record.explanation.cited_symbol_ids[:8]
        ]
        cited = "依赖 " + "、".join(bits)
    body = text.splitlines() or [text]
    return [
        target_open("symbol", symbol_id),
        f"<!-- symbol:{symbol_id} -->",
        f'<a id="{symbol_anchor(symbol_id)}"></a>',
        f"### `{record.qualified_name}`",
        "",
        f"- `{record.kind.value}` · 源码 `{record.path}:{record.span[0]}-{record.span[1]}`",
        *([f"- {cited}"] if cited else []),
        "",
        *body,
        "",
        target_close("symbol", symbol_id),
        "",
    ]


def _binding_unit(item: SurfaceBinding, *, key: str | None = None) -> list[str]:
    key = key or _binding_key(item)
    span = ""
    if item.lineno:
        end = item.end_lineno or item.lineno
        span = f" · 源码 `{item.path}:{item.lineno}-{end}`"
    target = ""
    if item.resolved_symbol_ids:
        target = " → " + md_link(item.resolved_symbol_ids[0], "symbol", item.resolved_symbol_ids[0])
    residual = item.residual or FILE_LEVEL_NOTE
    host = item.origin_path or item.path
    return [
        target_open("binding", key),
        f"<!-- surface-binding:{item.name} -->",
        f"### `{item.name}`（{FILE_LEVEL_NOTE}）",
        "",
        f"- `{item.kind}`{span}{target}",
        f"- 定义文件：`{host}`",
        f"- overlay 只解析到文件级：{residual}",
        "",
        target_close("binding", key),
        "",
    ]


def _file_units(
    path: str,
    symbol_ids: tuple[str, ...],
    ledger: SemanticLedger,
    surface: PublicSurface,
    files_in_page: tuple[str, ...],
) -> list[list[str]]:
    file_symbols = [symbol_id for symbol_id in symbol_ids if ledger.symbols[symbol_id].path == path]
    bindings = [item for item in _needed_bindings(surface, files_in_page) if (item.origin_path or item.path) == path or item.path == path]
    heading = [
        target_open("file", path),
        f"## `{path}`",
        "",
    ]
    toc: list[str] = []
    if file_symbols:
        toc.append("### 目录")
        toc.append("")
        for symbol_id in file_symbols:
            record = ledger.symbols[symbol_id]
            toc.append(
                f"- {md_link(f'`{record.qualified_name}`', 'symbol', symbol_id)}："
                f"{one_liner(record) if record.is_fresh else 'stale/uncovered'}"
            )
        toc.append("")
    if bindings:
        toc.append("### 公共绑定")
        toc.append("")
        for item in bindings:
            toc.append(f"- {md_link(f'`{item.name}`', 'binding', _binding_key(item))}")
        toc.append("")
    heading.extend(toc)
    units = [heading]
    for item in bindings:
        units.append(_binding_unit(item))
    for symbol_id in file_symbols:
        units.append(_symbol_unit(symbol_id, ledger))
    units.append([target_close("file", path), ""])
    return units


def _pack(
    prefix: list[str],
    units: list[list[str]],
    cont_prefix: list[str],
    *,
    limit: int = DETAIL_LINE_LIMIT,
) -> list[list[str]]:
    pages: list[list[str]] = []
    current = list(prefix)
    started = False
    def _n(lines: list[str]) -> int:
        return sum(item.count("\n") + 1 for item in lines) if lines else 0

    for unit in units:
        block = list(unit)
        cap = limit - _n(cont_prefix) - 2
        if _n(block) > cap:
            flat: list[str] = []
            for item in block:
                flat.extend(item.splitlines() or [item])
            block = flat[: max(4, cap - 2)] + ["", "（块超页上限，已截断。）"]
        if started and _n(current) + _n(block) > limit:
            pages.append(current)
            current = list(cont_prefix)
            started = False
        if _n(current) + _n(block) > limit:
            pages.append(current)
            current = list(cont_prefix)
            started = False
        current.extend(block)
        started = True
    if current:
        pages.append(current)
    return pages


def render_detail_pages(
    layout: ClusterLayout,
    bucket,
    ledger: SemanticLedger,
    surface: PublicSurface,
    traces: FlowTraceSet,
) -> dict[str, list[str]]:
    parent = layout.index_relpath or "INDEX.md"
    title = f"{layout.cluster.display} / {bucket.name}"
    base = detail_relpath(layout, bucket)
    prefix = [
        GENERATED_HEADER,
        f"# {title}",
        "",
        f"↑ {md_link('上级', 'page', parent)}",
        "",
        f"{len(bucket.files)} 个文件，{len(bucket.symbol_ids)} 个符号。同层同页；超 400 行分页。",
        "",
    ]
    if not layout.deep:
        trace = _trace_for(layout.cluster.cluster_id, traces)
        if trace and trace.ordered_symbol_ids:
            prefix.extend(_trace_block(trace, ledger, mermaid=False))
    units: list[list[str]] = []
    for path in bucket.files:
        units.extend(_file_units(path, bucket.symbol_ids, ledger, surface, bucket.files))
    if layout.cluster.unassigned_reason and not layout.deep:
        units.append(["## 残差", "", layout.cluster.unassigned_reason, ""])

    cont = [
        GENERATED_HEADER,
        f"# {title}（续）",
        "",
        f"↑ {md_link('上级', 'page', parent)}",
        "",
    ]
    # Leave slack for page-target wrap (2) + optional 分页 nav (~12).
    slack = 14
    packed = _pack(prefix, units, cont, limit=DETAIL_LINE_LIMIT - slack)
    documents: dict[str, list[str]] = {}
    for index, page_lines in enumerate(packed, start=1):
        relpath = detail_relpath(layout, bucket, None if index == 1 else index)
        if index == 1 and len(packed) > 1:
            nav = ["", "## 分页", ""]
            for part in range(2, len(packed) + 1):
                dest = detail_relpath(layout, bucket, part)
                nav.append(f"- {md_link(f'PART-{part}', 'page', dest)}")
            nav.append("")
            page_lines = page_lines[:6] + nav + page_lines[6:]
        wrapped = _page_wrap(relpath, page_lines)
        if len(wrapped) > DETAIL_LINE_LIMIT:
            wrapped = wrapped[: DETAIL_LINE_LIMIT - 1] + [target_close("page", relpath)]
        documents[relpath] = wrapped
    return documents


def render_overlay_pages(surface: PublicSurface) -> dict[str, list[str]]:
    items = overlay_items(surface)
    if not items:
        return {}
    n_parts = max(1, (len(items) + OVERLAY_PER_PAGE - 1) // OVERLAY_PER_PAGE)
    documents: dict[str, list[str]] = {}
    parent = "INDEX.md"
    for part in range(n_parts):
        chunk = items[part * OVERLAY_PER_PAGE : (part + 1) * OVERLAY_PER_PAGE]
        relpath = f"{OVERLAY_DIR}/DETAIL.md" if part == 0 else f"{OVERLAY_DIR}/PART-{part + 1}.md"
        title = "文件级公共面" if part == 0 else f"文件级公共面（续 {part + 1}）"
        lines = [
            GENERATED_HEADER,
            f"# {title}",
            "",
            f"↑ {md_link('根 INDEX', 'page', parent)}",
            "",
            f"{FILE_LEVEL_NOTE}。每个名字独占一块，不和别人共用文件标题。",
            "",
        ]
        if part == 0 and n_parts > 1:
            lines.extend(["## 分页", ""])
            for later in range(2, n_parts + 1):
                dest = f"{OVERLAY_DIR}/PART-{later}.md"
                lines.append(f"- {md_link(f'PART-{later}', 'page', dest)}")
            lines.append("")
        for item in chunk:
            lines.extend(_binding_unit(item, key=overlay_binding_key(item)))
        wrapped = _page_wrap(relpath, lines)
        if len(wrapped) > DETAIL_LINE_LIMIT:
            wrapped = wrapped[: DETAIL_LINE_LIMIT - 1] + [target_close("page", relpath)]
        documents[relpath] = wrapped
    return documents


def render_all_pages(
    repo_root: Path,
    ledger: SemanticLedger,
    surface: PublicSurface,
    layouts: tuple[ClusterLayout, ...],
    traces: FlowTraceSet,
) -> dict[str, list[str]]:
    pages: dict[str, list[str]] = {
        "INDEX.md": render_root_index(repo_root, ledger, surface, layouts, traces),
    }
    pages.update(render_overlay_pages(surface))
    for layout in layouts:
        if layout.deep and layout.index_relpath:
            pages[layout.index_relpath] = render_cluster_index(layout, ledger, traces)
        for bucket in layout.buckets:
            pages.update(render_detail_pages(layout, bucket, ledger, surface, traces))
    return pages
