"""Accepted module prose must stay bound to reviewed, frozen source evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cbe.inventory import build_inventory
from cbe.module_explanations import explanation_content_sha256, validate_module_explanations
from cbe.token_budget import count_text_tokens


@pytest.fixture
def evidence(tmp_path: Path) -> tuple[dict, dict, dict, Path]:
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "service.py").write_text(
        "def first(value):\n    return value + 1\n\n"
        "def second(value):\n    return first(value) * 2\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_service.py").write_text(
        "def test_first():\n    assert 1 + 1 == 2\n", encoding="utf-8"
    )
    inventory = build_inventory(repo).to_dict()
    ledger = {
        "repo_root": inventory["repo_root"],
        "git_head": inventory["git_head"],
        "source_revision": inventory["source_revision"],
        "inventory": inventory,
    }
    production = [sid for sid, symbol in inventory["symbols"].items() if symbol["path"] == "service.py"]
    tests = [sid for sid, symbol in inventory["symbols"].items() if symbol["path"].startswith("tests/")]
    first = next(sid for sid in production if inventory["symbols"][sid]["name"] == "first")
    plan = {
        "source_revision": inventory["source_revision"],
        "groups": {
            "root": {"group_id": "root", "children": ["service", "test-catalogue"], "member_ids": []},
            "service": {"group_id": "service", "children": [], "member_ids": production},
            "test-catalogue": {"group_id": "test-catalogue", "children": [], "member_ids": tests},
        },
    }
    review_report = tmp_path / "review-report.json"
    review_report.write_text(
        '{"reviewer_id":"reviewer-b","decision":"accepted"}\n', encoding="utf-8"
    )
    record = {
        "author_id": "producer-a",
        "summary": "The service transforms input values.",
        "flow": "second calls first, then doubles the result.",
        "key_symbols": [first],
        "source_refs": [{"path": "service.py", "line": 4}],
        "uncertainties": "No external callers are described.",
        "review": {
            "reviewer_id": "reviewer-b",
            "decision": "accepted",
            "content_sha256": "",
            "source_revision": inventory["source_revision"],
            "evidence_ref": str(review_report),
        },
    }
    record["review"]["content_sha256"] = explanation_content_sha256(record)
    package = {"source_revision": inventory["source_revision"], "modules": {"service": record}}
    return ledger, plan, package, repo


def test_valid_package_returns_independent_records_and_canonical_hash(evidence: tuple) -> None:
    ledger, plan, package, _ = evidence
    record = package["modules"]["service"]
    payload = {key: record[key] for key in ("summary", "flow", "key_symbols", "source_refs", "uncertainties")}
    expected = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert explanation_content_sha256(record) == expected
    accepted = validate_module_explanations(ledger, plan, package)
    assert accepted == {"service": record}
    assert accepted["service"] is not record
    accepted["service"]["key_symbols"].clear()
    assert record["key_symbols"]


def test_empty_optional_package_is_valid(evidence: tuple) -> None:
    ledger, plan, package, _ = evidence
    assert validate_module_explanations(
        ledger, plan, {"source_revision": package["source_revision"], "modules": {}}
    ) == {}


def test_dependencies_may_cite_another_frozen_module(evidence: tuple) -> None:
    ledger, plan, package, _ = evidence
    record = package["modules"]["service"]
    record["source_refs"].append({"path": "tests/test_service.py", "line": 1})
    record["uncertainties"] = ""
    record["review"]["content_sha256"] = explanation_content_sha256(record)
    assert validate_module_explanations(ledger, plan, package)["service"] == record


@pytest.mark.parametrize("where", ["package", "plan", "ledger", "inventory", "review"])
def test_revision_mismatch_rejected(evidence: tuple, where: str) -> None:
    ledger, plan, package, _ = evidence
    if where == "package":
        package["source_revision"] = "stale"
    elif where == "plan":
        plan["source_revision"] = "stale"
    elif where == "ledger":
        ledger["source_revision"] = "stale"
    elif where == "inventory":
        ledger["inventory"]["source_revision"] = "stale"
    else:
        package["modules"]["service"]["review"]["source_revision"] = "stale"
    with pytest.raises(ValueError, match="source_revision"):
        validate_module_explanations(ledger, plan, package)


def test_changed_source_bytes_and_mismatched_frozen_hash_are_rejected(evidence: tuple) -> None:
    ledger, plan, package, repo = evidence
    source_path = repo / "service.py"
    original = source_path.read_bytes()
    source_path.write_text("def replacement():\n    return 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_module_explanations(ledger, plan, package)
    source_path.write_bytes(original)

    ledger["inventory"]["files"]["service.py"]["content_hash"] = "0" * 64
    with pytest.raises(ValueError, match="source_revision"):
        validate_module_explanations(ledger, plan, package)


@pytest.mark.parametrize("bad_line", [0, -1, True, 99])
def test_invalid_source_line_rejected(evidence: tuple, bad_line: object) -> None:
    ledger, plan, package, _ = evidence
    package["modules"]["service"]["source_refs"][0]["line"] = bad_line
    package["modules"]["service"]["review"]["content_sha256"] = explanation_content_sha256(
        package["modules"]["service"]
    )
    with pytest.raises(ValueError, match="line"):
        validate_module_explanations(ledger, plan, package)


def test_unenrolled_or_unknown_reference_rejected(evidence: tuple) -> None:
    ledger, plan, package, _ = evidence
    ledger["inventory"]["files"]["service.py"]["enrolled"] = False
    with pytest.raises(ValueError, match="enrolled"):
        validate_module_explanations(ledger, plan, package)

    ledger, plan, package, _ = evidence
    package["modules"]["service"]["source_refs"][0]["path"] = "missing.py"
    package["modules"]["service"]["review"]["content_sha256"] = explanation_content_sha256(
        package["modules"]["service"]
    )
    with pytest.raises(ValueError, match="frozen file"):
        validate_module_explanations(ledger, plan, package)


@pytest.mark.parametrize("change", ["author", "decision", "hash", "evidence_ref", "review_extra"])
def test_unreviewed_or_forged_review_rejected(evidence: tuple, change: str) -> None:
    ledger, plan, package, _ = evidence
    record = package["modules"]["service"]
    if change == "author":
        record["review"]["reviewer_id"] = record["author_id"]
    elif change == "decision":
        record["review"]["decision"] = "candidate"
    elif change == "hash":
        record["summary"] = "Rewritten without a new review."
    elif change == "evidence_ref":
        record["review"]["evidence_ref"] = " "
    else:
        record["review"]["unrecognized"] = True
    with pytest.raises(ValueError, match="review|content_sha256|evidence_ref"):
        validate_module_explanations(ledger, plan, package)


@pytest.mark.parametrize("change", ["missing", "relative", "empty", "directory"])
def test_review_requires_an_existing_report_file(evidence: tuple, change: str, tmp_path: Path) -> None:
    ledger, plan, package, _ = evidence
    if change == "missing":
        ref = tmp_path / "missing-report.json"
    elif change == "relative":
        ref = Path("review-report.json")
    elif change == "empty":
        ref = tmp_path / "empty-report.json"
        ref.touch()
    else:
        ref = tmp_path
    package["modules"]["service"]["review"]["evidence_ref"] = str(ref)
    with pytest.raises(ValueError, match="evidence_ref"):
        validate_module_explanations(ledger, plan, package)


@pytest.mark.parametrize("change", ["parent", "test_only", "nonmember_key", "unknown_member", "duplicate_key"])
def test_only_leaf_production_modules_and_member_keys_are_accepted(evidence: tuple, change: str) -> None:
    ledger, plan, package, _ = evidence
    record = package["modules"].pop("service")
    if change == "parent":
        package["modules"]["root"] = record
    elif change == "test_only":
        package["modules"]["test-catalogue"] = record
    else:
        package["modules"]["service"] = record
        if change == "nonmember_key":
            record["key_symbols"] = [plan["groups"]["test-catalogue"]["member_ids"][0]]
        elif change == "unknown_member":
            plan["groups"]["service"]["member_ids"].append("ghost")
        else:
            record["key_symbols"].append(record["key_symbols"][0])
        record["review"]["content_sha256"] = explanation_content_sha256(record)
    with pytest.raises(ValueError, match="leaf|production|member|duplicate"):
        validate_module_explanations(ledger, plan, package)


@pytest.mark.parametrize("change", ["keys", "refs", "record_extra", "package_extra"])
def test_structural_limits_and_extra_keys_are_rejected(evidence: tuple, change: str) -> None:
    ledger, plan, package, _ = evidence
    record = package["modules"]["service"]
    if change == "keys":
        record["key_symbols"] = record["key_symbols"] * 9
    elif change == "refs":
        record["source_refs"] = record["source_refs"] * 13
    elif change == "record_extra":
        record["legacy_summary"] = "unreviewed"
    else:
        package["legacy_groups"] = {}
    record["review"]["content_sha256"] = explanation_content_sha256(record)
    with pytest.raises(ValueError, match="220|8|12|unexpected"):
        validate_module_explanations(ledger, plan, package)


def test_reviewed_prose_over_target_is_advisory(evidence: tuple) -> None:
    ledger, plan, package, _ = evidence
    record = package["modules"]["service"]
    record["flow"] = "second calls first, then doubles the result. " * 30
    assert sum(count_text_tokens(record[key]) for key in ("summary", "flow", "uncertainties")) > 220
    record["review"]["content_sha256"] = explanation_content_sha256(record)
    assert "service" in validate_module_explanations(ledger, plan, package)
