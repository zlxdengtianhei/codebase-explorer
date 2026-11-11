#!/usr/bin/env python3
"""Slim a CBE catalog.json(.gz) down to what the showcase page reads.

Everything in the output comes from the catalog: unit names, summaries, line
ranges, module titles, resolved call edges.  Nothing is typed in by hand.

    python3 prepare_data.py ../examples/cjson/catalog.json.gz --name cJSON --out data/cjson.json
    python3 prepare_data.py RUN/catalog.json --name Flask --out data/flask.json [--graph GRAPH.json]

Edges: resolved call/import edges of the catalog (plus those of an optional --graph file, which
carries an `edges` table in the catalog's own format). A catalog without resolved edges falls back
to the model-inferred `relations` of each unit; the output says so in `edge_basis` and the page
labels such edges "inferred".

The "find" block (the terminal scene) is the first row of the real `cbe find` run on the same
catalog when a CBE Python is available (--cbe-python or $CBE_PYTHON, with this checkout's src/);
otherwise a small exact-name-first fallback with the same ordering rule is used.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def clean(text: str) -> str:
    text = (text or "").strip().strip('"').strip()
    return re.sub(r"\s+", " ", text)


def sentences(text: str, max_sentences: int, max_chars: int) -> str:
    out = ""
    for s in SENT.split(clean(text)):
        if out and (len(out) + len(s) + 1 > max_chars):
            break
        out = f"{out} {s}".strip()
        max_sentences -= 1
        if max_sentences <= 0:
            break
    if len(out) > max_chars:
        out = out[: max_chars - 1].rstrip() + "…"
    return out


def loc_of(rng) -> tuple[str, int, int]:
    path = rng["path"]
    a, b = rng["lines"][0]
    return f"{path}:L{a}-L{b}", a, b


def unit_name(uid: str, unit: dict, symbols: dict) -> str:
    if uid in symbols and symbols[uid].get("name"):
        return symbols[uid]["name"]
    if uid.startswith("grp:"):
        slug = uid.split("-", 1)[1] if "-" in uid else uid[4:]
        return slug.replace("-", " ")
    parts = uid.split("::")
    return parts[2] if len(parts) > 2 and parts[2] else parts[0]


def build_nodes(catalog: dict, unit_index: dict[str, int]):
    raw = catalog["nodes"]
    own = {nid: [unit_index[u] for u in n.get("unit_ids", []) if u in unit_index] for nid, n in raw.items()}
    kids = defaultdict(list)
    for nid, n in raw.items():
        if n.get("parent") in raw:
            kids[n["parent"]].append(nid)
    memo: dict[str, bool] = {}

    def alive(nid: str) -> bool:  # has a unit in its own subtree
        if nid not in memo:
            memo[nid] = bool(own[nid]) or any(alive(c) for c in kids[nid])
        return memo[nid]

    keep = [nid for nid in raw if alive(nid)]
    skipped = [nid for nid in raw if nid not in set(keep)]
    roots = [nid for nid in keep if raw[nid].get("parent") not in raw]
    depth = {}

    def walk(nid, d):
        depth[nid] = d
        for c in kids[nid]:
            if alive(c):
                walk(c, d + 1)

    for r in roots:
        walk(r, 0)
    # "top" = the big blocks. One root: its children are the blocks (the root is the project).
    top = {}
    if len(roots) == 1:
        root = roots[0]
        for nid in keep:
            if nid == root:
                top[nid] = root
                continue
            cur = nid
            while raw[cur]["parent"] != root:
                cur = raw[cur]["parent"]
            top[nid] = cur
    else:
        for nid in keep:
            cur = nid
            while raw[cur].get("parent") in raw:
                cur = raw[cur]["parent"]
            top[nid] = cur
    nodes = []
    for nid in keep:
        n = raw[nid]
        nodes.append({
            "id": nid, "parent": n.get("parent") if n.get("parent") in raw else None,
            "title": clean(n.get("title")), "capability": clean(n.get("capability")),
            "depth": depth[nid], "top": top[nid], "units": own[nid],
            "children": [c for c in kids[nid] if alive(c)],
        })
    return nodes, roots, skipped


def run_cbe(cbe_python: str, cbe_src: str, args: list[str]):
    """Run one real `cbe` command; return its stdout text or None. Read-only commands only."""
    if not cbe_python or not (Path(cbe_python).exists() or shutil.which(cbe_python)):
        return None
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    if cbe_src:
        env["PYTHONPATH"] = cbe_src
    with tempfile.TemporaryDirectory(suffix=".noindex") as tmp:
        res = subprocess.run([cbe_python, "-m", "cbe", *args], capture_output=True, text=True, env=env, cwd=tmp)
    if res.returncode != 0:
        print("cbe failed:", args[:2], res.stderr[-300:], file=sys.stderr)
        return None
    return res.stdout


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("catalog")
    ap.add_argument("--name", required=True, help="repo name shown in the header")
    ap.add_argument("--out", required=True)
    ap.add_argument("--graph", help="optional JSON with an `edges` table (catalog format) to use instead of the catalog's")
    ap.add_argument("--cbe-python", default=os.environ.get("CBE_PYTHON", ""))
    ap.add_argument("--cbe-src", default=os.environ.get("CBE_SRC", ""), help="PYTHONPATH for cbe (empty: the installed one)")
    ap.add_argument("--run-dir", default="", help="CBE run directory for the real find/source commands (default: the catalog's folder)")
    args = ap.parse_args()

    path = Path(args.catalog)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        catalog = json.load(fh)
    cunits, symbols, disp = catalog["units"], catalog.get("symbols", {}), catalog.get("dispositions", {})

    # files: sorted by path so the columns are stable
    files = []
    for fpath, f in sorted(catalog["files"].items()):
        nlines = 0
        for r in f.get("ranges", []):
            for a, b in r["lines"]:
                nlines = max(nlines, b)
        files.append({"path": fpath, "tokens": f.get("tokens", 0), "nlines": nlines, "lang": f.get("language", "")})
    file_idx = {f["path"]: i for i, f in enumerate(files)}

    # units: sorted by (file, first line) so indices are stable
    def key(item):
        uid, u = item
        loc, a, b = loc_of(u["primary_range"])
        return (u["primary_range"]["path"], a, uid)

    ordered = sorted(cunits.items(), key=key)
    unit_index = {uid: i for i, (uid, _) in enumerate(ordered)}
    units = []
    for uid, u in ordered:
        loc, a, b = loc_of(u["primary_range"])
        total = sum(b2 - a2 + 1 for r in u.get("ranges", []) for a2, b2 in r["lines"]) or (b - a + 1)
        summ = clean(u.get("summary") or u.get("explain"))
        units.append({
            "id": uid, "name": unit_name(uid, u, symbols), "kind": u["kind"],
            "file": file_idx.get(u["primary_range"]["path"], 0), "l1": a, "l2": b, "nl": total, "loc": loc,
            "summary": sentences(summ, 1, 200),
            "explain": sentences(u.get("explain", ""), 3, 330),
            "sig": (u.get("signature") or "").strip(), "node": u.get("node"),
        })

    # edges between units: resolved ones (catalog or --graph); else the model-inferred relations
    edge_table = catalog.get("edges") or {}
    if args.graph:
        with open(args.graph, encoding="utf-8") as fh:
            g = json.load(fh)
        edge_table = g.get("edges", g)
    rows = list(edge_table.values() if isinstance(edge_table, dict) else edge_table)
    if args.graph:
        # a raw graph file: keep its resolved calls, and take the unit-level endpoints from the catalog's own
        # edge table (same edge id), because graph node ids do not name units
        table = catalog.get("edges") or {}
        mapped = []
        for e in rows:
            if e.get("kind") == "call" and e.get("status") == "resolved" and e.get("id") in table:
                c = table[e["id"]]
                mapped.append({"status": "resolved", "source_symbol": c.get("source_symbol"), "target_symbol": c.get("target_symbol")})
        rows = mapped
    sym2unit = {k: v.get("unit") for k, v in disp.items() if v.get("unit")}
    for uid, u in cunits.items():
        sym2unit.setdefault(uid, uid)
        for m in list(u.get("members", [])) + list(u.get("folded_members", [])):
            sym2unit.setdefault(m, uid)
    pair_count: Counter = Counter()
    for e in rows:
        if e.get("status") != "resolved":
            continue
        s_, t_ = sym2unit.get(e.get("source_symbol")), sym2unit.get(e.get("target_symbol"))
        if s_ in unit_index and t_ in unit_index and s_ != t_:
            pair_count[(unit_index[s_], unit_index[t_])] += 1
    edge_basis = "resolved"
    if not pair_count:
        edge_basis = "inferred"
        for uid, u in cunits.items():
            for r in u.get("relations") or []:
                t_ = sym2unit.get(r.get("target"))
                if t_ in unit_index and t_ != uid and r.get("kind") != "import":
                    pair_count[(unit_index[uid], unit_index[t_])] += 1
    pairs = [[a, b, n] for (a, b), n in sorted(pair_count.items())]

    nodes, roots, skipped = build_nodes(catalog, unit_index)
    node_of = {n["id"]: n for n in nodes}

    # --- scene rules (no hand-picked ids) -------------------------------------------------
    callers = Counter()
    for a, b, n in pairs:
        callers[b] += 1
    focus = {"node": None, "unit": None}
    degree = Counter()
    for a, b, n in pairs:
        degree[a] += n; degree[b] += n
    node_of_unit = {i: nd["id"] for nd in nodes for i in nd["units"]}
    hubs = [i for i in range(len(units)) if degree[i] and units[i]["kind"] in ("function", "method", "class") and units[i]["sig"]
            and i in node_of_unit]
    if hubs and edge_basis == "resolved":      # the piece with most resolved calls in and out; its module is the one we open
        hubs.sort(key=lambda i: (-degree[i], -units[i]["nl"], units[i]["id"]))
        focus = {"node": node_of_unit[hubs[0]], "unit": hubs[0]}
    cands = [] if focus["unit"] is not None else [n for n in nodes if len(n["units"]) >= 3]
    if cands:
        cands.sort(key=lambda n: (len(n["units"]), len(n["title"]), n["id"]))
        mid = len(cands) // 2   # median unit count; ties: shorter title
        # nearest to the median first; a module is usable when it has a function, method or class with a signature
        for k in sorted(range(len(cands)), key=lambda k: (abs(k - mid), k)):
            mod = cands[k]
            funcs = [i for i in mod["units"] if units[i]["kind"] in ("function", "method", "class") and units[i]["sig"]]
            if funcs:
                funcs.sort(key=lambda i: (-callers[i], -units[i]["nl"], units[i]["id"]))
                focus = {"node": mod["id"], "unit": funcs[0]}
                break
    find = None
    if focus["unit"] is not None:
        fu = units[focus["unit"]]
        parts = fu["id"].split("::")        # methods: the qualified name (Class.method) is what `cbe find` ranks first
        term = parts[2] if len(parts) > 3 and parts[1] in ("method", "function", "class") and parts[2] else fu["name"]
        run_dir = args.run_dir or str(path.resolve().parent)
        find_txt = run_cbe(args.cbe_python, args.cbe_src, ["find", "--run-dir", run_dir, "--term", term, "--limit", "1"])
        via, raw_find, raw_src = "cbe find (real)", None, None
        row = None
        if find_txt and find_txt.strip():
            raw_find = find_txt.strip().splitlines()[0]
            f = [x.strip() for x in raw_find.split(" | ")]
            if len(f) >= 5:
                row = {"id": f[1], "name": f[0], "location": f[3], "summary": f[4]}
        if row is None:  # fallback: exact name first, then catalog order
            via = "fallback"
            row = {"id": fu["id"], "name": fu["name"], "location": fu["loc"], "summary": fu["summary"]}
        else:
            src_txt = run_cbe(args.cbe_python, args.cbe_src, ["source", "--run-dir", run_dir, "--id", row["id"]])
            if src_txt:
                raw_src = src_txt.rstrip("\n").splitlines()
        hit_idx = unit_index.get(row["id"])
        hit = units[hit_idx] if hit_idx is not None else fu
        sig_lines = hit["sig"].splitlines()
        find = {
            "term": term, "via": via, "raw": raw_find, "src_raw": raw_src,
            "hit": {"id": row["id"], "name": row["name"], "loc": row["location"], "summary": row["summary"]},
            "source": {"id": hit["id"], "loc": hit["loc"], "line": hit["l1"], "sig": sig_lines[0].strip() if sig_lines else "",
                       "more": hit["l2"] - hit["l1"]},
        }
    out = {
        "name": args.name, "from": f"{path.name}",
        "stats": {"files": len(files), "tokens": sum(f["tokens"] for f in files), "units": len(units)},
        "files": files, "units": units, "pairs": pairs, "nodes": nodes,
        "edge_basis": edge_basis, "roots": roots, "skipped_empty_nodes": skipped, "focus": focus, "find": find,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{args.out}: {len(units)} units, {len(pairs)} unit pairs ({edge_basis}), {len(nodes)} nodes "
          f"({len(skipped)} empty skipped), {len(files)} files, focus={focus}, find={find and find['term']}")


if __name__ == "__main__":
    main()
