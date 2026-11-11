"""Checks on the scales themselves: situations where a reading could mislead. Writes results/controls.md and .json.

  controls.py [repo ...]   (model-free parts first, then the model calls; answers cached under LAB/raw*)
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import commits as commits_mod
import locate
import measures
from common import HERE, LAB, REPOS, Repo, file_membership, view_groups
from run import cuts

MODELS2 = ["glm-flash", "deepseek-flash"]


def fewer_modules(repo: Repo) -> list[dict]:
    """T1 cut at every depth: random-3 recall and lift as the module count falls; plus one module / one per unit."""
    t1 = repo.tree1()
    cm = commits_mod.load(repo.name)["selected"]
    rows = []
    for k in range(0, max(t1.depth(n) for n in t1.nodes) + 1):
        lab = t1.cut(f"depth:{k}", repo.units)
        rows.append(_ref(repo, t1, lab, cm, f"dir depth {k}"))
    one = {u: "ALL" for u in repo.units}
    rows.append(_ref(repo, t1, one, cm, "one module for everything", fake="ALL"))
    return rows


def _ref(repo, tree, lab, cm, name, fake=None):
    if fake:   # a single module holding everything: recall and share are 1 by construction
        return dict(name=name, modules=1, random3_recall=1.0, random3_share=1.0, oracle3_recall=1.0, lift=1.0)
    v = locate.run_view(repo, tree, lab, cm, [], name)
    r = v["reference"]
    return dict(name=name, modules=v["modules"], random3_recall=r["random3_recall"], random3_share=r["random3_share"],
                oracle3_recall=r["oracle3_recall"], lift=r["random3_recall"] / r["random3_share"])


def b_bias(repo: Repo) -> dict:
    t0, t1 = repo.tree0(), repo.tree1()
    out = {}
    pairs = repo.cochange()
    lab = t0.cut("up1", repo.units)
    mem = file_membership(repo, lab)
    hard = {f: {max(sorted(c), key=lambda g: c[g]): 1.0} for f, c in mem.items()}
    out["T0 up1: soft Q"] = measures.soft_modularity(pairs, mem)
    out["T0 up1: hard-majority Q (the probe's way)"] = measures.soft_modularity(pairs, hard)
    out["one file per module"] = measures.soft_modularity(pairs, {f: {f: 1.0} for f in repo.src_files})
    out["one module for everything"] = measures.soft_modularity(pairs, {f: {"A": 1.0} for f in repo.src_files})
    # B1 extremes
    out["B1 one module"] = measures.b1(repo, {u: "A" for u in repo.units}, "call")["q"]
    out["B1 one unit per module"] = measures.b1(repo, {u: u for u in repo.units}, "call")["q"]
    out["B1 edge weight (call edges)"] = measures.b1(repo, {u: "A" for u in repo.units}, "call")["edge_weight"]
    # does Q follow locality? whole directories scrambled into random groups vs real directories
    import random
    lab1 = t1.cut("leaf", repo.units)
    dirs = sorted(set(lab1.values()))
    rng = random.Random(3)
    qs = []
    for _ in range(30):
        shuffled = dict(zip(dirs, rng.sample(dirs, len(dirs))))
        # merge dirs pairwise at random: keeps files of a directory together, loses which directories belong together
        grp = {d: i % max(2, len(dirs) // 2) for i, d in enumerate(shuffled.values())}
        qs.append(measures.soft_modularity(pairs, file_membership(repo, {u: grp[shuffled[d]] for u, d in lab1.items()})))
    out["leaf dirs: real Q"] = measures.soft_modularity(pairs, file_membership(repo, lab1))
    out["leaf dirs randomly paired (files kept together), mean Q"] = sum(qs) / len(qs)
    return out


def leak(repo: Repo) -> dict:
    """How many T0 up1/leaf capability sentences name a file stem of their own member files."""
    t0 = repo.tree0()
    res = {}
    for lv in ("up1", "leaf"):
        lab = t0.cut(lv, repo.units)
        gs = view_groups(repo, t0, lab)
        hits = 0
        for g in gs:
            fl = {Path(p).stem.lower() for u, d in repo.unit_lines.items() if lab.get(u) == g["id"] for p in d}
            txt = (g["capability"] + " " + g["title"]).lower()
            if any(len(s) >= 4 and s in txt for s in fl):
                hits += 1
        res[lv] = f"{hits}/{len(gs)}"
    return res


def no_cap(repo: Repo) -> dict:
    t0 = repo.tree0()
    cm = commits_mod.load(repo.name)["selected"]
    lab = t0.cut("up1", repo.units)
    stripped = {k: dict(v, capability="", summary="") for k, v in t0.nodes.items()}
    t0.nodes = stripped
    return locate.run_view(repo, t0, lab, cm, MODELS2, "up1-no-capability")


NOMAP = """Repository: {name} (an open-source project on GitHub).

