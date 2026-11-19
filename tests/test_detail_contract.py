"""The detail answer contract: short symbol numbers in, internal units out; gaps re-asked alone;
the provider's rate limit waited out without stopping the run."""
from __future__ import annotations

import importlib
import json
import re

import pytest

from cbe import checks, host_run, symbols
from cbe.api_completion import Completion, _csv_row
from cbe.token_budget import count_text_tokens
from test_generate import _semantic_answer, _tiny_repo
from test_semantic import _inventory

generator = importlib.import_module("cbe.generate")

# Numbers of the hand-written inventory in test_semantic. The two ``reserve`` chunks are one
# symbol (design 2.1: a declaration the grammar cut into parts is one detail), so the table has
# four rows: 1 reserve (both chunks), 2 Pool (class), 3 Pool.submit (method), 4 module top-level.
TABLE = symbols.batch_table(["pkg/jobs.py"], _inventory())
ID = {row["n"]: row["id"] for row in TABLE}


def decode(answer, **kwargs):
    return checks.decode_details(answer, TABLE, **kwargs)


def test_numbers_follow_prompt_order_and_start_at_one() -> None:
    assert [row["n"] for row in TABLE] == [1, 2, 3, 4]
    assert [row["name"] for row in TABLE] == ["reserve", "Pool", "Pool.submit", "<module top-level>"]


def test_the_chunks_of_one_symbol_are_one_row_and_one_detail() -> None:
    # Design 2.1: an overload pair (or a declaration the grammar cut apart) is one symbol, so
    # the model sees one number; the decoder keeps every inventory id that row explains.
    row = TABLE[0]
    assert row["ids"] == ["pkg/jobs.py::reserve", "pkg/jobs.py::reserve@5"]
    out = decode({"units": [{"h": [1], "explain": "Reserves a value, refusing negatives."}]})
    assert out.units[0]["id"] == row["id"] and out.units[0]["kind"] == "function"
    assert out.units[0]["folded"] == ["pkg/jobs.py::reserve@5"]
    payload = checks.assemble_details(TABLE, out.units)
    assert payload["dispositions"]["pkg/jobs.py::reserve@5"] == {"how": "unit", "unit": row["id"]}
    assert checks.find_gaps(TABLE, out.units) == [row for row in TABLE
                                                  if row["kind"] in {"function", "method", "class"}][1:]


def test_the_leftover_regions_of_one_file_are_one_row() -> None:
    # Design 2.1: what a file holds outside its declarations is one file-level entry.
    inventory = {"pkg/x.py": {"tokens": 10, "sha256": "", "nlines": 9, "symbols": [
        {"id": "pkg/x.py::module_residual::::0", "name": "x", "kind": "module_residual", "parent": None,
         "lines": [[1, 2]]},
        {"id": "pkg/x.py::module_residual::::30", "name": "x", "kind": "module_residual", "parent": None,
         "lines": [[5, 6]]},
        {"id": "pkg/x.py::function::run::60", "name": "run", "kind": "function", "parent": None,
         "lines": [[7, 8]]}]}}
    table = symbols.batch_table(["pkg/x.py"], inventory)
    assert [row["ids"] for row in table] == [["pkg/x.py::module_residual::::0",
                                              "pkg/x.py::module_residual::::30"],
                                             ["pkg/x.py::function::run::60"]]
    assert table[0]["kind"] == "module_residual" and table[0]["lines"] == [[1, 2], [5, 6]]


def test_one_number_is_the_symbol_itself_with_the_kind_from_the_inventory() -> None:
    out = decode({"units": [{"h": [2], "explain": "A pool."}, {"h": [4], "explain": "Top level."}]})
    assert [(u["id"], u["kind"]) for u in out.units] == [(ID[2], "class"), (ID[4], "module_region")]
    assert not out.invalid and not out.flags


def test_several_numbers_make_one_group_with_a_generated_id() -> None:
    out = decode({"units": [{"h": [2, 3], "title": "Pool API!", "explain": "The pool."}]})
    group = out.units[0]
    # A group's id is made from its members' symbol names, never a file-stem slug.
    assert group["id"] == "grp:pool-submit" and group["kind"] == "group"
    assert group["members"] == [ID[2], ID[3]]


def test_group_without_title_is_named_after_its_first_member() -> None:
    assert decode({"units": [{"h": [3, 2], "explain": "x."}]}).units[0]["id"] == "grp:pool-submit"


