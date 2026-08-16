"""Map ClusterInput records onto the nested page tree (EV-16 / EV-04).

Promote (any): files>12 ∨ symbols>60 ∨ DAG layers≥3 ∨ estimated DETAIL lines>400.
Demote: child files≤2 ∧ symbols≤10 → merge into parent DETAIL, no extra INDEX.
Hard caps: INDEX ≤150 lines (enforced at render); DETAIL ≤40 symbol blocks or
400 lines (enforced here by packing). Hop budget: root is depth 0; we emit at
most one extra INDEX under a cluster so a symbol page is ≤3 hops from root.
"""

from __future__ import annotations

from collections.abc import Mapping

from src.semantic.models import SemanticLedger
from src.synthesis.variant_a.cluster_source import cluster_dir_map
from src.synthesis.variant_a.models import ClusterInput, PageKind, PageSpec


PROMOTE_FILES = 12
PROMOTE_SYMBOLS = 60
PROMOTE_LAYERS = 3
PROMOTE_EST_LINES = 400
DEMOTE_FILES = 2
DEMOTE_SYMBOLS = 10
MAX_SYMBOLS_PER_DETAIL = 40
MAX_DETAIL_LINES = 400
PACK_TARGET_LINES = 360
HEADER_RESERVE = 22
LINES_PER_BLOCK_FLOOR = 12
ROOT_ID = "root"


def estimate_detail_lines(n_symbols: int, n_files: int) -> int:
    return HEADER_RESERVE + n_files * 4 + n_symbols * 14


def should_promote(cluster: ClusterInput) -> bool:
    if cluster.is_unassigned:
        return False
    n_files = len(cluster.paths)
    n_symbols = len(cluster.symbol_ids)
    return (
        n_files > PROMOTE_FILES
        or n_symbols > PROMOTE_SYMBOLS
        or cluster.dag_layer_count >= PROMOTE_LAYERS
        or estimate_detail_lines(n_symbols, n_files) > PROMOTE_EST_LINES
    )


def should_demote(n_files: int, n_symbols: int) -> bool:
    return n_files <= DEMOTE_FILES and n_symbols <= DEMOTE_SYMBOLS


def _ordered_symbols(cluster: ClusterInput, ledger: SemanticLedger) -> list[str]:
    def key(symbol_id: str) -> tuple[int, str, int, str]:
        record = ledger.symbols[symbol_id]
        layer = cluster.dag_layer_by_path.get(record.path, 0)
        return (layer, record.path, record.span[0], symbol_id)

    return sorted(cluster.symbol_ids, key=key)


def _files_in_order(cluster: ClusterInput) -> list[str]:
    return sorted(cluster.paths, key=lambda path: (cluster.dag_layer_by_path.get(path, 0), path))


def _block_line_count(symbol_id: str, ledger: SemanticLedger) -> int:
    record = ledger.symbols[symbol_id]
    text = ""
    if record.explanation is not None:
        text = record.explanation.text.strip()
    text_lines = max(1, text.count("\n") + 1)
    return LINES_PER_BLOCK_FLOOR + text_lines


def pack_symbol_pages(
    symbol_ids: list[str],
    ledger: SemanticLedger,
) -> list[list[str]]:
    """Greedy pack under 40 blocks and ~400 lines. Keep going; never drop a symbol."""

    pages: list[list[str]] = []
    current: list[str] = []
    current_lines = HEADER_RESERVE
    current_files: set[str] = set()
    for symbol_id in symbol_ids:
        block = _block_line_count(symbol_id, ledger)
        path = ledger.symbols[symbol_id].path
        file_header = 0 if path in current_files else 3
        catalog = 1
        overflow = (
            current
            and (
                len(current) >= MAX_SYMBOLS_PER_DETAIL
                or current_lines + block + catalog + file_header > PACK_TARGET_LINES
            )
        )
        if overflow:
            pages.append(current)
            current = []
            current_lines = HEADER_RESERVE
            current_files = set()
            file_header = 3
        current.append(symbol_id)
        current_files.add(path)
        current_lines += block + catalog + file_header
    if current:
        pages.append(current)
    if not pages and not symbol_ids:
        pages.append([])
    return pages


def _part_name(index: int, total: int) -> str:
    if total == 1:
        return "DETAIL.md"
    return f"PART-{index}.md"


