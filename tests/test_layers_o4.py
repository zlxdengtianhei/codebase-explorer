"""O4 public consumers: compact pages and complete ID-addressable evidence."""
import hashlib
import json
from pathlib import Path

import pytest

from cbe import cli, docs, host_run, source_context
from cbe.records import frozen_sources, summary_sentence
from test_host_run import _drive, _repo
from test_semantic import SRC, _good_payload, _inventory, _tree, _grouped_run


def _run(tmp_path):
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg/jobs.py").write_text(SRC)
    context = source_context.build_context(repo)
    # Use grammar IDs, as real runs do (not AST compatibility IDs).
    from cbe.symbols import inventory_from_context
    inventory = inventory_from_context(context)
    payload = _good_payload(inventory)
    units = {u["id"]: u for u in payload["units"]}
    ids = list(units)
    units[ids[0]]["relations"] = [{"target": ids[-1], "kind": "use", "basis": "KEEP THIS EVIDENCE"}]
    units[ids[0]]["members"] = [ids[-1]]
    run = tmp_path / "run"
    run.mkdir()
    (run / "context.json").write_text(json.dumps(context))
    docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                dispositions=payload["dispositions"], tree=_tree(ids), languages={"pkg/jobs.py": "python"},
                context=context)
    return run, ids, units, inventory, context


def test_page_and_catalog_share_complete_records(tmp_path):
    run, ids, units, inventory, _ = _run(tmp_path)
    page = (run / "docs/nodes/root.md").read_text()
    catalog = json.loads((run / "catalog.json").read_text())
    assert "KEEP THIS EVIDENCE" not in page
    assert "folds:" not in page and "kind:" not in page
    assert "### `class::" not in page and "### `function::" not in page
    assert "pkg/jobs.py:L" in page and "**Relations.**" not in page
    assert "怎样查" in page and "cbe source --run-dir" in page
    assert "给 agent 的读法" in (run / "docs/INDEX.md").read_text()
    for uid, original in units.items():
        record = catalog["units"][uid]
        for field in ("explain", "extras", "relations", "uncertainties", "members"):
            assert record[field] == original.get(field, [])
        assert record["ranges"] == docs.unit_ranges(uid, original, inventory)
        assert {"signatures", "outgoing", "incoming", "graph_state", "reverse_relations"} <= record.keys()
        assert docs.query(run, uid)["explain"] == original["explain"]
        assert docs.query(run, uid)["ranges"] == record["ranges"]
    assert catalog["units"][ids[-1]]["reverse_relations"][0]["basis"] == "KEEP THIS EVIDENCE"


def test_file_query_is_a_drill_down_listing(tmp_path):
    run, ids, units, _, _ = _run(tmp_path)
    record = docs.query(run, "pkg/jobs.py")
    assert len(record["units"]) == len(units)
    assert record["ranges"][0]["lines"] == [[1, len(SRC.splitlines())]]
    assert "explain" not in record and "KEEP THIS EVIDENCE" not in json.dumps(record)
    assert all(set(row) == {"id", "name", "ranges", "summary"} for row in record["units"])
    symbol = docs.query(run, next(uid for uid in ids if units[uid]["kind"] == "function"))
    assert symbol["signature"] and symbol["ranges"]


def test_source_uses_frozen_bytes_and_rejects_corruption_without_stdout(tmp_path, capsys):
    run, ids, _, _, _ = _run(tmp_path)
    (tmp_path / "repo/pkg/jobs.py").write_text("LIVE FILE CHANGED")
    assert cli.main(["source", "--run-dir", str(run), "--id", "pkg/jobs.py"]) == 0
    printed = capsys.readouterr().out
    assert "negative" in printed and "LIVE FILE" not in printed
    assert "def submit" in docs.source(run, ids[0])
    for uid in ids:
        assert cli.main(["source", "--run-dir", str(run), "--id", uid, "--context", "1"]) == 0
        assert "pkg/jobs.py:L" in capsys.readouterr().out
    path = run / "context.json"
    context = json.loads(path.read_text())
    context["chunks"][-1]["text"] += "CORRUPT"
    path.write_text(json.dumps(context))
    assert cli.main(["source", "--run-dir", str(run), "--id", "pkg/jobs.py"]) == 2
    output = capsys.readouterr()
    assert not output.out and "digest mismatch" in output.err
    assert cli.main(["source", "--run-dir", str(run), "--id", ids[0], "--context", "-1"]) == 2
    assert not capsys.readouterr().out