def test_a_group_id_reads_as_names_not_a_file_stem() -> None:
    # Second judge: ``grp:general.ts-debounce-helpers`` is a machine slug. The id is built
    # from the members' names, without a shared prefix that says nothing and without a
    # dangling fragment when it is long.
    def gid(*names: str, known=()):
        return checks._group_id("ignored", [{"name": name} for name in names], set(known))

    assert gid("_CRT_SECURE_NO_DEPRECATE", "true", "false") == "grp:crt-secure-no-deprecate-and-true-and-false"
    assert gid("cJSON_CreateNull", "cJSON_CreateTrue", "cJSON_CreateArray") == \
        "grp:createnull-and-createtrue-and-createarray"
    assert gid("CJSON_PUBLIC", "CJSON_PUBLIC", "CJSON_PUBLIC") == "grp:cjson-public"
    assert gid("CJSON_PUBLIC", "CJSON_PUBLIC", known={"grp:cjson-public"}) == "grp:cjson-public-2"
    long = gid("RolldownChunk", "RolldownCodeChunk", "ChunksByFormat")
    assert long == "grp:rolldownchunk-and-rolldowncodechunk" and not long.endswith("-and")


def test_group_ids_never_collide_with_each_other_or_with_known_units() -> None:
    out = decode({"units": [{"h": [1, 2], "title": "same", "explain": "a."},
                            {"h": [3, 4], "title": "same", "explain": "b."}]},
                 known_ids={"grp:reserve-and-pool"})
    assert [u["id"] for u in out.units] == ["grp:reserve-and-pool-2",
                                            "grp:pool-submit-and-module-top-level"]


def test_unknown_number_is_removed_and_noted_but_the_unit_is_kept() -> None:
    out = decode({"units": [{"h": [2, 99, "x"], "explain": "A pool."}]})
    assert out.units[0]["id"] == ID[2] and not out.invalid
    assert any("99" in flag for flag in out.flags) and any("'x'" in flag for flag in out.flags)


def test_a_number_in_two_units_stays_with_the_first() -> None:
    out = decode({"units": [{"h": [2], "explain": "first."}, {"h": [2, 3], "explain": "second."}]})
    assert [u["id"] for u in out.units] == [ID[2], ID[3]]  # the second unit lost 2, so it is now just symbol 3
    assert out.units[1]["explain"] == "second." and any("already in an earlier unit" in f for f in out.flags)


def test_a_unit_whose_symbols_are_all_taken_is_ignored_not_re_asked() -> None:
    out = decode({"units": [{"h": [2], "explain": "first."}, {"h": [2], "explain": "again."}]})
    assert len(out.units) == 1 and not out.invalid and any("ignored" in flag for flag in out.flags)


@pytest.mark.parametrize("unit,why", [
    ({"h": [2], "explain": "  "}, "empty explain"),
    ({"h": [2]}, "empty explain"),
    ({"h": [], "explain": "x."}, "no symbol number"),
    ({"h": [77], "explain": "x."}, "no symbol number"),
    ({"explain": "x."}, "no symbol number"),
    ("not an object", "not an object"),
])
def test_an_unusable_unit_is_reported_and_the_other_units_are_kept(unit, why) -> None:
    out = decode({"units": [unit, {"h": [3], "explain": "Kept."}]})
    assert [u["id"] for u in out.units] == [ID[3]]
    assert len(out.invalid) == 1 and why in out.invalid[0]["why"]


@pytest.mark.parametrize("answer,message", [("text", "not a JSON object"), ([], "not a JSON object"),
                                            ({}, "no units list"), ({"units": {"h": [1]}}, "no units list")])
def test_only_a_non_object_or_a_missing_units_list_voids_the_whole_answer(answer, message) -> None:
    with pytest.raises(ValueError, match=message):
        decode(answer)


def test_an_empty_units_list_is_a_valid_answer() -> None:
    assert decode({"units": []}).units == []


def test_model_written_relations_are_ignored() -> None:
    # Design 2.1: call edges come from the graph, never from the model.
    out = decode({"units": [{"h": [3], "explain": "Submits.", "relations": [
        {"to": 1, "kind": "call", "basis": "reserve(value)"}]}]})
    assert out.units[0]["relations"] if False else "relations" not in out.units[0]


