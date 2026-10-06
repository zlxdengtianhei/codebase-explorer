"""A module author sees verified, bounded source, not old group prose."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from cbe.graph import build_graph
from cbe.inventory import build_inventory
from cbe.module_author import build_module_author_packet
from cbe.token_budget import count_text_tokens
from cbe.weighting import SourceDriftError, assign_detail_priorities


APP = '''import json


def important_flow(items, target):
    """Apply each item and persist the result."""
    result = []
    for item in items:
        try:
            result.append(item * 2)
        except TypeError:
            raise ValueError("bad item")
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(result, handle)
    return result


def small_helper(value):
    return value + 1
'''

TESTS = '''from app import important_flow


def test_important_flow(tmp_path):
    assert important_flow([1, 2], str(tmp_path / "out")) == [2, 4]
'''


def _fixture(tmp_path: Path) -> tuple[dict, dict, Path, dict[str, str]]:
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "app.py").write_text(APP, encoding="utf-8")
    (repo / "tests/test_app.py").write_text(TESTS, encoding="utf-8")
    inventory = build_inventory(repo)
    policy = assign_detail_priorities(inventory, build_graph(inventory), repo)
    ledger = {
        "repo_root": str(repo),
        "source_revision": inventory.source_revision,
        "inventory": inventory.to_dict(),
        "documentation_policy": {"symbols": policy},
        "groups": {"stale": {"body": "SECRET_OLD_BODY"}},
    }
    ids = {
        symbol.name: symbol.id
        for symbol in inventory.symbols.values()
        if symbol.kind == "function"
    }
    plan = {
        "source_revision": inventory.source_revision,
        "groups": {
            "root": {
                "group_id": "root", "parent_id": None, "children": ["module"],
                "member_ids": [], "title": "Root", "question_answered": "How does it work?",
            },
            "module": {
                "group_id": "module", "parent_id": "root", "children": [],
                "member_ids": list(inventory.symbols), "title": "App module",
                "question_answered": "How are values applied?", "body": "SECRET_OLD_BODY",
            },
        },
    }
    return ledger, plan, repo, ids


def test_packet_has_exact_bounded_source_and_honest_coverage(tmp_path: Path) -> None:
    ledger, plan, repo, ids = _fixture(tmp_path)
    before_ledger, before_plan = copy.deepcopy(ledger), copy.deepcopy(plan)
    packet = build_module_author_packet(ledger, plan, "module", max_source_tokens=110)

    metadata = packet["metadata"]
    assert metadata["source_revision"] == ledger["source_revision"]
    assert metadata["group_id"] == "module"
    assert metadata["source_token_count"] == count_text_tokens(packet["source_context"])
    assert 0 < metadata["source_token_count"] <= 110
    assert metadata["max_source_tokens"] == 110
    assert metadata["member_count"] == len(plan["groups"]["module"]["member_ids"])
    assert metadata["fully_covered_member_count"] < metadata["member_count"]
    assert metadata["omitted_sources"]
    assert metadata["fully_covered_member_count"] + len(metadata["omitted_sources"]) == metadata["member_count"]
    assert ids["important_flow"] in {item["symbol_id"] for item in metadata["selected_sources"]}
    assert all(item["source_role"] == "implementation" for item in metadata["selected_sources"])
    for item in metadata["selected_sources"]:
        text = (repo / item["path"]).read_text(encoding="utf-8")
        assert text[item["start_char"]:item["end_char"]] in packet["source_context"]
        assert f"{item['path']}:L{item['start_line']}" in packet["source_context"]
    assert "SECRET_OLD_BODY" not in packet["prompt"]
    assert "<=200" in packet["instruction"]
    assert "six-field" in packet["instruction"]
    assert all(field in packet["instruction"] for field in (
        "summary", "flow", "uncertainties", "key_symbols", "source_refs",
    ))
    assert "nonempty" in packet["instruction"]
    assert ledger == before_ledger and plan == before_plan


def test_production_precedes_tests_then_weighted_score(tmp_path: Path) -> None:
    ledger, plan, _repo, ids = _fixture(tmp_path)
    policies = ledger["documentation_policy"]["symbols"]
    policies[ids["test_important_flow"]]["score"] = 1000
    policies[ids["important_flow"]]["score"] = 20
    policies[ids["small_helper"]]["score"] = 10

    packet = build_module_author_packet(ledger, plan, "module", max_source_tokens=80)
    selected = packet["metadata"]["selected_sources"]
    assert selected
    assert selected[0]["symbol_id"] == ids["important_flow"]
    assert selected[0]["source_role"] == "implementation"
    assert ids["test_important_flow"] in {
        item["symbol_id"] for item in packet["metadata"]["omitted_sources"]
    }


@pytest.mark.parametrize("revision_field", ["plan", "ledger", "inventory"])
def test_rejects_revision_mismatch(tmp_path: Path, revision_field: str) -> None:
    ledger, plan, _repo, _ids = _fixture(tmp_path)
    if revision_field == "plan":
        plan["source_revision"] = "other"
    elif revision_field == "ledger":
        ledger["source_revision"] = "other"
    else:
        ledger["inventory"]["source_revision"] = "other"
    with pytest.raises(ValueError, match="source_revision"):
        build_module_author_packet(ledger, plan, "module")


def test_rejects_drift_even_in_budget_omitted_member_file(tmp_path: Path) -> None:
    ledger, plan, repo, _ids = _fixture(tmp_path)
    (repo / "tests/test_app.py").write_text(TESTS + "\n# changed\n", encoding="utf-8")
    with pytest.raises(SourceDriftError, match="tests/test_app.py"):
        build_module_author_packet(ledger, plan, "module", max_source_tokens=80)


def test_rejects_navigation_empty_and_test_only_groups(tmp_path: Path) -> None:
    ledger, plan, _repo, ids = _fixture(tmp_path)
    with pytest.raises(ValueError, match="leaf"):
        build_module_author_packet(ledger, plan, "root")

    plan["groups"]["module"]["member_ids"] = []
    with pytest.raises(ValueError, match="member"):
        build_module_author_packet(ledger, plan, "module")

    plan["groups"]["module"]["member_ids"] = [ids["test_important_flow"]]
    with pytest.raises(ValueError, match="test-only"):
        build_module_author_packet(ledger, plan, "module")


def test_rejects_missing_weighted_policy_instead_of_silently_ranking_by_id(tmp_path: Path) -> None:
    ledger, plan, _repo, ids = _fixture(tmp_path)
    del ledger["documentation_policy"]["symbols"][ids["important_flow"]]
    with pytest.raises(ValueError, match="weighted policy"):
        build_module_author_packet(ledger, plan, "module")


def test_budget_cannot_leave_only_test_evidence(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    long_name = "implementation_" + "x" * 100 + ".py"
    (repo / long_name).write_text("def prod(): return '" + "x" * 1200 + "'\n", encoding="utf-8")
    (repo / "tests/test_app.py").write_text(
        "def test_prod():\n    assert True\n", encoding="utf-8"
    )
    inventory = build_inventory(repo)
    ledger = {
        "repo_root": str(repo), "source_revision": inventory.source_revision,
        "inventory": inventory.to_dict(),
        "documentation_policy": {
            "symbols": assign_detail_priorities(inventory, build_graph(inventory), repo)
        },
    }
    plan = {
        "source_revision": inventory.source_revision,
        "groups": {"module": {
            "group_id": "module", "children": [], "member_ids": list(inventory.symbols),
        }},
    }
    with pytest.raises(ValueError, match="implementation source"):
        build_module_author_packet(ledger, plan, "module", max_source_tokens=60)
