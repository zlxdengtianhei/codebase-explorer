#!/usr/bin/env python3
"""Draw the 10-question sample from labels.json.  Run: python3 -I draw.py

Rule (same shape as flask runs/e1/questions/sample.json):
  1. Type quotas What/How/Why/Where = 3/3/2/2.
  2. A layer with exactly 1 question in the whole bank is included with certainty;
     it uses one slot of its type's quota.
  3. The remaining slots of a type are split over the layers of that type by
     largest remainder of quota * (layer count in type / type count).
     Floors first; leftover slots go by descending remainder.  A remainder tie goes
     to a layer not yet present in the sample (earlier types and floors count),
     then to the layer with fewer sampled questions, then to the lower layer number.
     Arithmetic uses fractions, so there is no float tie error.
  4. Inside a (type, layer) cell, draw the allocated number of qids with
     random.Random(20261017).sample over the sorted qid list; cells are visited
     in order What, How, Why, Where, then layer 1..4.
"""
import json
import random
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

SEED = 20261017
TYPES = ["What", "How", "Why", "Where"]
QUOTA = {"What": 3, "How": 3, "Why": 2, "Where": 2}
HERE = Path(__file__).resolve().parent

labels = json.loads((HERE / "labels.json").read_text())["labels"]
cells = defaultdict(list)  # (type, layer) -> qids
for lab in labels:
    cells[(lab["swe_type"], lab["layer"])].append(lab["qid"])
for v in cells.values():
    v.sort()
layer_total = defaultdict(int)
for (t, l), v in cells.items():
    layer_total[l] += len(v)
sole_layers = {l for l, n in layer_total.items() if n == 1}

alloc = {}  # type -> {layer: n}
present = set()  # layers already in the sample
for t in TYPES:
    layers = sorted(l for (tt, l) in cells if tt == t)
    n_type = sum(len(cells[(t, l)]) for l in layers)
    got = {l: 0 for l in layers}
    # certain inclusion of sole layers
    for l in layers:
        if l in sole_layers:
            got[l] = 1
    left = QUOTA[t] - sum(got.values())
    free = [l for l in layers if l not in sole_layers]
    n_free = sum(len(cells[(t, l)]) for l in free)
    ideal = {l: Fraction(left * len(cells[(t, l)]), n_free) for l in free}
    for l in free:
        got[l] = int(ideal[l])  # floor
    left -= sum(int(ideal[l]) for l in free)
    present |= {l for l in layers if got[l] > 0}
    while left > 0:
        rem = {l: ideal[l] - int(ideal[l]) for l in free
               if got[l] < len(cells[(t, l)]) and ideal[l] - int(ideal[l]) >= 0}
        # candidates that have not yet taken a remainder slot
        cand = [l for l in free if got[l] == int(ideal[l]) and got[l] < len(cells[(t, l)])]
        best = max(rem[l] for l in cand)
        tied = [l for l in cand if rem[l] == best]
        new = [l for l in tied if l not in present]
        pick = sorted(new or tied, key=lambda l: (got[l], l))[0]
        got[pick] += 1
        present.add(pick)
        left -= 1
    alloc[t] = got

rng = random.Random(SEED)
qids = []
for t in TYPES:
    for l in sorted(alloc[t]):
        k = alloc[t][l]
        if k:
            qids.extend(rng.sample(cells[(t, l)], k))
qids_sorted = sorted(qids)

result = {
    "seed": SEED,
    "qid_base": 0,
    "qids": qids_sorted,
    "design": ("Type quotas What/How/Why/Where = 3/3/2/2 on swe_type from labels.json. A layer with only 1 question "
               "in the whole bank would be included with certainty (none here: layer 1 has 4). Remaining slots per "
               "type use largest-remainder allocation over layers by in-type proportion (floors first; remainder "
               "ties go to a layer not yet in the sample, then to the layer with fewer sampled questions, then to "
               "the lower layer). Inside each (type, layer) cell, qids are drawn with random.Random(20261017).sample "
               "over the sorted qid list, cells visited in order What, How, Why, Where and layer 1..4."),
    "cell_sizes": {t: {str(l): len(cells[(t, l)]) for l in sorted(l for (tt, l) in cells if tt == t)} for t in TYPES},
    "allocation": {t: {str(l): n for l, n in sorted(alloc[t].items())} for t in TYPES},
    "drawn_by_cell": {},
}
by_qid = {lab["qid"]: lab for lab in labels}
for q in qids_sorted:
    lab = by_qid[q]
    result["drawn_by_cell"].setdefault(lab["swe_type"], {}).setdefault(str(lab["layer"]), []).append(q)
(HERE / "sample.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
