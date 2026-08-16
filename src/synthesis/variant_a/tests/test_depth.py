"""Layered content depth (r004 va5): status decides how much prose is shown.

This is not a coverage cut. Every ledger symbol stays on the page. Folded
symbols must show a visible ledger pointer; they must not vanish.
"""

from __future__ import annotations

import json

from src.synthesis.variant_a.depth import (
    ContentDepth,
    LEDGER_POINTER_PREFIX,
    body_mode,
    extract_core_fields,
    load_status_map,
    render_symbol_prose,
)
from src.synthesis.variant_a.fold_audit import audit_fold, run_fold_negative_control
from src.synthesis.variant_a.gates import GateContext, build_name_index
from src.synthesis.variant_a.models import ClusterInput, SynthesisLedger
from src.synthesis.variant_a.page_tree import plan_page_tree
from src.synthesis.variant_a.render import render_documents
from src.synthesis.variant_a.surface import PublicSurface, SurfaceBinding
from src.synthesis.variant_a.tests.conftest import make_ledger, make_symbol


LONG_TEXT = (
    "Widget.run 接收 name 与 timeout 两个输入，返回构建后的响应对象。"
    "当 timeout 非法或 name 为空时抛出 ValueError，其它异常向上传播。"
    "它还会把内部缓存写回磁盘，这段细节读者通常用不到。"
    "更多装配步骤包括注册钩子、合并默认值和通知监听器。"
)


def _ctx(ledger, surface, edges=frozenset()):
    return GateContext(
        ledger=ledger,
        surface=surface,
        ir_edges=frozenset(edges),
        name_index=build_name_index(ledger, surface),
    )


def _surface(ledger, bindings: list[SurfaceBinding]) -> PublicSurface:
    return PublicSurface(
        schema="cbe-public-surface-1",
        repo_root=ledger.repo_root,
        source_revision=ledger.source_revision,
        bindings=tuple(bindings),
        overlay_file_hashes={},
    )


def _mini(tmp_path):
    entry = make_symbol("app.py", "Flask", text=LONG_TEXT)
    core = make_symbol("app.py", "dispatch", text=LONG_TEXT)
    glue = make_symbol("app.py", "teardown", text=LONG_TEXT)
    adapter = make_symbol("app.py", "wsgi_app", text=LONG_TEXT)
    (tmp_path / "app.py").write_text("class Flask:\n    pass\n", encoding="utf-8")
    ledger = make_ledger(tmp_path, [entry, core, glue, adapter])
    surface = _surface(
        ledger,
        [
            SurfaceBinding(
                surface_id="surface:__init__.py:Flask",
                name="Flask",
                path="__init__.py",
                resolved_symbol_ids=(entry.symbol_id,),
                target_path="app.py",
            )
        ],
    )
    clusters = (
        ClusterInput(
            cluster_id="core",
            display_name="core",
            paths=("app.py",),
            symbol_ids=(entry.symbol_id, core.symbol_id, glue.symbol_id, adapter.symbol_id),
            dag_layer_by_path={"app.py": 0},
        ),
    )
    pages = plan_page_tree(clusters, ledger)
    ctx = _ctx(ledger, surface)
    status = {
        entry.symbol_id: "entry",
        core.symbol_id: "core",
        glue.symbol_id: "glue",
        adapter.symbol_id: "adapter",
    }
    return ledger, surface, clusters, pages, ctx, status, entry, core, glue, adapter