def test_optional_fields_are_tolerated_and_unknown_fields_ignored() -> None:
    out = decode({"units": [{"h": [1], "explain": "x. " * 400, "summary": ["no"], "id": "invented", "kind": "macro",
                             "extras": [{"topic": ["failure"], "note": " a note "}, {"topic": "failure"}, "junk"],
                             "uncertainties": ["real", 7], "relations": None}], "notes": " n "})
    unit = out.units[0]
    assert unit["id"] == ID[1] and unit["kind"] == "function" and "summary" not in unit  # length is never a failure
    assert unit["extras"] == [{"topic": "failure", "note": "a note"}] and unit["uncertainties"] == ["real"]
    assert out.notes == "n" and not out.invalid


def test_later_answers_add_to_earlier_units_without_repeating_them() -> None:
    first = decode({"units": [{"h": [2], "explain": "pool."}]})
    second = decode({"units": [{"h": [2], "explain": "again."}, {"h": [3], "explain": "submit."}]}, have=first.units)
    assert [u["id"] for u in second.units] == [ID[3]]
    assert checks.covered_ids(first.units + second.units, TABLE) == {ID[2], ID[3]}


def test_every_symbol_gets_a_disposition_written_by_the_program() -> None:
    units = decode({"units": [{"h": [1], "explain": "r."}, {"h": [2, 3], "title": "pool", "explain": "p."}]}).units
    payload = checks.assemble_details(TABLE, units, notes="n")
    d = payload["dispositions"]
    assert set(d) == {sid for row in TABLE for sid in row["ids"]}
    assert d[ID[1]] == {"how": "unit", "unit": ID[1]}
    assert d["pkg/jobs.py::reserve@5"] == {"how": "unit", "unit": ID[1]}
    assert d[ID[2]] == d[ID[3]] == {"how": "grouped", "unit": "grp:pool-submit"}
    assert d[ID[4]] == {"how": "index_only", "unit": None, "reason": "not explained; indexed without prose"}
    assert payload["batch_notes"] == "n" and "batch_notes" not in checks.assemble_details(TABLE, units)


def test_a_grouped_unit_keeps_every_inventory_id_of_the_rows_it_covers() -> None:
    # A grouped unit over a merged row (a declaration in parts) dispositions the parts too.
    out = decode({"units": [{"h": [1, 2], "title": "reserve and pool", "explain": "Both."}]})
    payload = checks.assemble_details(TABLE, out.units)
    assert payload["dispositions"]["pkg/jobs.py::reserve@5"] == {"how": "grouped", "unit": "grp:reserve-and-pool"}
    assert out.units[0]["folded"] == ["pkg/jobs.py::reserve@5"]


def test_an_unexplained_row_still_dispositions_every_id_it_stands_for() -> None:
    # A merged row that no unit explains must not lose its folded inventory ids.
    units = decode({"units": [{"h": [2], "explain": "A pool."}]}).units
    payload = checks.assemble_details(TABLE, units)
    assert payload["dispositions"]["pkg/jobs.py::reserve@5"] == {
        "how": "index_only", "unit": None, "reason": "not explained; indexed without prose"}


def test_gap_guard_flags_every_function_method_and_class() -> None:
    # No size rule: 1 is a function (two chunks), 2 a class, 3 a method. 4 is a module region
    # (imports/constants) and is indexed without prose, like a pure constant.
    assert [row["n"] for row in checks.find_gaps(TABLE, [])] == [1, 2, 3]


def test_gap_guard_ignores_what_a_unit_or_group_already_explains() -> None:
    units = decode({"units": [{"h": [1], "explain": "r."}, {"h": [2, 3, 4], "title": "pool", "explain": "p."}]}).units
    assert checks.find_gaps(TABLE, units) == []


def test_gap_guard_treats_test_files_like_any_other() -> None:
    """Tests carry information too (which behavior is pinned where), so a test function that no
    unit mentions is a gap like any other; one grouped unit closes both."""
    table = symbols.batch_table(["tests/test_x.py"], {"tests/test_x.py": {"symbols": [
        {"id": "tests/test_x.py::test_a", "name": "test_a", "kind": "function", "parent": None, "lines": [[1, 30]]},
        {"id": "tests/test_x.py::test_b", "name": "test_b", "kind": "function", "parent": None, "lines": [[31, 33]]}]}})
    assert [row["name"] for row in checks.find_gaps(table, [])] == ["test_a", "test_b"]
    group = checks.decode_details({"units": [{"h": [1, 2], "title": "x behavior", "explain": "Pins x."}]}, table).units
    assert checks.find_gaps(table, group) == []


