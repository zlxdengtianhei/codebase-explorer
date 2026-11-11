"""Commands for the module-tree scales.

  run.py commits [repo ...]                       choose the 30 commits per repo (writes commits/<repo>.json)
  run.py row REPO TREE [--match TREE] [--models a,b] [--no-c] [--out rows.jsonl]
        TREE is T0 (the tree in the catalog), T1 (directories) or a path to a tree json file.
        One JSON line: A, B1, B2 at three levels, C at two views.
  run.py table rows.jsonl [...]                   Markdown tables from row files
  run.py all                                      commits + rows for T0 and T1 on every repo + results/table.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import commits as commits_mod
import locate
import measures
from common import HERE, LAB, REPOS, Repo, Tree, load_tree, view_groups

LEVELS = ("leaf", "up1", "top")


def get_tree(repo: Repo, spec: str) -> Tree:
    if spec == "T0":
        return repo.tree0()
    if spec == "T1":
        return repo.tree1()
    if spec == "T1f":
        return repo.tree1(files=True)
    return load_tree(spec)


def cuts(repo: Repo, tree: Tree, match: Tree | None) -> dict[str, tuple[dict, dict]]:
    """level -> (unit->group label, info). A directory tree is cut at the depth whose module count is
    closest to the matched tree's count at the same level; other trees use their own leaf/up1/top cuts."""
    own = {lv: tree.cut(lv, repo.units) for lv in LEVELS}
    if not (tree.name.startswith("T1-") and match is not None):
        return {lv: (own[lv], dict(modules=len(view_groups(repo, tree, own[lv])))) for lv in LEVELS}
    out = {}
    maxd = max(tree.depth(n) for n in tree.nodes)
    for lv in LEVELS:
        target = len(view_groups(repo, match, match.cut(lv, repo.units)))
        best = None
        for k in range(0, maxd + 1):
            lab = tree.cut(f"depth:{k}", repo.units)
            n = len(view_groups(repo, tree, lab))
            if best is None or abs(n - target) < abs(best[1] - target):
                best = (k, n, lab)
        out[lv] = (best[2], dict(modules=best[1], depth=best[0], match_target=target))
    return out


def row(repo_name: str, tree_spec: str, match_spec: str | None, models: list[str], do_c: bool, target: int | None = None) -> dict:
    repo = Repo(repo_name)
    tree = get_tree(repo, tree_spec)
    match = get_tree(repo, match_spec) if match_spec else (repo.tree0() if tree.name.startswith("T1-") else None)
    res = dict(repo=repo_name, tree=tree.name, matched_to=match.name if match and tree.name.startswith("T1-") else None,
               A=measures.scale_a(repo, tree), levels={}, B1={}, B1_with_relations={}, B2={}, C={})
    cs = cuts(repo, tree, match)
    for lv, (label, info) in cs.items():
        res["levels"][lv] = info
        res["B1"][lv] = measures.b1(repo, label, "call")
        res["B1_with_relations"][lv] = measures.b1(repo, label, "all")
        res["B2"][lv] = measures.b2(repo, label)
    if do_c:
        cm = commits_mod.load(repo_name)["selected"]
        views = ("leaf",) if tree.name.startswith("T1f-") else LEVELS
        if target is not None:   # one view only: the level whose module count is closest to the target (ties: finer)
            views = (min(LEVELS, key=lambda lv: (abs(res["levels"][lv]["modules"] - target), LEVELS.index(lv))),)
        for lv in views:
            res["C"][lv] = locate.run_view(repo, tree, cs[lv][0], cm, models, lv)
    return res


# ----------------------------------------------------------------- table

def f(x, d=3):
    return "n/a" if x is None or x != x else f"{x:.{d}f}"


