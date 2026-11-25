"""Long files: a file over the read limit is read in parts, each part within the limit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_host_run import _drive

from cbe import host_run, parts, records
from cbe.catalog_query import find
from cbe.generate import _verify_embedded_source
from cbe.token_budget import count_text_tokens

LIMIT = 2_000


def _function(index: int, lines: int = 12) -> str:
    body = "\n".join(f"    value_{index}_{n} = compute_{index}(value, {n}) + {n * 7}" for n in range(lines))
    return f"def handler_{index}(value):\n{body}\n    return value\n\n"


def _long_repo(tmp_path: Path, functions: int = 40, extra: str = "") -> Path:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    source = "import os\n\nLIMIT = 3\n\n" + "".join(_function(i) for i in range(functions)) + extra
    (repo / "pkg" / "big.py").write_text(source, encoding="utf-8")
    (repo / "pkg" / "small.py").write_text("def tiny():\n    return 1\n", encoding="utf-8")
    return repo


def _plan(repo: Path, run_dir: Path, limit: int = LIMIT) -> dict:
    host_run.plan(repo, run_dir, review="none", host="test", driver="script",
                  batch_target_tokens=limit * 4 // 5, batch_max_tokens=limit)
    return json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))


def _part_modules(state: dict) -> list[dict]:
    return [row for row in state["modules"] if "part" in row]


def test_even_groups_fit_the_budget_stay_even_and_repeat() -> None:
    costs = [300, 120, 80, 500, 40, 40, 900, 60, 60, 60, 410, 25]
    groups = parts.even_groups(costs, 1000)
    assert [i for group in groups for i in group] == list(range(len(costs)))
    assert all(sum(costs[i] for i in group) <= 1000 for group in groups)
    assert len(groups) == 3
    even = parts.even_groups([90] * 20, 1000)  # 1,800 tokens: two equal halves, not 1,000 and 800
    assert [len(group) for group in even] == [10, 10]
    assert groups == parts.even_groups(costs, 1000)
    assert parts.even_groups([50], 1000) == [[0]] and parts.even_groups([], 1000) == []
    assert parts.even_groups([1500, 10], 1000) == [[0], [1]]  # a lone piece over the budget stays whole


def test_a_file_over_the_limit_is_read_in_parts_that_each_fit(tmp_path: Path) -> None:
    repo = _long_repo(tmp_path)
    state = _plan(repo, tmp_path / "run")
    cut = _part_modules(state)
    assert len(cut) >= 3 and [row["part"]["index"] for row in cut] == list(range(1, len(cut) + 1))
    assert {row["part"]["count"] for row in cut} == {len(cut)}
    assert all(row["part"]["tokens"] <= LIMIT for row in cut)
    # Each part's real input (source text with headers, plus its note) is within the limit.
    context = json.loads((tmp_path / "run" / "context.json").read_text(encoding="utf-8"))
    for row in cut:
        part = row["part"]
        real = count_text_tokens(parts.source_text("pkg/big.py", context["chunks"], set(part["ids"]))
                                 + part["note"])
        assert real == part["tokens"] <= LIMIT
        assert f"PART {part['index']} OF {part['count']}" in part["note"]
    # Every inventory id of the file is in exactly one part; a function is never split.
    ids = [sid for row in cut for sid in row["part"]["ids"]]
    assert sorted(ids) == sorted(s["id"] for s in state["inventory"]["pkg/big.py"]["symbols"])
    for index in range(40):
        owners = [row["number"] for row in cut for sid in row["part"]["ids"] if f"::handler_{index}::" in sid]
        assert len(owners) == 1
    # The small file is its own batch without a part; the numbering is continuous.
    assert [row["number"] for row in state["modules"]] == list(range(len(state["modules"])))
    assert any(row["files"] == ["pkg/small.py"] and "part" not in row for row in state["modules"])


def test_the_same_input_gives_the_same_parts(tmp_path: Path) -> None:
    repo = _long_repo(tmp_path)
    first = _plan(repo, tmp_path / "one")
    second = _plan(repo, tmp_path / "two")
    assert first["modules"] == second["modules"]
    assert first["inventory"] == second["inventory"]


def test_a_file_within_the_limit_is_one_batch_as_before(tmp_path: Path) -> None:
    repo = _long_repo(tmp_path, functions=6)
    text = (repo / "pkg" / "big.py").read_text(encoding="utf-8")
    exact = count_text_tokens(text)
    state = _plan(repo, tmp_path / "run", limit=exact)  # exactly at the limit: no cut
    assert not _part_modules(state)
    script, _ = host_run.completion_prompt(tmp_path / "run", "module_1")
    assert "==== FILE pkg/big.py ====" in script and "PART " not in script and text in script
    state = _plan(repo, tmp_path / "run2", limit=exact - 1)  # one token over: cut
    assert len(_part_modules(state)) >= 2


def test_a_unit_over_the_limit_is_cut_by_lines_into_named_pieces(tmp_path: Path) -> None:
    repo = _long_repo(tmp_path, functions=3, extra=_function(99, lines=400))
    run_dir = tmp_path / "run"
    state = _plan(repo, run_dir)
    names = [s["name"] for s in state["inventory"]["pkg/big.py"]["symbols"]]
    pieces = sorted(name for name in names if name.startswith("handler_99 (part "))
    count = len(pieces)
    assert count >= 3 and pieces == sorted(f"handler_99 (part {k} of {count})" for k in range(1, count + 1))
    assert all(row["part"]["tokens"] <= LIMIT for row in _part_modules(state))
    # The pieces are exclusive slices: the frozen file reassembles byte for byte.
    context = host_run._verified_context(run_dir, state)
    assert records.frozen_sources(context, ["pkg/big.py"])["pkg/big.py"] == (
        repo / "pkg" / "big.py").read_text(encoding="utf-8")
    slices = [c for c in context["chunks"] if c["id"].startswith("pkg/big.py::function::handler_99")]
    assert [c["end_byte"] for c in slices[:-1]] == [c["start_byte"] for c in slices[1:]]
    assert all(a["end_line"] < b["start_line"] for a, b in zip(slices, slices[1:]))


def test_one_line_over_the_limit_is_cut_in_character_spans(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    blob = ", ".join(f"'item-{n}-{n * 31 % 97}'" for n in range(1_800))
    (repo / "data.py").write_text(f"DATA = [{blob}]\n\ndef first():\n    return DATA[0]\n", encoding="utf-8")
    state = _plan(repo, tmp_path / "run")
    cut = _part_modules(state)
    assert len(cut) >= 2 and all(row["part"]["tokens"] <= LIMIT for row in cut)
    context = host_run._verified_context(tmp_path / "run", state)
    assert records.frozen_sources(context, ["data.py"])["data.py"] == (repo / "data.py").read_text(encoding="utf-8")


def test_script_prompt_carries_the_note_and_only_its_parts_source(tmp_path: Path) -> None:
    repo = _long_repo(tmp_path)
    run_dir = tmp_path / "run"
    state = _plan(repo, run_dir)
    cut = _part_modules(state)
    context = json.loads((run_dir / "context.json").read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in context["chunks"]}
    for row in cut:
        script, source_tokens = host_run.completion_prompt(run_dir, f"module_{row['number'] + 1}")
        assert row["part"]["note"].rstrip("\n") in script
        assert f"(part {row['part']['index']} of {row['part']['count']}, " in script
        mine = set(row["part"]["ids"])
        assert all(by_id[sid]["text"] in script for sid in mine)
        assert all(c["text"] not in script for c in context["chunks"]
                   if c["id"] not in mine and c["path"] == "pkg/big.py" and c["text"].strip()
                   and c["kind"] == "function")
        assert source_tokens == count_text_tokens(parts.source_text("pkg/big.py", context["chunks"], mine))
        _verify_embedded_source(run_dir, f"module_{row['number'] + 1}", script, source_tokens)
    # A prompt that lacks a chunk of its part is refused before the model is called.
    first = cut[0]
    script, source_tokens = host_run.completion_prompt(run_dir, f"module_{first['number'] + 1}")
    lost = next(by_id[sid] for sid in first["part"]["ids"] if by_id[sid]["kind"] == "function")
    with pytest.raises(Exception, match="lacks"):
        _verify_embedded_source(run_dir, f"module_{first['number'] + 1}", script.replace(lost["text"], ""),
                                source_tokens)


def test_a_run_over_a_long_file_renders_verifies_and_explains_each_unit_once(tmp_path: Path) -> None:
    repo = _long_repo(tmp_path, functions=30, extra=_function(99, lines=400))  # one unit is itself over
    run_dir = tmp_path / "run"
    host_run.plan(repo, run_dir, review="none", host="test", batch_target_tokens=1600, batch_max_tokens=LIMIT)
    _drive(run_dir)
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    assert state["status"] == "complete" and state["verify"]["ok"], state["verify"]
    assert host_run.verify(run_dir)["ok"]
    catalog = json.loads((run_dir / "catalog.json").read_text(encoding="utf-8"))
    covered: dict[str, int] = {}
    wholes = [unit for uid, unit in catalog["units"].items() if uid.endswith("-whole")]
    for unit in catalog["units"].values():
        if unit in wholes:  # the whole of a cut unit repeats its pieces as members; they stay explained once
            continue
        for sid in [unit["id"], *(unit.get("members") or []), *(unit.get("folded_members") or [])]:
            covered[sid] = covered.get(sid, 0) + 1
    functions = [s["id"] for s in state["inventory"]["pkg/big.py"]["symbols"] if s["kind"] == "function"]
    pieces = [s["name"] for s in state["inventory"]["pkg/big.py"]["symbols"] if s["name"].startswith("handler_99 (")]
    assert len(functions) == 30 + len(pieces) and len(pieces) >= 3
    assert all(covered.get(sid) == 1 for sid in functions)
    assert len(wholes) == 1 and wholes[0]["id"] == "grp:handler-99-whole"
    assert wholes[0]["explain"] == "The whole unit does what its pieces do together."
    assert len(wholes[0]["members"]) == len(pieces)
    assert find(run_dir, "handler_17") and find(run_dir, "handler_99 (part 2")


def test_a_host_task_lists_only_the_spans_of_its_part(tmp_path: Path) -> None:
    repo = _long_repo(tmp_path)
    run_dir = tmp_path / "run"
    host_run.plan(repo, run_dir, review="none", host="test", batch_target_tokens=1600, batch_max_tokens=LIMIT)
    item = host_run.next_tasks(run_dir)["tasks"][0]
    prompt = Path(item["prompt_file"]).read_text(encoding="utf-8")
    assert "PART 1 OF" in prompt and "read only the listed line spans, not the whole file" in prompt
    assert prompt.startswith("# Codebase Explorer task `module_1`") and "Read only the listed line spans" in prompt
    assert "completely" not in prompt.split("When you are done", 1)[0]


def test_a_unit_made_of_several_slices_goes_into_one_part_whole(tmp_path: Path) -> None:
    """The grammar cuts a declaration over 32 KB into slices; they are one unit and stay together."""
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    source = "".join(_function(i) for i in range(30)) + _function(7777, lines=800) + _function(31)
    (repo / "pkg" / "big.py").write_text(source, encoding="utf-8")
    limit = 20_000
    assert count_text_tokens(source) > limit
    state = _plan(repo, tmp_path / "run", limit=limit)
    cut = _part_modules(state)
    slices = [s["id"] for s in state["inventory"]["pkg/big.py"]["symbols"] if "handler_7777" in s["id"]]
    assert len(slices) >= 2 and all("::s" in sid or "::function::handler_7777" in sid for sid in slices)
    assert len(cut) >= 2
    owners = {row["number"] for row in cut for sid in row["part"]["ids"] if sid in slices}
    assert len(owners) == 1
    assert not [s for s in state["inventory"]["pkg/big.py"]["symbols"] if "(part" in s["name"]]