def test_the_prompt_asks_for_every_symbol_and_names_grouped_members() -> None:
    from cbe import prompts
    text = prompts.detail_prompt(["pkg/jobs.py"], _inventory())
    assert "Write one detail for every function, method and class" in text
    assert "the sentence must name every symbol it covers" in text
    assert "Do not write call relations" in text
    assert "the tests that pin one behavior" not in text  # no separate test-file rule any more


def _sources(language: str = "python", text: str = "value = compute()\n",
             tokens: int = 60) -> dict[str, dict]:
    """Per-symbol source facts, one shape for every id in the hand-written table."""
    return {sid: {"tokens": tokens, "text": text, "language": language} for sid in ID.values()}


def test_detail_caps_follow_whether_the_source_branches() -> None:
    assert checks.detail_cap("value = compute()\n", "python") == checks.DETAIL_PLAIN_MAX_TOKENS
    for text in ("if value < 0:\n    raise ValueError()\n",
                 "try:\n    x = 1\nexcept OSError:\n    pass\n",
                 "return 1 if ready else 2\n",
                 "match command:\n    case 'x':\n        pass\n",
                 "def run(a, b=1):\n    return a\n"):
        assert checks.detail_cap(text, "python") == checks.DETAIL_MAX_TOKENS, text


def test_a_language_the_program_cannot_read_keeps_the_loose_cap() -> None:
    # No pattern table means the program cannot tell whether the source branches, so it does
    # not hold the answer to the plain cap.
    assert checks.detail_cap("value = compute()\n", "cobol") == checks.DETAIL_MAX_TOKENS
    assert checks.detail_cap("value = compute()\n", "") == checks.DETAIL_MAX_TOKENS


def test_a_branch_other_languages_read_keeps_the_loose_cap_too() -> None:
    assert checks.detail_cap("if err != nil {\n\treturn err\n}\n", "go") == checks.DETAIL_MAX_TOKENS
    assert checks.detail_cap("fn run(x: u8) -> u8 {\n    if x > 0 { x } else { 0 }\n}\n", "rust") == checks.DETAIL_MAX_TOKENS
    assert checks.detail_cap("x = a ? b : c;\n", "javascript") == checks.DETAIL_MAX_TOKENS


def test_cap_details_cuts_a_long_explanation_at_a_sentence_and_counts_it() -> None:
    units = decode({"units": [{"h": [1], "explain": "Reserve a value. " * 40}]}).units
    flags, cut = checks.cap_details(units, _sources(), TABLE)
    assert cut == [units[0]["id"]] and flags and "sentence end" in flags[0]
    assert not units[0]["explain"].endswith("…")
    assert count_text_tokens(units[0]["explain"]) <= checks.DETAIL_PLAIN_MAX_TOKENS


def test_cut_at_sentence_never_leaves_an_ellipsis() -> None:
    cut = checks.cut_at_sentence("One sentence. " * 50, 30)
    assert cut.endswith(".") and "…" not in cut and count_text_tokens(cut) <= 30
    # A single sentence longer than the cap has no complete sentence to keep; it ends at a
    # whole word with a period, still without "…".
    single = checks.cut_at_sentence("word " * 100, 20)
    assert single.endswith(".") and "…" not in single and count_text_tokens(single) <= 20
    assert checks.cut_at_sentence("Short one.", 60) == "Short one."


def test_over_long_units_names_only_the_units_over_their_own_cap() -> None:
    units = decode({"units": [{"h": [1], "explain": "Short."},
                              {"h": [2, 3], "title": "pool",
                               "explain": "Long explanation of a thing. " * 15}]}).units
    over = checks.over_long_units(units, _sources())
    assert [row["id"] for row in over] == [units[1]["id"]]
    assert over[0]["cap"] == checks.DETAIL_PLAIN_MAX_TOKENS
    # A branch in the source raises that unit's cap, and a short answer under it is not flagged.
    assert checks.over_long_units(units, _sources(text="if x:\n    return 1\n")) == []


def test_a_shorter_answer_lands_on_the_unit_it_was_asked_for() -> None:
    units = decode({"units": [{"h": [1], "explain": "Long."},
                              {"h": [2, 3], "title": "pool", "explain": "Also long."}]}).units
    rewrite = decode({"units": [{"h": [2, 3], "title": "pool", "explain": "Keeps the pool."}]}).units
    merged, flags = checks.apply_shortened(units, rewrite)
    assert merged[1]["explain"] == "Keeps the pool." and merged[1]["id"] == units[1]["id"]
    assert merged[0]["explain"] == "Long." and not flags


