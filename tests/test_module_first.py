"""A legacy group tree can seed, but cannot verify, module ownership."""

from __future__ import annotations

import copy
import json

import pytest

from cbe.module_first import build_collapsed_module_plan


def _fixture() -> tuple[dict, dict]:
    symbols = {name: {"id": name} for name in ("alpha", "beta", "gamma", "delta")}

    def group(
        group_id: str,
        parent_id: str | None,
        children: list[str],
        member_ids: list[str],
    ) -> dict:
        return {
            "group_id": group_id,
            "parent_id": parent_id,
            "children": children,
            "member_ids": member_ids,
            "title": f"Title {group_id}",
            "question_answered": f"Question {group_id}?",
            "body": "SECRET_OLD_BODY: do not copy this prose",
            "grouping_reason": "SECRET_OLD_REASON: do not copy this prose",
            "extra": {"evidence_summary": {"behavior": "SECRET_OLD_EXTRA"}},
        }

    groups = {
        "root": group("root", None, ["area-b", "area-a"], []),
        "area-b": group("area-b", "root", ["module-b"], []),
        "module-b": group("module-b", "area-b", ["workflow-b"], ["alpha"]),
        "workflow-b": group("workflow-b", "module-b", ["leaf-b"], ["beta"]),
        "leaf-b": group("leaf-b", "workflow-b", [], ["gamma"]),
        "area-a": group("area-a", "root", ["module-a"], []),
        "module-a": group("module-a", "area-a", [], ["delta"]),
    }
    inventory = {"source_revision": "revision-1", "symbols": symbols}
    legacy = {
        "source_revision": "revision-1",
        "inventory": copy.deepcopy(inventory),
        "groups": groups,
    }
    return legacy, inventory


def test_collapse_keeps_two_levels_and_moves_every_canonical_symbol() -> None:
    legacy, inventory = _fixture()
    before = copy.deepcopy(legacy)
    plan = build_collapsed_module_plan(legacy, inventory, group_limit=7)

    assert list(plan["groups"]) == ["root", "area-b", "area-a", "module-b", "module-a"]
    assert plan["groups"]["root"]["children"] == ["area-b", "area-a"]
    assert plan["groups"]["area-b"]["children"] == ["module-b"]
    assert plan["groups"]["module-b"]["children"] == []
    assert plan["groups"]["module-b"]["member_ids"] == ["alpha", "beta", "gamma"]
    assert plan["groups"]["module-a"]["member_ids"] == ["delta"]
    assert "symbol_to_module" not in plan
    assert sorted(plan["groups"]["module-b"]["member_ids"]) == ["alpha", "beta", "gamma"]
    assert plan["stats"]["legacy_group_count"] == 7
    assert plan["stats"]["retained_group_count"] == 5
    assert plan["stats"]["collapsed_group_count"] == 2
    assert plan["stats"]["module_count"] == 2
    assert plan["stats"]["symbol_count"] == 4
    assert legacy == before
    assert "SECRET_OLD" not in json.dumps(plan)
    assert all(group["body"] == "" for group in plan["groups"].values())
    assert all(group["extra"]["review_state"] == "candidate" for group in plan["groups"].values())
    assert plan["groups"]["module-b"]["title"] == "Title module-b"
    assert plan["groups"]["module-b"]["question_answered"] == "Where is Title module b in the source tree?"


def test_test_only_groups_collapse_into_one_explicit_test_catalogue() -> None:
    legacy, inventory = _fixture()
    for symbol in inventory["symbols"].values():
        symbol["path"] = "celery/core.py"
    legacy["inventory"] = copy.deepcopy(inventory)
    inventory["symbols"]["alpha"]["path"] = "t/unit/test_core.py"
    inventory["symbols"]["beta"]["path"] = "t/unit/test_core.py"
    inventory["symbols"]["gamma"]["path"] = "t/unit/test_core.py"
    legacy["inventory"]["symbols"] = copy.deepcopy(inventory["symbols"])
    plan = build_collapsed_module_plan(legacy, inventory)
    assert "module-b" not in plan["groups"]
    assert "area-b" not in plan["groups"]
    assert plan["groups"]["test-support-catalogue"]["member_ids"] == ["alpha", "beta", "gamma"]
    assert plan["groups"]["test-support-catalogue"]["parent_id"] == "support-catalogue-area"
    assert plan["groups"]["module-a"]["member_ids"] == ["delta"]
    assert plan["stats"]["test_only_modules_collapsed"] == 1
    assert plan["stats"]["test_symbol_count"] == 3
    assert plan["stats"]["module_count"] == 2


@pytest.mark.parametrize("where", ["top", "legacy_inventory", "current_inventory"])
def test_revision_mismatch_is_rejected(where: str) -> None:
    legacy, inventory = _fixture()
    if where == "top":
        legacy["source_revision"] = "another-revision"
    elif where == "legacy_inventory":
        legacy["inventory"]["source_revision"] = "another-revision"
    else:
        inventory["source_revision"] = "another-revision"
    with pytest.raises(ValueError, match="source_revision"):
        build_collapsed_module_plan(legacy, inventory)


def test_canonical_symbol_id_set_must_match() -> None:
    legacy, inventory = _fixture()
    del inventory["symbols"]["alpha"]
    with pytest.raises(ValueError, match="canonical symbol IDs"):
        build_collapsed_module_plan(legacy, inventory)


def test_duplicate_and_missing_symbol_ownership_are_rejected() -> None:
    legacy, inventory = _fixture()
    legacy["groups"]["module-a"]["member_ids"].append("alpha")
    with pytest.raises(ValueError, match="duplicate symbol ownership"):
        build_collapsed_module_plan(legacy, inventory)

    legacy, inventory = _fixture()
    legacy["groups"]["module-a"]["member_ids"].clear()
    with pytest.raises(ValueError, match="missing symbol ownership"):
        build_collapsed_module_plan(legacy, inventory)


def test_unknown_member_is_rejected() -> None:
    legacy, inventory = _fixture()
    legacy["groups"]["module-a"]["member_ids"] = ["delta", "ghost"]
    with pytest.raises(ValueError, match="unknown canonical symbol"):
        build_collapsed_module_plan(legacy, inventory)


def test_cycle_and_broken_parent_are_rejected() -> None:
    legacy, inventory = _fixture()
    legacy["groups"]["leaf-b"]["children"] = ["workflow-b"]
    legacy["groups"]["workflow-b"]["parent_id"] = "leaf-b"
    with pytest.raises(ValueError, match="cycle"):
        build_collapsed_module_plan(legacy, inventory)

    legacy, inventory = _fixture()
    legacy["groups"]["module-b"]["parent_id"] = "missing-parent"
    with pytest.raises(ValueError, match="missing parent"):
        build_collapsed_module_plan(legacy, inventory)


def test_group_limit_and_shallow_owner_are_rejected() -> None:
    legacy, inventory = _fixture()
    with pytest.raises(ValueError, match="group_limit"):
        build_collapsed_module_plan(legacy, inventory, group_limit=4)

    legacy, inventory = _fixture()
    legacy["groups"]["area-a"]["member_ids"] = ["delta"]
    legacy["groups"]["module-a"]["member_ids"] = []
    with pytest.raises(ValueError, match="depth 2"):
        build_collapsed_module_plan(legacy, inventory)
