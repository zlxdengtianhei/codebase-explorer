"""Host-agent driven generation: plan, lease, submit, resume, render, verify, cost."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cbe import usage
from cbe import cli, host_run, prompts
from cbe.docs import find


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src" / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "pkg" / "jobs.py").write_text(
        "import typing\n\n@typing.overload\ndef reserve_run(value: int) -> int: ...\n"
        "def reserve_run(value):\n    if value < 0:\n        raise ValueError('negative')\n    return value\n",
        encoding="utf-8")
    (repo / "src" / "pkg" / "cli.py").write_text(
        "from pkg.jobs import reserve_run\n\ndef main(argv):\n    return reserve_run(len(argv))\n",
        encoding="utf-8")
    (repo / "tests" / "test_jobs.py").write_text(
        "from pkg.jobs import reserve_run\n\ndef test_reserve():\n    assert reserve_run(1) == 1\n",
        encoding="utf-8")
    return repo


def _detail_from_prompt(prompt: str) -> dict:
    inv = json.loads(prompt.split("INVENTORY (this batch, authoritative ids):\n", 1)[1]
                     .split("\n\n", 1)[0])
    units, dispositions = [], {}
    for file_row in inv:
        for symbol in file_row["symbols"]:
            units.append({"id": symbol["id"], "kind": symbol["kind"],
                          "explain": f"Unit {symbol['name']} does its job.",
                          "extras": [], "relations": [], "uncertainties": []})
            dispositions[symbol["id"]] = {"how": "unit", "unit": symbol["id"],
                                           "reason": "real behavior"}
    return {"units": units, "dispositions": dispositions, "batch_notes": "batch ok"}


def _tree_from_prompt(prompt: str) -> dict:
    units = json.loads(prompt.split("UNITS:\n", 1)[1])
    ids = [unit["id"] for unit in units]
    return {"nodes": [{"id": "root", "parent": None, "title": "Root",
                       "capability": "All units of the repository under one semantic root.",
                       "summary": "Start here.", "unit_ids": ids}], "depends_on": []}


def _answer(task: dict, prompt: str, *, decision: str = "accepted") -> dict:
    """Play the subagent: answer from the instruction file alone."""
    kind = task["kind"]
    if kind == "names":
        rows = json.loads(prompt.split("Modules:\n", 1)[1])
        return {"names": [{"module": row["module"], "title": f"Area {row['module']}"} for row in rows]}
    if kind in {"module", "repair"}:
        return _detail_from_prompt(prompt)
    if kind == "tree":
        return _tree_from_prompt(prompt)
    if kind == "review":
        return {"decision": decision, "issues": ["the negative check is missing"] if decision != "accepted" else []}
    return {"overview": "A tiny job reservation package.", "maintenance_navigation": "Open the root node."}


def _drive(run_dir: Path, *, decision: str = "accepted") -> list[str]:
    handed: list[str] = []
    for _ in range(50):
        batch = host_run.next_tasks(run_dir)
        if not batch["tasks"]:
            break
        for item in batch["tasks"]:
            prompt = Path(item["prompt_file"]).read_text(encoding="utf-8")
            assert item["output_file"] in prompt and item["dispatch_message"].startswith("Codebase Explorer task")
            task = {"kind": item["kind"]}
            Path(item["output_file"]).write_text(json.dumps(_answer(task, prompt, decision=decision)),
                                                 encoding="utf-8")
            result = host_run.submit(run_dir, item["task"], usage={"total_tokens": 1000, "source": "test"})
            assert result["accepted"], result
            handed.append(item["task"])
    return handed


def test_full_host_run_renders_verifies_and_is_queryable(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    planned = host_run.plan(repo, review="sample", jobs=2, host="test")
    run_dir = Path(planned["run_dir"])
    assert planned["source_files"] == 3 and planned["modules"] >= 2
    assert (repo / ".codebase-analysis" / "host-latest").read_text().strip() == str(run_dir)

    first = host_run.next_tasks(run_dir)
    assert [item["task"] for item in first["tasks"]] == ["names"]  # modules wait for titles
    host_run.release(run_dir)
    handed = _drive(run_dir)
    assert handed[0] == "names" and handed[-1] == "system"
    assert sum(task.startswith("review_") for task in handed) == 1

    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"], state["verify"]
    index = (run_dir / "docs" / "INDEX.md").read_text()
    assert "## Responsibility tree" in index and "](nodes/" in index and str(tmp_path) not in index
    assert find(run_dir, "reserve_run")
    assert host_run.verify(run_dir)["ok"]


def test_concurrency_limit_and_schema_retry_then_failure(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=1)["run_dir"])
    names = host_run.next_tasks(run_dir)["tasks"][0]
    prompt = Path(names["prompt_file"]).read_text()
    Path(names["output_file"]).write_text(json.dumps(_answer({"kind": "names"}, prompt)))
    host_run.submit(run_dir, "names")

    batch = host_run.next_tasks(run_dir)
    assert len(batch["tasks"]) == 1 and host_run.next_tasks(run_dir)["tasks"] == []  # jobs=1
    item = batch["tasks"][0]
    Path(item["output_file"]).write_text('{"summary": ""}')
    rejected = host_run.submit(run_dir, item["task"])
    assert not rejected["accepted"] and "schema_error" in rejected["error"] and rejected["task_status"] == "pending"

    again = host_run.next_tasks(run_dir)["tasks"][0]
    assert again["task"] == item["task"]
    assert "previous attempt failed validation" in Path(again["prompt_file"]).read_text()
    second = host_run.submit(run_dir, item["task"])  # no file written: counts as the second attempt
    assert not second["accepted"] and second["task_status"] == "failed" and second["failed"]
    with pytest.raises(host_run.HostRunError):
        host_run.submit(run_dir, item["task"])
    assert host_run.retry(run_dir, item["task"])["counts"]["pending"] >= 1
    third = host_run.next_tasks(run_dir)["tasks"][0]
    Path(third["output_file"]).write_text(json.dumps(_answer({"kind": "module"}, Path(third["prompt_file"]).read_text())))
    accepted = host_run.submit(run_dir, item["task"])
    assert accepted["accepted"] and accepted["attempts"] == 3
    assert (run_dir / "host" / "raw" / f"{item['task']}.attempt-3.txt").is_file()


def test_resume_adopts_finished_results_and_releases_lost_leases(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=4)["run_dir"])
    names = host_run.next_tasks(run_dir)["tasks"][0]
    Path(names["output_file"]).write_text(
        json.dumps(_answer({"kind": "names"}, Path(names["prompt_file"]).read_text())))
    host_run.submit(run_dir, "names")
    batch = host_run.next_tasks(run_dir)["tasks"]
    assert len(batch) >= 2
    done, lost = batch[0], batch[1:]
    Path(done["output_file"]).write_text(
        json.dumps(_answer({"kind": "module"}, Path(done["prompt_file"]).read_text())))
    # The host crashed here: one subagent wrote its file, the others never finished.
    resumed = host_run.resume(run_dir, owner="codex")
    assert [row["task"] for row in resumed["submitted"]] == [done["task"]]
    assert sorted(resumed["released"]) == sorted(item["task"] for item in lost)
    assert resumed["leased"] == []
    _drive(run_dir)
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["host"] == "codex" and state["verify"]["ok"]


def test_review_all_queues_repairs_before_the_overview(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="all", jobs=8)["run_dir"])
    handed = _drive(run_dir, decision="needs_repair")
    modules = json.loads((run_dir / "host" / "state.json").read_text())["modules"]
    assert sum(task.startswith("review_") for task in handed) == len(modules)
    assert sum(task.startswith("repair_") for task in handed) == len(modules)
    assert handed[-1] == "system"
    repair_prompt = (run_dir / "host" / "tasks" / "repair_1.md").read_text()
    assert "the negative check is missing" in repair_prompt


def test_source_drift_blocks_dispatch_and_fails_verify(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none")["run_dir"])
    names = host_run.next_tasks(run_dir)["tasks"][0]
    Path(names["output_file"]).write_text(
        json.dumps(_answer({"kind": "names"}, Path(names["prompt_file"]).read_text())))
    host_run.submit(run_dir, "names")
    (repo / "src" / "pkg" / "jobs.py").write_text("def changed():\n    pass\n", encoding="utf-8")
    with pytest.raises(host_run.HostRunError, match="missing or changed"):
        host_run.next_tasks(run_dir)
    report = host_run.verify(run_dir)
    assert not report["ok"]
    assert any(row["check"] == "sources_unchanged" and not row["ok"] for row in report["checks"])


def test_host_dispatch_refuses_missing_or_unreadable_source(tmp_path: Path) -> None:
    """Host tasks list paths: every listed path must exist, be readable, and match the plan."""
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none")["run_dir"])
    names = host_run.next_tasks(run_dir)["tasks"][0]
    Path(names["output_file"]).write_text(
        json.dumps(_answer({"kind": "names"}, Path(names["prompt_file"]).read_text())))
    host_run.submit(run_dir, "names")

    (repo / "src" / "pkg" / "cli.py").unlink()
    with pytest.raises(host_run.HostRunError, match="missing or changed.*cli.py"):
        host_run.next_tasks(run_dir)

    (repo / "src" / "pkg" / "cli.py").write_text(
        "from pkg.jobs import reserve_run\n\ndef main(argv):\n    return reserve_run(len(argv))\n",
        encoding="utf-8")
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        os.chmod(repo / "src" / "pkg" / "cli.py", 0o000)
        try:
            with pytest.raises(host_run.HostRunError, match="missing or changed.*cli.py"):
                host_run.next_tasks(run_dir)
        finally:
            os.chmod(repo / "src" / "pkg" / "cli.py", 0o644)


def test_import_claude_and_codex_usage_and_cost_report(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none")["run_dir"])
    _drive(run_dir)
    tag = json.loads((run_dir / "host" / "state.json").read_text())["run_tag"]

    estimate = usage.cost(run_dir, model="claude-sonnet-5-5")
    assert estimate["basis"] == "estimate" and "ESTIMATES" in estimate["statement"]
    assert estimate["totals"]["usd"] > 0 and (run_dir / "host" / "COST.md").is_file()

    session = tmp_path / "claude" / "proj" / "session" / "subagents"
    session.mkdir(parents=True)
    (session / "agent-a1.meta.json").write_text(json.dumps({"description": f"cbe {tag} names"}))
    lines = [
        {"message": {"id": "m1", "model": "claude-sonnet-5-5", "usage": {
            "input_tokens": 3, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 0, "output_tokens": 1}}},
        {"message": {"id": "m1", "model": "claude-sonnet-5-5", "usage": {
            "input_tokens": 3, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 0, "output_tokens": 40}}},
        {"message": {"id": "m2", "model": "claude-sonnet-5-5", "usage": {
            "input_tokens": 2, "cache_creation_input_tokens": 10, "cache_read_input_tokens": 100, "output_tokens": 60}}},
    ]
    (session / "agent-a1.jsonl").write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    imported = usage.import_usage(run_dir, "claude-code", tmp_path / "claude")
    assert imported["tasks_with_exact_usage"] == 1

    rollouts = tmp_path / "codex" / "2026" / "10" / "06"
    rollouts.mkdir(parents=True)
    events = [
        {"type": "session_meta", "payload": {"source": {"subagent": {"thread_spawn": {
            "parent_thread_id": "p", "agent_path": f"/root/cbe_{tag}_system"}}}}},
        {"type": "turn_context", "payload": {"model": "gpt-6.1-sol"}},
        {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {
            "input_tokens": 900, "cached_input_tokens": 600, "output_tokens": 50, "reasoning_output_tokens": 20}}}},
    ]
    (rollouts / "rollout-x.jsonl").write_text("\n".join(json.dumps(event) for event in events) + "\n")
    (rollouts / "rollout-main.jsonl").write_text(json.dumps({"type": "session_meta", "payload": {"source": "cli"}}) + "\n")
    assert usage.import_usage(run_dir, "codex", tmp_path / "codex")["tasks_with_exact_usage"] == 1

    report = usage.cost(run_dir, model="claude-sonnet-5-5")
    rows = {row["task"]: row for row in report["tasks"]}
    assert report["basis"] == "mixed"
    assert rows["names"]["basis"] == "exact"
    assert rows["names"]["cache_write_tokens"] == 110 and rows["names"]["output_tokens"] == 100
    assert rows["names"]["harness_reported_total_tokens"] == 1000
    assert rows["system"]["cache_read_tokens"] == 600 and rows["system"]["input_tokens"] == 300
    assert rows["system"]["models"] == ["gpt-6.1-sol"]
    assert rows["names"]["usd_api_equivalent"] > 0
    assert rows["system"]["usd_api_equivalent"] is None
    assert report["totals"]["usd"] is None
    assert report["estimate_usd"] is None
    assert "dollar totals are unknown" in report["statement"]
    assert "Price equivalent: unknown" in (run_dir / "host" / "COST.md").read_text()
    assert json.loads((run_dir / "host" / "cost.json").read_text())["totals"]["usd"] is None

    supplied = usage.cost(run_dir, price=(1.0, 2.0, 3.0, 4.0))
    priced = {row["task"]: row for row in supplied["tasks"]}
    assert priced["system"]["usd_api_equivalent"] == 0.0028
    assert supplied["totals"]["usd"] > 0
    assert supplied["price_basis"] == ["price given on the command line"]


def test_cost_unknown_estimates_and_explicit_free_rates(tmp_path: Path) -> None:
    run_dir = Path(host_run.plan(_repo(tmp_path), tmp_path / "run")["run_dir"])
    _drive(run_dir)
    unknown = usage.cost(run_dir, model="gpt-6-astra")
    assert unknown["basis"] == "estimate"
    assert unknown["totals"]["usd"] is None and unknown["estimate_usd"] is None
    free = usage.cost(run_dir, model="gpt-6-astra", price=(0.0, 0.0, 0.0, 0.0))
    assert free["totals"]["usd"] == 0.0 and free["estimate_usd"] == 0.0
    assert "Price equivalent: $0.00" in (run_dir / "host" / "COST.md").read_text()


@pytest.mark.parametrize("rates", ["nan,2,3,4", "1,inf,3,4", "-1,2,3,4"])
def test_cli_cost_rejects_invalid_rates(tmp_path: Path, capsys, rates: str) -> None:
    run_dir = Path(host_run.plan(_repo(tmp_path), tmp_path / "run")["run_dir"])
    assert cli.main(["host", "cost", "--run-dir", str(run_dir), "--price=" + rates]) == 2
    output = capsys.readouterr()
    assert "finite, nonnegative" in output.out + output.err


def test_cli_host_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path)
    assert cli.main(["host", "plan", str(repo), "--review", "none", "--jobs", "3", "--host", "claude-code"]) == 0
    planned = json.loads(capsys.readouterr().out)
    assert cli.main(["host", "status", "--repo", str(repo)]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["run_dir"] == planned["run_dir"] and status["ready"] == 1
    assert cli.main(["host", "next", "--run-dir", planned["run_dir"]]) == 0
    item = json.loads(capsys.readouterr().out)["tasks"][0]
    Path(item["output_file"]).write_text(json.dumps(_answer({"kind": "names"}, Path(item["prompt_file"]).read_text())))
    assert cli.main(["host", "submit", "--run-dir", planned["run_dir"], "--task", "names",
                     "--usage-tokens", "52859", "--tool-uses", "3", "--usage-source", "claude-code agent result"]) == 0
    assert json.loads(capsys.readouterr().out)["accepted"]
    assert cli.main(["host", "submit", "--run-dir", planned["run_dir"], "--task", "nope"]) == 2
    assert cli.main(["host", "cost", "--run-dir", planned["run_dir"], "--price", "1,2"]) == 2
    assert cli.main(["host", "plan", str(repo), "--run-dir", planned["run_dir"]]) == 2
    assert os.path.isdir(planned["run_dir"])


def _answer_task(run_dir: Path, item: dict, value) -> dict:
    text = value if isinstance(value, str) else json.dumps(value)
    Path(item["output_file"]).write_text(text, encoding="utf-8")
    return host_run.submit(run_dir, item["task"])


def _good(item: dict, run_dir: Path) -> dict:
    return _answer({"kind": item["kind"]}, Path(item["prompt_file"]).read_text())


def test_second_invalid_detail_answer_is_normalized_flagged_and_rendered(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=8)["run_dir"])
    names = host_run.next_tasks(run_dir)["tasks"][0]
    _answer_task(run_dir, names, _good(names, run_dir))
    batch = host_run.next_tasks(run_dir)["tasks"]
    target = batch[0]
    for item in batch[1:]:
        _answer_task(run_dir, item, _good(item, run_dir))
    bad = _good(target, run_dir)
    bad["units"][0]["kind"] = "not-a-kind"
    dropped = next(iter(bad["dispositions"]))
    bad["dispositions"].pop(dropped)
    first = _answer_task(run_dir, target, bad)
    assert not first["accepted"] and first["task_status"] == "pending"
    assert "kind" in first["error"].lower() or "disposition" in first["error"].lower()
    again = host_run.next_tasks(run_dir)["tasks"][0]
    assert again["task"] == target["task"]
    second = _answer_task(run_dir, again, bad)
    assert second["accepted"] and second["normalized"]
    assert any("module_region" in flag for flag in second["flags"])
    accepted = json.loads((run_dir / "host" / "accepted" / f"{target['task']}.json").read_text())
    assert all(unit["kind"] in {"class", "function", "method", "group", "module_region"}
               for unit in accepted["units"])
    assert dropped in accepted["dispositions"] and accepted["dispositions"][dropped]["how"] == "index_only"
    tree_item = host_run.next_tasks(run_dir)["tasks"][0]
    assert tree_item["kind"] == "tree"
    _answer_task(run_dir, tree_item, _good(tree_item, run_dir))
    system = host_run.next_tasks(run_dir)["tasks"][0]
    assert system["kind"] == "system"
    nav = "Open the root node for reservations. " * 200  # far above the scaled cap
    _answer_task(run_dir, system, {"overview": "A tiny package.", "maintenance_navigation": nav})
    _answer_task(run_dir, host_run.next_tasks(run_dir)["tasks"][0],
                 {"overview": "A tiny package.", "maintenance_navigation": nav})
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"]
    index = (run_dir / "docs" / "INDEX.md").read_text()
    assert "## Generation notes" in index and "maintenance_navigation truncated" in index
    assert "Normalized after a second invalid answer" in index
    log = (run_dir / "progress.log").read_text()
    for word in ("plan ", "claim ", "reject ", "normalize ", "accept ", "render "):
        assert word in log, word
    assert "| module_1 |" in (run_dir / "STATUS.md").read_text()


def test_unusable_module_renders_partial_and_resume_finishes_it(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="sample", jobs=8)["run_dir"])
    names = host_run.next_tasks(run_dir)["tasks"][0]
    _answer_task(run_dir, names, _good(names, run_dir))
    batch = host_run.next_tasks(run_dir)["tasks"]
    broken = batch[-1]
    for item in batch[:-1]:
        _answer_task(run_dir, item, _good(item, run_dir))
    for _ in range(2):
        item = host_run.next_tasks(run_dir, limit=1)["tasks"][0] if _ else broken
        assert item["task"] == broken["task"]
        result = _answer_task(run_dir, item, "the model wrote prose instead of JSON")
    assert result["task_status"] == "failed"
    _drive(run_dir)  # the review of a finished module and the overview still run
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "partial" and state["tasks"]["system"]["status"] == "done"
    assert state["tasks"]["system"]["covered"] and broken["task"] not in [f"module_{n + 1}" for n in state["tasks"]["system"]["covered"]]
    checks = {row["check"]: row["ok"] for row in state["verify"]["checks"]}
    assert not checks["all_tasks_done"] and checks["each_file_in_exactly_one_module"]
    assert not checks["semantic_dispositions_cover_inventory"]
    index = (run_dir / "docs" / "INDEX.md").read_text()
    assert "pending" in index
    assert find(run_dir, "reserve_run") or find(run_dir, "main")

    resumed = host_run.resume(run_dir, owner="codex")
    assert resumed["retried"] == [broken["task"]] and resumed["status"] == "running"
    _drive(run_dir)
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"]
    assert broken["task"] in [f"module_{n + 1}" for n in state["tasks"]["system"]["covered"]]
    assert "are pending" not in (run_dir / "docs" / "INDEX.md").read_text()


def test_failed_overview_falls_back_and_is_retried_on_its_own(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=8)["run_dir"])
    for _ in range(10):
        batch = host_run.next_tasks(run_dir)["tasks"]
        if not batch:
            break
        for item in batch:
            _answer_task(run_dir, item, "{}" if item["kind"] == "system" else _good(item, run_dir))
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["tasks"]["system"]["status"] == "failed" and state["status"] == "partial"
    index = (run_dir / "docs" / "INDEX.md").read_text()
    assert "are mechanical" in index and "`system` task is failed" in index
    host_run.retry(run_dir, "system")
    item = host_run.next_tasks(run_dir)["tasks"][0]
    assert item["task"] == "system"
    _answer_task(run_dir, item, _good(item, run_dir))
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete"
    assert "are mechanical" not in (run_dir / "docs" / "INDEX.md").read_text()


def test_script_prompt_embeds_source_and_host_task_lists_paths(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "src" / "pkg" / "empty.py").write_text("", encoding="utf-8")
    run_dir = tmp_path / "run"
    host_run.plan(repo, run_dir, review="none", host="opencode", driver="script")
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    batch = host_run.next_tasks(run_dir, limit=1)
    assert [item["task"] for item in batch["tasks"]] == ["names"]
    Path(batch["tasks"][0]["output_file"]).write_text(
        json.dumps(_answer({"kind": "names"}, host_run.completion_prompt(run_dir, "names"))), encoding="utf-8")
    assert host_run.submit(run_dir, "names")["accepted"]
    checked = 0
    for item in host_run.next_tasks(run_dir)["tasks"]:
        module = state["modules"][int(item["task"].split("_")[1]) - 1]
        script = host_run.completion_prompt(run_dir, item["task"])
        hosted = Path(item["prompt_file"]).read_text(encoding="utf-8")
        for path in module["files"]:
            text = (repo / path).read_text(encoding="utf-8")
            if text:
                assert text in script, f"script prompt for {item['task']} lacks the body of {path}"
            # Host mode hands over absolute paths, never the text.
            assert str(repo / path) in hosted
            if text:
                assert text not in hosted
                checked += 1
    assert checked >= 3  # every non-empty file of the repository was compared


def test_script_prompt_refuses_changed_source(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    host_run.plan(repo, run_dir, review="none", host="opencode", driver="script")
    (repo / "src" / "pkg" / "jobs.py").write_text("changed = 1\n", encoding="utf-8")
    with pytest.raises(host_run.HostRunError, match="source changed"):
        for number in range(len(json.loads((run_dir / "host" / "state.json").read_text())["modules"])):
            host_run.completion_prompt(run_dir, f"module_{number + 1}")


def test_host_run_pages_and_catalog_carry_concrete_facts(tmp_path: Path) -> None:
    """Host state keeps digests, not text: the facts must still be extracted at render time."""
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, review="none", jobs=2, host="test")["run_dir"])
    host_run.release(run_dir)
    _drive(run_dir)
    # (Pages print no facts table; the catalogue is where the facts are asserted.)
    catalog = json.loads((run_dir / "catalog.json").read_text())
    assert any(entry.get("facts") for entry in catalog["symbols"].values())
    assert any("negative" in json.dumps(item) for item in find(run_dir, "negative"))


def _graph_for(repo: Path, paths: list[str]) -> dict:
    import hashlib
    manifest = [{"path": path, "language": "python",
                 "sha256": hashlib.sha256((repo / path).read_bytes()).hexdigest()} for path in paths]
    nodes = [{"id": f"n-{index}", "kind": "function", "path": path,
              "start_line": 1, "end_line": 1, "name": Path(path).stem}
             for index, path in enumerate(paths)]
    return {"schema": "cbe-graph/1", "source_manifest": manifest,
            "backend": {"name": "test", "version": "1"},
            "nodes": nodes, "edges": [], "capabilities": [], "diagnostics": []}


def test_plan_freezes_graph_and_detail_prompt_carries_it(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(_graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])), encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", graph_path=graph_path)["run_dir"])
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["context"]["graph_present"] is True and state["context"]["schema"] == "cbe-context/1"
    module = next(row for row in state["modules"] if "src/pkg/jobs.py" in row["files"])
    prompt = host_run.completion_prompt(run_dir, f"module_{module['number'] + 1}")
    assert "Batch-internal resolved calls" in prompt or "Graph: internal=" in prompt
    assert "n-0" not in prompt  # Joern ids no longer leak into author evidence


def test_host_graph_file_and_review_repair_share_frozen_evidence(tmp_path: Path):
    repo = _repo(tmp_path)
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(_graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])))
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="all", graph_path=graph_path)["run_dir"])
    state = json.loads((run_dir / "host" / "state.json").read_text())
    module = next(row for row in state["modules"] if "src/pkg/jobs.py" in row["files"])
    number = module["number"]
    detail = state["tasks"][f"module_{number + 1}"]
    # Tool-free construction must not create graph artifacts or mention a file.
    script = host_run.completion_prompt(run_dir, detail["id"])
    assert "tool-free; omitted evidence cannot be inspected" in script
    assert ".graph.txt" not in script and "graph query" not in script
    assert not list((run_dir / "host" / "tasks").glob("*.graph.txt"))
    full = None
    expected = None
    seen = set()
    for _ in range(30):
        batch = host_run.next_tasks(run_dir)
        if not batch["tasks"]:
            break
        for item in batch["tasks"]:
            body = Path(item["prompt_file"]).read_text()
            kind = item["kind"]
            if kind in {"module", "review", "repair"} and item["task"].endswith(f"_{number + 1}"):
                target = run_dir / "host" / "tasks" / f"module_{number + 1}.graph.txt"
                assert target.is_file() and str(target) in body
                assert "graph query" not in body
                section = body.split("Graph access:", 1)[1].split("SOURCE FILES", 1)[0]
                if expected is None:
                    expected, full = section, target.read_text()
                    assert "Omitted: none" in full
                assert section == expected and target.read_text() == full
                seen.add(kind)
            decision = "needs_repair" if kind == "review" and "repair" not in seen else "accepted"
            Path(item["output_file"]).write_text(json.dumps(_answer(item, body, decision=decision)))
            result = host_run.submit(run_dir, item["task"])
            assert result["accepted"], result
    assert seen == {"module", "review", "repair"}



def test_plan_rejects_a_graph_that_does_not_match_the_source(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    graph = _graph_for(repo, ["src/pkg/jobs.py"])
    graph["source_manifest"][0]["sha256"] = "0" * 64
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    with pytest.raises(host_run.HostRunError, match="source context build failed"):
        host_run.plan(repo, tmp_path / "run", review="none", graph_path=graph_path)


def test_script_driver_carries_the_graph_into_the_module_prompt(tmp_path: Path, monkeypatch) -> None:
    from cbe.headless_completion import Completion, _csv_row
    repo = _repo(tmp_path)
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(_graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])), encoding="utf-8")
    seen: dict[str, str] = {}

    def fake_invoke(**kwargs):
        seen[kwargs["task"]] = kwargs["prompt"]
        prompt = kwargs["prompt"]
        if "Modules:\n" in prompt and "INVENTORY (" not in prompt:
            rows = json.loads(prompt.split("Modules:\n", 1)[1])
            value = {"names": [{"module": row["module"], "title": f"Area {row['module']}"} for row in rows]}
        elif "INVENTORY (this batch" in prompt:
            inv = json.loads(prompt.split("INVENTORY (this batch, authoritative ids):\n", 1)[1].split("\n\n", 1)[0])
            units, dispositions = [], {}
            for file_row in inv:
                for symbol in file_row["symbols"]:
                    units.append({"id": symbol["id"], "kind": symbol["kind"],
                                  "explain": f"Unit {symbol['name']}.", "extras": [],
                                  "relations": [], "uncertainties": []})
                    dispositions[symbol["id"]] = {"how": "unit", "unit": symbol["id"], "reason": "behavior"}
            value = {"units": units, "dispositions": dispositions, "batch_notes": "ok"}
        elif "UNITS:\n" in prompt:
            units = json.loads(prompt.split("UNITS:\n", 1)[1])
            value = {"nodes": [{"id": "root", "parent": None, "title": "Root",
                                "capability": "Every unit under one responsibility root.",
                                "summary": "Start here.", "unit_ids": [u["id"] for u in units]}],
                     "depends_on": []}
        elif "DOCUMENTATION (structured units)" in prompt:
            value = {"decision": "accepted", "issues": []}
        else:
            value = {"overview": "A package.", "maintenance_navigation": "Open the root node."}
        _csv_row(kwargs["csv_path"], {"task": kwargs["task"], "attempt": kwargs["attempt"],
                                      "input_tokens": 500, "output_tokens": 2, "cache_tokens": 0,
                                      "result": "ok", "seconds": 0.01})
        return Completion(value, None, json.dumps(value), {"input": 500, "output": 2, "cache": 0}, 0.01)

    monkeypatch.setattr("cbe.generate.invoke", fake_invoke)
    from cbe.generate import generate
    result = generate(repo, tmp_path / "run", model="example/model", jobs=2, graph_path=graph_path)
    assert result["status"] == "complete"
    module_prompts = [prompt for task, prompt in seen.items()
                      if task.startswith("module_") and task[7:].isdigit()]
    assert module_prompts and any("Batch-internal resolved calls:" in prompt or "Graph: internal=" in prompt
                                  for prompt in module_prompts)
    assert all(".graph.txt" not in prompt and "graph query" not in prompt for prompt in module_prompts)
    assert not list((tmp_path / "run" / "host" / "tasks").glob("*.graph.txt"))
    for task_file in (tmp_path / "run" / "host" / "tasks").glob("*.md"):
        assert "graph evidence file" not in task_file.read_text()


@pytest.mark.parametrize("graph", [None, {"schema": "wrong"},
    {"schema": "cbe-graph/1", "nodes": [], "edges": [], "capabilities": []}])
def test_graph_status_does_not_invite_file_reads(graph):
    prompt = prompts.detail_prompt(["a.py"], {"a.py": {"symbols": []}}, graph=graph,
                                   embed=False, graph_file="/missing.graph.txt")
    assert "Graph access:" not in prompt
    assert "/missing.graph.txt" not in prompt


def test_summary_reports_structure_and_semantic_review_separately(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="sample")["run_dir"])
    _drive(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["deterministic_checks_ok"] is True
    assert summary["semantic_review"]["mode"] == "sample"
    assert summary["semantic_review"]["outcomes"] == {"accepted": 1}
    assert "not a bill" not in summary.get("truth", "")  # the note names the review distinction
    status = (run_dir / "STATUS.md").read_text()
    assert "Semantic review" in status and "separate reader" in status


def test_forged_frozen_context_graph_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none")["run_dir"])
    path = run_dir / "context.json"
    context = json.loads(path.read_text())
    context["graph"] = {"schema": "cbe-graph/1", "source_manifest": [],
                        "nodes": [{"id": "forged", "path": "src/pkg/jobs.py",
                                   "name": "FORGED_GRAPH_SENTINEL"}],
                        "edges": [], "capabilities": [], "diagnostics": []}
    path.write_text(json.dumps(context))
    with pytest.raises(host_run.HostRunError, match="modified after planning"):
        host_run.completion_prompt(run_dir, "module_1")
    with pytest.raises(host_run.HostRunError, match="modified after planning"):
        host_run.next_tasks(run_dir)
    report = host_run.verify(run_dir)
    assert not report["ok"]
    assert any(row["check"] == "frozen_context_intact" and not row["ok"] for row in report["checks"])


def test_tampered_frozen_context_chunk_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none")["run_dir"])
    path = run_dir / "context.json"
    context = json.loads(path.read_text())
    context["chunks"][0]["text"] = "FORGED_CHUNK_SENTINEL"
    path.write_text(json.dumps(context))
    with pytest.raises(host_run.HostRunError, match="modified after planning"):
        host_run.completion_prompt(run_dir, "module_1")


def test_submit_refuses_evidence_against_a_tampered_context(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none")["run_dir"])
    names = host_run.next_tasks(run_dir)["tasks"][0]
    _answer_task(run_dir, names, _good(names, run_dir))
    host_run.submit(run_dir, "names")
    item = host_run.next_tasks(run_dir)["tasks"][0]
    Path(item["output_file"]).write_text(json.dumps(_good(item, run_dir)), encoding="utf-8")
    path = run_dir / "context.json"
    context = json.loads(path.read_text())
    context["chunks"][0]["text"] = "FORGED_CHUNK_SENTINEL"
    path.write_text(json.dumps(context))
    with pytest.raises(host_run.HostRunError, match="modified after planning"):
        host_run.submit(run_dir, item["task"])


def _boundary_graph(repo: Path) -> dict:
    import hashlib
    def digest(path: str) -> str:
        return hashlib.sha256((repo / path).read_bytes()).hexdigest()
    return {"schema": "cbe-graph/1", "backend": {"name": "test", "version": "1"},
            "source_manifest": [{"path": "data/config.json", "sha256": digest("data/config.json")},
                                {"path": "src/pkg/jobs.py", "sha256": digest("src/pkg/jobs.py")}],
            "nodes": [{"id": "n-jobs", "kind": "function", "path": "src/pkg/jobs.py",
                       "start_line": 1, "end_line": 1, "name": "reserve_run"},
                      {"id": "n-data", "kind": "external", "path": "data/config.json",
                       "start_line": 1, "end_line": 1, "name": "config"}],
            "edges": [], "capabilities": [], "diagnostics": []}


def test_graph_boundary_file_drift_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "data").mkdir()
    (repo / "data" / "config.json").write_text('{"a": 1}\n', encoding="utf-8")
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(_boundary_graph(repo)), encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", graph_path=graph_path)["run_dir"])
    host_run.completion_prompt(run_dir, "module_1")  # intact: no error
    (repo / "data" / "config.json").write_text('{"a": 2}\n', encoding="utf-8")
    with pytest.raises(host_run.HostRunError, match="boundary source drifted"):
        host_run.completion_prompt(run_dir, "module_1")


def test_resume_rejects_a_different_graph(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    graph_a = _graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])
    ga = tmp_path / "ga.json"
    ga.write_text(json.dumps(graph_a), encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", graph_path=ga)["run_dir"])
    graph_b = {**graph_a, "backend": {"name": "test", "version": "2"}}
    gb = tmp_path / "gb.json"
    gb.write_text(json.dumps(graph_b), encoding="utf-8")
    with pytest.raises(host_run.HostRunError, match="differs from the frozen graph"):
        host_run.resume(run_dir, graph_path=gb)
    host_run.resume(run_dir, graph_path=ga)  # the frozen graph itself is accepted
    with pytest.raises(host_run.HostRunError, match="planned without a graph"):
        repo2 = _repo(tmp_path / "nograph")
        other = Path(host_run.plan(repo2, tmp_path / "nograph-run", review="none")["run_dir"])
        host_run.resume(other, graph_path=ga)


def test_known_empty_file_is_indexed_without_a_model_call(tmp_path: Path) -> None:
    """A zero-byte file is known-empty: no chunk, no unit, no model call, but it
    stays in the manifest/catalogue and the run still completes."""
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "pkg" / "core.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (repo / "tests" / "__init__.py").write_text("", encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=2)["run_dir"])
    state = json.loads((run_dir / "host" / "state.json").read_text())
    empty_module = next(row for row in state["modules"] if "tests/__init__.py" in row["files"])
    assert state["inventory"]["tests/__init__.py"]["symbols"] == []
    assert state["inventory"]["tests/__init__.py"]["known_empty"] is True
    assert not any(chunk["path"] == "tests/__init__.py"
                   for chunk in json.loads((run_dir / "context.json").read_text())["chunks"])

    handed = _drive(run_dir)
    empty_task = f"module_{empty_module['number'] + 1}"
    assert empty_task not in handed, "the known-empty batch must not spend a model call"
    accepted = json.loads((run_dir / "host" / "accepted" / f"{empty_task}.json").read_text())
    assert accepted["units"] == [] and accepted["known_empty"] is True
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"]
    catalog = json.loads((run_dir / "catalog.json").read_text())
    assert catalog["files"]["tests/__init__.py"]["known_empty"] is True
    index = (run_dir / "docs" / "INDEX.md").read_text()
    assert "Known-empty files" in index and "tests/__init__.py" in index


def test_comment_only_file_still_reaches_the_model(tmp_path: Path) -> None:
    """Legitimate comments/docstrings are not 'empty': they keep a reading chunk
    and an inventory id, so the batch is documented, not auto-completed."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "doc.py").write_text('"""Module docstring only."""\n', encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=1)["run_dir"])
    state = json.loads((run_dir / "host" / "state.json").read_text())
    module = state["modules"][0]
    assert not state["inventory"]["doc.py"].get("known_empty")
    assert any(symbol["id"].startswith("doc.py::")
               for symbol in state["inventory"]["doc.py"]["symbols"])
    handed = _drive(run_dir)
    assert f"module_{module['number'] + 1}" in handed


def test_repair_requeues_the_tree_so_new_group_units_get_an_owner(tmp_path: Path) -> None:
    """A repair can add grp: units; the ownership tree must be rebuilt or those
    units have no primary owner and verify fails."""
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="all", jobs=8)["run_dir"])
    handed: list[str] = []
    for _ in range(60):
        batch = host_run.next_tasks(run_dir)
        if not batch["tasks"]:
            break
        for item in batch["tasks"]:
            handed.append(item["task"])
            prompt = Path(item["prompt_file"]).read_text()
            kind = item["kind"]
            if kind == "names":
                value = _answer({"kind": "names"}, prompt)
            elif kind in {"module", "repair"}:
                value = _detail_from_prompt(prompt)
                if kind == "repair":
                    value["units"].append({"id": f"grp:extra-{item['task']}", "kind": "group",
                                           "explain": "A helper grouped by the repair.",
                                           "extras": [], "relations": [], "uncertainties": []})
            elif kind == "tree":
                value = _tree_from_prompt(prompt)
            elif kind == "review":
                value = {"decision": "needs_repair", "issues": ["group the helper"]}
            else:
                value = {"overview": "A tiny package.", "maintenance_navigation": "Open the root node."}
            Path(item["output_file"]).write_text(json.dumps(value), encoding="utf-8")
            result = host_run.submit(run_dir, item["task"], usage={"total_tokens": 1000})
            assert result["accepted"], result
    assert handed.count("tree") >= 2  # rebuilt after the repair changed the unit set
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"], state["verify"]["checks"]
    tree = json.loads((run_dir / "host" / "accepted" / "tree.json").read_text())
    owned = {uid for node in tree["nodes"] for uid in node.get("unit_ids") or []}
    assert {"grp:extra-repair_1", "grp:extra-repair_2"} <= owned


def test_repair_may_reuse_its_own_module_group_ids(tmp_path: Path) -> None:
    """A repair may redefine a ``grp:`` unit its own module already defined.

    That is the same unit being revised, not a cross-batch duplicate. The old
    path-only exclusion kept ``grp:`` ids (which carry no path) in the known
    set and rejected the repair with a false duplicate error."""
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "jobs.py").write_text(
        "def reserve_run(value):\n    if value < 0:\n        raise ValueError('negative')\n    return value\n",
        encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="all", jobs=4)["run_dir"])
    group_id = "grp:jobs-helpers"
    repair_seen = False
    for _ in range(40):
        batch = host_run.next_tasks(run_dir)
        if not batch["tasks"]:
            break
        for item in batch["tasks"]:
            prompt = Path(item["prompt_file"]).read_text()
            kind = item["kind"]
            if kind == "names":
                value = _answer({"kind": "names"}, prompt)
            elif kind == "module":
                value = _detail_from_prompt(prompt)
                value["units"].append({"id": group_id, "kind": "group",
                                       "explain": "Grouped helpers.",
                                       "extras": [], "relations": [], "uncertainties": []})
            elif kind == "repair":
                repair_seen = True
                value = _detail_from_prompt(prompt)
                value["units"].append({"id": group_id, "kind": "group",
                                       "explain": "Grouped helpers, revised.",
                                       "extras": [], "relations": [], "uncertainties": []})
            elif kind == "tree":
                value = _tree_from_prompt(prompt)
            elif kind == "review":
                value = {"decision": "needs_repair", "issues": ["revise the group"]}
            else:
                value = {"overview": "A tiny package.", "maintenance_navigation": "Open the root node."}
            Path(item["output_file"]).write_text(json.dumps(value), encoding="utf-8")
            result = host_run.submit(run_dir, item["task"], usage={"total_tokens": 1000})
            assert result["accepted"], result
    assert repair_seen
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"], state["verify"]["checks"]


def test_empty_module_does_not_shortcut_the_tree_before_real_modules_finish(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "pkg" / "core.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (repo / "tests" / "__init__.py").write_text("", encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=2)["run_dir"])
    host_run.next_tasks(run_dir)  # auto-completes the empty batch, leases names
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["tasks"]["tree"]["status"] == "pending"
    assert state["tasks"]["system"]["status"] == "pending"
    assert not (run_dir / "host" / "accepted" / "tree.json").exists()
    host_run.release(run_dir)  # hand the leased names task back before driving
    _drive(run_dir)
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"]


def test_module_with_no_graph_node_gets_an_explicit_no_local_node_statement(tmp_path: Path) -> None:
    """A graph that anchors only one file must not read as an empty graph for a
    module whose files it never analyzed; the frozen full graph is projected."""
    repo = _repo(tmp_path)
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(_graph_for(repo, ["src/pkg/jobs.py"])), encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", graph_path=graph_path)["run_dir"])
    state = json.loads((run_dir / "host" / "state.json").read_text())
    module = next(row for row in state["modules"] if "src/pkg/jobs.py" not in row["files"])
    prompt = host_run.completion_prompt(run_dir, f"module_{module['number'] + 1}")
    assert "no graph node anchors the listed file(s)" in prompt
    assert "not an empty graph and not a missing graph" in prompt
    anchored = next(row for row in state["modules"] if "src/pkg/jobs.py" in row["files"])
    anchored_prompt = host_run.completion_prompt(run_dir, f"module_{anchored['number'] + 1}")
    assert "Batch-internal resolved calls" in anchored_prompt or "Graph: internal=" in anchored_prompt
