"""Write `examples/<name>/README.md` from the example's own files, a spec entry and the run's readings.

    python render_readme.py --example-dir examples/NAME --spec examples_spec.json \
        --readings ROW.json --cbe-commit SHA --wall-note "5 min, one command"

Needs `cbe` importable (it runs one `cbe find` and one `cbe query` on a scratch copy of the
example directory, unpacks the catalog there, and quotes the real output).  Local paths in the
quoted output are replaced.  The spec entry holds the hand-written facts (what the repository
is, where to start reading, which term to find, extra known gaps); every number comes from
`--readings` (see readings.py) and every other known gap from the run's summary.json and RUN.md.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_LINE = 200
MODEL_NOTE = ("GLM-5.3-flash through a local gateway, API path, route `group/glm-5.3-flash`, with `--config` "
              '`{"timeout": 1800, "output_max_tokens": 49152, "reasoning_effort": "low", "response_format": {"type": "json_object"}, '
              '"batch_target_tokens": 8000, "batch_max_tokens": 10000}` (the built-in defaults of route `zai/glm-5.3-flash`, '
              "which a route name outside the model profile does not get)")


def _cbe(args: list[str]) -> str:
    out = subprocess.run([sys.executable, "-m", "cbe", *args], capture_output=True, text=True, check=False)
    if out.returncode != 0:
        sys.exit(f"cbe {' '.join(args[:2])} failed: {out.stderr[-400:]}")
    return out.stdout


def _short(line: str) -> str:
    return line if len(line) <= MAX_LINE else line[: MAX_LINE - 1].rstrip() + "…"


def _scrub(text: str, scratch: Path) -> str:
    text = text.replace(str(scratch), "<EXAMPLE_DIR>")
    return re.sub(r"(/home|/Users)/[^\s'\"|:]+", "<LOCAL_PATH>", text)


def excerpts(example: Path, term: str, query_id: str | None) -> tuple[str, str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "run"
        shutil.copytree(example, scratch)
        (scratch / "catalog.json").write_bytes(gzip.decompress((scratch / "catalog.json.gz").read_bytes()))
        found_all = _scrub(_cbe(["find", "--run-dir", str(scratch), "--term", term]), scratch).splitlines()
        found = found_all
        if not found:
            sys.exit(f"find --term {term!r} returned nothing")
        rows = [line.split(" | ") for line in found if line.count(" | ") >= 2]
        exact = [r for r in rows if r[0].split(".")[-1] == term and r[2].strip() in ("function", "method", "class")]
        qid = query_id or (exact or rows)[0][1].strip()
        got = _scrub(_cbe(["query", "--run-dir", str(scratch), "--id", qid]), scratch).splitlines()
    chosen = next(line for line in found if line.count(" | ") >= 2 and line.split(" | ")[1].strip() == qid)
    shown = [chosen] + [line for line in found if line != chosen][:1]
    return "\n".join(_short(line) for line in shown), "\n".join(_short(line) for line in got[:7]), qid


def unexplained_line(example: Path, unexplained: int) -> str:
    """Two different counts: symbols the program insisted on, and symbols it let pass without prose."""
    catalog = json.loads(gzip.decompress((example / "catalog.json.gz").read_bytes()))
    silent = [sid for sid, row in catalog["symbol_index"].items() if row.get("how") == "index_only"]
    code = sum((catalog["symbols"].get(sid) or {}).get("kind") in {"function", "method", "class"} for sid in silent)
    return (f"Functions, methods and classes of at least 40 tokens that ended without an explanation "
            f"(`unexplained`): {unexplained}. Indexed without prose and not asked for again (smaller symbols, "
            f"declarations, leftover module-level code): {len(silent):,} catalogue entries, {code:,} of them "
            "functions, methods or classes.")


def gaps(example: Path, row: dict, spec: dict, graph: Path | None = None) -> list[str]:
    summary = json.loads((example / "summary.json").read_text(encoding="utf-8"))
    out = []
    if row["status"] != "complete":
        out.append(f"The run ended `{row['status']}`: {row['pending']} task(s) pending, {row['failed']} failed. "
                   "It is published as it stopped.")
    if not row.get("verify_ok"):
        out.append("`cbe host verify` did not pass: " + ", ".join(row.get("verify_failed_checks") or ["see summary.json"]) + ".")
    out.append(unexplained_line(example, row["unexplained"]))
    review = summary.get("semantic_review") or {}
    reviewed = review.get("reviewed") or []
    if reviewed:
        parts = [f"module {item['module']}: {item['decision']}, {len(item.get('issues') or [])} issue(s)"
                 + (f", repair {item['repair']}" if item.get("repair") else "") for item in reviewed]
        repaired = any(item.get("repair") for item in reviewed)
        out.append("Sample review by a separate reader of the source read " + str(len(reviewed)) + " module batch(es) ("
                   + "; ".join(parts) + ")." + (" The repaired text was not read again." if repaired else ""))
    if row.get("program_made_titles"):
        out.append(f"{row['program_made_titles']} tree node title(s) were made by the program because the model did not name them.")
    index = (summary.get("tree") or {}).get("index") or {}
    if index.get("over_budget"):
        out.append(f"`docs/INDEX.md` is over its {index.get('budget')}-token budget ({index.get('tokens')} tokens).")
    for item in summary.get("context_fallback") or []:
        out.append(f"`{item['path']}` was read as one whole-file chunk ({item['reason']}).")
    if row["rejected"] or row["rate_limited_rows"]:
        out.append(f"{row['rejected']} answer(s) were refused by the program's checks and asked again; "
                   f"{row['rate_limited_rows']} call(s) waited on a rate limit.")
    run_md = example / "docs" / "RUN.md"
    if run_md.exists():
        for line in run_md.read_text(encoding="utf-8").splitlines():
            if line.startswith("Incomplete capabilities:"):
                out.append("Graph: " + line.replace("Incomplete capabilities:", "analyzer capabilities that did not complete:", 1))
    if graph is not None:
        by_code: dict[str, list[str]] = {}
        for item in json.loads(graph.read_text(encoding="utf-8")).get("diagnostics") or []:
            by_code.setdefault(item.get("code", "diagnostic"), []).append(item.get("message", ""))
        for code, messages in by_code.items():
            extra = f" ({len(messages)} entries, first shown)" if len(messages) > 1 else ""
            out.append(f"Graph diagnostic `{code}`{extra}: " + _short(messages[0]))
    out.extend(spec.get("gaps", []))
    return out


def render(example: Path, name: str, spec: dict, row: dict, cbe_commit: str, wall_note: str,
           graph: Path | None = None) -> str:
    find_text, query_text, qid = excerpts(example, spec["term"], spec.get("query_id"))
    nodes = [(page, (example / "docs" / "nodes" / page).read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip())
             for page in spec["read"]]
    links = ", ".join(f"[{title}](docs/nodes/{page})" for page, title in nodes)
    n = lambda value: f"{value:,}"  # noqa: E731
    lines = [
        f"# {spec['title']}: CBE example",
        f"{spec['description']} Language: **{spec['language']}**.", "",
        f"{spec['origin']}; input: {spec['scope']} ({row['files']} files read, {n(row['source_tokens'])} `o200k_base` tokens; "
        "definition in [inputs.json](../../evaluation/inputs/inputs.json)). "
        f"Generated by CBE `{cbe_commit}` with {spec.get('model_note', MODEL_NOTE)}.", "",
        f"**Read.** Start at [docs/INDEX.md](docs/INDEX.md), then {links}. Each unit has an id for `cbe query`.", "",
        "**Search and inspect.**", "```sh", "gzip -dk catalog.json.gz",
        f"cbe find --run-dir . --term '{spec['term']}'",
        f"cbe query --run-dir . --id '{qid}'", "```",
        "Real output from a scratch copy of this directory (first lines; paths replaced):",
        "```text", find_text, "", query_text, "```", "",
        f"**This run.** `{row['status']}`, `cbe host verify` {'pass' if row.get('verify_ok') else 'FAIL'}. "
        f"{row['modules']} model tasks, {row['nodes']} tree nodes, {row['units']} units. "
        f"{row['requests']} requests, {row['rejected']} answers refused and asked again. "
        f"Prompt {n(row['prompt_tokens'])} tokens (cached included, {row['prompt_per_source']}x source), "
        f"output {n(row['output_tokens'])} tokens ({row['output_per_source']}x source). "
        f"`docs/INDEX.md`: {n(row['index_tokens'])} tokens. Wall time {wall_note}.", "",
        "**Known gaps.**",
        *[f"- {item}" for item in gaps(example, row, spec, graph)],
        "Counts: [summary.json](summary.json) and the run's "
        + ("`cbe host cost` output" if spec.get("host") else "`calls.csv`") + " (not published). Verify checks structure, coverage and links, not truth of the prose. "
        "License of the described code: [LICENSE](LICENSE).",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--example-dir", type=Path, required=True)
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--readings", type=Path, required=True, help="JSON file written by readings.py")
    ap.add_argument("--cbe-commit", required=True)
    ap.add_argument("--wall-note", required=True)
    ap.add_argument("--graph", type=Path, help="graph JSON the run used; its diagnostics are quoted as known gaps")
    ap.add_argument("--name")
    args = ap.parse_args()
    name = args.name or args.example_dir.name
    spec = json.loads(args.spec.read_text(encoding="utf-8"))[name]
    row = json.loads(args.readings.read_text(encoding="utf-8"))
    text = render(args.example_dir, name, spec, row, args.cbe_commit, args.wall_note, args.graph)
    (args.example_dir / "README.md").write_text(text, encoding="utf-8")
    print(f"{args.example_dir / 'README.md'}: {len(text.splitlines())} lines")


if __name__ == "__main__":
    main()
