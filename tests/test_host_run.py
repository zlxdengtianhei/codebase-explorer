"""Host-agent driven generation: plan, lease, submit, resume, render, verify, cost."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import pytest

from cbe import usage
from cbe import checks, cli, host_run, prompts, symbols
from cbe.catalog_query import find


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


def _prompt_symbols(prompt: str) -> list[tuple[int, str, str]]:
    """(number, kind, name) of every symbol line in a detail prompt's numbered list."""
    block = prompt.split("SYMBOLS (this batch; number, kind, name, source lines):\n", 1)[1].split("\n\n", 1)[0]
    rows = []
    for line in block.splitlines():
        match = re.fullmatch(r"(\d+) (\w+) (.+) L[\d,-]+", line)
        if match:
            rows.append((int(match[1]), match[2], match[3]))
    return rows


def _detail_from_prompt(prompt: str) -> dict:
    """Play the author: one unit per listed symbol, answering with short numbers."""
    return {"units": [{"h": [number], "explain": f"Unit {name} does its job."}
                      for number, _, name in _prompt_symbols(prompt)]}


def _group_first(value: dict, title: str, count: int = 2) -> dict:
    """Fold the first ``count`` answer units into one grouped unit (``h`` lists several numbers)."""
    units = value["units"]
    merged = {"h": [number for unit in units[:count] for number in unit["h"]], "title": title,
              "explain": f"Helpers {title} work together."}
    return {**value, "units": [merged, *units[count:]]}


def _tree_name_from_prompt(prompt: str) -> dict:
    """Play the namer of leaf modules: one record per ``## M<k>`` block, titles that differ across batches."""
    body = prompt.split("MODULES:\n\n", 1)[1]
    rows = []
    for block in re.split(r"(?m)^(?=## M\d+ )", body):
        head = re.match(r"## (M\d+) ", block)
        if head:
            tag = hashlib.md5(block.encode()).hexdigest()[:6]
            rows.append({"id": head[1], "title": f"Module {head[1]} {tag}",
                         "capability": f"Handles the work of {head[1]}.",
                         "summary": "Come here for this work. It holds the units.",
                         "evidence_units": re.findall(r"(?m)^  (u\d+):", block)[:2]})
    return {"modules": rows}


def _tree_top_from_prompt(prompt: str) -> dict:
    return {"groups": [{"id": label, "title": f"Group {label} area",
                        "capability": "Groups several modules that share one responsibility.",
                        "summary": "Come here to see how the modules divide the work."}
                       for label in re.findall(r"(?m)^## (G\d+) ", prompt)]}


def _system_answer(prompt):
    view = json.loads(prompt.split("RELATIONSHIPS: ", 1)[1].split("\nNODE SUMMARIES:", 1)[0])
    candidates = view["candidate_flows"]
    return {"dependency_descriptions": [{"from": e["from"], "to": e["to"], "description": "Uses its service."}
                                         for e in view["dependencies"][:1]],
            "key_flows": [{"name": f"Flow {i}", "description": "Runs the operation.",
                           "steps": candidates[i % len(candidates)]} for i in range(3)] if candidates else []}


def _answer(task: dict, prompt: str, *, decision: str = "accepted") -> dict:
    """Play the subagent: answer from the instruction file alone."""
    kind = task["kind"]
    if kind in {"module", "repair"}:
        return _detail_from_prompt(prompt)
    if kind == "tree_name":
        return _tree_name_from_prompt(prompt)
    if kind == "tree_top":
        return _tree_top_from_prompt(prompt)
    if kind == "review":
        return {"decision": decision, "issues": ["the negative check is missing"] if decision != "accepted" else []}
    return {"overview": "A tiny job reservation package.", **_system_answer(prompt)}


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
    assert [item["task"] for item in first["tasks"]] == ["module_1", "module_2"]
    host_run.release(run_dir)
    handed = _drive(run_dir)
    assert handed[-1] == "system"
    assert "tree_top" not in handed, "a one-module repository has nothing to group"
    assert handed.index("tree_name_1") < handed.index("system")
    assert sum(task.startswith("review_") for task in handed) == 1

    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"], state["verify"]
    index = (run_dir / "docs" / "INDEX.md").read_text()
    assert "## Modules" in index and "](nodes/" in index and str(tmp_path) not in index
    assert (run_dir / "docs" / "DEPENDENCIES.md").is_file() and (run_dir / "docs" / "RUN.md").is_file()
    assert find(run_dir, "reserve_run")
    assert host_run.verify(run_dir)["ok"]
    assert not list((run_dir / "host/tasks").glob("*.graph.txt"))
    assert all("Graph access:" not in file.read_text() for file in (run_dir / "host/tasks").glob("*.md"))


