"""The film's script is assembled from the map by the program: order, wording, and the cut to length.

Nothing here calls a model or renders a slide; these are the rules the planner promises.
"""

from __future__ import annotations

import json

import pytest

from cbe import video


def _unit(kind: str, explain: str, node: str) -> dict:
    return {"kind": kind, "explain": explain, "summary": explain, "node": node}


def _catalog() -> dict:
    nodes = {
        "demo": {"parent": None, "children": ["core", "tools"], "title": "demo", "unit_ids": [],
                 "capability": "",
                 "summary": "demo is a small reservation service for a bike shop: it takes a booking "
                            "and tells the counter which bike to hand out. The two parts split the work."},
        "core": {"parent": "demo", "children": ["core-booking", "core-billing"], "title": "Core",
                 "unit_ids": [], "capability": "Hands out bikes and takes the money.",
                 "summary": "Come here to read the booking flow first."},
        "core-booking": {"parent": "core", "children": [], "title": "Booking (1)",
                         "unit_ids": ["src/book.ts::function::book::10", "src/book.ts::function::book::90",
                                      "src/book.ts::module_region::HOURS::400"],
                         "capability": "Books a bike for a start and end time.",
                         "summary": "Come here to book a bike."},
        "core-billing": {"parent": "core", "children": [], "title": "Billing (1)",
                         "unit_ids": ["src/bill.ts::function::charge::20",
                                      "src/bill.ts::function::refund::120"],
                         "capability": "Charges and refunds a deposit.", "summary": ""},
        "tools": {"parent": "demo", "children": ["tools-cli"], "title": "Tools", "unit_ids": [],
                  "capability": "Runs the counter's small commands.", "summary": ""},
        "tools-cli": {"parent": "tools", "children": [], "title": "CLI (1)",
                      "unit_ids": ["src/cli.ts::function::parseArgs::30"],
                      "capability": "Reads the command line.", "summary": ""},
    }
    units = {
        "src/book.ts::function::book::10": _unit(
            "function", "`book` accepts a single request and writes one row.", "core-booking"),
        "src/book.ts::function::book::90": _unit(
            "function", "`book` checks the request against the fleet, marks the bike for the whole "
                        "interval, writes the row and returns its id; it throws when no bike is free.",
            "core-booking"),
        "src/book.ts::module_region::HOURS::400": _unit(
            "module_region", "`HOURS` holds the opening hours.", "core-booking"),
        "src/bill.ts::function::charge::20": _unit(
            "function", "`charge` takes the deposit through the payment provider.", "core-billing"),
        "src/bill.ts::function::refund::120": _unit(
            "function", "`refund` returns the deposit after the bike comes back.", "core-billing"),
        "src/cli.ts::function::parseArgs::30": _unit(
            "function", "`parseArgs` reads `argv` and returns the options object.", "tools-cli"),
    }
    return {
        "schema": "cbe-semantic/1", "project": "Codebase Explorer",
        "files": {"src/book.ts": {"tokens": 900}, "src/bill.ts": {"tokens": 400},
                  "src/cli.ts": {"tokens": 200}},
        "nodes": nodes, "units": units, "edges": {},
        "short_names": {"src/book.ts::function::book::10": "src/book.ts:book",
                        "src/book.ts::function::book::90": "src/book.ts:book (1)"},
        "symbols": {},
    }


def _run(tmp_path):
    run = tmp_path / "run"
    run.mkdir(exist_ok=True)
    (run / "catalog.json").write_text(json.dumps(_catalog()), encoding="utf-8")
    return run


def test_script_follows_the_reading_order(tmp_path) -> None:
    plan = video.build_plan(_run(tmp_path), seconds=10_000)
    kinds = [item["slide"]["kind"] for item in plan["items"]]
    assert kinds[0] == "title"
    assert kinds[-1] == "closing"
    assert kinds[1] == "map" and kinds.count("map") == 3      # the headline plus two systems
    titles = [system["title"] for system in plan["systems"]]
    assert titles == ["Core", "Tools"]
    assert kinds[kinds.index("module")] == "module"
    # systems in tree order, each said once, in the order the entry page lists them
    says = [item["say"] for item in plan["items"] if item["slide"]["kind"] == "map"]
    assert says[0] == "The map has 2 parts."
    assert says[1].startswith("Core. Hands out bikes")


