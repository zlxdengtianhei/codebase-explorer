"""Copy a finished CBE run into an `examples/<name>/` directory.

    python publish_example.py --run-dir RUN --source SOURCE --example-dir examples/NAME \\
        (--source-url-base https://github.com/OWNER/REPO/blob/COMMIT | --source-local-dir ../../source)

Replaces `docs/`, `catalog.json.gz` and `summary.json` with the run's own files and removes
the run-time `STATUS.md`.  The only change made to a produced file is a text replacement of
local paths: the run directory becomes `<RUN>` and the input directory becomes `<SOURCE>`
(`--replace PATH=TOKEN` adds more).  License files already in the example directory stay.
The node pages hold source references (`[f1]: ../../../../in/x/file.c`) that point into the
run's input directory.  They are rewritten to `<base>/<path>` (upstream blob URL) or
`<local-dir>/<path>` (a copy of the input kept in the example); `<path>` is the longest tail of the
link target that is a file in the catalog.  The command fails, after copying, if any published file (a `.gz` is read through) still holds
`/home/` or `/Users/`.  Paths come only from arguments; none is written in this script.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import sys
from pathlib import Path

LOCAL_MARKERS = ("/home/", "/Users/")


def _replacements(args: argparse.Namespace) -> list[tuple[str, str]]:
    pairs = [(str(args.run_dir.resolve()), "<RUN>"), (str(args.source.resolve()), "<SOURCE>")]
    for item in args.replace or []:
        path, _, token = item.partition("=")
        pairs.append((path, token))
    return sorted(pairs, key=lambda pair: -len(pair[0]))


def _clean(text: str, pairs: list[tuple[str, str]]) -> str:
    for path, token in pairs:
        text = text.replace(path, token)
    return text


_REF = re.compile(r"^(\[f\d+\]: )(\S+)$", re.MULTILINE)


def _source_links(text: str, files: set[str], base: str) -> str:
    def swap(match: re.Match) -> str:
        parts = [part for part in os.path.normpath(match.group(2)).split(os.sep) if part not in ("..", ".")]
        for start in range(len(parts)):
            tail = "/".join(parts[start:])
            if tail in files:
                return match.group(1) + base.rstrip("/") + "/" + tail
        sys.exit(f"source reference {match.group(2)!r} matches no catalog file")
    return _REF.sub(swap, text)


def _gzip_bytes(text: str) -> bytes:
    # mtime 0 and no file name: the same catalog always gives the same bytes
    import io
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=9) as handle:
        handle.write(text.encode("utf-8"))
    return buffer.getvalue()


def scan(example: Path) -> list[str]:
    hits = []
    for path in sorted(example.rglob("*")):
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()
            text = gzip.decompress(raw).decode("utf-8", "replace") if path.suffix == ".gz" else raw.decode("utf-8", "replace")
        except OSError as exc:
            hits.append(f"{path}: unreadable ({exc})")
            continue
        for marker in LOCAL_MARKERS:
            if marker in text:
                line = next(item for item in text.splitlines() if marker in item)
                hits.append(f"{path}: {line.strip()[:160]}")
                break
    return hits


def publish(args: argparse.Namespace) -> int:
    run, example = args.run_dir, args.example_dir
    pairs = _replacements(args)
    for need in ("docs", "catalog.json", "summary.json"):
        if not (run / need).exists():
            sys.exit(f"run directory lacks {need}")
    if bool(args.source_url_base) == bool(args.source_local_dir):
        sys.exit("give exactly one of --source-url-base and --source-local-dir")
    files = set(json.loads((run / "catalog.json").read_text(encoding="utf-8"))["files"])
    base = args.source_url_base or args.source_local_dir
    example.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(example / "docs", ignore_errors=True)
    for src in sorted((run / "docs").rglob("*")):
        dest = example / "docs" / src.relative_to(run / "docs")
        if src.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            text = _clean(src.read_text(encoding="utf-8"), pairs)
            if src.suffix == ".md":
                text = _source_links(text, files, base)
            dest.write_text(text, encoding="utf-8")
    (example / "catalog.json.gz").write_bytes(
        _gzip_bytes(_clean((run / "catalog.json").read_text(encoding="utf-8"), pairs)))
    (example / "summary.json").write_text(
        _clean((run / "summary.json").read_text(encoding="utf-8"), pairs), encoding="utf-8")
    status = example / "STATUS.md"
    if status.exists():
        status.unlink()
    hits = scan(example)
    for hit in hits:
        print("local path left:", hit, file=sys.stderr)
    return 1 if hits else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--source", type=Path, required=True, help="input directory the run read")
    ap.add_argument("--example-dir", type=Path, required=True)
    ap.add_argument("--replace", action="append", metavar="PATH=TOKEN")
    ap.add_argument("--source-url-base", help="upstream blob URL up to and including the commit")
    ap.add_argument("--source-local-dir", help="path from docs/nodes/ to a copy of the input kept in the example")
    sys.exit(publish(ap.parse_args()))


if __name__ == "__main__":
    main()
