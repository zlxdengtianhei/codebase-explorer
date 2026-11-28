"""Make the inputs of the module-tree scales from nothing.

  prepare.py [--refresh] [--lab DIR] [--commits] [repo ...]

Clones each repo blobless (`--filter=blob:none --no-checkout`) into $CBE_EVAL_CLONES/<name> and verifies
that the pinned commit from common.REPOS is present. A, B1 and B2 read only `git log` paths, so no
working tree is needed. A clone that already verifies is kept; --refresh deletes and re-clones.
--lab DIR creates the lab directory (default $CBE_EVAL_LAB). --commits also draws the 30 scale-C
commits per repo (commits/<name>.json) when missing. That reads `git log --numstat`, which needs blobs:
on a blobless clone git would fetch them one at a time (minutes), so the clone is first turned into a
full one with a single `git fetch --refetch`. Only the model tier needs this.
Prints one line per repo: name, pinned sha, rev-parse of the clone, clone size, seconds.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from common import CLONES, HERE, LAB, REPOS

URLS = {
    "ruby_llm": "https://github.com/crmne/ruby_llm.git",
    "gson": "https://github.com/google/gson.git",
    "tsdown": "https://github.com/sxzz/tsdown.git",
    "fmt": "https://github.com/fmtlib/fmt.git",
    "flask": "https://github.com/pallets/flask.git",
}


def verify(clone: Path, sha: str) -> str | None:
    if not (clone / ".git").exists() and not (clone / "HEAD").exists():
        return None
    r = subprocess.run(["git", "-C", str(clone), "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def size(path: Path) -> str:
    n = sum(f.stat().st_size for f in path.rglob("*") if f.is_file() and not f.is_symlink())
    return f"{n / 1e6:.1f} MB"


def prepare(name: str, refresh: bool) -> tuple[str, str, str, float]:
    sha = REPOS[name]["sha"]
    clone = CLONES / name
    t = time.monotonic()
    if refresh and clone.exists():
        shutil.rmtree(clone)
    got = verify(clone, sha)
    if got is None:
        if clone.exists():
            shutil.rmtree(clone)
        clone.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", URLS[name], str(clone)], check=True)
        got = verify(clone, sha)
    return sha, got or "MISSING", size(clone), time.monotonic() - t


def unfilter(clone: Path) -> None:
    """Turn a blobless clone into a full one in one fetch (git >= 2.36)."""
    if subprocess.run(["git", "-C", str(clone), "config", "--get", "remote.origin.partialclonefilter"],
                      capture_output=True).returncode != 0:
        return
    subprocess.run(["git", "-C", str(clone), "config", "--unset", "remote.origin.partialclonefilter"], check=True)
    subprocess.run(["git", "-C", str(clone), "config", "remote.origin.promisor", "false"], check=True)
    subprocess.run(["git", "-C", str(clone), "fetch", "--quiet", "--refetch", "origin"], check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repos", nargs="*", help="any of " + ", ".join(REPOS) + " (default: all five)")
    ap.add_argument("--refresh", action="store_true", help="delete and re-clone")
    ap.add_argument("--lab", nargs="?", const=str(LAB), help="create the lab directory (default $CBE_EVAL_LAB)")
    ap.add_argument("--commits", action="store_true", help="draw commits/<repo>.json for scale C when missing")
    a = ap.parse_args()
    names = a.repos or list(REPOS)
    unknown = [n for n in names if n not in REPOS]
    if unknown:
        ap.error("unknown repo: " + ", ".join(unknown))
    if a.lab:
        Path(a.lab).mkdir(parents=True, exist_ok=True)
        print(f"lab {Path(a.lab).resolve()}")
    print(f"clones {CLONES}")
    bad = 0
    for name in names:
        sha, got, sz, sec = prepare(name, a.refresh)
        ok = got == sha
        bad += not ok
        print(f"{name:<9} pinned {sha} clone {got} {sz:>9} {sec:6.1f} s {'ok' if ok else 'MISMATCH'}", flush=True)
    if bad:
        return 1
    if a.commits:
        import commits as commits_mod
        for name in names:
            if not (HERE / "commits" / f"{name}.json").exists():
                t = time.monotonic()
                unfilter(CLONES / name)
                commits_mod.write_all([name])
                print(f"{name:<9} commits drawn in {time.monotonic() - t:.1f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
