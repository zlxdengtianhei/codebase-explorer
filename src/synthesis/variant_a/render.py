"""Project gated synthesis pages onto the nested markdown tree."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path

from src.semantic.models import SemanticLedger
from src.synthesis.variant_a.anchors import (
    _GENERATED_HEADER,
    file_anchor,
    filebind_anchor,
    md_link,
    page_anchor,
    symbol_anchor,
)
from src.synthesis.variant_a.depth import (
    ContentDepth,
    ThresholdSignals,
    body_mode,
    compute_threshold_signals,
    render_symbol_prose,
)
from src.synthesis.variant_a.gates import GateContext, page_is_projectable
from src.synthesis.variant_a.line_ranges import apply_line_ranges
from src.synthesis.variant_a.models import ClusterInput, PageKind, PageSpec, SynthesisLedger, SynthesisPage
from src.synthesis.variant_a.page_tree import pages_by_id, symbol_locator
from src.synthesis.variant_a.surface import PublicSurface, SurfaceBinding, entry_bindings, oracle_init_exports

FILE_LEVEL_NOTE = "模块级绑定，非枚举符号"
OVERLAY_DIR = "_overlay"
OVERLAY_PER_PAGE = 35


def _first_sentence(text: str) -> str:
    clipped = " ".join(text.split())
    for sep in ("。", ". ", "！", "!"):
        if sep in clipped:
            return clipped.split(sep, 1)[0] + ("" if sep == ". " else sep)
    return clipped[:180]


def _locate_binding(
    binding: SurfaceBinding,
    ledger: SemanticLedger,
    loc: Mapping[str, str],
    pages: tuple[PageSpec, ...],
) -> tuple[str, str, str, str]:
    """Return dest, fragment, precision ('symbol'|'file'), and path label."""

    if binding.resolved_symbol_ids:
        symbol_id = binding.resolved_symbol_ids[0]
        if symbol_id in loc and symbol_id in ledger.symbols:
            return loc[symbol_id], symbol_anchor(symbol_id), "symbol", ledger.symbols[symbol_id].path
    path = binding.target_path or binding.path
    dest, _ = _file_page(path, pages, loc, ledger)
    return dest, filebind_anchor(path, binding.name), "file", path


def _file_page(path: str, pages: tuple[PageSpec, ...], loc: Mapping[str, str], ledger: SemanticLedger) -> tuple[str, str]:
    for symbol_id, record in ledger.symbols.items():
        if record.path == path and symbol_id in loc:
            return loc[symbol_id], file_anchor(path)
    for page in pages:
        if path in page.paths:
            return page.relpath, file_anchor(path)
    return "_unassigned/DETAIL.md", file_anchor(path)


def _file_level_label(name: str, path: str) -> str:
    shown = Path(path).name or path
    return f"`{name}` → {shown}（{FILE_LEVEL_NOTE}）"


def _filebind_block(path: str, name: str, reason: str) -> list[str]:
    shown = Path(path).as_posix()
    why = reason or "AST 看不见 FunctionDef/ClassDef，台账无此符号"
    return [
        f"<!-- surface-binding:{name} -->",
        f'<a id="{filebind_anchor(path, name)}"></a>',
        f"### `{name}`（{FILE_LEVEL_NOTE}）",
        "",
        f"- 定义文件：`{shown}`",
        f"- overlay 只解析到文件级：{why}",
        "",
        f"<!-- end:surface-binding:{name} -->",
        "",
    ]


def collect_index_surface(
    surface: PublicSurface,
    ledger: SemanticLedger,
    loc: Mapping[str, str],
    pages: tuple[PageSpec, ...],
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str, str, str]]]:
    """Symbol-level (name, dest, frag) and file-level (name, dest, frag, path, reason)."""

    symbols: list[tuple[str, str, str]] = []
    files: list[tuple[str, str, str, str, str]] = []
    seen: set[str] = set()
    for item in entry_bindings(surface):
        if item.name in seen:
            continue
        seen.add(item.name)
        dest, frag, precision, path = _locate_binding(item, ledger, loc, pages)
        if precision == "symbol":
            symbols.append((item.name, dest, frag))
        else:
            files.append((item.name, "", filebind_anchor(path, item.name), path, item.unresolved_reason))
    for name, init_path in oracle_init_exports(ledger.repo_root):
        if name in seen:
            continue
        seen.add(name)
        files.append(
            (
                name,
                "",
                filebind_anchor(init_path, name),
                init_path,
                "oracle __init__ export, not a ledger symbol",
            )
        )
    return symbols, place_file_level_items(files)


def place_file_level_items(
    file_items: list[tuple[str, str, str, str, str]],
) -> list[tuple[str, str, str, str, str]]:
    """Park leftover file-level names on `_overlay/` so symbol PART pages stay under 400 lines."""

    n = len(file_items)
    if n == 0:
        return file_items
    n_parts = max(1, (n + OVERLAY_PER_PAGE - 1) // OVERLAY_PER_PAGE)
    placed: list[tuple[str, str, str, str, str]] = []
    for index, (name, _dest, frag, path, reason) in enumerate(file_items):
        part = index // OVERLAY_PER_PAGE + 1
        dest = f"{OVERLAY_DIR}/DETAIL.md" if n_parts == 1 else f"{OVERLAY_DIR}/PART-{part}.md"
        placed.append((name, dest, frag, path, reason))
    return placed


def render_overlay_pages(
    file_items: list[tuple[str, str, str, str, str]],
    pages: tuple[PageSpec, ...],
) -> dict[str, str]:
    if not file_items:
        return {}
    by_id = pages_by_id(pages)
    root = by_id["root"]
    grouped: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for name, dest, _frag, path, reason in file_items:
        grouped[dest].append((name, path, reason))
    docs: dict[str, str] = {}
    for dest, rows in grouped.items():
        page_id = f"overlay:{dest}"
        lines = [
            _GENERATED_HEADER,
            f'<a id="{page_anchor(page_id)}"></a>',
            "# 文件级公共面绑定",
            "",
            md_link("↑ 根 INDEX", dest, root.relpath, page_anchor(root.page_id)),
            "",
            "这些名字出现在公共面，但 AST 枚举不到 FunctionDef/ClassDef。链接保持文件级，不伪装成符号精度。",
            "",
        ]
        seen_paths: set[str] = set()
        for name, path, reason in rows:
            if path not in seen_paths:
                seen_paths.add(path)
                lines.extend([f'<a id="{file_anchor(path)}"></a>', f"## `{path}`", ""])
            lines.extend(_filebind_block(path, name, reason))
        lines.extend(["## 导航", "", f"- {md_link('↑ 根 INDEX', dest, root.relpath, page_anchor(root.page_id))}", ""])
        docs[dest] = "\n".join(lines).rstrip() + "\n"
    return docs


def _cluster_for(page: PageSpec, clusters: tuple[ClusterInput, ...]) -> ClusterInput | None:
    if not page.cluster_id:
        return None
    for cluster in clusters:
        if cluster.cluster_id == page.cluster_id:
            return cluster
    return None


def _capability_header(cluster: ClusterInput | None) -> list[str]:
    if cluster is None or cluster.is_unassigned:
        return []
    if not cluster.purpose and not cluster.boundary_not:
        return []
    lines: list[str] = []
    if cluster.purpose:
        lines.extend([cluster.purpose.strip(), ""])
    if cluster.boundary_not:
        lines.append("它不做什么：")
        for item in cluster.boundary_not:
            lines.append(f"- {item}")
        lines.append("")
    return lines


def _up_link(page: PageSpec, by_id: Mapping[str, PageSpec]) -> str:
    if page.parent_id is None:
        return md_link("↑ 根 INDEX", page.relpath, "INDEX.md", page_anchor("root"))
    parent = by_id[page.parent_id]
    return md_link(f"↑ {parent.title}", page.relpath, parent.relpath, page_anchor(parent.page_id))


def _tail(symbol_id: str, ledger: SemanticLedger) -> str:
    return ledger.symbols[symbol_id].qualified_name.rsplit(".", 1)[-1]


def _in_degree(symbol_ids: tuple[str, ...], ir_edges: frozenset[tuple[str, str]]) -> Counter[str]:
    wanted = set(symbol_ids)
    counts: Counter[str] = Counter()
    for _src, dst in ir_edges:
        if dst in wanted:
            counts[dst] += 1
    return counts


def _child_content_label(
    child: PageSpec,
    ledger: SemanticLedger,
    ctx: GateContext,
    surface: PublicSurface,
) -> str:
    if not child.symbol_ids:
        n_files = len(child.paths)
        return f"{child.title}（{n_files} 个文件）" if n_files else child.title
    exported = {item.name for item in surface.bindings if item.resolved_symbol_ids}
    indeg = _in_degree(child.symbol_ids, ctx.ir_edges)
    ranked = sorted(
        child.symbol_ids,
        key=lambda sid: (
            0 if _tail(sid, ledger) in exported else 1,
            -indeg[sid],
            ledger.symbols[sid].span[0],
            sid,
        ),
    )
    picked = ranked[:3]
    names = ", ".join(_tail(sid, ledger) for sid in picked)
    sentence = ""
    top = ledger.symbols[picked[0]]
    if top.explanation is not None and top.explanation.text.strip():
        sentence = _first_sentence(top.explanation.text)
        if len(sentence) > 80:
            sentence = sentence[:77] + "…"
    title = child.title
    if title.endswith("DETAIL"):
        title = title[: -len("DETAIL")].rstrip()
    if "PART-" in title:
        title = "PART-" + title.rsplit("PART-", 1)[-1]
    bit = f"{title} · {names}"
    return f"{bit} — {sentence}" if sentence else bit


def _down_links(page: PageSpec, by_id: Mapping[str, PageSpec]) -> list[str]:
    lines: list[str] = []
    for child_id in page.child_ids:
        child = by_id[child_id]
        n_sym = len(child.symbol_ids)
        label = f"{child.title} ({n_sym} symbols)" if n_sym else child.title
        lines.append(f"- {md_link(label, page.relpath, child.relpath, page_anchor(child.page_id))}")
    return lines


def _down_links_with_content(
    page: PageSpec,
    by_id: Mapping[str, PageSpec],
    ledger: SemanticLedger,
    ctx: GateContext,
    surface: PublicSurface,
) -> list[str]:
    lines: list[str] = []
    for child_id in page.child_ids:
        child = by_id[child_id]
        label = _child_content_label(child, ledger, ctx, surface)
        lines.append(f"- {md_link(label, page.relpath, child.relpath, page_anchor(child.page_id))}")
    return lines


def _render_claims(page: SynthesisPage, ledger: SemanticLedger, src: str, loc: Mapping[str, str]) -> list[str]:
    lines = [
        f"<!-- synthesis:{page.page_id} -->",
        "",
    ]
    for claim in page.claims:
        lines.append(claim.text.strip())
        lines.append("")
        if claim.graph_edge is not None:
            src_id, dst_id = claim.graph_edge
            bits: list[str] = []
            for sid in (src_id, dst_id):
                if sid not in ledger.symbols:
                    bits.append(f"`{sid}`")
                    continue
                tail = ledger.symbols[sid].qualified_name.rsplit(".", 1)[-1]
                dest = loc.get(sid, "INDEX.md")
                bits.append(md_link(f"`{tail}`", src, dest, symbol_anchor(sid)))
            lines.append(f"- {bits[0]} → {bits[1]}")
            lines.append("")
    lines.append(f"<!-- end:synthesis:{page.page_id} -->")
    lines.append("")
    return lines


def _compact_row(symbol_id: str, ledger: SemanticLedger, src: str) -> list[str]:
    """One visible index row: name + anchor + line range. No explanation.

    Marker, ``<a id>``, name and source span share one line so
    ``apply_line_ranges`` + pointing see the name inside the dest span.
    """

    record = ledger.symbols[symbol_id]
    start, end = record.span
    name = record.qualified_name
    link = md_link("`" + name + "`", src, src, symbol_anchor(symbol_id))
    return [
        (
            f"| <!-- symbol:{symbol_id} --><a id=\"{symbol_anchor(symbol_id)}\"></a>"
            f"<!-- compact:{symbol_id} -->{link} | `{record.path}:{start}-{end}` "
            f"<!-- end:symbol:{symbol_id} --> |"
        )
    ]


def _compact_table(symbol_ids: list[str], ledger: SemanticLedger, src: str) -> list[str]:
    if not symbol_ids:
        return []
    lines = [
        "## 本页其余符号",
        "",
        "| 名字 | 行区间 |",
        "| --- | --- |",
    ]
    for symbol_id in symbol_ids:
        lines.extend(_compact_row(symbol_id, ledger, src))
    lines.append("")
    return lines


def _split_symbols(
    symbol_ids: tuple[str, ...],
    depth: ContentDepth,
    status_by_symbol: Mapping[str, str] | None,
    signals: ThresholdSignals | None,
) -> tuple[list[str], list[str]]:
    """Return (block_ids, compact_ids) in the original page order."""

    blocks: list[str] = []
    compact: list[str] = []
    status_map = status_by_symbol or {}
    for symbol_id in symbol_ids:
        mode = body_mode(
            status_map.get(symbol_id),
            depth,
            symbol_id=symbol_id,
            signals=signals,
        )
        if mode == "compact":
            compact.append(symbol_id)
        else:
            blocks.append(symbol_id)
    return blocks, compact


def _symbol_block(
    symbol_id: str,
    ledger: SemanticLedger,
    src: str,
    loc: Mapping[str, str],
    *,
    depth: ContentDepth = ContentDepth.FULL,
    status_by_symbol: Mapping[str, str] | None = None,
    signals: ThresholdSignals | None = None,
) -> list[str]:
    record = ledger.symbols[symbol_id]
    explanation = record.explanation
    text = explanation.text.strip() if explanation is not None else ""
    status = (status_by_symbol or {}).get(symbol_id)
    mode = body_mode(status, depth, symbol_id=symbol_id, signals=signals)
    cited = explanation.cited_symbol_ids if explanation is not None else ()
    if mode == "compact":
        return _compact_row(symbol_id, ledger, src) + [""]
    if mode == "full":
        cite_bits: list[str] = []
        for cited_id in cited[:8]:
            if cited_id not in ledger.symbols:
                continue
            dest = loc.get(cited_id, src)
            cite_bits.append(md_link(f"`{cited_id}`", src, dest, symbol_anchor(cited_id)))
        return [
            f"<!-- symbol:{symbol_id} -->",
            f'<a id="{symbol_anchor(symbol_id)}"></a>',
            f"### `{record.qualified_name}`",
            "",
            f"- Symbol id：`{symbol_id}`",
            f"- 类型：`{record.kind.value}`；源码：`{record.path}:{record.span[0]}-{record.span[1]}`",
            f"- 被依赖事实：{'、'.join(cite_bits) if cite_bits else '无 ledger 内符号引用'}",
            "",
            text,
            "",
            f"<!-- end:symbol:{symbol_id} -->",
            "",
        ]
    prose = render_symbol_prose(symbol_id=symbol_id, text=text, mode=mode, status=status)
    return [
        f"<!-- symbol:{symbol_id} -->",
        f'<a id="{symbol_anchor(symbol_id)}"></a>',
        f"### `{record.qualified_name}`",
        "",
        f"- Symbol id：`{symbol_id}` · `{record.kind.value}` · `{record.path}:{record.span[0]}-{record.span[1]}`",
        *prose,
        f"<!-- end:symbol:{symbol_id} -->",
        "",
    ]


def render_root_index(
    *,
    repo_name: str,
    ledger: SemanticLedger,
    surface: PublicSurface,
    synthesis: SynthesisLedger,
    pages: tuple[PageSpec, ...],
    clusters: tuple[ClusterInput, ...],
    ctx: GateContext,
) -> str:
    by_id = pages_by_id(pages)
    loc = symbol_locator(pages)
    src = "INDEX.md"
    lines = [
        _GENERATED_HEADER,
        f'<a id="{page_anchor("root")}"></a>',
        f"# {repo_name} 代码语义索引",
        "",
        "入口页投影公共面、库综述与功能簇。每条链接带目标文件的行区间，禁检索下可换算。",
        "",
        f'<a id="public-surface"></a>',
        "## 公共面",
        "",
    ]
    symbol_items, file_items = collect_index_surface(surface, ledger, loc, pages)
    chunk: list[str] = []
    packed: list[str] = []
    for name, dest, frag in symbol_items:
        chunk.append(md_link(f"`{name}`", src, dest, frag))
        if len(chunk) >= 5:
            packed.append(" · ".join(chunk))
            chunk = []
    if chunk:
        packed.append(" · ".join(chunk))
    lines.extend(packed or (["（overlay 无已解析符号）"] if file_items else ["（overlay 为空）"]))
    lines.append("")
    if file_items:
        lines.extend(
            [
                "文件级绑定（overlay 只知道所在文件，不是台账符号；链接文字保持文件级）：",
                "",
            ]
        )
        for name, dest, frag, path, _reason in file_items:
            lines.append(f"- {md_link(_file_level_label(name, path), src, dest, frag)}")
        lines.append("")

    library = synthesis.pages.get("library")
    if library is not None and page_is_projectable(library, ctx):
        lines.extend(_render_claims(library, ledger, src, loc))
    flow = synthesis.pages.get("flow-main")
    if flow is not None and page_is_projectable(flow, ctx):
        lines.extend(_render_claims(flow, ledger, src, loc))

    lines.extend(["## 功能", ""])
    cluster_by_id = {item.cluster_id: item for item in clusters}
    root = by_id["root"]
    for child_id in root.child_ids:
        child = by_id[child_id]
        cluster = cluster_by_id.get(child.cluster_id)
        reason = ""
        if cluster is not None and cluster.unassigned_reason:
            reason = cluster.unassigned_reason.split(";")[0]
        link = md_link(child.title, src, child.relpath, page_anchor(child.page_id))
        n_files = len(child.paths)
        n_sym = len(child.symbol_ids) or (len(cluster.symbol_ids) if cluster else 0)
        extra = f"{n_files} 个文件，{n_sym} 个符号"
        purpose = (cluster.purpose if cluster is not None else "").strip()
        if purpose:
            extra = f"{extra}。{_first_sentence(purpose)}"
        if child.kind == PageKind.UNASSIGNED:
            lines.append(f"- {link}：{reason}")
        elif child.inline_fragment:
            lines.append(f"- {link}（浅簇，{extra}）")
        else:
            lines.append(f"- {link}：{extra}")
    lines.extend(["", "## 导航", ""])
    lines.append(f"- {_up_link(root, by_id)}")
    lines.extend(
        [
            "",
            "## 可复算状态",
            "",
            f"- Ledger schema：`{ledger.schema}`",
            f"- Source revision：`{ledger.source_revision}`",
            "- 综述块只投影 fresh 且引用闭包完整的 synthesis 页。",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_cluster_index(
    page: PageSpec,
    ledger: SemanticLedger,
    synthesis: SynthesisLedger,
    pages: tuple[PageSpec, ...],
    ctx: GateContext,
    surface: PublicSurface,
    cluster: ClusterInput | None = None,
) -> str:
    by_id = pages_by_id(pages)
    loc = symbol_locator(pages)
    lines = [
        _GENERATED_HEADER,
        f'<a id="{page_anchor(page.page_id)}"></a>',
        f"# {page.title}",
        "",
        _up_link(page, by_id),
        "",
    ]
    lines.extend(_capability_header(cluster))
    syn = synthesis.pages.get(page.synthesis_page_id or "")
    if syn is not None and page_is_projectable(syn, ctx):
        lines.extend(_render_claims(syn, ledger, page.relpath, loc))
    lines.extend(["## 下层", ""])
    lines.extend(_down_links_with_content(page, by_id, ledger, ctx, surface) or ["- （无子页）"])
    lines.extend(["", "## 导航", "", f"- {_up_link(page, by_id)}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_detail(
    page: PageSpec,
    ledger: SemanticLedger,
    pages: tuple[PageSpec, ...],
    *,
    unassigned_reason: str = "",
    mentions: Mapping[str, list[tuple[str, str]]] | None = None,
    cluster: ClusterInput | None = None,
    depth: ContentDepth = ContentDepth.FULL,
    status_by_symbol: Mapping[str, str] | None = None,
    signals: ThresholdSignals | None = None,
) -> str:
    by_id = pages_by_id(pages)
    loc = symbol_locator(pages)
    src = page.relpath
    page_mentions = mentions or {}
    lines = [
        _GENERATED_HEADER,
        f'<a id="{page_anchor(page.page_id)}"></a>',
        f"# {page.title}",
        "",
        _up_link(page, by_id),
        "",
    ]
    if page.kind is not PageKind.UNASSIGNED and page.kind is not PageKind.PART:
        lines.extend(_capability_header(cluster))
    if page.kind is PageKind.UNASSIGNED:
        lines.extend(["## 未归类文件（每个条目带原因）", ""])
        for path in page.paths:
            reason = unassigned_reason
            for part in unassigned_reason.split(";"):
                if part.strip().startswith(path):
                    reason = part.strip()
                    break
            lines.extend(
                [
                    f'<a id="{file_anchor(path)}"></a>',
                    f"## `{path}`",
                    "",
                    reason or "unassigned: no reason recorded",
                    "",
                ]
            )
            for name, why in page_mentions.get(path, ()):
                lines.extend(_filebind_block(path, name, why))
            file_symbols = [sid for sid in page.symbol_ids if ledger.symbols[sid].path == path]
            file_blocks, file_compact = _split_symbols(
                tuple(file_symbols), depth, status_by_symbol, signals
            )
            lines.extend(_compact_table(file_compact, ledger, src))
            for symbol_id in file_blocks:
                lines.extend(
                    _symbol_block(
                        symbol_id,
                        ledger,
                        src,
                        loc,
                        depth=depth,
                        status_by_symbol=status_by_symbol,
                        signals=signals,
                    )
                )
        leftover_paths = [path for path in page_mentions if path not in page.paths]
        for path in leftover_paths:
            lines.extend(
                [
                    f'<a id="{file_anchor(path)}"></a>',
                    f"## `{path}`",
                    "",
                    "file-level overlay target not listed in unassigned paths",
                    "",
                ]
            )
            for name, why in page_mentions[path]:
                lines.extend(_filebind_block(path, name, why))
        lines.extend(["## 导航", "", f"- {_up_link(page, by_id)}", ""])
        return "\n".join(lines).rstrip() + "\n"

    block_ids, compact_ids = _split_symbols(page.symbol_ids, depth, status_by_symbol, signals)
    lines.extend(_compact_table(compact_ids, ledger, src))
    if block_ids:
        lines.extend(["## 本页符号", ""])
        for symbol_id in block_ids:
            record = ledger.symbols[symbol_id]
            sentence = ""
            if record.explanation is not None:
                sentence = _first_sentence(record.explanation.text)
            lines.append(
                f"- {md_link('`' + record.qualified_name + '`', src, src, symbol_anchor(symbol_id))}：{sentence}"
            )
        lines.append("")
    seen_files: set[str] = set()
    for symbol_id in block_ids:
        record = ledger.symbols[symbol_id]
        if record.path not in seen_files:
            seen_files.add(record.path)
            lines.extend([f'<a id="{file_anchor(record.path)}"></a>', f"## `{record.path}`", ""])
            for name, why in page_mentions.get(record.path, ()):
                lines.extend(_filebind_block(record.path, name, why))
        lines.extend(
            _symbol_block(
                symbol_id,
                ledger,
                src,
                loc,
                depth=depth,
                status_by_symbol=status_by_symbol,
                signals=signals,
            )
        )
    for symbol_id in compact_ids:
        path = ledger.symbols[symbol_id].path
        if path in seen_files:
            continue
        seen_files.add(path)
        lines.extend([f'<a id="{file_anchor(path)}"></a>'])
        for name, why in page_mentions.get(path, ()):
            lines.extend(_filebind_block(path, name, why))
    for path, names in page_mentions.items():
        if path in seen_files:
            continue
        lines.extend([f'<a id="{file_anchor(path)}"></a>', f"## `{path}`", ""])
        for name, why in names:
            lines.extend(_filebind_block(path, name, why))
    lines.extend(["## 导航", "", f"- {_up_link(page, by_id)}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_documents(
    *,
    repo_name: str,
    ledger: SemanticLedger,
    surface: PublicSurface,
    synthesis: SynthesisLedger,
    pages: tuple[PageSpec, ...],
    clusters: tuple[ClusterInput, ...],
    ctx: GateContext,
    depth: ContentDepth = ContentDepth.FULL,
    status_by_symbol: Mapping[str, str] | None = None,
) -> dict[str, str]:
    docs: dict[str, str] = {}
    unassigned_reason = ""
    for cluster in clusters:
        if cluster.is_unassigned:
            unassigned_reason = cluster.unassigned_reason
    loc = symbol_locator(pages)
    signals = None
    if depth is ContentDepth.THRESHOLD:
        signals = compute_threshold_signals(
            surface=surface,
            ir_edges=ctx.ir_edges,
            symbol_ids=ledger.symbols,
        )
    _symbol_items, file_items = collect_index_surface(surface, ledger, loc, pages)
    file_items = place_file_level_items(file_items)
    for page in pages:
        if page.kind is PageKind.ROOT_INDEX:
            docs[page.relpath] = render_root_index(
                repo_name=repo_name,
                ledger=ledger,
                surface=surface,
                synthesis=synthesis,
                pages=pages,
                clusters=clusters,
                ctx=ctx,
            )
        elif page.kind is PageKind.CLUSTER_INDEX:
            docs[page.relpath] = render_cluster_index(
                page,
                ledger,
                synthesis,
                pages,
                ctx,
                surface,
                cluster=_cluster_for(page, clusters),
            )
        else:
            docs[page.relpath] = render_detail(
                page,
                ledger,
                pages,
                unassigned_reason=unassigned_reason,
                cluster=_cluster_for(page, clusters),
                depth=depth,
                status_by_symbol=status_by_symbol,
                signals=signals,
            )
    docs.update(render_overlay_pages(file_items, pages))
    return apply_line_ranges(docs)


def write_documents(docs_root: Path, documents: Mapping[str, str]) -> None:
    if docs_root.exists():
        for old in docs_root.rglob("*"):
            if old.is_file():
                old.unlink()
    for rel, content in documents.items():
        dest = docs_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8", newline="\n")
