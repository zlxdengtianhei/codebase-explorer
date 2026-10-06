"""CLI unique entry. Schema is the argparse surface below."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from cbe.errors import RunnerError
from cbe.store import LedgerStore, StoreError, derived_status


def _abs(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise argparse.ArgumentTypeError(f"expected an absolute path, got {value}")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cbe",
        description="Codebase Explorer semantic documentation workflow",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    generate_p = sub.add_parser("generate", help="Generate documentation with scripted, fresh tool-free OpenCode completions")
    generate_p.add_argument("repo", type=lambda value: Path(value).expanduser().resolve())
    generate_p.add_argument("--run-dir", type=_abs, default=None)
    generate_p.add_argument("--host", choices=("opencode", "devin"), default="opencode")
    generate_p.add_argument("--model", default=None)
    generate_p.add_argument("--config", type=_abs, default=None,
                            help="optional task-specific OpenCode config; default is generated inside the run")
    generate_p.add_argument("--jobs", type=int, default=4)
    generate_p.add_argument("--review", choices=("none", "sample"), default="sample")
    generate_p.add_argument("--timeout", type=int, default=420)

    find_p = sub.add_parser("find", help="Search the generated symbol catalogue")
    find_p.add_argument("--run-dir", type=_abs, required=True)
    find_p.add_argument("--term", required=True)
    find_p.add_argument("--limit", type=int, default=25)

    analyze_p = sub.add_parser("analyze", help="Freeze inventory, packets, graph, and detail tasks")
    analyze_p.add_argument("--repo", type=_abs, required=True)
    analyze_p.add_argument("--run-dir", type=_abs, required=True)
    analyze_p.add_argument("--legacy-run", type=_abs, default=None, help="optional same-revision legacy group tree for module-first-v2")
    analyze_p.add_argument(
        "--documentation-profile",
        choices=("legacy-v1", "weighted-v1", "module-first-v2"),
        default="weighted-v1",
        help="weighted-v1 (default) ranks Details; module-first-v2 freezes an automatic structural module plan without Detail tasks; legacy-v1 is historical",
    )

    work_p = sub.add_parser("work", help="Run decided Detail / group_body / merge tasks")
    work_p.add_argument("--run-dir", type=_abs, required=True)
    work_p.add_argument("--model", default="grok", help="grok (production) or mock (tests)")
    work_p.add_argument("--jobs", type=int, default=1)
    work_p.add_argument("--limit", type=int, default=None, help="optional max tasks this invocation")

    status_p = sub.add_parser("status", help="Derived status; not a producer PASS field")
    status_p.add_argument("--run-dir", type=_abs, required=True)
    status_p.add_argument("--json", action="store_true")

    budget_policy_p = sub.add_parser(
        "budget-policy",
        help="Show or set this run's source-read dispatch ceiling; the 2S reference line is never redefined",
    )
    budget_policy_p.add_argument("--run-dir", type=_abs, required=True)
    budget_policy_p.add_argument("--source-read-cap-multiplier", type=float, default=None,
                                  help="active dispatch ceiling as a multiple of S chars; omit to only show")
    budget_policy_p.add_argument("--reason", default=None,
                                  help="required with --source-read-cap-multiplier: the on-record authorization")
    budget_policy_p.add_argument("--set-by", default=None,
                                  help="identity recording the decision, e.g. the owner session id")

    resume_p = sub.add_parser("resume", help="Import durable raw, repair render, continue work")
    resume_p.add_argument("--run-dir", type=_abs, required=True)
    resume_p.add_argument("--model", default="grok")
    resume_p.add_argument("--jobs", type=int, default=1)
    resume_p.add_argument("--limit", type=int, default=None, help="optional max new tasks this invocation")

    render_p = sub.add_parser("render", help="Project INDEX / groups / details from the ledger")
    render_p.add_argument("--run-dir", type=_abs, required=True)
    render_p.add_argument("--output", type=_abs, default=None,
                          help="reader directory; defaults to the run's recorded current output")

    collapse_p = sub.add_parser(
        "collapse-module-plan",
        help="Build an unreviewed module-first candidate from a same-revision legacy run",
    )
    collapse_p.add_argument("--run-dir", type=_abs, required=True)
    collapse_p.add_argument("--legacy-run", type=_abs, required=True)
    collapse_p.add_argument("--out", type=_abs, required=True)

    fresh_plan_p = sub.add_parser(
        "build-module-plan", help="Build a neutral module candidate directly from a frozen inventory"
    )
    fresh_plan_p.add_argument("--run-dir", type=_abs, required=True)
    fresh_plan_p.add_argument("--out", type=_abs, required=True)

    module_packet_p = sub.add_parser(
        "module-packet", help="Build a bounded, source-verified author packet for one implementation module"
    )
    module_packet_p.add_argument("--run-dir", type=_abs, required=True)
    module_packet_p.add_argument("--plan", type=_abs, required=True)
    module_packet_p.add_argument("--group-id", required=True)
    module_packet_p.add_argument("--out", type=_abs, required=True)
    module_packet_p.add_argument("--max-source-tokens", type=int, default=12000)

    module_render_p = sub.add_parser(
        "render-module-plan",
        help="Render a candidate module plan with complete source locators and a half-code token gate",
    )
    module_render_p.add_argument("--run-dir", type=_abs, required=True)
    module_render_p.add_argument("--plan", type=_abs, required=True)
    module_render_p.add_argument("--output", type=_abs, required=True)
    module_render_p.add_argument("--explanations", type=_abs, default=None, help="independently reviewed module explanation package")

    module_members_p = sub.add_parser(
        "module-members", help="Page exact symbol ownership for a module-first candidate"
    )
    module_members_p.add_argument("--run-dir", type=_abs, required=True)
    module_members_p.add_argument("--plan", type=_abs, required=True)
    module_members_p.add_argument("--group-id", required=True)
    module_members_p.add_argument("--offset", type=int, default=0)
    module_members_p.add_argument("--limit", type=int, default=100)

    module_init_p = sub.add_parser("module-init", help="Adopt module tasks into the recoverable ledger")
    module_init_p.add_argument("--run-dir", type=_abs, required=True)
    module_claim_p = sub.add_parser("module-claim", help="Claim one external module author or review task")
    module_claim_p.add_argument("--run-dir", type=_abs, required=True)
    module_claim_p.add_argument("--group-id", required=True)
    module_claim_p.add_argument("--kind", choices=("module_author", "module_review"), required=True)
    module_claim_p.add_argument("--owner", required=True)
    module_claim_p.add_argument("--max-source-tokens", type=int, default=24000)
    module_import_p = sub.add_parser("module-import", help="Import an external module result with its claim envelope")
    module_import_p.add_argument("--run-dir", type=_abs, required=True)
    module_import_p.add_argument("--task-id", required=True)
    module_import_p.add_argument("--result", type=_abs, required=True)
    module_import_p.add_argument("--usage-receipt", type=_abs)
    module_delivery_p = sub.add_parser("module-delivery", help="Bind a module packet to positive host delivery evidence")
    module_delivery_p.add_argument("--run-dir", type=_abs, required=True)
    module_delivery_p.add_argument("--task-id", required=True)
    module_delivery_p.add_argument("--evidence", type=_abs, required=True)
    module_release_p = sub.add_parser("module-release", help="Release an abandoned module lease")
    module_release_p.add_argument("--run-dir", type=_abs, required=True)
    module_release_p.add_argument("--task-id", required=True)
    module_release_p.add_argument("--owner", required=True)
    module_refresh_p = sub.add_parser("module-refresh", help="Stage a new frozen run and conservatively carry valid module explanations")
    module_refresh_p.add_argument("--old-run", type=_abs, required=True)
    module_refresh_p.add_argument("--repo", type=_abs, required=True)
    module_refresh_p.add_argument("--new-run", type=_abs, required=True)
    fact_init_p = sub.add_parser("fact-init", help="Register source-partitioned short-fact tasks in a module-first run")
    fact_init_p.add_argument("--run-dir", type=_abs, required=True)
    fact_init_p.add_argument("--batched", action="store_true", help="combine adjacent source partitions in the same ledger")
    fact_init_p.add_argument("--auto-budget", action="store_true", help="select the lowest-cost feasible pre-dispatch batch plan")
    fact_init_p.add_argument("--max-input-tokens", type=int)
    fact_init_p.add_argument("--max-output-estimate", type=int)
    fact_init_p.add_argument("--usage-baseline-run", type=_abs, default=None)
    attribution_init_p = sub.add_parser("attribution-init", help="Register attribution batches for non-executable objects in the same ledger")
    attribution_init_p.add_argument("--run-dir", type=_abs, required=True)
    attribution_init_p.add_argument("--max-batch-chars", type=int, default=12000)
    system_init_p = sub.add_parser("system-init", help="Register the system-level synthesis tasks once implementation modules are accepted")
    system_init_p.add_argument("--run-dir", type=_abs, required=True)
    system_init_p.add_argument("--allow-pending-modules", action="store_true")
    fact_plan_p = sub.add_parser("fact-plan", help="Preview deterministic multi-partition batches without mutating the run")
    fact_plan_p.add_argument("--run-dir", type=_abs, required=True)
    fact_plan_p.add_argument("--auto-budget", action="store_true", help="compare feasible first-use plans within explicit ceilings")
    fact_plan_p.add_argument("--max-input-tokens", type=int)
    fact_plan_p.add_argument("--max-output-estimate", type=int)
    fact_plan_p.add_argument("--usage-baseline-run", type=_abs, default=None)
    fact_rebatch_p = sub.add_parser("fact-rebatch", help="Atomically regroup only never-claimed fact batches")
    fact_rebatch_p.add_argument("--run-dir", type=_abs, required=True)
    fact_rebatch_p.add_argument("--max-input-tokens", type=int, default=8000)
    fact_rebatch_p.add_argument("--max-output-estimate", type=int, default=3000)
    fact_claim_p = sub.add_parser("fact-claim", help="Prepare a short-fact author or review packet")
    fact_claim_p.add_argument("--run-dir", type=_abs, required=True)
    fact_claim_p.add_argument("--packet-id", required=True)
    fact_claim_p.add_argument("--owner", required=True)
    fact_claim_p.add_argument("--kind", choices=("author", "review"), default="author")
    fact_claim_p.add_argument("--max-input-tokens", type=int, help="complete prompt limit for this fresh claim (1000..24000); default uses unchanged batch limit")
    fact_claim_p.add_argument("--review-ids-file", type=_abs, default=None,
                              help="JSON list of IDs for a bounded independent source sample")
    fact_claim_p.add_argument("--full-context", action="store_true",
                              help="present the full frozen partitions while checking only assigned IDs")
    fact_claim_p.add_argument("--review-question-file", type=_abs, default=None,
                              help="specific prior-review conflict to adjudicate against frozen source")
    context_repair_p = sub.add_parser("fact-reconcile-context", help="Explicitly queue one targeted author rewrite for unresolved context findings using exact frozen locators")
    context_repair_p.add_argument("--run-dir", type=_abs, required=True)
    context_repair_p.add_argument("--task-id", required=True)
    context_repair_p.add_argument("--decision", type=_abs, required=True)
    feedback_p = sub.add_parser("native-feedback", help="Register reader findings for fresh native audits without claiming or sending")
    feedback_p.add_argument("--run-dir", type=_abs, required=True)
    feedback_p.add_argument("--findings", type=_abs, required=True,
                            help="JSON list of {target_id (or symbol_id), reason}; system target is 'system'")
    fact_delivery_p = sub.add_parser("fact-delivery", help="Bind positive host delivery evidence to a prepared fact packet")
    fact_delivery_p.add_argument("--run-dir", type=_abs, required=True)
    fact_delivery_p.add_argument("--task-id", required=True)
    fact_delivery_p.add_argument("--evidence", type=_abs, required=True)
    fact_import_p = sub.add_parser("fact-import", help="Import one claimed short-fact result")
    fact_import_p.add_argument("--run-dir", type=_abs, required=True)
    fact_import_p.add_argument("--task-id", required=True)
    fact_import_p.add_argument("--result", type=_abs, required=True)
    fact_release_p = sub.add_parser("fact-release", help="Release a fact lease and account for delivery state")
    fact_release_p.add_argument("--run-dir", type=_abs, required=True)
    fact_release_p.add_argument("--task-id", required=True)
    fact_release_p.add_argument("--owner", required=True)
    fact_split_p = sub.add_parser("fact-split-repair", help="Partition unleased fact work without changing frozen input identity")
    fact_split_p.add_argument("--run-dir", type=_abs, required=True)
    fact_split_p.add_argument("--task-id", required=True)
    fact_reject_p = sub.add_parser("fact-reject", help="Quarantine a delivered invalid raw fact result and target repair")
    fact_reject_p.add_argument("--run-dir", type=_abs, required=True)
    fact_reject_p.add_argument("--task-id", required=True)
    fact_reject_p.add_argument("--result", type=_abs, required=True)
    fact_reject_p.add_argument("--reason", required=True)
    fact_reject_p.add_argument("--repair-ids-file", type=_abs, required=True)
    module_reject_p = sub.add_parser("module-reject", help="Reject mechanically invalid completed module author business output, preserving raw, cost and full scope")
    module_reject_p.add_argument("--run-dir", type=_abs, required=True)
    module_reject_p.add_argument("--task-id", required=True)
    module_reject_p.add_argument("--result", type=_abs, required=True)
    module_reject_p.add_argument("--reason", required=True)
    module_reject_p.add_argument("--host-completion", type=_abs, required=True, help="original OpenCode public Task completion capture; active or misbound child refuses")
    fact_merge_p = sub.add_parser("fact-merge", help="Merge reviewed source fragments without a model call")
    fact_merge_p.add_argument("--run-dir", type=_abs, required=True)
    fact_merge_p.add_argument("--limit", type=int, default=None)
    reconcile_p = sub.add_parser("call-reconcile", help="Finalize an uncertain call after an explicit no-delivery evidence search")
    reconcile_p.add_argument("--run-dir", type=_abs, required=True)
    reconcile_p.add_argument("--call-id", required=True)
    reconcile_p.add_argument("--searched-file", type=_abs, required=True,
                             help="JSON list of evidence locations searched for this call")
    reconcile_p.add_argument("--note", default="")
    abandon_p = sub.add_parser("native-abandon", help="Explicitly abandon a stopped controller's unresolved offer; retain unknown delivery and retry unaccepted obligations")
    abandon_p.add_argument("--run-dir", type=_abs, required=True)
    abandon_p.add_argument("--call-id", required=True)
    abandon_p.add_argument("--decision", type=_abs, required=True)
    cancelled_p = sub.add_parser("native-cancelled", help="Reconcile an actually launched Agent cancelled before its native handle was recorded")
    cancelled_p.add_argument("--run-dir", type=_abs, required=True)
    cancelled_p.add_argument("--invocation-id", required=True)
    cancelled_p.add_argument("--host-metadata", type=_abs, required=True)
    cancelled_p.add_argument("--host-output", type=_abs, required=True)
    cancelled_p.add_argument("--parent-public-evidence", type=_abs, required=True,
                             help="original public parent Agent tool launch capture binding parent/tool/agent and frozen invocation")
    system_import_p = sub.add_parser("system-import", help="Import an existing positively delivered system result with its original envelope")
    system_import_p.add_argument("--run-dir", type=_abs, required=True)
    system_import_p.add_argument("--task-id", required=True)
    system_import_p.add_argument("--result", type=_abs, required=True)
    terminal_p = sub.add_parser("native-reconcile-terminal", help="Dispose a proven terminal obsolete native call while preserving its cost and current tasks")
    terminal_p.add_argument("--run-dir", type=_abs, required=True)
    terminal_p.add_argument("--call-id", required=True)
    terminal_p.add_argument("--event", type=_abs)
    terminal_p.add_argument("--host-metadata", type=_abs)
    terminal_p.add_argument("--host-output", type=_abs)
    terminal_p.add_argument("--parent-public-evidence", type=_abs)
    terminal_p.add_argument("--host-session", type=_abs, help="original public Codex child rollout; parent-public-evidence is the public parent rollout")
    terminal_p.add_argument("--acknowledge-misbound-prompt", action="store_true")
    produce_p = sub.add_parser("produce", help="Execute one module-first fact, module, or system task through a configured public provider")
    produce_p.add_argument("--run-dir", type=_abs, required=True)
    produce_p.add_argument("--scope", choices=("fact", "module", "system"), required=True)
    produce_p.add_argument("--id", required=True, help="batch/packet ID for facts, group ID for modules; ignored for system")
    produce_p.add_argument("--kind", choices=("author", "review"), required=True)
    produce_p.add_argument("--owner", required=True)
    produce_p.add_argument("--provider-config", type=_abs, required=True)
    produce_p.add_argument("--resume", action="store_true", help="reconcile an existing call; never resends")
    produce_p.add_argument("--max-source-tokens", type=int, default=24000)
    produce_p.add_argument("--full-context", action="store_true", help="present full frozen fact partitions for source review")
    produce_p.add_argument("--review-ids-file", type=_abs, default=None,
                           help="JSON list for a focused fact review or supplemental audit")
    produce_p.add_argument("--review-question-file", type=_abs, default=None,
                           help="specific conflict for an independent fact reviewer")

    native_next_p = sub.add_parser(
        "native-next", help="Prepare the next host-owned subagent task without a provider config")
    native_next_p.add_argument("--run-dir", type=_abs, required=True)
    native_next_p.add_argument("--owner", required=True)
    native_next_p.add_argument("--model", default=None,
                               help="optional host-requested model; observation is recorded separately")
    native_next_p.add_argument("--count", type=int, default=1)
    native_next_p.add_argument("--max-input-tokens", type=int, help="complete prompt limit for fresh fact calls in this invocation (1000..24000); keeps all content")
    native_next_p.add_argument("--audit-task", action="append", default=[],
                               help="explicitly dispatch only this existing finding review in none; retains run policy")
    native_next_p.add_argument("--review-mode", choices=("none", "sample", "full"), default=None,
                               help="new runs default to none; explicitly migrate existing future review obligations")
    native_next_p.add_argument("--adopt-review-efficiency", action="store_true",
                               help="explicitly migrate only untouched pending structural attributions")
    native_next_p.add_argument("--review-bundles", action="store_true", default=None,
                               help="pack ready independent review calls within the full prompt window")
    native_record_p = sub.add_parser(
        "native-record", help="Bind one native subagent event and import its completed result")
    native_record_p.add_argument("--run-dir", type=_abs, required=True)
    native_identity = native_record_p.add_mutually_exclusive_group(required=True)
    native_identity.add_argument("--call-id")
    native_identity.add_argument("--invocation-id")
    native_record_p.add_argument("--event", type=_abs, default=None, help="advanced legacy event JSON")
    native_record_p.add_argument("--status", choices=["started", "completed", "failed", "not_sent"])
    native_record_p.add_argument("--host")
    native_record_p.add_argument("--child-handle")
    native_record_p.add_argument("--host-metadata", type=_abs)
    native_record_p.add_argument("--parent-public-evidence", type=_abs)
    native_record_p.add_argument("--host-result", type=_abs)
    native_record_p.add_argument("--session-file", type=_abs)
    native_record_p.add_argument("--transport", choices=["file", "inline"], default="file")
    native_record_p.add_argument("--result", type=_abs, default=None)

    binding_p = sub.add_parser("native-reconcile-binding", help="Correct two public-launch-proven parent pairing identities; preserves business and usage")
    binding_p.add_argument("--run-dir", type=_abs, required=True)
    binding_p.add_argument("--call-id", required=True)
    binding_p.add_argument("--host-metadata", type=_abs, required=True)
    binding_p.add_argument("--conflicting-call-id", required=True)
    binding_p.add_argument("--conflicting-metadata", type=_abs, required=True)
    binding_p.add_argument("--parent-public-evidence", type=_abs, required=True)

    refresh_p = sub.add_parser("refresh", help="Re-freeze source and propagate stale records")
    refresh_p.add_argument("--run-dir", type=_abs, required=True)
    refresh_p.add_argument("--repo", type=_abs, required=True)

    query_p = sub.add_parser("query", help="Fetch one ledger record by id")
    query_p.add_argument("--run-dir", type=_abs, required=True)
    query_p.add_argument("--id", required=True)

    resolve_p = sub.add_parser("resolve", help="Resolve one record to its published reader page")
    resolve_p.add_argument("--run-dir", type=_abs, required=True)
    resolve_p.add_argument("--id", required=True)

    edges_p = sub.add_parser("group-edges", help="Page exact frozen graph evidence for group inputs")
    edges_p.add_argument("--run-dir", type=_abs, required=True)
    edges_p.add_argument("--input-ids-file", type=_abs, required=True)
    edges_p.add_argument("--section", choices=("internal", "boundary", "unknown"), required=True)
    edges_p.add_argument("--offset", type=int, default=0)
    edges_p.add_argument("--limit", type=int, default=100)

    promote_p = sub.add_parser("promote", help="Raise one weighted symbol tier with source evidence")
    promote_p.add_argument("--run-dir", type=_abs, required=True)
    promote_p.add_argument("--symbol-id", required=True)
    promote_p.add_argument("--tier", choices=("standard", "deep"), default=None)
    promote_p.add_argument("--reason", default=None, help="manual missing fact; omit to consume a producer request")
    promote_p.add_argument("--source-line", default=None, help="required with --reason")
    promote_p.add_argument("--extra-tokens", type=int, default=None, help="evidenced extra content budget, including within deep")

    import_p = sub.add_parser("import-result", help="Import a claimed group/review/detail result")
    import_p.add_argument("--run-dir", type=_abs, required=True)
    import_p.add_argument("--task-id", required=True)
    import_p.add_argument("--result", type=_abs, required=True)
    import_p.add_argument("--call-id", default=None, help="registered call_id")
    import_p.add_argument(
        "--external",
        action="store_true",
        help="mark the result as produced by a session-dispatched external sub-agent",
    )

    release_p = sub.add_parser("release", help="Release dead leases or cancel obsolete claims")
    release_p.add_argument("--run-dir", type=_abs, required=True)
    release_p.add_argument("--task-ids-file", type=_abs, required=True)
    release_p.add_argument("--cancel", action="store_true")

    claim_p = sub.add_parser("claim", help="Lease a detail/group-design/review packet")
    claim_p.add_argument("--run-dir", type=_abs, required=True)
    claim_p.add_argument("--kind", required=True, choices=("detail", "merge", "group_body", "group", "review"))
    claim_p.add_argument("--task-id", default=None)
    claim_p.add_argument(
        "--count",
        type=int,
        default=1,
        help="--kind detail only: claim up to N runnable detail tasks",
    )
    claim_p.add_argument(
        "--input-ids-file",
        type=_abs,
        default=None,
        help="JSON string array of fresh Detail/group ids for --kind group",
    )
    claim_p.add_argument(
        "--target-ids-file",
        type=_abs,
        default=None,
        help="JSON string array of review target ids for --kind review",
    )
    claim_p.add_argument(
        "--replace-group-id",
        default=None,
        help="Allow regrouping this group's current direct children in the same claim",
    )
    claim_p.add_argument(
        "--include-source",
        action="store_true",
        help="Review only: pack frozen source spans after reserving the 2S budget",
    )
    claim_p.add_argument("--page", type=int, default=0, help="Frontier page (0-based)")
    claim_p.add_argument("--page-size", type=int, default=40, help="Frontier page size")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            from datetime import datetime, timezone
            from uuid import uuid4
            from cbe.generate import generate

            repo = args.repo.resolve()
            run_dir = args.run_dir or (repo / ".codebase-analysis" / "runs" /
                (datetime.now(timezone.utc).strftime("generate-%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]))
            model = args.model or ("swe-2-medium" if args.host == "devin" else "zai-coding-plan/glm-5.3-flash")
            value = generate(repo, run_dir, model=model, config=args.config,
                             jobs=args.jobs, review=args.review, timeout=args.timeout,
                             host=args.host)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.command == "find":
            from cbe.generate import find

            print(json.dumps(find(args.run_dir, args.term, limit=args.limit), ensure_ascii=False, indent=2))
            return 0
        if args.command == "module-reject":
            from cbe.module_business_reject import reject_result
            value = reject_result(args.run_dir,args.task_id,args.result,reason=args.reason,host_completion=args.host_completion)
            print(json.dumps(value,ensure_ascii=False,indent=2))
            return 0
        if args.command == "fact-reconcile-context":
            from cbe.module_facts import queue_uncertainty_reconciliation
            decision = json.loads(args.decision.read_text(encoding="utf-8"))
            task_id = queue_uncertainty_reconciliation(args.run_dir, args.task_id,
                decision.get("symbol_ids") or [], decision=decision)
            if task_id is None:
                raise ValueError("current finding cannot be reconciled by a one-symbol author rewrite")
            print(json.dumps({"task_id": task_id, "model_sent": False,
                "business_acceptance": "none", "next_action": "native-next"}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "native-feedback":
            from cbe.module_facts import register_reader_findings
            value = register_reader_findings(args.run_dir, json.loads(args.findings.read_text(encoding="utf-8")))
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.command == "module-refresh":
            from cbe.module_refresh import staged_refresh

            print(json.dumps(staged_refresh(args.old_run, args.repo, args.new_run), ensure_ascii=False, indent=2))
            return 0
        if args.command in {"fact-init", "fact-plan", "fact-rebatch", "fact-claim", "fact-delivery", "fact-import", "fact-release", "fact-split-repair", "fact-reject", "fact-merge", "attribution-init", "module-delivery"}:
            from cbe import module_facts

            if args.command == "fact-init":
                value = module_facts.initialize(args.run_dir, batched=args.batched,
                    max_input_tokens=8000 if args.max_input_tokens is None else args.max_input_tokens,
                    max_output_estimate=3000 if args.max_output_estimate is None else args.max_output_estimate,
                    usage_baseline_run=args.usage_baseline_run,
                    auto_budget=args.auto_budget,
                    auto_input_cap=args.max_input_tokens if args.auto_budget else None,
                    auto_output_cap=args.max_output_estimate if args.auto_budget else None)
            elif args.command == "attribution-init":
                value = module_facts.register_attribution_batches(args.run_dir,
                    max_batch_chars=args.max_batch_chars)
            elif args.command == "system-init":
                from cbe import system_workflow
                value = system_workflow.initialize(args.run_dir,
                    require_modules=not args.allow_pending_modules)
            elif args.command == "fact-plan":
                value = (module_facts.preview_auto_batches(
                    args.run_dir, max_input_cap=args.max_input_tokens,
                    max_output_cap=args.max_output_estimate,
                    usage_baseline_run=args.usage_baseline_run)
                    if args.auto_budget else module_facts.preview_batches(
                        args.run_dir,
                        max_input_tokens=8000 if args.max_input_tokens is None else args.max_input_tokens,
                        max_output_estimate=3000 if args.max_output_estimate is None else args.max_output_estimate,
                        usage_baseline_run=args.usage_baseline_run))
            elif args.command == "fact-rebatch":
                value = module_facts.rebatch_pending(args.run_dir,
                    max_input_tokens=args.max_input_tokens,
                    max_output_estimate=args.max_output_estimate)
            elif args.command == "fact-claim":
                review_ids = (
                    json.loads(args.review_ids_file.read_text(encoding="utf-8"))
                    if args.review_ids_file else None
                )
                value = module_facts.claim(args.run_dir, args.packet_id, owner=args.owner,
                                           kind=args.kind, review_ids=review_ids,
                                           full_context=args.full_context,
                                           max_input_tokens=args.max_input_tokens,
                                           review_question=(args.review_question_file.read_text(encoding="utf-8")
                                                            if args.review_question_file else None))
            elif args.command in {"fact-delivery", "module-delivery"}:
                value = module_facts.mark_delivered(args.run_dir, args.task_id, args.evidence)
            elif args.command == "fact-import":
                value = module_facts.import_result(args.run_dir, args.task_id, args.result)
            elif args.command == "fact-reject":
                value = module_facts.reject_result(args.run_dir, args.task_id, args.result,
                    reason=args.reason,
                    repair_ids=json.loads(args.repair_ids_file.read_text(encoding="utf-8")))
            elif args.command == "fact-merge":
                value = module_facts.merge_ready(args.run_dir, limit=args.limit)
            elif args.command == "fact-split-repair":
                changed = module_facts.split_pending_repair(args.run_dir, args.task_id, allow_pending=True)
                value = {"task_id": args.task_id, "split": changed,
                         "next_action": "native-next" if changed else "reconcile_active_call_or_indivisible_scope"}
            else:
                value = module_facts.release(args.run_dir, args.task_id, owner=args.owner)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.command == "native-abandon":
            from cbe.native_abandon import abandon
            print(json.dumps(abandon(args.run_dir, args.call_id, args.decision), ensure_ascii=False, indent=2))
            return 0
        if args.command == "native-reconcile-terminal":
            from cbe.native_terminal import reconcile_terminal
            value = reconcile_terminal(args.run_dir, args.call_id, event=args.event,
                host_metadata=args.host_metadata, host_output=args.host_output,
                parent_public_evidence=args.parent_public_evidence,
                host_session=args.host_session,
                acknowledge_misbound_prompt=args.acknowledge_misbound_prompt)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.command == "system-import":
            from cbe.system_workflow import import_result
            print(json.dumps(import_result(args.run_dir, args.task_id, args.result), ensure_ascii=False, indent=2))
            return 0
        if args.command == "native-cancelled":
            from cbe.native_bundles import record_cancelled_invocation
            value = record_cancelled_invocation(args.run_dir, args.invocation_id,
                host_metadata=args.host_metadata, host_output=args.host_output,
                parent_public_evidence=args.parent_public_evidence)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.command == "call-reconcile":
            from cbe.store import reconcile_call_delivery

            searched = json.loads(args.searched_file.read_text(encoding="utf-8"))
            store = LedgerStore(args.run_dir)

            def _reconcile(current: dict) -> dict:
                call = current.get("calls", {}).get(args.call_id) or {}
                if call.get("task_id", "").startswith(("task:fact_", "task:module_", "task:system_")):
                    from cbe.native_handoff import reconcile_existing_call
                    reconcile_existing_call(current, args.call_id, searched=searched, note=args.note)
                else:
                    reconcile_call_delivery(current, args.call_id,
                                            conclusion="no_delivery_evidence",
                                            searched=searched, note=args.note)
                return current

            updated = store.mutate(_reconcile)
            record = (updated.get("calls") or {})[args.call_id]
            print(json.dumps({"call_id": args.call_id, "state": record["state"],
                              "extra": record.get("extra")}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "produce":
            from cbe.external_provider import produce
            value = produce(args.run_dir, args.id, scope=args.scope, kind=args.kind,
                            owner=args.owner, provider_config=args.provider_config,
                            resume=args.resume, max_source_tokens=args.max_source_tokens,
                            full_context=args.full_context,
                            review_ids=(json.loads(args.review_ids_file.read_text(encoding="utf-8"))
                                        if args.review_ids_file else None),
                            review_question=(args.review_question_file.read_text(encoding="utf-8")
                                             if args.review_question_file else None))
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.command in {"native-next", "native-record"}:
            from cbe.native_handoff import next_work, record, record_event

            if args.command == "native-record" and args.invocation_id:
                from cbe.native_bundles import record_invocation
                if args.host_metadata or args.parent_public_evidence:
                    raise ValueError("launch metadata applies to a single call; invocation uses its original bundle evidence")
                if args.event:
                    raise ValueError("invocation record uses explicit host/session/result inputs")
                value = record_invocation(args.run_dir,args.invocation_id,status=args.status,host=args.host,
                    child_handle=args.child_handle,host_result=args.host_result,
                    session_file=args.session_file,result_path=args.result)
                print(json.dumps(value,ensure_ascii=False,indent=2))
                return 0

            if args.command == "native-record" and args.event and (args.host_metadata or args.parent_public_evidence):
                raise ValueError("choose advanced event or verified launch metadata; do not silently ignore launch evidence")
            value = (next_work(args.run_dir, owner=args.owner, model=args.model,
                               count=args.count, adopt_review_efficiency=args.adopt_review_efficiency,
                               review_bundles=args.review_bundles, review_mode=args.review_mode,
                               audit_tasks=args.audit_task,
                               max_input_tokens=args.max_input_tokens)
                     if args.command == "native-next" else
                     record_event(args.run_dir, args.call_id, args.event,
                                  result_path=args.result) if args.event else
                     record(args.run_dir, args.call_id, status=args.status, host=args.host,
                            child_handle=args.child_handle, host_result=args.host_result,
                            session_file=args.session_file, result_path=args.result,
                            transport=args.transport, host_metadata=args.host_metadata,
                            parent_public_evidence=args.parent_public_evidence))
            if args.command == "native-next":
                value["active_semantics"] = "ledger protection records; not host running children"
                value["protected_call_count"] = len(value.get("active") or [])
                value["host_running_count"] = None
                value["dispatch_rule"] = "Spawn each latest ready item once, pairing call/task/generation/prompt path; old ready and active are not retry work"
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.command == "native-reconcile-binding":
            from cbe.native_binding import reconcile_binding
            value = reconcile_binding(args.run_dir, args.call_id, host_metadata=args.host_metadata,
                conflicting_call_id=args.conflicting_call_id, conflicting_metadata=args.conflicting_metadata,
                parent_public_evidence=args.parent_public_evidence)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.command in {"module-init", "module-claim", "module-import", "module-release"}:
            from cbe import module_workflow

            if args.command == "module-init":
                value = module_workflow.initialize(args.run_dir)
            elif args.command == "module-claim":
                value = module_workflow.claim(args.run_dir, args.group_id, kind=args.kind,
                    owner=args.owner, max_source_tokens=args.max_source_tokens)
            elif args.command == "module-import":
                value = module_workflow.import_result(args.run_dir, args.task_id, args.result,
                    usage_receipt=args.usage_receipt)
            else:
                value = module_workflow.release(args.run_dir, args.task_id, owner=args.owner)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.command == "analyze":
            from cbe.runner import analyze

            ledger = analyze(
                args.repo, args.run_dir,
                documentation_profile=args.documentation_profile,
                legacy_run=args.legacy_run,
            )
            print(json.dumps({
                "run_id": ledger.get("run_id"),
                "source_revision": ledger.get("source_revision"),
                "s_chars": (ledger.get("inventory") or {}).get("s_chars"),
                "files": len((ledger.get("inventory") or {}).get("files") or {}),
                "symbols": len((ledger.get("inventory") or {}).get("symbols") or {}),
                "documentation_profile": args.documentation_profile,
                "tasks": len(ledger.get("tasks") or {}),
                "run_dir": str(args.run_dir),
            }, indent=2))
            return 0
        if args.command == "work":
            from cbe.runner import work

            result = work(
                args.run_dir,
                model=args.model,
                jobs=args.jobs,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "budget-policy":
            from cbe.store import set_budget_policy, show_budget_policy

            if args.source_read_cap_multiplier is None:
                value = show_budget_policy(args.run_dir)
            else:
                value = set_budget_policy(
                    args.run_dir,
                    multiplier=args.source_read_cap_multiplier,
                    reason=args.reason or "",
                    set_by=args.set_by,
                )
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if args.command == "status":
            ledger = LedgerStore(args.run_dir).open()
            payload = derived_status(ledger)
            if (ledger.get("documentation_policy") or {}).get("version") == "module-first-v2":
                from cbe.module_explanations import validate_module_explanations
                from cbe.module_first_render import _validate_plan, fact_projection_hash

                plan = json.loads((args.run_dir / "module_plan.json").read_text(encoding="utf-8"))
                _validate_plan(ledger, plan)
                explanations_path = args.run_dir / "module_explanations.json"
                if ledger.get("module_workflow_version"):
                    from cbe.module_workflow import accepted_package, SUPPORT_IDS

                    package = accepted_package(ledger)
                else:
                    package = (
                        json.loads(explanations_path.read_text(encoding="utf-8"))
                        if explanations_path.exists()
                        else {"source_revision": ledger["source_revision"], "modules": {}}
                    )
                accepted = validate_module_explanations(ledger, plan, package)
                support_ids = set(SUPPORT_IDS) if ledger.get("module_workflow_version") else {
                    "test-support-catalogue", "example-source-catalogue",
                    "docs-and-release-catalogue", "example-support-catalogue",
                    "docs-support-catalogue", "extra-support-catalogue",
                    "release-support-catalogue",
                }
                implementation_ids = sorted(
                    gid for gid, group in plan["groups"].items()
                    if group.get("member_ids") and gid not in support_ids
                )
                accepted_implementation = set(accepted) & set(implementation_ids)
                payload["module_progress"] = {
                    "group_count": len(plan["groups"]),
                    "implementation_module_count": len(implementation_ids),
                    "accepted_implementation_count": len(accepted_implementation),
                    "pending_implementation_count": len(implementation_ids) - len(accepted_implementation),
                    "pending_implementation_ids": [gid for gid in implementation_ids if gid not in accepted_implementation],
                    "support_catalogue_count": sum(
                        bool(group.get("member_ids")) and gid in support_ids
                        for gid, group in plan["groups"].items()
                    ),
                    "candidate_group_count": len(plan["groups"]) - len(accepted),
                }
                symbols = ledger["inventory"]["symbols"]
                details = ledger.get("details") or {}
                reviews = ledger.get("fact_reviews") or {}
                fact_progress: dict[str, dict[str, int]] = {
                    "implementation": {}, "support": {},
                }
                for gid, group in plan["groups"].items():
                    part = "support" if gid in support_ids else "implementation"
                    for sid in group.get("member_ids") or []:
                        if symbols[sid].get("kind") not in {"function", "method", "lambda"}:
                            continue
                        detail = details.get(sid)
                        review = reviews.get(sid) or {}
                        state = "catalogued"
                        if isinstance(detail, dict):
                            digest = hashlib.sha256(json.dumps(
                                detail, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                            ).encode()).hexdigest()
                            if review.get("content_sha256") == digest:
                                state = review.get("state") or "author_fact"
                        counts = fact_progress[part]
                        counts[state] = counts.get(state, 0) + 1
                payload["fact_progress"] = fact_progress
                attribution_progress: dict[str, int] = {}
                for sid, symbol in symbols.items():
                    if symbol.get("kind") in {"function", "method", "lambda"}:
                        continue
                    detail = details.get(sid)
                    review = reviews.get(sid) or {}
                    state = "catalogued"
                    if isinstance(detail, dict):
                        digest = hashlib.sha256(json.dumps(
                            detail, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                        ).encode()).hexdigest()
                        if review.get("content_sha256") == digest:
                            state = review.get("state") or "author_fact"
                    attribution_progress[state] = attribution_progress.get(state, 0) + 1
                payload["attribution_progress"] = attribution_progress
                from cbe.system_workflow import accepted_system
                system_record = accepted_system(ledger)
                payload["system_progress"] = {
                    "state": (ledger.get("system_record") or {}).get("state") or "none",
                    "accepted": system_record is not None,
                }
                manifest_path = Path(ledger.get("reader_output_dir") or args.run_dir / "render") / "manifest.json"
                if manifest_path.exists():
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    compact = lambda value: json.dumps(
                        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    ).encode("utf-8")
                    plan_hash = hashlib.sha256(compact(plan)).hexdigest()
                    package_hash = hashlib.sha256(compact(
                        package if (explanations_path.exists() or ledger.get("module_workflow_version")) else {}
                    )).hexdigest()
                    diagnostics = ledger.get("reader_render_diagnostics") or manifest
                    current = (
                        manifest.get("source_revision") == ledger["source_revision"]
                        and diagnostics.get("plan_sha256") == plan_hash
                        and diagnostics.get("explanations_sha256") == package_hash
                        and diagnostics.get("facts_sha256") == fact_projection_hash(ledger)
                    )
                    payload["module_progress"]["render_state"] = "current" if current else "stale"
                    if current:
                        payload["module_progress"]["published_tokens"] = (
                            manifest.get("token_budget") or {}
                        ).get("published_tokens")
                        payload["module_progress"]["effective_document_tokens"] = (
                            manifest.get("token_budget") or {}
                        ).get("effective_document_tokens")
                else:
                    payload["module_progress"]["render_state"] = "missing"
            if args.json:
                print(json.dumps(payload, indent=2))
            else:
                if payload.get("module_progress"):
                    progress = payload["module_progress"]
                    documentation = payload["documentation_budget"]
                    print(
                        f"run {payload.get('run_id')} rev {payload.get('ledger_revision')} "
                        "profile=module-first-v2 "
                        f"source_exposure={payload.get('source_exposure_chars')}/{payload.get('cap_chars')} "
                        f"L={payload.get('known_source_chars')} "
                        f"U={payload.get('possible_source_upper_chars')} "
                        f"reserved={payload.get('reserved_chars')}"
                    )
                    print(
                        "modules",
                        f"accepted={progress['accepted_implementation_count']}/"
                        f"{progress['implementation_module_count']} "
                        f"pending={progress['pending_implementation_count']} "
                        f"support_catalogues={progress['support_catalogue_count']}",
                    )
                    print(
                        "documentation",
                        f"source={documentation.get('source_tokens')} "
                        f"cap={documentation.get('published_cap_tokens')} "
                        f"published={progress.get('published_tokens', 'unknown')} "
                        f"render={progress['render_state']} "
                        f"groups={progress['group_count']}/{documentation.get('group_limit')}",
                    )
                    print("facts", json.dumps(payload.get("fact_progress"), ensure_ascii=False))
                else:
                    print(
                        f"run {payload.get('run_id')} rev {payload.get('ledger_revision')} "
                        f"details={payload.get('detail_count')} groups={payload.get('group_count')} "
                        f"source_exposure={payload.get('source_exposure_chars')}/{payload.get('cap_chars')} "
                        f"L={payload.get('known_source_chars')} U={payload.get('possible_source_upper_chars')} "
                        f"status={payload.get('logical_exposure_status')}"
                    )
                    print("tasks", json.dumps(payload.get("task_counts")))
                    if payload.get("documentation_budget"):
                        documentation = payload["documentation_budget"]
                        print(
                            "documentation",
                            f"source={documentation.get('source_tokens')} "
                            f"cap={documentation.get('published_cap_tokens')} "
                            f"fixed_navigation={documentation.get('fixed_navigation_tokens')} "
                            f"detail_allocated={documentation.get('detail_allocated_tokens')} "
                            f"groups_reserved={documentation.get('group_reserve_tokens')} "
                            f"groups={payload.get('group_count')}/{documentation.get('group_limit')}",
                        )
                    frontier = payload.get("frontier") or {}
                    details = (frontier.get("ungrouped_details") or {}).get("total")
                    groups = (frontier.get("fresh_groups") or {}).get("total")
                    print(f"frontier ungrouped_details={details} fresh_groups={groups}")
            return 0
        if args.command == "resume":
            from cbe.runner import resume

            print(
                json.dumps(
                    resume(
                        args.run_dir,
                        model=args.model,
                        jobs=args.jobs,
                        limit=args.limit,
                            ),
                    indent=2,
                )
            )
            return 0
        if args.command == "render":
            from cbe.render import render as render_run
            from cbe.runner import failpoint

            failpoint("after_commit_before_render")
            result = render_run(args.run_dir, output_dir=args.output)
            if result.get("documentation_policy_version") == "weighted-v1":
                result = {
                    "ledger_revision": result.get("ledger_revision"),
                    "page_count": result.get("page_count"),
                    "token_budget": result.get("token_budget"),
                    "broken_links": result.get("broken_links"),
                    "manifest_path": str(Path(ledger.get("reader_output_dir") or args.run_dir / "render") / "manifest.json"),
                    "index_path": str(Path(ledger.get("reader_output_dir") or args.run_dir / "render") / "INDEX.md"),
                }
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "collapse-module-plan":
            from cbe.module_first import build_collapsed_module_plan

            current = LedgerStore(args.run_dir).open()
            legacy = LedgerStore(args.legacy_run).open()
            plan = build_collapsed_module_plan(
                legacy, current["inventory"],
                group_limit=int((current.get("documentation_policy") or {}).get("group_limit") or 312),
            )
            encoded = json.dumps(plan, ensure_ascii=False, separators=(",", ":")) + "\n"
            args.out.parent.mkdir(parents=True, exist_ok=True)
            if args.out.exists() and args.out.read_text(encoding="utf-8") != encoded:
                raise RunnerError(f"module plan output already exists with different content: {args.out}")
            args.out.write_text(encoded, encoding="utf-8")
            print(json.dumps({"plan_path": str(args.out), "stats": plan["stats"]}, indent=2))
            return 0
        if args.command == "build-module-plan":
            from cbe.module_inventory_plan import build_inventory_module_plan

            plan = build_inventory_module_plan(LedgerStore(args.run_dir).open())
            encoded = json.dumps(plan, ensure_ascii=False, separators=(",", ":")) + "\n"
            args.out.parent.mkdir(parents=True, exist_ok=True)
            if args.out.exists() and args.out.read_text(encoding="utf-8") != encoded:
                raise RunnerError(f"module plan output already exists with different content: {args.out}")
            args.out.write_text(encoded, encoding="utf-8")
            print(json.dumps({"plan_path": str(args.out), "stats": plan["stats"]}, indent=2))
            return 0
        if args.command == "module-packet":
            from cbe.module_author import build_module_author_packet

            plan = json.loads(args.plan.read_text(encoding="utf-8"))
            if not isinstance(plan, dict):
                raise RunnerError("module plan must be a JSON object")
            packet = build_module_author_packet(
                LedgerStore(args.run_dir).open(), plan, args.group_id,
                max_source_tokens=args.max_source_tokens,
            )
            encoded = json.dumps(packet, ensure_ascii=False, indent=2) + "\n"
            args.out.parent.mkdir(parents=True, exist_ok=True)
            if args.out.exists() and args.out.read_text(encoding="utf-8") != encoded:
                raise RunnerError(f"module packet output already exists with different content: {args.out}")
            args.out.write_text(encoded, encoding="utf-8")
            metadata = packet["metadata"]
            print(json.dumps({
                "packet_path": str(args.out),
                "group_id": metadata["group_id"],
                "member_count": metadata["member_count"],
                "fully_covered_member_count": metadata["fully_covered_member_count"],
                "omitted_source_count": len(metadata["omitted_sources"]),
                "prompt_token_count": metadata["prompt_token_count"],
            }, indent=2))
            return 0
        if args.command == "render-module-plan":
            from cbe.module_first_render import render_module_plan

            plan = json.loads(args.plan.read_text(encoding="utf-8"))
            if not isinstance(plan, dict):
                raise RunnerError("module plan must be a JSON object")
            explanations = None
            if args.explanations is not None:
                explanations = json.loads(args.explanations.read_text(encoding="utf-8"))
                if not isinstance(explanations, dict):
                    raise RunnerError("module explanations must be a JSON object")
            manifest = render_module_plan(LedgerStore(args.run_dir).open(), plan,
                args.output, explanations, run_dir=args.run_dir, plan_path=args.plan)
            print(json.dumps({
                "manifest_path": str(args.output / "manifest.json"),
                "index_path": str(args.output / "INDEX.md"),
                "page_count": manifest["page_count"],
                "token_budget": manifest["token_budget"],
                "candidate_group_count": manifest["candidate_group_count"],
                "accepted_group_explanation_count": manifest["accepted_group_explanation_count"],
                "symbol_catalogue_count": manifest["symbol_catalogue_count"],
            }, indent=2))
            return 0
        if args.command == "module-members":
            from cbe.module_first_render import page_module_members

            plan = json.loads(args.plan.read_text(encoding="utf-8"))
            if not isinstance(plan, dict):
                raise RunnerError("module plan must be a JSON object")
            print(json.dumps(page_module_members(
                LedgerStore(args.run_dir).open(), plan, args.group_id,
                offset=args.offset, limit=args.limit,
            ), ensure_ascii=False, indent=2))
            return 0
        if args.command == "refresh":
            from cbe.runner import refresh

            print(json.dumps(refresh(args.run_dir, args.repo), indent=2))
            return 0
        if args.command == "query":
            if (args.run_dir / "catalog.json").exists():
                from cbe.generate import query as generated_query

                print(json.dumps(generated_query(args.run_dir, args.id), ensure_ascii=False, indent=2))
                return 0
            from cbe.runner import query

            print(json.dumps(query(args.run_dir, args.id), indent=2))
            return 0
        if args.command == "resolve":
            ledger = LedgerStore(args.run_dir).open()
            if (ledger.get("documentation_policy") or {}).get("version") == "module-first-v2":
                from cbe.module_first_render import resolve_module_reader_target

                plan = json.loads((args.run_dir / "module_plan.json").read_text(encoding="utf-8"))
                target = resolve_module_reader_target(ledger, plan, args.id)
            else:
                from cbe.render import resolve_reader_target

                target = resolve_reader_target(ledger, args.id)
            if target is None:
                raise RunnerError(f"no weighted reader target for {args.id}")
            relative, marker, anchor = target.partition("#")
            print(json.dumps({
                "id": args.id,
                "target": target,
                "absolute_path": str(Path(ledger.get("reader_output_dir") or args.run_dir / "render") / relative) + (f"#{anchor}" if marker else ""),
            }, indent=2))
            return 0
        if args.command == "group-edges":
            from cbe.group_projection import page_group_edges

            ids = json.loads(args.input_ids_file.read_text(encoding="utf-8"))
            if not isinstance(ids, list) or any(not isinstance(value, str) for value in ids):
                raise RunnerError("input ids must be a JSON string array")
            if args.offset < 0 or not 1 <= args.limit <= 500:
                raise RunnerError("offset must be nonnegative and limit must be between 1 and 500")
            ledger = LedgerStore(args.run_dir).open()
            print(json.dumps(page_group_edges(
                ledger, input_ids=ids, section=args.section,
                offset=args.offset, limit=args.limit,
            ), indent=2))
            return 0
        if args.command == "promote":
            from cbe.promotion import promote_symbol

            print(json.dumps(promote_symbol(
                args.run_dir, args.symbol_id, tier=args.tier,
                reason=args.reason, source_line=args.source_line,
                extra_tokens=args.extra_tokens,
            ), indent=2))
            return 0
        if args.command == "import-result":
            from cbe.runner import import_result

            print(
                json.dumps(
                    import_result(
                        args.run_dir,
                        args.task_id,
                        args.result,
                        call_id=args.call_id,
                        external=args.external,
                    ),
                    indent=2,
                )
            )
            return 0
        if args.command == "release":
            from cbe.runner import release_tasks

            ids = json.loads(Path(args.task_ids_file).read_text(encoding="utf-8"))
            print(json.dumps(release_tasks(args.run_dir, [str(i) for i in ids], cancel=args.cancel), indent=2))
            return 0
        if args.command == "claim":
            from cbe.runner import claim_kind

            print(
                json.dumps(
                    claim_kind(
                        args.run_dir,
                        kind=args.kind,
                        task_id=args.task_id,
                        input_ids_file=args.input_ids_file,
                        target_ids_file=args.target_ids_file,
                        replace_group_id=args.replace_group_id,
                        include_source=args.include_source,
                        page=args.page,
                        page_size=args.page_size,
                        count=args.count,
                    ),
                    indent=2,
                )
            )
            return 0
    except (RunnerError, StoreError, FileNotFoundError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    parser.error(f"unhandled command {args.command}")
    return 2