def test_concurrency_limit_and_schema_retry_then_failure(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=1)["run_dir"])
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
    assert not second["accepted"] and second["task_status"] == "pending"
    host_run.next_tasks(run_dir)
    failed = host_run.submit(run_dir, item["task"])
    assert not failed["accepted"] and failed["task_status"] == "failed" and failed["failed"]
    with pytest.raises(host_run.HostRunError):
        host_run.submit(run_dir, item["task"])
    assert host_run.retry(run_dir, item["task"])["counts"]["pending"] >= 1
    third = host_run.next_tasks(run_dir)["tasks"][0]
    Path(third["output_file"]).write_text(json.dumps(_answer({"kind": "module"}, Path(third["prompt_file"]).read_text())))
    accepted = host_run.submit(run_dir, item["task"])
    assert accepted["accepted"] and accepted["attempts"] == 4
    assert (run_dir / "host" / "raw" / f"{item['task']}.attempt-4.txt").is_file()


def test_resume_adopts_finished_results_and_releases_lost_leases(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=4)["run_dir"])
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


def test_a_sampled_review_with_findings_escalates_to_every_batch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="sample", jobs=8)["run_dir"])
    handed = _drive(run_dir, decision="needs_repair")
    state = json.loads((run_dir / "host" / "state.json").read_text())
    modules = state["modules"]
    assert len(modules) >= 2
    assert sum(task.startswith("review_") for task in handed) == len(modules)
    assert sum(task.startswith("repair_") for task in handed) == len(modules)
    assert handed[-1] == "system"
    escalated = state["review_escalated"]
    assert escalated["issues"] == 1 and len(escalated["added"]) == len(modules) - 1
    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["semantic_review"]["escalated"] == escalated
    notes = (run_dir / "docs" / "RUN.md").read_text()
    assert (f"Review: the sampled batch ({escalated['from']}) reported 1 issue(s), so every batch was reviewed: "
            f"{len(modules)} of {len(modules)} reviewed, {len(modules)} issue(s) in total.") in notes
    assert host_run.verify(run_dir)["ok"]


def test_a_clean_sampled_review_stays_a_sample(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="sample", jobs=8)["run_dir"])
    handed = _drive(run_dir)
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert sum(task.startswith("review_") for task in handed) == 1 and "review_escalated" not in state
    notes = (run_dir / "docs" / "RUN.md").read_text()
    others = len(state["modules"]) - 1
    assert f"0 issue(s); the other {others} batch(es) were not reviewed." in notes


