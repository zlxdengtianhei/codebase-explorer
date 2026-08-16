"""Recursive layering: split-until-fit, invariants, and flask/httpx negative control."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.semantic.layering import (
    DETAIL_LEAF_NAME,
    LayerBudget,
    Page,
    PageUnit,
    collect_symbol_anchor_set,
    finalize_pages,
    page_over_budget,
    scan_docs_tree,
    split_over_budget,
    split_until_fit,
    tree_depth,
)
from src.semantic.models import SemanticLedger
from src.semantic.render import render_semantic_docs

_JOB = Path(__file__).resolve().parents[3]
_FLASK_LEDGER = (
    _JOB
    / "runs/r003_20260813_eval_feedback_loop/experiments/scale/repos/flask/src/flask/.codebase-analysis/semantic_ledger.json"
)
_HTTPX_LEDGER = (
    _JOB
    / "runs/r003_20260813_eval_feedback_loop/experiments/scale/repos/httpx/httpx/.codebase-analysis/semantic_ledger.json"
)


def _heading(group_key: str, title: str) -> PageUnit:
    return PageUnit(
        unit_id=f"heading:{group_key}",
        kind="heading",
        group_key=group_key,
        name=title,
        one_liner="",
        lines=(f"## {title}", ""),
    )


def _module_entry(index: int) -> PageUnit:
    target = f"mod-{index}/{DETAIL_LEAF_NAME}"
    return PageUnit(
        unit_id=f"module:{index}",
        kind="entry",
        group_key="module",
        name=f"capability-{index}",
        one_liner="one-line capability summary without omission.",
        lines=(
            f"- [capability-{index}](@@PAGE:{target}@@)：one-line capability summary without omission.",
        ),
        nav_target=target,
    )


def _index_page(n_modules: int) -> Page:
    units: list[PageUnit] = [
        PageUnit(
            unit_id="intro",
            kind="fixed",
            group_key="fixed",
            name="intro",
            one_liner="",
            lines=("Deterministic index page used as a layering fixture.",),
        ),
        _heading("module", "模块"),
        *(_module_entry(index) for index in range(n_modules)),
        PageUnit(
            unit_id="status",
            kind="fixed",
            group_key="fixed",
            name="status",
            one_liner="",
            lines=("## 可复算状态", "", "- fixture"),
        ),
    ]
    return Page(
        relpath="INDEX.md",
        kind="index",
        title="fixture 代码语义索引",
        parent_relpath=None,
        parent_title="",
        units=tuple(units),
    )


def _symbol_unit(index: int) -> PageUnit:
    sid = f"file.py::fn{index}"
    return PageUnit(
        unit_id=f"sym:{sid}",
        kind="symbol",
        group_key="layer:0",
        name=f"fn{index}",
        one_liner="returns a fixture value without side effects here.",
        lines=(
            f"<!-- symbol:{sid} -->",
            f'<a id="symbol-{index:016d}"></a>',
            f"### `fn{index}`",
            "",
            f"- Symbol id：`{sid}`",
            "- 类型：`function`；源码：`file.py:1-3`",
            "This fixture explanation is long enough to count as a real block.",
            "",
            f"<!-- end:symbol:{sid} -->",
        ),
        symbol_ids=(sid,),
        block_count=1,
    )


def _detail_page(n_blocks: int) -> Page:
    children = tuple(_symbol_unit(index) for index in range(n_blocks))
    file_unit = PageUnit(
        unit_id="file:file.py",
        kind="file",
        group_key="layer:0",
        name="file.py",
        one_liner=f"{n_blocks} 个 fresh 符号",
        lines=("## `file.py`", "", "### 文件语义目录", ""),
        children=children,
        symbol_ids=tuple(sid for unit in children for sid in unit.symbol_ids),
        block_count=n_blocks,
    )
    return Page(
        relpath=f"mod/{DETAIL_LEAF_NAME}",
        kind="detail",
        title="mod 模块语义详情",
        parent_relpath="INDEX.md",
        parent_title="fixture 代码语义索引",
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


def test_split_over_budget_index_terminates_under_line_cap() -> None:
    page = _index_page(80)
    budget = LayerBudget(index_max_lines=40)
    assert page_over_budget(page, budget)
    parent, children = split_over_budget(page, budget, occupied={"INDEX.md"})
    assert children, "over-budget INDEX must sink at least one child"
    layered = split_until_fit({"INDEX.md": page}, budget)
    for relpath, item in layered.items():
        reasons = page_over_budget(item, budget)
        assert not reasons, (relpath, reasons)
    documents = finalize_pages(layered, budget)
    nav_lines = [
        line
        for text in documents.values()
        for line in text.splitlines()
        if line.startswith("- [") and "：" in line
    ]
    assert nav_lines, "parent must keep name + one-liner + link nav rows"
    assert all("](" in line and "：" in line for line in nav_lines)
    for relpath, text in documents.items():
        if relpath == "INDEX.md":
            continue
        assert "↑ [" in text, relpath


def test_split_detail_packs_symbol_blocks_into_parts() -> None:
    page = _detail_page(50)
    budget = LayerBudget(detail_max_blocks=40, detail_max_lines=400, index_max_lines=150)
    assert page_over_budget(page, budget)
    layered = split_until_fit(
        {
            "INDEX.md": Page(
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
                        lines=("- [mod](@@PAGE:mod/DETAIL.md@@)：module",),
                        nav_target="mod/DETAIL.md",
                    ),
                ),
            ),
            page.relpath: page,
        },
        budget,
    )
    detail_pages = [item for item in layered.values() if item.kind == "detail"]
    assert len(detail_pages) >= 2
    for item in detail_pages:
        assert not page_over_budget(item, budget)
    part_names = [Path(rel).name for rel in layered if Path(rel).name.startswith("PART-")]
    assert part_names, "DETAIL overflow must emit PART-n.md"


def test_split_until_fit_has_no_depth_parameter() -> None:
    assert "depth" not in split_until_fit.__code__.co_varnames
    assert "max_depth" not in LayerBudget.__dataclass_fields__


def _relocate_ledger(raw: SemanticLedger, tmp_path: Path) -> SemanticLedger:
    tmp_path.mkdir(parents=True, exist_ok=True)
    return raw.model_copy(update={"repo_root": tmp_path.resolve().as_posix()})


def _load_ledger(path: Path) -> SemanticLedger:
    if not path.is_file():
        pytest.skip(f"ledger missing: {path}")
    return SemanticLedger.model_validate_json(path.read_bytes())


def _docs_map(tmp_path: Path) -> dict[str, str]:
    docs = tmp_path / ".codebase-docs"
    return {
        path.relative_to(docs).as_posix(): path.read_text(encoding="utf-8")
        for path in docs.rglob("*.md")
        if path.is_file()
    }


@pytest.mark.parametrize("ledger_path,name", [(_FLASK_LEDGER, "flask"), (_HTTPX_LEDGER, "httpx")])
def test_negative_control_small_index_budget_deepens_without_losing_symbols(
    tmp_path: Path,
    ledger_path: Path,
    name: str,
) -> None:
    raw = _load_ledger(ledger_path)
    default_root = tmp_path / "default"
    small_root = tmp_path / "small"
    default_ledger = _relocate_ledger(raw, default_root)
    small_ledger = _relocate_ledger(raw, small_root)

    default = render_semantic_docs(default_root, default_ledger)
    small = render_semantic_docs(small_root, small_ledger, index_max_lines=40)

    default_docs = _docs_map(default_root)
    small_docs = _docs_map(small_root)
    assert small["page_count"] > default["page_count"]
    assert tree_depth(small_docs) >= 3
    assert tree_depth(small_docs) >= tree_depth(default_docs)

    default_ids, default_frags = collect_symbol_anchor_set(default_docs)
    small_ids, small_frags = collect_symbol_anchor_set(small_docs)
    assert default_ids == small_ids
    assert default_frags == small_frags
    assert default_ids, name


@pytest.mark.parametrize("ledger_path,name", [(_FLASK_LEDGER, "flask"), (_HTTPX_LEDGER, "httpx")])
def test_integration_default_budget_pages_hops_and_no_dead_ends(
    tmp_path: Path,
    ledger_path: Path,
    name: str,
) -> None:
    raw = _load_ledger(ledger_path)
    root = tmp_path / name
    ledger = _relocate_ledger(raw, root)
    result = render_semantic_docs(root, ledger)
    docs = root / ".codebase-docs"
    scan = scan_docs_tree(docs)
    assert scan["index_violations"] == []
    assert scan["detail_line_violations"] == []
    assert scan["detail_block_violations"] == []
    assert scan["dead_ends"] == []
    hops_path = Path(result["hops_path"])
    assert hops_path.is_file()
    payload = json.loads(hops_path.read_text(encoding="utf-8"))
    tree = next(iter(payload["trees"].values()))
    assert "distribution" in tree
    assert set(tree["distribution"]) == {"0", "1", "2", "3", "4+", "unreachable"}
    assert tree["n_ledger"] >= tree["n_rendered"]
