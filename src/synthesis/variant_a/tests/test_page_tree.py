from __future__ import annotations

from src.semantic.models import SemanticSymbolKind
from src.synthesis.variant_a.cluster_source import ExistingLedgerModuleSource
from src.synthesis.variant_a.models import ClusterInput
from src.synthesis.variant_a.page_tree import hops_from_root, pack_symbol_pages, plan_page_tree, should_promote
from src.synthesis.variant_a.tests.conftest import make_ledger, make_symbol


def test_promote_on_symbol_count_and_est_lines(tmp_path) -> None:
    small = ClusterInput(
        cluster_id="tiny",
        display_name="tiny",
        paths=("a.py",),
        symbol_ids=("a.py::x",),
        dag_layer_by_path={"a.py": 0},
    )
    assert should_promote(small) is False
    fat = ClusterInput(
        cluster_id="fat",
        display_name="fat",
        paths=tuple(f"f{i}.py" for i in range(5)),
        symbol_ids=tuple(f"f0.py::s{i}" for i in range(70)),
        dag_layer_by_path={f"f{i}.py": 0 for i in range(5)},
    )
    assert should_promote(fat) is True


def test_pack_respects_40_and_does_not_drop(tmp_path) -> None:
    symbols = [
        make_symbol("m.py", f"fn{i}", text="Explains responsibility, inputs, outputs, and the important failure boundary. " * 8)
        for i in range(90)
    ]
    ledger = make_ledger(tmp_path, symbols)
    packed = pack_symbol_pages([item.symbol_id for item in symbols], ledger)
    assert sum(len(chunk) for chunk in packed) == 90
    assert all(len(chunk) <= 40 for chunk in packed)


def test_existing_module_id_source_and_unassigned(tmp_path) -> None:
    core = make_symbol("core.py", "run", module_id="core")
    other = make_symbol("other.py", "help", module_id="helpers")
    ledger = make_ledger(tmp_path, [core, other], extra_files=["empty.py"])
    clusters = ExistingLedgerModuleSource().load(ledger, set())
    ids = {item.cluster_id for item in clusters}
    assert ids == {"core", "helpers", "unassigned"}
    unassigned = next(item for item in clusters if item.is_unassigned)
    assert unassigned.paths == ("empty.py",)
    assert "no_symbols" in unassigned.unassigned_reason


def test_tree_emits_index_for_deep_and_stays_within_3_hops(tmp_path) -> None:
    symbols = [
        make_symbol(
            f"f{i}.py",
            "run",
            module_id="shared_infrastructure",
            kind=SemanticSymbolKind.FUNCTION,
        )
        for i in range(15)
    ]
    # more symbols to trip the 60/400 promote
    extras = [
        make_symbol("f0.py", f"helper{i}", module_id="shared_infrastructure")
        for i in range(50)
    ]
    ledger = make_ledger(tmp_path, symbols + extras)
    clusters = ExistingLedgerModuleSource().load(ledger, set())
    tree = plan_page_tree(clusters, ledger)
    kinds = {page.kind.value for page in tree}
    assert "root_index" in kinds
    assert "cluster_index" in kinds
    dist = hops_from_root(tree)
    assert all(value <= 3 for value in dist.values())
    assert any(page.relpath.endswith("INDEX.md") and page.relpath != "INDEX.md" for page in tree)