def test_source_drift_blocks_dispatch_and_fails_verify(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none")["run_dir"])
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
    assert "excludes graph evidence files read by host authors" in (run_dir / "host" / "COST.md").read_text()

    session = tmp_path / "claude" / "proj" / "session" / "subagents"
    session.mkdir(parents=True)
    (session / "agent-a1.meta.json").write_text(json.dumps({"description": f"cbe {tag} module_1"}))
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
    assert rows["module_1"]["basis"] == "exact"
    assert rows["module_1"]["cache_write_tokens"] == 110 and rows["module_1"]["output_tokens"] == 100
    assert rows["module_1"]["harness_reported_total_tokens"] == 1000
    assert rows["system"]["cache_read_tokens"] == 600 and rows["system"]["input_tokens"] == 300
    assert rows["system"]["models"] == ["gpt-6.1-sol"]
    host_run.render(run_dir)
    assert json.loads((run_dir / "summary.json").read_text())["basis"]["models"] == [
        "claude-sonnet-5-5", "gpt-6.1-sol"]
    assert rows["module_1"]["usd_api_equivalent"] > 0
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
    assert status["run_dir"] == planned["run_dir"] and status["ready"] == planned["modules"]
    assert cli.main(["host", "next", "--run-dir", planned["run_dir"]]) == 0
    item = json.loads(capsys.readouterr().out)["tasks"][0]
    Path(item["output_file"]).write_text(json.dumps(_answer({"kind": "module"}, Path(item["prompt_file"]).read_text())))
    assert cli.main(["host", "submit", "--run-dir", planned["run_dir"], "--task", item["task"],
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


def test_gaps_are_re_asked_alone_and_the_last_answer_indexes_what_stays_unexplained(
        tmp_path: Path, monkeypatch) -> None:
    """Replaces the final-answer normalizer test: an answer with a gap is not accepted whole or
    thrown away. The re-ask lists only the gap, and after the last answer the symbol that nobody
    explained is indexed without prose, flagged ``unexplained``, and the run still completes."""
    monkeypatch.setattr(checks, "GAP_MIN_TOKENS", 1)  # the tiny test functions count as having logic
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=8)["run_dir"])
    batch = host_run.next_tasks(run_dir)["tasks"]
    target = batch[0]
    for item in batch[1:]:
        _answer_task(run_dir, item, _good(item, run_dir))
    state = json.loads((run_dir / "host" / "state.json").read_text())
    table = symbols.batch_table(state["modules"][int(target["task"].split("_")[1]) - 1]["files"], state["inventory"])
    gap_row = next(row for row in table if row["kind"] == "function")  # no unit will mention this one
    bad = _good(target, run_dir)
    bad["units"] = [unit for unit in bad["units"] if unit["h"] != [gap_row["n"]]]
    bad["units"][0]["h"].append(99)  # an unknown number is dropped and noted, the unit is kept
    first = _answer_task(run_dir, target, bad)
    assert not first["accepted"] and first["task_status"] == "pending"
    assert first["error"].startswith("incomplete:")
    again = host_run.next_tasks(run_dir)["tasks"][0]
    assert again["task"] == target["task"]
    followup = Path(again["prompt_file"]).read_text().split("FOLLOW-UP:", 1)[1].split("\n---\n", 1)[0]
    assert f"{gap_row['n']} function {gap_row['name']}" in followup  # the gap is listed ...
    assert followup.count("\n") < 8  # ... and only the gap: no unit that was kept comes back
    second = _answer_task(run_dir, again, {"units": []})  # a useless re-answer changes nothing
    assert not second["accepted"] and second["task_status"] == "pending"
    third = _answer_task(run_dir, host_run.next_tasks(run_dir)["tasks"][0], {"units": []})
    assert third["accepted"] and third["normalized"]
    assert third["flags"].count(f"unexplained: {gap_row['id']}") == 1
    assert any("unknown symbol number 99" in flag for flag in third["flags"])
    accepted = json.loads((run_dir / "host" / "accepted" / f"{target['task']}.json").read_text())
    assert accepted["dispositions"][gap_row["id"]]["how"] == "index_only"
    assert gap_row["id"] not in {unit["id"] for unit in accepted["units"]}
    tree_item = host_run.next_tasks(run_dir)["tasks"][0]
    assert tree_item["kind"] == "tree_name"
    _answer_task(run_dir, tree_item, _good(tree_item, run_dir))
    system = host_run.next_tasks(run_dir)["tasks"][0]
    assert system["kind"] == "system"
    overview = "A tiny package that reserves job runs. " * 80  # far above the cap
    _answer_task(run_dir, system, {"overview": overview})
    _answer_task(run_dir, host_run.next_tasks(run_dir)["tasks"][0], {"overview": overview})
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"]
    notes = (run_dir / "docs" / "RUN.md").read_text()
    assert "## Generation notes" in notes and "overview truncated" in notes
    assert "Accepted with repairs or gaps" in notes and "left without prose" in notes
    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["unexplained"] == [{"task": target["task"], "symbol": gap_row["id"]}]
    log = (run_dir / "progress.log").read_text()
    for word in ("plan ", "claim ", "reject ", "normalize ", "accept ", "render "):
        assert word in log, word
    assert "| module_1 |" in (run_dir / "STATUS.md").read_text()


def test_unusable_module_renders_partial_and_resume_finishes_it(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="sample", jobs=8)["run_dir"])
    batch = host_run.next_tasks(run_dir)["tasks"]
    broken = batch[-1]
    for item in batch[:-1]:
        _answer_task(run_dir, item, _good(item, run_dir))
    for _ in range(3):
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
    assert "pending" in (run_dir / "docs" / "RUN.md").read_text()
    assert find(run_dir, "reserve_run") or find(run_dir, "main")

    resumed = host_run.resume(run_dir, owner="codex")
    assert resumed["retried"] == [broken["task"]] and resumed["status"] == "running"
    _drive(run_dir)
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"]
    assert broken["task"] in [f"module_{n + 1}" for n in state["tasks"]["system"]["covered"]]
    assert "are pending" not in (run_dir / "docs" / "RUN.md").read_text()


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
    notes = (run_dir / "docs" / "RUN.md").read_text()
    assert "is mechanical" in notes and "`system` task is failed" in notes
    host_run.retry(run_dir, "system")
    item = host_run.next_tasks(run_dir)["tasks"][0]
    assert item["task"] == "system"
    _answer_task(run_dir, item, _good(item, run_dir))
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete"
    assert "is mechanical" not in (run_dir / "docs" / "RUN.md").read_text()


def test_script_prompt_embeds_source_and_host_task_lists_paths(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "src" / "pkg" / "empty.py").write_text("", encoding="utf-8")
    run_dir = tmp_path / "run"
    host_run.plan(repo, run_dir, review="none", host="api", driver="script")
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
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
    host_run.plan(repo, run_dir, review="none", host="api", driver="script")
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
    from cbe.catalog_query import query
    matches = find(run_dir, "negative")
    assert matches and all(row["id"] and row["location"] and row["matched_fields"] for row in matches)
    assert any("negative" in json.dumps(query(run_dir, row["id"])) for row in matches)


