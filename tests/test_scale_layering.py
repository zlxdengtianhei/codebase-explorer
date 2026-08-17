"""Scale-cell tests: M1 suffix split and M2 _clusters/ nav-ratio layering."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.semantic.layering import (
    DETAIL_LEAF_NAME,
    LayerBudget,
    LayeringError,
    LayeringInvariantError,
    Page,
    PageUnit,
    _explode_file_unit,
    _NAV_LINE,
    finalize_pages,
    iter_unit_lines,
    page_over_budget,
    render_page_lines,
    split_until_fit,
)

_LAYERING_SRC = Path(__file__).resolve().parents[1] / "src" / "semantic" / "layering.py"


def _heading(group_key: str, title: str) -> PageUnit:
    return PageUnit(
        unit_id=f"heading:{group_key}",
        kind="heading",
        group_key=group_key,
        name=title,
        one_liner="",
        lines=(f"## {title}", ""),
    )


def _suffix_rows(n: int, *, path: str = "fat.py") -> list[str]:
    rows = ["### 未覆盖与 stale 状态", ""]
    for index in range(n):
        rows.append(f"- `{path}::fn{index}`：uncovered；pending semantic explanation")
    rows.append("")
    return rows


def _suffix_file_unit(n_rows: int, *, path: str = "fat.py") -> PageUnit:
    suffix = tuple(_suffix_rows(n_rows, path=path))
    return PageUnit(
        unit_id=f"file:{path}",
        kind="file",
        group_key="layer:0",
        name=path,
        one_liner="0 个 fresh 符号",
        lines=(f"## `{path}`", ""),
        suffix_lines=suffix,
        symbol_ids=(),
        block_count=0,
    )


def _detail_with_suffix(n_rows: int, *, relpath: str = f"mod/{DETAIL_LEAF_NAME}") -> Page:
    file_unit = _suffix_file_unit(n_rows)
    return Page(
        relpath=relpath,
        kind="detail",
        title="mod 模块语义详情",
        parent_relpath="INDEX.md",
        parent_title="root",
        units=(
            PageUnit(
                unit_id="overview",
                kind="fixed",
                group_key="overview",
                name="overview",
                one_liner="",
                lines=("## 模块概览", "", "Fixture module overview.", ""),
            ),
            file_unit,
        ),
    )


def _root_pointing_at(detail_rel: str) -> Page:
    return Page(
        relpath="INDEX.md",
        kind="index",
        title="root",
        parent_relpath=None,
        parent_title="",
        units=(
            PageUnit(
                unit_id="link",
                kind="nav",
                group_key="module",
                name="mod",
                one_liner="module",
                lines=(f"- [mod](@@PAGE:{detail_rel}@@)：module",),
                nav_target=detail_rel,
            ),
        ),
    )


def _module_entry(index: int) -> PageUnit:
    target = f"mod-{index}/{DETAIL_LEAF_NAME}"
    return PageUnit(
        unit_id=f"module:{index}",
        kind="entry",
        group_key="module",
        name=f"capability-{index}",
        one_liner="cluster responsibility sentence without omission.",
        lines=(
            f"- [capability-{index}](@@PAGE:{target}@@)：1 个文件，0/10 fresh，0 stale。"
            "cluster responsibility sentence without omission.",
        ),
        nav_target=target,
    )


def _clusters_page(n_modules: int) -> Page:
    return Page(
        relpath="_clusters/INDEX.md",
        kind="index",
        title="功能模块",
        parent_relpath="INDEX.md",
        parent_title="root",
        units=(
            PageUnit(
                unit_id="blurb",
                kind="fixed",
                group_key="fixed",
                name="blurb",
                one_liner="",
                lines=(
                    "本页是分层入口。被下沉到子页的条目在子页完整保留，没有删除、省略或截断。",
                    f"本组共 {n_modules} 条，按单页预算继续嵌套。",
                    "导航行只指向子页；符号解释与残差原文均在对应子页。",
                    "本分层由页预算推导，深度不是配置项。",
                    "公共面、模块入口与残差清单使用同一套分裂规则。",
                    "读者从本页选择分组后下钻，不必在本页读完全部分组内容。",
                    "若一组仍然超预算，渲染器会再加一层，而不是裁剪。",
                    "锚点带行区间；上行链接保证无死胡同。",
                ),
            ),
            _heading("module", "功能模块"),
            *(_module_entry(index) for index in range(n_modules)),
        ),
    )


def test_only_one_live_explode_file_unit() -> None:
    tree = ast.parse(_LAYERING_SRC.read_text(encoding="utf-8"))
    defs = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_explode_file_unit"]
    assert len(defs) == 1, [(node.lineno, node.end_lineno) for node in defs]


def test_suffix_only_unit_splits_at_line_boundaries() -> None:
    unit = _suffix_file_unit(500)
    budget = LayerBudget()
    assert unit.block_count == 0
    pieces = _explode_file_unit(unit, budget)
    assert len(pieces) >= 2
    original = list(iter_unit_lines(unit))
    rebuilt: list[str] = []
    for piece in pieces:
        rebuilt.extend(iter_unit_lines(piece))
    for line in _suffix_rows(500):
        assert line in rebuilt
    assert all("\n" not in line for piece in pieces for line in piece.suffix_lines)
    # No original suffix row dropped.
    original_rows = [line for line in original if line.startswith("- `")]
    rebuilt_rows = [line for line in rebuilt if line.startswith("- `")]
    assert original_rows == rebuilt_rows


def test_suffix_detail_publishes_without_cutting() -> None:
    detail = _detail_with_suffix(420)
    budget = LayerBudget()
    assert page_over_budget(detail, budget)
    original_rows = [line for line in render_page_lines(detail) if line.startswith("- `")]
    assert len(original_rows) == 420
    layered = split_until_fit(
        {"INDEX.md": _root_pointing_at(detail.relpath), detail.relpath: detail},
        budget,
    )
    detail_pages = [page for page in layered.values() if page.kind == "detail"]
    assert len(detail_pages) >= 2
    for page in detail_pages:
        assert not page_over_budget(page, budget), (page.relpath, page_over_budget(page, budget))
    documents = finalize_pages(layered, budget)
    rebuilt_rows = [line for text in documents.values() for line in text.splitlines() if line.startswith("- `")]
    assert rebuilt_rows == original_rows
    parts = [rel for rel in documents if Path(rel).name.startswith("PART-")]
    assert parts
    for rel, text in documents.items():
        if rel == "INDEX.md":
            continue
        assert "↑ [" in text, rel


def test_recursive_suffix_split_preserves_every_row() -> None:
    detail = _detail_with_suffix(2000)
    budget = LayerBudget()
    original_rows = [line for line in render_page_lines(detail) if line.startswith("- `")]
    layered = split_until_fit(
        {"INDEX.md": _root_pointing_at(detail.relpath), detail.relpath: detail},
        budget,
    )
    documents = finalize_pages(layered, budget)
    rebuilt_rows = [line for text in documents.values() for line in text.splitlines() if line.startswith("- `")]
    assert rebuilt_rows == original_rows
    assert len(layered) >= 6


def test_negative_control_suffix_raises_original_layering_error() -> None:
    detail = _detail_with_suffix(420)
    budget = LayerBudget(scale_layering=False)
    with pytest.raises(LayeringError, match="cannot split further without cutting content"):
        split_until_fit(
            {"INDEX.md": _root_pointing_at(detail.relpath), detail.relpath: detail},
            budget,
        )


def test_clusters_nav_ratio_finalizes_under_25_percent() -> None:
    n_modules = 50
    clusters = _clusters_page(n_modules)
    root = Page(
        relpath="INDEX.md",
        kind="index",
        title="root",
        parent_relpath=None,
        parent_title="",
        units=(
            PageUnit(
                unit_id="nav-clusters",
                kind="nav",
                group_key="module",
                name="功能模块",
                one_liner="功能模块入口的完整清单，无删减。",
                lines=("- [功能模块](@@PAGE:_clusters/INDEX.md@@)：功能模块入口的完整清单，无删减。",),
                nav_target="_clusters/INDEX.md",
            ),
        ),
    )
    budget = LayerBudget()
    layered = split_until_fit({"INDEX.md": root, clusters.relpath: clusters}, budget)
    documents = finalize_pages(layered, budget)
    cluster_pages = [rel for rel in documents if rel.startswith("_clusters/")]
    assert cluster_pages
    for rel, text in documents.items():
        lines = text.splitlines()
        nav = sum(1 for line in lines if _NAV_LINE.match(line))
        ratio = nav / len(lines) if lines else 0.0
        assert ratio <= budget.max_nav_ratio + 1e-9, (rel, ratio, nav, len(lines))
        if rel != "INDEX.md":
            assert "↑ [" in text
    names = [line for text in documents.values() for line in text.splitlines() if "capability-" in line and line.startswith("- [")]
    assert len(names) == n_modules


def test_negative_control_clusters_raises_original_nav_ratio_error() -> None:
    n_modules = 36
    clusters = _clusters_page(n_modules)
    root = Page(
        relpath="INDEX.md",
        kind="index",
        title="root",
        parent_relpath=None,
        parent_title="",
        units=(
            PageUnit(
                unit_id="nav-clusters",
                kind="nav",
                group_key="module",
                name="功能模块",
                one_liner="功能模块入口的完整清单，无删减。",
                lines=("- [功能模块](@@PAGE:_clusters/INDEX.md@@)：功能模块入口的完整清单，无删减。",),
                nav_target="_clusters/INDEX.md",
            ),
        ),
    )
    budget = LayerBudget(scale_layering=False)
    layered = split_until_fit({"INDEX.md": root, clusters.relpath: clusters}, budget)
    with pytest.raises(LayeringInvariantError, match="nav ratio"):
        finalize_pages(layered, budget)


def test_legacy_explode_is_noop_on_suffix_only() -> None:
    unit = _suffix_file_unit(500)
    pieces = _explode_file_unit(unit, LayerBudget(scale_layering=False))
    assert pieces == [unit]
