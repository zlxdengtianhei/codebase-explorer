"""N7b self-check: a `` `name` Lstart-Lend `` link must land on a definition of name.

Orchestrator finding: `evidence/eval/FINDING_N7_RESOLVES_BUT_MISPOINTS.md`.
N7 only asks whether the fragment resolves. This module asks whether the
span names the linked object. File-level overlay labels must not use this
promise shape — they use `` `name` → file `` instead.
"""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from os.path import normpath
from pathlib import Path, PurePosixPath

_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


_PROMISE = re.compile(r"^`([^`]+)` L(\d+)-L(\d+)$")
_HEADING_DEF = re.compile(r"^#{2,3}\s+`([^`]+)`")
_SYMBOL_MARK = re.compile(r"<!--\s*symbol:([^\s>]+)\s*-->")
_SURFACE_MARK = re.compile(r"<!--\s*surface-binding:([^\s>]+)\s*-->")
_SYMBOL_ID_LINE = re.compile(r"Symbol id：`([^`]+)`")


def load_docs(docs_root: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    for path in sorted(docs_root.rglob("*.md")):
        rel = path.relative_to(docs_root).as_posix()
        docs[rel] = path.read_text(encoding="utf-8")
    return docs


def _defined_names(span_text: str) -> set[str]:
    names: set[str] = set()
    for line in span_text.splitlines():
        heading = _HEADING_DEF.match(line.strip())
        if heading:
            qualified = heading.group(1)
            names.add(qualified)
            names.add(qualified.rsplit(".", 1)[-1])
            names.add(qualified.rsplit("::", 1)[-1])
        mark = _SYMBOL_MARK.search(line)
        if mark:
            token = mark.group(1).strip()
            names.add(token)
            names.add(token.rsplit("::", 1)[-1])
            names.add(token.rsplit(".", 1)[-1])
        surface = _SURFACE_MARK.search(line)
        if surface:
            names.add(surface.group(1).strip())
        sid = _SYMBOL_ID_LINE.search(line)
        if sid:
            token = sid.group(1)
            names.add(token)
            names.add(token.rsplit("::", 1)[-1])
    return {item for item in names if item}


def name_is_defined_object(name: str, span_text: str) -> bool:
    return name in _defined_names(span_text)


def _join(source: str, dest: str) -> str:
    if not dest:
        return source
    combined = PurePosixPath(source).parent.joinpath(dest)
    return normpath(combined.as_posix()).replace("\\", "/")


def extract_promise_links(docs: dict[str, str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for rel, text in sorted(docs.items()):
        for label, target in _LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            match = _PROMISE.match(label.strip())
            if match is None:
                continue
            name, start_s, end_s = match.group(1), match.group(2), match.group(3)
            path_part, _, _frag = target.partition("#")
            dest = rel if not path_part else _join(rel, path_part)
            if dest.startswith("./"):
                dest = dest[2:]
            rows.append(
                {
                    "source": rel,
                    "name": name,
                    "label": label,
                    "target": target,
                    "dest": dest,
                    "start": int(start_s),
                    "end": int(end_s),
                    "href_frag": target.partition("#")[2],
                }
            )
    return rows


def public_href_repeats(index_text: str) -> dict[str, object]:
    counts: Counter[str] = Counter()
    in_public = False
    for line in index_text.splitlines():
        if line.startswith("## ") and "公共面" in line:
            in_public = True
            continue
        if in_public and line.startswith("## "):
            break
        if not in_public:
            continue
        for _label, target in _LINK.findall(line):
            counts[target] += 1
    max_repeat = max(counts.values(), default=0)
    top = counts.most_common(5)
    return {
        "max_repeat": max_repeat,
        "ok_max_repeat_le_2": max_repeat <= 2,
        "top": [{"href": href, "count": n} for href, n in top],
        "n_public_links": sum(counts.values()),
    }


def evaluate_docs(docs: dict[str, str]) -> dict[str, object]:
    links = extract_promise_links(docs)
    hits: list[dict[str, object]] = []
    misses: list[dict[str, object]] = []
    for row in links:
        dest = str(row["dest"])
        text = docs.get(dest, "")
        lines = text.splitlines()
        start, end = int(row["start"]), int(row["end"])
        if dest not in docs or start < 1 or end > len(lines) or end < start:
            item = {**row, "hit": False, "why": "target span missing"}
            misses.append(item)
            continue
        span = "\n".join(lines[start - 1 : end])
        hit = name_is_defined_object(str(row["name"]), span)
        item = {
            **row,
            "hit": hit,
            "span_preview": span[:180],
            "why": "" if hit else "name not a defined object in span",
        }
        (hits if hit else misses).append(item)
    n = len(links)
    rate = (len(hits) / n) if n else 1.0
    index = docs.get("INDEX.md", "")
    hrefs = public_href_repeats(index)
    return {
        "links_checked": n,
        "hits": len(hits),
        "misses": len(misses),
        "rate_hit": round(rate, 4),
        "ok_hit_ge_0_90": rate >= 0.90,
        "miss_sample": [
            {"name": item["name"], "source": item["source"], "target": item["target"], "why": item["why"]}
            for item in misses[:20]
        ],
        "public_hrefs": hrefs,
    }


def _first_hit_link(docs: dict[str, str]) -> tuple[str, str, str, int, int] | None:
    for row in extract_promise_links(docs):
        dest = str(row["dest"])
        text = docs.get(dest, "")
        lines = text.splitlines()
        start, end = int(row["start"]), int(row["end"])
        if dest in docs and 1 <= start <= end <= len(lines):
            span = "\n".join(lines[start - 1 : end])
            if name_is_defined_object(str(row["name"]), span):
                return str(row["source"]), dest, str(row["name"]), start, end
    return None


def run_negative_control(docs_root: Path, scratch: Path) -> dict[str, object]:
    if scratch.exists():
        shutil.rmtree(scratch)
    shutil.copytree(docs_root, scratch, ignore=shutil.ignore_patterns("*.json"))
    docs = load_docs(scratch)
    found = _first_hit_link(docs)
    if found is None:
        return {"ran": False, "ok_flagged_red": False, "why": "no hit link to mutate"}
    source, dest, name, start, end = found
    src_path = scratch / source
    text = src_path.read_text(encoding="utf-8")
    old = f"`{name}` L{start}-L{end}"
    new = f"`{name}` L1-L2"
    if old not in text:
        return {"ran": False, "ok_flagged_red": False, "why": f"could not find {old!r} in {source}"}
    src_path.write_text(text.replace(old, new, 1), encoding="utf-8")
    mutated = evaluate_docs(load_docs(scratch))
    flagged = any(item["name"] == name for item in mutated["miss_sample"])
    if not flagged:
        flagged = mutated["misses"] > 0 and mutated["rate_hit"] < 1.0
    return {
        "ran": True,
        "mutated_source": source,
        "mutated_name": name,
        "original_span": f"L{start}-L{end}",
        "injected_span": "L1-L2",
        "rate_hit_after": mutated["rate_hit"],
        "misses_after": mutated["misses"],
        "ok_flagged_red": bool(flagged),
    }


def report(docs_root: Path, *, scratch: Path | None = None) -> dict[str, object]:
    docs = load_docs(docs_root)
    body = evaluate_docs(docs)
    control_dir = scratch if scratch is not None else docs_root.parent / f".pointing_neg_{docs_root.name}"
    control = run_negative_control(docs_root, control_dir)
    if control_dir.exists() and scratch is None:
        shutil.rmtree(control_dir)
    hrefs = body["public_hrefs"]
    return {
        "docs_root": str(docs_root),
        **body,
        "negative_control": control,
        "ok": bool(
            body["ok_hit_ge_0_90"]
            and control.get("ok_flagged_red")
            and hrefs["ok_max_repeat_le_2"]
        ),
    }