def _graph_for(repo: Path, paths: list[str]) -> dict:
    import hashlib
    from cbe.graph import graph_quality
    manifest = [{"path": path, "language": "python",
                 "sha256": hashlib.sha256((repo / path).read_bytes()).hexdigest()} for path in paths]
    nodes = [{"id": f"n-{index}", "kind": "function", "path": path,
              "start_line": 1, "end_line": 1, "name": Path(path).stem}
             for index, path in enumerate(paths)]
    value = {"schema": "cbe-graph/1", "source_manifest": manifest,
             "backend": {"name": "test", "version": "1"},
             "nodes": nodes, "edges": [], "capabilities": [], "diagnostics": []}
    value["quality"] = graph_quality(value)
    return value


def test_graph_query_accepts_frozen_context_json(tmp_path: Path, capsys):
    repo = _repo(tmp_path)
    graph = _graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])
    graph["edges"] = [{"id": "call", "kind": "call", "source": "n-1", "target": "n-0",
                       "status": "resolved", "path": "src/pkg/cli.py", "line": 4}]
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph))
    run_dir = Path(host_run.plan(repo, tmp_path / "run", graph_path=graph_path)["run_dir"])
    assert cli.main(["graph", "query", "--graph", str(run_dir / "context.json"),
                     "--path", "src/pkg/cli.py", "--kind", "call"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert [edge["id"] for edge in result["edges"]] == ["call"]
    assert {node["id"] for node in result["nodes"]} == {"n-0", "n-1"}


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
    from cbe.api_completion import Completion, _csv_row
    repo = _repo(tmp_path)
    graph_path = tmp_path / "graph.json"
    graph = _graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])
    graph["edges"] = [{"id": "visible-call", "kind": "call", "status": "resolved",
                       "source": "n-0", "target": "n-0", "path": "src/pkg/jobs.py", "line": 8,
                       "column": 5}]
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    seen: dict[str, str] = {}

    def fake_invoke(**kwargs):
        seen[kwargs["task"]] = kwargs["prompt"]
        prompt = kwargs["prompt"]
        if "MODULES:\n\n" in prompt:
            value = _tree_name_from_prompt(prompt)
        elif "GROUPS:\n\n" in prompt:
            value = _tree_top_from_prompt(prompt)
        elif "SYMBOLS (this batch" in prompt:
            value = _detail_from_prompt(prompt)
        elif "DOCUMENTATION (structured units)" in prompt:
            value = {"decision": "accepted", "issues": []}
        else:
            value = {"overview": "A package.", **_system_answer(prompt)}
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
    assert module_prompts and any("Batch-internal resolved calls: 1 " in prompt or "Graph: internal=1," in prompt
                                  for prompt in module_prompts)
    assert all(".graph.txt" not in prompt and "graph query" not in prompt for prompt in module_prompts)
    assert not list((tmp_path / "run" / "host" / "tasks").glob("*.graph.txt"))
    for task_file in (tmp_path / "run" / "host" / "tasks").glob("*.md"):
        assert "graph evidence file" not in task_file.read_text()


@pytest.mark.parametrize("graph", [None, {"schema": "wrong"},
    {"schema": "cbe-graph/1", "nodes": [], "edges": [], "capabilities": []}])
def test_graph_status_does_not_invite_file_reads(graph):
    if graph and graph.get("schema") == "cbe-graph/1":
        from cbe.graph import graph_quality
        graph["quality"] = graph_quality(graph)
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
    assert summary["basis"]["graph"] is None
    assert "- Graph: none" in (run_dir / "docs/RUN.md").read_text()
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
    from cbe.graph import graph_quality
    def digest(path: str) -> str:
        return hashlib.sha256((repo / path).read_bytes()).hexdigest()
    value = {"schema": "cbe-graph/1", "backend": {"name": "test", "version": "1"},
             "source_manifest": [{"path": "data/config.json", "sha256": digest("data/config.json")},
                                 {"path": "src/pkg/jobs.py", "sha256": digest("src/pkg/jobs.py")}],
             "nodes": [{"id": "n-jobs", "kind": "function", "path": "src/pkg/jobs.py",
                        "start_line": 1, "end_line": 1, "name": "reserve_run"},
                       {"id": "n-data", "kind": "external", "path": "data/config.json",
                        "start_line": 1, "end_line": 1, "name": "config"}],
             "edges": [], "capabilities": [], "diagnostics": []}
    value["quality"] = graph_quality(value)
    return value


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


def _graph_with_dataflow(graph: dict) -> dict:
    from copy import deepcopy
    from cbe.graph import graph_quality
    value = deepcopy(graph)
    value["nodes"].append({"id": "df-node", "kind": "dataflow_node", "path": "src/pkg/jobs.py",
                           "start_line": 1, "end_line": 1, "name": "value"})
    value["edges"].append({"id": "df-edge", "kind": "dataflow", "source": "df-node",
                           "target": "df-node", "path": "src/pkg/jobs.py", "line": 1})
    value["quality"] = graph_quality(value)
    return value


