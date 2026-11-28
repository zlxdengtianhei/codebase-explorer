"""Compare replayed module-tree rows with the frozen numbers in replay_expected.json.

  check_replay.py [ROWS.jsonl] [--expected FILE]

ROWS defaults to $RUNNER_TEMP/rows.jsonl (CI). Without a rows file the rows are computed here with
`run.row(repo, "T0", ..., do_c=False)`, the same as `run.py row <repo> T0 --no-c`.
Gated per repo: levels.leaf.modules, A.empty (exact), B1.leaf.q, B2.leaf.q (within 1e-6), and C must be
empty (no model ran). Other fields of the stored row are compared for information only.
Exit 1 on any gated mismatch.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOL = 1e-6
FIELDS = (("leaf_modules", lambda r: r["levels"]["leaf"]["modules"], False),
          ("A.empty", lambda r: r["A"]["empty"], False),
          ("B1.leaf.q", lambda r: r["B1"]["leaf"]["q"], True),
          ("B2.leaf.q", lambda r: r["B2"]["leaf"]["q"], True))


def same(e, a, approx: bool) -> bool:
    if approx:
        return isinstance(a, (int, float)) and not math.isnan(a) and abs(a - e) <= TOL
    return type(a) is int and a == e


def diff_paths(e, a, path="") -> list[str]:
    """Paths where two JSON values differ (floats within TOL count as equal)."""
    if isinstance(e, dict) and isinstance(a, dict):
        return [p for k in sorted(set(e) | set(a)) for p in diff_paths(e.get(k), a.get(k), f"{path}.{k}" if path else k)]
    if isinstance(e, list) and isinstance(a, list) and len(e) == len(a):
        return [p for i, (x, y) in enumerate(zip(e, a)) for p in diff_paths(x, y, f"{path}[{i}]")]
    if isinstance(e, float) and isinstance(a, (int, float)):
        return [] if (math.isnan(e) and math.isnan(a)) or abs(e - a) <= TOL else [path]
    return [] if e == a else [path]


def load_rows(path: Path | None, repos: list[str]) -> dict[str, dict]:
    if path is not None and path.exists():
        rows = {}
        for line in open(path):
            if line.strip():
                r = json.loads(line)
                rows[r["repo"]] = r
        return rows
    print(f"no rows file{f' at {path}' if path else ''}; computing rows with run.row(..., do_c=False)")
    import run
    return {name: run.row(name, "T0", None, [], False) for name in repos}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    rt = os.environ.get("RUNNER_TEMP")
    ap.add_argument("rows", nargs="?", default=str(Path(rt) / "rows.jsonl") if rt else None)
    ap.add_argument("--expected", default=str(HERE / "replay_expected.json"))
    a = ap.parse_args()
    exp = json.load(open(a.expected))
    expected = exp["rows"]
    rows = load_rows(Path(a.rows) if a.rows else None, [e["repo"] for e in expected])
    print(f"expected: {a.expected} (measured on {exp.get('measured_on', '?')})")
    print(f"| repo | field | expected | actual | verdict |\n|---|---|---|---|---|")
    bad = 0
    for e in expected:
        name, r = e["repo"], rows.get(e["repo"])
        if r is None:
            print(f"| {name} | row | present | missing | FAIL |")
            bad += 1
            continue
        for field, get, approx in FIELDS:
            try:
                got = get(r)
            except (KeyError, TypeError):
                got = None
            ok = same(e[field], got, approx)
            bad += not ok
            fmt = (lambda x: f"{x:.6f}" if isinstance(x, float) else str(x)) if approx else str
            print(f"| {name} | {field} | {fmt(e[field])} | {fmt(got) if got is not None else 'missing'} | {'ok' if ok else 'FAIL'} |")
        c = r.get("C")
        ok = c == {}
        bad += not ok
        print(f"| {name} | C | {{}} | {json.dumps(c)[:40] if c else c} | {'ok' if ok else 'FAIL'} |")
    for e in expected:
        r = rows.get(e["repo"])
        if r is not None and "row" in e:
            d = diff_paths(e["row"], r)
            if d:
                print(f"info: {e['repo']}: {len(d)} other field(s) differ from the stored row (not gated): {', '.join(d[:8])}"
                      + (" ..." if len(d) > 8 else ""))
    extra = sorted(set(rows) - {e["repo"] for e in expected})
    if extra:
        print("info: rows with no expected entry (not gated): " + ", ".join(extra))
    print(f"{'FAIL' if bad else 'PASS'}: {bad} mismatch(es)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
