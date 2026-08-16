from src.synthesis.variant_a.enrich import _parse_claims


def test_parse_router_envelope_result_text() -> None:
    envelope = {
        "tier_used": "grok-build:xhigh",
        "result_text": '{"claims":[{"claim_id":"x","text":"alpha","cited_symbol_ids":["a.py::alpha"],"cited_surface_ids":[],"claim_kind":"overview"}]}',
    }
    import json

    rows = _parse_claims(json.dumps(envelope))
    assert len(rows) == 1
    assert rows[0]["claim_id"] == "x"


def test_parse_bare_claims() -> None:
    rows = _parse_claims('{"claims":[{"claim_id":"y","text":"z"}]}')
    assert rows[0]["claim_id"] == "y"