def test_the_shorten_prompt_carries_only_those_units_and_their_limits() -> None:
    from cbe import prompts
    units = decode({"units": [{"h": [1], "explain": "Reserve a value, refusing negatives."}]}).units
    rows = [row for row in TABLE if row["id"] in checks.covered_ids(units, TABLE) or row["id"] == units[0]["id"]]
    chunks = [{"id": row["id"], "path": row["path"], "language": "python",
               "text": "def reserve(value):\n    return value\n", "start_line": 1, "end_line": 2}
              for row in rows]
    text = prompts.shorten_prompt(rows, units, {units[0]["id"]: 60}, chunks=chunks)
    assert "REWRITE THESE DETAILS SHORTER" in text
    assert "at most 48 tokens (cap 60" in text
    assert "earlier: Reserve a value, refusing negatives." in text
    assert "==== pkg/jobs.py :: reserve ====" in text
    assert "Pool" not in text.split("SOURCE OF THESE SYMBOLS")[1]
    assert "Do NOT drop a condition to save tokens" in text


def test_cap_details_flags_a_grouped_unit_that_does_not_name_a_member() -> None:
    units = decode({"units": [{"h": [1, 2], "title": "x", "explain": "Does something."}]}).units
    flags, _ = checks.cap_details(units, _sources(), TABLE)
    assert any("does not name" in flag for flag in flags)


def test_cap_details_does_not_flag_a_group_that_names_every_member() -> None:
    # The second judge saw this flag on a page that named both members: the old check ran on
    # character-spaced text. A group's cap follows its members' source, too.
    units = decode({"units": [{"h": [1, 2], "title": "x",
                               "explain": "`reserve` returns a value; `Pool` holds the items."}]}).units
    flags, _ = checks.cap_details(units, _sources(), TABLE)
    assert not [flag for flag in flags if "does not name" in flag]


# ------------------------------------------------------------ run level


def test_a_run_with_another_schema_says_to_start_a_new_plan(tmp_path) -> None:
    run = tmp_path / "run"
    host_run.plan(_tiny_repo(tmp_path), run, review="none", driver="script")
    state_path = run / "host" / "state.json"
    state = json.loads(state_path.read_text())
    state["schema"] = "cbe-host-run/2"
    state_path.write_text(json.dumps(state))
    with pytest.raises(host_run.HostRunError, match="^this run directory was made by a different version of cbe; start a new plan$"):
        host_run.next_tasks(run)
    with pytest.raises(host_run.HostRunError, match="^this run directory was made by a different version of cbe; start a new plan$"):
        host_run.resume(run)


def test_old_format_answers_are_not_accepted(tmp_path, monkeypatch) -> None:
    """A full-id answer with dispositions has no ``h``: its units are rejected, so the symbols
    with logic are gaps and nothing is published."""
    run = tmp_path / "run"
    host_run.plan(_tiny_repo(tmp_path), run, review="none", jobs=1, driver="script")
    state = json.loads((run / "host" / "state.json").read_text())
    ids = symbols.inventory_ids(state["inventory"])
    old = {"units": [{"id": i, "kind": "function", "explain": "x."} for i in ids],
           "dispositions": {i: {"how": "unit", "unit": i} for i in ids}, "batch_notes": "n"}
    item = host_run.next_tasks(run, limit=1)["tasks"][0]
    path = run / "host" / "outbox" / f"{item['task']}.json"
    path.write_text(json.dumps(old))
    result = host_run.submit(run, item["task"])
    assert not result["accepted"] and not (run / "host" / "accepted" / f"{item['task']}.json").exists()


def _model(monkeypatch, behave):
    """Script the model: ``behave(task, attempt, prompt)`` returns a value, or an error string."""
    calls: list[tuple[str, int]] = []

    def fake(**kw):
        calls.append((kw["task"], kw["attempt"]))
        outcome = behave(kw["task"], kw["attempt"], kw["prompt"])
        error = outcome if isinstance(outcome, str) else None
        value = None if error else outcome
        _csv_row(kw["csv_path"], {"task": kw["task"], "attempt": kw["attempt"], "input_tokens": 5000,
                                  "output_tokens": 2, "cache_tokens": 0, "result": error or "ok", "seconds": .01})
        return Completion(value, error, json.dumps(value) if value else "", None if error else
                          {"input": 5000, "output": 2, "cache": 0}, .01)

    monkeypatch.setattr(generator, "invoke", fake)
    monkeypatch.setattr(generator, "LIMIT_PAUSE_SECONDS", 0.5)
    pauses: list[float] = []
    monkeypatch.setattr(generator, "_sleep", pauses.append)
    return calls, pauses


