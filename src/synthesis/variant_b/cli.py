"""CLI: python -m src.synthesis.variant_b render|scan|gradient"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.synthesis.variant_b.pipeline import render_variant_b
from src.synthesis.variant_b.scan import scan_docs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="variant_b")
    sub = parser.add_subparsers(dest="cmd", required=True)

    render = sub.add_parser("render")
    render.add_argument("--repo", required=True)
    render.add_argument("--ledger", required=True)
    render.add_argument("--out", required=True)
    render.add_argument("--ir", default=None)
    render.add_argument("--partition", default=None)
    render.add_argument("--names", default=None)

    scan = sub.add_parser("scan")
    scan.add_argument("--docs", required=True)

    pointing = sub.add_parser("pointing")
    pointing.add_argument("--docs", required=True)
    pointing.add_argument("--json-out", default="")

    gradient = sub.add_parser("gradient")
    gradient.add_argument("--repo", required=True)
    gradient.add_argument("--ledger", required=True)
    gradient.add_argument("--out", required=True)
    gradient.add_argument("--budgets", default="0,1,3,9")

    measure = sub.add_parser("measure")
    measure.add_argument("--docs", required=True)
    measure.add_argument("--repo", default="")
    measure.add_argument("--ledger", default="")
    measure.add_argument("--json-out", default="")

    consume = sub.add_parser("consume-score")
    consume.add_argument("--tasks", required=True)
    consume.add_argument("--raw-dir", required=True)
    consume.add_argument("--docs", required=True)
    consume.add_argument("--src", required=True)
    consume.add_argument("--json-out", required=True)

    args = parser.parse_args(argv)
    if args.cmd == "render":
        report = render_variant_b(
            args.repo,
            Path(args.ledger),
            args.out,
            ir_path=args.ir,
            partition_path=args.partition,
            names_path=args.names,
        )
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    if args.cmd == "scan":
        json.dump(scan_docs(Path(args.docs)), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    if args.cmd == "pointing":
        from src.synthesis.variant_b.pointing import report as pointing_report

        payload = pointing_report(Path(args.docs))
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        print(text)
        if args.json_out:
            Path(args.json_out).write_text(text + "\n", encoding="utf-8")
        return 0 if payload["ok"] else 1
    if args.cmd == "gradient":
        from src.synthesis.variant_b.gradient import run_gradient

        budgets = tuple(int(item) for item in args.budgets.split(",") if item.strip())
        report = run_gradient(args.repo, Path(args.ledger), Path(args.out), budgets=budgets)
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    if args.cmd == "measure":
        from src.synthesis.variant_b.measure import measure_docs

        payload = measure_docs(
            Path(args.docs),
            repo_root=Path(args.repo) if args.repo else None,
            ledger_path=Path(args.ledger) if args.ledger else None,
        )
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        print(text)
        if args.json_out:
            Path(args.json_out).write_text(text + "\n", encoding="utf-8")
        return 0
    if args.cmd == "consume-score":
        from src.synthesis.variant_b.consumption import score_run

        payload = score_run(
            Path(args.tasks),
            Path(args.raw_dir),
            docs_root=Path(args.docs),
            src_root=Path(args.src),
        )
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    return 2
