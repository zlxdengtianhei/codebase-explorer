"""C4 counterexamples exercised through published pages, queries and checks."""
import json
import re

import pytest

from cbe import cli, docs, source_context
from cbe.symbols import inventory_from_context
from test_layers_o4 import _run


def test_edges_obey_exclusive_ownership_at_shared_boundary(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    text = "class MethodView:\n    marker = 1\n\n    def __init_subclass__(cls):\n        return cls\n"
    (repo / "views.py").write_text(text)
    context = source_context.build_context(repo)
    inventory = inventory_from_context(context)
    symbols = inventory["views.py"]["symbols"]
    units = {s["id"]: {"id": s["id"], "kind": s["kind"], "explain": "First. Complete explanation."}
             for s in symbols}
    parent = next(s for s in symbols if s["name"] == "MethodView")
    child = next(s for s in symbols if s["name"] == "__init_subclass__")
    assert parent["lines"][-1][-1] == child["lines"][0][0]
    nodes = [{"id": s["id"], "path": "views.py", "start_line": s["lines"][0][0]}
             for s in (parent, child)]
    graph = {"nodes": nodes, "edges": [
        {"id": f"{i}-{kind}", "kind": kind, "source": s["id"], "target": s["id"]}
        for i, s in enumerate((parent, child)) for kind in ("cfg", "dataflow")]}
    context["graph"] = graph
    run = tmp_path / "run"
    run.mkdir()
    (run / "context.json").write_text(json.dumps(context))
    docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                dispositions={uid: {"how": "unit", "unit": uid} for uid in units},
                tree={"nodes": [{"id": "root", "unit_ids": list(units)}]},
                languages={"views.py": "python"}, context=context, graph=graph)
    for uid in units:
        record = docs.query(run, uid, edges="cfg,dataflow")
        for kind in ("cfg", "dataflow"):
            assert sum(e["kind"] == kind for e in record["raw_edges"]) == record["internal_edge_counts"][kind]
    assert [e["id"] for e in docs.query(run, parent["id"], edges="cfg")["raw_edges"]] == ["0-cfg"]
    assert cli.main(["query", "--run-dir", str(run), "--id", parent["id"], "--edges", "cfgg"]) == 2
    assert "--edges" in capsys.readouterr().err
    # A folded symbol still selects its own edges; the owning unit selects both.
    units.pop(child["id"])
    units[parent["id"]]["members"] = [child["id"]]
    dispositions = {uid: {"how": "unit", "unit": uid} for uid in units}
    dispositions[child["id"]] = {"how": "grouped", "unit": parent["id"]}
    docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                dispositions=dispositions, tree={"nodes": [{"id": "root", "unit_ids": list(units)}]},
                languages={"views.py": "python"}, context=context, graph=graph)
    assert [e["id"] for e in docs.query(run, child["id"], edges="cfg")["raw_edges"]] == ["1-cfg"]
    assert len(docs.query(run, parent["id"], edges="cfg")["raw_edges"]) == 2


@pytest.mark.parametrize("prefix", ["Prose with a stray ` backtick.\n\n", "Prose with `` unmatched.\n\n", ""])
def test_verify_reports_broken_link_after_unmatched_code_delimiter(tmp_path, prefix):
    run, _, units, inventory, _ = _run(tmp_path)
    page = run / "docs/nodes/root.md"
    text = page.read_text()
    catalog = json.loads((run / "catalog.json").read_text())
    tree = {"nodes": [{"id": nid, **node} for nid, node in catalog["nodes"].items()]}
    def check():
        return next(c for c in docs.verify(run, inventory, units, catalog["dispositions"], tree)
                    if c["check"] == "relative_links_resolve")
    literal = "\n`value[x][f999]`\n\n~~~py\n[example](not-a-page.md)\n~~~\n\n    [example](not-a-page.md)\n"
    page.write_text(text + literal)
    assert check()["ok"]
    page.write_text("Continuation paragraph\n    [broken](missing-page.md).\n\n" + text)
    assert not check()["ok"]
    page.write_text(prefix + "See [broken](missing-page.md).\n\n" + text + literal)
    result = check()
    assert not result["ok"]
    assert any("missing-page.md" in item for item in result["detail"]["broken"])


def test_every_page_title_finds_its_id_despite_many_incidental_matches(tmp_path):
    run, _, _, _, _ = _run(tmp_path)
    path = run / "catalog.json"
    catalog = json.loads(path.read_text())
    titles = re.findall(r'<a id="(u-[0-9a-f]+)"></a>\n### `([^`]+)`',
                        (run / "docs/nodes/root.md").read_text())
    # Incidental matches must not crowd a named unit out of the default limit.
    catalog["symbols"] = {**{f"noise-{i}": {"name": f"noise-{i}", "explain": " ".join(t for _, t in titles)}
                            for i in range(40)}, **catalog["symbols"]}
    path.write_text(json.dumps(catalog))
    for anchor, title in titles:
        uid = next(uid for uid, row in catalog["units"].items() if row["anchor"] == "#" + anchor)
        assert uid in [row["id"] for row in docs.find(run, title)]
        assert docs.find(run, uid, limit=1)[0]["id"] == uid
    footer = (run / "docs/nodes/root.md").read_text().split("## 怎样查")[1]
    assert 'cbe find --run-dir "$RUN" --term' in footer
    assert "按 [INDEX]" not in footer