def test_a_provider_limit_returns_the_task_to_the_queue_and_the_run_goes_on(tmp_path, monkeypatch) -> None:
    refused: set[str] = set()

    def behave(task, attempt, prompt):
        if task == "module_1" and not refused:
            refused.add(task)
            return "provider_limit"
        return _semantic_answer(prompt)

    calls, pauses = _model(monkeypatch, behave)
    result = generator.generate(_tiny_repo(tmp_path), tmp_path / "run", model="m", review="none", jobs=1)
    assert result["status"] == "complete" and result["stopped"] is None
    assert pauses and pauses[0] <= 0.5  # the run paused once before going on
    state = json.loads((tmp_path / "run" / "host" / "state.json").read_text())
    assert state["tasks"]["module_1"]["attempts"] == 1  # the refused call used no answer attempt
    assert calls.count(("module_1", 1)) == 2  # asked twice as attempt 1


def test_the_run_stops_only_after_three_refusals_in_a_row(tmp_path, monkeypatch) -> None:
    calls, _ = _model(monkeypatch, lambda task, attempt, prompt: "provider_limit")
    result = generator.generate(_tiny_repo(tmp_path), tmp_path / "run", model="m", review="none", jobs=1)
    assert result["stopped"] == "provider_limit" and result["status"] != "complete"
    assert len(calls) == generator.LIMIT_STREAK_STOP
    state = json.loads((tmp_path / "run" / "host" / "state.json").read_text())
    assert all(task["attempts"] == 0 and task["status"] == "pending" for task in state["tasks"].values())


def test_a_response_between_refusals_restarts_the_count(tmp_path, monkeypatch) -> None:
    seen: list[str] = []

    def behave(task, attempt, prompt):
        seen.append(task)
        if len(seen) % 3 != 0:  # two refusals, one answer, and so on
            return "provider_limit"
        return _semantic_answer(prompt)

    _model(monkeypatch, behave)
    result = generator.generate(_tiny_repo(tmp_path), tmp_path / "run", model="m", review="none", jobs=1)
    assert result["status"] == "complete" and result["stopped"] is None


def test_a_rejected_unit_alone_costs_no_re_ask_but_is_flagged(tmp_path, monkeypatch) -> None:
    """A stray non-object in the units list names no symbol: nothing is lost, so the answer is
    accepted at once and the junk is recorded in the task's flags."""
    def behave(task, attempt, prompt):
        answer = _semantic_answer(prompt)
        if task == "module_1":
            answer["units"].insert(0, "stray text")
        return answer

    calls, _ = _model(monkeypatch, behave)
    result = generator.generate(_tiny_repo(tmp_path), tmp_path / "run", model="m", review="none", jobs=1)
    assert result["status"] == "complete" and calls.count(("module_1", 1)) == 1 and ("module_1", 2) not in calls
    state = json.loads((tmp_path / "run" / "host" / "state.json").read_text())
    assert any("not an object" in flag for flag in state["tasks"]["module_1"]["flags"])


def test_an_answer_with_a_gap_is_marked_incomplete_in_calls_csv(tmp_path, monkeypatch) -> None:
    import csv

    def behave(task, attempt, prompt):
        answer = _semantic_answer(prompt)
        if task == "module_1" and attempt == 1:
            answer["units"] = [u for u in answer["units"] if not u["explain"].startswith("Unit reserve_run")]
        return answer

    _model(monkeypatch, behave)
    result = generator.generate(_tiny_repo(tmp_path), tmp_path / "run", model="m", review="none", jobs=1)
    assert result["status"] == "complete"
    with (tmp_path / "run" / "calls.csv").open(newline="", encoding="utf-8") as stream:
        rows = [(r["task"], r["attempt"], r["result"]) for r in csv.DictReader(stream) if r["task"] == "module_1"]
    assert rows == [("module_1", "1", "incomplete"), ("module_1", "2", "ok")]


# ------------------------------------------------- length: re-ask once, then cut


