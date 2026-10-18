"""Pick the 10 E5 answers for the judge spot-check (REPORT_RULES.md, 判分抽查).

Written by the main session on 10-18 before it read any E5 answer or score.
Rule: all three arms, mostly layers 3 and 4. Arms S 3, C0 3, C 4; per arm
one answer from layers 1-2 for S and C0 (none for C), the rest from layers
3-4, so 8 of 10 are layer 3-4. Draws use random.Random(20261020) on the
sorted cids of each (arm, layer band), arms in the order S, C0, C; a cid is
not reused across arms, so the 10 answers cover 10 different questions.
"""
import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUESTIONS_SHA = "597ed0c8ea1685787de7b6ec5fadeace4d5b7ad9d0ff166d7f2def198b2440cd"
SEED = 20261020
PLAN = [("S", "12", 1), ("S", "34", 2), ("C0", "12", 1), ("C0", "34", 2), ("C", "34", 4)]


def main():
    qp = HERE / "questions_frozen.jsonl"
    assert hashlib.sha256(qp.read_bytes()).hexdigest() == QUESTIONS_SHA
    qs = [json.loads(l) for l in qp.read_text().splitlines() if l.strip()]
    band = {q["cid"]: ("12" if q["label_layer"] <= 2 else "34") for q in qs}
    layer = {q["cid"]: q["label_layer"] for q in qs}
    rng = random.Random(SEED)
    used, picks = set(), []
    for arm, b, k in PLAN:
        pool = sorted(c for c in band if band[c] == b and c not in used)
        for c in sorted(rng.sample(pool, k)):
            used.add(c)
            picks.append({"arm": arm, "cid": c, "label_layer": layer[c]})
    out = {"rule": __doc__.strip(), "seed": SEED, "questions_sha256": QUESTIONS_SHA,
           "picks": picks}
    (HERE / "spotcheck_selection.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(picks, ensure_ascii=False))


if __name__ == "__main__":
    main()
