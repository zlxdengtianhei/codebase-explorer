"""Measure the files CBE would enroll under chosen directories.

Mirrors CBE's discovery (source_context.py a87674d): os.walk, skip DEFAULT_EXCLUDE_DIR_NAMES,
keep files whose suffix has a registered grammar, skip files > 8 MiB.  Counts files, lines
(newline count, +1 when the last line has no newline), non-blank lines, bytes and o200k_base
tokens per language.  Read-only; does not run CBE.

usage: measure.py ROOT [--dirs a,b] [--exclude prefix1,prefix2] [--test-re REGEX]
                  [--header cpp|c] [--label NAME] [--json OUT] [--top N]
--dirs     comma list of ROOT-relative dirs or files to include (default ".")
--exclude  comma list of ROOT-relative path prefixes to drop (after --dirs)
--test-re  regex on ROOT-relative path; matching files are reported in a separate "test" group
--header   language for .h (CBE default is c)
"""
import argparse, json, os, re, sys
from pathlib import PurePosixPath

import tiktoken

EXCL = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__",
        ".mypy_cache", ".pytest_cache", ".tox", ".codebase-analysis"}
SUFFIX = {}
for lang, sfx in {
    "C": (".c", ".h"),
    "C++": (".cc", ".cpp", ".cxx", ".c++", ".hh", ".hpp", ".hxx", ".h++", ".inl"),
    "Python": (".py",),
    "JavaScript": (".js", ".jsx", ".mjs", ".cjs"),
    "TypeScript": (".ts", ".mts", ".cts"),
    "TSX": (".tsx",),
    "Java": (".java",),
    "Go": (".go",),
    "Ruby": (".rb", ".rake", ".gemspec", ".ru"),
    "Rust": (".rs",),
    "PHP": (".php", ".phtml"),
    "C#": (".cs",),
    "Kotlin": (".kt", ".kts"),
    "Swift": (".swift",),
    "SQL(fallback)": (".sql",),
}.items():
    for s in sfx:
        SUFFIX[s] = lang

ENC = tiktoken.get_encoding("o200k_base")
MAX_FILE_BYTES = 8 * 1024 * 1024


def select_files(root, dirs, excludes, header="c"):
    """Return ({rel: language}, {other suffix: count}) the way CBE discovery would enroll them."""
    seen = {}
    other_sfx = {}
    for d in dirs.split(","):
        base = os.path.join(root, d)
        if os.path.isfile(base):
            walk = [(os.path.dirname(base), [], [os.path.basename(base)])]
        else:
            walk = os.walk(base)
        for cur, dirnames, filenames in walk:
            dirnames[:] = sorted(n for n in dirnames if n not in EXCL)
            for fn in sorted(filenames):
                full = os.path.join(cur, fn)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                if any(rel == e or rel.startswith(e.rstrip("/") + "/") for e in excludes):
                    continue
                if os.path.islink(full):
                    continue
                sfx = PurePosixPath(rel).suffix
                lang = SUFFIX.get(sfx)
                if lang is None:
                    other_sfx[sfx or "(none)"] = other_sfx.get(sfx or "(none)", 0) + 1
                    continue
                if sfx == ".h" and header == "cpp":
                    lang = "C++"
                if os.path.getsize(full) > MAX_FILE_BYTES:
                    continue
                seen[rel] = lang
    return seen, other_sfx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--dirs", default=".")
    ap.add_argument("--exclude", default="")
    ap.add_argument("--test-re", default="")
    ap.add_argument("--header", default="c")
    ap.add_argument("--label", default="")
    ap.add_argument("--json", default="")
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    excludes = [e for e in a.exclude.split(",") if e]
    test_re = re.compile(a.test_re) if a.test_re else None
    seen, other_sfx = select_files(root, a.dirs, excludes, a.header)
    groups = {"src": {}, "test": {}}
    files = []
    for rel, lang in sorted(seen.items()):
        raw = open(os.path.join(root, rel), "rb").read()
        text = raw.decode("utf-8", errors="replace")
        nl = raw.count(b"\n") + (1 if raw and not raw.endswith(b"\n") else 0)
        nb = sum(1 for ln in text.splitlines() if ln.strip())
        tok = len(ENC.encode(text, disallowed_special=()))
        g = "test" if (test_re and test_re.search(rel)) else "src"
        s = groups[g].setdefault(lang, {"files": 0, "lines": 0, "nonblank": 0, "bytes": 0, "tokens": 0})
        s["files"] += 1; s["lines"] += nl; s["nonblank"] += nb; s["bytes"] += len(raw); s["tokens"] += tok
        files.append((tok, rel, nl, lang, g))
    out = {"label": a.label, "root": root, "dirs": a.dirs, "exclude": excludes, "test_re": a.test_re,
           "header": a.header, "groups": groups, "other_suffix_counts": other_sfx}

    def tot(g):
        t = {"files": 0, "lines": 0, "nonblank": 0, "bytes": 0, "tokens": 0}
        for s in groups[g].values():
            for k in t:
                t[k] += s[k]
        return t
    out["total"] = {g: tot(g) for g in groups}
    out["top_files"] = [{"rel": r, "tokens": t, "lines": n, "group": g} for t, r, n, l, g in sorted(files, reverse=True)[: a.top]]
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1, ensure_ascii=False)
    print(f"== {a.label or root}  dirs={a.dirs} exclude={excludes} test_re={a.test_re!r} header={a.header}")
    for g in ("src", "test"):
        if not groups[g]:
            continue
        print(f"  [{g}]")
        for lang, s in sorted(groups[g].items()):
            print(f"    {lang:14s} files={s['files']:5d} lines={s['lines']:7d} nonblank={s['nonblank']:7d} bytes={s['bytes']:9d} tokens={s['tokens']:8d}")
        t = out["total"][g]
        print(f"    {'TOTAL':14s} files={t['files']:5d} lines={t['lines']:7d} nonblank={t['nonblank']:7d} bytes={t['bytes']:9d} tokens={t['tokens']:8d}")
    print("  top files:", "; ".join(f"{x['rel']}({x['tokens']}t,{x['lines']}l)" for x in out["top_files"]))
    if other_sfx:
        print("  non-CBE suffix counts (top):", dict(sorted(other_sfx.items(), key=lambda kv: -kv[1])[:8]))


if __name__ == "__main__":
    main()
