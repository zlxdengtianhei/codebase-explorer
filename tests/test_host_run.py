"""Host-agent driven generation: plan, lease, submit, resume, render, verify, cost."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from cbe import cli, host_run
from cbe.generate import find


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


def _answer(task: dict, prompt: str, *, decision: str = "accepted") -> dict:
    """Play the subagent: answer from the instruction file alone."""
    kind = task["kind"]
    if kind == "names":
        rows = json.loads(prompt.split("Modules:\n", 1)[1])
        return {"names": [{"module": row["module"], "title": f"Area {row['module']}"} for row in rows]}
    if kind in {"module", "repair"}:
        symbols = json.loads(re.search(r"Available symbols: (.*)\n", prompt).group(1))
        return {"summary": "Reserves work.", "flow": "Checks input.",
                "test_coverage": "Covers reserve." if "test_jobs.py" in prompt else "",
                "key_behaviors": [{"symbol": name, "behavior": "Does it.", "conditions": "", "failures": ""}
                                  for name in symbols[:1]],
                "uncertainties": []}
    if kind == "review":
        return {"decision": decision, "issues": ["flow omits the negative check"] if decision != "accepted" else []}
    return {"overview": "A tiny job reservation package.", "maintenance_navigation": "Open the jobs page."}


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
    assert "## Subsystems" in index and "](modules/" in index and str(tmp_path) not in index
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
    assert "flow omits the negative check" in repair_prompt


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

    estimate = host_run.cost(run_dir, model="claude-sonnet-5-5")
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
    imported = host_run.import_usage(run_dir, "claude-code", tmp_path / "claude")
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
    assert host_run.import_usage(run_dir, "codex", tmp_path / "codex")["tasks_with_exact_usage"] == 1

    report = host_run.cost(run_dir, model="claude-sonnet-5-5")
    rows = {row["task"]: row for row in report["tasks"]}
    assert report["basis"] == "mixed"
    assert rows["names"]["basis"] == "exact"
    assert rows["names"]["cache_write_tokens"] == 110 and rows["names"]["output_tokens"] == 100
    assert rows["names"]["harness_reported_total_tokens"] == 1000
    assert rows["system"]["cache_read_tokens"] == 600 and rows["system"]["input_tokens"] == 300
    assert rows["system"]["models"] == ["gpt-6.1-sol"]


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


def test_second_overlong_answer_is_normalized_flagged_and_rendered(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=8)["run_dir"])
    names = host_run.next_tasks(run_dir)["tasks"][0]
    _answer_task(run_dir, names, _good(names, run_dir))
    batch = host_run.next_tasks(run_dir)["tasks"]
    long_flow = "Checks the input and reserves a run. " * 80  # about 2900 characters
    target = batch[0]
    for item in batch[1:]:
        _answer_task(run_dir, item, _good(item, run_dir))
    first = _answer_task(run_dir, target, {**_good(target, run_dir), "flow": long_flow})
    assert not first["accepted"] and first["task_status"] == "pending" and "flow" in first["error"]
    again = host_run.next_tasks(run_dir)["tasks"][0]
    assert "at most 2000 characters" in Path(again["prompt_file"]).read_text()
    second = _answer_task(run_dir, again, {**_good(again, run_dir), "flow": long_flow})
    assert second["accepted"] and second["normalized"]
    assert any("flow truncated" in flag for flag in second["flags"])
    accepted = json.loads((run_dir / "host" / "accepted" / f"{target['task']}.json").read_text())
    assert len(accepted["flow"]) <= 2000 and accepted["flow"].endswith("…")
    system = host_run.next_tasks(run_dir)["tasks"][0]
    nav = "Open the jobs page for reservations. " * 200  # far above the scaled cap
    _answer_task(run_dir, system, {"overview": "A tiny package.", "maintenance_navigation": nav})
    _answer_task(run_dir, host_run.next_tasks(run_dir)["tasks"][0],
                 {"overview": "A tiny package.", "maintenance_navigation": nav})
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"]
    index = (run_dir / "docs" / "INDEX.md").read_text()
    assert "## Generation notes" in index and "maintenance_navigation truncated" in index
    pages = "".join(path.read_text() for path in (run_dir / "docs" / "modules").glob("*.md"))
    assert "CBE normalized this page" in pages
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
    assert not checks["all_tasks_done"] and checks["each_file_in_exactly_one_module"] and checks["pages_list_their_files"]
    pages = "".join(path.read_text() for path in (run_dir / "docs" / "modules").glob("*.md"))
    assert "Documentation for this module is pending." in pages
    assert "pending" in (run_dir / "docs" / "INDEX.md").read_text()
    assert find(run_dir, "reserve_run") or find(run_dir, "main")

    resumed = host_run.resume(run_dir, owner="codex")
    assert resumed["retried"] == [broken["task"]] and resumed["status"] == "running"
    _drive(run_dir)
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"]
    assert broken["task"] in [f"module_{n + 1}" for n in state["tasks"]["system"]["covered"]]
    assert "pending" not in (run_dir / "docs" / "INDEX.md").read_text().split("## Subsystems")[0]


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
    assert "generated mechanically" in index and "`system` task is failed" in index
    host_run.retry(run_dir, "system")
    item = host_run.next_tasks(run_dir)["tasks"][0]
    assert item["task"] == "system"
    _answer_task(run_dir, item, _good(item, run_dir))
    state = json.loads((run_dir / "host" / "state.json").read_text())
    assert state["status"] == "complete"
    assert "generated mechanically" not in (run_dir / "docs" / "INDEX.md").read_text()


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
