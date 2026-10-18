"""Resolve a graph through real source coordinates and publish linked flows."""
import json
from cbe import docs


def test_render_resolved_calls_and_inferred_transitions(tmp_path):
    from test_semantic import SRC, _inventory, _good_payload
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg/jobs.py").write_text(SRC)
    inventory = _inventory()
    payload = _good_payload(inventory)
    units = {u["id"]: u for u in payload["units"]}
    a, b = "pkg/jobs.py::Pool.submit", "pkg/jobs.py::reserve@5"
    tree = {"nodes": [dict(id="top", parent=None, title="Top", unit_ids=[]),
                       dict(id="root", parent="top", title="Submit", unit_ids=[a]),
                       dict(id="helper", parent="top", title="Reserve",
                            unit_ids=sorted(set(units) - {a}))],
            "depends_on": [{"from": "root", "to": "helper", "basis": "Reserves values."}]}
    evidence = {"schema": "cbe-graph/1", "nodes": [
        dict(id="submit", path="pkg/jobs.py", start_line=11, kind="method"),
        dict(id="reserve", path="pkg/jobs.py", start_line=5, kind="method")],
        "edges": [dict(id="call", kind="call", status="resolved", source="submit", target="reserve",
                       path="pkg/jobs.py", line=12, column=16)]}
    system = dict(overview="Reserve submitted values.", maintenance_navigation="Open Submit.",
                  dependency_descriptions=[dict(**{"from": "root", "to": "helper"},
                                               description="Submission reserves a value.")],
                  key_flows=[dict(name="Submit", description="Reserve a submitted value.", steps=[a, b]),
                             dict(name="Reverse", description="An inferred transition.", steps=[b, a]),
                             dict(name="Round trip", description="Combines both transitions.", steps=[a, b, a])])
    run = tmp_path / "run"
    import hashlib
    context = {"files": [{"path": "pkg/jobs.py", "source": SRC,
                           "sha256": hashlib.sha256(SRC.encode()).hexdigest()}],
               "chunks": [{"id": a, "path": "pkg/jobs.py", "start_byte": SRC.index("    def submit"),
                           "end_byte": len(SRC.encode())},
                          {"id": b, "path": "pkg/jobs.py", "start_byte": SRC.index("def reserve(value):"),
                           "end_byte": SRC.index("class Pool:")}]}
    result = docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                         dispositions=payload["dispositions"], tree=tree, languages={"pkg/jobs.py": "python"},
                         graph=evidence, system=system, context=context)
    catalog = json.loads((run / "catalog.json").read_text())
    assert catalog["node_dependencies"][0]["source"] == "graph_confirmed"
    assert catalog["node_dependencies"][0]["count"] == 1
    assert result["key_flows"] == 3 and result["candidate_flows"] == 1
    assert [f["inferred_steps"] for f in catalog["key_flows"]] == [[], [1], [2]]
    index = (run / "docs/INDEX.md").read_text()
    assert f"nodes/root.md#{docs.anchor(a)}" in index
    assert f"nodes/helper.md#{docs.anchor(b)}" in index
    assert "(model-inferred)" in index and "graph-confirmed" in index
    assert all(row["ok"] for row in docs.verify(run, inventory, units, payload["dispositions"], tree))