def test_body_mode_table() -> None:
    assert body_mode("entry", ContentDepth.FULL) == "full"
    assert body_mode("glue", ContentDepth.FULL) == "full"
    assert body_mode("entry", ContentDepth.LAYERED) == "full"
    assert body_mode("public_api", ContentDepth.LAYERED) == "full"
    assert body_mode("core", ContentDepth.LAYERED) == "core"
    assert body_mode("adapter", ContentDepth.LAYERED) == "folded"
    assert body_mode("data", ContentDepth.LAYERED) == "folded"
    assert body_mode("glue", ContentDepth.LAYERED) == "folded"
    assert body_mode("error_path", ContentDepth.LAYERED) == "folded"
    assert body_mode("entry", ContentDepth.PUBLIC_ONLY) == "full"
    assert body_mode("core", ContentDepth.PUBLIC_ONLY) == "folded"
    assert body_mode("glue", ContentDepth.PUBLIC_ONLY) == "folded"
    assert body_mode(None, ContentDepth.LAYERED) == "core"
    assert body_mode(None, ContentDepth.PUBLIC_ONLY) == "folded"


def test_extract_core_fields_pulls_io_and_failure() -> None:
    one, fail, io = extract_core_fields(LONG_TEXT)
    assert "Widget.run" in one or "接收" in one
    assert "ValueError" in fail or "抛" in fail
    assert "输入" in io or "返回" in io
    assert "监听器" not in one
    assert "监听器" not in fail
    assert len(one) <= 160


def test_folded_prose_is_one_liner_plus_visible_pointer() -> None:
    lines = render_symbol_prose(
        symbol_id="app.py::teardown",
        text=LONG_TEXT,
        mode="folded",
        status="glue",
    )
    blob = "\n".join(lines)
    assert LEDGER_POINTER_PREFIX in blob
    assert "`app.py::teardown`" in blob
    assert "监听器" not in blob
    assert "<!-- folded:app.py::teardown -->" in blob
    assert "地位：`glue`" in blob


def test_entry_keeps_full_behavior() -> None:
    lines = render_symbol_prose(
        symbol_id="app.py::Flask",
        text=LONG_TEXT,
        mode="full",
        status="entry",
    )
    blob = "\n".join(lines)
    assert "监听器" in blob
    assert LEDGER_POINTER_PREFIX not in blob


def test_layered_render_keeps_denominator_and_marks_folds(tmp_path) -> None:
    ledger, surface, clusters, pages, ctx, status, entry, core, glue, adapter = _mini(tmp_path)
    docs = render_documents(
        repo_name="demo",
        ledger=ledger,
        surface=surface,
        synthesis=SynthesisLedger(
            schema="cbe-synthesis-ledger-1",
            repo_root=ledger.repo_root,
            source_revision=ledger.source_revision,
        ),
        pages=pages,
        clusters=clusters,
        ctx=ctx,
        depth=ContentDepth.LAYERED,
        status_by_symbol=status,
    )
    joined = "\n".join(docs.values())
    for sid in ledger.symbols:
        assert f"<!-- symbol:{sid} -->" in joined
    assert "监听器" in joined  # entry keeps full prose
    assert f"{LEDGER_POINTER_PREFIX}`{glue.symbol_id}`" in joined
    assert f"{LEDGER_POINTER_PREFIX}`{adapter.symbol_id}`" in joined
    glue_block = joined.split(f"<!-- symbol:{glue.symbol_id} -->", 1)[1].split("<!-- end:symbol:", 1)[0]
    assert "监听器" not in glue_block
    assert "完整解释见台账" in glue_block
    core_block = joined.split(f"<!-- symbol:{core.symbol_id} -->", 1)[1].split("<!-- end:symbol:", 1)[0]
    assert "ValueError" in core_block or "失败" in core_block
    assert "输入" in core_block or "返回" in core_block
    assert "完整解释见台账" in core_block
    audit = audit_fold(docs, list(ledger.symbols), status, ContentDepth.LAYERED)
    assert audit["n_ledger"] == 4
    assert audit["n_rendered"] == 4
    assert audit["missing_markers"] == []
    assert audit["silent_folds"] == []
    assert audit["ok_denominator"]
    assert audit["ok_visible_folds"]


