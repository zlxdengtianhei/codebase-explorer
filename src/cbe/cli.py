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


def build_parser() -> argparse.ArgumentParser:
    from cbe.host_run import DEFAULT_REVIEW, REVIEW_MODES
    from cbe.model_settings import MODEL_DEFAULTS

    parser = argparse.ArgumentParser(
        prog="python -m cbe",
        description="Codebase Explorer: a navigable, source-grounded documentation map of a repository",
    )
    from cbe import __version__

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    generate_p = sub.add_parser("generate", help="Generate documentation through an API, OpenCode, or Devin")
    generate_p.add_argument("repo", type=lambda value: Path(value).expanduser().resolve())
    generate_p.add_argument("--run-dir", type=_abs, default=None)
    generate_p.add_argument("--host", choices=("api", "opencode", "devin"), default="opencode")
    generate_p.add_argument("--model", default=None)
    generate_p.add_argument("--config", type=_abs, default=None,
                            help="optional host/API configuration file")
    generate_p.add_argument("--graph", type=_abs, default=None, help="analyzed graph matching this source snapshot")
    generate_p.add_argument("--base-url", default=None, help="OpenAI-compatible API base URL (--host api)")
    generate_p.add_argument("--api-key-env", default=None, help="environment variable containing the API key")
    generate_p.add_argument("--jobs", type=int, default=4)
    generate_p.add_argument("--review", choices=REVIEW_MODES, default=DEFAULT_REVIEW)
    generate_p.add_argument("--resume", action="store_true",
                            help="continue the run in --run-dir (default: the repository's latest run)")
    generate_p.add_argument("--timeout", type=int, default=None,
                            help="seconds per call; overrides API config/model default (otherwise 420). "
                                 "API model defaults: " + json.dumps(MODEL_DEFAULTS, sort_keys=True) +
                                 "; override via --config JSON keys timeout,output_max_tokens,reasoning_effort,"
                                 "response_format,batch_target_tokens,batch_max_tokens,price_per_million")

    host_p = sub.add_parser("host", help="Host-agent driven generation: the CLI plans and checks, "
                            "the host agent (Claude Code, Codex) dispatches one subagent per task")
    host_sub = host_p.add_subparsers(dest="host_command", required=True)
    host_plan = host_sub.add_parser("plan", help="Freeze source and graph context and plan semantic generation")
    host_plan.add_argument("repo", type=lambda value: Path(value).expanduser().resolve())
    host_plan.add_argument("--run-dir", type=_abs, default=None)
    host_plan.add_argument("--graph", type=_abs, default=None, help="analyzed graph matching this source snapshot")
    host_plan.add_argument("--review", choices=REVIEW_MODES, default=DEFAULT_REVIEW)
    host_plan.add_argument("--jobs", type=int, default=4, help="maximum concurrently dispatched subagents")
    host_plan.add_argument("--host", default="other", help="label only, e.g. claude-code or codex")
    for name, text in (("next", "Lease ready tasks up to the concurrency limit and write their instruction files"),
                       ("submit", "Check one subagent result: detail (module/repair) allows 3 answers, others 2; normalize or fail on the final invalid answer"),
                       ("status", "Show every task's state, attempts, timing, output, and the next action"),
                       ("resume", "Continue from the run records: adopt finished results, release lost "
                        "leases, retry failed tasks"),
                       ("retry", "Give a failed task (or `all`) fresh answers: detail (module/repair) allows 3, others 2"),
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

    sub.add_parser("languages", help="Show source grammars, extensions, and availability")

    graph_p = sub.add_parser("graph", help="Build and query source-linked code graphs")
    graph_sub = graph_p.add_subparsers(dest="graph_command", required=True)
    graph_build = graph_sub.add_parser("build", help="Run the configured open-source analyzers")
    graph_build.add_argument("repo", type=lambda value: Path(value).expanduser().resolve())
    graph_build.add_argument("--output", type=_abs, required=True, help="graph JSON output path")
    graph_build.add_argument("--backend", default="auto", help="analyzer selection; default: auto")
    graph_build.add_argument("--language", action="append", dest="languages", default=None)
    graph_build.add_argument("--joern-home", type=_abs, default=None)
    graph_build.add_argument("--joern-heap", default=None, metavar="SIZE",
                             help="Joern JVM maximum heap via JAVA_TOOL_OPTIONS (for example 8g); default: inherit JVM settings")
    graph_build.add_argument("--depcruise-bin", type=_abs, default=None)
    graph_build.add_argument("--timeout", type=int, default=300)
    graph_build.add_argument("--max-methods", type=int, default=None,
                             help="maximum methods for CFG export per frontend; default: unlimited; omitted methods are reported")
    graph_build.add_argument("--max-reaching-defs", type=int, default=50000)
    graph_build.add_argument("--dataflow-path-method", action="append", dest="dataflow_path_methods",
                             help="opt in to sampled value-flow paths for a named method")
    graph_build.add_argument("--max-paths-per-method", type=int, default=5)
    graph_query = graph_sub.add_parser("query", help="Select relations and their boundary nodes")
    graph_query.add_argument("--graph", type=_abs, required=True,
                             help="cbe-graph/1 JSON or a frozen context.json containing a graph")
    graph_query.add_argument("--path", action="append", dest="paths", default=None)
    graph_query.add_argument("--kind", choices=("import", "call", "cfg", "dataflow"), default=None)
    graph_query.add_argument("--direction", choices=("both", "in", "out"), default="both")
    graph_query.add_argument("--node", dest="node_id", default=None)
    graph_caps = graph_sub.add_parser("capabilities", help="Read the analyzed language/type coverage")
    graph_caps.add_argument("--graph", type=_abs, required=True)
    graph_caps.add_argument("--repo", type=_abs, help="Recompute quality with a live repository-file snapshot")

    context_p = sub.add_parser("context", help="Build or select frozen code chunks with graph evidence")
    context_sub = context_p.add_subparsers(dest="context_command", required=True)
    context_build = context_sub.add_parser("build", help="Parse source and validate an optional graph snapshot")
    context_build.add_argument("repo", type=lambda value: Path(value).expanduser().resolve())
    context_build.add_argument("--output", type=_abs, required=True)
    context_build.add_argument("--graph", type=_abs, default=None)
    context_build.add_argument("--path", action="append", dest="paths", default=None)
    context_query = context_sub.add_parser("query", help="Select code chunks and their graph boundary")
    context_query.add_argument("--context", type=_abs, required=True)
    context_query.add_argument("--path", action="append", dest="paths", required=True)

    find_p = sub.add_parser("find", help="Search the generated symbol catalogue")
    find_p.add_argument("--run-dir", type=_abs, required=True)
    find_p.add_argument("--term", required=True)
    find_p.add_argument("--limit", type=int, default=25)
    find_p.add_argument("--json", action="store_true", help="machine-readable locator fields")

    query_p = sub.add_parser("query", help="Return explanation and evidence by unit ID, symbol ID or file path")
    query_p.add_argument("--run-dir", type=_abs, required=True)
    query_p.add_argument("--id", required=True)
    query_p.add_argument("--json", action="store_true", help="machine-readable object (no duplicate detail)")
    query_p.add_argument("--edges", default=None, help="expand frozen raw edges: all or comma-separated kinds")
    source_p = sub.add_parser("source", help="Print frozen source by unit ID, symbol ID or file path; verify SHA-256 first")
    source_p.add_argument("--run-dir", type=_abs, required=True)
    source_p.add_argument("--id", required=True)
    source_p.add_argument("--context", type=int, default=0, metavar="N",
                          help="include N surrounding lines (nonnegative; default: 0)")
    for source_parser in (generate_p, host_plan, context_build, graph_build):
        source_parser.add_argument("--header-language", choices=("c", "cpp"), default=None,
                                   help="interpret .h files as C or C++ when planning source context")

    return parser


def _host(args: argparse.Namespace):
    from cbe import host_run, usage

    command = args.host_command
    if command == "plan":
        return host_run.plan(args.repo, args.run_dir, review=args.review, jobs=args.jobs, host=args.host,
                             graph_path=args.graph)
    run_dir = args.run_dir or (host_run.latest_run(args.repo) if args.repo else None)
    if run_dir is None:
        raise host_run.HostRunError("pass --run-dir, or --repo to use the repository's latest run")
    if command == "next":
        return host_run.next_tasks(run_dir, limit=args.max, owner=args.owner, reclaim_after=args.reclaim_after)
    if command == "submit":
        reported = {"total_tokens": args.usage_tokens, "tool_uses": args.tool_uses,
                    "duration_ms": args.duration_ms, "source": args.usage_source}
        return host_run.submit(run_dir, args.task, result=args.result, usage=reported)
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
        return usage.import_usage(run_dir, args.harness, args.root)
    price = None
    if args.price:
        parts = [float(value) for value in args.price.split(",")]
        if len(parts) != 4:
            raise host_run.HostRunError("--price needs input,output,cache_write,cache_read")
        price = tuple(parts)
    return usage.cost(run_dir, model=args.model, price=price,
                         overhead=args.overhead or usage.DEFAULT_OVERHEAD_TOKENS)


def main(argv: list[str] | None = None) -> int:
    from cbe.source_context import ContextError

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        header_language = getattr(args, "header_language", None)
        if header_language:
            from dataclasses import replace
            from cbe.source_context import GRAMMARS, register_language

            spec = next(spec for spec in GRAMMARS if spec.name == header_language)
            register_language(replace(spec, suffixes=tuple(dict.fromkeys((*spec.suffixes, ".h")))))
        if args.command == "languages":
            from cbe.source_context import available_languages

            print(json.dumps(available_languages(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "graph":
            from cbe.graph import analyze_graph, query_graph, read_graph_quality, GraphError, BACKEND_FAILURE_CODES

            build_error = None
            if args.graph_command == "build":
                try:
                    graph = analyze_graph(args.repo, args.output, backend=args.backend,
                                          languages=args.languages, joern_home=args.joern_home,
                                          joern_heap=args.joern_heap,
                                          depcruise_bin=args.depcruise_bin, timeout=args.timeout,
                                          max_methods=args.max_methods, max_reaching_defs=args.max_reaching_defs,
                                          dataflow_path_methods=args.dataflow_path_methods,
                                          max_paths_per_method=args.max_paths_per_method)
                except GraphError as exc:
                    if exc.graph is None:
                        raise
                    graph, build_error = exc.graph, str(exc)
                quality = read_graph_quality(graph)
                failures = [d["message"] for d in graph["diagnostics"]
                            if d.get("code") in BACKEND_FAILURE_CODES]
                failures += [f"{c.get('language')}/{c.get('graph')}: {c.get('status')}"
                             for c in quality["incomplete_capabilities"] if c.get("status") == "failed"]
                if quality["dangling_edges"]["count"]:
                    failures.append(f"dangling edges: {quality['dangling_edges']['count']} "
                                    f"{quality['dangling_edges']['examples']}")
                if build_error:
                    failures.append(build_error)
                if failures:
                    print("cbe graph build: " + "; ".join(failures), file=sys.stderr)
                value = {"output": str(args.output), "schema": graph["schema"],
                         "backend": graph["backend"], "files": len(graph["source_manifest"]),
                         "nodes": len(graph["nodes"]), "edges": len(graph["edges"]),
                         "quality": quality,
                         "capabilities": graph["capabilities"], "diagnostics": graph["diagnostics"]}
            else:
                graph = json.loads(args.graph.read_text(encoding="utf-8"))
                if isinstance(graph, dict) and graph.get("schema") == "cbe-context/1":
                    graph = graph.get("graph")
                if not isinstance(graph, dict):
                    raise ValueError("input contains no graph; this run may have been planned without one")
                if args.graph_command == "capabilities":
                    if graph.get("schema") != "cbe-graph/1":
                        raise ValueError("expected a cbe-graph/1 file")
                    if args.repo is not None:
                        from cbe.graph_backends.identity import repository_files
                        quality = read_graph_quality(graph, existing_paths=repository_files(args.repo))
                    else:
                        quality = read_graph_quality(graph)
                    value = {"backend": graph.get("backend"), "quality": quality,
                             "capabilities": graph.get("capabilities", []),
                             "diagnostics": graph.get("diagnostics", [])}
                else:
                    value = query_graph(graph, paths=args.paths, kind=args.kind,
                                        direction=args.direction, node_id=args.node_id)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 2 if build_error else 0
        if args.command == "context":
            from cbe.source_context import build_context, context_for_paths

            if args.context_command == "build":
                value = build_context(args.repo, args.paths, graph_path=args.graph)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                result = {"output": str(args.output), "schema": value["schema"],
                          "files": len(value["files"]), "chunks": len(value["chunks"]),
                          "diagnostics": value["diagnostics"]}
            else:
                value = json.loads(args.context.read_text(encoding="utf-8"))
                result = context_for_paths(value, args.paths)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
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
            if args.host == "api" and not args.model:
                raise ValueError("--host api requires --model")
            if args.host != "api" and (args.base_url is not None or args.api_key_env is not None):
                raise ValueError("--base-url and --api-key-env require --host api")
            if args.resume and header_language:
                frozen = json.loads((run_dir / "context.json").read_text(encoding="utf-8"))
                if any(row["language"] != header_language for row in frozen["files"]
                       if Path(row["path"]).suffix.lower() == ".h"):
                    raise ValueError("header language differs from the frozen context; start a new plan")
            model = args.model or ("swe-2-medium" if args.host == "devin" else "zai-coding-plan/glm-5.3-flash")
            value = generate(repo, run_dir, model=model, config=args.config,
                             jobs=args.jobs, review=args.review, timeout=args.timeout, default_timeout=420,
                             host=args.host, resume=args.resume, graph_path=args.graph,
                             api_base_url=args.base_url, api_key_env=args.api_key_env)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            # 3 means docs were rendered but some tasks are still pending.
            return 0 if value.get("status") == "complete" else 3
        if args.command == "host":
            value = _host(args)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 3 if args.host_command == "verify" and not value["ok"] else 0
        from cbe.docs import find, find_text, query, query_text, source

        if args.command == "source":
            print(source(args.run_dir, args.id, context=args.context), end="")
            return 0

        if args.command == "find":
            results = find(args.run_dir, args.term, limit=args.limit)
            print(json.dumps(results, ensure_ascii=False, indent=2) if args.json else find_text(results),
                  end="\n" if args.json else "")
            return 0
        record = query(args.run_dir, args.id, edges=args.edges)
        print(json.dumps(record, ensure_ascii=False, indent=2) if args.json else query_text(record),
              end="\n" if args.json else "")
        return 0
    except ContextError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False), file=sys.stderr)
        return 2
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
