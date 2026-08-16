from __future__ import annotations

from src.synthesis.variant_a.anchors import filebind_anchor
from src.synthesis.variant_a.cluster_source import JsonClusterSource
from src.synthesis.variant_a.gates import GateContext, build_name_index
from src.synthesis.variant_a.models import ClusterInput, SynthesisLedger
from src.synthesis.variant_a.page_tree import plan_page_tree
from src.synthesis.variant_a.pointing import evaluate_docs, name_is_defined_object, run_negative_control
from src.synthesis.variant_a.render import render_documents
from src.synthesis.variant_a.surface import PublicSurface, SurfaceBinding, extract_public_surface
from src.synthesis.variant_a.tests.conftest import make_ledger, make_symbol


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


def test_file_level_overlay_is_honest_and_unique(tmp_path) -> None:
    flask = make_symbol("app.py", "Flask", module_id="core")
    helper = make_symbol("app.py", "wsgi_app", module_id="core")
    (tmp_path / "app.py").write_text("class Flask:\n    def wsgi_app(self):\n        pass\n", encoding="utf-8")
    (tmp_path / "globals.py").write_text("request = object()\n", encoding="utf-8")
    (tmp_path / "__init__.py").write_text("from app import Flask\nfrom globals import request\n", encoding="utf-8")
    ledger = make_ledger(tmp_path, [flask, helper], extra_files=["globals.py", "__init__.py"])
    surface = _surface(
        ledger,
        [
            SurfaceBinding(
                surface_id="surface:__init__.py:Flask",
                name="Flask",
                path="__init__.py",
                resolved_symbol_ids=(flask.symbol_id,),
                target_path="app.py",
            ),
            SurfaceBinding(
                surface_id="surface:__init__.py:request",
                name="request",
                path="__init__.py",
                resolved_symbol_ids=(),
                unresolved_reason="import request resolved to ('globals.py',) with no lexical symbol",
                target_path="globals.py",
            ),
            SurfaceBinding(
                surface_id="surface:__init__.py:g",
                name="g",
                path="__init__.py",
                resolved_symbol_ids=(),
                unresolved_reason="import g resolved to ('globals.py',) with no lexical symbol",
                target_path="globals.py",
            ),
        ],
    )
    clusters = (
        ClusterInput(
            cluster_id="core",
            display_name="core",
            paths=("app.py",),
            symbol_ids=(flask.symbol_id, helper.symbol_id),
            dag_layer_by_path={"app.py": 0},
        ),
        ClusterInput(
            cluster_id="unassigned",
            display_name="unassigned",
            paths=("globals.py", "__init__.py"),
            symbol_ids=(),
            dag_layer_by_path={"globals.py": 0, "__init__.py": 0},
            unassigned_reason="globals.py: no_symbols; __init__.py: no_symbols",
        ),
    )
    pages = plan_page_tree(clusters, ledger)
    ctx = _ctx(ledger, surface, {(flask.symbol_id, helper.symbol_id)})
    docs = render_documents(
        repo_name="flask",
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
    index = docs["INDEX.md"]
    assert "[`Flask`" in index
    assert "→ globals.py（模块级绑定，非枚举符号）" in index
    assert "[`request` L" not in index
    assert "[`g` L" not in index
    overlay = docs["_overlay/DETAIL.md"]
    assert "### `request`（模块级绑定，非枚举符号）" in overlay
    assert "### `g`（模块级绑定，非枚举符号）" in overlay
    req_frag = filebind_anchor("globals.py", "request")
    g_frag = filebind_anchor("globals.py", "g")
    assert req_frag != g_frag
    audit = evaluate_docs(docs)
    assert audit["public_hrefs"]["ok_max_repeat_le_2"]
    assert audit["rate_hit"] >= 0.90


def test_cluster_index_labels_and_nav_not_duplicated(tmp_path) -> None:
    symbols = [make_symbol("app.py", f"fn{i}", module_id="shared_infrastructure") for i in range(70)]
    (tmp_path / "app.py").write_text("def fn0():\n    return 1\n", encoding="utf-8")
    ledger = make_ledger(tmp_path, symbols)
    surface = _surface(
        ledger,
        [
            SurfaceBinding(
                surface_id="surface:__init__.py:fn0",
                name="fn0",
                path="__init__.py",
                resolved_symbol_ids=(symbols[0].symbol_id,),
                target_path="app.py",
            )
        ],
    )
    clusters = (
        ClusterInput(
            cluster_id="shared_infrastructure",
            display_name="shared infrastructure",
            paths=("app.py",),
            symbol_ids=tuple(item.symbol_id for item in symbols),
            dag_layer_by_path={"app.py": 0},
        ),
    )
    pages = plan_page_tree(clusters, ledger)
    ctx = _ctx(ledger, surface)
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
    cluster_index = docs["shared-infrastructure/INDEX.md"]
    assert "## 下层" in cluster_index
    lower = cluster_index.split("## 下层", 1)[1].split("## 导航", 1)[0]
    nav = cluster_index.split("## 导航", 1)[1]
    assert "PART-" in lower
    assert "fn0" in lower
    assert "PART-" not in nav
    assert "↑" in nav


def test_clus_partition_loader(tmp_path) -> None:
    a = make_symbol("app.py", "Flask", module_id="core")
    b = make_symbol("helpers.py", "url_for", module_id="core")
    ledger = make_ledger(tmp_path, [a, b], extra_files=["signals.py"])
    payload = {
        "candidates": [
            {
                "cluster_id": "feature--app--aaaaaa--L0",
                "kind": "exclusive",
                "layer_index": 0,
                "member_paths": ["app.py"],
                "signature": ["app.py"],
                "symbol_count": 1,
            },
            {
                "cluster_id": "shared--helpers--bbbbbb",
                "kind": "shared",
                "layer_index": None,
                "member_paths": ["helpers.py"],
                "signature": ["app.py"],
                "symbol_count": 1,
            },
        ],
        "unassigned": [{"path": "signals.py", "reason": "no symbols", "reason_code": "outside_graph"}],
        "total_paths": 3,
        "total_symbols": 2,
    }
    path = tmp_path / "partition_flask.json"
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")
    clusters = JsonClusterSource(path).load(ledger, set())
    ids = {item.cluster_id for item in clusters}
    assert "feature--app--aaaaaa--L0" in ids
    assert "unassigned" in ids
    unassigned = next(item for item in clusters if item.is_unassigned)
    assert "signals.py" in unassigned.paths
    assert "no symbols" in unassigned.unassigned_reason


def test_star_import_resolves_all_name(tmp_path) -> None:
    client = make_symbol("_client.py", "Client", module_id="core")
    (tmp_path / "_client.py").write_text("class Client:\n    pass\n", encoding="utf-8")
    (tmp_path / "__init__.py").write_text("from ._client import *\n\n__all__ = ['Client']\n", encoding="utf-8")
    ledger = make_ledger(tmp_path, [client])
    surface = extract_public_surface(tmp_path, ledger)
    hit = next(item for item in surface.bindings if item.path == "__init__.py" and item.name == "Client")
    assert hit.resolved_symbol_ids == (client.symbol_id,)
    assert hit.target_path == "_client.py"


def test_pointing_negative_control_flags_red(tmp_path) -> None:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    (docs_root / "INDEX.md").write_text(
        "# x\n\n[`Flask` L5-L8](mod/DETAIL.md#L5-L8)\n",
        encoding="utf-8",
    )
    (docs_root / "mod").mkdir()
    (docs_root / "mod" / "DETAIL.md").write_text(
        "# d\n\n<!-- symbol:app.py::Flask -->\n<a id=\"symbol-x\"></a>\n### `Flask`\n\nbody\n<!-- end:symbol:app.py::Flask -->\n",
        encoding="utf-8",
    )
    docs = {
        "INDEX.md": (docs_root / "INDEX.md").read_text(encoding="utf-8"),
        "mod/DETAIL.md": (docs_root / "mod" / "DETAIL.md").read_text(encoding="utf-8"),
    }
    assert evaluate_docs(docs)["rate_hit"] == 1.0
    assert name_is_defined_object("Flask", "### `Flask`\n")
    control = run_negative_control(docs_root, tmp_path / "neg")
    assert control["ran"] is True
    assert control["ok_flagged_red"] is True