def test_public_only_folds_core(tmp_path) -> None:
    ledger, surface, clusters, pages, ctx, status, entry, core, glue, adapter = _mini(tmp_path)
    docs = render_documents(
        repo_name="demo",
        ledger=ledger,
        surface=surface,
        synthesis=SynthesisLedger(
            schema="cbe-synthesis-ledger-1",
            repo_root=ledger.repo_root,
            source_revision=ledger.source_revision,
        ),
        pages=pages,
        clusters=clusters,
        ctx=ctx,
        depth=ContentDepth.PUBLIC_ONLY,
        status_by_symbol=status,
    )
    joined = "\n".join(docs.values())
    core_block = joined.split(f"<!-- symbol:{core.symbol_id} -->", 1)[1].split("<!-- end:symbol:", 1)[0]
    assert "监听器" not in core_block
    assert "完整解释见台账" in core_block
    entry_block = joined.split(f"<!-- symbol:{entry.symbol_id} -->", 1)[1].split("<!-- end:symbol:", 1)[0]
    assert "监听器" in entry_block


def test_full_depth_does_not_fold(tmp_path) -> None:
    ledger, surface, clusters, pages, ctx, status, *_ = _mini(tmp_path)
    docs = render_documents(
        repo_name="demo",
        ledger=ledger,
        surface=surface,
        synthesis=SynthesisLedger(
            schema="cbe-synthesis-ledger-1",
            repo_root=ledger.repo_root,
            source_revision=ledger.source_revision,
        ),
        pages=pages,
        clusters=clusters,
        ctx=ctx,
    )
    joined = "\n".join(docs.values())
    assert LEDGER_POINTER_PREFIX not in joined
    assert joined.count("监听器") == 4


def test_unlabelled_is_visible_not_dropped(tmp_path) -> None:
    ledger, surface, clusters, pages, ctx, status, entry, core, glue, adapter = _mini(tmp_path)
    status = {entry.symbol_id: "entry"}  # others unlabelled
    docs = render_documents(
        repo_name="demo",
        ledger=ledger,
        surface=surface,
        synthesis=SynthesisLedger(
            schema="cbe-synthesis-ledger-1",
            repo_root=ledger.repo_root,
            source_revision=ledger.source_revision,
        ),
        pages=pages,
        clusters=clusters,
        ctx=ctx,
        depth=ContentDepth.LAYERED,
        status_by_symbol=status,
    )
    joined = "\n".join(docs.values())
    assert f"<!-- symbol:{glue.symbol_id} -->" in joined
    glue_block = joined.split(f"<!-- symbol:{glue.symbol_id} -->", 1)[1].split("<!-- end:symbol:", 1)[0]
    assert "地位未标注" in glue_block
    assert "完整解释见台账" in glue_block


def test_load_status_map_from_l2_result(tmp_path) -> None:
    path = tmp_path / "l2_result.json"
    path.write_text(
        json.dumps(
            {
                "status_labels": [
                    {"symbol_id": "a.py::A", "status": "entry"},
                    {"symbol_id": "b.py::B", "status": "glue"},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert load_status_map(path) == {"a.py::A": "entry", "b.py::B": "glue"}


def test_fold_negative_control_flags_missing_pointer(tmp_path) -> None:
    ledger, surface, clusters, pages, ctx, status, *_rest = _mini(tmp_path)
    docs = render_documents(
        repo_name="demo",
        ledger=ledger,
        surface=surface,
        synthesis=SynthesisLedger(
            schema="cbe-synthesis-ledger-1",
            repo_root=ledger.repo_root,
            source_revision=ledger.source_revision,
        ),
        pages=pages,
        clusters=clusters,
        ctx=ctx,
        depth=ContentDepth.LAYERED,
        status_by_symbol=status,
    )
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    for rel, text in docs.items():
        dest = docs_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    control = run_fold_negative_control(docs_root, tmp_path / "neg", list(ledger.symbols), status, ContentDepth.LAYERED)
    assert control["ran"] is True
    assert control["ok_flagged_red"] is True