def test_a_too_long_explanation_is_asked_again_once_with_only_that_unit(tmp_path, monkeypatch) -> None:
    long_tasks: set[str] = set()
    shorten_prompts: list[str] = []

    def behave(task, attempt, prompt):
        if "REWRITE THESE DETAILS SHORTER" in prompt:
            shorten_prompts.append(prompt)
            numbers = re.findall(r"h=(\d+)", prompt)
            return {"units": [{"h": [int(number)], "explain": "Does the job."} for number in numbers]}
        value = _semantic_answer(prompt)
        if task.startswith("module_") and task not in long_tasks:
            long_tasks.add(task)
            return {"units": [{"h": unit["h"], "explain": "It does the job. " * 40} for unit in value["units"]]}
        return value

    _model(monkeypatch, behave)
    result = generator.generate(_tiny_repo(tmp_path), tmp_path / "run", model="m", review="none", jobs=1)
    assert result["status"] == "complete"
    assert result["explain_length"]["asked_again"] == len(long_tasks) == len(shorten_prompts)
    assert result["explain_length"]["units_asked_again"] >= len(shorten_prompts)
    assert result["explain_length"]["truncated"] == 0
    assert all("SYMBOLS (this batch" not in prompt for prompt in shorten_prompts)
    assert all("Does the job" not in prompt for prompt in shorten_prompts)  # the earlier detail is shown
    run_md = (tmp_path / "run" / "docs" / "RUN.md").read_text(encoding="utf-8")
    assert "sent back once for a shorter one that keeps the conditions" in run_md
    summary = json.loads((tmp_path / "run" / "summary.json").read_text(encoding="utf-8"))
    assert summary["explain_length"]["asked_again"] == len(long_tasks)


def test_a_shorter_answer_that_still_does_not_fit_is_cut_and_not_asked_twice(tmp_path, monkeypatch) -> None:
    asked: set[str] = set()

    def behave(task, attempt, prompt):
        if "REWRITE THESE DETAILS SHORTER" in prompt:
            numbers = re.findall(r"h=(\d+)", prompt)
            return {"units": [{"h": [int(number)], "explain": "Still far too long. " * 40}
                              for number in numbers]}
        value = _semantic_answer(prompt)
        if task.startswith("module_") and task not in asked:
            asked.add(task)
            return {"units": [{"h": unit["h"], "explain": "It does the job. " * 40} for unit in value["units"]]}
        return value

    _model(monkeypatch, behave)
    result = generator.generate(_tiny_repo(tmp_path), tmp_path / "run", model="m", review="none", jobs=1)
    assert result["status"] == "complete"
    assert result["explain_length"]["asked_again"] == len(asked)  # one re-ask per task, never two
    assert result["explain_length"]["truncated"] >= 1
    for page in (tmp_path / "run" / "docs" / "nodes").glob("*.md"):
        assert "…" not in page.read_text(encoding="utf-8"), page.name


def test_the_shorten_prompt_names_the_symbols_a_group_must_keep() -> None:
    from cbe import prompts
    units = decode({"units": [{"h": [2, 3], "title": "pool", "explain": "Also long."}]}).units
    rows = [row for row in TABLE if row["id"] in units[0]["members"]]
    chunks = [{"id": row["id"], "path": row["path"], "language": "python",
               "text": "def submit(self):\n    return 1\n", "start_line": 1, "end_line": 2}
              for row in rows]
    text = prompts.shorten_prompt(rows, units, {units[0]["id"]: 100}, chunks=chunks)
    assert "the rewrite must name each one: `Pool`, `Pool.submit`" in text


def test_the_shorten_prompt_for_a_host_agent_lists_files_and_spans() -> None:
    from pathlib import Path
    from cbe import prompts
    units = decode({"units": [{"h": [1], "explain": "Long."}]}).units
    rows = [row for row in TABLE if row["id"] == units[0]["id"]]
    chunks = [{"id": row["id"], "path": row["path"], "language": "python", "text": "x = 1\n",
               "start_line": 3, "end_line": 9} for row in rows]
    text = prompts.shorten_prompt(rows, units, {units[0]["id"]: 60}, chunks=chunks,
                                 source_root=Path("/repo"), embed=False)
    assert "SOURCE FILES AND LINES (read only these spans):" in text
    assert "- /repo/pkg/jobs.py (L3-L9)" in text
    assert "SOURCE OF THESE SYMBOLS" not in text