def test_agent_query_prose_once_and_json_opt_in(tmp_path, capsys):
    run, ids, units, _, _ = _run(tmp_path)
    uid = ids[0]
    assert cli.main(["query", "--run-dir", str(run), "--id", uid]) == 0
    text = capsys.readouterr().out
    assert text.count(units[uid]["explain"]) == 1
    assert "unit_detail" not in text and "KEEP THIS EVIDENCE" in text
    assert cli.main(["query", "--run-dir", str(run), "--id", uid, "--json"]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["explain"] == units[uid]["explain"] and "unit_detail" not in record
    catalog = json.loads((run / "catalog.json").read_text())
    residuals = [uid for uid in catalog["short_names"] if "::module_residual::" in uid]
    assert residuals
    for uid in residuals:
        assert "模块代码（L" in catalog["short_names"][uid]


def test_frozen_source_crlf_and_utf8_round_trip(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    raw = 'def café():\r\n    return "茶"\r\n'.encode()
    (repo / "a.py").write_bytes(raw)
    context = source_context.build_context(repo)
    assert frozen_sources(context)["a.py"].encode() == raw


def test_summary_optional_and_fallback_preserves_full_explanation():
    assert summary_sentence({"explain": "First. Second."}) == "First."
    assert summary_sentence({"explain": "第一句。第二句。"}) == "第一句。"
    assert summary_sentence({"summary": "Chosen.", "explain": "First. Second."}) == "Chosen."


def test_grouped_and_index_only_queries_keep_scope_and_explanation(tmp_path):
    run, inventory, units, dispositions, tree, members, group, index_only = _grouped_run(tmp_path)
    for sid in members:
        record = docs.query(run, sid)
        assert record["explain"] == units[group]["explain"]
        assert record["ranges"] == next(s["ranges"] for s in json.loads(
            (run / "catalog.json").read_text())["symbols"].values() if s["id"] == sid)
        assert "unit_detail" not in record
        assert record["unit_id"] == group
        assert record["unit_ranges"] == docs.unit_ranges(group, units[group], inventory)
    record = docs.query(run, index_only)
    assert record["explain"] == dispositions[index_only]["reason"]
    assert record["ranges"] and record["how"] == "index_only"


def test_grouped_dispositions_supply_ranges_even_without_declared_members(tmp_path):
    run, inventory, units, dispositions, tree, members, group, _ = _grouped_run(tmp_path)
    units[group]["members"] = []
    repo = tmp_path / "repo"
    context = source_context.build_context(repo)
    (run / "context.json").write_text(json.dumps(context))
    docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                dispositions=dispositions, tree=tree, languages={"pkg/jobs.py": "python"}, context=context)
    record = docs.query(run, group)
    assert record["members"] == [] and set(record["folded_members"]) == set(members)
    assert record["ranges"] and record["primary_range"]["path"] == "pkg/jobs.py"
    text = docs.source(run, group)
    assert "def reserve" in text and "def submit" in text


def test_optional_summary_validation_is_compatible_and_does_not_truncate():
    from cbe import checks
    inventory = _inventory()
    payload = _good_payload(inventory)
    summary = "long sentence " * 40
    payload["units"][0]["summary"] = summary
    assert not checks.validate_details(payload, ["pkg/jobs.py"], inventory, set())
    assert payload["units"][0]["summary"] == summary
    payload["units"][0]["summary"] = ["a sentence"]
    assert any("summary" in p for p in checks.validate_details(payload, ["pkg/jobs.py"], inventory, set()))
    checks.normalize_details(payload, ["pkg/jobs.py"], inventory, set())
    assert isinstance(payload["units"][0]["summary"], str)


def test_fallback_snapshot_keeps_exact_unsupported_source_after_repo_is_gone(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    raw = b"create table jobs (id integer);\r\n\r\n"
    (repo / "schema.sql").write_bytes(raw)
    run = Path(host_run.plan(repo, tmp_path / "run", review="none")["run_dir"])
    _drive(run)
    (repo / "schema.sql").unlink()
    context = json.loads((run / "context.json").read_text())
    assert frozen_sources(context)["schema.sql"].encode() == raw
    assert cli.main(["source", "--run-dir", str(run), "--id", "schema.sql"]) == 0
    assert "create table jobs" in capsys.readouterr().out


def test_summary_prompt_and_tree_digest_preserve_full_semantics():
    from cbe import prompts
    unit = {"id": "a.py::f", "kind": "function", "explain": "First. Second."}
    digest = prompts.unit_digest(unit)
    assert digest["summary"] == "First." and digest["explain"] == unit["explain"]
    unit["summary"] = "Chosen."
    assert prompts.unit_digest(unit)["summary"] == "Chosen."
    prompt = prompts.detail_prompt(["a.py"], {"a.py": {"symbols": []}})
    assert "summary (string, optional)" in prompt and "25 words" in prompt


def test_full_signatures_are_not_limited_to_prompt_signature_budget(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    signature = "def many(" + ", ".join(f"arg_{i}: int = {i}" for i in range(90)) + "):"
    body = "    value = arg_0\n" + "".join(f"    value += arg_{i}\n" for i in range(1, 90)) + "    return value\n"
    (repo / "long.py").write_text(signature + "\n" + body)
    by_id, by_location = source_context.source_signatures("long.py", (repo / "long.py").read_text(), "python")
    assert by_location["many", 1] == signature
    assert next(iter(by_id.values())) == signature
    # The symbol_id metadata is additive. Older segmented contexts still carry
    # enough canonical identity in their ::sN suffix to recover the full header.
    from cbe.records import build_records
    from cbe.symbols import inventory_from_context
    context = source_context.build_context(repo, max_segment_bytes=64)
    for chunk in context["chunks"]:
        chunk.pop("symbol_id", None)
    inventory = inventory_from_context(context)
    units = {row["id"]: {"id": row["id"], "kind": row["kind"], "explain": "A long signature."}
             for row in inventory["long.py"]["symbols"]}
    dispositions = {uid: {"how": "unit", "unit": uid} for uid in units}
    records, _ = build_records(units, dispositions, inventory,
                               {uid: docs.unit_ranges(uid, unit, inventory) for uid, unit in units.items()},
                               {"long.py": (repo / "long.py").read_text()}, {"long.py": "python"}, context, None)
    assert any(c["start_line"] > 1 for c in context["chunks"] if c["kind"] == "function")
    assert all(row["signature"] == signature for row in records.values() if row["kind"] == "function")


def test_legacy_overload_signatures_match_their_own_source_spans(tmp_path):
    run, _, _, _, _, _, _, _ = _grouped_run(tmp_path)
    overloaded = docs.query(run, "pkg/jobs.py::reserve")
    implementation = docs.query(run, "pkg/jobs.py::reserve@5")
    assert "value: int" in overloaded["signature"]
    assert implementation["signature"] == "def reserve(value):"
    assert implementation["ranges"][0]["lines"] == [[5, 8]]


def test_arrow_signature_does_not_include_its_expression_body():
    _, by_location = source_context.source_signatures("a.js", "export const add = (a, b) => a + b;\n", "javascript")
    assert by_location["add", 1].endswith("=>")
    assert "a + b" not in by_location["add", 1]


def test_summary_metrics_use_the_published_artifacts_and_frozen_source(tmp_path):
    from cbe.token_budget import count_text_tokens
    repo = _repo(tmp_path)
    run = Path(host_run.plan(repo, tmp_path / "run", review="none")["run_dir"])
    _drive(run)
    summary = json.loads((run / "summary.json").read_text())
    expected = docs.layer_metrics(run)
    assert summary["layers"] == expected
    assert expected["semantic_tokens"] > 0 and expected["deterministic_tokens"] > 0
    assert expected["source_tokens"] == sum(count_text_tokens(path.read_bytes().decode("utf-8"))
                                             for path in repo.rglob("*.py"))
    assert "Markdown" in expected["scope"]
    assert sum(expected["semantic_breakdown"].values()) == expected["semantic_tokens"]
    assert expected["semantic_breakdown"]["model_body"] > 0
    assert expected["semantic_breakdown"]["signature_location"] > 0
    assert expected["semantic_breakdown"]["heading_anchor"] > 0
    assert expected["model_body_source_ratio"] == expected["model_body_tokens"] / expected["source_tokens"]
    assert summary["layers"]["semantic_source_ratio"] == expected["semantic_tokens"] / expected["source_tokens"]


def test_graph_edges_and_statuses_remain_available_in_both_directions(tmp_path):
    repo = _repo(tmp_path)
    from test_host_run import _graph_for
    graph = _graph_for(repo, ["src/pkg/jobs.py", "src/pkg/cli.py"])
    graph["nodes"] = [
        {"id": "main", "kind": "function", "path": "src/pkg/cli.py", "start_line": 3, "name": "main"},
        {"id": "reserve", "kind": "function", "path": "src/pkg/jobs.py", "start_line": 5, "name": "reserve_run"},
    ]
    graph["edges"] = [{"id": "edge", "kind": "call", "source": "main", "target": "reserve",
                        "path": "src/pkg/cli.py", "line": 4, "column": 12, "status": "resolved",
                        "expression": "reserve_run(len(argv))"}]
    graph["edges"].append({"id": "internal", "kind": "cfg", "source": "main", "target": "main"})
    gp = tmp_path / "graph.json"
    gp.write_text(json.dumps(graph))
    run = Path(host_run.plan(repo, tmp_path / "run", review="none", graph_path=gp)["run_dir"])
    _drive(run)
    catalog = json.loads((run / "catalog.json").read_text())
    caller = next(r for r in catalog["units"].values() if r["outgoing"])
    callee = next(r for r in catalog["units"].values() if r["incoming"])
    assert caller["outgoing"] == callee["incoming"] == ["edge"]
    assert catalog["edges"]["edge"]["status"] == "resolved"
    assert len(catalog["edges"]) == 1
    assert caller["internal_edge_counts"] == {"cfg": 1, "dataflow": 0}
    assert all(isinstance(e, str) for section in ("units", "symbols")
               for row in catalog[section].values() for d in ("outgoing", "incoming") for e in row[d])
    assert catalog["graph_ref"] == "context.json" and catalog["graph"] is None
    assert json.loads((run / "context.json").read_text())["graph"] == graph
    queried = docs.query(run, caller["id"])
    assert queried["outgoing"][0]["target_name"] == "reserve_run"
    assert "graph_nodes" not in queried and "unit_detail" not in queried
    assert docs.query(run, caller["id"], edges="all")["raw_edges"][0]["expression"] == "reserve_run(len(argv))"
    assert docs.query(run, caller["id"], edges="cfg")["raw_edges"] == [graph["edges"][1]]
    assert cli.main(["query", "--run-dir", str(run), "--id", caller["id"]]) == 0
    # Ordinary reads work with the large frozen context unavailable.
    (run / "context.json").rename(run / "context.saved")
    assert docs.query(run, caller["id"])["outgoing"][0]["status"] == "resolved"
    assert docs.find(run, "reserve")
    (run / "context.saved").rename(run / "context.json")
    assert "reserve_run(len(argv))" not in (run / "catalog.json").read_text()
    metrics = docs.layer_metrics(run)
    assert metrics["frozen_graph_tokens"] > 0
    assert metrics["deterministic_tokens"] == metrics["catalog_tokens"] + metrics["frozen_graph_tokens"]