def plan_page_tree(
    clusters: tuple[ClusterInput, ...],
    ledger: SemanticLedger,
) -> tuple[PageSpec, ...]:
    pages: dict[str, PageSpec] = {}
    root_children: list[str] = []

    assigned = [c for c in clusters if not c.is_unassigned]
    unassigned = [c for c in clusters if c.is_unassigned]
    dir_of = cluster_dir_map(clusters)

    for cluster in assigned:
        dir_name = dir_of[cluster.cluster_id]
        symbols = _ordered_symbols(cluster, ledger)
        packed = pack_symbol_pages(symbols, ledger)
        promote = should_promote(cluster) and not should_demote(len(cluster.paths), len(cluster.symbol_ids))

        if promote:
            index_id = f"idx:{cluster.cluster_id}"
            child_ids: list[str] = []
            for part_i, chunk in enumerate(packed, start=1):
                part_id = f"part:{cluster.cluster_id}:{part_i}"
                fname = _part_name(part_i, len(packed))
                pages[part_id] = PageSpec(
                    page_id=part_id,
                    relpath=f"{dir_name}/{fname}",
                    kind=PageKind.PART if len(packed) > 1 else PageKind.DETAIL,
                    title=f"{cluster.display_name} {fname.removesuffix('.md')}",
                    parent_id=index_id,
                    child_ids=(),
                    symbol_ids=tuple(chunk),
                    paths=tuple(dict.fromkeys(ledger.symbols[s].path for s in chunk)),
                    cluster_id=cluster.cluster_id,
                    layer=None,
                )
                child_ids.append(part_id)
            pages[index_id] = PageSpec(
                page_id=index_id,
                relpath=f"{dir_name}/INDEX.md",
                kind=PageKind.CLUSTER_INDEX,
                title=cluster.display_name,
                parent_id=ROOT_ID,
                child_ids=tuple(child_ids),
                symbol_ids=(),
                paths=cluster.paths,
                cluster_id=cluster.cluster_id,
                synthesis_page_id=f"cluster-{cluster.cluster_id}",
            )
            root_children.append(index_id)
        else:
            if len(packed) == 1:
                page_id = f"detail:{cluster.cluster_id}"
                pages[page_id] = PageSpec(
                    page_id=page_id,
                    relpath=f"{dir_name}/DETAIL.md",
                    kind=PageKind.DETAIL,
                    title=cluster.display_name,
                    parent_id=ROOT_ID,
                    child_ids=(),
                    symbol_ids=tuple(packed[0]),
                    paths=cluster.paths,
                    cluster_id=cluster.cluster_id,
                    synthesis_page_id=f"cluster-{cluster.cluster_id}",
                    inline_fragment=True,
                )
                root_children.append(page_id)
            else:
                index_id = f"idx:{cluster.cluster_id}"
                child_ids = []
                for part_i, chunk in enumerate(packed, start=1):
                    part_id = f"part:{cluster.cluster_id}:{part_i}"
                    pages[part_id] = PageSpec(
                        page_id=part_id,
                        relpath=f"{dir_name}/PART-{part_i}.md",
                        kind=PageKind.PART,
                        title=f"{cluster.display_name} PART-{part_i}",
                        parent_id=index_id,
                        child_ids=(),
                        symbol_ids=tuple(chunk),
                        paths=tuple(dict.fromkeys(ledger.symbols[s].path for s in chunk)),
                        cluster_id=cluster.cluster_id,
                    )
                    child_ids.append(part_id)
                pages[index_id] = PageSpec(
                    page_id=index_id,
                    relpath=f"{dir_name}/INDEX.md",
                    kind=PageKind.CLUSTER_INDEX,
                    title=cluster.display_name,
                    parent_id=ROOT_ID,
                    child_ids=tuple(child_ids),
                    symbol_ids=(),
                    paths=cluster.paths,
                    cluster_id=cluster.cluster_id,
                    synthesis_page_id=f"cluster-{cluster.cluster_id}",
                )
                root_children.append(index_id)

    for cluster in unassigned:
        page_id = "unassigned"
        pages[page_id] = PageSpec(
            page_id=page_id,
            relpath="_unassigned/DETAIL.md",
            kind=PageKind.UNASSIGNED,
            title="unassigned",
            parent_id=ROOT_ID,
            child_ids=(),
            symbol_ids=cluster.symbol_ids,
            paths=cluster.paths,
            cluster_id="unassigned",
            inline_fragment=True,
        )
        root_children.append(page_id)

    pages[ROOT_ID] = PageSpec(
        page_id=ROOT_ID,
        relpath="INDEX.md",
        kind=PageKind.ROOT_INDEX,
        title="root",
        parent_id=None,
        child_ids=tuple(root_children),
        symbol_ids=(),
        paths=(),
        synthesis_page_id="library",
    )
    return tuple(pages[key] for key in (ROOT_ID, *root_children, *sorted(set(pages) - {ROOT_ID, *root_children})))


def symbol_locator(pages: tuple[PageSpec, ...]) -> dict[str, str]:
    """symbol_id → page relpath that contains its block."""

    located: dict[str, str] = {}
    for page in pages:
        for symbol_id in page.symbol_ids:
            located[symbol_id] = page.relpath
    return located


def pages_by_id(pages: tuple[PageSpec, ...]) -> dict[str, PageSpec]:
    return {page.page_id: page for page in pages}


def hops_from_root(pages: tuple[PageSpec, ...]) -> Mapping[str, int]:
    by_id = pages_by_id(pages)
    dist: dict[str, int] = {ROOT_ID: 0}
    queue = [ROOT_ID]
    while queue:
        current = queue.pop(0)
        for child in by_id[current].child_ids:
            if child not in dist:
                dist[child] = dist[current] + 1
                queue.append(child)
    return dist
