"""skeleton.build: pure, deterministic, always a legal tree."""
from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pytest

from cbe import skeleton
from cbe.skeleton import Weights, build

ROOT = Path(__file__).resolve().parents[1]


def unit(path: str, summary: str = "") -> dict:
    return {"summary": summary, "ranges": [{"path": path, "lines": [[1, 5]]}]}


def clustered(clusters: int = 4, size: int = 14, hub: bool = False):
    """``clusters`` groups of ``size`` units; calls form a ring with chords inside a group."""
    units, edges = {}, []
    for c in range(clusters):
        ids = [f"c{c}u{i}" for i in range(size)]
        for i, uid in enumerate(ids):
            units[uid] = unit(f"pkg/mod{c}.py", f"handle thing{c} step {i}")
        for i, uid in enumerate(ids):
            for step in (1, 2, 3):
                edges.append({"from": uid, "to": ids[(i + step) % size], "kind": "call", "count": 2})
    if hub:
        units["util"] = unit("pkg/util.py", "format a value")
        for uid in list(units):
            if uid != "util":
                edges.append({"from": uid, "to": "util", "kind": "call", "count": 1})
    return units, edges


def kids_of(nodes):
    kids = defaultdict(list)
    for n in nodes:
        if n["parent"] is not None:
            kids[n["parent"]].append(n["id"])
    return kids


def check_invariants(res, units, grain=(5, 30)):
    nodes, kids = res["nodes"], kids_of(res["nodes"])
    ids = [n["id"] for n in nodes]
    assert len(ids) == len(set(ids))
    assert sum(1 for n in nodes if n["parent"] is None) == 1
    assert all(n["parent"] is None or n["parent"] in ids for n in nodes)
    owner = defaultdict(list)
    for n in nodes:
        for u in n["unit_ids"]:
            owner[u].append(n["id"])
        if kids[n["id"]]:
            assert n["unit_ids"] == [], "only leaves hold units"
            assert len(kids[n["id"]]) >= 2, "internal node needs two children"
        else:
            assert n["unit_ids"], "empty leaf"
            size = len(n["unit_ids"])
            assert grain[0] <= size <= grain[1] or n.get("flag"), f"{size} units outside grain without a flag"
    assert sorted(owner) == sorted(units)
    assert all(len(v) == 1 for v in owner.values())


def test_same_input_same_bytes():
    units, edges = clustered(5, 12, hub=True)
    a = json.dumps(build(units, edges), sort_keys=True)
    b = json.dumps(build(dict(reversed(list(units.items()))), list(reversed(edges))), sort_keys=True)
    assert a == b


def test_same_bytes_across_hash_seeds():
    code = (
        "import json,sys\nfrom tests.test_skeleton import clustered\nfrom cbe.skeleton import build\n"
        "u,e=clustered(5,12,hub=True)\nsys.stdout.write(json.dumps(build(u,e),sort_keys=True))\n")
    outs = []
    for hash_seed in ("1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=hash_seed,
                   PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(ROOT)]))
        outs.append(subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True,
                                   check=True, cwd=ROOT).stdout)
    assert outs[0] == outs[1] and outs[0]


@pytest.mark.skipif(not (ROOT / "examples/ruby_llm/catalog.json.gz").exists(), reason="example catalog not present")
def test_real_catalog_same_bytes_across_hash_seeds():
    """Regression: a subgraph view iterated a set in hash order, so real catalogs differed between processes."""
    code = (
        "import gzip,json,sys\nfrom cbe.aggregation import unit_edges\nfrom cbe.skeleton import build\n"
        "c=json.load(gzip.open('examples/ruby_llm/catalog.json.gz'))\n"
        "sys.stdout.write(json.dumps(build(c['units'],unit_edges(c['units'],c['edges'])),sort_keys=True))\n")
    outs = []
    for hash_seed in ("1", "3", "5"):
        env = dict(os.environ, PYTHONHASHSEED=hash_seed, PYTHONPATH=str(ROOT / "src"))
        outs.append(subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True,
                                   check=True, cwd=ROOT).stdout)
    assert outs[0] == outs[1] == outs[2] and outs[0]


def test_invariants_on_clusters():
    units, edges = clustered(5, 12)
    res = build(units, edges)
    check_invariants(res, units)
    assert len([n for n in res["nodes"] if not n["unit_ids"] == []]) >= 4


def test_isolated_units_still_make_a_tree():
    units = {f"u{i}": unit(f"d{i}/f{i}.py") for i in range(47)}
    res = build(units, [])
    check_invariants(res, units)
    res_flat = build(units, [], weights=Weights(0, 0, 0))   # no position, no wording, no edge at all
    check_invariants(res_flat, units)
    assert any(n.get("flag", "").startswith("packed_by_path") for n in res_flat["nodes"])


@pytest.mark.parametrize("n", [1, 2, 4, 6])
def test_tiny_inputs(n):
    units = {f"u{i}": unit("a.py", f"thing {i}") for i in range(n)}
    res = build(units, [])
    check_invariants(res, units)


def test_empty_input():
    assert build({}, []) == {"nodes": []}


def test_helper_called_by_everyone_does_not_glue_everyone():
    units, edges = clustered(4, 12, hub=True)
    res = build(units, edges)
    check_invariants(res, units)
    leaves = [n for n in res["nodes"] if n["unit_ids"]]
    assert len(leaves) >= 4
    for leaf in leaves:
        groups = {u[:2] for u in leaf["unit_ids"] if u != "util"}
        assert len(groups) == 1, f"leaf mixes clusters {groups}"


def test_dependency_only_weights():
    units, edges = clustered(4, 12)
    res = build(units, edges, weights=Weights(w_file=0, w_dir=0, w_text=0))
    check_invariants(res, units)


def test_large_clique_is_split_into_grain():
    # a 40-unit clique is above the limit: it is split again inside its own subgraph
    units = {f"u{i}": unit("a.py", "same words") for i in range(40)}
    edges = [{"from": f"u{i}", "to": f"u{j}", "kind": "call", "count": 1} for i in range(40) for j in range(40) if i != j]
    res = build(units, edges)
    check_invariants(res, units)


def test_edges_to_unknown_units_are_ignored():
    units, edges = clustered(3, 10)
    edges = edges + [{"from": "ghost", "to": "c0u0", "kind": "call", "count": 1},
                     {"from": "c0u0", "to": "c0u0", "kind": "call", "count": 1}]
    check_invariants(build(units, edges), units)


def test_no_unit_or_edge_input_is_mutated():
    units, edges = clustered(3, 10)
    before = json.dumps([units, edges], sort_keys=True)
    build(units, edges)
    assert json.dumps([units, edges], sort_keys=True) == before


@pytest.mark.skipif(not (ROOT / "examples/ruby_llm/catalog.json.gz").exists(), reason="example catalog not present")
def test_real_catalog_ruby_llm():
    from cbe.aggregation import unit_edges
    cat = json.load(gzip.open(ROOT / "examples/ruby_llm/catalog.json.gz"))
    units = cat["units"]
    res = build(units, unit_edges(units, cat["edges"]))
    check_invariants(res, units)
    assert len(res["nodes"]) > 10
