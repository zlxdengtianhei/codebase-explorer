"""L1 runner: T0/T1/T3 split, checkpoint, and T0-only path (no LLM)."""

from __future__ import annotations

from pathlib import Path

from src.semantic.l1_run import assign_execution_tiers, run_repository
from src.semantic.tiering import measure_repository


def test_execution_tiers_are_three_way_and_sum_to_denominator(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text(
        "def tiny():\n    return 1\n\n"
        "def messy(a, b, c, d, e, f, g, h):\n"
        "    try:\n"
        "        if a:\n"
        "            if b:\n"
        "                if c:\n"
        "                    if d:\n"
        "                        if e:\n"
        "                            return getattr(a, 'x')\n"
        "    except Exception:\n"
        "        pass\n"
        "    return 0\n",
        encoding="utf-8",
    )
    metrics = measure_repository(tmp_path)
    assigned = assign_execution_tiers(metrics)
    assert len(assigned) == len(metrics)
    tiers = {item.tier for item in assigned}
    assert tiers <= {"T0", "T1", "T3"}
    assert any(item.tier == "T3" for item in assigned)


def test_local_run_uses_canonical_service_without_parallel_ledger(tmp_path: Path) -> None:
    (tmp_path / "tiny.py").write_text("def ping():\n    return 1\n", encoding="utf-8")
    out = tmp_path / "out"
    summary = run_repository(tmp_path, name="tiny", out_dir=out, workers=1)
    assert summary["authoritative"] is False
    assert summary["canonical"]["ledger_revision"] == 0
    assert summary["completion"]["totals"]["symbols"] == 1
    assert not (out / "L1_LEDGER_tiny.json").exists()
    assert not (out / "L1_RUN_tiny.json").exists()
    assert summary["calls"]["total"] == 0