A commit was made in this repository with this description:

"{subject}"

Without seeing the code, which three source files (paths relative to the repository root) did this commit most likely change?
Reply with only JSON and no other text: {{"files": ["<path>", "<path>", "<path>"]}}"""


def no_map(repo: Repo) -> dict:
    """Memory test: the model gets only the repository name and the commit text, and names files."""
    cm = commits_mod.load(repo.name)["selected"]
    res = {}
    for short in MODELS2:
        mid = locate.MODELS[short]
        jobs = [(c, LAB / "raw_nomap" / repo.name / locate.slug(mid) / f"{c['sha'][:12]}.json",
                 NOMAP.format(name=repo.name, subject=c["subject"])) for c in cm]
        with ThreadPoolExecutor(6) as ex:
            recs = list(ex.map(lambda j: locate._call(mid, j[2], j[1]), jobs))
        exact, base, tok = [], [], 0
        for (c, _, _), r in zip(jobs, recs):
            m = re.search(r"\{.*\}", r["content"], re.S)
            try:
                named = [x for x in json.loads(m.group(0)).get("files", []) if isinstance(x, str)][:3]
            except Exception:
                named = []
            w = c["files"]
            t = sum(w.values())
            exact.append(sum(n for p, n in w.items() if p in named) / t)
            base.append(sum(n for p, n in w.items() if Path(p).name in {Path(x).name for x in named}) / t)
            u = r.get("usage") or {}
            tok += u.get("prompt_tokens", 0) + u.get("completion_tokens", 0)
        k = len(cm)
        res[short] = dict(exact_path_recall=sum(exact) / k, same_file_name_recall=sum(base) / k, tokens_per_q=tok / k)
    return res


def repeat(repo: Repo) -> dict:
    """Ask the same 30 questions of the T0 up1 page a second time; how often does the chosen set change?"""
    t0 = repo.tree0()
    cm = commits_mod.load(repo.name)["selected"]
    lab = t0.cut("up1", repo.units)
    groups = view_groups(repo, t0, lab)
    page = locate.make_page(groups)
    import hashlib
    pid = hashlib.sha1(page.encode()).hexdigest()[:10]
    valid = {g["id"] for g in groups}
    res = {}
    for short in MODELS2:
        mid = locate.MODELS[short]
        same = 0
        r1, r2 = [], []
        mem = file_membership(repo, lab)
        lines = {g["id"]: g["lines"] for g in groups}
        jobs = [(c, LAB / "raw_repeat" / repo.name / locate.slug(mid) / pid / f"{c['sha'][:12]}.json", locate.PROMPT.format(page=page, subject=c["subject"])) for c in cm]
        with ThreadPoolExecutor(6) as ex:
            second = list(ex.map(lambda j: locate._call(mid, j[2], j[1]), jobs))
        for c, rec2 in zip(cm, second):
            first = json.load(open(LAB / "raw" / repo.name / locate.slug(mid) / pid / f"{c['sha'][:12]}.json"))
            a = set(locate.parse_ids(first["content"], valid)[0])
            b = set(locate.parse_ids(rec2["content"], valid)[0])
            same += a == b
            tot = sum(lines.values())
            r1.append(locate.recall_share(c, mem, lines, tot, list(a))[0])
            r2.append(locate.recall_share(c, mem, lines, tot, list(b))[0])
        res[short] = f"{same}/{len(cm)} identical chosen sets; mean recall run 1 {sum(r1)/len(cm):.2f}, run 2 {sum(r2)/len(cm):.2f}"
    return res


def f(x, d=2):
    return "n/a" if x is None or x != x else f"{x:.{d}f}"


def table() -> str:
    res = HERE / "results"
    mf = json.load(open(res / "controls_model_free.json"))
    md = json.load(open(res / "controls.json")) if (res / "controls.json").exists() else {}
    rep = json.load(open(res / "controls_repeat.json")) if (res / "controls_repeat.json").exists() else {}
    rows = {(r["repo"], r["tree"][:2]): r for r in (json.loads(l) for l in open(res / "rows_T0_T1.jsonl"))}
    o = ["# Checks on the scales", "",
         "## 1. Fewer modules, higher recall (C)", "",
         "Directory cuts of each repo at every depth, plus one module for everything. Random-3 = expected recall when three modules are picked at random; "
         "lift = recall / share. Lift stays near 1 for a random pick at any size; recall alone does not.", "",
         "| repo | cut | modules | random-3 recall | random-3 share | lift | best-3 recall |", "|---|---|---|---|---|---|---|"]
    for r, v in mf.items():
        for x in v["fewer_modules"]:
            o.append(f"| {r} | {x['name']} | {x['modules']} | {f(x['random3_recall'])} | {f(x['random3_share'])} | {f(x['lift'])} | {f(x['oracle3_recall'])} |")
    o += ["", "## 2. B reads mostly 'files of one directory stay together' (B2) and has fixed floor and ceiling (B1, B2)", "",
          "Q values. 'randomly paired' keeps every directory whole but merges directories at random into groups of about two.", "",
          "| repo | " + " | ".join(next(iter(mf.values()))["b_bias"].keys()) + " |",
          "|---|" + "---|" * len(next(iter(mf.values()))["b_bias"])]
    for r, v in mf.items():
        o.append(f"| {r} | " + " | ".join(f(x, 3) for x in v["b_bias"].values()) + " |")
    o += ["", "## 3. Capability sentences that name a file of their own module", "",
          "Count of T0 modules whose title or capability contains the stem (4 or more letters) of one of their own member files.", "",
          "| repo | one level above leaf | leaf |", "|---|---|---|"]
    for r, v in mf.items():
        o.append(f"| {r} | {v['leak']['up1']} | {v['leak']['leaf']} |")
    if md:
        o += ["", "## 4. T0 one-level-above-leaf page with and without the capability sentence (C)", "",
              "| repo | model | recall with | share with | recall without | share without | lift with | lift without | page tokens with | without |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r, v in md.items():
            if "no_capability_up1" not in v:
                continue
            w = rows[(r, "T0")]["C"]["up1"]
            n = v["no_capability_up1"]
            for m in MODELS2:
                a, b = w["models"][m], n["models"][m]
                o.append(f"| {r} | {m} | {f(a['recall'])} | {f(a['share'])} | {f(b['recall'])} | {f(b['share'])} | {f(a['lift'])} | {f(b['lift'])} | {w['page_tokens']} | {n['page_tokens']} |")
        o += ["", "## 5. Memory test: file names with no map (repo name and commit text only)", "",
              "Share of the change (by changed lines) that sits in the three files the model named. Compare with the best-3 module recall of the same repo.", "",
              "| repo | model | exact-path hit | same-file-name hit | tokens per question |", "|---|---|---|---|---|"]
        for r, v in md.items():
            for m, x in (v.get("no_map") or {}).items():
                o.append(f"| {r} | {m} | {f(x['exact_path_recall'])} | {f(x['same_file_name_recall'])} | {x['tokens_per_q']:.0f} |")
    if rep:
        o += ["", "## 6. Same question asked twice (temperature 0 sent)", "", "| repo | model | result |", "|---|---|---|"]
        for r, v in rep.items():
            for m, x in v.items():
                o.append(f"| {r} | {m} | {x} |")
    return "\n".join(o) + "\n"


def main():
    if "--table" in sys.argv:
        (HERE / "results" / "controls.md").write_text(table())
        return
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    names = args or list(REPOS)
    (HERE / "results").mkdir(exist_ok=True)
    out = {}
    for n in names:
        repo = Repo(n)
        out[n] = dict(fewer_modules=fewer_modules(repo), b_bias=b_bias(repo), leak=leak(repo))
        json.dump(out, open(HERE / "results" / "controls_model_free.json", "w"), indent=1)
        print("model-free done", n, flush=True)
    if "--model-free" in sys.argv:
        return
    if "--repeat" in sys.argv:       # needs the T0 up1 answers of `run.py all` to exist
        rep = {n: repeat(Repo(n)) for n in names}
        json.dump(rep, open(HERE / "results" / "controls_repeat.json", "w"), indent=1)
        return
    for n in names:
        repo = Repo(n)
        out[n]["no_map"] = no_map(repo)
        out[n]["no_capability_up1"] = no_cap(repo)
        json.dump(out, open(HERE / "results" / "controls.json", "w"), indent=1)
        print("model controls done", n, flush=True)


if __name__ == "__main__":
    main()