def test_modules_go_down_to_functions_one_per_symbol(tmp_path) -> None:
    plan = video.build_plan(_run(tmp_path), seconds=10_000)
    first = plan["modules"][0]
    assert first["title"] == "Booking (1)"                     # the module with more units comes first
    names = [function["name"] for function in first["functions"]]
    assert names == ["book"]                                  # two units, one overload of the same symbol
    detail = first["functions"][0]["detail"]
    assert detail.startswith("book checks the request against the fleet")   # the longer detail speaks
    assert "HOURS" not in json.dumps(plan)                     # module regions are not narrated
    assert [item["reveal"]["functions"] for item in plan["items"]
            if item["slide"].get("module") == first["id"]] == [0, 1]


def test_map_prose_is_made_speakable(tmp_path) -> None:
    plan = video.build_plan(_run(tmp_path), seconds=10_000)
    text = " ".join(item["say"] for item in plan["items"])
    assert "`" not in text and "](" not in text
    assert "Come here to" not in text
    assert "Understand" not in text                            # the page lead-in is dropped, not reworded
    assert "parseArgs reads argv and returns the options object." in text   # ticks removed, case kept
    tool = plan["modules"][1]
    assert tool["capability"] == "Reads the command line."


def test_stats_come_from_the_catalog(tmp_path) -> None:
    plan = video.build_plan(_run(tmp_path), seconds=10_000)
    assert plan["stats"] == {"files": 3, "figures": 5, "pages": 6, "systems": 2, "modules": 3}
    assert plan["project"] == "demo"
    assert plan["items"][0]["say"].startswith("demo is a small reservation service")


def test_the_cut_to_length_never_leaves_a_module_without_functions(tmp_path) -> None:
    full = video.build_plan(_run(tmp_path), seconds=10_000)
    short = video.build_plan(_run(tmp_path), seconds=1)
    assert len(short["items"]) < len(full["items"])
    assert short["modules"] and all(module["functions"] for module in short["modules"])
    # what stays is a prefix: the cut removes the later lines, it does not reorder them
    kept = [item["say"] for item in short["items"] if item["slide"]["kind"] != "closing"]
    assert kept == [item["say"] for item in full["items"]][:len(kept)]
    assert short["items"][-1]["slide"]["kind"] == "closing"
    # the whole film keeps both modules, each down to its functions
    assert len(full["modules"]) == 2 and all(module["functions"] for module in full["modules"])


def test_planning_is_deterministic(tmp_path) -> None:
    run = _run(tmp_path)
    assert video.build_plan(run) == video.build_plan(run)


def test_script_document_is_what_make_audio_reads(tmp_path) -> None:
    plan = video.build_plan(_run(tmp_path))
    document = video.script_document(plan)
    assert set(document) == {"facts", "items"}
    assert document["facts"]["symbols"] == plan["stats"]["figures"]
    assert [item["id"] for item in document["items"]] == [item["id"] for item in plan["items"]]
    for item in document["items"]:
        assert item["say"] and item["scene"] in {"title", "map", "module", "closing"}


def test_a_run_without_a_tree_says_so(tmp_path) -> None:
    run = tmp_path / "flat"
    run.mkdir()
    (run / "catalog.json").write_text(json.dumps({"units": {}, "nodes": {}}), encoding="utf-8")
    with pytest.raises(video.VideoError):
        video.build_plan(run)


def test_captions_use_the_same_timeline(tmp_path) -> None:
    plan = video.build_plan(_run(tmp_path))
    timing = {"items": [{"id": item["id"], "t0": index * 2.0, "t1": index * 2.0 + 1.5}
                        for index, item in enumerate(plan["items"])]}
    text = video.captions(plan, timing)
    assert text.startswith("1\n00:00:00,000 --> 00:00:01,500\n")
    assert text.count("-->") == len(plan["items"])
