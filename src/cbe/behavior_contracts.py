"""Structural ownership and reader projection of reviewed behavior claims.

The existing Detail.provenance is the only store. These checks cannot establish
semantic equivalence: independent review must check every coverage assertion.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

FIELDS = ("behavior", "inputs_outputs", "effects", "failures", "dependencies", "unresolved")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def obligations(details: dict[str, dict]) -> dict[str, dict]:
    """Every nonempty old field has an immutable, locatable coverage obligation."""
    return {sid + ":" + field: {"symbol_id": sid, "field": field,
                                "content_sha256": digest(detail[field])}
            for sid, detail in details.items() for field in FIELDS
            if detail.get(field) not in (None, "", [], {})}


def check_coverage_location(item: dict) -> None:
    if "coverage" in item:
        raise ValueError("coverage is at the wrong location: items[i].coverage is not consumed; "
            "write items[i].behavior_contract.coverage with EVERY exact Old obligations ID and valid claim targets; "
            "the program will not move or rewrite the original business JSON")


def validate(value: object, *, symbol_id: str, source_revision: str,
             owned_spans: list[dict], prior: dict[str, dict] | None = None,
             prior_findings: list[dict] | None = None) -> dict:
    if not isinstance(value, dict):
        raise ValueError("behavior_contract must be an object")
    claims = value.get("claims") or []
    refs = value.get("claim_refs") or []
    ids: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get("id"), str) or not claim["id"]:
            raise ValueError("behavior claim needs a nonempty local id")
        if claim["id"] in ids:
            raise ValueError("duplicate behavior claim id")
        ids.add(claim["id"])
        if not any(isinstance(claim.get(key), str) and claim[key].strip()
                   for key in ("condition", "effect", "failure")):
            raise ValueError("behavior claim needs condition/effect/failure content")
    for ref in refs:
        if not isinstance(ref, dict) or any(not isinstance(ref.get(key), str) or not ref[key]
                                          for key in ("symbol_id", "claim_id", "content_sha256")):
            raise ValueError("behavior claim reference needs bound owner/id/hash")
    gaps = value.get("local_view_gaps") or []
    for gap in gaps:
        if not isinstance(gap, dict) or not gap.get("dependency_id") or not gap.get("reason"):
            raise ValueError("local view gap needs dependency_id and reason")
    coverage = value.get("coverage") or {}
    expected = obligations(prior or {})
    expected.update(finding_obligations(prior_findings or []))
    if prior is not None:
        if not isinstance(coverage, dict):
            raise ValueError("behavior_contract.coverage must be an object keyed by exact Old obligations IDs")
        if set(coverage) != set(expected):
            raise ValueError("canonical coverage must map every old accepted obligation at behavior_contract.coverage; "
                f"missing={sorted(set(expected) - set(coverage))}; unexpected={sorted(set(coverage) - set(expected))}; "
                "copy complete IDs, including :behavior or other field suffixes and finding: hashes")
        for old_id, mapping in coverage.items():
            if not isinstance(mapping, dict) or mapping.get("old_sha256") != expected[old_id]["content_sha256"]:
                raise ValueError(f"canonical coverage old hash mismatch at behavior_contract.coverage[{old_id!r}]")
            targets = mapping.get("claims") or []
            unknown_ids = {f"current_unresolved:{index}" for index, _ in enumerate(value.get("current_unresolved") or [])}
            allowed = ids | {"unique_delta"} | unknown_ids
            if not isinstance(targets, list) or not targets or any(not isinstance(t, str) for t in targets) or not set(targets) <= allowed:
                raise ValueError("canonical coverage has dangling new claim targets at "
                    f"behavior_contract.coverage[{old_id!r}].claims; actual={targets!r}; allowed={sorted(allowed)}; "
                    "use local claim IDs, unique_delta, or current_unresolved:<index>, never prose")
    return {"version": 2, "owner_id": symbol_id, "source_revision": source_revision,
            "owned_spans": owned_spans, "claims": claims, "claim_refs": refs,
            "local_view_gaps": gaps, "current_unresolved": value.get("current_unresolved") or [],
            "coverage": coverage, "prior_detail_hashes": {
                sid: digest(detail) for sid, detail in (prior or {}).items()}}


def finding_obligations(findings: list[dict]) -> dict[str, dict]:
    return {"finding:" + digest(finding): {"content_sha256": digest(finding)} for finding in findings}


def contract(detail: dict) -> dict:
    return (detail.get("provenance") or {}).get("behavior_contract") or {}


def claim_text(claim: dict) -> str:
    return "; ".join(str(claim[key]) for key in ("condition", "effect", "failure") if claim.get(key))


def _current_dependency_locator(ledger: dict, symbol_id: str) -> bool:
    """Reuse normal fact input validation; availability is not relation review."""
    from cbe.models import TaskRecord
    from cbe.module_facts import accepted_fact, _validate_author_input
    from cbe.packets import Packet
    from cbe.store import StaleWriteError
    if not accepted_fact(ledger, symbol_id):
        return False
    detail = ledger["details"][symbol_id]
    for raw in (ledger.get("tasks") or {}).values():
        if (raw.get("kind") != "fact_author" or symbol_id not in raw.get("input_ids", [])
            or not detail.get("input_hash") or raw.get("input_hash") != detail["input_hash"]):
            continue
        try:
            packets = []
            if not (raw.get("extra") or {}).get("batch_id"):
                packets = [Packet.from_dict(p) for p in (ledger.get("packets") or {}).get("packets", [])
                           if p.get("packet_id") == detail.get("packet_id")]
            _validate_author_input(ledger, TaskRecord.from_dict(raw), packets)
        except (StaleWriteError, ValueError, KeyError):
            continue
        return True
    return False


def accepted_projection(ledger: dict, symbol_id: str) -> dict:
    """Resolve only same-revision, hash-bound accepted claim references.

    A local evidence gap may gain a dependency locator, but is never silently
    erased or called a runtime guarantee by this structural projection.
    """
    from cbe.module_facts import accepted_fact
    detail = (ledger.get("details") or {}).get(symbol_id) or {}
    own = contract(detail)
    resolved = []
    for ref in own.get("claim_refs") or []:
        target = (ledger.get("details") or {}).get(ref["symbol_id"]) or {}
        target_contract = contract(target)
        claim = next((item for item in target_contract.get("claims") or []
                      if item["id"] == ref["claim_id"]), None)
        valid = (accepted_fact(ledger, ref["symbol_id"])
                 and target_contract.get("source_revision") == ledger["source_revision"]
                 and claim is not None and digest(claim) == ref["content_sha256"])
        resolved.append({**ref, "status": "accepted" if valid else "unresolved",
                         **({"claim": claim} if valid else {})})
    gaps = []
    symbols = (ledger.get("inventory") or {}).get("symbols") or {}
    for gap in own.get("local_view_gaps") or []:
        declared = gap["dependency_id"]
        target = declared
        # A unique frozen qualified name gives a declaration locator, never a
        # runtime binding or an independently checked caller/callee relation.
        if (declared not in symbols and declared not in (ledger.get("details") or {})
            and own.get("source_revision") == ledger.get("source_revision")):
            matches = [sid for sid, record in symbols.items()
                       if record.get("qualified_name") == declared]
            if len(matches) == 1 and _current_dependency_locator(ledger, matches[0]):
                target = matches[0]
        gaps.append({**gap, "dependency_id": target,
                     **({"declared_dependency_id": declared} if target != declared else {}),
                     "accepted_dependency_available": accepted_fact(ledger, target)})
    return {"owner_id": symbol_id, "claims": own.get("claims") or [],
            "claim_refs": [{key: value for key, value in ref.items() if key != "claim"} for ref in resolved],
            "local_view_gaps": gaps, "current_unresolved": own.get("current_unresolved") or []}


def reader_detail(detail: dict) -> dict:
    """Keep composition audit mappings in the original internal provenance."""
    result = {key: value for key, value in detail.items() if key != "nav_sentence"}
    if contract(detail):
        result["provenance"] = {key: value for key, value in (detail.get("provenance") or {}).items()
                                if key != "behavior_contract"}
    return result
