from __future__ import annotations

import json

from src.synthesis.variant_a.cluster_source import JsonClusterSource, STRUCTURAL_NAME_RE, cluster_dir_map
from src.synthesis.variant_a.gates import GateContext, build_name_index
from src.synthesis.variant_a.models import ClusterInput, SynthesisLedger
from src.synthesis.variant_a.page_tree import plan_page_tree
from src.synthesis.variant_a.render import render_documents
from src.synthesis.variant_a.surface import PublicSurface, SurfaceBinding
from src.synthesis.variant_a.tests.conftest import make_ledger, make_symbol


STRUCTURAL_WORDS = ("工具", "通用", "共享", "基础设施", "PART", "独占")


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


def _clus_payload() -> dict:
    return {
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
        "clusters": [
            {
                "cluster_id": "feature--app--aaaaaa--L0",
                "name": "serve HTTP requests",
                "purpose": "Make the app a callable WSGI object that dispatches the matched view.",
                "boundary_not": [
                    "load configuration from files",
                    "persist session data in a cookie",
                ],
                "member_paths": ["app.py"],
            },
            {
                "cluster_id": "shared--helpers--bbbbbb",
                "name": "generate URLs and view responses",
                "purpose": "Give views url_for, abort, and redirect.",
                "boundary_not": ["register routes or blueprints"],
                "member_paths": ["helpers.py"],
            },
        ],
    }


def test_clus_loader_joins_l2_names_and_slugs_dirs(tmp_path) -> None:
    flask = make_symbol("app.py", "Flask", module_id="core")
    helper = make_symbol("helpers.py", "url_for", module_id="core")
    ledger = make_ledger(tmp_path, [flask, helper], extra_files=["signals.py"])
    path = tmp_path / "partition_demo.json"
    path.write_text(json.dumps(_clus_payload()), encoding="utf-8")
    clusters = JsonClusterSource(path).load(ledger, set())
    named = {item.cluster_id: item for item in clusters if not item.is_unassigned}
    assert named["feature--app--aaaaaa--L0"].display_name == "serve HTTP requests"
    assert named["feature--app--aaaaaa--L0"].purpose.startswith("Make the app")
    assert named["feature--app--aaaaaa--L0"].boundary_not == (
        "load configuration from files",
        "persist session data in a cookie",
    )
    assert named["shared--helpers--bbbbbb"].display_name == "generate URLs and view responses"
    dirs = cluster_dir_map(clusters)
    assert dirs["feature--app--aaaaaa--L0"] == "serve-http-requests"
    assert dirs["shared--helpers--bbbbbb"] == "generate-urls-and-view-responses"
    assert dirs["unassigned"] == "_unassigned"
    for item in named.values():
        assert not STRUCTURAL_NAME_RE.search(item.display_name)
        for word in STRUCTURAL_WORDS:
            assert word not in item.display_name


def test_sidecar_l2_result_joins_when_partition_has_no_clusters(tmp_path) -> None:
    flask = make_symbol("app.py", "Flask", module_id="core")
    helper = make_symbol("helpers.py", "url_for", module_id="core")
    ledger = make_ledger(tmp_path, [flask, helper])
    partition = {
        "candidates": _clus_payload()["candidates"],
        "unassigned": [],
    }
    names = {"clusters": _clus_payload()["clusters"]}
    part_path = tmp_path / "partition_demo.json"
    part_path.write_text(json.dumps(partition), encoding="utf-8")
    (tmp_path / "l2_result_demo.json").write_text(json.dumps(names), encoding="utf-8")
    clusters = JsonClusterSource(part_path).load(ledger, set())
    served = next(item for item in clusters if item.cluster_id.endswith("aaaaaa--L0"))
    assert served.display_name == "serve HTTP requests"
    assert served.boundary_not[0].startswith("load configuration")


def test_explicit_l2_names_path(tmp_path) -> None:
    flask = make_symbol("app.py", "Flask", module_id="core")
    ledger = make_ledger(tmp_path, [flask])
    partition = {
        "candidates": [_clus_payload()["candidates"][0]],
        "unassigned": [],
    }
    part_path = tmp_path / "partition_x.json"
    names_path = tmp_path / "names.json"
    part_path.write_text(json.dumps(partition), encoding="utf-8")
    names_path.write_text(json.dumps({"clusters": [_clus_payload()["clusters"][0]]}), encoding="utf-8")
    clusters = JsonClusterSource(part_path, names_path=names_path).load(ledger, set())
    assert clusters[0].display_name == "serve HTTP requests"


def test_cluster_pages_carry_purpose_and_boundary_and_root_nav_is_up_only(tmp_path) -> None:
    symbols = [make_symbol("app.py", f"fn{i}", module_id="core") for i in range(70)]
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
            cluster_id="feature--app--aaaaaa--L0",
            display_name="serve HTTP requests",
            paths=("app.py",),
            symbol_ids=tuple(item.symbol_id for item in symbols),
            dag_layer_by_path={"app.py": 0},
            purpose="Make the app a callable WSGI object that dispatches the matched view.",
            boundary_not=("load configuration from files", "persist session data in a cookie"),
        ),
    )
    pages = plan_page_tree(clusters, ledger)
    assert any(page.relpath == "serve-http-requests/INDEX.md" for page in pages)
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
        ctx=_ctx(ledger, surface),
    )
    index = docs["INDEX.md"]
    assert "serve HTTP requests" in index
    assert "serve-http-requests/" in index
    assert "共享" not in index.split("## 功能", 1)[1].split("## 导航", 1)[0]
    nav = index.split("## 导航", 1)[1]
    assert "serve HTTP requests" not in nav
    assert "↑" in nav
    cluster_index = docs["serve-http-requests/INDEX.md"]
    assert "# serve HTTP requests" in cluster_index
    assert "Make the app a callable WSGI object" in cluster_index
    assert "它不做什么" in cluster_index
    assert "load configuration from files" in cluster_index
    lower = cluster_index.split("## 下层", 1)[1].split("## 导航", 1)[0]
    assert "fn0" in lower
    assert "PART-" in lower
    assert "PART-" not in cluster_index.split("## 导航", 1)[1]
