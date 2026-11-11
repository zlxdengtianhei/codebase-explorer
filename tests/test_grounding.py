"""Identifier grounding at detail-answer settlement and in published output."""
from __future__ import annotations

import json
from pathlib import Path

from cbe import catalog_query, grounding, host_run
from test_host_run import _answer_task, _drive, _good


GO_SOURCE = "func (p Point) Sum() int { return p.X + p.Y }"


def test_repo_names_uses_valid_final_dotted_segments() -> None:
    assert grounding.repo_names(["pkg.Point.Sum", "bad-name", "", None]) == frozenset({"Sum"})


def test_go_value_receiver_examples() -> None:
    names = grounding.repo_names(["helper", "Point", "Sum"])
    assert grounding.ungrounded(
        "helper is an object method returning the constant 1.", GO_SOURCE, names) == ["helper"]
    assert grounding.ungrounded(
        "Value-receiver method on Point returning the sum of the struct's X and Y fields.",
        GO_SOURCE, names) == []


def test_grounding_needs_a_mention_and_accepts_one_grounded_name() -> None:
    assert grounding.ungrounded("Ordinary prose only.", "def alpha(): pass", frozenset()) == []
    assert grounding.ungrounded("missing_name calls alpha().", "def alpha(): pass",
                                grounding.repo_names(["alpha"])) == []


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "jobs.py").write_text(
        "def alpha():\n    return 1\n\n"
        "def beta():\n    return 2\n\n"
        "def gamma():\n    return 3\n", encoding="utf-8")
    return repo


def _start(tmp_path: Path):
    run = tmp_path / "run"
    host_run.plan(_repo(tmp_path), run, review="none", jobs=1)
    return run, host_run.next_tasks(run)["tasks"][0]


def test_one_ungrounded_unit_alone_is_accepted_without_a_mark(tmp_path: Path) -> None:
    run, item = _start(tmp_path)
    answer = _good(item, run)
    answer["units"][1]["explain"] = "Unit missing_name does its job."
    result = _answer_task(run, item, answer)
    assert result["accepted"] and not [flag for flag in result["flags"] if flag.startswith("ungrounded")]
    accepted = json.loads((run / "host" / "accepted" / f"{item['task']}.json").read_text())
    assert len(accepted["units"]) == 3 and not any("ungrounded" in unit for unit in accepted["units"])


def test_ungrounded_batch_discards_all_of_this_answer(tmp_path: Path) -> None:
    run, item = _start(tmp_path)
    answer = _good(item, run)
    for unit, name in zip(answer["units"], ("missing_name", "other_name", "third_name")):
        unit["explain"] = f"Unit {name} does its job."
    result = _answer_task(run, item, answer)
    assert not result["accepted"] and result["error"].startswith("ungrounded: 3 explanation(s)")
    assert "look attached to other numbers" in result["error"]
    partial = json.loads((run / "host" / "partial" / f"{item['task']}.json").read_text())
    assert partial["units"] == [] and len(partial["invalid"]) == 3
    again = host_run.next_tasks(run)["tasks"][0]
    prompt = Path(again["prompt_file"]).read_text()
    assert "Your last answer could not be used: ungrounded: 3 explanation(s)" in prompt
    assert "names missing_name, not found in the source under these numbers" in prompt
    assert _answer_task(run, again, _good(again, run))["accepted"]


def test_an_answer_still_ungrounded_at_the_last_attempt_is_kept_marked_and_visible(tmp_path: Path) -> None:
    run, item = _start(tmp_path)
    for attempt in range(host_run.DETAIL_MAX_ATTEMPTS):
        answer = _good(item, run)
        for unit, name in zip(answer["units"], ("missing_name", "other_name", "third_name")):
            unit["explain"] = f"Unit {name} does its job."
        result = _answer_task(run, item, answer)
        if attempt < host_run.DETAIL_MAX_ATTEMPTS - 1:
            assert not result["accepted"]
            item = host_run.next_tasks(run)["tasks"][0]
    assert result["accepted"]
    assert len([flag for flag in result["flags"] if flag.startswith("ungrounded: ")]) == 3
    accepted = json.loads((run / "host" / "accepted" / f"{item['task']}.json").read_text())
    marked = next(unit for unit in accepted["units"] if unit.get("ungrounded") == ["missing_name"])

    _drive(run)
    catalog = json.loads((run / "catalog.json").read_text())
    assert catalog["units"][marked["id"]]["ungrounded"] == ["missing_name"]
    line = "check: names missing_name, not found in this unit's source"
    assert line in catalog_query.query_text(catalog_query.query(run, marked["id"]))
    pages = "".join(path.read_text() for path in (run / "docs" / "nodes").glob("*.md"))
    assert line in pages
    assert json.loads((run / "summary.json").read_text())["ungrounded_count"] == 3