def table(files: list[str]) -> str:
    rows = [json.loads(l) for p in files for l in open(p) if l.strip()]
    order = {r: i for i, r in enumerate(REPOS)}
    rows.sort(key=lambda r: (order.get(r["repo"], 99), r["tree"], r.get("matched_to") or ""))
    out = ["## A. Self-consistency (counts; lower is better)", "",
           "| repo | tree | nodes | empty | sibling dup titles | dup titles anywhere | dup capability | near-dup capability pairs | unit cover faults | source files no unit covers | their lines / all non-test lines |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        a = r["A"]
        out.append(f"| {r['repo']} | {r['tree']} | {a['nodes']} | {a['empty']} | {a['sibling_dup_title']} | {a['dup_title_anywhere']} | "
                   f"{a['dup_capability']} | {a['near_dup_capability_pairs']} | {a['unit_cover_faults']} | "
                   f"{a['uncovered_source_files']} | {a['uncovered_source_lines']}/{a['nontest_lines']} |")
    for key, title in (("B1", "B1. Static cohesion: modularity Q on resolved call edges between units"),
                       ("B1_with_relations", "B1x. Same, with model-inferred relation edges added"),
                       ("B2", "B2. Co-change agreement: soft-membership modularity Q on the co-change graph")):
        out += ["", f"## {title}", "",
                "Each cell: Q (random Q) [modules]. Random = same group sizes, unit labels shuffled, mean of 30."
                + (" Second random value for B2 is whole-file shuffle." if key == "B2" else ""), "",
                "| repo | tree | leaf | up1 (one level above leaf) | top |", "|---|---|---|---|---|"]
        for r in rows:
            cells = []
            for lv in LEVELS:
                b = r[key][lv]
                if key == "B2":
                    rnd = f"{f(b['rand_unit'])} / {f(b['rand_file'])}"
                else:
                    rnd = f(b["rand"])
                cells.append(f"{f(b['q'])} ({rnd}) [{r['levels'][lv]['modules']}]")
            tag = r["tree"] + (f" (depth-matched to {r['matched_to']})" if r.get("matched_to") else "")
            out.append(f"| {r['repo']} | {tag} | " + " | ".join(cells) + " |")
    models = sorted({m for r in rows for v in r["C"].values() for m in v["models"]})
    for m in models:
        out += ["", f"## C. Locating a change: model `{m}`", "",
                "Recall (95% bootstrap interval over the 30 commits), share of source lines chosen, lift = recall / share. "
                "Reference rows below give random-3, largest-3 and best-possible-3 recall for the same page.", "",
                "| repo | tree | view | modules | recall | share | lift | tokens per question | page tokens | no valid answer | random-3 recall | largest-3 recall | best-3 recall |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            for lv, v in r["C"].items():
                if m not in v["models"]:
                    continue
                x, ref = v["models"][m], v["reference"]
                tag = r["tree"] + (f" (depth {r['levels'][lv]['depth']})" if r.get("matched_to") else "")
                out.append(f"| {r['repo']} | {tag} | {lv} | {v['modules']} | {f(x['recall'], 2)} ({f(x['recall_ci95'][0], 2)}-{f(x['recall_ci95'][1], 2)}) | {f(x['share'], 2)} | {f(x['lift'], 2)} | "
                           f"{x['tokens_per_q']:.0f} | {v['page_tokens']} | {x['no_valid_answer']} | {f(ref['random3_recall'], 2)} | "
                           f"{f(ref['largest3_recall'], 2)} | {f(ref['oracle3_recall'], 2)} |")
    return "\n".join(out) + "\n"


TREE_DIR = Path(os.environ.get("CBE_EVAL_TREES", LAB / "trees"))   # candidate tree files (T2/T3/T3m per repo)


def compare(files: list[str]) -> str:
    """Side-by-side of every tree: for each repo, the C view whose module count is closest to the T0 one-level-above-leaf count.
    Differences use paired bootstrap over the 30 commits on 'excess recall' = recall minus the random-3 recall of the same page."""
    import random
    rows = [json.loads(l) for p in files for l in open(p) if l.strip()]
    by = {}
    for r in rows:
        by[(r["repo"], r["tree"].split("-")[0])] = r
    models = sorted({m for r in rows for v in r["C"].values() for m in v["models"]})
    out = ["# Trees side by side", "",
           "For each repo the target size is the module count of T0 one level above the leaf. Each tree uses the C view (leaf, up1 or top) whose "
           "module count is closest to it (ties go to the finer view); T1 uses the directory depth matched to T0's up1; T1f has one module per file. "
           "Excess recall = recall minus the recall of picking 3 modules at random on the same page.", ""]
    names = [n for n in ("T0", "T1", "T1f", "T2", "T3", "T3m") if any(k[1] == n for k in by)]
    def pick(r, target):
        best = None
        for lv, v in r["C"].items():
            d = abs(v["modules"] - target)
            if best is None or d < best[0]:
                best = (d, lv)
        return best[1]
    for m in models:
        out += [f"## C with `{m}`", "", "| repo | tree | view | modules | recall | share | excess recall | lift | B1 Q at that level | B2 Q at that level | empty nodes |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for repo in REPOS:
            t0 = by.get((repo, "T0"))
            if not t0:
                continue
            target = t0["C"]["up1"]["modules"]
            for n in names:
                r = by.get((repo, n))
                if not r:
                    continue
                lv = "up1" if n == "T1" else pick(r, target)
                v = r["C"][lv]
                x, ref = v["models"][m], v["reference"]
                out.append(f"| {repo} | {n} | {lv} | {v['modules']} | {f(x['recall'], 2)} | {f(x['share'], 2)} | {f(x['recall'] - ref['random3_recall'], 2)} | {f(x['lift'], 2)} | "
                           f"{f(r['B1'][lv]['q'])} | {f(r['B2'][lv]['q'])} | {r['A']['empty']} |")
        out.append("")
    out += ["## Paired differences in excess recall (row tree minus column tree), 95% bootstrap interval over the 30 commits", "",
            "A difference is called 'cannot tell' when the interval holds zero. Share of source lines differs between trees; read it with the table above.", "",
            "Column 'modules' gives the module counts of the two views; when one is more than 1.5 times the other, the pair is flagged because excess recall at very different sizes is not a fair comparison.", "",
            "| repo | model | comparison | modules | difference | 95% interval | verdict |", "|---|---|---|---|---|---|---|"]
    rng = random.Random(5)
    for repo in REPOS:
        t0 = by.get((repo, "T0"))
        if not t0:
            continue
        target = t0["C"]["up1"]["modules"]
        for m in models:
            def size(n):
                r = by.get((repo, n))
                lv = "up1" if n == "T1" else pick(r, target)
                return r["C"][lv]["modules"]

            def excess(n):
                r = by.get((repo, n))
                if not r:
                    return None
                lv = "up1" if n == "T1" else pick(r, target)
                v = r["C"][lv]
                return [a - b for a, b in zip(v["models"][m]["recall_per_q"], v["reference"]["random3_per_q"])]
            for a, b in (("T3", "T0"), ("T3", "T1"), ("T2", "T0"), ("T3", "T2"), ("T3m", "T3")):
                ea, eb = excess(a), excess(b)
                if ea is None or eb is None:
                    continue
                d = [x - y for x, y in zip(ea, eb)]
                n = len(d)
                boots = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(2000))
                lo, hi = boots[49], boots[1949]
                verdict = "cannot tell" if lo <= 0 <= hi else ("first is better" if lo > 0 else "first is worse")
                sa, sb = size(a), size(b)
                flag = " (sizes too different)" if max(sa, sb) > 1.5 * min(sa, sb) else ""
                out.append(f"| {repo} | {m} | {a} - {b} | {sa} / {sb} | {sum(d)/n:+.2f} | {lo:+.2f} to {hi:+.2f} | {verdict}{flag} |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("commits").add_argument("repos", nargs="*")
    p = sub.add_parser("row")
    p.add_argument("repo"); p.add_argument("tree"); p.add_argument("--match"); p.add_argument("--models", default=",".join(locate.MODELS))
    p.add_argument("--no-c", action="store_true"); p.add_argument("--out")
    sub.add_parser("table").add_argument("files", nargs="+")
    sub.add_parser("compare").add_argument("files", nargs="+")
    p = sub.add_parser("trees"); p.add_argument("--models", default=",".join(locate.MODELS))
    p = sub.add_parser("all"); p.add_argument("--models", default=",".join(locate.MODELS)); p.add_argument("--no-c", action="store_true")
    a = ap.parse_args()
    if a.cmd == "commits":
        commits_mod.write_all(a.repos or None)
    elif a.cmd == "row":
        r = row(a.repo, a.tree, a.match, a.models.split(","), not a.no_c)
        line = json.dumps(r)
        if a.out:
            open(a.out, "a").write(line + "\n")
        print(line)
    elif a.cmd == "table":
        sys.stdout.write(table(a.files))
    elif a.cmd == "compare":
        sys.stdout.write(compare(a.files))
    elif a.cmd == "trees":      # T2, T3, T3m tree files from the skeleton work, five repos each
        outp = HERE / "results" / "rows_trees.jsonl"
        outp.write_text("")
        for name in REPOS:
            for t in ("T2", "T3", "T3m"):
                fpath = TREE_DIR / f"{t}-{name}.json"
                if not fpath.exists():
                    continue
                t0 = Repo(name)
                target = len(view_groups(t0, t0.tree0(), t0.tree0().cut("up1", t0.units)))
                r = row(name, str(fpath), None, a.models.split(","), True, target)
                open(outp, "a").write(json.dumps(r) + "\n")
                print("done", name, t, flush=True)
    elif a.cmd == "all":
        res = HERE / "results"
        res.mkdir(exist_ok=True)
        for name in REPOS:
            if not (HERE / "commits" / f"{name}.json").exists():
                commits_mod.write_all([name])
        outp = res / "rows_T0_T1.jsonl"
        if not outp.exists():
            outp.write_text("")
        done = {(json.loads(l)["repo"], json.loads(l)["tree"].split("-")[0]) for l in open(outp) if l.strip()}
        for name in REPOS:
            for t in ("T0", "T1", "T1f"):
                if (name, t) in done:
                    continue
                r = row(name, t, None, a.models.split(","), not a.no_c)
                open(outp, "a").write(json.dumps(r) + "\n")
                print("done", name, t, flush=True)
        (res / "table_T0_T1.md").write_text(table([str(outp)]))


if __name__ == "__main__":
    main()
