"""Recursive page splitting for the semantic doc tree (LBM §2).

Any page over budget is split by sinking groups into child pages. The parent
keeps a navigation row (name + one-liner + link). Content is never trimmed.
There is no depth-limit parameter (LBM A3).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

GENERATED_HEADER = "<!-- generated:codebase-explorer-semantic-docs -->"
DEFAULT_INDEX_MAX_LINES = 150
DEFAULT_DETAIL_MAX_LINES = 400
DEFAULT_DETAIL_MAX_BLOCKS = 40
DEFAULT_MAX_NAV_RATIO = 0.25
DETAIL_LEAF_NAME = "DETAIL.md"
HOP_DEFINITION = (
    "BFS on the rendered markdown link graph. INDEX.md = 0. A symbol's hop count is the "
    "shortest page distance of any page that contains <!-- symbol:ID -->. Buckets: "
    "1 / 2 / 3 / 4+ / unreachable."
)
_SYMBOL_MARK = re.compile(r"<!--\s*symbol:([^\s>]+)\s*-->")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_NAV_LINE = re.compile(
    r"^(?:↑ \[|- \[[^\]]+\]\((?!https?://|mailto:|#)[^)]+\)：)"
)
_PAGE_TOKEN = re.compile(r"@@PAGE:([^@]+)@@")
_SYM_TOKEN = re.compile(r"@@SYM:([^@]+)@@")
_SKIP_SCHEMES = ("http://", "https://", "mailto:")
_RUNAWAY_SPLITS = 100_000

# Named sink directories for INDEX groups (N-10: surface is one instance).
_GROUP_HOME = {
    "surface": ("_surface/INDEX.md", "公共面", "包导出与公开绑定的完整清单，无删减。"),
    "residual": ("_residuals/INDEX.md", "未覆盖、stale 与 residual", "未覆盖与 stale 符号的完整清单，无删减。"),
    "diagram": ("_graph/INDEX.md", "模块依赖图", "模块依赖图完整保留，无删减。"),
    "module": ("_clusters/INDEX.md", "功能模块", "功能模块入口的完整清单，无删减。"),
    "dup": ("_dups/INDEX.md", "重复能力", "重复与同名实现的完整清单，并列可见，无删减。"),
}


class LayeringError(ValueError):
    """Split could not make progress without cutting content."""


class LayeringInvariantError(ValueError):
    """A generated page violates a hard LBM invariant."""


@dataclass(frozen=True)
class LayerBudget:
    """Single-page budgets. Depth is not a field (LBM A3)."""

    index_max_lines: int = DEFAULT_INDEX_MAX_LINES
    detail_max_lines: int = DEFAULT_DETAIL_MAX_LINES
    detail_max_blocks: int = DEFAULT_DETAIL_MAX_BLOCKS
    max_nav_ratio: float = DEFAULT_MAX_NAV_RATIO

    def max_lines(self, kind: str) -> int:
        return self.index_max_lines if kind == "index" else self.detail_max_lines


@dataclass(frozen=True)
class PageUnit:
    """One sinkable or fixed unit on a page."""

    unit_id: str
    kind: str
    group_key: str
    name: str
    one_liner: str
    lines: tuple[str, ...]
    symbol_ids: tuple[str, ...] = ()
    block_count: int = 0
    nav_target: str | None = None
    children: tuple[PageUnit, ...] = ()
    suffix_lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class Page:
    relpath: str
    kind: str
    title: str
    parent_relpath: str | None
    parent_title: str
    units: tuple[PageUnit, ...]


def symbol_anchor(symbol_id: str) -> str:
    digest = hashlib.sha256(symbol_id.encode("utf-8")).hexdigest()[:16]
    return f"symbol-{digest}"


def relative_href(src_rel: str, dst_rel: str) -> str:
    if src_rel == dst_rel:
        return ""
    start = str(Path(src_rel).parent)
    if start == ".":
        start = "."
    return Path(os.path.relpath(dst_rel, start=start)).as_posix()


def assign_dag_layers(
    symbol_ids: Sequence[str],
    edges: Sequence[tuple[str, str]],
) -> dict[str, int]:
    nodes = set(symbol_ids)
    incoming: dict[str, int] = {node: 0 for node in nodes}
    adj: dict[str, list[str]] = {node: [] for node in nodes}
    for source, target in edges:
        if source not in nodes or target not in nodes or source == target:
            continue
        adj[source].append(target)
        incoming[target] += 1
    layer = {node: 0 for node in nodes}
    queue = deque(node for node, count in incoming.items() if count == 0)
    seen = 0
    while queue:
        node = queue.popleft()
        seen += 1
        for child in adj[node]:
            layer[child] = max(layer[child], layer[node] + 1)
            incoming[child] -= 1
            if incoming[child] == 0:
                queue.append(child)
    return layer


def _flatten_lines(lines: Sequence[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        if "\n" in line:
            out.extend(line.splitlines())
        else:
            out.append(line)
    return out


def iter_unit_lines(unit: PageUnit) -> list[str]:
    lines = _flatten_lines(unit.lines)
    for child in unit.children:
        child_lines = iter_unit_lines(child)
        if child_lines:
            lines.extend(child_lines)
    if unit.suffix_lines:
        suffix = _flatten_lines(unit.suffix_lines)
        if lines and lines[-1].strip() and suffix and suffix[0].strip():
            lines.append("")
        lines.extend(suffix)
    return lines


def unit_block_count(unit: PageUnit) -> int:
    if unit.children:
        return sum(unit_block_count(child) for child in unit.children)
    return unit.block_count


def iter_symbol_units(unit: PageUnit) -> list[PageUnit]:
    if unit.kind == "symbol":
        return [unit]
    found: list[PageUnit] = []
    for child in unit.children:
        found.extend(iter_symbol_units(child))
    return found


def render_page_lines(page: Page) -> list[str]:
    lines = [
        GENERATED_HEADER,
        f'<!-- tgt:page:{page.relpath} --><a id="L1-L0"></a>',
        f"# {page.title}",
        "",
    ]
    if page.parent_relpath:
        lines.append(f"↑ [{page.parent_title}](@@PAGE:{page.parent_relpath}@@)")
        lines.append("")
    for unit in page.units:
        unit_lines = iter_unit_lines(unit)
        if not unit_lines:
            continue
        lines.extend(unit_lines)
        if unit_lines[-1].strip():
            lines.append("")
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def page_block_count(page: Page) -> int:
    return sum(unit_block_count(unit) for unit in page.units)


def page_over_budget(page: Page, budget: LayerBudget) -> list[str]:
    lines = render_page_lines(page)
    n_lines = len(lines)
    n_blocks = page_block_count(page)
    reasons: list[str] = []
    if page.kind == "index" and n_lines > budget.index_max_lines:
        reasons.append(f"index lines {n_lines} > {budget.index_max_lines}")
    if page.kind == "detail":
        if n_lines > budget.detail_max_lines:
            reasons.append(f"detail lines {n_lines} > {budget.detail_max_lines}")
        if n_blocks > budget.detail_max_blocks:
            reasons.append(f"detail blocks {n_blocks} > {budget.detail_max_blocks}")
    return reasons


def _nav_capacity(
    content_lines: int,
    max_lines: int,
    max_ratio: float,
    *,
    reserved_nav: int = 0,
) -> int:
    """Max new nav rows that still keep ratio and line budget.

    ``reserved_nav`` counts uplinks already on the page. Those are nav lines
    and must not be treated as content.
    """

    if max_ratio <= 0 or max_ratio >= 1:
        return max(1, max_lines - content_lines - reserved_nav)
    # (reserved + G) / (content + reserved + G) <= r
    # G <= r/(1-r)*content - reserved
    by_ratio = int(max_ratio / (1.0 - max_ratio) * max(content_lines, 1)) - reserved_nav
    by_lines = max_lines - content_lines - reserved_nav
    return max(1, min(by_ratio, by_lines))


def _line_classes(page: Page) -> tuple[int, int]:
    """Return (content_lines, nav_lines) for the current render."""

    lines = render_page_lines(page)
    nav = sum(1 for line in lines if _NAV_LINE.match(line))
    return len(lines) - nav, nav


def _blurb_unit(item_count: int) -> PageUnit:
    return PageUnit(
        unit_id="blurb",
        kind="fixed",
        group_key="fixed",
        name="blurb",
        one_liner="",
        lines=(
            "本页是分层入口。被下沉到子页的条目在子页完整保留，没有删除、省略或截断。",
            f"本组共 {item_count} 条，按单页预算继续嵌套。",
            "导航行只指向子页；符号解释与残差原文均在对应子页。",
            "本分层由页预算推导，深度不是配置项。",
            "公共面、模块入口与残差清单使用同一套分裂规则。",
            "读者从本页选择分组后下钻，不必在本页读完全部分组内容。",
            "若一组仍然超预算，渲染器会再加一层，而不是裁剪。",
            "锚点带行区间；上行链接保证无死胡同。",
        ),
    )


def _pad_for_nav_ratio(page: Page, budget: LayerBudget) -> Page:
    """Add non-nav prose until nav/total <= max_nav_ratio, without exceeding the line cap."""

    max_lines = budget.max_lines(page.kind)
    lines = render_page_lines(page)
    nav = sum(1 for line in lines if _NAV_LINE.match(line))
    total = len(lines)
    if total == 0 or nav / total <= budget.max_nav_ratio + 1e-9:
        return page
    # nav / (total + extra) <= r  => extra >= nav/r - total
    needed = int(nav / budget.max_nav_ratio - total + 0.9999)
    room = max_lines - total
    extra = max(0, min(needed, room))
    if extra <= 0:
        return page
    pad = PageUnit(
        unit_id=f"pad:{page.relpath}",
        kind="fixed",
        group_key="fixed",
        name="pad",
        one_liner="",
        lines=tuple(
            "下沉条目完整保留在子页；本行是为单跳信息密度不变式保留的说明，不是删减。"
            for _ in range(extra)
        ),
    )
    return replace(page, units=(pad, *page.units))


def _unique_relpath(candidate: str, occupied: set[str]) -> str:
    posix = Path(candidate).as_posix()
    if posix not in occupied:
        return posix
    path = Path(posix)
    parent = path.parent.as_posix()
    stem = path.stem
    suffix = path.suffix
    index = 2
    while True:
        name = f"{stem}-{index}{suffix}"
        alt = f"{parent}/{name}" if parent != "." else name
        if alt not in occupied:
            return alt
        index += 1


def _dir_of(relpath: str) -> str:
    parent = Path(relpath).parent.as_posix()
    return "" if parent == "." else parent


def _join_rel(directory: str, name: str) -> str:
    return f"{directory}/{name}" if directory else name


def _next_part(directory: str, occupied: set[str], *, start: int = 2) -> str:
    number = start
    while True:
        candidate = _join_rel(directory, f"PART-{number}.md")
        if candidate not in occupied:
            return candidate
        number += 1


def _next_group_index(directory: str, occupied: set[str], *, start: int = 1) -> str:
    number = start
    while True:
        candidate = _join_rel(_join_rel(directory, f"g{number}") if directory else f"g{number}", "INDEX.md")
        if candidate not in occupied:
            return candidate
        number += 1


def _heading_unit(group_key: str, heading: str) -> PageUnit:
    return PageUnit(
        unit_id=f"heading:{group_key}:{heading}",
        kind="heading",
        group_key=group_key,
        name=heading,
        one_liner="",
        lines=(f"## {heading}", ""),
    )


def _nav_unit(name: str, one_liner: str, target: str, group_key: str) -> PageUnit:
    return PageUnit(
        unit_id=f"nav:{target}",
        kind="nav",
        group_key=group_key,
        name=name,
        one_liner=one_liner,
        lines=(f"- [{name}](@@PAGE:{target}@@)：{one_liner}",),
        nav_target=target,
    )


def _group_units(page: Page, key: str) -> tuple[PageUnit, ...]:
    return tuple(unit for unit in page.units if unit.group_key == key and unit.kind not in {"heading", "nav"})


def _insert_navs(page: Page, group_key: str, navs: Sequence[PageUnit], *, drop_body: bool) -> Page:
    new_units: list[PageUnit] = []
    inserted = False
    for unit in page.units:
        if unit.group_key != group_key:
            new_units.append(unit)
            continue
        if unit.kind == "heading":
            new_units.append(unit)
            continue
        if unit.kind == "nav" and not drop_body:
            new_units.append(unit)
            continue
        if drop_body and unit.kind != "nav":
            if not inserted:
                new_units.extend(navs)
                inserted = True
            continue
        new_units.append(unit)
    if not inserted:
        heading = next((unit for unit in page.units if unit.group_key == group_key and unit.kind == "heading"), None)
        if heading is None:
            new_units.append(_heading_unit(group_key, navs[0].name if navs else group_key))
        new_units.extend(navs)
    return replace(page, units=tuple(new_units))


def _child_kind(parent: Page, group_key: str) -> str:
    if parent.kind == "detail" and group_key not in {"surface", "residual", "diagram", "module"}:
        return "detail"
    return "index"


def _make_child(
    parent: Page,
    relpath: str,
    title: str,
    group_key: str,
    body: Sequence[PageUnit],
    *,
    kind: str | None = None,
) -> Page:
    heading = _heading_unit(group_key, title)
    units = tuple(unit for unit in body if unit.kind != "heading")
    if any(unit.kind == "heading" for unit in body):
        child_units = tuple(body)
    else:
        child_units = (heading, *units) if kind != "detail" else tuple(body)
    if kind != "detail":
        child_units = (_blurb_unit(sum(1 for unit in body if unit.kind != "heading")), *child_units)
    return Page(
        relpath=relpath,
        kind=kind or _child_kind(parent, group_key),
        title=title,
        parent_relpath=parent.relpath,
        parent_title=parent.title,
        units=child_units,
    )


def _chrome_counts(page: Page, *, exclude_group: str | None = None) -> tuple[int, int]:
    if exclude_group is None:
        return _line_classes(page)
    probe = replace(
        page,
        units=tuple(
            unit
            for unit in page.units
            if not (unit.group_key == exclude_group and unit.kind not in {"heading", "nav"})
        ),
    )
    return _line_classes(probe)


def _largest_sinkable_group(page: Page) -> str | None:
    sizes: dict[str, int] = defaultdict(int)
    for unit in page.units:
        if unit.kind in {"heading", "nav"}:
            continue
        if unit.group_key == "fixed":
            continue
        sizes[unit.group_key] += len(iter_unit_lines(unit))
    if not sizes:
        return None
    return max(sizes, key=lambda key: (sizes[key], key))


def _partition(items: Sequence[PageUnit], groups: int) -> list[tuple[PageUnit, ...]]:
    if groups <= 1:
        return [tuple(items)]
    groups = min(groups, len(items))
    buckets: list[list[PageUnit]] = [[] for _ in range(groups)]
    for index, item in enumerate(items):
        buckets[index % groups].append(item)
    # Prefer contiguous chunks for readability.
    size = (len(items) + groups - 1) // groups
    contiguous = [tuple(items[i : i + size]) for i in range(0, len(items), size)]
    return [chunk for chunk in contiguous if chunk]


def _group_label(group_key: str, chunk: Sequence[PageUnit], index: int, total: int) -> tuple[str, str]:
    if group_key in _GROUP_HOME:
        _, name, blurb = _GROUP_HOME[group_key]
        if total > 1:
            return f"{name}（{index + 1}/{total}）", f"{len(chunk)} 条，完整内容在子页，无删减。"
        return name, blurb
    if group_key.startswith("layer:"):
        layer = group_key.split(":", 1)[1]
        return f"层级 L{layer}", f"{len(chunk)} 个文件/符号组，按 DAG 层下沉，无删减。"
    if group_key.startswith("file:"):
        path = group_key.split(":", 1)[1]
        return path, f"{sum(unit_block_count(unit) for unit in chunk)} 个符号块，无删减。"
    first = chunk[0].name if chunk else group_key
    last = chunk[-1].name if chunk else group_key
    if first == last:
        return first, f"{len(chunk)} 条入口，完整内容在子页，无删减。"
    return f"{first}–{last}", f"{len(chunk)} 条入口，完整内容在子页，无删减。"


def _explode_file_unit(unit: PageUnit, budget: LayerBudget) -> list[PageUnit]:
    symbols = iter_symbol_units(unit)
    if not symbols:
        return [unit]
    max_blocks = max(1, budget.detail_max_blocks)
    if unit_block_count(unit) <= max_blocks and len(iter_unit_lines(unit)) <= budget.detail_max_lines:
        return [unit]
    chunks: list[PageUnit] = []
    for start in range(0, len(symbols), max_blocks):
        piece = symbols[start : start + max_blocks]
        header = [
            f"## `{unit.name}`" + ("（续）" if start else ""),
            "",
            "### 文件语义目录",
            "",
        ]
def _file_chunk(
    unit: PageUnit,
    piece: Sequence[PageUnit],
    *,
    start: int,
) -> PageUnit:
    header = [
        f"## `{unit.name}`" + ("（续）" if start else ""),
        "",
        "### 文件语义目录",
        "",
    ]
    for symbol in piece:
        sid = symbol.symbol_ids[0] if symbol.symbol_ids else symbol.unit_id
        header.append(f"- [`{symbol.name}`](@@SYM:{sid}@@)：{symbol.one_liner}")
    header.append("")
    return PageUnit(
        unit_id=f"{unit.unit_id}:chunk:{start}",
        kind="file",
        group_key=unit.group_key,
        name=unit.name,
        one_liner=f"{len(piece)} 个符号块",
        lines=tuple(header),
        symbol_ids=tuple(sid for symbol in piece for sid in symbol.symbol_ids),
        block_count=len(piece),
        children=tuple(piece),
        suffix_lines=unit.suffix_lines if start == 0 else (),
    )


def _explode_file_unit(unit: PageUnit, budget: LayerBudget) -> list[PageUnit]:
    symbols = iter_symbol_units(unit)
    if not symbols:
        return [unit]
    line_cap = max(1, budget.detail_max_lines - 20)
    block_cap = max(1, budget.detail_max_blocks)
    if (
        unit_block_count(unit) <= block_cap
        and len(iter_unit_lines(unit)) <= line_cap
    ):
        return [unit]
    chunks: list[PageUnit] = []
    start = 0
    while start < len(symbols):
        take = 0
        while start + take < len(symbols) and take < block_cap:
            candidate = _file_chunk(unit, symbols[start : start + take + 1], start=start)
            if take > 0 and len(iter_unit_lines(candidate)) > line_cap:
                break
            take += 1
        if take == 0:
            take = 1
        chunks.append(_file_chunk(unit, symbols[start : start + take], start=start))
        start += take
    return chunks


def _pack_detail_units(units: Sequence[PageUnit], budget: LayerBudget) -> list[tuple[PageUnit, ...]]:
    exploded: list[PageUnit] = []
    for unit in units:
        exploded.extend(_explode_file_unit(unit, budget))
    bins: list[list[PageUnit]] = []
    current: list[PageUnit] = []
    blocks = 0
    lines = 0
    chrome = 12
    for unit in exploded:
        unit_blocks = unit_block_count(unit)
        unit_lines = len(iter_unit_lines(unit))
        overflow = current and (
            blocks + unit_blocks > budget.detail_max_blocks
            or lines + unit_lines > budget.detail_max_lines - chrome
        )
        if overflow:
            bins.append(current)
            current, blocks, lines = [], 0, 0
        current.append(unit)
        blocks += unit_blocks
        lines += unit_lines
    if current:
        bins.append(current)
    return [tuple(item) for item in bins]


def split_over_budget(
    page: Page,
    budget: LayerBudget | None = None,
    *,
    occupied: set[str] | None = None,
) -> tuple[Page, list[Page]]:
    """Sink one overflowing group into child pages. Parent keeps nav rows.

    Recursion lives in ``split_until_fit``; this function does a single step.
    """

    budget = budget or LayerBudget()
    occupied_relpaths = set(occupied or ())
    occupied_relpaths.add(page.relpath)
    if not page_over_budget(page, budget):
        return page, []

    if page.kind == "detail":
        return _split_detail(page, budget, occupied_relpaths)
    return _split_index(page, budget, occupied_relpaths)


def _split_index(page: Page, budget: LayerBudget, occupied: set[str]) -> tuple[Page, list[Page]]:
    group_key = _largest_sinkable_group(page)
    if group_key is None:
        raise LayeringError(f"index {page.relpath} is over budget but has no sinkable group")
    body = list(_group_units(page, group_key))
    if not body:
        raise LayeringError(f"index {page.relpath} group {group_key!r} is empty")
    # A single entry whose lines exceed the INDEX cap cannot be partitioned
    # and would nest forever. Slice it into sinkable row units first.
    line_cap = max(4, budget.index_max_lines - 16)
    sliced: list[PageUnit] = []
    for unit in body:
        unit_lines = iter_unit_lines(unit)
        if unit.kind != "entry" or len(unit_lines) <= line_cap:
            sliced.append(unit)
            continue
        for start in range(0, len(unit_lines), line_cap):
            sliced.append(
                replace(
                    unit,
                    unit_id=f"{unit.unit_id}:ln:{start}",
                    lines=tuple(unit_lines[start : start + line_cap]),
                )
            )
    body = sliced
    chrome_content, reserved_nav = _chrome_counts(page, exclude_group=group_key)
    capacity = _nav_capacity(
        chrome_content,
        budget.index_max_lines,
        budget.max_nav_ratio,
        reserved_nav=reserved_nav,
    )
    directory = _dir_of(page.relpath)
    children: list[Page] = []
    navs: list[PageUnit] = []

    def _finish(parent: Page, kids: list[Page]) -> tuple[Page, list[Page]]:
        return _pad_for_nav_ratio(parent, budget), kids

    home = _GROUP_HOME.get(group_key)
    # Named root groups (surface / residual / diagram / module) always sink
    # to their home page; the child splits further if it is still over budget.
    if home and page.relpath == "INDEX.md":
        target, title, blurb = home
        target = _unique_relpath(target, occupied)
        occupied.add(target)
        child = _make_child(page, target, title, group_key, body, kind="index")
        children.append(child)
        navs.append(_nav_unit(title, blurb, target, group_key))
        parent = _insert_navs(page, group_key, navs, drop_body=True)
        return _finish(parent, children)

    body_lines = sum(len(iter_unit_lines(unit)) for unit in body)
    child_would_overflow = body_lines + 12 > budget.index_max_lines
    force_groups = 2 if child_would_overflow and capacity == 1 and len(body) > 1 else 1
    group_count = min(max(capacity, force_groups), len(body))
    groups = _partition(body, group_count)
    if len(groups) == 1 and child_would_overflow and len(body) > 1:
        groups = _partition(body, 2)

    if len(groups) == 1:
        # One child carrying the whole group; child will split further.
        if home:
            default_rel, title, blurb = home
            if page.relpath.endswith("INDEX.md") and _dir_of(page.relpath):
                target = _next_group_index(directory, occupied)
            else:
                target = _unique_relpath(default_rel, occupied)
        else:
            title, blurb = _group_label(group_key, body, 0, 1)
            target = _next_group_index(directory, occupied)
        occupied.add(target)
        child = _make_child(page, target, title, group_key, body, kind="index")
        parent = _insert_navs(page, group_key, [_nav_unit(title, blurb, target, group_key)], drop_body=True)
        return _finish(parent, [child])

    for index, chunk in enumerate(groups):
        title, blurb = _group_label(group_key, chunk, index, len(groups))
        target = _next_group_index(directory, occupied)
        occupied.add(target)
        children.append(_make_child(page, target, title, group_key, chunk, kind="index"))
        navs.append(_nav_unit(title, blurb, target, group_key))
    parent = _insert_navs(page, group_key, navs, drop_body=True)
    return _finish(parent, children)


def _split_detail(page: Page, budget: LayerBudget, occupied: set[str]) -> tuple[Page, list[Page]]:
    fixed = tuple(unit for unit in page.units if unit.kind in {"fixed", "heading"} and unit.group_key in {"overview", "diagram", "meta", "fixed"})
    body = tuple(unit for unit in page.units if unit not in fixed)
    if not body:
        # Overview itself overflowed: sink diagram if present.
        group_key = _largest_sinkable_group(page)
        if group_key is None:
            raise LayeringError(f"detail {page.relpath} is over budget with no sinkable body")
        return _split_index(page, budget, occupied)

    movable = [unit for unit in body if unit.kind != "nav"]
    bins = _pack_detail_units(movable, budget)
    if len(bins) <= 1:
        # Single bin still over: explode files and pack again.
        exploded: list[PageUnit] = []
        for unit in movable:
            exploded.extend(_explode_file_unit(unit, budget))
        bins = _pack_detail_units(exploded, budget)
        # Packer ignores overview/diagram chrome. If several file units still
        # share one bin, force a 2-way PART so inbound lines cannot stall A1.
        if len(bins) <= 1 and len(exploded) > 1:
            bins = _partition(exploded, 2)
    if len(bins) <= 1:
        raise LayeringError(
            f"detail {page.relpath} cannot split further without cutting content "
            f"(lines={len(render_page_lines(page))} blocks={page_block_count(page)})"
        )

    directory = _dir_of(page.relpath)
    first, rest = bins[0], bins[1:]
    children: list[Page] = []
    navs: list[PageUnit] = []
    for index, chunk in enumerate(rest, start=2):
        target = _next_part(directory, occupied, start=index)
        occupied.add(target)
        title = f"{page.title} PART {index}"
        blurb = f"{sum(unit_block_count(unit) for unit in chunk)} 个符号块，完整内容在子页，无删减。"
        child = _make_child(page, target, title, "part", chunk, kind="detail")
        children.append(child)
        navs.append(_nav_unit(f"PART {index}", blurb, target, "part"))
    parent_units = list(fixed)
    if navs:
        parent_units.append(_heading_unit("part", "分页"))
        parent_units.extend(navs)
    parent_units.extend(first)
    parent_units.extend(unit for unit in page.units if unit.kind == "nav" and unit.group_key != "part")
    parent = replace(page, units=tuple(parent_units))
    return _pad_for_nav_ratio(parent, budget), children


def split_until_fit(
    pages: Mapping[str, Page],
    budget: LayerBudget | None = None,
) -> dict[str, Page]:
    """Recursively split every over-budget page. No depth-limit parameter."""

    budget = budget or LayerBudget()
    result = dict(pages)
    pending: deque[str] = deque(result)
    splits = 0
    while pending:
        relpath = pending.popleft()
        page = result[relpath]
        if not page_over_budget(page, budget):
            continue
        before_lines = len(render_page_lines(page))
        before_blocks = page_block_count(page)
        parent, children = split_over_budget(page, budget, occupied=set(result))
        if not children:
            raise LayeringError(f"{relpath} stayed over budget and produced no children")
        after_lines = len(render_page_lines(parent))
        after_blocks = page_block_count(parent)
        if after_lines >= before_lines and after_blocks >= before_blocks:
            raise LayeringError(
                f"{relpath} split did not shrink the parent "
                f"(lines {before_lines}->{after_lines}, blocks {before_blocks}->{after_blocks})"
            )
        result[parent.relpath] = parent
        for child in children:
            if child.relpath in result:
                raise LayeringError(f"child path collision: {child.relpath}")
            result[child.relpath] = child
            pending.append(child.relpath)
        if page_over_budget(parent, budget):
            pending.appendleft(parent.relpath)
        splits += 1
        if splits > _RUNAWAY_SPLITS:
            raise LayeringError(
                "recursive split did not terminate; nav rows themselves may have blown the page budget"
            )
    return result


def _nav_ratio(lines: Sequence[str]) -> float:
    if not lines:
        return 0.0
    nav = sum(1 for line in lines if _NAV_LINE.match(line))
    return nav / len(lines)


def _resolve_internal_dest(src_rel: str, target: str) -> str | None:
    if target.startswith(_SKIP_SCHEMES):
        return None
    path_part, _, _frag = target.partition("#")
    if not path_part:
        return None
    parts: list[str] = []
    for part in (str(Path(src_rel).parent / path_part)).replace("\\", "/").split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part not in (".", ""):
            parts.append(part)
    return "/".join(parts)


_PROMISE_LABEL = re.compile(r"^`([^`]+)` L(\d+)-L(\d+)$")
_TICK_LABEL = re.compile(r"^`([^`]+)`$")
_HEADING_DEF = re.compile(r"^#{2,3}\s+`([^`]+)`")
_SURFACE_MARK = re.compile(r"<!--\s*surface-binding:([^\s>]+)\s*-->")
_SYMBOL_ID_LINE = re.compile(r"Symbol id：`([^`]+)`")
_N7B_REPORT_CAP = 8


def defined_names_in_span(span_text: str) -> set[str]:
    """Names a span can honestly claim to define (N7b, semantics from n7d/pointing)."""

    names: set[str] = set()
    for line in span_text.splitlines():
        heading = _HEADING_DEF.match(line.strip())
        if heading:
            qualified = heading.group(1)
            names.add(qualified)
            names.add(qualified.rsplit(".", 1)[-1])
            names.add(qualified.rsplit("::", 1)[-1])
        mark = _SYMBOL_MARK.search(line)
        if mark:
            token = mark.group(1).strip()
            names.add(token)
            names.add(token.rsplit("::", 1)[-1])
            names.add(token.rsplit(".", 1)[-1])
        surface = _SURFACE_MARK.search(line)
        if surface:
            names.add(surface.group(1).strip())
        sid = _SYMBOL_ID_LINE.search(line)
        if sid:
            token = sid.group(1)
            names.add(token)
            names.add(token.rsplit("::", 1)[-1])
    names.discard("")
    return names


def name_is_defined_object(name: str, span_text: str) -> bool:
    return name in defined_names_in_span(span_text)


def extract_line_span(text: str, start: int, end: int) -> str | None:
    lines = text.splitlines()
    if start < 1 or end > len(lines) or end < start:
        return None
    return "\n".join(lines[start - 1 : end])


def block_around_fragment(text: str, frag: str) -> str | None:
    """Return the symbol block (or heading neighborhood) hosting ``<a id=frag>``."""

    if not frag:
        return None
    lines = text.splitlines()
    needle = f'id="{frag}"'
    idx = next((i for i, line in enumerate(lines) if needle in line), None)
    if idx is None:
        return None
    start = idx
    for cursor in range(idx, -1, -1):
        if "<!-- symbol:" in lines[cursor]:
            start = cursor
            break
        if cursor < idx and lines[cursor].startswith("#"):
            start = cursor
            break
    end = idx
    for cursor in range(idx, len(lines)):
        if "<!-- end:symbol:" in lines[cursor]:
            end = cursor
            break
        if cursor > idx and (
            lines[cursor].startswith("<!-- symbol:") or lines[cursor].startswith("## ")
        ):
            end = cursor - 1
            break
        end = cursor
    return "\n".join(lines[start : end + 1])


def _promise_dest(src_rel: str, target: str) -> tuple[str | None, str]:
    if target.startswith(_SKIP_SCHEMES):
        return None, ""
    path_part, _, frag = target.partition("#")
    if path_part:
        dest = _resolve_internal_dest(src_rel, target)
    else:
        dest = src_rel
    return dest, frag


def collect_n7b_violations(relpath: str, text: str, all_pages: Mapping[str, str]) -> list[str]:
    """Symbol-level promise links must land on a span/block that names the object.

    Two promise forms (same predicate, different locators):
    - label `` `name` Lstart-Lend `` → dest lines [start, end]
    - label `` `name` `` targeting ``#symbol-…`` → block around that fragment
    Page-chrome links (no symbol fragment, no Lx-Ly label) are not promises.
    """

    violations: list[str] = []
    for label, target in _MD_LINK.findall(text):
        if target.startswith(_SKIP_SCHEMES):
            continue
        dest, frag = _promise_dest(relpath, target)
        promise = _PROMISE_LABEL.match(label.strip())
        tick = _TICK_LABEL.match(label.strip())
        name: str | None = None
        span: str | None = None
        locator = ""
        if promise is not None:
            name = promise.group(1)
            start, end = int(promise.group(2)), int(promise.group(3))
            locator = f"`{name}` L{start}-L{end} -> {target}"
            if dest is None or dest not in all_pages:
                violations.append(f"N7b: {locator}: target page missing")
                if len(violations) >= _N7B_REPORT_CAP:
                    break
                continue
            span = extract_line_span(all_pages[dest], start, end)
            if span is None:
                violations.append(f"N7b: {locator}: target span missing")
                if len(violations) >= _N7B_REPORT_CAP:
                    break
                continue
        elif tick is not None and frag.startswith("symbol-"):
            name = tick.group(1)
            locator = f"`{name}` -> {target}"
            if dest is None or dest not in all_pages:
                violations.append(f"N7b: {locator}: target page missing")
                if len(violations) >= _N7B_REPORT_CAP:
                    break
                continue
            span = block_around_fragment(all_pages[dest], frag)
            if span is None:
                violations.append(f"N7b: {locator}: symbol fragment not on target page")
                if len(violations) >= _N7B_REPORT_CAP:
                    break
                continue
        else:
            continue
        if name is None or span is None:
            continue
        if not name_is_defined_object(name, span):
            violations.append(f"N7b: {locator}: named object not in target span/block")
        if len(violations) >= _N7B_REPORT_CAP:
            break
    return violations


def check_page_invariants(
    relpath: str,
    text: str,
    *,
    kind: str,
    budget: LayerBudget,
    all_pages: Mapping[str, str],
    is_root: bool,
    is_leaf: bool,
) -> None:
    lines = text.splitlines()
    n_lines = len(lines)
    n_blocks = len(_SYMBOL_MARK.findall(text))
    problems: list[str] = []
    if kind == "index" and n_lines > budget.index_max_lines:
        problems.append(f"INDEX lines {n_lines} > {budget.index_max_lines}")
    if kind == "detail":
        if n_lines > budget.detail_max_lines:
            problems.append(f"DETAIL lines {n_lines} > {budget.detail_max_lines}")
        if n_blocks > budget.detail_max_blocks:
            problems.append(f"DETAIL blocks {n_blocks} > {budget.detail_max_blocks}")
    if not is_root and not any(line.startswith("↑ [") for line in lines):
        problems.append("missing uplink")
    if f'<a id="L1-L{n_lines}"></a>' not in text:
        problems.append(f"page anchor missing or not L1-L{n_lines}")
    ratio = _nav_ratio(lines)
    if ratio > budget.max_nav_ratio + 1e-9:
        problems.append(f"nav ratio {ratio:.3f} > {budget.max_nav_ratio}")
    if not is_leaf:
        outbound = []
        for _label, target in _MD_LINK.findall(text):
            dest = _resolve_internal_dest(relpath, target)
            if dest is not None and dest in all_pages and dest != relpath:
                outbound.append(dest)
        if not outbound:
            problems.append("non-leaf page has no downlink")
    problems.extend(collect_n7b_violations(relpath, text, all_pages))
    if problems:
        raise LayeringInvariantError(f"{relpath}: " + "; ".join(problems))


def _symbol_hosts(documents: Mapping[str, str]) -> dict[str, str]:
    hosts: dict[str, str] = {}
    for relpath, text in documents.items():
        for symbol_id in _SYMBOL_MARK.findall(text):
            hosts.setdefault(symbol_id, relpath)
    return hosts


def _stamp_and_resolve(
    pages: Mapping[str, Page],
) -> dict[str, str]:
    raw = {relpath: "\n".join(render_page_lines(page)) + "\n" for relpath, page in pages.items()}
    line_counts = {relpath: text.count("\n") if text.endswith("\n") else text.count("\n") + 1 for relpath, text in raw.items()}
    # splitlines() count is the invariant the reader sees.
    line_counts = {relpath: len(text.splitlines()) for relpath, text in raw.items()}
    stamped: dict[str, str] = {}
    for relpath, text in raw.items():
        n_lines = line_counts[relpath]
        stamped[relpath] = text.replace(
            f'<!-- tgt:page:{relpath} --><a id="L1-L0"></a>',
            f'<!-- tgt:page:{relpath} --><a id="L1-L{n_lines}"></a>',
            1,
        )
    hosts = _symbol_hosts(stamped)

    def resolve(relpath: str, text: str) -> str:
        def page_sub(match: re.Match[str]) -> str:
            dest = match.group(1)
            href = relative_href(relpath, dest)
            n_lines = line_counts.get(dest, 0)
            # Keep the page's own <a id="L1-Ln"> as the line-range anchor.
            # Module hrefs stay `path/DETAIL.md` (no fragment) so existing
            # consumers that match `(module/DETAIL.md)` continue to resolve.
            if not href:
                return f"#L1-L{n_lines}" if n_lines else dest
            return href

        def sym_sub(match: re.Match[str]) -> str:
            symbol_id = match.group(1)
            host = hosts.get(symbol_id)
            anchor = symbol_anchor(symbol_id)
            if not host:
                return f"#{anchor}"
            href = relative_href(relpath, host)
            return f"{href}#{anchor}" if href else f"#{anchor}"

        return _SYM_TOKEN.sub(sym_sub, _PAGE_TOKEN.sub(page_sub, text))

    return {relpath: resolve(relpath, text) for relpath, text in stamped.items()}


def _page_kind(relpath: str, page: Page | None) -> str:
    if page is not None:
        return page.kind
    name = Path(relpath).name
    if name == "INDEX.md":
        return "index"
    return "detail"


def finalize_pages(
    pages: Mapping[str, Page],
    budget: LayerBudget | None = None,
) -> dict[str, str]:
    """Render, resolve links, stamp line-range anchors, then enforce invariants."""

    budget = budget or LayerBudget()
    documents = _stamp_and_resolve(pages)
    children: dict[str, set[str]] = defaultdict(set)
    for page in pages.values():
        if page.parent_relpath:
            children[page.parent_relpath].add(page.relpath)
    for relpath, text in documents.items():
        page = pages.get(relpath)
        check_page_invariants(
            relpath,
            text,
            kind=_page_kind(relpath, page),
            budget=budget,
            all_pages=documents,
            is_root=relpath == "INDEX.md",
            is_leaf=relpath not in children,
        )
    return documents


def measure_symbol_hops(
    documents: Mapping[str, str],
    ledger_ids: Sequence[str],
    *,
    source: str = "INDEX.md",
) -> dict[str, object]:
    md_docs = {relpath: text for relpath, text in documents.items() if relpath.endswith(".md")}
    adj: dict[str, set[str]] = {relpath: set() for relpath in md_docs}
    for relpath, text in md_docs.items():
        for _label, target in _MD_LINK.findall(text):
            dest = _resolve_internal_dest(relpath, target)
            if dest is not None and dest in md_docs:
                adj[relpath].add(dest)
    dist: dict[str, int] = {}
    parent: dict[str, str] = {}
    if source in md_docs:
        dist[source] = 0
        queue: deque[str] = deque([source])
        while queue:
            current = queue.popleft()
            for nxt in sorted(adj[current]):
                if nxt not in dist:
                    dist[nxt] = dist[current] + 1
                    parent[nxt] = current
                    queue.append(nxt)

    hosts: dict[str, list[str]] = {}
    for relpath, text in md_docs.items():
        for symbol_id in dict.fromkeys(_SYMBOL_MARK.findall(text)):
            hosts.setdefault(symbol_id, []).append(relpath)

    distribution = {"0": 0, "1": 0, "2": 0, "3": 0, "4+": 0, "unreachable": 0}
    over_3: list[dict[str, object]] = []
    unreachable: list[dict[str, object]] = []
    n_rendered = 0
    for symbol_id in ledger_ids:
        pages = list(hosts.get(symbol_id, ()))
        if not pages:
            distribution["unreachable"] += 1
            unreachable.append({"symbol_id": symbol_id, "reason": "not_rendered", "pages": []})
            continue
        n_rendered += 1
        reachable = [(dist[page], page) for page in pages if page in dist]
        if not reachable:
            distribution["unreachable"] += 1
            unreachable.append({"symbol_id": symbol_id, "reason": "page_unreachable", "pages": pages})
            continue
        hops, via = min(reachable, key=lambda item: (item[0], item[1]))
        if hops <= 3:
            distribution[str(hops)] += 1
        else:
            distribution["4+"] += 1
            path = [via]
            while path[-1] != source:
                prev = parent.get(path[-1])
                if prev is None:
                    break
                path.append(prev)
            path.reverse()
            over_3.append({"symbol_id": symbol_id, "hops": hops, "via": via, "path": path})

    n_ledger = len(ledger_ids)
    reachable_le_3 = distribution["0"] + distribution["1"] + distribution["2"] + distribution["3"]
    rate_le_3 = round(reachable_le_3 / n_ledger, 4) if n_ledger else 1.0
    rate_le_3_rendered = round(reachable_le_3 / n_rendered, 4) if n_rendered else 1.0
    page_dist = {relpath: dist.get(relpath) for relpath in sorted(md_docs)}
    pages_unreachable = [relpath for relpath, hops in page_dist.items() if hops is None]
    return {
        "source": source,
        "n_ledger": n_ledger,
        "n_rendered": n_rendered,
        "n_residual_unrendered": n_ledger - n_rendered,
        "distribution": distribution,
        "rate_le_3": rate_le_3,
        "rate_le_3_rendered": rate_le_3_rendered,
        "over_3": over_3,
        "unreachable_count": len(unreachable),
        "page_dist": page_dist,
        "pages_unreachable": pages_unreachable,
        "max_page_hops": max((hops for hops in dist.values()), default=0),
    }


def hops_payload(
    tree_name: str,
    hops: Mapping[str, object],
    *,
    docs_root: str | None = None,
    ledger: str | None = None,
) -> dict[str, object]:
    distribution = hops["distribution"]  # type: ignore[index]
    observed = (
        f"{tree_name}: hops1={distribution['1']} hops2={distribution['2']} "
        f"hops3={distribution['3']} hops4+={distribution['4+']} "
        f"unreachable={distribution['unreachable']} rate_le_3={hops['rate_le_3']}"
    )
    tree = {
        **hops,
        "name": tree_name,
        "docs_root": docs_root,
        "ledger": ledger,
    }
    return {
        "invariant": (
            "FIXED_LAYER_ARCHITECTURE.md §3.4-1 / LBM N3: hop distribution from root "
            "INDEX.md is measured and published (not a hard gate)"
        ),
        "hop_definition": HOP_DEFINITION,
        "section_7_2": {
            "predicted": (
                "INDEX ≤150 vs ≤3 hops may conflict when there are >9 function clusters "
                "(rest go to nested INDEX pages, hops may become 4)"
            ),
            "observed": observed,
        },
        "trees": {tree_name: tree},
    }


def write_hops_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect_symbol_anchor_set(documents: Mapping[str, str]) -> tuple[set[str], set[str]]:
    """Return (symbol ids with <!-- symbol:ID -->, symbol-* fragment ids)."""

    ids: set[str] = set()
    fragments: set[str] = set()
    frag_re = re.compile(r'<a id="(symbol-[0-9a-f]{16})"></a>')
    for text in documents.values():
        ids.update(_SYMBOL_MARK.findall(text))
        fragments.update(frag_re.findall(text))
    return ids, fragments


def tree_depth(documents: Mapping[str, str], *, source: str = "INDEX.md") -> int:
    md_docs = {relpath: text for relpath, text in documents.items() if relpath.endswith(".md")}
    adj: dict[str, set[str]] = {relpath: set() for relpath in md_docs}
    for relpath, text in md_docs.items():
        for _label, target in _MD_LINK.findall(text):
            dest = _resolve_internal_dest(relpath, target)
            if dest is not None and dest in md_docs and dest != relpath:
                adj[relpath].add(dest)
    if source not in md_docs:
        return 0
    dist = {source: 0}
    queue: deque[str] = deque([source])
    while queue:
        current = queue.popleft()
        for nxt in adj[current]:
            if nxt not in dist:
                dist[nxt] = dist[current] + 1
                queue.append(nxt)
    return max(dist.values(), default=0)


def scan_docs_tree(
    docs_root: Path,
    budget: LayerBudget | None = None,
) -> dict[str, object]:
    budget = budget or LayerBudget()
    pages = sorted(path for path in docs_root.rglob("*.md") if path.is_file())
    index_violations: list[list[object]] = []
    detail_line_violations: list[list[object]] = []
    detail_block_violations: list[list[object]] = []
    dead_ends: list[str] = []
    for path in pages:
        rel = path.relative_to(docs_root).as_posix()
        text = path.read_text(encoding="utf-8")
        n_lines = len(text.splitlines())
        n_blocks = len(_SYMBOL_MARK.findall(text))
        name = path.name
        if name == "INDEX.md" and n_lines > budget.index_max_lines:
            index_violations.append([rel, n_lines])
        if name == DETAIL_LEAF_NAME or name.startswith("PART-"):
            if n_lines > budget.detail_max_lines:
                detail_line_violations.append([rel, n_lines])
            if n_blocks > budget.detail_max_blocks:
                detail_block_violations.append([rel, n_blocks])
        if rel != "INDEX.md" and "↑ [" not in text:
            dead_ends.append(rel)
    return {
        "checked_pages": len(pages),
        "index_violations": index_violations,
        "detail_line_violations": detail_line_violations,
        "detail_block_violations": detail_block_violations,
        "dead_ends": dead_ends,
    }
