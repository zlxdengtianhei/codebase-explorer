"""Independent static coverage and optional runtime-heat tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.semantic.coverage import (
    apply_runtime_coverage,
    derive_static_coverage,
    load_runtime_coverage,
)
from src.semantic.inventory import (
    enumerate_semantic_inventory,
    reconcile_semantic_ledger,
)


FIXTURE = Path(__file__).parent / "fixtures/semantic_disclosure"


def test_runtime_coverage_maps_executed_lines_without_changing_static_denominator() -> None:
    repo = FIXTURE / "cycle_repo"
    inventory = enumerate_semantic_inventory(repo)
    ledger = reconcile_semantic_ledger(inventory)
    before = derive_static_coverage(inventory, ledger)

    runtime = load_runtime_coverage(FIXTURE / "coverage.json", repo_root=repo)
    projected = apply_runtime_coverage(ledger, runtime)
    after = derive_static_coverage(inventory, projected)

    assert before == after
    assert set(projected.symbols) == set(inventory.symbols)
    assert projected.totals == ledger.totals
    assert projected.coverage_percent == ledger.coverage_percent
    assert projected.symbols["a.py::hot_leaf"].runtime_covered_lines == 2
    assert projected.symbols["a.py::cold_path"].runtime_covered_lines == 0
    assert projected.symbols["b.py::cold_only"].runtime_covered_lines == 0


def test_static_coverage_uses_inventory_truth_and_rejects_a_shrunken_ledger(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "app.py").write_text(
        "def kept():\n    return 1\n\ndef hidden():\n    return 2\n",
        encoding="utf-8",
    )
    inventory = enumerate_semantic_inventory(tmp_path)
    full = reconcile_semantic_ledger(inventory)
    hidden_id = "app.py::hidden"
    shrunken = full.model_copy(
        update={
            "symbols": {key: value for key, value in full.symbols.items() if key != hidden_id},
            "residuals": tuple(item for item in full.residuals if item.symbol_id != hidden_id),
            "uncovered_symbols": ("app.py::kept",),
            "totals": full.totals.model_copy(
                update={"symbols": 1, "uncovered": 1, "residual": 1}
            ),
        }
    )

    with pytest.raises(ValueError, match="static symbol denominator mismatch"):
        derive_static_coverage(inventory, shrunken)


def test_runtime_coverage_rejects_traversal_and_non_integer_lines(tmp_path) -> None:  # type: ignore[no-untyped-def]
    bad_path = tmp_path / "bad-path.json"
    bad_path.write_text(
        json.dumps({"files": {"../outside.py": {"executed_lines": [1]}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="outside repository"):
        load_runtime_coverage(bad_path, repo_root=tmp_path)

    bad_lines = tmp_path / "bad-lines.json"
    bad_lines.write_text(
        json.dumps({"files": {"inside.py": {"executed_lines": [True, "2"]}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="positive integers"):
        load_runtime_coverage(bad_lines, repo_root=tmp_path)