@pytest.mark.parametrize("summary", [None, "Chosen summary.", "First sentence."])
def test_page_keeps_complete_explanation_with_or_without_summary(tmp_path, summary):
    run, ids, units, inventory, context = _run(tmp_path)
    uid = ids[0]
    explain = "First sentence. Second sentence with the essential boundary.\n\nFinal paragraph about failure."
    units[uid]["explain"] = explain
    if summary is not None:
        units[uid]["summary"] = summary
    tree = {"nodes": [{"id": "root", "unit_ids": ids}]}
    docs.render(run_dir=run, source_root=tmp_path / "repo", inventory=inventory,
                units=units, dispositions={sid: {"how": "unit", "unit": sid} for sid in ids},
                tree=tree, languages={"pkg/jobs.py": "python"}, context=context)
    page = (run / "docs/nodes/root.md").read_text()
    body = page.split(f'<a id="{docs.anchor(uid)}"></a>')[1].split('<a id="')[0]
    for sentence in ("First sentence.", "Second sentence with the essential boundary.",
                     "Final paragraph about failure."):
        assert body.count(sentence) == 1
    if summary:
        assert summary in body
    assert docs.query(run, uid)["explain"] == explain


def test_product_read_query_instructions_use_available_commands(tmp_path, capsys):
    import shlex
    from pathlib import Path

    run, ids, _, _, _ = _run(tmp_path)
    skill = (Path(__file__).resolve().parents[1] / ".dsh/skills/codebase-explorer/SKILL.md").read_text()
    section = skill.split("## 读与查 / Read and query the result")[1].split("## Script-driven")[0]
    assert "unit_detail" not in section and "unit_id" in section
    assert "--edges cfg,dataflow" in section and "--edges all --json" in section
    for line in section.splitlines():
        if line.startswith("cbe "):
            args = shlex.split(line.replace("$RUN", str(run)).replace("$ID", ids[0]))
            assert cli.main(args[1:]) == 0
            capsys.readouterr()


def test_json_queries_preserve_file_metadata_and_inventory_names(tmp_path, capsys):
    run, _, _, _, _ = _run(tmp_path)
    path = run / "catalog.json"
    catalog = json.loads(path.read_text())
    sid = next(iter(catalog["symbols"]))
    original_name = catalog["symbols"][sid]["name"]
    catalog["short_names"][sid] = "pkg/jobs.py:" + original_name
    path.write_text(json.dumps(catalog))
    assert cli.main(["query", "--run-dir", str(run), "--id", sid, "--json"]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["name"] == original_name
    assert record["display_name"] == "pkg/jobs.py:" + original_name
    assert cli.main(["query", "--run-dir", str(run), "--id", "pkg/jobs.py", "--json"]) == 0
    file = json.loads(capsys.readouterr().out)
    for key in ("tokens", "language", "known_empty"):
        assert file[key] == catalog["files"]["pkg/jobs.py"][key]


def test_layer_metrics_count_footer_in_footer_category(tmp_path):
    from cbe.token_budget import count_section_tokens

    run, _, _, _, _ = _run(tmp_path)
    page = (run / "docs/nodes/root.md").read_text()
    before, footer = page.split("## 怎样查", 1)
    footer, references = footer.split("[f1]:", 1)
    expected = count_section_tokens([("before", before), ("footer", "## 怎样查" + footer),
                                     ("references", "[f1]:" + references)])["footer"]
    metrics = docs.layer_metrics(run)
    assert expected > 0
    assert metrics["semantic_breakdown"]["footer"] == expected
    assert sum(metrics["semantic_breakdown"].values()) == metrics["semantic_tokens"]


def test_method_titles_keep_their_declaring_class(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "views.py").write_text("class View:\n    def dispatch_request(self):\n        pass\n\n"
                                   "class MethodView:\n    def dispatch_request(self):\n        pass\n")
    context = source_context.build_context(repo)
    inventory = inventory_from_context(context)
    units = {s["id"]: {"id": s["id"], "kind": s["kind"], "explain": "Dispatch a request."}
             for s in inventory["views.py"]["symbols"]}
    run = tmp_path / "run"
    run.mkdir()
    docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                dispositions={uid: {"how": "unit", "unit": uid} for uid in units},
                tree={"nodes": [{"id": "root", "unit_ids": list(units)}]},
                languages={"views.py": "python"}, context=context)
    page = (run / "docs/nodes/root.md").read_text()
    assert "### `View.dispatch_request`" in page
    assert "### `MethodView.dispatch_request`" in page
    assert "dispatch_request (2)" not in page


@pytest.mark.parametrize("abbreviation", ["i.e.", "e.g.", "I.E."])
def test_summary_does_not_split_at_explanatory_abbreviations(tmp_path, abbreviation):
    from cbe.records import summary_sentence

    first = f"Registers a callback, {abbreviation} a function called before dispatch."
    assert summary_sentence({"explain": first + " The complete body remains available."}) == first
    assert summary_sentence({"explain": "第一句。第二句。"}) == "第一句。"
