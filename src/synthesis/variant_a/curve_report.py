"""Assemble one budget-curve row from already-measured artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from src.synthesis.variant_a.budget import measure_budget
from src.synthesis.variant_a.budget_curve import band_position, closest_tier, in_band_tiers
from src.synthesis.variant_a.symbol_hops import report_tree
from src.synthesis.variant_a.verify import report as verify_report


def page_stats(verify: Mapping[str, object]) -> dict[str, object]:
    lengths = verify["lengths"]  # type: ignore[index]
    pages = lengths["pages"]  # type: ignore[index]
    return {
        "n_pages": verify["n_pages"],
        "max_page_lines": lengths["max_lines"],
        "over_detail_400": lengths["over_detail_400"],
        "over_index_150": lengths["over_index_150"],
    }


def measure_tier(
    *,
    name: str,
    docs_root: Path,
    src_root: Path,
    ledger_path: Path,
) -> dict[str, object]:
    budget = measure_budget(docs_root, src_root)
    hops = report_tree(docs_root, ledger_path, name)
    verify = verify_report(docs_root)
    return {
        "name": name,
        "docs_root": str(docs_root),
        "doc_tokens": budget["doc_tokens"],
        "src_tokens": budget["src_tokens"],
        "ratio": budget["ratio"],
        "band": band_position(float(budget["ratio"])),
        "verdict_ev14": budget["verdict"],
        "n_pages": verify["n_pages"],
        "max_page_lines": verify["lengths"]["max_lines"],
        "over_detail_400": verify["lengths"]["over_detail_400"],
        "over_index_150": verify["lengths"]["over_index_150"],
        "hops": hops["distribution"],
        "rate_le_3": hops["rate_le_3"],
        "n_rendered": hops["n_rendered"],
        "n_ledger": hops["n_ledger"],
        "unreachable": hops["unreachable"],
        "over_3": hops["over_3"],
        "nav": budget["nav"],
        "line_range_rate": verify["line_ranges"]["rate_with_line_range"],
    }


def summarize_curve(tiers: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    ratios = {name: float(row["ratio"]) for name, row in tiers.items()}
    return {
        "in_band": in_band_tiers(ratios),
        "closest": closest_tier(ratios),
        "ev14_compatible": bool(in_band_tiers(ratios)),
    }
