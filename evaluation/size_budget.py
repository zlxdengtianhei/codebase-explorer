"""Measure the size of src/ and gate it against evaluation/size_budget_limits.json.

Standard library only; it reads the source and never imports or installs the package.

    python evaluation/size_budget.py --report
    python evaluation/size_budget.py --check
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = ROOT / "src"
DEFAULT_LIMITS = Path(__file__).resolve().parent / "size_budget_limits.json"
DEFAULT_THRESHOLD = 120
TOP_FILES = 5


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def measure(src: Path, threshold: int = DEFAULT_THRESHOLD) -> dict:
    files: list[tuple[str, int]] = []
    functions: list[tuple[str, str, int, int]] = []
    for path in sorted(src.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        name = _display(path)
        files.append((name, len(text.splitlines())))
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = node.end_lineno - node.lineno + 1
                functions.append((name, node.name, node.lineno, length))
    files.sort(key=lambda item: (-item[1], item[0]))
    functions.sort(key=lambda item: (-item[3], item[0], item[2]))
    long_functions = [
        {"file": f, "name": n, "lineno": ln, "lines": length}
        for f, n, ln, length in functions
        if length > threshold
    ]
    longest = functions[0] if functions else None
    return {
        "src": _display(src),
        "file_count": len(files),
        "total_lines": sum(lines for _, lines in files),
        "largest_files": [{"file": f, "lines": lines} for f, lines in files[:TOP_FILES]],
        "max_file_lines": files[0][1] if files else 0,
        "long_function_threshold": threshold,
        "long_functions": long_functions,
        "long_function_count": len(long_functions),
        "max_function_lines": longest[3] if longest else 0,
        "max_function": (
            {"file": longest[0], "name": longest[1], "lineno": longest[2], "lines": longest[3]}
            if longest
            else None
        ),
    }


def report(m: dict) -> None:
    print(f"size budget report for {m['src']} ({m['file_count']} files)")
    print()
    print(f"total_lines: {m['total_lines']}")
    print()
    print(f"largest_files (top {TOP_FILES}):")
    for item in m["largest_files"]:
        print(f"  {item['lines']:>6}  {item['file']}")
    print()
    print(f"long_functions (> {m['long_function_threshold']} lines): {m['long_function_count']}")
    for item in m["long_functions"]:
        print(f"  {item['lines']:>6}  {item['file']}:{item['lineno']}  {item['name']}")
    print()
    mf = m["max_function"]
    if mf:
        print(f"max_function_lines: {mf['lines']} ({mf['name']} in {mf['file']}:{mf['lineno']})")


def check(m: dict, limits_path: Path) -> int:
    config = json.loads(limits_path.read_text(encoding="utf-8"))
    limits = config["limits"]

    rows = []
    breaches = []
    for name in ("total_lines", "max_file_lines", "max_function_lines", "long_function_count"):
        limit = limits[name]["limit"]
        actual = m[name]
        headroom = limit - actual
        verdict = "ok" if actual <= limit else "BREACH"
        rows.append((name, str(limit), str(actual), str(headroom), verdict))
        if verdict != "ok":
            breaches.append(name)

    header = ("name", "limit", "actual", "headroom", "verdict")
    widths = [max(len(r[i]) for r in rows + [header]) for i in range(len(header))]
    line = lambda r: " | ".join(c.ljust(w) for c, w in zip(r, widths))
    print(f"size budget check for {m['src']} against {_display(limits_path)}")
    print(line(header))
    print("-+-".join("-" * w for w in widths))
    for r in rows:
        print(line(r))

    if not breaches:
        print()
        print("size budget: ok")
        return 0

    print()
    for name in breaches:
        limit = limits[name]["limit"]
        print(f"BREACH {name}: {m[name]} > {limit} ({limits[name]['reason']})")
        if name == "total_lines":
            print("  largest files:")
            for item in m["largest_files"]:
                print(f"    {item['lines']:>6}  {item['file']}")
        elif name == "max_file_lines":
            for item in m["largest_files"]:
                if item["lines"] > limit:
                    print(f"    {item['lines']:>6}  {item['file']}  <- split this file")
        elif name == "max_function_lines":
            for item in m["long_functions"]:
                if item["lines"] > limit:
                    print(f"    {item['lines']:>6}  {item['file']}:{item['lineno']}  {item['name']}  <- split this function")
        elif name == "long_function_count":
            for item in m["long_functions"]:
                print(f"    {item['lines']:>6}  {item['file']}:{item['lineno']}  {item['name']}")
    print()
    print(f"size budget: {len(breaches)} limit(s) breached")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--report", action="store_true", help="print the measurement and exit 0")
    mode.add_argument("--check", action="store_true", help="compare with the limits file; exit 1 on any breach")
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC, help="source directory (default: src/)")
    parser.add_argument("--limits", type=Path, default=DEFAULT_LIMITS, help="limits JSON file")
    parser.add_argument("--json", action="store_true", help="with --report, print the measurement as JSON")
    args = parser.parse_args(argv)

    if not args.src.is_dir():
        parser.error(f"--src {args.src} is not a directory")

    if args.check:
        threshold = json.loads(args.limits.read_text(encoding="utf-8")).get(
            "long_function_threshold", DEFAULT_THRESHOLD
        )
        return check(measure(args.src, threshold), args.limits)

    m = measure(args.src)
    if args.json:
        print(json.dumps(m, indent=2))
    else:
        report(m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
