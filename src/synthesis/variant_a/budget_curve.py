"""EV-14 budget curve: classify depth tiers against the 15–30% band."""

from __future__ import annotations

from typing import Mapping

BUDGET_LO, BUDGET_HI = 0.15, 0.30


def band_position(ratio: float) -> str:
    if ratio < BUDGET_LO:
        return "below"
    if ratio > BUDGET_HI:
        return "above"
    return "in_band"


def in_band_tiers(tiers: Mapping[str, float]) -> list[str]:
    return [name for name, ratio in tiers.items() if band_position(ratio) == "in_band"]


def closest_tier(tiers: Mapping[str, float]) -> dict[str, object]:
    """Name of the tier nearest the 15–30% band (inside counts as distance 0)."""

    if not tiers:
        raise ValueError("no tiers")
    scored: list[tuple[float, str, float]] = []
    for name, ratio in tiers.items():
        if ratio < BUDGET_LO:
            dist = BUDGET_LO - ratio
        elif ratio > BUDGET_HI:
            dist = ratio - BUDGET_HI
        else:
            dist = 0.0
        scored.append((dist, name, ratio))
    scored.sort(key=lambda item: (item[0], item[2], item[1]))
    dist, name, ratio = scored[0]
    return {
        "name": name,
        "ratio": ratio,
        "distance_to_band": round(dist, 4),
        "in_band": dist == 0.0,
        "verdict": (
            "in_band"
            if dist == 0.0
            else "EV-14 and full-coverage symbol pages cannot both be met; closest tier reported"
        ),
    }
