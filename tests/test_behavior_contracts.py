from cbe.behavior_contracts import digest, obligations, validate, accepted_projection
import pytest


def test_coverage_diagnostics_name_missing_key_and_dangling_target():
    from cbe.behavior_contracts import validate, obligations, check_coverage_location
    prior = {"f": {"behavior": "old maintenance contract"}}
    with pytest.raises(ValueError, match=r"items\[i\]\.behavior_contract\.coverage"):
        check_coverage_location({"coverage": {"f:behavior": {"claims": ["unique_delta"]}}})
    value = {"claims": [{"id": "c1", "effect": "new effect"}], "coverage": {}}
    with pytest.raises(ValueError, match=r"missing=\['f:behavior'\]"):
        validate(value, symbol_id="f", source_revision="r", owned_spans=[], prior=prior)
    value["coverage"] = {"f:behavior": {"old_sha256": obligations(prior)["f:behavior"]["content_sha256"],
                                        "claims": ["explanatory prose"]}}
    with pytest.raises(ValueError, match=r"allowed=\['c1', 'unique_delta'\]"):
        validate(value, symbol_id="f", source_revision="r", owned_spans=[], prior=prior)


def test_canonical_mapping_cannot_drop_old_failure_or_change_old_hash():
    prior = {"frag-a": {"behavior": "Sets state before failure", "failures": ["raises"]}}
    value = {"claims": [{"id": "transition", "effect": "sets state then raises"}],
             "coverage": {key: {"old_sha256": item["content_sha256"], "claims": ["transition"]}
                          for key, item in obligations(prior).items()}}
    result = validate(value, symbol_id="f", source_revision="r", owned_spans=[], prior=prior)
    assert result["prior_detail_hashes"] == {"frag-a": digest(prior["frag-a"])}
    value["coverage"].pop("frag-a:failures")
    with pytest.raises(ValueError, match="every old"):
        validate(value, symbol_id="f", source_revision="r", owned_spans=[], prior=prior)
    value["coverage"]["frag-a:failures"] = {"old_sha256": "wrong", "claims": ["transition"]}
    with pytest.raises(ValueError, match="hash mismatch"):
        validate(value, symbol_id="f", source_revision="r", owned_spans=[], prior=prior)


def test_same_revision_accepted_shared_claim_and_local_gap_are_distinct():
    claim = {"id": "empty", "condition": "empty input", "effect": "unchanged"}
    target = {"behavior": "unique delta", "provenance": {"behavior_contract": {
        "source_revision": "r", "claims": [claim]}}}
    owner = {"behavior": "calls target", "provenance": {"behavior_contract": {
        "claim_refs": [{"symbol_id": "target", "claim_id": "empty", "content_sha256": digest(claim)}],
        "local_view_gaps": [{"dependency_id": "target", "reason": "not in original local view"}]}}}
    ledger = {"source_revision": "r", "details": {"owner": owner, "target": target},
              "fact_reviews": {"target": {"state": "source_checked", "content_sha256": digest(target)}}}
    result = accepted_projection(ledger, "owner")
    assert result["claim_refs"][0]["status"] == "accepted"
    assert result["local_view_gaps"][0]["accepted_dependency_available"] is True
    assert result["local_view_gaps"][0]["reason"] == "not in original local view"
    ledger["source_revision"] = "new"
    assert accepted_projection(ledger, "owner")["claim_refs"][0]["status"] == "unresolved"


def test_local_gap_qualified_name_locates_only_unique_current_hash_bound_dependency():
    target = {"behavior": "R non-None values replace L", "provenance": {}}
    owner = {"provenance": {"behavior_contract": {"source_revision": "r",
        "local_view_gaps": [{"dependency_id": "pkg.helper", "reason": "not in original local view"}],
        "current_unresolved": ["actual runtime binding unverified"]}}}
    ledger = {"source_revision": "r", "inventory": {"symbols": {
        "helper-id": {"qualified_name": "pkg.helper"}}},
        "details": {"owner": owner, "helper-id": target},
        "fact_reviews": {"helper-id": {"state": "batch_accepted", "content_sha256": digest(target)}}}
    from cbe.models import TaskRecord
    batch = {"batch_id": "b", "input_ids": ["helper-id"]}
    identity = digest({"contract": "module-facts/1", "batch": batch, "source_revision": "r"})
    target["input_hash"] = identity
    ledger["fact_reviews"]["helper-id"]["content_sha256"] = digest(target)
    ledger["fact_batches"] = {"b": batch}
    ledger["tasks"] = {"author": TaskRecord("author", "fact_author", ["helper-id"], identity,
        "committed", extra={"fact_contract": "module-facts/1", "batch_id": "b"}).to_dict()}
    import copy
    before = copy.deepcopy(ledger)
    result = accepted_projection(ledger, "owner")
    gap = result["local_view_gaps"][0]
    assert gap["dependency_id"] == "helper-id" and gap["declared_dependency_id"] == "pkg.helper"
    assert gap["accepted_dependency_available"] is True
    assert gap["reason"] == "not in original local view"
    assert result["claim_refs"] == [] and result["current_unresolved"] == ["actual runtime binding unverified"]
    assert ledger == before
    stale = copy.deepcopy(before)
    stale["source_revision"] = "new"
    stale["details"]["owner"]["provenance"]["behavior_contract"]["source_revision"] = "new"
    assert accepted_projection(stale, "owner")["local_view_gaps"][0]["dependency_id"] == "pkg.helper"
    missing = copy.deepcopy(before)
    missing["tasks"] = {}
    assert accepted_projection(missing, "owner")["local_view_gaps"][0]["dependency_id"] == "pkg.helper"
    collision = copy.deepcopy(before)
    collision["inventory"]["symbols"]["other-id"] = {"qualified_name": "pkg.helper"}
    assert accepted_projection(collision, "owner")["local_view_gaps"][0]["dependency_id"] == "pkg.helper"
    ledger["source_revision"] = "new"
    gap = accepted_projection(ledger, "owner")["local_view_gaps"][0]
    assert gap["dependency_id"] == "pkg.helper" and not gap["accepted_dependency_available"]
    ledger["source_revision"] = "r"
    ledger["details"]["helper-id"]["behavior"] = "changed body"
    assert accepted_projection(ledger, "owner")["local_view_gaps"][0]["accepted_dependency_available"] is False
    ledger["inventory"]["symbols"]["other-id"] = {"qualified_name": "pkg.helper"}
    gap = accepted_projection(ledger, "owner")["local_view_gaps"][0]
    assert gap["dependency_id"] == "pkg.helper" and not gap["accepted_dependency_available"]
    ledger["inventory"]["symbols"]["other-id"]["qualified_name"] = "other.helper"
    ledger["inventory"]["symbols"]["helper-id"]["qualified_name"] = "other.pkg.helper"
    assert accepted_projection(ledger, "owner")["local_view_gaps"][0]["dependency_id"] == "pkg.helper"
