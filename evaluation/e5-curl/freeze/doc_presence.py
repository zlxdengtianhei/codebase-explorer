"""Label each frozen E5 question: are its key units in the CBE docs?

Written by the main session after E5a generation and before any E5 answer
exists (REPORT_RULES.md, "关键单元是否在 CBE 文档里"; D-71).

Rule as applied:
- Read the `source` of every core rubric item. Split on ';' into entries.
  An entry "path: n1, n2" gives the pairs (path, n1), (path, n2). An entry
  without ':' names only a file: it has no function, is recorded under
  `file_only`, and does not change the label.
- Name clean-up: drop a leading "struct ", "union " or "enum ", a trailing
  "()" and a trailing " comment" (B16 writes "... comment").
- Pair status from catalog.json `symbols` with the same `file` and `name`:
  "unit" if any such symbol has its own unit, else "grouped" if any is a
  member of a group unit, else "index_only" if any is index-only, else
  "missing" (no symbol with that file and name).
- Label `in_docs` ("在"): every pair is "unit" or "grouped", i.e. described
  in a CBE unit (its own or a group unit that lists it). Otherwise "不在".
  This label is the one E5qa reports by.
- `own_unit` (informational, not reported by): every pair is "unit".
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUESTIONS_SHA = "597ed0c8ea1685787de7b6ec5fadeace4d5b7ad9d0ff166d7f2def198b2440cd"
RUN = Path.home() / "clones/cbe_lab1_20261016/runs/e5/cbe-curl/run"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def clean(name):
    n = name.strip()
    for pre in ("struct ", "union ", "enum "):
        if n.startswith(pre):
            n = n[len(pre):]
    if n.endswith(" comment"):
        n = n[: -len(" comment")]
    if n.endswith("()"):
        n = n[:-2]
    return n.strip()


def parse_source(src):
    pairs, file_only = [], []
    for ent in src.split(";"):
        ent = ent.strip()
        if not ent:
            continue
        if ":" in ent:
            path, names = ent.split(":", 1)
            for n in names.split(","):
                if n.strip():
                    pairs.append((path.strip(), clean(n), n.strip()))
        else:
            file_only.append(ent)
    return pairs, file_only


def main():
    qpath = HERE / "questions_frozen.jsonl"
    assert sha(qpath) == QUESTIONS_SHA, "questions_frozen.jsonl changed"
    cat_path = RUN / "catalog.json"
    cat = json.loads(cat_path.read_text())
    units = cat["units"]
    by_key = {}
    for sid, s in cat["symbols"].items():
        by_key.setdefault((s.get("file"), s.get("name")), []).append((sid, s))

    def status(path, name):
        hits = by_key.get((path, name), [])
        hows = {s.get("how") for _, s in hits}
        for sid, s in hits:
            if s.get("how") == "unit":
                assert s.get("unit") in units, sid
            if s.get("how") == "grouped":
                g = units.get(s.get("unit"))
                assert g and sid in g.get("members", []) + g.get("folded_members", []), sid
        for h in ("unit", "grouped", "index_only"):
            if h in hows:
                return h, [sid for sid, _ in hits]
        return "missing", []

    out, counts = [], Counter()
    for line in qpath.read_text().splitlines():
        if not line.strip():
            continue
        q = json.loads(line)
        pairs, file_only = [], []
        for r in q["rubric"]:
            if r["kind"] != "core":
                continue
            p, fo = parse_source(r["source"])
            pairs += [(r["id"],) + x for x in p]
            file_only += [(r["id"], x) for x in fo]
        rows = []
        for rid, path, name, raw in pairs:
            st, ids = status(path, name)
            rows.append({"rubric": rid, "file": path, "name": name, "as_written": raw,
                         "status": st, "symbols": ids})
        if rows:
            in_docs = all(x["status"] in ("unit", "grouped") for x in rows)
            own = all(x["status"] == "unit" for x in rows)
        else:
            in_docs = own = None
        counts["in" if in_docs else ("none" if in_docs is None else "out")] += 1
        out.append({"cid": q["cid"], "label_layer": q["label_layer"],
                    "label_swe_type": q["label_swe_type"],
                    "in_docs": in_docs, "label": {True: "在", False: "不在", None: "无可判"}[in_docs],
                    "own_unit": own,
                    "not_in_docs": [f'{x["file"]}: {x["name"]} ({x["status"]})'
                                    for x in rows if x["status"] not in ("unit", "grouped")],
                    "pairs": rows,
                    "file_only": [{"rubric": rid, "file": f} for rid, f in file_only]})

    status_md = (RUN / "STATUS.md").read_text().splitlines()[2] if (RUN / "STATUS.md").exists() else ""
    summary = {
        "rule": __doc__.strip(),
        "inputs": {"questions_frozen.jsonl": QUESTIONS_SHA,
                   "catalog.json": sha(cat_path), "catalog_path": str(cat_path),
                   "run_status_line": status_md},
        "counts": {"在": counts["in"], "不在": counts["out"], "无可判": counts["none"]},
        "own_unit_count": sum(1 for x in out if x["own_unit"]),
        "pair_status": dict(Counter(p["status"] for x in out for p in x["pairs"])),
        "questions": out,
    }
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "doc_presence.json"
    dest.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("counts", "own_unit_count", "pair_status")},
                     ensure_ascii=False))
    for x in out:
        if not x["in_docs"]:
            print(x["cid"], x["label_layer"], x["not_in_docs"])


if __name__ == "__main__":
    main()
