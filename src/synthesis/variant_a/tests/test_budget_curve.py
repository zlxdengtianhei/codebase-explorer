from src.synthesis.variant_a.budget_curve import band_position, closest_tier, in_band_tiers


def test_band_and_closest() -> None:
    assert band_position(0.20) == "in_band"
    assert band_position(0.10) == "below"
    assert band_position(1.17) == "above"
    tiers = {"full": 1.1756, "layered": 0.62, "public_only": 0.41}
    assert in_band_tiers(tiers) == []
    closest = closest_tier(tiers)
    assert closest["name"] == "public_only"
    assert closest["in_band"] is False
    assert "cannot both be met" in str(closest["verdict"])


def test_in_band_wins() -> None:
    tiers = {"full": 1.2, "layered": 0.22, "public_only": 0.11}
    assert in_band_tiers(tiers) == ["layered"]
    assert closest_tier(tiers)["name"] == "layered"
    assert closest_tier(tiers)["in_band"] is True
