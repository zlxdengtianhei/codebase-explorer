"""Pick the 30 commits per repo that scale C asks the model about. The rules are code; the funnel is stored.

A commit is kept when it is before the snapshot, is not a merge, changes 1-5 snapshot non-test source files,
has a title that says something, and the snapshot source files hold at least half of its changed lines in
non-test code files (so a commit whose real code moved or was deleted is not scored on one leftover file). Dropped titles are counted by the first rule that matches, in this order:
vague, version/release, dependencies, docs, format/style. Sampling is seeded.
"""
from __future__ import annotations

import json
import random
import re
import subprocess
from collections import Counter

from common import HERE, REPOS, Repo, is_test

SEED = 20261111
N = 30
OUT = HERE / "commits"

# order matters: a commit is counted under the first category that matches
CATEGORIES = [
    ("vague_title", None),   # handled in code: fewer than 3 words after removing issue numbers, or a bare filler word
    ("version_release", re.compile(r"^\s*(v?\d+\.\d+[\w.\-]*\b|bump\b|release\b|version\b|prepare (for )?(the )?(release|v?\d)|\[?(release|version) )", re.I)),
    ("dependencies", re.compile(r"\b(deps?|dependenc\w+|dependabot|renovate|upgrade[sd]?|bump(ed)? [\w@/.\-]+ (from|to)|lockfile|autoupdate|update (the )?[\w@/.\-]+ (gem|package|dependency|requirement)s?)\b", re.I)),
    ("docs_only", re.compile(r"^\s*(docs?|documentation|readme|changelog)\b|\b(readme|changelog|docstrings?|documentation|release notes|license|copyright|badge|typos? in (the )?(docs?|readme|comment))\b", re.I)),
    ("format_style", re.compile(r"\b(format(ting)?|reformat\w*|lint(ing)?|rubocop|prettier|eslint|clang-format|whitespace|code style|style fix|indentation|trailing|typo|spelling|rename (variable|param))\b", re.I)),
]
_NONCODE = re.compile(r"(\.(md|rst|txt|yml|yaml|json|toml|lock|cfg|ini|cmake|gemspec|xml|html|css|svg|png|jpg|gif|csv|in|gradle|properties)$)|(^|/)(Makefile|Gemfile|Rakefile|CMakeLists\.txt|LICENSE[\w.\-]*)$", re.I)
_FILLER = re.compile(r"^(wip|fix(es)?|update[sd]?|cleanup|clean up|misc|minor|tweaks?|tests?|refactor(ing)?|more|stuff|oops|changes?|improvements?)\.?$", re.I)


def category(subject: str) -> str | None:
    s = re.sub(r"\(?#\d+\)?", " ", subject)
    words = re.findall(r"[A-Za-z0-9_]+", s)
    if len(words) < 3 or _FILLER.match(s.strip()):
        return "vague_title"
    for name, rx in CATEGORIES[1:]:
        if rx.search(subject):
            return name
    return None


def history(repo: Repo) -> tuple[list[dict], int]:
    """Non-merge commits strictly before the snapshot, newest first, with changed lines per path (renames followed)."""
    out = subprocess.run(["git", "-C", str(repo.clone), "log", "--no-merges", "--numstat", "-M", "-z",
                          "--format=%x01%H%x09%s", repo.sha + "^"], capture_output=True, text=True, check=True).stdout
    merges = int(subprocess.run(["git", "-C", str(repo.clone), "rev-list", "--count", "--min-parents=2", repo.sha + "^"],
                                capture_output=True, text=True, check=True).stdout)
    commits = []
    for block in out.split("\x01")[1:]:
        toks = block.split("\0")
        sha, _, subject = toks[0].partition("\t")
        files: dict[str, int] = {}
        i = 1
        while i < len(toks):
            t = toks[i].lstrip("\n")
            m = re.match(r"^(\d+|-)\t(\d+|-)\t(.*)$", t, re.S)
            if not m:
                i += 1
                continue
            a, d, p = m.groups()
            if p == "":                       # rename: old and new path follow
                p = toks[i + 2] if i + 2 < len(toks) else ""
                i += 3
            else:
                i += 1
            if a != "-":
                files[p] = files.get(p, 0) + int(a) + int(d)
        commits.append(dict(sha=sha, subject=subject, all_files=files))
    return commits, merges


def select(repo: Repo) -> dict:
    commits, merges = history(repo)
    funnel = Counter(non_merge_commits=len(commits), merge_commits_excluded=merges)
    pool = []
    for c in commits:
        cat = category(c["subject"])
        if cat:
            funnel["title_" + cat] += 1
            continue
        snap = {p: n for p, n in c["all_files"].items() if p in repo.src_set and n > 0}
        other = sum(n for p, n in c["all_files"].items() if p not in repo.src_set and not is_test(p) and not _NONCODE.search(p))
        if not snap:
            funnel["no_snapshot_source_file_changed"] += 1
        elif len(snap) > 5:
            funnel["more_than_5_snapshot_source_files"] += 1
        elif sum(snap.values()) < other:
            funnel["snapshot_files_under_half_of_code_change"] += 1
        else:
            pool.append(dict(sha=c["sha"], subject=c["subject"], files=snap))
    funnel["pool"] = len(pool)
    rng = random.Random(SEED)
    chosen = rng.sample(pool, min(N, len(pool)))
    return dict(repo=repo.name, snapshot=repo.sha, seed=SEED, rules=__doc__.strip(), funnel=dict(funnel), selected=chosen)


def write_all(names=None):
    OUT.mkdir(exist_ok=True)
    for name in names or REPOS:
        res = select(Repo(name))
        json.dump(res, open(OUT / f"{name}.json", "w"), indent=1)
        print(name, res["funnel"])


def load(name: str) -> dict:
    return json.load(open(OUT / f"{name}.json"))


if __name__ == "__main__":
    import sys
    write_all(sys.argv[1:] or None)
