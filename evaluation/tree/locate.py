"""Scale C: from a module map, can a model find where a past change landed?

Page (made by code from the tree), one fixed prompt, answer = three module ids, score = how much of the
change (weighted by changed lines, files softly assigned to modules) sits in the chosen modules.
Raw answers go to LAB/raw (not in git) and are reused on rerun, keyed by model + full prompt.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from pathlib import Path

from common import LAB, Repo, Tree, file_membership, view_groups

GATEWAY = os.environ.get("CBE_EVAL_GATEWAY", "http://127.0.0.1:3425/v1/chat/completions")   # any OpenAI-compatible endpoint
MODELS = {  # short name -> gateway id
    "glm-flash": "group/glm-5.3-flash",
    "deepseek-flash": "group/deepseek-v4.1-flash",
    "mistral-medium": "mistral/mistral-medium-latest",
}

# glm-5.3-flash at default effort spends 1000-5000 reasoning tokens per question (and stalls the run); it is asked with
# reasoning_effort=low. Other models use their defaults. Answers are cached under a different folder name per setting.
MODEL_EXTRA = {"group/glm-5.3-flash": {"reasoning_effort": "low"}}


def slug(model_id: str) -> str:
    return model_id.replace("/", "_") + ("_low" if model_id in MODEL_EXTRA else "")


PROMPT = """Below is a map of a code repository: its modules, each with an id, a title, what it is responsible for, and its three largest source files.

{page}

A developer is about to work on this change (the description of a commit that was made in this repository):

"{subject}"

