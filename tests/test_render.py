from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from cbe.inventory import build_inventory
from cbe.render import _broken_markdown_links, _compact_page, _write_weighted_pages, estimate_weighted_navigation_tokens, render, resolve_reader_target
from cbe.runner import analyze, claim_kind, import_result, query, work
from cbe.store import LedgerStore
from cbe.token_budget import (
    RenderBudgetExceeded,
    count_frozen_source_tokens,
    count_ledger_semantic_tokens,
    count_published_text_tokens,
    count_source_tokens,
    count_text_tokens,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def test_render_is_projection_with_real_detail_links(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copy(FIXTURES / "python_case.py", repo / "python_case.py")
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", limit=80)
    ledger = LedgerStore(run_dir).open()
    helper = next(
        sid for sid, sym in ledger["inventory"]["symbols"].items() if sym["name"] == "helper"
    )
    ids = tmp_path / "ids.json"
    ids.write_text(json.dumps([helper]), encoding="utf-8")
    claimed = claim_kind(run_dir, kind="group", input_ids_file=ids)
    plan = {
        "envelope": claimed["envelope"],
        "groups": [{
            "group_id": "root-sample",
            "children": [],
            "member_ids": [helper],
            "question_answered": "What does helper do?",
            "grouping_reason": "fixture",
            "entry_routes": [helper],
            "relations": [],
            "body": "See helper Detail.",
            "partial": True,
        }],
    }
    path = tmp_path / "g.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    imported = import_result(run_dir, claimed["task_id"], path)
    assert imported["state"] == "committed"
    manifest = render(run_dir)
    index = (run_dir / "render" / "INDEX.md").read_text(encoding="utf-8")
    assert "root-sample" in index or "What does helper do?" in index
    assert "python_case.py" in index
    assert index.count("\n") < 400
    group_page = (run_dir / "render" / "groups" / "root-sample.md").read_text(encoding="utf-8")
    assert "helper" in group_page
    assert "](../details/" in group_page
    looked = query(run_dir, helper)
    assert looked["type"] == "detail"
    assert "mock detail" in looked["record"]["behavior"]
    assert manifest["broken_links"] == []
    assert resolve_reader_target(LedgerStore(run_dir).open(), helper) is None


def test_replace_group_index_points_at_current_group(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copy(FIXTURES / "python_case.py", repo / "python_case.py")
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", limit=80)
    ledger = LedgerStore(run_dir).open()
    helper = next(
        sid for sid, sym in ledger["inventory"]["symbols"].items() if sym["name"] == "helper"
    )
    ids = tmp_path / "ids.json"
    ids.write_text(json.dumps([helper]), encoding="utf-8")
    claimed = claim_kind(run_dir, kind="group", input_ids_file=ids)
    plan = {
        "envelope": claimed["envelope"],
        "groups": [{
            "group_id": "root-sample",
            "children": [],
            "member_ids": [helper],
            "question_answered": "What does helper do?",
            "grouping_reason": "fixture",
            "entry_routes": [helper],
            "relations": [],
            "body": "See helper Detail.",
            "partial": True,
        }],
    }
    path = tmp_path / "g.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    imported = import_result(run_dir, claimed["task_id"], path)
    assert imported["state"] == "committed"
    claimed2 = claim_kind(run_dir, kind="group", input_ids_file=ids, replace_group_id="root-sample")
    plan2 = {
        "envelope": claimed2["envelope"],
        "groups": [{
            "group_id": "root-sample-v2",
            "children": [],
            "member_ids": [helper],
            "question_answered": "What does helper do now?",
            "grouping_reason": "replace",
            "entry_routes": [helper],
            "relations": [],
            "body": "Replacement group.",
            "partial": True,
        }],
    }
    path2 = tmp_path / "g2.json"
    path2.write_text(json.dumps(plan2), encoding="utf-8")
    imported2 = import_result(run_dir, claimed2["task_id"], path2)
    assert imported2["state"] == "committed"
    manifest = render(run_dir)
    index = (run_dir / "render" / "INDEX.md").read_text(encoding="utf-8")
    current_block = index.split("## Semantic groups", 1)[1].split("## Replaced groups", 1)[0]
    replaced_block = index.split("## Replaced groups", 1)[1]
    assert "root-sample-v2.md" in current_block
    assert "root-sample.md" not in current_block.replace("root-sample-v2.md", "")
    assert "What does helper do now?" in current_block
    assert "root-sample.md" in replaced_block
    assert "root-sample-v2.md" not in replaced_block
    assert "replaced by" in replaced_block
    assert (run_dir / "render" / "groups" / "root-sample.md").exists()
    assert (run_dir / "render" / "groups" / "root-sample-v2.md").exists()
    old_page = (run_dir / "render" / "groups" / "root-sample.md").read_text(encoding="utf-8")
    assert "replaced_by" in old_page
    looked = query(run_dir, "root-sample")
    assert looked["type"] == "group"
    assert (looked["record"].get("extra") or {}).get("replaced_by")
    current_page = (run_dir / "render" / "groups" / "root-sample-v2.md").read_text(encoding="utf-8")
    assert "](../details/" in current_page
    assert manifest["broken_links"] == []


def test_partial_details_keep_accepted_and_task_needs_repair(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copy(FIXTURES / "python_case.py", repo / "python_case.py")
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    store = LedgerStore(run_dir)
    ledger = store.open()
    task_id, task = next(iter(ledger["tasks"].items()))
    if len(task["input_ids"]) < 2:
        # pick a packet with multiple symbols if present
        for tid, raw in ledger["tasks"].items():
            if len(raw["input_ids"]) >= 2:
                task_id, task = tid, raw
                break
    ids = task["input_ids"]
    if len(ids) < 2:
        return
    from cbe.store import claim_task, submit_details
    import os

    def mutate(current: dict) -> dict:
        claim_task(current, task_id=task_id, owner="t", owner_pid=os.getpid(), lease_seconds=60)
        claimed = current["tasks"][task_id]
        submit_details(
            current,
            task_id=task_id,
            owner="t",
            generation=claimed["generation"],
            items=[{"symbol_id": ids[0], "behavior": "kept accepted item"}],
            packet=None,
            call_id=None,
        )
        return current

    store.mutate(mutate)
    ledger = store.open()
    assert ledger["tasks"][task_id]["state"] == "needs_repair"
    assert ids[0] in ledger["details"]
    assert ids[1] not in ledger["details"]
    assert any(item.get("code") == "missing_item" for item in ledger["tasks"][task_id]["residual"])


def test_index_parsefail_and_space_underscore_collision(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ok.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    (repo / "a b.py").write_text("def space():\n    return 1\n", encoding="utf-8")
    (repo / "a_b.py").write_text("def under():\n    return 1\n", encoding="utf-8")
    (repo / "bad.py").write_text("def oops(\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", limit=80)
    manifest = render(run_dir)
    files_dir = run_dir / "render" / "files"
    names = {path.name for path in files_dir.glob("*.md")}
    assert "a_20_b.py.md" in names
    assert "a_b.py.md" in names
    assert "bad.py.md" in names
    space_page = (files_dir / "a_20_b.py.md").read_text(encoding="utf-8")
    under_page = (files_dir / "a_b.py.md").read_text(encoding="utf-8")
    assert "space" in space_page
    assert "under" in under_page
    bad_page = (files_dir / "bad.py.md").read_text(encoding="utf-8")
    assert "parse failure" in bad_page.lower() or "Parse failure" in bad_page
    index = (run_dir / "render" / "INDEX.md").read_text(encoding="utf-8")
    assert "files/a_20_b.py.md" in index
    assert "files/a_b.py.md" in index
    assert "files/bad.py.md" in index
    assert (run_dir / "render" / "files" / "bad.py.md").exists()
    assert manifest["broken_links"] == []


def _weighted_run(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    # Enough real source content to exercise the half-source cap without
    # making the fixed navigation scaffolding alone impossible to publish.
    rules = "\n".join(f"    'rule_{i:03d}': {i * 7}," for i in range(280))
    source = (
        "RULES = {\n" + rules + "\n}\n\n"
        "def trivial(value):\n    return value + 1\n\n"
        "def important(value):\n"
        "    if value < 0:\n        raise ValueError('negative')\n"
        "    return RULES.get('rule_001', 0) + value\n"
        "\nclass Alpha:\n    def run(self):\n        return 1\n"
        "\nclass Beta:\n    def run(self):\n        return 2\n"
    )
    (repo / "service.py").write_text(source, encoding="utf-8")
    run_dir = tmp_path / "run"
    analyze(repo, run_dir)
    work(run_dir, model="mock", limit=80)
    store = LedgerStore(run_dir)
    ledger = store.open()
    symbols = ledger["inventory"]["symbols"]
    ids = {symbol["name"]: sid for sid, symbol in symbols.items()}

    def weighted(current: dict) -> dict:
        current["documentation_policy"] = {
            "version": "weighted-v1",
            "symbols": {
                sid: {"tier": ("deep" if sid == ids["important"] else "standard" if sid == ids["trivial"] else "brief")}
                for sid in symbols
            },
        }
        current["details"][ids["trivial"]]["behavior"] = "Adds one to the value."
        current["details"][ids["trivial"]]["effects"] = ["Returns a new integer"]
        current["details"][ids["important"]]["behavior"] = "Reads the rules and rejects negative input."
        current["details"][ids["important"]]["failures"] = ["Raises ValueError for negative input"]
        current["groups"] = {
            "root-service": {
                "group_id": "root-service",
                "question_answered": "How does the service process input?",
                "body": f"Start at [important]({ids['important']}) or [[{ids['trivial']}|trivial]].",
                "member_ids": [],
                "children": ["input-processing"],
                "entry_routes": [],
                "parent_id": None,
            },
            "input-processing": {
                "group_id": "input-processing",
                "question_answered": "How is input processed?",
                "body": "The important path checks input before using the rules.",
                "member_ids": [ids["important"], ids["trivial"]],
                "children": [],
                "entry_routes": [ids["important"]],
                "parent_id": "root-service",
            },
        }
        return current

    store.mutate(weighted)
    return repo, run_dir, ids


def test_weighted_render_preserves_symbol_navigation_without_brief_detail_pages(tmp_path: Path) -> None:
    _, run_dir, ids = _weighted_run(tmp_path)
    def fragment(current: dict) -> dict:
        current["details"]["fragment::not-canonical"] = {"behavior": "internal fragment only"}
        return current

    LedgerStore(run_dir).mutate(fragment)
    manifest = render(run_dir)
    rendered = run_dir / "render"
    ledger = LedgerStore(run_dir).open()
    targets = _write_weighted_pages(ledger, None)["symbol_targets"]
    assert set(targets) == set(ledger["inventory"]["symbols"])
    assert "symbol_targets" not in manifest
    assert "group_members" not in manifest
    assert "page_names" not in manifest
    assert targets[ids["trivial"]].startswith("files/")
    assert targets[ids["trivial"]].endswith("#trivial")
    assert targets[ids["important"]].startswith("details/")
    run_targets = [
        target for sid, target in targets.items()
        if LedgerStore(run_dir).open()["inventory"]["symbols"][sid]["name"] == "run"
    ]
    assert {target.rsplit("#", 1)[1] for target in run_targets} == {"run", "run-1"}
    assert not (rendered / "details" / Path(targets[ids["trivial"]]).name).exists()
    assert len(list((rendered / "details").glob("*.md"))) == 1
    assert "fragment::not-canonical" not in targets
    file_page = (rendered / targets[ids["trivial"]].split("#", 1)[0]).read_text(encoding="utf-8")
    assert "Adds one to the value." in file_page
    assert "Returns a new integer" in file_page
    assert "### trivial" in file_page
    detail_page = (rendered / targets[ids["important"]]).read_text(encoding="utf-8")
    assert "Raises ValueError" in detail_page
    assert "## Inputs / outputs" not in detail_page
    index = (rendered / "INDEX.md").read_text(encoding="utf-8")
    assert "[Source files](FILES.md)" in index
    assert "details/d-" in index
    assert "files/f-" in index
    assert "## Semantic groups" not in index
    assert "## File tree" not in index
    group_page = (rendered / _compact_page("groups", "input-processing")).read_text(encoding="utf-8")
    assert "important" in group_page
    assert ledger["groups"]["input-processing"]["member_ids"] == [ids["important"], ids["trivial"]]
    assert "service.py" in (rendered / "FILES.md").read_text(encoding="utf-8")
    assert manifest["broken_links"] == []
    budget = manifest["token_budget"]
    assert budget["tokenizer"] == "o200k_base"
    assert budget["source_tokens"] == count_frozen_source_tokens(LedgerStore(run_dir).open())
    assert budget["published_tokens"] == count_published_text_tokens(rendered)
    assert budget["published_tokens"] <= budget["limit_tokens"]
    assert abs(float(budget["ratio"]) - budget["published_tokens"] / budget["source_tokens"]) < 0.000001


def test_resolve_reader_target_matches_published_weighted_links(tmp_path: Path) -> None:
    _, run_dir, ids = _weighted_run(tmp_path)
    render(run_dir)
    ledger = LedgerStore(run_dir).open()
    rendered = run_dir / "render"
    symbols = ledger["inventory"]["symbols"]
    runs = sorted(
        (sid for sid, symbol in symbols.items() if symbol["name"] == "run"),
        key=lambda sid: (symbols[sid]["span"]["start"], sid),
    )
    assert [resolve_reader_target(ledger, sid).rsplit("#", 1)[1] for sid in runs] == ["run", "run-1"]
    for sid, expected_folder in (
        (runs[0], "files/"),
        (ids["trivial"], "files/"),
        (ids["important"], "details/"),
    ):
        target = resolve_reader_target(ledger, sid)
        assert target is not None and target.startswith(expected_folder)
        file_path, _, anchor = target.partition("#")
        page = rendered / file_path
        assert page.is_file()
        if anchor:
            assert f"### {symbols[sid]['name']}" in page.read_text(encoding="utf-8")
    child = resolve_reader_target(ledger, "input-processing")
    assert child == _compact_page("groups", "input-processing")
    assert f"]({child})" in (rendered / "INDEX.md").read_text(encoding="utf-8")
    child_page = (rendered / child).read_text(encoding="utf-8")
    assert f"](../{resolve_reader_target(ledger, ids['trivial'])})" in child_page
    assert f"](../{resolve_reader_target(ledger, ids['important'])})" in child_page
    assert resolve_reader_target(ledger, "service.py") == _compact_page("files", "service.py")
    assert resolve_reader_target(ledger, "missing::symbol") is None


def test_weighted_render_rejects_over_budget_without_replacing_live_pages(tmp_path: Path) -> None:
    _, run_dir, _ = _weighted_run(tmp_path)
    render(run_dir)
    store = LedgerStore(run_dir)
    before_revision = store.open()["render_revision"]
    before_index = (run_dir / "render" / "INDEX.md").read_bytes()

    def bloat(current: dict) -> dict:
        current["groups"]["input-processing"]["body"] = " ".join(
            f"unnecessary tutorial paragraph {i} contains repeated code narration" for i in range(1500)
        )
        return current

    store.mutate(bloat)
    with pytest.raises(RenderBudgetExceeded, match="staged render was not published"):
        render(run_dir)
    assert (run_dir / "render" / "INDEX.md").read_bytes() == before_index
    assert store.open()["render_revision"] == before_revision
    staged = json.loads((run_dir / ".render-staging" / "manifest.json").read_text(encoding="utf-8"))
    assert staged["token_budget"]["published_tokens"] > staged["token_budget"]["limit_tokens"]


def test_weighted_render_rejects_broken_links_and_changed_frozen_source(tmp_path: Path) -> None:
    repo, run_dir, _ = _weighted_run(tmp_path)
    render(run_dir)
    store = LedgerStore(run_dir)
    before_revision = store.open()["render_revision"]

    def broken(current: dict) -> dict:
        current["groups"]["input-processing"]["body"] = "See [missing](not-a-page.md)."
        return current

    store.mutate(broken)
    with pytest.raises(ValueError, match="broken links"):
        render(run_dir)
    assert store.open()["render_revision"] == before_revision

    def media(current: dict) -> dict:
        current["groups"]["input-processing"]["body"] = "![diagram](https://example.test/diagram.png)"
        return current

    store.mutate(media)
    with pytest.raises(ValueError, match="no accounted media tokens"):
        render(run_dir)
    assert store.open()["render_revision"] == before_revision

    def fixed(current: dict) -> dict:
        current["groups"]["input-processing"]["body"] = "The important path checks input."
        return current

    store.mutate(fixed)
    (repo / "service.py").write_text((repo / "service.py").read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="frozen source hash mismatch"):
        render(run_dir)
    assert store.open()["render_revision"] == before_revision


def test_weighted_visible_field_change_updates_render_fingerprint(tmp_path: Path) -> None:
    _, run_dir, ids = _weighted_run(tmp_path)
    render(run_dir)
    store = LedgerStore(run_dir)
    old_fingerprint = store.open()["render_revision"]

    def change(current: dict) -> dict:
        current["details"][ids["important"]]["effects"] = ["Reads RULES mapping"]
        return current

    store.mutate(change)
    render(run_dir)
    assert store.open()["render_revision"] != old_fingerprint


def test_weighted_preflight_and_per_file_source_accounting(tmp_path: Path) -> None:
    repo, run_dir, _ = _weighted_run(tmp_path)
    inventory = build_inventory(repo)
    expected = sum(
        count_text_tokens((repo / path).read_text(encoding="utf-8"))
        for path in inventory.files
    )
    assert count_source_tokens(inventory, repo) == expected
    preflight = estimate_weighted_navigation_tokens(LedgerStore(run_dir).open())
    assert preflight["source_tokens"] == expected
    assert preflight["navigation_tokens"] < preflight["limit_tokens"]
    manifest = render(run_dir)
    assert preflight["navigation_tokens"] < manifest["token_budget"]["published_tokens"]


def test_navigation_group_with_only_brief_members_has_source_entry(tmp_path: Path) -> None:
    _, run_dir, ids = _weighted_run(tmp_path)
    store = LedgerStore(run_dir)

    def navigation(current: dict) -> dict:
        group = current["groups"]["input-processing"]
        group["member_ids"] = [ids["run"]]
        group["entry_routes"] = []
        group["body"] = ""
        group["extra"] = {"presentation": "navigation"}
        return current

    store.mutate(navigation)
    manifest = render(run_dir)
    page = run_dir / "render" / _compact_page("groups", "input-processing")
    body = page.read_text(encoding="utf-8")
    assert "## Source entry" in body
    assert "service.py" in body
    assert "../files/f-" in body


def test_weighted_replaced_group_alias_does_not_publish_old_page(tmp_path: Path) -> None:
    _, run_dir, _ = _weighted_run(tmp_path)
    store = LedgerStore(run_dir)

    def replace(current: dict) -> dict:
        current["groups"]["archived-path"] = {
            "group_id": "archived-path",
            "question_answered": "Old path",
            "body": "Historical body should stay in the ledger only.",
            "member_ids": [],
            "children": [],
            "entry_routes": [],
            "parent_id": None,
            "extra": {"replaced_by": "input-processing"},
        }
        current["groups"]["root-service"]["body"] = "See [[archived-path]]."
        return current

    store.mutate(replace)
    manifest = render(run_dir)
    assert not (run_dir / "render" / _compact_page("groups", "archived-path")).exists()
    index = (run_dir / "render" / "INDEX.md").read_text(encoding="utf-8")
    assert _compact_page("groups", "input-processing") in index
    assert resolve_reader_target(store.open(), "archived-path") == _compact_page("groups", "input-processing")


def test_link_check_ignores_code_examples_but_rejects_actual_missing_link(tmp_path: Path) -> None:
    (tmp_path / "INDEX.md").write_text(
        "```md\n[example](missing-code.md)\n```\n"
        "`[inline](missing-inline.md)`\n"
        "[broken](missing-real.md)\n",
        encoding="utf-8",
    )
    broken = _broken_markdown_links(tmp_path, check_anchors=True)
    assert broken == ["INDEX.md -> missing-real.md"]


def test_ledger_semantic_tokens_count_queryable_fact_fields_exactly() -> None:
    evidence = {
        "behavior": "Coordinates requests.",
        "effects": ["Writes a result."],
        "failures": [],
        "unresolved": None,
    }
    ledger = {
        "details": {
            "canonical": {
                "behavior": "Returns the cached value.",
                "inputs_outputs": ["input key", "output value"],
                "effects": None,
                "failures": ["Raises on missing key."],
                "dependencies": [{"role": "lookup", "symbol_id": "cache.get"}],
                "unresolved": [],
                "nav_sentence": "A short duplicate of behavior.",
            },
            "fragment": {"behavior": "Historical source fragment.", "provenance": {"historical": True}},
        },
        "groups": {
            "current": {
                "body": "The module coordinates the request.",
                "extra": {"evidence_summary": evidence},
            },
            "replaced": {"body": "Old group prose remains queryable.", "extra": {"replaced_by": "current"}},
        },
    }
    expected_detail = sum(
        count_text_tokens(text) for text in (
            "Returns the cached value.",
            json.dumps(["input key", "output value"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            json.dumps(["Raises on missing key."], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            json.dumps([{"role": "lookup", "symbol_id": "cache.get"}], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            "Historical source fragment.",
        )
    )
    expected_body = count_text_tokens("The module coordinates the request.") + count_text_tokens("Old group prose remains queryable.")
    expected_evidence = count_text_tokens(json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    assert count_ledger_semantic_tokens(ledger) == {
        "ledger_semantic_tokens": expected_detail + expected_body + expected_evidence,
        "detail_tokens": expected_detail,
        "group_body_tokens": expected_body,
        "group_evidence_tokens": expected_evidence,
        "module_tokens": 0,
    }


def test_weighted_manifest_reports_unpublished_ledger_semantic_text(tmp_path: Path) -> None:
    _, run_dir, _ = _weighted_run(tmp_path)
    store = LedgerStore(run_dir)
    initial = render(run_dir)

    def hidden_summary(current: dict) -> dict:
        current["groups"]["input-processing"].setdefault("extra", {})["evidence_summary"] = {
            "behavior": "HIDDEN_LEDGER_ONLY behavior fact.",
            "effects": ["HIDDEN_LEDGER_ONLY state effect."],
            "failures": [],
            "unresolved": None,
        }
        return current

    store.mutate(hidden_summary)
    manifest = render(run_dir)
    assert manifest["ledger_semantic_tokens"] > initial["ledger_semantic_tokens"]
    assert manifest["ledger_semantic_tokens"] == count_ledger_semantic_tokens(store.open())["ledger_semantic_tokens"]
    assert sum(manifest["ledger_semantic_breakdown"].values()) == manifest["ledger_semantic_tokens"]
    assert "do not add" in manifest["ledger_semantic_note"]
    assert manifest["token_budget"]["published_tokens"] == count_published_text_tokens(run_dir / "render")
    assert "HIDDEN_LEDGER_ONLY" not in "\n".join(
        path.read_text(encoding="utf-8") for path in (run_dir / "render").rglob("*.md")
    )


@pytest.mark.parametrize("stale_group", ["root-service", "input-processing"])
@pytest.mark.parametrize("stale_field", ["stale", "body_stale"])
def test_weighted_stale_group_body_is_withheld_from_live_render(
    tmp_path: Path, stale_group: str, stale_field: str
) -> None:
    _, run_dir, _ = _weighted_run(tmp_path)
    store = LedgerStore(run_dir)

    def claims(current: dict) -> dict:
        current["groups"]["root-service"]["body"] = "OLD_ROOT_ASSERTION"
        current["groups"]["input-processing"]["body"] = "OLD_CHILD_ASSERTION"
        return current

    store.mutate(claims)
    render(run_dir)
    assert "OLD_ROOT_ASSERTION" in (run_dir / "render" / "INDEX.md").read_text(encoding="utf-8")
    assert "OLD_CHILD_ASSERTION" in (
        run_dir / "render" / _compact_page("groups", "input-processing")
    ).read_text(encoding="utf-8")

    def stale(current: dict) -> dict:
        current["groups"][stale_group].setdefault("extra", {})[stale_field] = True
        return current

    store.mutate(stale)
    manifest = render(run_dir)
    pages = "\n".join(path.read_text(encoding="utf-8") for path in (run_dir / "render").rglob("*.md"))
    assert "OLD_ROOT_ASSERTION" not in pages
    assert "Pending refresh" in pages
    assert stale_group in manifest["pending_group_ids"]
    if stale_group == "input-processing":
        assert "OLD_CHILD_ASSERTION" not in pages
        assert "root-service" in manifest["pending_group_ids"]
    else:
        assert "OLD_CHILD_ASSERTION" in pages
    assert manifest["pending_group_count"] == len(manifest["pending_group_ids"])


def test_legacy_stale_group_keeps_original_projection(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copy(FIXTURES / "python_case.py", repo / "python_case.py")
    run_dir = tmp_path / "run"
    analyze(repo, run_dir, documentation_profile="legacy-v1")
    work(run_dir, model="mock", limit=80)
    store = LedgerStore(run_dir)
    symbols = store.open()["inventory"]["symbols"]
    first = next(iter(symbols))

    def group(current: dict) -> dict:
        current["details"][first]["behavior"] = "LEGACY_DETAIL_CLAIM"
        current["details"][first].setdefault("provenance", {})["stale"] = True
        current["groups"] = {
            "legacy-root": {
                "group_id": "legacy-root",
                "question_answered": "Legacy question",
                "body": "LEGACY_OLD_BODY",
                "children": [],
                "member_ids": [first],
                "entry_routes": [],
                "parent_id": None,
                "extra": {"stale": True, "body_stale": True},
            }
        }
        return current

    store.mutate(group)
    render(run_dir)
    assert "LEGACY_OLD_BODY" in (run_dir / "render" / "INDEX.md").read_text(encoding="utf-8")
    assert "LEGACY_OLD_BODY" in (run_dir / "render" / "groups" / "legacy-root.md").read_text(encoding="utf-8")
    assert any(
        "LEGACY_DETAIL_CLAIM" in page.read_text(encoding="utf-8")
        for page in (run_dir / "render" / "details").glob("*.md")
    )


@pytest.mark.parametrize(
    ("symbol_name", "tier", "provenance_flag"),
    [
        ("run", "brief", "stale"),
        ("trivial", "standard", "historical"),
        ("important", "deep", "incomplete"),
    ],
)
def test_weighted_unverified_detail_prose_is_withheld_but_source_remains_navigable(
    tmp_path: Path, symbol_name: str, tier: str, provenance_flag: str
) -> None:
    _, run_dir, ids = _weighted_run(tmp_path)
    sid = ids[symbol_name]
    store = LedgerStore(run_dir)

    def invalidate(current: dict) -> dict:
        assert current["documentation_policy"]["symbols"][sid]["tier"] == tier
        detail = current["details"][sid]
        detail["behavior"] = "OLD_WRONG_BEHAVIOR"
        detail["effects"] = ["OLD_WRONG_EFFECT"]
        detail["failures"] = ["OLD_WRONG_FAILURE"]
        detail["unresolved"] = ["OLD_WRONG_UNRESOLVED"]
        detail["inputs_outputs"] = ["OLD_WRONG_INPUT"]
        detail["dependencies"] = ["OLD_WRONG_DEPENDENCY"]
        detail.setdefault("provenance", {})[provenance_flag] = True
        child = current["groups"]["input-processing"]
        if sid not in child["member_ids"]:
            child["member_ids"].append(sid)
        child["body"] = "OLD_DERIVED_GROUP_CLAIM"
        current["groups"]["root-service"]["body"] = "OLD_DERIVED_ROOT_CLAIM"
        return current

    store.mutate(invalidate)
    manifest = render(run_dir)
    rendered = run_dir / "render"
    markdown = "\n".join(page.read_text(encoding="utf-8") for page in rendered.rglob("*.md"))
    assert "OLD_WRONG_" not in markdown
    assert "OLD_DERIVED_" not in markdown
    assert "Pending verification" in markdown
    assert sid in manifest["pending_detail_ids"]
    assert manifest["pending_detail_count"] >= 1
    assert set(manifest["pending_group_ids"]) == {"root-service", "input-processing"}
    assert manifest["broken_links"] == []
    file_page = next((rendered / "files").glob("*.md")).read_text(encoding="utf-8")
    if tier == "deep":
        detail_page = rendered / _compact_page("details", sid)
        assert detail_page.exists()
        assert "Pending verification" in detail_page.read_text(encoding="utf-8")
        assert detail_page.name in file_page
    else:
        assert f"### {symbol_name}" in file_page
        assert "Pending verification" in file_page


def test_weighted_html_media_embeds_are_rejected(tmp_path: Path) -> None:
    _, run_dir, _ = _weighted_run(tmp_path)
    store = LedgerStore(run_dir)
    render(run_dir)
    revision = store.open()["render_revision"]
    media = [
        '<img src="diagram.png">',
        '<picture><source srcset="diagram.png"></picture>',
        '<video src="demo.mp4"></video>',
        '<svg><circle r="4" /></svg>',
    ]
    for snippet in media:
        def embed(current: dict) -> dict:
            current["groups"]["input-processing"]["body"] = snippet
            return current

        store.mutate(embed)
        with pytest.raises(ValueError, match="no accounted media tokens"):
            render(run_dir)
        assert store.open()["render_revision"] == revision

    def code_example(current: dict) -> dict:
        current["groups"]["input-processing"]["body"] = '```html\n<img src="example.png">\n```'
        return current

    store.mutate(code_example)
    assert render(run_dir)["broken_links"] == []
@pytest.mark.parametrize("snippet", [
    '<img src="diagram.png">', '<IMG SRC="diagram.png" />',
    '<object data="diagram.svg"></object>', '<svg viewBox="0 0 2 2"></svg>',
    '<embed\n src="diagram.svg">', '<iframe src="demo.html"></iframe>',
    '<audio src="demo.wav"></audio>', '<video src="demo.mp4"></video>',
    '<picture><source srcset="diagram.png"></picture>', '<canvas></canvas>',
    '<img title="a > b" src="diagram.png">', '![diagram](diagram.png)',
    '![a <span>label</span>](diagram.png)',
    '![outer [inner] tail](https://example.test/diagram.png)',
    '![outer ![inner](inner.png) tail](outer.png)',
    '![label][media]\n\n[media]: diagram.png',
    '![label][]\n\n[label]: diagram.png',
    '![label]\n\n[label]: diagram.png',
    '![label](https://example.test/path_(part).png "title")',
    r'\`![chart](diagram.png)`',
])
def test_media_check_keeps_real_complete_embeds(tmp_path, snippet):
    from cbe.render import _unaccounted_media
    (tmp_path / "page.md").write_text(snippet)
    assert _unaccounted_media(tmp_path) == ["page.md -> media embed has no accounted media tokens"]


@pytest.mark.parametrize("snippet", [
    'res2 = e1 < object(); statement runs only to observe behavior',
    'x < object() and y > 0', 'x < img_count and y > 0', '<object',
    '< object()>', '<object()>', '<imglike src="example.png">',
    '`<img src="example.png">`', '```html\n<object data="example.svg">\n```',
    '<!-- <IMG src="example.png"> -->',
    '<!--\n<object data="example.svg">\n![diagram](example.png)\n-->',
    '    ![chart](diagram.png)\n    <img src="diagram.png">',
    r'\![outer [inner] tail](https://example.test/diagram.png)',
])
def test_media_check_ignores_comparisons_code_and_comments(tmp_path, snippet):
    from cbe.render import _unaccounted_media
    (tmp_path / "page.md").write_text(snippet)
    assert _unaccounted_media(tmp_path) == []


@pytest.mark.parametrize("slashes", range(5))
@pytest.mark.parametrize("markup", ['<object data="demo.svg">literal text</object>', '![chart](diagram.png)'])
def test_media_check_commonmark_opening_escape_parity(tmp_path, slashes, markup):
    from cbe.render import _unaccounted_media
    (tmp_path / "page.md").write_text("Example: " + "\\" * slashes + markup)
    assert bool(_unaccounted_media(tmp_path)) == (slashes % 2 == 0)


@pytest.mark.parametrize("slashes", range(5))
def test_media_check_commonmark_alt_closing_escape_parity(tmp_path, slashes):
    from cbe.render import _unaccounted_media
    (tmp_path / "page.md").write_text("![chart" + "\\" * slashes + "](diagram.png)")
    assert bool(_unaccounted_media(tmp_path)) == (slashes % 2 == 0)


def test_escaped_comment_open_does_not_hide_true_media(tmp_path):
    from cbe.render import _unaccounted_media
    (tmp_path / "page.md").write_text(r'\<!-- <img src="diagram.png"> -->')
    assert _unaccounted_media(tmp_path)


def test_manifest_self_count_cycle_uses_exact_json_whitespace(tmp_path, monkeypatch):
    import json
    from cbe import render
    from cbe.token_budget import count_published_text_tokens
    manifest = {"token_budget": {"published_tokens": 0, "ratio": "0.000000",
                                 "query_only_tokens": 0, "effective_document_tokens": 0,
                                 "effective_ratio": "0.000000", "target_status": "within_target"}}
    observed = []
    def counted(path):
        value = count_published_text_tokens(path)
        observed.append(value)
        return value
    monkeypatch.setattr(render, "count_published_text_tokens", counted)
    actual = render._write_counted_manifest(tmp_path, manifest, 80)
    assert observed[:4] == [43, 46, 44, 46]
    text = (tmp_path / "manifest.json").read_text()
    assert "\t\n" in text
    budget = json.loads(text)["token_budget"]
    assert actual == budget["published_tokens"] == count_published_text_tokens(tmp_path)
    assert budget["effective_document_tokens"] == actual
    assert budget["ratio"] == budget["effective_ratio"] == f"{actual / 80:.6f}"
    assert budget["target_status"] == "above_guidance"


def test_convergent_manifest_serialization_is_unchanged(tmp_path):
    import json
    from cbe.render import _write_counted_manifest
    manifest = {"token_budget": {"published_tokens": 0, "ratio": "0.000000"}}
    actual = _write_counted_manifest(tmp_path, manifest, 1000)
    text = (tmp_path / "manifest.json").read_text()
    assert text == json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n"
    assert manifest["token_budget"]["ratio"] == f"{actual / 1000:.6f}"