def test_update_graph_adds_dataflow_without_rerunning_a_complete_run(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    graph = _graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", graph_path=graph_path)["run_dir"])
    _drive(run_dir)
    old_raw = (run_dir / "context.json").read_bytes()
    unchanged = [run_dir / "docs/INDEX.md", run_dir / "docs/DEPENDENCIES.md",
                 *sorted((run_dir / "docs/nodes").glob("*.md"))]
    before = {path: path.read_bytes() for path in unchanged}
    graph_path.write_text(json.dumps(_graph_with_dataflow(graph)), encoding="utf-8")

    assert cli.main(["host", "update-graph", "--run-dir", str(run_dir), "--graph", str(graph_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "updated" and result["old_graph_digest"] != result["new_graph_digest"]
    assert all(path.read_bytes() == raw for path, raw in before.items())
    from cbe.catalog_query import query
    assert [edge["id"] for edge in query(run_dir, "src/pkg/jobs.py", edges="dataflow")["raw_edges"]] == ["df-edge"]
    assert host_run.verify(run_dir)["ok"]
    state = json.loads((run_dir / "host/state.json").read_text())
    assert state["graph_updates"] == [{"at": result["updated_at"],
                                       "old_graph_digest": result["old_graph_digest"],
                                       "new_graph_digest": result["new_graph_digest"]}]
    basis = json.loads((run_dir / "summary.json").read_text())["basis"]
    assert basis["cbe_version"] == state["cbe_version"]
    assert basis["models"] == []  # host tasks have no model records unless exact usage is imported
    source_rows = [{"path": row["path"], "digest": row["digest"]} for row in state["files"]]
    source_digest = hashlib.sha256(json.dumps(
        source_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert basis["source"] == {"files": len(state["files"]), "sha256": source_digest}
    assert basis["graph"] == {"digest": result["new_graph_digest"],
                              "backend": {"name": "test", "version": "1"},
                              "edge_counts": {"dataflow": 1}, "updated": True,
                              "updated_at": result["updated_at"]}
    notes = (run_dir / "docs/RUN.md").read_text()
    assert "## Generation basis" in notes
    assert f"- CBE version: `{state['cbe_version']}`" in notes
    assert "- Models: none recorded" in notes
    assert f"- Source: {len(state['files'])} files · SHA-256 `{source_digest}`" in notes
    assert (f"- Graph: SHA-256 `{result['new_graph_digest']}` · built by `test` 1 · "
            f"edges dataflow=1 · replaced yes, latest {result['updated_at']}") in notes
    verifier = host_run._RunState(state)
    host_run._verified_context(run_dir, verifier)  # the new raw fingerprint is accepted
    verifier["context"]["raw_digest"] = hashlib.sha256(old_raw).hexdigest()
    with pytest.raises(host_run.HostRunError, match="modified after planning"):
        host_run._verified_context(run_dir, verifier)  # the old one no longer is
    assert cli.main(["host", "update-graph", "--run-dir", str(run_dir), "--graph", str(graph_path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "nothing to update"
    # `cbe generate` writes one record per call; its model name is part of the basis
    (run_dir / "raw").mkdir()
    (run_dir / "raw" / "module_1-1.api.json").write_text(json.dumps({"actual_model": "some/model"}))
    host_run.render(run_dir)
    assert json.loads((run_dir / "summary.json").read_text())["basis"]["models"] == ["some/model"]


def _assert_update_refused(run_dir: Path, graph_path: Path, capsys, message: str) -> None:
    files = lambda: {path: path.read_bytes() for path in run_dir.rglob("*")
                     if path.is_file() and path.name != ".lock"}
    before = files()
    assert cli.main(["host", "update-graph", "--run-dir", str(run_dir), "--graph", str(graph_path)]) == 2
    assert capsys.readouterr().err.strip() == message
    assert before == files()


def test_update_graph_leaves_a_usable_run_when_rendering_breaks(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    graph = _graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", graph_path=graph_path)["run_dir"])
    _drive(run_dir)
    graph_path.write_text(json.dumps(_graph_with_dataflow(graph)), encoding="utf-8")

    def broken(*_args, **_kwargs):
        raise RuntimeError("disk full")

    with monkeypatch.context() as patch:
        patch.setattr(host_run, "_render", broken)
        with pytest.raises(RuntimeError, match="disk full"):
            host_run.update_graph(run_dir, graph_path)
    # The new context and its digest were saved together: the run still verifies and renders.
    assert host_run.verify(run_dir)["ok"]
    assert host_run.update_graph(run_dir, graph_path)["status"] == "nothing to update"


def test_update_graph_refuses_an_unfinished_run(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    graph = _graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(_graph_with_dataflow(graph)), encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", graph_path=graph_path)["run_dir"])
    _assert_update_refused(run_dir, graph_path, capsys,
                           "only a completed run with no pending or failed tasks can update its graph")


def test_update_graph_refuses_a_non_dataflow_edge_change(tmp_path: Path, capsys) -> None:
    from copy import deepcopy
    repo = _repo(tmp_path)
    graph = _graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", graph_path=graph_path)["run_dir"])
    _drive(run_dir)
    changed = deepcopy(graph)
    changed["edges"].append({"id": "extra-call", "kind": "call", "source": "n-0", "target": "n-1",
                             "path": "src/pkg/jobs.py", "status": "resolved"})
    graph_path.write_text(json.dumps(changed), encoding="utf-8")
    _assert_update_refused(
        run_dir, graph_path, capsys,
        "the new graph differs from this run's graph in more than dataflow; start a new plan")


def test_update_graph_refuses_a_different_source_manifest(tmp_path: Path, capsys) -> None:
    from copy import deepcopy
    repo = _repo(tmp_path)
    graph = _graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", graph_path=graph_path)["run_dir"])
    _drive(run_dir)
    changed = deepcopy(graph)
    changed["source_manifest"].append({
        "path": "tests/test_jobs.py", "language": "python",
        "sha256": hashlib.sha256((repo / "tests/test_jobs.py").read_bytes()).hexdigest()})
    graph_path.write_text(json.dumps(changed), encoding="utf-8")
    _assert_update_refused(run_dir, graph_path, capsys,
                           "the new graph has a different source_manifest; start a new plan")


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
    notes = (run_dir / "docs" / "RUN.md").read_text()
    assert "Known-empty files" in notes and "tests/__init__.py" in notes


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


def test_tree_waits_for_repairs_so_new_group_units_get_an_owner(tmp_path: Path) -> None:
    """Repairs can add grp: units; the first ownership tree must include them."""
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
            if kind in {"module", "repair"}:
                value = _detail_from_prompt(prompt)
                if kind == "repair":
                    value = _group_first(value, f"extra-{item['task']}")
            elif kind in {"tree_name", "tree_top"}:
                value = _answer({"kind": kind}, prompt)
            elif kind == "review":
                value = {"decision": "needs_repair", "issues": ["group the helper"]}
            else:
                value = {"overview": "A tiny package.", **_system_answer(prompt)}
            Path(item["output_file"]).write_text(json.dumps(value), encoding="utf-8")
            result = host_run.submit(run_dir, item["task"], usage={"total_tokens": 1000})
            assert result["accepted"], result
    assert handed.count("tree_name_1") == 1
    assert all(handed.index(task) < handed.index("tree_name_1")
               for task in handed if task.startswith(("review_", "repair_")))
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"], state["verify"]["checks"]
    with host_run.locked_state(run_dir) as locked:
        tree = host_run._semantic_tree(run_dir, locked)
    owned = {uid for node in tree["nodes"] for uid in node.get("unit_ids") or []}
    assert {"grp:cli.py-extra-repair-1", "grp:test_jobs.py-extra-repair-2"} <= owned


def test_repair_may_reuse_its_own_module_group_ids(tmp_path: Path) -> None:
    """A repair may redefine a ``grp:`` unit its own module already defined.

    That is the same unit being revised, not a cross-batch duplicate. The old
    path-only exclusion kept ``grp:`` ids (which carry no path) in the known
    set and rejected the repair with a false duplicate error."""
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "jobs.py").write_text(
        "def reserve_run(value):\n    if value < 0:\n        raise ValueError('negative')\n    return value\n\n"
        "def release_run(value):\n    return -value\n",
        encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="all", jobs=4)["run_dir"])
    group_id = "grp:jobs.py-helpers"
    repair_seen = False
    for _ in range(40):
        batch = host_run.next_tasks(run_dir)
        if not batch["tasks"]:
            break
        for item in batch["tasks"]:
            prompt = Path(item["prompt_file"]).read_text()
            kind = item["kind"]
            if kind == "module":
                value = _group_first(_detail_from_prompt(prompt), "helpers")
            elif kind == "repair":
                repair_seen = True
                value = _group_first(_detail_from_prompt(prompt), "helpers")
                value["units"][0]["explain"] = "Grouped helpers, revised."
            elif kind in {"tree_name", "tree_top"}:
                value = _answer({"kind": kind}, prompt)
            elif kind == "review":
                value = {"decision": "needs_repair", "issues": ["revise the group"]}
            else:
                value = {"overview": "A tiny package.", **_system_answer(prompt)}
            Path(item["output_file"]).write_text(json.dumps(value), encoding="utf-8")
            result = host_run.submit(run_dir, item["task"], usage={"total_tokens": 1000})
            assert result["accepted"], result
    assert repair_seen
    repaired = json.loads((run_dir / "host" / "accepted" / "repair_1.json").read_text())
    assert group_id in {unit["id"] for unit in repaired["units"]}  # the repair rebuilt its own module's group
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"], state["verify"]["checks"]


def test_empty_module_does_not_shortcut_the_tree_before_real_modules_finish(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "pkg" / "core.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (repo / "tests" / "__init__.py").write_text("", encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=2)["run_dir"])
    host_run.next_tasks(run_dir)  # auto-completes the empty batch, leases the real one
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert not any(task["kind"] in host_run.TREE_KINDS for task in state["tasks"].values())
    assert state["tasks"]["system"]["status"] == "pending"
    assert not (run_dir / "host" / "accepted" / "tree.json").exists()
    host_run.release(run_dir)  # hand the leased task back before driving
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
    assert "Graph access:" not in prompt
    host_run.release(run_dir)
    _drive(run_dir)
    assert not (run_dir / "host/tasks" / f"module_{module['number'] + 1}.graph.txt").exists()
    anchored = next(row for row in state["modules"] if "src/pkg/jobs.py" in row["files"])
    anchored_prompt = host_run.completion_prompt(run_dir, f"module_{anchored['number'] + 1}")
    assert "Batch-internal resolved calls" in anchored_prompt or "Graph: internal=" in anchored_prompt


@pytest.mark.parametrize("tamper", ["whitespace", "value"])
@pytest.mark.parametrize("operation", ["next", "submit", "resume", "render", "prompt", "verify"])
def test_context_rejects_same_size_same_mtime_change(tmp_path, operation, tamper):
    run_dir = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    host_run.next_tasks(run_dir, limit=1)  # exercise an already-used context
    path = run_dir / "context.json"
    raw, stat = path.read_bytes(), path.stat()
    assert raw.endswith(b"\n")
    if tamper == "whitespace":
        changed = raw[:-1] + b" "  # same JSON value, different frozen byte
    else:
        original = b'"text": "from pkg.jobs import reserve_run'
        forged = b'"text": "from pkg.fake import reserve_run'
        assert original in raw
        changed = raw.replace(original, forged, 1)
        assert json.loads(changed) != json.loads(raw)
    path.write_bytes(changed)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert path.stat().st_size == stat.st_size and path.stat().st_mtime_ns == stat.st_mtime_ns
    if operation == "verify":
        report = host_run.verify(run_dir)
        assert any(row["check"] == "frozen_context_intact" and not row["ok"] for row in report["checks"])
        return
    actions = {"next": lambda: host_run.next_tasks(run_dir),
               "submit": lambda: host_run.submit(run_dir, "module_1", error="unused"),
               "resume": lambda: host_run.resume(run_dir),
               "render": lambda: host_run.render(run_dir),
               "prompt": lambda: host_run.completion_prompt(run_dir, "module_1")}
    with pytest.raises(host_run.HostRunError, match="modified after planning"):
        actions[operation]()


def test_context_digest_not_recomputed_and_parsing_is_scoped_to_locked_operation(tmp_path, monkeypatch):
    run_dir = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    raw = (run_dir / "context.json").read_bytes()
    loads, parsed = json.loads, []

    def counting_loads(value, *args, **kwargs):
        if value == raw or value == raw.decode():
            parsed.append(1)
        return loads(value, *args, **kwargs)

    def no_canonical_digest(value):
        pytest.fail("a new run must not recompute its canonical context digest")

    monkeypatch.setattr(json, "loads", counting_loads)
    monkeypatch.setattr(host_run, "context_digest", no_canonical_digest)
    # Multiple detail prompts in one next operation share a parse, but still
    # read/hash the bytes at every boundary. No cache survives the lock.
    with host_run.locked_state(run_dir) as state:
        host_run._verified_context(run_dir, state)
        host_run._verified_context(run_dir, state)
        assert len(parsed) == 1
        path = run_dir / "context.json"
        path.write_bytes(raw[:-1] + b" ")
        with pytest.raises(host_run.HostRunError, match="modified after planning"):
            host_run._verified_context(run_dir, state)
        path.write_bytes(raw)
    host_run.next_tasks(run_dir, limit=1)
    assert len(parsed) == 2
    host_run.submit(run_dir, "module_1", error="test failure")
    host_run.resume(run_dir)
    host_run.render(run_dir)
    host_run.verify(run_dir)


def test_a_run_without_a_byte_digest_asks_for_a_new_plan(tmp_path):
    """State written before the byte freeze has no ``raw_digest``; it is refused, not upgraded."""
    run_dir = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    state_path = run_dir / "host" / "state.json"
    state = json.loads(state_path.read_text())
    state["context"].pop("raw_digest")
    host_run.write_json(state_path, state)
    with pytest.raises(host_run.HostRunError, match="start a new plan"):
        host_run.resume(run_dir)


def test_details_run_in_parallel_and_the_naming_tasks_wait_for_all_of_them(tmp_path):
    run_dir = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none", jobs=8)["run_dir"])
    batch = host_run.next_tasks(run_dir)["tasks"]
    details = [item for item in batch if item["kind"] == "module"]
    state = json.loads((run_dir / "host/state.json").read_text())
    assert len(details) == len(state["modules"]) == len(batch)
    before = {item["task"]: host_run.completion_prompt(run_dir, item["task"]) for item in details}
    for item in details[:-1]:
        _answer_task(run_dir, item, _good(item, run_dir))
    assert host_run.next_tasks(run_dir)["tasks"] == []  # one reading batch is still out
    _answer_task(run_dir, details[-1], _good(details[-1], run_dir))
    for item in details:
        assert host_run.completion_prompt(run_dir, item["task"]).encode() == before[item["task"]].encode()
    assert [item["kind"] for item in host_run.next_tasks(run_dir)["tasks"]] == ["tree_name"]


@pytest.mark.parametrize("accepted_system", [True, False])
def test_resume_new_group_preserves_last_accepted_system(tmp_path, accepted_system):
    run_dir = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none", jobs=8)["run_dir"])
    _drive(run_dir)
    accepted = run_dir / "host/accepted"
    unit_ids = sorted(json.loads((run_dir / "catalog.json").read_text())["units"])
    system_path = accepted / "system.json"
    system = {"overview": "Previously accepted overview.",
              "dependency_descriptions": [],
              "key_flows": [{"name": "Saved flow", "description": "Preserved flow explanation.",
                             "steps": unit_ids[:2]}]}
    if accepted_system:
        system_path.write_text(json.dumps(system))
    else:
        system_path.unlink()
    state_path = run_dir / "host/state.json"
    state = json.loads(state_path.read_text())
    task = state["tasks"]["module_1"]
    task["status"] = "leased"
    state["tasks"]["system"]["covered"] = []
    state_path.write_text(json.dumps(state))
    detail = _group_first(_detail_from_prompt(host_run.completion_prompt(run_dir, "module_1")), "new-helper")
    (run_dir / "host/outbox/module_1.json").write_text(json.dumps(detail))
    assert cli.main(["host", "resume", "--run-dir", str(run_dir)]) == 0
    state = json.loads(state_path.read_text())
    assert state["tasks"]["module_1"]["status"] == "done"
    assert state["tasks"]["system"]["status"] == "pending"
    assert "grp:cli.py-new-helper" in json.loads((run_dir / "catalog.json").read_text())["units"]
    index = (run_dir / "docs/INDEX.md").read_text()
    notes = (run_dir / "docs/RUN.md").read_text()
    if accepted_system:
        assert "Previously accepted overview." in index
        assert "Preserved flow explanation." in index
        assert "The overview was written before some modules finished" in notes
    else:
        assert "The overview is mechanical" in notes
        assert "Previously accepted overview." not in index
        assert "The overview was written before some modules finished" not in notes


def test_plan_covers_every_nonempty_file_byte_for_byte_with_one_inventory(tmp_path: Path) -> None:
    """The coverage guarantee behind the single (grammar) inventory: for any file the
    frozen chunks join back to its bytes, and only a blank file has no inventory id."""
    repo = tmp_path / "repo"
    repo.mkdir()
    sources = {"ok.py": "def f():\r\n    return 1\r\n", "broken.py": "def (:\n  x = \n",
               "doc.py": '"""Only a docstring."""\n', "blank.py": "  \n\n", "empty.py": ""}
    for name, text in sources.items():
        (repo / name).write_bytes(text.encode())
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none")["run_dir"])
    state = json.loads((run_dir / "host" / "state.json").read_text())
    chunks = json.loads((run_dir / "context.json").read_text())["chunks"]
    for name, text in sources.items():
        symbols = state["inventory"][name]["symbols"] if name in state["inventory"] else []
        if text.strip():
            assert symbols, name
            joined = "".join(c["text"] for c in sorted((c for c in chunks if c["path"] == name),
                                                       key=lambda c: c["start_byte"]))
            assert joined == text, name
        else:
            assert symbols == [], name


def test_rendering_a_complete_run_again_keeps_its_wall_time(tmp_path: Path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, review="none", jobs=2, host="test")["run_dir"])
    _drive(run_dir)
    first = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert first["status"] == "complete"
    real_time = host_run.time.time
    monkeypatch.setattr(host_run.time, "time", lambda: real_time() + 5000)
    host_run.render(run_dir)
    again = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert again["wall_seconds"] == first["wall_seconds"]
