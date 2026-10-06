"""The module-first profile can freeze and render a new repository directly."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbe.cli import main
from cbe.render import render as render_run
from cbe.runner import RunnerError, analyze, refresh, resume
from cbe.store import LedgerStore, derived_status
from cbe.token_budget import RenderBudgetExceeded


def test_module_first_profile_skips_detail_tasks_and_publishes_candidate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    filler = "DATA = {\n" + "".join(f"    'item_{index}': {index},\n" for index in range(600)) + "}\n"
    (repo / "service.py").write_text(
        filler + "\ndef dispatch(value):\n    return value + 1\n", encoding="utf-8"
    )
    run = tmp_path / "run"
    ledger = analyze(repo, run, documentation_profile="module-first-v2")
    assert ledger["documentation_policy"]["version"] == "module-first-v2"
    assert ledger["tasks"] == {}
    assert ledger["packets"]["packets"] == []
    assert set(ledger["documentation_policy"]["symbols"]) == set(ledger["inventory"]["symbols"])
    plan = json.loads((run / "module_plan.json").read_text(encoding="utf-8"))
    assert plan["source_revision"] == ledger["source_revision"]
    assert plan["stats"]["symbol_count"] == len(ledger["inventory"]["symbols"])
    status = derived_status(LedgerStore(run).open())
    assert status["design_ready"]["module_plan_state"] == "structural_candidate"
    assert status["open_tasks"] == []
    assert main(["status", "--run-dir", str(run), "--json"]) == 0
    progress = json.loads(capsys.readouterr().out)["module_progress"]
    assert progress["implementation_module_count"] == 1
    assert progress["accepted_implementation_count"] == 0
    assert progress["pending_implementation_count"] == 1
    assert progress["render_state"] == "current"
    assert progress["published_tokens"] > 0

    assert main(["render", "--run-dir", str(run)]) == 0
    reader = Path(LedgerStore(run).open()["reader_output_dir"])
    manifest = json.loads((reader / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["symbol_catalogue_count"] == len(ledger["inventory"]["symbols"])
    assert manifest["accepted_group_explanation_count"] == 0
    assert manifest["token_budget"]["published_tokens"] <= manifest["token_budget"]["limit_tokens"]
    capsys.readouterr()
    symbol_id = next(iter(ledger["inventory"]["symbols"]))
    assert main(["resolve", "--run-dir", str(run), "--id", symbol_id]) == 0
    resolved = json.loads(capsys.readouterr().out)
    assert resolved["id"] == symbol_id
    page_path = resolved["absolute_path"].partition("#")[0]
    assert Path(page_path).exists()
    if "#" in resolved["target"]:
        assert resolved["target"].partition("#")[2]
    else:
        # Locator-only symbols resolve to their file page.
        assert Path(page_path).name.startswith("f-")
    resumed = resume(run, limit=0)
    assert resumed["render"]["accepted_group_explanation_count"] == 0
    assert json.loads((reader / "manifest.json").read_text())["documentation_policy_version"] == "module-first-v2-candidate"
    assert render_run(run)["documentation_policy_version"] == "module-first-v2-candidate"

    (run / "module_explanations.json").write_text(
        json.dumps({"source_revision": ledger["source_revision"], "modules": {}}),
        encoding="utf-8",
    )
    assert main(["status", "--run-dir", str(run), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["module_progress"]["render_state"] == "stale"
    assert render_run(run)["documentation_policy_version"] == "module-first-v2-candidate"
    assert main(["status", "--run-dir", str(run), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["module_progress"]["render_state"] == "current"

    ledger_before = (run / "semantic_ledger.json").read_bytes()
    plan_before = (run / "module_plan.json").read_bytes()
    with pytest.raises(RunnerError, match="requires a new frozen run"):
        refresh(run, repo)
    assert (run / "semantic_ledger.json").read_bytes() == ledger_before
    assert (run / "module_plan.json").read_bytes() == plan_before


def test_module_first_reports_tiny_navigation_overage_before_model_work(tmp_path: Path) -> None:
    repo = tmp_path / "tiny"
    repo.mkdir()
    (repo / "one.py").write_text("def one():\n    return 1\n", encoding="utf-8")
    run = tmp_path / "run"
    ledger = analyze(repo, run, documentation_profile="module-first-v2")
    assert ledger["documentation_policy"]["budget_mode"] == "report"
    assert ledger["documentation_policy"]["allocation_warning"]
    assert (run / "semantic_ledger.json").is_file()
    assert (repo / "docs/codebase/INDEX.md").is_file()


def test_same_revision_legacy_tree_can_seed_module_profile_without_old_prose(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = "DATA = {\n" + "".join(f"    'k{index}': {index},\n" for index in range(600)) + "}\n"
    (repo / "service.py").write_text(source + "\ndef execute(value):\n    return value + 1\n", encoding="utf-8")
    legacy_dir = tmp_path / "legacy"
    legacy = analyze(repo, legacy_dir, documentation_profile="legacy-v1")
    ids = list(legacy["inventory"]["symbols"])
    groups = {
        "root": {"group_id": "root", "parent_id": None, "children": ["area"], "member_ids": [], "title": "Root", "question_answered": "Old false behavior?", "body": "OLD_PROSE"},
        "area": {"group_id": "area", "parent_id": "root", "children": ["service"], "member_ids": [], "title": "Area", "question_answered": "Old false behavior?", "body": "OLD_PROSE"},
        "service": {"group_id": "service", "parent_id": "area", "children": [], "member_ids": ids, "title": "Service", "question_answered": "Old false behavior?", "body": "OLD_PROSE"},
    }
    LedgerStore(legacy_dir).mutate(lambda current: {**current, "groups": groups})
    new_dir = tmp_path / "new"
    new = analyze(repo, new_dir, documentation_profile="module-first-v2", legacy_run=legacy_dir)
    plan = json.loads((new_dir / "module_plan.json").read_text(encoding="utf-8"))
    assert new["tasks"] == {}
    assert set(plan["groups"]) == {"root", "area", "service"}
    assert plan["groups"]["service"]["member_ids"] == ids
    assert "OLD_PROSE" not in json.dumps(plan)
    assert "Old false behavior" not in json.dumps(plan)
    assert (Path(LedgerStore(new_dir).open()["reader_output_dir"]) / "INDEX.md").exists()
    with pytest.raises(RunnerError, match="only available"):
        analyze(repo, tmp_path / "invalid", documentation_profile="weighted-v1", legacy_run=legacy_dir)
