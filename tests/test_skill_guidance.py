"""The shipped skill's example commands and the output shapes it tells the host agent to read,
checked against the real CLI."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

import pytest

from cbe import cli, host_run, usage
from test_host_run import _answer, _drive, _repo

SKILL_DIR = Path(__file__).resolve().parents[1] / ".dsh/skills/codebase-explorer"
PAGES = [SKILL_DIR / "SKILL.md", SKILL_DIR / "references/claude-code.md", SKILL_DIR / "references/codex.md"]
PLACEHOLDERS = {"RUN": "/abs/run", "ID": "unit-id", "TASK": "module_1", "SEARCH_TERM": "needle"}


def _example_commands() -> list[str]:
    """Commands in sh blocks, plus inline commands that name a run or repository."""
    found = []
    for page in PAGES:
        text = page.read_text(encoding="utf-8")
        for block in re.findall(r"```sh\n(.*?)```", text, re.S):
            for line in re.sub(r"\\\n\s*", " ", block).splitlines():
                if line.strip().startswith("cbe "):
                    found.append(line.strip())
        found += re.findall(r"`(cbe [^`<]*--(?:run-dir|repo)[^`<]*)`", text)
    return found


def test_every_example_command_parses_with_the_real_cli() -> None:
    commands = _example_commands()
    assert {" ".join(c.split()[:3]) for c in commands} >= {
        "cbe host plan", "cbe host next", "cbe host submit", "cbe host import-usage", "cbe host cost",
        "cbe host verify", "cbe host resume", "cbe find --run-dir", "cbe generate ."}
    for line in commands:
        words = [PLACEHOLDERS.get(word, word) for word in shlex.split(line, comments=True)]
        cli.build_parser().parse_args(words[1:])


def test_example_commands_carry_no_quoted_text() -> None:
    """Claude Code asks before running a command whose quoted text it cannot check."""
    for line in _example_commands():
        assert '"' not in line and "'" not in line, line


def test_plan_takes_dot_but_run_lookup_needs_an_absolute_repo(tmp_path: Path, monkeypatch, capsys) -> None:
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo)
    assert cli.main(["host", "plan", ".", "--review", "none", "--jobs", "2", "--host", "claude-code"]) == 0
    planned = json.loads(capsys.readouterr().out)
    assert Path(planned["run_dir"]).is_absolute()
    assert Path(planned["run_dir"]).is_relative_to(repo.resolve())
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["host", "resume", "--repo", "."])
    assert cli.main(["host", "resume", "--repo", str(repo)]) == 0


def test_submit_output_tells_acceptance_from_rejection(tmp_path: Path, capsys) -> None:
    run_dir = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none", jobs=1)["run_dir"])
    names = host_run.next_tasks(run_dir)["tasks"][0]
    Path(names["output_file"]).write_text(
        json.dumps(_answer({"kind": "names"}, Path(names["prompt_file"]).read_text())))
    accepted = host_run.submit(run_dir, "names")
    assert accepted["accepted"] is True and accepted["normalized"] is False and accepted["flags"] == []
    repeated = host_run.submit(run_dir, "names")
    assert repeated["accepted"] is True and repeated["already"] is True
    assert "normalized" not in repeated and "flags" not in repeated

    item = host_run.next_tasks(run_dir)["tasks"][0]
    Path(item["output_file"]).write_text('{"summary": ""}')
    assert cli.main(["host", "submit", "--run-dir", str(run_dir), "--task", item["task"]]) == 0
    rejected = json.loads(capsys.readouterr().out)
    assert rejected["accepted"] is False
    assert rejected["error"].startswith("schema_error") and rejected["task_status"] == "pending"
    assert rejected["attempts"] == 1
    assert "normalized" not in rejected and "flags" not in rejected
    assert "reject" in (run_dir / "progress.log").read_text()

    again = host_run.next_tasks(run_dir)["tasks"]
    assert [row["task"] for row in again] == [item["task"]]
    assert again[0]["description"] == item["description"]
    assert again[0]["dispatch_message"] == item["dispatch_message"]
    assert rejected["error"][:60] in Path(again[0]["prompt_file"]).read_text()


def _transcript(directory: Path, name: str, description: str, output_tokens: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.meta.json").write_text(json.dumps({"description": description}))
    message = {"id": f"m-{name}", "model": "claude-sonnet-5-5", "usage": {
        "input_tokens": 1, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000,
        "output_tokens": output_tokens}}
    (directory / f"{name}.jsonl").write_text(json.dumps({"message": message}) + "\n")


def test_cost_needs_model_only_for_estimated_rows_and_adds_attempts(tmp_path: Path) -> None:
    run_dir = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    _drive(run_dir)
    tag = json.loads((run_dir / "host" / "state.json").read_text())["run_tag"]
    subagents = tmp_path / "claude" / "proj" / "session" / "subagents"
    _transcript(subagents, "agent-a1", f"cbe {tag} names", output_tokens=10)
    _transcript(subagents, "agent-a2", f"cbe {tag} names", output_tokens=30)
    imported = usage.import_usage(run_dir, "claude-code", tmp_path / "claude")
    assert imported["tasks_with_exact_usage"] == 1 and imported["subagent_transcripts"] == 2
    estimated = imported["tasks_without_exact_usage"]
    assert estimated and "names" not in estimated

    plain = usage.cost(run_dir)
    rows = {row["task"]: row for row in plain["tasks"]}
    assert rows["names"]["basis"] == "exact" and rows["names"]["subagents"] == 2
    assert rows["names"]["output_tokens"] == 40 and rows["names"]["usd_api_equivalent"] > 0
    assert all(rows[task]["basis"] == "estimate" and rows[task]["usd_api_equivalent"] is None
               for task in estimated)
    assert plain["totals"]["usd"] is None

    priced = usage.cost(run_dir, model="claude-sonnet-5-5")
    assert all(row["usd_api_equivalent"] > 0 for row in priced["tasks"])
    assert priced["totals"]["usd"] > 0


def _sentences(page: Path) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", " ".join(page.read_text(encoding="utf-8").split()))


def test_pages_never_tell_the_host_to_wait_for_a_notification() -> None:
    """Claude Code delivers a completion notification only to an idle session and starts no new turn for it."""
    for page in PAGES:
        for sentence in _sentences(page):
            if "notification" in sentence.lower():
                assert re.search(r"\b(do not|never)\b", sentence, re.I), (page.name, sentence)


def test_claude_code_page_has_the_host_start_calls_that_return_when_the_subagent_ends() -> None:
    page = (SKILL_DIR / "references/claude-code.md").read_text(encoding="utf-8")
    assert "Do not set the call to run in the background." in page
    assert "returns when its subagent has ended" in page
    assert "Async agent launched" in page
    assert "Submit that task as soon as its hand-back arrives, without the usage flags" in page
    assert "Do not end your turn to wait for the later completion notification" in page
    assert "host status --run-dir RUN` between checks" not in page
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "Never end your turn to wait for a notification" in skill
    assert "Do not wait for usage that arrives later" in skill


def test_claude_code_page_names_the_agent_that_cbe_install_installs() -> None:
    page = (SKILL_DIR / "references/claude-code.md").read_text(encoding="utf-8")
    shipped = {path.stem for path in (SKILL_DIR.parents[1] / "agents").glob("*.md")}
    assert shipped == {"cbe-writer"}
    assert ".claude/agents/cbe-writer.md" in page
    subagent = next(line for line in page.splitlines() if line.startswith("- `subagent_type`"))
    assert "`cbe-writer` once `cbe-install`" in subagent
    assert "`general-purpose`" in subagent
