"""Select and freeze the 40 E5 (curl) questions before any answering.

Rule (D-71): independent labels (label/labels.json) decide type and layer.
Types 10 each. Layers take what exists: layer 1 all, layer 2 What and How
(Why is full from layer 4), layer 4 What all and Why 10 of 11, layer 3 fills
the rest by type. Random draws inside a cell use random.Random(SEED) on the
sorted cids of that cell, cells in fixed order. Closed-book scores are only
used for the >=70 exclusion (none excluded); answers do not exist yet.
Secondary comparison: 20 of the 40, layer-stratified 1/4/9/6 (largest
remainder, tie to the higher layer), random.Random(SEED + 1).
"""
import copy
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = 20261018
EXPECTED = {
    "A": "67e128d378d5ab82b256f4c0e19912e243ed0f1a0d9816c05f229df52faee187",
    "B": "94dad9d9ae901061c20c939dd76b8d61857cb2dbece7043229adc2d2021dfcdb",
}
SPOTCHECK = ["B02", "A12", "B03", "A23", "A25", "B24", "A06", "B16"]
# (type, layer): how many to take; None = all available
PLAN = [
    (("Where", 1), None),
    (("What", 2), None),
    (("How", 2), None),
    (("What", 4), None),
    (("Why", 4), 10),
    (("What", 3), 4),
    (("How", 3), 7),
    (("Where", 3), 7),
]
SECONDARY = {1: 1, 2: 4, 3: 9, 4: 6}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    qs = {}
    for half in "AB":
        p = ROOT / f"verify/{half}/questions_verified.jsonl"
        assert sha(p) == EXPECTED[half], f"{p} changed"
        for line in p.read_text().splitlines():
            if line.strip():
                q = json.loads(line)
                qs[q["cid"]] = q
    assert len(qs) == 55
    labels = {x["cid"]: x for x in json.loads((ROOT / "label/labels.json").read_text())["labels"]}
    filt = json.loads((ROOT / "judge/filter.json").read_text())
    assert filt["excluded_cids"] == [] and filt["threshold"] == 70
    anchors = {a["id"]: a for a in json.loads((ROOT / "prep/anchors.json").read_text())["anchors"]}
    adj = json.loads((ROOT / "adjudications.json").read_text())

    cells = {}
    for cid in sorted(qs):
        lab = labels[cid]
        cells.setdefault((lab["swe_type"], lab["layer"]), []).append(cid)
    rng = random.Random(SEED)
    chosen, cell_log = [], []
    for cell, k in PLAN:
        pool = cells.get(cell, [])
        pick = sorted(pool) if k is None else sorted(rng.sample(pool, k))
        chosen += pick
        cell_log.append({"type": cell[0], "layer": cell[1], "available": len(pool),
                         "taken": len(pick), "cids": pick,
                         "left_out": [c for c in pool if c not in pick]})
    chosen = sorted(chosen)
    assert len(chosen) == 40 and len(set(chosen)) == 40
    unplanned = {f"{t}/{l}": v for (t, l), v in cells.items() if (t, l) not in [c for c, _ in PLAN]}

    frozen = []
    for cid in chosen:
        q = copy.deepcopy(qs[cid])
        applied = []
        for a in adj["items"]:
            if a["cid"] != cid:
                continue
            if cid == "B16":
                for r in q["rubric"]:
                    if r["id"] in ("r3", "r4"):
                        assert r["kind"] == "core" and r["weight"] == 2
                        r["kind"], r["weight"] = "support", 1
                applied.append(a["change"])
            elif cid == "B11":
                r1 = [r for r in q["rubric"] if r["id"] == "r1"][0]
                r1["text"] = a["new_text"]
                applied.append(a["change"])
        anc = anchors.get(q.get("anchor"))
        q["label_swe_type"] = labels[cid]["swe_type"]
        q["label_layer"] = labels[cid]["layer"]
        q["dispatch_anchor"] = bool(anc and anc.get("is_dispatch"))
        q["spotchecked"] = cid in SPOTCHECK
        q["closed_book_score"] = next(x["score"] for x in filt["questions"] if x["cid"] == cid)
        q["adjudications_applied"] = applied
        cores = [r for r in q["rubric"] if r["kind"] == "core"]
        assert len(cores) >= 2, cid
        frozen.append(q)

    rng2 = random.Random(SEED + 1)
    by_layer = {}
    for q in frozen:
        by_layer.setdefault(q["label_layer"], []).append(q["cid"])
    secondary = []
    for layer in (1, 2, 3, 4):
        secondary += sorted(rng2.sample(sorted(by_layer[layer]), SECONDARY[layer]))
    secondary = sorted(secondary)
    assert len(secondary) == 20

    out = Path(__file__).resolve().parent
    with open(out / "questions_frozen.jsonl", "w") as f:
        for q in frozen:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    with open(out / "curl_sweqa.jsonl", "w") as f:
        for i, q in enumerate(frozen):
            f.write(json.dumps({"qid": i, "cid": q["cid"], "question": q["question"],
                                "build_assumptions": q["build_assumptions"],
                                "answer": q["reference_answer"]}, ensure_ascii=False) + "\n")
    cb = sorted(q["closed_book_score"] for q in frozen)
    summary = {
        "seed": SEED, "secondary_seed": SEED + 1, "rule": __doc__.strip(),
        "inputs": {"A": EXPECTED["A"], "B": EXPECTED["B"],
                   "labels": sha(ROOT / "label/labels.json"),
                   "filter": sha(ROOT / "judge/filter.json"),
                   "adjudications": sha(ROOT / "adjudications.json"),
                   "anchors": sha(ROOT / "prep/anchors.json")},
        "cells": cell_log, "cells_not_used": unplanned,
        "left_out_total": sorted(set(qs) - set(chosen)),
        "layer_counts": dict(sorted(Counter(q["label_layer"] for q in frozen).items())),
        "type_counts": dict(sorted(Counter(q["label_swe_type"] for q in frozen).items())),
        "layer34_share": sum(q["label_layer"] >= 3 for q in frozen) / 40,
        "dispatch_anchor_count": sum(q["dispatch_anchor"] for q in frozen),
        "dispatch_anchor_layer34": sum(q["dispatch_anchor"] and q["label_layer"] >= 3 for q in frozen),
        "spotchecked_in_40": [q["cid"] for q in frozen if q["spotchecked"]],
        "closed_book_median_40": (cb[19] + cb[20]) / 2,
        "closed_book_zero_count_40": sum(s == 0 for s in cb),
        "secondary20": secondary,
        "secondary_layer_counts": dict(sorted(Counter(next(q["label_layer"] for q in frozen if q["cid"] == c) for c in secondary).items())),
        "chosen": chosen,
    }
    (out / "selection.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({k: summary[k] for k in ("layer_counts", "type_counts", "layer34_share",
          "dispatch_anchor_count", "dispatch_anchor_layer34", "spotchecked_in_40",
          "closed_book_median_40", "closed_book_zero_count_40", "secondary_layer_counts",
          "left_out_total", "cells_not_used")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