Which three modules should they read first to find the code that has to change? Choose only from the ids in the map.
Reply with only JSON and no other text: {{"modules": ["<id>", "<id>", "<id>"]}}"""


def make_page(groups: list[dict]) -> str:
    lines = [f"{len(groups)} modules. Each line: id | title | responsibility | largest files"]
    for g in groups:
        lines.append(f"- {g['id']} | {g['title']} | {g['capability'] or '-'} | {', '.join(g['files'])}")
    return "\n".join(lines)


_enc = None


def count_tokens(text: str) -> int:
    global _enc
    if _enc is None:
        import tiktoken
        _enc = tiktoken.get_encoding("cl100k_base")
    return len(_enc.encode(text))


def _log(model_id: str, usage: dict, failed_before: int) -> None:
    """One line per real gateway call that returned an answer (cache hits are not logged)."""
    LAB.mkdir(parents=True, exist_ok=True)
    with open(LAB / "calls.jsonl", "a") as fh:
        fh.write(json.dumps(dict(model=model_id, prompt=usage.get("prompt_tokens", 0), completion=usage.get("completion_tokens", 0),
                                 reasoning=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0),
                                 failed_attempts_before=failed_before)) + "\n")


def _call(model_id: str, prompt: str, cache: "Path") -> dict:
    if cache.exists():
        return json.load(open(cache))
    last = None
    for attempt in range(8):
        try:
            r = requests.post(GATEWAY, json=dict(model=model_id, temperature=0, max_tokens=6000,
                                                 messages=[dict(role="user", content=prompt)], **MODEL_EXTRA.get(model_id, {})), timeout=150)
            if r.status_code == 429:
                time.sleep(8 + 4 * attempt)
                last = "429 rate limited"
                continue
            r.raise_for_status()
            d = r.json()
            content = (d["choices"][0]["message"].get("content") or "").strip()
            if not content:
                raise RuntimeError("empty content, finish_reason=" + str(d["choices"][0].get("finish_reason")))
            rec = dict(model=model_id, prompt=prompt, content=content, usage=d.get("usage", {}),
                       reasoning=d["choices"][0]["message"].get("reasoning_content"), attempts=attempt + 1)
            _log(model_id, rec["usage"], attempt)
            cache.parent.mkdir(parents=True, exist_ok=True)
            json.dump(rec, open(cache, "w"))
            return rec
        except Exception as e:  # network, HTTP, empty answer: try again; after the last try the failure is returned, not cached
            last = repr(e)
            time.sleep(2 + attempt)
    return dict(model=model_id, prompt=prompt, content="", usage={}, error=last, attempts=8)


def parse_ids(content: str, valid: set[str]) -> tuple[list[str], int]:
    """Up to three distinct valid ids from the first JSON object in the answer; second value = invalid ids dropped."""
    m = re.search(r"\{.*\}", content, re.S)
    ids = []
    if m:
        try:
            raw = json.loads(m.group(0)).get("modules", [])
            ids = [x for x in raw if isinstance(x, str)] if isinstance(raw, list) else []
        except Exception:
            ids = re.findall(r'"([^"]+)"', m.group(0))
            ids = [x for x in ids if x in valid]
    good = []
    for x in ids:
        if x in valid and x not in good:
            good.append(x)
    return good[:3], len([x for x in ids if x not in valid])


def recall_share(commit: dict, member: dict, lines: dict, total: int, chosen: list[str]) -> tuple[float, float]:
    w = commit["files"]
    t = sum(w.values())
    hit = sum(n * sum(member.get(p, {}).get(g, 0.0) for g in chosen) for p, n in w.items())
    return hit / t, sum(lines.get(g, 0) for g in chosen) / total


def run_view(repo: Repo, tree: Tree, label: dict, commits: list[dict], models: list[str], view_name: str,
             workers: int = 18) -> dict:
    groups = view_groups(repo, tree, label)
    page = make_page(groups)
    pid = hashlib.sha1(page.encode()).hexdigest()[:10]
    member = file_membership(repo, label)
    lines = {g["id"]: g["lines"] for g in groups}
    total = sum(lines.values())
    valid = set(lines)
    out = dict(view=view_name, modules=len(groups), page_tokens=count_tokens(page), page_id=pid, questions=len(commits))
    # no-model references
    rng = random.Random(7)
    ids = sorted(valid)
    big3 = sorted(ids, key=lambda g: (-lines[g], g))[:3]
    rr, rs, orc, bg = [], [], [], []
    for c in commits:
        draws = [rng.sample(ids, min(3, len(ids))) for _ in range(200)]
        v = [recall_share(c, member, lines, total, d) for d in draws]
        rr.append(sum(x[0] for x in v) / len(v))
        rs.append(sum(x[1] for x in v) / len(v))
        per = sorted(ids, key=lambda g: -sum(n * member.get(p, {}).get(g, 0.0) for p, n in c["files"].items()))[:3]
        orc.append(recall_share(c, member, lines, total, per)[0])
        bg.append(recall_share(c, member, lines, total, big3)[0])
    n = len(commits)
    out["reference"] = dict(random3_per_q=rr, random3_recall=sum(rr) / n, random3_share=sum(rs) / n, largest3_recall=sum(bg) / n,
                            largest3_share=sum(lines[g] for g in big3) / total, oracle3_recall=sum(orc) / n)
    out["models"] = {}
    all_jobs = {}
    for short in models:
        mid = MODELS[short]
        all_jobs[short] = [(c, LAB / "raw" / repo.name / slug(mid) / pid / f"{c['sha'][:12]}.json",
                            PROMPT.format(page=page, subject=c["subject"])) for c in commits]
    flat = [(short, j) for short, js in all_jobs.items() for j in js]
    with ThreadPoolExecutor(workers) as ex:      # all models at once: the slow reasoning models set the pace
        done = list(ex.map(lambda sj: _call(MODELS[sj[0]], sj[1][2], sj[1][1]), flat))
    by_model = {short: [] for short in models}
    for (short, _), rec in zip(flat, done):
        by_model[short].append(rec)
    for short in models:
        jobs, recs = all_jobs[short], by_model[short]
        rec_l, sh_l, tok_l, fail, invalid, nsel = [], [], [], 0, 0, []
        for (c, _, _), rec in zip(jobs, recs):
            chosen, bad = parse_ids(rec["content"], valid)
            invalid += bad
            if not chosen:
                fail += 1
            r, s = recall_share(c, member, lines, total, chosen)
            rec_l.append(r)
            sh_l.append(s)
            nsel.append(len(chosen))
            u = rec.get("usage") or {}
            tok_l.append(u.get("prompt_tokens", 0) + u.get("completion_tokens", 0))
        mr, ms = sum(rec_l) / n, sum(sh_l) / n
        brng = random.Random(11)
        boots = sorted(sum(rec_l[brng.randrange(n)] for _ in range(n)) / n for _ in range(1000))
        ci = (boots[25], boots[974])
        out["models"][short] = dict(recall=mr, recall_per_q=rec_l, share_per_q=sh_l, recall_ci95=ci, share=ms, lift=mr / ms if ms else None, tokens_per_q=sum(tok_l) / n,
                                    no_valid_answer=fail, invalid_ids_dropped=invalid, mean_modules_chosen=sum(nsel) / n)
    return out
