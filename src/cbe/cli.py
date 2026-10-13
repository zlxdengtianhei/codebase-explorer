"""CLI unique entry. Schema is the argparse surface below."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _abs(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise argparse.ArgumentTypeError(f"expected an absolute path, got {value}")
    return path


def _package_version() -> str:
    try:
        from importlib.metadata import version
        return version("codebase-explorer")
    except Exception:  # noqa: BLE001 - a source checkout has no metadata
        return "source"


def build_parser() -> argparse.ArgumentParser:
    from cbe.host_run import DEFAULT_REVIEW, REVIEW_MODES

    parser = argparse.ArgumentParser(
        prog="python -m cbe",
        description="Codebase Explorer: a navigable, source-grounded documentation map of a repository",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    sub = parser.add_subparsers(dest="command", required=True)

    generate_p = sub.add_parser("generate", help="Generate documentation with fresh tool-free OpenCode or Devin "
                                "completions, one per task")
    generate_p.add_argument("repo", type=lambda value: Path(value).expanduser().resolve())
    generate_p.add_argument("--run-dir", type=_abs, default=None)
    generate_p.add_argument("--host", choices=("opencode", "devin"), default="opencode")
    generate_p.add_argument("--model", default=None)
    generate_p.add_argument("--config", type=_abs, default=None,
                            help="optional task-specific OpenCode config; default is generated inside the run")
    generate_p.add_argument("--jobs", type=int, default=4)
    generate_p.add_argument("--review", choices=REVIEW_MODES, default=DEFAULT_REVIEW)
    generate_p.add_argument("--resume", action="store_true",
                            help="continue the run in --run-dir (default: the repository's latest run)")
    generate_p.add_argument("--timeout", type=int, default=420)

    host_p = sub.add_parser("host", help="Host-agent driven generation: the CLI plans and checks, "
                            "the host agent (Claude Code, Codex) dispatches one subagent per task")
    host_sub = host_p.add_subparsers(dest="host_command", required=True)
    host_plan = host_sub.add_parser("plan", help="Scan, plan directory-first modules, and write the run state")
    host_plan.add_argument("repo", type=lambda value: Path(value).expanduser().resolve())
    host_plan.add_argument("--run-dir", type=_abs, default=None)
    host_plan.add_argument("--review", choices=REVIEW_MODES, default=DEFAULT_REVIEW)
    host_plan.add_argument("--jobs", type=int, default=4, help="maximum concurrently dispatched subagents")
    host_plan.add_argument("--host", default="other", help="label only, e.g. claude-code or codex")
    for name, text in (("next", "Lease ready tasks up to the concurrency limit and write their instruction files"),
                       ("submit", "Check one subagent result: accept, re-ask once, then normalize or fail"),
                       ("status", "Show every task's state, attempts, timing, output, and the next action"),
                       ("resume", "Continue from the run records: adopt finished results, release lost "
                        "leases, retry failed tasks"),
                       ("retry", "Give a failed task (or `all`) two fresh attempts"),
                       ("release", "Return leased tasks to the queue"),
                       ("render", "Render docs now; pending parts get placeholder pages"),
                       ("verify", "Coverage, link, catalogue, and source-drift checks"),
                       ("import-usage", "Read exact per-subagent usage recorded by Claude Code or Codex"),
                       ("cost", "Write the cost report: exact where imported, otherwise labelled estimates")):
        part = host_sub.add_parser(name, help=text)
        part.add_argument("--run-dir", type=_abs, default=None)
        part.add_argument("--repo", type=_abs, default=None, help="use the latest run of this repository")
        if name == "next":
            part.add_argument("--max", type=int, default=None)
            part.add_argument("--owner", default=None)
            part.add_argument("--reclaim-after", type=int, default=None,
                              help="release leases older than this many seconds first")
        if name in ("submit", "retry", "release"):
            part.add_argument("--task", required=name != "release",
                              help="task id" + ("; `all` retries every failed task" if name == "retry" else ""))
        if name == "submit":
            part.add_argument("--result", type=_abs, default=None)
            part.add_argument("--usage-tokens", type=int, default=None,
                              help="token total the harness reported for this subagent")
            part.add_argument("--tool-uses", type=int, default=None)
            part.add_argument("--duration-ms", type=int, default=None)
            part.add_argument("--usage-source", default=None)
        if name == "resume":
            part.add_argument("--owner", default=None)
            part.add_argument("--keep-failed", action="store_true",
                              help="do not give failed tasks fresh attempts")
        if name == "import-usage":
            part.add_argument("--harness", choices=("claude-code", "codex"), required=True)
            part.add_argument("--root", type=_abs, default=None,
                              help="Claude projects/session directory or Codex sessions directory")
        if name == "cost":
            part.add_argument("--model", default=None, help="model used for estimated tasks, e.g. claude-sonnet-5-5")
            part.add_argument("--price", default=None,
                              help="USD per million tokens: input,output,cache_write,cache_read")
            part.add_argument("--overhead", type=int, default=None,
                              help="estimated harness tokens per subagent turn context")

    find_p = sub.add_parser("find", help="Search the generated symbol catalogue")
    find_p.add_argument("--run-dir", type=_abs, required=True)
    find_p.add_argument("--term", required=True)
    find_p.add_argument("--limit", type=int, default=25)

    query_p = sub.add_parser("query", help="Return one catalogue entry by symbol ID or file path")
    query_p.add_argument("--run-dir", type=_abs, required=True)
    query_p.add_argument("--id", required=True)
    return parser


def _host(args: argparse.Namespace):
    from cbe import host_run

    command = args.host_command
    if command == "plan":
        return host_run.plan(args.repo, args.run_dir, review=args.review, jobs=args.jobs, host=args.host)
    run_dir = args.run_dir or (host_run.latest_run(args.repo) if args.repo else None)
    if run_dir is None:
        raise host_run.HostRunError("pass --run-dir, or --repo to use the repository's latest run")
    if command == "next":
        return host_run.next_tasks(run_dir, limit=args.max, owner=args.owner, reclaim_after=args.reclaim_after)
    if command == "submit":
        usage = {"total_tokens": args.usage_tokens, "tool_uses": args.tool_uses,
                 "duration_ms": args.duration_ms, "source": args.usage_source}
        return host_run.submit(run_dir, args.task, result=args.result, usage=usage)
    if command == "status":
        return host_run.status(run_dir)
    if command == "resume":
        return host_run.resume(run_dir, owner=args.owner, retry_failed=not args.keep_failed)
    if command == "retry":
        return host_run.retry(run_dir, args.task)
    if command == "release":
        return host_run.release(run_dir, args.task)
    if command == "render":
        return host_run.render(run_dir)
    if command == "verify":
        return host_run.verify(run_dir)
    if command == "import-usage":
        return host_run.import_usage(run_dir, args.harness, args.root)
    price = None
    if args.price:
        parts = [float(value) for value in args.price.split(",")]
        if len(parts) != 4:
            raise host_run.HostRunError("--price needs input,output,cache_write,cache_read")
        price = tuple(parts)
    return host_run.cost(run_dir, model=args.model, price=price,
                         overhead=args.overhead or host_run.DEFAULT_OVERHEAD_TOKENS)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            from datetime import datetime, timezone
            from uuid import uuid4
            from cbe.generate import generate

            repo = args.repo.resolve()
            if args.resume and args.run_dir is None:
                from cbe.host_run import latest_run
                args.run_dir = latest_run(repo)
            run_dir = args.run_dir or (repo / ".codebase-analysis" / "runs" /
                (datetime.now(timezone.utc).strftime("generate-%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]))
            model = args.model or ("swe-2-medium" if args.host == "devin" else "zai-coding-plan/glm-5.3-flash")
            value = generate(repo, run_dir, model=model, config=args.config,
                             jobs=args.jobs, review=args.review, timeout=args.timeout,
                             host=args.host, resume=args.resume)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            # 3 means docs were rendered but some tasks are still pending.
            return 0 if value.get("status") == "complete" else 3
        if args.command == "host":
            print(json.dumps(_host(args), ensure_ascii=False, indent=2))
            return 0
        from cbe.generate import find, query

        if args.command == "find":
            print(json.dumps(find(args.run_dir, args.term, limit=args.limit), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(query(args.run_dir, args.id), ensure_ascii=False, indent=2))
        return 0
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
