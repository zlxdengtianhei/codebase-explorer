"""A fresh inventory can seed a bounded structural module candidate."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from cbe.inventory import build_inventory
from cbe.module_first_render import _validate_plan
from cbe.module_inventory_plan import build_inventory_module_plan


def _ledger(paths: list[str], *, group_limit: int = 40) -> dict:
    symbols = {
        f"{path}::function::item::{index}": {
            "id": f"{path}::function::item::{index}",
            "path": path,
            "name": "item",
        }
        for index, path in enumerate(paths)
    }
    files = {path: {"path": path} for path in paths}
    return {
        "source_revision": "rev_frozen",
        "inventory": {
            "source_revision": "rev_frozen",
            "files": files,
            "symbols": symbols,
        },
        "documentation_policy": {"group_limit": group_limit},
        "groups": {"stale": {"body": "SECRET_OLD_BEHAVIOR: do not use"}},
        "details": {"stale": {"behavior": "SECRET_OLD_DETAIL: do not use"}},
    }


def _owners(plan: dict) -> dict[str, str]:
    return {
        symbol_id: group_id
        for group_id, group in plan["groups"].items()
        for symbol_id in group["member_ids"]
    }


def test_directory_modules_have_exact_source_ownership_and_renderer_shape() -> None:
    ledger = _ledger([
        "src/cbe/first.py", "src/cbe/second.py", "src/api/main.py",
        "scripts/run.py", "top.py",
    ])
    before = copy.deepcopy(ledger)
    plan = build_inventory_module_plan(ledger)
    groups = plan["groups"]

    assert plan["source_revision"] == "rev_frozen"
    assert groups["root"]["children"] == ["area:.", "area:scripts", "area:src"]
    assert groups["area:src"]["children"] == ["module:src/api", "module:src/cbe"]
    assert {sid for sid in groups["module:src/cbe"]["member_ids"]} == {
        sid for sid, record in ledger["inventory"]["symbols"].items()
        if record["path"].startswith("src/cbe/")
    }
    assert groups["module:src/cbe"]["extra"]["inventory_path"] == "src/cbe"
    assert groups["module:src/cbe"]["children"] == []
    assert all(not group["member_ids"] for group in groups.values() if group["children"])
    assert _validate_plan(ledger, plan) == _owners(plan)
    assert set(_owners(plan)) == set(ledger["inventory"]["symbols"])
    assert plan["stats"]["directory_count"] == 4
    assert plan["stats"]["module_count"] == 4
    assert ledger == before


def test_tests_from_both_roots_share_one_catalogue_without_mixing_production() -> None:
    ledger = _ledger([
        "src/tests_helper.py", "t/unit/test_a.py", "tests/integration/test_b.py",
    ])
    plan = build_inventory_module_plan(ledger)
    groups = plan["groups"]
    catalogue = groups["test-support-catalogue"]
    test_ids = {
        sid for sid, record in ledger["inventory"]["symbols"].items()
        if record["path"].startswith(("t/", "tests/"))
    }

    assert catalogue["parent_id"] == "support-catalogue-area"
    assert catalogue["member_ids"] == sorted(test_ids)
    assert groups["support-catalogue-area"]["children"] == ["test-support-catalogue"]
    assert "support-catalogue-area" in groups["root"]["children"]
    assert groups["module:src"]["member_ids"] == sorted(set(_owners(plan)) - test_ids)
    assert plan["stats"]["test_symbol_count"] == 2
    assert plan["stats"]["module_count"] == 2
    assert _validate_plan(ledger, plan) == _owners(plan)


def test_example_docs_extra_release_and_name_based_tests_are_support_only() -> None:
    ledger = _ledger([
        "setup.py", "examples/sample.py", "docs/conf.py", "extra/script.py",
        "release/make.py", "src/test_helper.py", "src/example_client.py",
        "src/production.py",
    ])
    plan = build_inventory_module_plan(ledger)
    groups = plan["groups"]
    paths = {
        group_id: {ledger["inventory"]["symbols"][sid]["path"] for sid in group["member_ids"]}
        for group_id, group in groups.items()
        if group["member_ids"]
    }

    assert paths["test-support-catalogue"] == {"src/test_helper.py"}
    assert paths["example-support-catalogue"] == {"examples/sample.py", "src/example_client.py"}
    assert paths["docs-support-catalogue"] == {"docs/conf.py"}
    assert paths["extra-support-catalogue"] == {"extra/script.py"}
    assert paths["release-support-catalogue"] == {"release/make.py"}
    assert paths["module:."] == {"setup.py"}
    assert paths["module:src"] == {"src/production.py"}
    assert groups["support-catalogue-area"]["children"] == [
        "test-support-catalogue", "example-support-catalogue",
        "docs-support-catalogue", "extra-support-catalogue", "release-support-catalogue",
    ]
    assert plan["stats"]["support_symbol_counts"] == {
        "test": 1, "example": 2, "docs": 1, "extra": 1, "release": 1,
    }
    assert _validate_plan(ledger, plan) == _owners(plan)


def test_group_cap_merges_smallest_directories_within_area_without_losing_symbols() -> None:
    ledger = _ledger([
        "src/a/one.py", "src/b/two.py", "src/c/three.py", "src/d/four.py",
        "pkg/core.py", "tests/test_core.py",
    ], group_limit=8)
    plan = build_inventory_module_plan(ledger)

    assert len(plan["groups"]) == 8
    assert plan["stats"]["group_count"] == 8
    assert plan["stats"]["merged_directory_count"] == 2
    assert "area:pkg" in plan["groups"] and "area:src" in plan["groups"]
    assert set(_owners(plan)) == set(ledger["inventory"]["symbols"])
    assert len(_owners(plan)) == len(ledger["inventory"]["symbols"])
    for sid, group_id in _owners(plan).items():
        source_dir = ledger["inventory"]["symbols"][sid]["path"].rsplit("/", 1)[0]
        prefix = plan["groups"][group_id]["extra"]["inventory_path"]
        if group_id != "test-support-catalogue":
            assert source_dir == prefix or source_dir.startswith(prefix + "/")
    assert _validate_plan(ledger, plan) == _owners(plan)


def test_oversized_directory_splits_by_files_and_large_file_chunks() -> None:
    ledger = _ledger(
        ["src/large.py"] * 180 + ["src/helper.py"] * 60 + ["src/other.py"] * 40,
        group_limit=4,
    )
    plan = build_inventory_module_plan(ledger)
    groups = plan["groups"]
    leaves = [groups[group_id] for group_id in groups["area:src"]["children"]]

    assert len(leaves) == 2
    assert all(group["group_id"].startswith("module-part:src:") for group in leaves)
    assert all(0 < len(group["member_ids"]) <= 150 for group in leaves)
    assert sorted(len(group["member_ids"]) for group in leaves) == [130, 150]
    assert set(_owners(plan)) == set(ledger["inventory"]["symbols"])
    assert plan["stats"]["split_directory_count"] == 1
    assert plan["stats"]["split_module_count"] == 1
    assert plan["stats"]["max_production_module_symbols"] == 150
    assert _validate_plan(ledger, plan) == _owners(plan)

    with pytest.raises(ValueError, match="group_limit.*minimum"):
        build_inventory_module_plan(ledger, group_limit=3)


def test_cap_cannot_merge_two_modules_beyond_symbol_bound() -> None:
    ledger = _ledger(["src/a.py"] * 100 + ["src/b.py"] * 100)
    with pytest.raises(ValueError, match="group_limit.*minimum"):
        build_inventory_module_plan(ledger, group_limit=3)


def test_tight_cap_repartitions_whole_files_deterministically() -> None:
    ledger = _ledger(
        ["src/a.py"] * 100 + ["src/b.py"] * 100 + ["src/c.py"] * 100,
        group_limit=4,
    )
    plan = build_inventory_module_plan(ledger)
    modules = [plan["groups"][gid] for gid in plan["groups"]["area:src"]["children"]]

    assert len(plan["groups"]) == 4
    assert [len(module["member_ids"]) for module in modules] == [150, 150]
    assert all(module["extra"]["inventory_path"] == "src" for module in modules)
    assert plan["stats"]["repacked_area_count"] == 1
    assert set(_owners(plan)) == set(ledger["inventory"]["symbols"])
    assert _validate_plan(ledger, plan) == _owners(plan)


def test_impossible_cap_is_explicit_and_does_not_mutate_ledger() -> None:
    ledger = _ledger(["alpha/a.py", "beta/b.py", "tests/test_a.py"])
    before = copy.deepcopy(ledger)
    with pytest.raises(ValueError, match="group_limit.*minimum|minimum.*group_limit"):
        build_inventory_module_plan(ledger, group_limit=6)
    assert ledger == before


def test_output_is_deterministic_under_inventory_order_and_carries_no_old_prose() -> None:
    ledger = _ledger([
        "src/a/a.py", "src/b/b.py", "src/c/c.py", "src/d/d.py", "tests/test_x.py",
    ], group_limit=5)
    reversed_ledger = copy.deepcopy(ledger)
    for key in ("files", "symbols"):
        reversed_ledger["inventory"][key] = dict(
            reversed(list(reversed_ledger["inventory"][key].items()))
        )
    first = build_inventory_module_plan(ledger)
    second = build_inventory_module_plan(reversed_ledger)

    assert first == second
    assert len(first["groups"]) <= 5
    assert "SECRET_OLD" not in json.dumps(first)
    assert all(group["body"] == "" for group in first["groups"].values())
    assert all(group["extra"]["review_state"] == "candidate" for group in first["groups"].values())
    assert all("behavior" not in group["question_answered"].lower() for group in first["groups"].values())


@pytest.mark.parametrize("field", ["ledger_revision", "inventory_revision", "symbol_id", "symbol_path", "symbol_name", "file_path"])
def test_bad_inventory_identity_is_rejected(field: str) -> None:
    ledger = _ledger(["src/a.py"])
    sid = next(iter(ledger["inventory"]["symbols"]))
    if field == "ledger_revision":
        ledger["source_revision"] = "wrong"
    elif field == "inventory_revision":
        ledger["inventory"]["source_revision"] = "wrong"
    elif field == "symbol_id":
        ledger["inventory"]["symbols"][sid]["id"] = "wrong"
    elif field == "symbol_path":
        ledger["inventory"]["symbols"][sid]["path"] = "../outside.py"
    elif field == "symbol_name":
        del ledger["inventory"]["symbols"][sid]["name"]
    else:
        ledger["inventory"]["files"]["src/a.py"]["path"] = "wrong.py"
    with pytest.raises(ValueError):
        build_inventory_module_plan(ledger)


def test_missing_source_file_and_invalid_group_limit_are_rejected() -> None:
    ledger = _ledger(["src/a.py"])
    ledger["inventory"]["files"].clear()
    with pytest.raises(ValueError, match="source file"):
        build_inventory_module_plan(ledger)
    with pytest.raises(ValueError, match="group_limit"):
        build_inventory_module_plan(_ledger(["src/a.py"]), group_limit=True)
    with pytest.raises(ValueError, match="max_symbols_per_module"):
        build_inventory_module_plan(_ledger(["src/a.py"]), max_symbols_per_module=0)


def test_actual_frozen_inventory_is_accepted_by_renderer(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    for path, contents in {
        "src/app.py": "def run():\n    return 1\n",
        "src/test_app.py": "def test_run():\n    assert True\n",
        "examples/demo.py": "def show():\n    return 'example'\n",
        "docs/conf.py": "def configure():\n    return None\n",
    }.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")
    inventory = build_inventory(repo)
    ledger = {
        "source_revision": inventory.source_revision,
        "inventory": inventory.to_dict(),
        "documentation_policy": {"group_limit": 12},
    }

    plan = build_inventory_module_plan(ledger)
    assignments = _validate_plan(ledger, plan)
    assert set(assignments) == set(inventory.symbols)
    assert {record["path"] for sid, record in ledger["inventory"]["symbols"].items()
            if assignments[sid] == "module:src"} == {"src/app.py"}
    assert plan["stats"]["support_symbol_counts"]["test"] > 0
    assert plan["stats"]["support_symbol_counts"]["example"] > 0
    assert plan["stats"]["support_symbol_counts"]["docs"] > 0
