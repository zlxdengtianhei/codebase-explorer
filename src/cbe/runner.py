"""Production runner. The only place that invokes the model CLI."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from cbe.errors import RunnerError

from cbe.accounting import (
    COUNTED_KNOWN,
    DELIVERY_PACKET,
    _release_matching_reservation,
    finalize_not_sent_presentation,
    promote_initial_for_state,
    sync_budget,
    usage_from_result,
)
from cbe.graph import build_graph, callers_of, page_list
from cbe.group_projection import (
    PROJECTION_VERSION as GROUP_PROJECTION_VERSION,
    leaf_member_ids,
    page_group_edges,
    project_group_evidence,
)
from cbe.inventory import Inventory, build_inventory
from cbe.ir import sha256_bytes, sha256_text
from cbe.models import (
    AGGREGATION_REFERENCE_PATH,
    CBE_SKILL_PATH,
    CLEAN_CONTEXT_PATH,
    DETAIL_PRODUCTION_FIELD_NAMES,
    DETAIL_REFERENCE_PATH,
    PRODUCT_ROOT,
    RECOVERY_REFERENCE_PATH,
    CallRecord,
    TaskRecord,
    detail_production_contract,
    group_body_production_contract,
)
from cbe.packets import (
    DEFAULT_PACKET_WINDOW_CHARS,
    DuplicateIdentityError,
    FragmentRef,
    Packet,
    PacketIndex,
    PacketSourceError,
    load_frozen_offsets,
    pack_inventory,
    packet_source,
    retarget_fragment,
    source_for_fragment_ids,
    source_for_symbol_ids,
    span_key,
    unique_by_id,
    write_packet_file,
)
from cbe.store import (
    BudgetError,
    LedgerStore,
    LeaseError,
    StaleWriteError,
    StoreError,
    ancestor_group_ids,
    claim_task,
    content_fingerprint,
    derived_status,
    fragment_plan_residuals,
    frontier_ids,
    frontier_payload,
    group_body_input_hash,
    group_selection_input_hash,
    invalidate_group_bodies,
    is_historical_task,
    iso,
    load_unique_packets,
    mark_call,
    mark_detail_historical,
    narrative_evidence_summary,
    pid_alive,
    reserve_call,
    submit_details,
    submit_groups,
    submit_review,
    task_fragment_refs,
)

PROCESSED_DISPOSITIONS = frozenset(
    {
        "bootstrap_failed",
        "provider_failed",
        "rejected",
        "partial",
        "accepted",
        "needs_evidence",
    }
)

LLM_ARGV = ["llm", "-m", "grok", "--strict", "--skill-discovery", "off"]
DETAIL_SCHEMA_KEYS = DETAIL_PRODUCTION_FIELD_NAMES
START_RE = re.compile(
    r"llm:\s+START\s+alias=(\S+)\s+channel=(\S+)\s+task=(\S+)\s+progress=(\S+)\s+runtime=(\S+)"
)
ROUTE_RE = re.compile(r"llm:\s+ROUTE\s+(\S+)")
STATUS_RE = re.compile(r"llm:\s+STATUS\s+(.*)")
DEFAULT_GROUP_PACKET_WINDOW = 200_000
DEFAULT_FRONTIER_PAGE = 40


def durable_raw_exists(run_dir: Path, ledger: dict[str, Any], task: TaskRecord) -> bool:
    for call in (ledger.get("calls") or {}).values():
        if call.get("task_id") != task.task_id:
            continue
        path = call.get("raw_path")
        if path and Path(path).exists():
            return True
    return False


def _protocol_of(raw: dict[str, Any]) -> dict[str, Any]:
    protocol = raw.get("protocol")
    return protocol if isinstance(protocol, dict) else {}


def _stderr_of(raw: dict[str, Any]) -> str:
    pieces = [str(raw.get("stderr") or "")]
    protocol = _protocol_of(raw)
    for key in ("stderr", "cli_stderr"):
        value = protocol.get(key)
        if value:
            pieces.append(str(value))
    return "\n".join(pieces)


def _has_predispatch_bootstrap_exception(stderr: str) -> bool:
    text = stderr or ""
    if "ModuleNotFoundError" in text or "ImportError" in text:
        return True
    if "No module named" in text and "Traceback (most recent call last)" in text:
        return True
    return False


def is_not_sent_bootstrap(raw: dict[str, Any]) -> bool:
    """Predispatch CLI bootstrap that died before send. Missing route/native is not enough."""
    protocol = _protocol_of(raw)
    start = protocol.get("start") if isinstance(protocol.get("start"), dict) else {}
    route = raw.get("route") if raw.get("route") is not None else protocol.get("route")
    native = raw.get("native_path") or protocol.get("native_path")
    returncode = raw.get("returncode")
    if returncode in (0, None):
        return False
    if start.get("task") or start.get("runtime") or start.get("line"):
        return False
    if route:
        return False
    if native:
        path = Path(str(native))
        if path.exists() and path.stat().st_size > 0 and path.name != "cli_stdout.txt":
            return False
    if not _has_predispatch_bootstrap_exception(_stderr_of(raw)):
        return False
    return True


def _load_raw_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    if not isinstance(payload, dict):
        return None
    payload.setdefault("raw_path", str(path))
    return payload


def _looks_successful_result(raw: dict[str, Any]) -> bool:
    if raw.get("returncode") not in (0, None):
        return False
    text = str(raw.get("result_text") or "").strip()
    return bool(text)


def matching_raw_payload(
    run_dir: Path,
    task: TaskRecord,
    ledger: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    """Return (raw, kind) where kind is importable | needs_evidence | none.

    Only unconsumed successful results are importable. Processed failed raws
    are not replayed. needs_evidence is returned so route can be attached
    without reproducing content.
    """
    importable: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    for call in (ledger.get("calls") or {}).values():
        if call.get("task_id") != task.task_id:
            continue
        if call.get("input_hash") != task.input_hash:
            continue
        path = call.get("raw_path")
        if not path:
            continue
        payload = _load_raw_file(Path(path))
        if payload is None:
            continue
        payload.setdefault("call_id", call.get("call_id"))
        disposition = (call.get("extra") or {}).get("disposition")
        if disposition == "needs_evidence":
            evidence.append(payload)
            continue
        if disposition in PROCESSED_DISPOSITIONS:
            continue
        if call.get("state") in {"durable"} and _looks_successful_result(payload):
            importable.append(payload)
    if importable:
        return importable[-1], "importable"
    if evidence:
        return evidence[-1], "needs_evidence"
    return None, "none"


def next_attempt_index(ledger: dict[str, Any], task_id: str) -> int:
    count = 0
    for call in (ledger.get("calls") or {}).values():
        if call.get("task_id") == task_id:
            count += 1
    return count + 1




def failpoint(name: str) -> None:
    configured = os.environ.get("CBE_FAILPOINT", "").strip()
    if configured and configured == name:
        sys.stderr.write(f"CBE_FAILPOINT triggered:{name} pid={os.getpid()}\n")
        sys.stderr.flush()
        os._exit(99)


def owner_name() -> str:
    return os.environ.get("CBE_OWNER") or f"runner-{uuid.uuid4().hex[:10]}"


def packet_window() -> int:
    raw = os.environ.get("CBE_PACKET_WINDOW_CHARS", "").strip()
    if raw:
        value = int(raw)
        if value < 1:
            raise RunnerError("CBE_PACKET_WINDOW_CHARS must be >= 1")
        return value
    return DEFAULT_PACKET_WINDOW_CHARS


def group_packet_window() -> int:
    raw = os.environ.get("CBE_GROUP_PACKET_WINDOW_CHARS", "").strip()
    if raw:
        value = int(raw)
        if value < 1:
            raise RunnerError("CBE_GROUP_PACKET_WINDOW_CHARS must be >= 1")
        return value
    return DEFAULT_GROUP_PACKET_WINDOW


def analyze(
    repo: Path,
    run_dir: Path,
    *,
    documentation_profile: str = "legacy-v1",
    legacy_run: Path | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    run_dir = run_dir.resolve()
    if documentation_profile not in {"legacy-v1", "weighted-v1", "module-first-v2"}:
        raise RunnerError(f"unsupported documentation profile: {documentation_profile}")
    if legacy_run is not None and documentation_profile != "module-first-v2":
        raise RunnerError("legacy_run is only available for module-first-v2")
    inventory = build_inventory(repo)
    if documentation_profile == "module-first-v2":
        packets = PacketIndex(window_chars=packet_window())
    else:
        try:
            packets = pack_inventory(inventory, repo=repo, window_chars=packet_window())
        except PacketSourceError as exc:
            raise RunnerError(str(exc)) from exc
        except DuplicateIdentityError as exc:
            raise RunnerError(str(exc)) from exc
    graph = build_graph(inventory)
    symbol_policies: dict[str, dict[str, Any]] | None = None
    if documentation_profile in {"weighted-v1", "module-first-v2"}:
        from cbe.weighting import assign_detail_priorities

        symbol_policies = assign_detail_priorities(inventory, graph, repo)
        if set(symbol_policies) != set(inventory.symbols):
            raise RunnerError("weighted policy must assign every frozen symbol exactly once")
    try:
        unique_by_id(packets.packets, id_of=lambda packet: packet.packet_id, kind="packet")
        tasks: dict[str, TaskRecord] = {}
        if documentation_profile != "module-first-v2":
            for packet in packets.packets:
                _register_packet_tasks(tasks, packet, symbol_policies=symbol_policies)
            _register_merge_tasks(tasks, packets.packets, symbol_policies=symbol_policies)
        unique_by_id(tasks.values(), id_of=lambda task: task.task_id, kind="task")
    except DuplicateIdentityError as exc:
        raise RunnerError(str(exc)) from exc
    run_id = f"run-{uuid.uuid4().hex}"
    store = LedgerStore(run_dir)
    ledger = store.empty_ledger(
        run_id=run_id,
        inventory=inventory,
        graph=graph,
        packets=packets,
        tasks=tasks,
    )
    module_plan: dict[str, Any] | None = None
    if documentation_profile == "module-first-v2":
        from cbe.module_inventory_plan import build_inventory_module_plan
        from cbe.token_budget import count_source_tokens

        source_tokens = count_source_tokens(inventory, repo)
        ledger["native_default_review_mode"] = "none"
        group_limit = max(12, min(312, (len(inventory.files) * 3 + 3) // 4))
        ledger["documentation_policy"] = {
            "version": "module-first-v2",
            "budget_mode": "report",
            "budget_policy_version": "native-report-v1",
            "tokenizer": "o200k_base",
            "source_tokens": source_tokens,
            "published_cap_tokens": source_tokens // 2,
            "group_limit": group_limit,
            "symbols": symbol_policies,
        }
        ledger["reader_output_dir"] = str(repo / "docs" / "codebase")
        if legacy_run is None:
            module_plan = build_inventory_module_plan(ledger)
        else:
            from cbe.module_first import build_collapsed_module_plan

            legacy_ledger = LedgerStore(legacy_run).open()
            module_plan = build_collapsed_module_plan(
                legacy_ledger, ledger["inventory"], group_limit=group_limit
            )
        from cbe.module_first_render import render_module_plan
        from cbe.documentation_budget import allocate_symbol_tokens

        run_dir.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="cbe-module-preflight-", dir=run_dir.parent) as temporary:
            preflight = render_module_plan(ledger, module_plan, Path(temporary) / "reader",
                                           run_dir=run_dir)
        allocation = allocate_symbol_tokens(
            symbol_policies, source_tokens=source_tokens,
            navigation_tokens=int(preflight["token_budget"]["published_tokens"])
            + int(preflight["token_budget"]["query_only_tokens"]),
            report_infeasible=True,
        )
        ledger["documentation_policy"].update(allocation)
        ledger["documentation_policy"]["fixed_published_tokens"] = preflight["token_budget"]["published_tokens"]
        ledger["documentation_policy"]["fixed_query_only_tokens"] = preflight["token_budget"]["query_only_tokens"]
        if allocation["allocation_status"] == "necessary_overage":
            ledger["documentation_policy"]["allocation_warning"] = (
                "Final fixed layout plus starting writing recommendations exceeds the half-source target by "
                f"{allocation['necessary_overage_tokens']} tokens; recommendations were reduced, "
                "complete scope continues and actual publication is reported.")
    elif symbol_policies is not None:
        from cbe.token_budget import count_source_tokens
        from cbe.documentation_budget import allocate_symbol_tokens
        from cbe.render import estimate_weighted_navigation_tokens

        source_tokens = count_source_tokens(inventory, repo)
        group_limit = max(12, min(400, (len(inventory.files) * 3 + 3) // 4))
        ledger["documentation_policy"] = {
            "version": "weighted-v1",
            "tokenizer": "o200k_base",
            "source_tokens": source_tokens,
            "published_cap_tokens": source_tokens // 2,
            "group_limit": group_limit,
            "symbols": symbol_policies,
        }
        preflight = estimate_weighted_navigation_tokens(ledger)
        budget = allocate_symbol_tokens(
            symbol_policies,
            source_tokens=source_tokens,
            navigation_tokens=int(preflight["navigation_tokens"]),
        )
        ledger["documentation_policy"].update(budget)
        ledger["documentation_policy"]["group_body_content_tokens"] = max(
            24, budget["group_reserve_tokens"] // (3 * group_limit)
        )
        budgeted_tasks: dict[str, TaskRecord] = {}
        for packet in packets.packets:
            _register_packet_tasks(budgeted_tasks, packet, symbol_policies=symbol_policies)
        _register_merge_tasks(budgeted_tasks, packets.packets, symbol_policies=symbol_policies)
        ledger["tasks"] = {task_id: task.to_dict() for task_id, task in budgeted_tasks.items()}
    created = store.create(ledger)
    if module_plan is not None:
        from cbe.store import atomic_write_bytes
        from cbe.module_first_render import render_module_plan

        atomic_write_bytes(
            run_dir / "module_plan.json",
            (json.dumps(module_plan, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"),
        )
        initial_manifest = render_module_plan(created, module_plan,
                                              Path(created["reader_output_dir"]),
                                              run_dir=run_dir)
        def record_initial_reader(current: dict) -> dict:
            current["reader_render_diagnostics"] = {key: initial_manifest[key] for key in (
                "source_revision", "plan_sha256", "facts_sha256", "explanations_sha256", "syntax_projection_accounting")}
            return current
        created = store.mutate(record_initial_reader)
    _write_analyze_projection(run_dir, created)
    return created


def detail_task_spec(packet: Packet) -> tuple[list[str], dict[str, Any]]:
    fragments = list(packet.fragments)
    if fragments:
        input_ids = [fragment.output_id for fragment in fragments]
        extra: dict[str, Any] = {"fragments": [fragment.to_dict() for fragment in fragments]}
        split = [fragment for fragment in fragments if fragment.fragment_count > 1]
        if len(fragments) == 1 and split:
            extra.update(
                {
                    "parent_symbol_id": split[0].symbol_id,
                    "slice_index": split[0].fragment_index,
                    "slice_count": split[0].fragment_count,
                    "canonical_symbol_id": split[0].symbol_id,
                }
            )
        elif packet.parent_symbol_id:
            extra["parent_symbol_id"] = packet.parent_symbol_id
        return input_ids, extra
    return list(packet.symbol_ids) or [packet.packet_id], {}


def build_detail_task(
    packet: Packet,
    *,
    symbol_policies: dict[str, dict[str, Any]] | None = None,
) -> TaskRecord:
    input_ids, extra = detail_task_spec(packet)
    input_hash = sha256_text(packet.packet_id + ":" + ",".join(input_ids) + ":" + packet.content_hash)
    if symbol_policies is not None:
        fragments_by_output = {fragment.output_id: fragment for fragment in packet.fragments}
        output_policy = {
            output_id: dict(
                symbol_policies[
                    fragments_by_output[output_id].symbol_id
                    if output_id in fragments_by_output
                    else output_id
                ]
            )
            for output_id in input_ids
        }
        for output_id, fragment in fragments_by_output.items():
            if output_id not in output_policy or fragment.fragment_count <= 1:
                continue
            canonical_quota = int(output_policy[output_id]["suggested_output_tokens"])
            output_policy[output_id]["suggested_output_tokens"] = max(
                8, (canonical_quota + fragment.fragment_count - 1) // fragment.fragment_count
            )
            output_policy[output_id]["shared_canonical_budget"] = canonical_quota
        extra.update({"policy_version": "weighted-v1", "output_policy": output_policy})
        input_hash = sha256_text(
            input_hash + json.dumps(extra, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        )
    task_id = f"task:detail:{packet.packet_id}"
    return TaskRecord(
        task_id=task_id,
        kind="detail",
        input_ids=input_ids,
        input_hash=input_hash,
        state="pending",
        packet_id=packet.packet_id,
        extra=extra,
    )


def _register_packet_tasks(
    tasks: dict[str, TaskRecord],
    packet: Packet,
    *,
    symbol_policies: dict[str, dict[str, Any]] | None = None,
) -> None:
    task = build_detail_task(packet, symbol_policies=symbol_policies)
    if task.task_id in tasks:
        raise DuplicateIdentityError(f"duplicate task id: {task.task_id}")
    tasks[task.task_id] = task


def _register_merge_tasks(
    tasks: dict[str, TaskRecord],
    packets: list[Packet],
    *,
    symbol_policies: dict[str, dict[str, Any]] | None = None,
) -> None:
    by_symbol: dict[str, list[FragmentRef]] = {}
    packet_of: dict[str, str] = {}
    for packet in packets:
        for fragment in packet.fragments:
            if fragment.fragment_count > 1:
                by_symbol.setdefault(fragment.symbol_id, []).append(fragment)
                packet_of[fragment.fragment_id] = packet.packet_id
    for parent, fragments in by_symbol.items():
        unique_by_id(fragments, id_of=lambda item: item.fragment_id, kind="fragment")
        fragments = sorted(
            fragments,
            key=lambda item: (
                item.owned_spans[0].start if item.owned_spans else 0,
                item.fragment_index,
            ),
        )
        if fragments and len(fragments) != fragments[0].fragment_count:
            raise DuplicateIdentityError(
                f"symbol {parent} packed {len(fragments)} fragments, count {fragments[0].fragment_count}"
            )
        fragment_ids = [item.fragment_id for item in fragments]
        slice_task_ids = [f"task:detail:{packet_of[item]}" for item in fragment_ids]
        merge_id = f"task:merge:{parent}"
        extra = {
            "parent_symbol_id": parent,
            "fragment_ids": fragment_ids,
            "slice_ids": fragment_ids,
            "slice_task_ids": slice_task_ids,
            "source_reread": False,
        }
        merge_hash = sha256_text(parent + ":" + ",".join(fragment_ids))
        if symbol_policies is not None:
            extra["policy_version"] = "weighted-v1"
            extra["output_policy"] = {parent: symbol_policies[parent]}
            merge_hash = sha256_text(
                merge_hash + json.dumps(extra["output_policy"], sort_keys=True, ensure_ascii=False)
            )
        existing = tasks.get(merge_id)
        if existing is not None:
            prev = list((existing.extra or {}).get("fragment_ids") or (existing.extra or {}).get("slice_ids") or [])
            if prev == fragment_ids:
                continue
            if existing.state == "leased":
                continue
            existing.input_ids = [parent]
            existing.input_hash = merge_hash
            merged_extra = dict(existing.extra or {})
            merged_extra.update(extra)
            existing.extra = merged_extra
            if existing.state == "committed":
                existing.state = "pending"
            tasks[merge_id] = existing
            continue
        tasks[merge_id] = TaskRecord(
            task_id=merge_id,
            kind="merge",
            input_ids=[parent],
            input_hash=merge_hash,
            state="pending",
            extra=extra,
        )


def _write_analyze_projection(run_dir: Path, ledger: dict[str, Any]) -> None:
    (run_dir / "status.json").write_text(
        json.dumps(derived_status(ledger), indent=2),
        encoding="utf-8",
    )


def load_packet_map(ledger: dict[str, Any]) -> dict[str, Packet]:
    try:
        return load_unique_packets(ledger)
    except DuplicateIdentityError as exc:
        raise RunnerError(str(exc)) from exc


def symbol_prompt_meta(symbol: dict[str, Any] | None) -> dict[str, Any]:
    """Names, kinds, spans, and structural ids only. Verbatim source lives in `source` once."""

    if not symbol:
        return {}
    return {
        "id": symbol.get("id") or symbol.get("symbol_id"),
        "kind": symbol.get("kind"),
        "name": symbol.get("name"),
        "qualified_name": symbol.get("qualified_name"),
        "parent_id": symbol.get("parent_id"),
        "span": symbol.get("span"),
        "exclusive_spans": symbol.get("exclusive_spans"),
    }


def _detail_prompt_symbols(
    symbols_map: dict[str, Any],
    packet: Packet,
    fragments: list[FragmentRef],
    target_ids: list[str],
    extra: dict[str, Any],
) -> list[dict[str, Any]]:
    wanted = set(target_ids)
    if fragments:
        entries: list[dict[str, Any]] = []
        for fragment in fragments:
            if wanted and fragment.output_id not in wanted and fragment.fragment_id not in wanted:
                continue
            parent_sym = symbols_map.get(fragment.symbol_id) or {}
            owned = [span.to_dict() for span in fragment.owned_spans]
            entry = {
                **symbol_prompt_meta(parent_sym),
                "id": fragment.output_id,
                "canonical_symbol_id": fragment.symbol_id,
                "fragment_id": fragment.fragment_id,
                "fragment_index": fragment.fragment_index,
                "fragment_count": fragment.fragment_count,
                "slice_index": fragment.fragment_index,
                "slice_count": fragment.fragment_count,
                "owned_spans": owned,
                "exclusive_spans": owned,
            }
            if fragment.owned_spans:
                entry["span"] = {
                    "start": fragment.owned_spans[0].start,
                    "end": fragment.owned_spans[-1].end,
                }
            entries.append(entry)
        return entries
    if extra.get("slice_index") is not None:
        parent = extra.get("canonical_symbol_id") or extra.get("parent_symbol_id")
        parent_sym = symbols_map.get(parent) or {}
        return [
            {
                **symbol_prompt_meta(parent_sym),
                "id": target_ids[0] if target_ids else packet.packet_id,
                "canonical_symbol_id": parent,
                "slice_index": extra.get("slice_index"),
                "slice_count": extra.get("slice_count"),
                "span": packet.spans[0].to_dict() if packet.spans else parent_sym.get("span"),
            }
        ]
    return [
        symbol_prompt_meta(symbols_map.get(symbol_id))
        for symbol_id in target_ids
        if symbols_map.get(symbol_id)
    ]


def _prompt_resources(kind: str, *, weighted: bool = False) -> dict[str, str]:
    if weighted:
        # The weighted producer prompt embeds its full assignment contract.
        # Requiring the orchestration skill and reference on every packet adds
        # thousands of repeated input tokens without adding source evidence.
        return {"clean_context": CLEAN_CONTEXT_PATH} if CLEAN_CONTEXT_PATH else {}
    resources = {
        "product_root": PRODUCT_ROOT,
        "cbe_skill": CBE_SKILL_PATH,
    }
    if kind == "group_body":
        resources["aggregation_reference"] = AGGREGATION_REFERENCE_PATH
    else:
        resources["detail_reference"] = DETAIL_REFERENCE_PATH
    if CLEAN_CONTEXT_PATH:
        resources["clean_context"] = CLEAN_CONTEXT_PATH
    return resources


def build_detail_prompt(
    *,
    packet: Packet,
    source: str,
    symbols: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    envelope: dict[str, Any] | None = None,
    result_path: str | None = None,
    feedback: list[dict[str, Any]] | None = None,
) -> str:
    contract = detail_production_contract()
    weighted = any(isinstance(item.get("output_policy"), dict) for item in symbols)
    result_rule = contract["result_file"]
    if result_path:
        result_rule = (
            f"Write valid UTF-8 JSON to exactly this result file: {result_path}. "
            "Do not invent a second destination, and do not only put JSON in the final reply."
        )
    rules = [
        "The exclusive source interval is injected in this prompt once under `source`.",
        "Produce a top-level JSON object {\"details\": [...]} with exactly one record per assigned symbol_id.",
        result_rule,
        "Do not Read the packet file or the source tree to discover this schema. If the host requires loading a skill, load the exact paths in resources.",
        "Explain execution cause and effect: inputs/conditions/outputs, effects, failures/cancel/retry, evidenced dependencies, unknowns.",
        "Class records explain class contract and link methods; do not copy method bodies.",
        "Module residual covers top-level imports, registration, decorators, and side effects.",
        "Tests: fixture, asserted behavior, and what failure means.",
        "[] only when that aspect is absent; uncertainty goes in unresolved with a sentence, never as fake known dependencies.",
        "Unknown IDs must not be invented. Use the supplied symbol_id and slice id values.",
        "Do not repeat source text, signatures, or exclusive bodies in the symbols array.",
        "nav_sentence/source_spans/packet_id/input_hash/revision/provenance are filled by the program.",
        "The placeholder example is format metadata. Replace placeholders; do not copy them.",
    ]
    if weighted:
        rules.extend(
            [
                "This is weighted-v1. The output_policy attached to each symbol is binding: emit exactly the assigned IDs, satisfy its required_fields, and keep each record within suggested_output_tokens using o200k_base tokens.",
                "Count content tokens as o200k_base encode_ordinary of nonempty strings from behavior, inputs_outputs, effects, failures, dependencies, unresolved joined by newlines. This rule is complete; do not read consumer implementation files to discover it.",
                "For brief symbols, one precise behavior sentence is normally enough. Empty arrays are allowed for fields without evidence; never add a six-part essay merely to fill the schema.",
                "For an assigned structural fragment whose owned source is only whitespace, use the shortest factual behavior ('No executable behavior.') and empty arrays; do not describe separators between declarations.",
                "For standard and deep symbols, include only facts that change how a reader understands behavior, state, effects, failure, or collaborators. Deep means more evidence, not a tutorial.",
                "A short symbol can still contain a critical failure or registration effect. If the assigned tier cannot hold an evidenced boundary, return needs_promotion with the source line and missing fact for that symbol.",
                "Never merge distinct exception handlers, retry/requeue outcomes, or callback-before-state ordering into an ambiguous sentence such as 'rest reported internally'. Name the triggering context and outcome separately.",
                "If accurate behavior-changing facts do not fit the quota, return only {symbol_id, needs_promotion: {source_line, missing_fact}} for that ID. This is a deliberate repair request, not a partial accepted explanation; it also applies to deep symbols that need more quota.",
                "Do not write tutorials, images, diagrams, examples, or restate source code. Do not invent facts to fill optional fields.",
            ]
        )
    if envelope is not None:
        rules.append(
            "Echo the supplied `envelope` object verbatim into the result JSON under key `envelope`; "
            "it is the claim receipt the importer verifies."
        )
        rules.append(
            "Add a `report` object: {\"read\": [<what you actually read, e.g. this prompt's injected source only>], "
            "\"method\": \"<how you completed the task>\"}. The program mechanically checks it against this assignment."
        )
    if weighted:
        prompt_symbols = []
        for item in symbols:
            meta = symbol_prompt_meta(item)
            for key in (
                "canonical_symbol_id", "slice_index", "slice_count", "fragment_id",
                "fragment_index", "fragment_count", "owned_spans",
            ):
                if key in item:
                    meta[key] = item[key]
            if "owned_spans" in item:
                # Ownership is exact; exclusive_spans repeat it. Keep span for
                # the enclosing symbol scope (notably classes with methods).
                meta.pop("exclusive_spans", None)
            if "fragment_index" in item and "fragment_count" in item:
                meta.pop("slice_index", None)
                meta.pop("slice_count", None)
            policy = item.get("output_policy")
            if isinstance(policy, dict):
                # Grading signals and promotion history remain in the frozen task,
                # while the producer receives only its binding output assignment.
                meta["output_policy"] = {
                    key: policy[key]
                    for key in (
                        "tier", "required_fields", "suggested_output_tokens",
                        "shared_canonical_budget",
                    )
                    if key in policy
                }
            prompt_symbols.append(meta)
    else:
        prompt_symbols = [
            symbol_prompt_meta(item)
            | {
                k: item[k]
                for k in item
                if k
                in {
                    "canonical_symbol_id",
                    "slice_index",
                    "slice_count",
                    "fragment_id",
                    "fragment_index",
                    "fragment_count",
                    "owned_spans",
                    "id",
                    "output_policy",
                    "tier",
                    "required_fields",
                    "suggested_output_tokens",
                }
            }
            for item in symbols
        ]
    payload = {
        "role": "Detail producer",
        "task": "Write function/module Detail records from the exclusive source interval only.",
        "schema": contract["fields"],
        "schema_keys": list(DETAIL_SCHEMA_KEYS),
        "placeholder_example": None if weighted else contract["example"],
        "placeholder_note": contract["example_note"],
        "result_file_rule": result_rule,
        "consumer": "runner.import / import-result",
        "resources": _prompt_resources("detail", weighted=weighted),
        "rules": rules,
        "packet_id": packet.packet_id,
        "path": packet.path,
        "language": packet.language,
        "spans": [span.to_dict() for span in packet.spans],
        "symbols": prompt_symbols,
        "direct_edges": edges,
        "source": source,
    }
    if envelope is not None:
        payload["envelope"] = envelope
    if weighted:
        payload["documentation_profile"] = "weighted-v1"
    if feedback:
        payload["review_feedback"] = feedback
        payload["rules"].append(
            "review_feedback lists factual errors found by an independent source-checked review; "
            "fix exactly those records against the source."
        )
    if weighted:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_group_body_prompt(
    group: dict[str, Any],
    child_docs: list[dict[str, Any]],
    *,
    envelope: dict[str, Any] | None = None,
    result_path: str | None = None,
    weighted: bool = False,
    quota_tokens: int | None = None,
    evidence_residual: list[dict[str, Any]] | None = None,
) -> str:
    contract = group_body_production_contract()
    result_rule = contract["result_file"]
    if result_path:
        result_rule = (
            f"Write valid UTF-8 JSON to exactly this result file: {result_path}. "
            "Do not invent a second destination."
        )
    rules = [
        "Do not read source code. Use the supplied documents only.",
        "Return JSON {\"body\": \"...\"} as a nonempty string describing combined behavior with links, not concatenated child text.",
        result_rule,
        "Describe duty, combined flow, boundaries, failure paths, and relation evidence. Link child pages.",
        "Do not change membership, do not introduce source, and do not search the whole repo or old artifacts.",
        "If a required child is missing, return the concrete dependency gap instead of inventing it.",
        "Do not re-embed descendant Detail records that are not direct children.",
        "If the host requires loading a skill, load the exact paths in resources.",
    ]
    if weighted:
        rules = [
            "Use only direct-child projection and relation evidence in this prompt; do not read source or old Detail pages.",
            "Write one concise module-level explanation of combined behavior. Preserve behavior-changing effects, failures, and unknowns.",
            "Preserve each child's scope and conditions. Do not strengthen local cleanup into a global guarantee, or infer an ordering from missing evidence.",
            "Return JSON with a nonempty body only; the program carries forward direct-child effects, failures, and unknowns with their source IDs, so do not repeat them in a second evidence_summary.",
            f"Keep the body within {quota_tokens} o200k_base tokens.",
            "No tutorial, examples, diagram, image, or repeated per-function prose.",
            result_rule,
        ]
    if envelope is not None:
        rules.append(
            "Echo the supplied `envelope` object verbatim into the result JSON under key `envelope`."
        )
        rules.append(
            "Add a `report` object: {\"read\": [<what you actually read>], \"method\": \"<how you completed the task>\"}."
        )
    payload = {
        "role": "Group body writer",
        "task": "Write the group body for an already decided grouping. Do not change membership.",
        "schema": (
            {"body": "concise str"} if weighted else contract["schema"]
        ),
        "placeholder_example": None if weighted else contract["example"],
        "result_file_rule": result_rule,
        "resources": _prompt_resources("group_body", weighted=weighted),
        "group": (
            {k: group[k] for k in ("group_id", "question_answered", "grouping_reason", "entry_routes", "relations") if k in group}
            if weighted else {k: group[k] for k in group if k != "body"}
        ),
        "children_and_details": child_docs,
        "rules": rules,
    }
    if envelope is not None:
        payload["envelope"] = envelope
    if weighted:
        payload["documentation_profile"] = "weighted-v1"
        payload["quota_tokens"] = quota_tokens
        payload["evidence_residual"] = evidence_residual or []
        feedback = (group.get("extra") or {}).get("review_feedback")
        if feedback:
            payload["review_feedback"] = feedback
            payload["rules"].append(
                "An independent source review found the listed errors in the previous module body. "
                "Correct them using the supplied child facts and the source-checked review feedback; "
                "if neither supports a correction, state the limit without inventing a claim."
            )
    return json.dumps(payload, ensure_ascii=False, indent=2)


class ProviderResult:
    def __init__(
        self,
        *,
        text: str,
        argv: list[str],
        returncode: int,
        stdout: str,
        stderr: str,
        result_path: Path,
        route: dict[str, Any] | None,
        mocked: bool,
        task_name: str | None = None,
        runtime: dict[str, Any] | None = None,
        progress: dict[str, Any] | None = None,
        stream_paths: list[str] | None = None,
        native_path: Path | None = None,
        route_path: str | None = None,
        protocol: dict[str, Any] | None = None,
    ) -> None:
        self.text = text
        self.argv = argv
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.result_path = result_path
        self.route = route
        self.mocked = mocked
        self.task_name = task_name
        self.runtime = runtime or {}
        self.progress = progress or {}
        self.stream_paths = stream_paths or []
        self.native_path = native_path
        self.route_path = route_path
        self.protocol = protocol or {}


def _find_llm() -> str:
    override = os.environ.get("CBE_LLM_BIN", "").strip()
    if override:
        return override
    from shutil import which

    found = which("llm")
    if found:
        return found
    candidate = Path.home() / ".local/bin/llm"
    if candidate.exists():
        return str(candidate)
    raise RunnerError("llm CLI is not on PATH")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _copy_if_exists(source: Path, dest: Path) -> bool:
    if not source.exists() or not source.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == dest.resolve():
        return True
    shutil.copy2(source, dest)
    return True


def collect_llm_artifacts(
    *,
    stderr: str,
    stdout: str,
    call_dir: Path,
    route_root: Path | None = None,
    receipts_path: Path | None = None,
) -> dict[str, Any]:
    """Persist the direct-call stdout/stderr. No event trace auditing (2026-09-21)."""

    call_dir.mkdir(parents=True, exist_ok=True)
    (call_dir / "cli_stdout.txt").write_text(stdout or "", encoding="utf-8")
    (call_dir / "cli_stderr.log").write_text(stderr or "", encoding="utf-8")
    return {"returncode": None}

def _llm_argv(prompt_path: Path, result_path: Path) -> list[str]:
    template = os.environ.get("CBE_LLM_CMD", "").strip()
    if template:
        import shlex

        parts = shlex.split(template)
        had_prompt = any("{prompt}" in part for part in parts)
        had_result = any("{result}" in part for part in parts)
        argv = [
            part.replace("{prompt}", str(prompt_path)).replace("{result}", str(result_path))
            for part in parts
        ]
        if not had_prompt:
            argv.append(str(prompt_path))
        if not had_result:
            argv.extend(["--result-file", str(result_path)])
        return argv
    return [
        _find_llm(),
        "-m",
        os.environ.get("CBE_LLM_MODEL", "grok"),
        "--strict",
        "--skill-discovery",
        "off",
        "-f",
        str(prompt_path),
        "--result-file",
        str(result_path),
    ]


def invoke_llm(prompt_path: Path, result_path: Path, *, call_dir: Path | None = None) -> ProviderResult:
    """Thin caller of the installed llm CLI or the user's CBE_LLM_CMD. No second liveness platform."""

    call_dir = Path(call_dir or result_path.parent)
    call_dir.mkdir(parents=True, exist_ok=True)
    route_root = call_dir / "provider-routes"
    receipts_path = call_dir / "provider-receipts.jsonl"
    route_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["LLM_ROUTE_JSON_ROOT"] = str(route_root)
    env["TOOL_RECEIPTS_LEDGER"] = str(receipts_path)
    argv = _llm_argv(prompt_path, result_path)
    stdout_path = call_dir / "cli_stdout.txt"
    stderr_path = call_dir / "cli_stderr.log"
    interrupted = False
    returncode = -1
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        proc = subprocess.Popen(argv, stdout=out, stderr=err, env=env, text=True)
        (call_dir / "provider.pid").write_text(str(proc.pid), encoding="utf-8")
        try:
            returncode = proc.wait()
        except BaseException:
            interrupted = True
            # Do not kill the CLI: its own idle/hard-ceiling contract is the supervisor.
            raise
    stdout = stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else ""
    stderr = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
    artifacts = collect_llm_artifacts(
        stderr=stderr,
        stdout=stdout,
        call_dir=call_dir,
        route_root=route_root,
        receipts_path=receipts_path,
    )
    text = result_path.read_text(encoding="utf-8") if result_path.exists() else ""
    route = artifacts.get("route")
    native_path = Path(artifacts["native_path"]) if artifacts.get("native_path") else None
    protocol = dict(artifacts)
    protocol["interrupted"] = interrupted
    protocol["returncode"] = returncode
    return ProviderResult(
        text=text,
        argv=argv,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        result_path=result_path,
        route=route if isinstance(route, dict) else None,
        mocked=False,
        task_name=artifacts.get("task"),
        runtime=artifacts.get("runtime") or {},
        progress=artifacts.get("progress") or {},
        stream_paths=list(artifacts.get("stream_paths") or []),
        native_path=native_path,
        route_path=artifacts.get("route_path"),
        protocol=protocol,
    )


def invoke_mock(prompt_path: Path, result_path: Path, **_kwargs: Any) -> ProviderResult:
    prompt = json.loads(prompt_path.read_text(encoding="utf-8"))
    details = []
    if prompt.get("role") == "Canonical fragment consolidator":
        details.append({
            "symbol_id": prompt["symbol_id"], "behavior": "Mock merge.",
            "inputs_outputs": [], "effects": [], "failures": [],
            "dependencies": [], "unresolved": ["mock"],
        })
    for symbol in prompt.get("symbols") or []:
        symbol_id = symbol.get("id") or symbol.get("symbol_id")
        kind = symbol.get("kind")
        name = symbol.get("name")
        weighted = prompt.get("documentation_profile") == "weighted-v1"
        details.append(
            {
                "symbol_id": symbol_id,
                "behavior": (
                    "Mock behavior." if weighted else
                    f"mock detail for {kind} {name}: follows the exclusive source interval "
                    f"at {prompt.get('path')} without claiming production semantics."
                ),
                "inputs_outputs": [] if weighted else ["mock: arguments and results taken from the signature only"],
                "effects": [],
                "failures": [],
                "dependencies": [],
                "unresolved": ["mock"] if weighted else ["mock provider; not a real model"],
            }
        )
    if prompt.get("group") and not details:
        body = {
            "body": (
                "Mock group." if prompt.get("documentation_profile") == "weighted-v1"
                else f"mock group body for {prompt['group'].get('group_id')}: membership is already decided."
            )
        }
        if prompt.get("documentation_profile") == "weighted-v1":
            body["evidence_summary"] = {
                "behavior": "Mock group.", "effects": [], "failures": [], "unresolved": ["mock"],
            }
        result_path.write_text(json.dumps(body, indent=2), encoding="utf-8")
        return ProviderResult(
            text=result_path.read_text(encoding="utf-8"),
            argv=["mock-provider"],
            returncode=0,
            stdout="",
            stderr="mock provider",
            result_path=result_path,
            route={"provider": "mock", "model": "mock", "model_id_observed": "mock", "model_evidence_source": "mock"},
            mocked=True,
        )
    payload = {"details": details}
    result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return ProviderResult(
        text=result_path.read_text(encoding="utf-8"),
        argv=["mock-provider"],
        returncode=0,
        stdout="",
        stderr="mock provider",
        result_path=result_path,
        route={"provider": "mock", "model": "mock", "model_id_observed": "mock", "model_evidence_source": "mock"},
        mocked=True,
    )


def parse_json_result(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise RunnerError("provider result is empty")
    try:
        value = json.loads(stripped)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        try:
            value = json.loads(stripped[start:end + 1])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError as exc:
            raise RunnerError(f"provider result is not JSON: {exc}") from exc
    raise RunnerError("provider result is not a JSON object")


def _provider_for(model: str):
    if model == "mock" or os.environ.get("CBE_PROVIDER") == "mock":
        return invoke_mock
    if os.environ.get("CBE_LLM_CMD"):
        # User-configured command template (2026-09-21 ruling: no fixed model).
        # The template may contain {prompt} and {result} placeholders; without
        # placeholders the prompt path is appended as the final argument and the
        # result is expected on stdout. `model` is informational only here.
        return invoke_llm
    if model != "grok":
        raise RunnerError(
            f"unsupported model {model}; production path is grok, mock, or CBE_LLM_CMD"
        )
    return invoke_llm


_PACKET_HASH_PREFIXES = ("review-", "group-")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_PACKET_IDENTITY_FLAGS = (
    "packet_path_identity_mismatch",
    "packet_content_digest_mismatch",
    "packet_bound_hash_unproven",
)


def work(
    run_dir: Path,
    *,
    model: str = "grok",
    jobs: int = 1,
    limit: int | None = None,
) -> dict[str, Any]:
    store = LedgerStore(run_dir)
    reconcile_unprocessed_calls(store, run_dir)
    recover_orphaned_leases(store, run_dir, owner=owner_name(), owner_pid=os.getpid())
    ledger = store.open()
    results: list[dict[str, Any]] = []
    remaining = limit
    workers = max(1, jobs)
    owner = owner_name()
    attempted: set[tuple[str, str]] = set()

    def take() -> TaskRecord | None:
        nonlocal remaining
        box: dict[str, TaskRecord | None] = {"task": None}

        def mutate(current: dict[str, Any]) -> dict[str, Any] | None:
            nonlocal remaining
            if remaining is not None and remaining <= 0:
                return None
            task = _next_runnable(current, skip=attempted)
            if task is None:
                return None
            key = (task.task_id, task.input_hash)
            attempted.add(key)
            claimed = claim_task(
                current,
                task_id=task.task_id,
                owner=owner,
                owner_pid=os.getpid(),
                lease_seconds=int(os.environ.get("CBE_LEASE_SECONDS") or 3600),
                raw_exists=durable_raw_exists(run_dir, current, task),
            )
            box["task"] = claimed
            if remaining is not None:
                remaining -= 1
            return current

        store.mutate(mutate)
        return box["task"]

    if workers == 1:
        while True:
            task = take()
            if task is None:
                break
            results.append(_run_one(store, run_dir, task, model=model, claimed=True))
    else:
        from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

        with ThreadPoolExecutor(max_workers=workers) as pool:
            active = set()

            def refill() -> None:
                while len(active) < workers:
                    task = take()
                    if task is None:
                        break
                    active.add(pool.submit(_run_one, store, run_dir, task, model=model, claimed=True))

            refill()
            while active:
                completed, active = wait(active, return_when=FIRST_COMPLETED)
                for future in completed:
                    results.append(future.result())
                refill()
    ledger = store.open()
    status = derived_status(ledger)
    return {
        "ran": results,
        "status": status,
        "design_packet_hint": _design_hint(run_dir, ledger),
    }


def _next_runnable(
    ledger: dict[str, Any], skip: set[tuple[str, str]] | None = None,
    *, kind: str | None = None,
) -> TaskRecord | None:
    tasks = [TaskRecord.from_dict(item) for item in (ledger.get("tasks") or {}).values()]
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    skipped = skip or set()
    runnable: list[TaskRecord] = []
    for task in tasks:
        if kind is not None and task.kind != kind:
            continue
        if is_historical_task(task):
            continue
        if (task.task_id, task.input_hash) in skipped:
            continue
        if task.state not in {"pending", "needs_repair"}:
            continue
        if task.kind == "detail":
            runnable.append(task)
        elif task.kind == "merge":
            slice_ids = list(
                (task.extra or {}).get("fragment_ids") or (task.extra or {}).get("slice_ids") or []
            )
            if slice_ids and all(item in details for item in slice_ids):
                runnable.append(task)
        elif task.kind == "group_body":
            group_id = (task.extra or {}).get("group_id") or (task.input_ids[0] if task.input_ids else None)
            group = groups.get(group_id or "")
            if group:
                _docs, missing = _group_documents(ledger, group)
                if not missing:
                    runnable.append(task)
    runnable.sort(key=lambda item: item.task_id)
    return runnable[0] if runnable else None


def _prepare_call(
    store: LedgerStore,
    run_dir: Path,
    task: TaskRecord,
    *,
    model: str,
    claimed: bool = False,
    external: bool = False,
    owner_override: str | None = None,
) -> dict[str, Any]:
    """Shared prepare phase: claim, prompt build, budget reserve, prompt/packet persist, mark sent.

    Returns {"status": "done"|"error", "result": ...} for early exits, or
    {"status": "ready", ...context} for the caller to continue with a provider.
    `external=True` marks the call as produced by a session-dispatched sub-agent:
    the prompt embeds the claim envelope and the explicit result path, and no
    local provider is invoked by this process.
    """
    owner = owner_override or task.owner or owner_name()
    pid = os.getpid()
    packet_map = load_packet_map(store.open())
    if not claimed:
        def claim(ledger: dict[str, Any]) -> dict[str, Any]:
            claim_task(
                ledger,
                task_id=task.task_id,
                owner=owner,
                owner_pid=pid,
                lease_seconds=int(os.environ.get("CBE_LEASE_SECONDS") or 3600),
                raw_exists=durable_raw_exists(run_dir, ledger, task),
            )
            return ledger

        try:
            ledger = store.mutate(claim)
        except LeaseError as exc:
            return {"status": "error", "result": {"task_id": task.task_id, "error": str(exc)}}
        task = TaskRecord.from_dict(ledger["tasks"][task.task_id])
    else:
        ledger = store.open()
        task = TaskRecord.from_dict(ledger["tasks"][task.task_id])
    raw_existing, match_kind = matching_raw_payload(run_dir, task, ledger)
    if match_kind == "importable" and raw_existing is not None:
        return {"status": "done", "result": _import_raw(store, run_dir, task, raw_existing, replay=True)}
    if match_kind == "needs_evidence" and raw_existing is not None:
        return {"status": "done", "result": _import_raw(store, run_dir, task, raw_existing, replay=True)}

    if task.kind == "merge" and not any(
        item.get("code") == "merge_requires_consolidation" for item in task.residual
    ):
        return {"status": "done", "result": _run_merge(store, ledger, task)}

    packet = packet_map.get(task.packet_id or "")
    repo = Path(ledger["repo_root"])
    source = ""
    source_spans: list[dict[str, Any]] = []
    call_id = f"call-{uuid.uuid4().hex}"
    result_dir = run_dir / "provider" / call_id
    result_path = result_dir / "result.txt"
    envelope: dict[str, Any] | None = None
    if external:
        envelope = {
            "task_id": task.task_id,
            "generation": task.generation,
            "owner": owner,
            "input_hash": task.input_hash,
            "call_id": call_id,
        }
    call_extra: dict[str, Any] = {
        "model": model,
        "attempt": next_attempt_index(ledger, task.task_id),
        "delivery": "inline_initial",
        "original_input_ids": list(task.input_ids),
        "original_input_hash": task.input_hash,
    }
    if external:
        call_extra["external_subagent"] = True
    explicit_result = str(result_path) if external else None
    if task.kind == "detail":
        if packet is None:
            return {"status": "error", "result": _fail_task(store, task, owner, "missing_packet")}
        files = (ledger.get("inventory") or {}).get("files") or {}
        symbols_map = (ledger.get("inventory") or {}).get("symbols") or {}
        extra = task.extra or {}
        remaining = [item for item in (extra.get("repair_ids") or []) if item]
        fragments = list(packet.fragments) or task_fragment_refs(task, packet)
        if remaining and fragments:
            owned_keys: set[str] = set()
            for fragment in fragments:
                owned_keys.add(fragment.output_id)
                owned_keys.add(fragment.fragment_id)
                owned_keys.add(fragment.identity_hash)
                if fragment.writes_canonical:
                    owned_keys.add(fragment.symbol_id)
            foreign = [item for item in remaining if item not in owned_keys]
            if foreign:
                # Repair ids belonging to OTHER packets of a multi-packet symbol
                # are handled by those packets' own tasks (2026-09-21 fix).
                call_extra["skipped_foreign_repair_ids"] = foreign
                remaining = [item for item in remaining if item in owned_keys]
        try:
            offsets = load_frozen_offsets(repo, packet.path, files.get(packet.path) or {})
            if remaining:
                if fragments:
                    source, source_spans, basis = source_for_fragment_ids(offsets, packet, remaining)
                else:
                    source, source_spans, basis = source_for_symbol_ids(
                        offsets, symbols_map, remaining, packet
                    )
                call_extra["repair_ids"] = remaining
                call_extra["source_subset_basis"] = basis
            else:
                source = packet_source(offsets, packet)
                source_spans = [{"path": packet.path, **span.to_dict()} for span in packet.spans]
        except PacketSourceError as exc:
            return {"status": "error", "result": _fail_task(store, task, owner, f"source_conflict:{exc}")}
        target_ids = remaining or list(task.input_ids)
        symbols = _detail_prompt_symbols(symbols_map, packet, fragments, target_ids, extra)
        if extra.get("policy_version") == "weighted-v1":
            output_policy = extra.get("output_policy") or {}
            for item in symbols:
                symbol_id = item.get("id")
                policy = output_policy.get(symbol_id)
                if not isinstance(policy, dict):
                    return {
                        "status": "error",
                        "result": _fail_task(store, task, owner, f"missing_output_policy:{symbol_id}"),
                    }
                item["output_policy"] = policy
                item["tier"] = policy.get("tier")
                item["required_fields"] = policy.get("required_fields")
                item["suggested_output_tokens"] = policy.get("suggested_output_tokens")
        edge_ids = set(target_ids) | set(packet.symbol_ids)
        edges = [
            edge
            for edge in (ledger.get("graph") or {}).get("edges") or []
            if edge.get("subject_id") in edge_ids or edge.get("target_id") in edge_ids
        ]
        prompt_text = build_detail_prompt(
            packet=packet, source=source, symbols=symbols, edges=edges,
            envelope=envelope, result_path=explicit_result,
            feedback=[r for r in (task.residual or []) if r.get("code") == "review_revision"] or None,
        )
        source_chars = len(source)
    elif task.kind == "merge":
        parent = (task.extra or {}).get("parent_symbol_id") or (task.input_ids[0] if task.input_ids else None)
        fragment_ids = list((task.extra or {}).get("fragment_ids") or [])
        fragment_docs = [
            (ledger.get("details") or {}).get(fragment_id)
            for fragment_id in fragment_ids
        ]
        if not parent or not fragment_ids or any(doc is None for doc in fragment_docs):
            return {"status": "error", "result": _fail_task(store, task, owner, "merge_missing_fragments")}
        policy = ((task.extra or {}).get("output_policy") or {}).get(parent) or {}
        prompt_payload = {
            "role": "Canonical fragment consolidator",
            "task": "Compress the already documented disjoint source fragments into one accurate canonical Detail. Preserve every behavior-changing effect, failure, and unknown; do not add facts or tutorials.",
            "documentation_profile": "weighted-v1",
            "symbol_id": parent,
            "output_policy": policy,
            "fragments": fragment_docs,
            "result_file_rule": explicit_result,
            "schema": {"details": [{
                "symbol_id": parent, "behavior": "str",
                "inputs_outputs": "list[str]", "effects": "list[str]",
                "failures": "list[str]", "dependencies": "list[str]",
                "unresolved": "list[str]",
            }]},
        }
        if envelope is not None:
            prompt_payload["envelope"] = envelope
            prompt_payload["report"] = {"read": ["this prompt's fragment evidence"], "method": "consolidation"}
        prompt_text = json.dumps(prompt_payload, ensure_ascii=False, separators=(",", ":"))
        from cbe.token_budget import count_text_tokens
        if count_text_tokens(prompt_text) > 6_000:
            return {"status": "error", "result": _fail_task(store, task, owner, "merge_evidence_over_6000_tokens")}
        source_chars = 0
        packet = None
    elif task.kind == "group_body":
        group_id = (task.extra or {}).get("group_id") or (task.input_ids[0] if task.input_ids else None)
        group = (ledger.get("groups") or {}).get(group_id or "")
        if not group:
            return {"status": "error", "result": _fail_task(store, task, owner, "missing_group")}
        child_docs, missing = _group_documents(ledger, group)
        if missing:
            return {"status": "error", "result": _fail_task(store, task, owner, "unfinished_direct_children:" + json.dumps(missing))}
        expected_hash = group_body_input_hash(ledger, group)
        if task.input_hash and task.input_hash != expected_hash:
            # Children changed since the task was queued: re-key the obligation to
            # the current content version instead of failing forever (design: a
            # changed child re-queues the body task, never skips it permanently).
            def rekey(current: dict[str, Any]) -> dict[str, Any]:
                record = TaskRecord.from_dict(current["tasks"][task.task_id])
                record.input_hash = expected_hash
                record.generation += 1
                record.state = "leased"
                record.residual = []
                current["tasks"][task.task_id] = record.to_dict()
                return current

            store.mutate(rekey)
            ledger = store.open()
            task = TaskRecord.from_dict(ledger["tasks"][task.task_id])
            if external:
                envelope = {
                    "task_id": task.task_id,
                    "generation": task.generation,
                    "owner": owner,
                    "input_hash": task.input_hash,
                    "call_id": call_id,
                }
        weighted_group = (ledger.get("documentation_policy") or {}).get("version") == "weighted-v1"
        evidence_residual: list[dict[str, Any]] = []
        if weighted_group:
            from cbe.token_budget import count_text_tokens

            projection = project_group_evidence(
                child_docs,
                edges={"relations": list(group.get("relations") or [])},
                max_chars=12_000,
                max_tokens=3_000,
                count_tokens=count_text_tokens,
            )
            if projection.payload is None:
                return {
                    "status": "error",
                    "result": _fail_task(
                        store, task, owner,
                        "group_body_evidence_gap:" + json.dumps(projection.residual, ensure_ascii=False),
                    ),
                }
            child_docs = list(projection.payload["children"])
            evidence_residual = list(projection.residual)
        prompt_text = build_group_body_prompt(
            group, child_docs, envelope=envelope, result_path=explicit_result,
            weighted=weighted_group,
            quota_tokens=(ledger.get("documentation_policy") or {}).get("group_body_content_tokens"),
            evidence_residual=evidence_residual,
        )
        if weighted_group and count_text_tokens(prompt_text) > 4_000:
            return {
                "status": "error",
                "result": _fail_task(store, task, owner, "group_body_prompt_over_4000_tokens"),
            }
        source_chars = 0
        packet = None
    else:
        return {"status": "error", "result": _fail_task(store, task, owner, f"unsupported_kind:{task.kind}")}

    call = CallRecord(
        call_id=call_id,
        task_id=task.task_id,
        input_hash=task.input_hash,
        source_spans=source_spans,
        source_chars=source_chars,
        state="prepared",
        prompt_chars=len(prompt_text),
        extra=call_extra,
    )

    def prepare(ledger_now: dict[str, Any]) -> dict[str, Any]:
        reserve_call(ledger_now, call)
        return ledger_now

    try:
        ledger = store.mutate(prepare)
    except BudgetError as exc:
        return {"status": "error", "result": {"task_id": task.task_id, "error": str(exc), "budget": True}}

    prompt_dir = run_dir / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"{call_id}.json"
    prompt_path.write_text(prompt_text, encoding="utf-8")
    packet_hash = None
    packet_path: Path | None = None
    if packet is not None:
        packet_path = write_packet_file(run_dir, packet, source, extra={"prompt_call_id": call_id})
        packet_hash = packet_path.stem

    def mark_sent(current: dict[str, Any]) -> dict[str, Any]:
        if external:
            # Mechanical counting (2026-09-21 ruling): handing the prompt to the
            # session IS the presentation; no trace audit will ever settle it.
            mark_call(
                current,
                call_id,
                state="sent",
                packet_hash=packet_hash,
                extra={"send_evidence": "presented", "send_basis": "external_prompt_handed_to_session"},
            )
        else:
            mark_call(current, call_id, state="sent", packet_hash=packet_hash)
        return current

    store.mutate(mark_sent)
    return {
        "status": "ready",
        "task": task,
        "owner": owner,
        "call_id": call_id,
        "envelope": envelope,
        "prompt_text": prompt_text,
        "prompt_path": prompt_path,
        "result_dir": result_dir,
        "result_path": result_path,
        "packet": packet,
        "packet_path": packet_path,
        "source_chars": source_chars,
        "source_spans": source_spans,
    }


def _run_one(
    store: LedgerStore,
    run_dir: Path,
    task: TaskRecord,
    *,
    model: str,
    claimed: bool = False,
) -> dict[str, Any]:
    prep = _prepare_call(store, run_dir, task, model=model, claimed=claimed)
    if prep["status"] != "ready":
        return prep["result"]
    task = prep["task"]
    owner = prep["owner"]
    call_id = prep["call_id"]
    prompt_path = prep["prompt_path"]
    result_dir = prep["result_dir"]
    result_path = prep["result_path"]
    packet = prep["packet"]
    packet_path = prep["packet_path"]
    source_chars = prep["source_chars"]
    provider = _provider_for(model)
    try:
        result = provider(prompt_path, result_path, call_dir=result_dir)
    except Exception as exc:
        def mark_uncertain(current: dict[str, Any]) -> dict[str, Any]:
            mark_call(
                current,
                call_id,
                state="uncertain",
                residual=[{"code": "provider_exception", "message": str(exc)}],
            )
            return current

        store.mutate(mark_uncertain)
        return {"task_id": task.task_id, "error": str(exc), "call_id": call_id, "state": "uncertain"}

    protocol = result.protocol or {}
    usage = usage_from_result(protocol.get("result") if isinstance(protocol.get("result"), dict) else None)

    raw_payload = {
        "call_id": call_id,
        "task_id": task.task_id,
        "input_hash": task.input_hash,
        "generation": task.generation,
        "owner": owner,
        "argv": result.argv,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "result_text": result.text,
        "route": result.route,
        "mocked": result.mocked,
        "packet_id": packet.packet_id if packet else None,
        "source_chars": source_chars,
        "prompt_path": str(prompt_path),
        "packet_path": str(packet_path) if packet_path else None,
        "result_path": str(result_path),
        "protocol": result.protocol,
        "task_name": result.task_name,
    }
    raw_path = run_dir / "raw" / f"{sha256_text(task.input_hash + ':' + call_id)}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def mark_durable(current: dict[str, Any]) -> dict[str, Any]:
        bootstrap = is_not_sent_bootstrap(raw_payload)
        # Mechanical counting (2026-09-21 ruling): the command ran and returned,
        # so the prompt was presented. A proven predispatch bootstrap failure is
        # the only not-sent case.
        if bootstrap:
            send_evidence = "not_sent_bootstrap"
        else:
            send_evidence = "presented"
        extra_fields = {
            "mocked": result.mocked,
            "argv": result.argv,
            "returncode": result.returncode,
            "task_name": result.task_name,
            "send_evidence": send_evidence,
            "delivery": "inline_initial",
        }
        mark_call(
            current,
            call_id,
            state="durable",
            raw_path=str(raw_path),
            result_path=str(result_path),
            route=result.route,
            actual_model=None,
            output_chars=len(result.text),
            usage=usage,
            extra=extra_fields,
        )
        if bootstrap:
            rec = (current.get("calls") or {}).get(call_id)
            if rec:
                finalize_not_sent_presentation(rec)
                current["calls"][call_id] = rec
                sync_budget(current)
        return current

    store.mutate(mark_durable)
    failpoint("after_raw")
    return _import_raw(store, run_dir, task, raw_payload, replay=False, call_id=call_id)


def _matching_raw(run_dir: Path, task: TaskRecord, ledger: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if ledger is None:
        return None
    payload, kind = matching_raw_payload(run_dir, task, ledger)
    if kind == "importable":
        return payload
    return None


def _weighted_group_body_errors(
    ledger: dict[str, Any], payload: dict[str, Any], *, group_id: str | None = None,
) -> list[dict[str, Any]]:
    policy = ledger.get("documentation_policy") or {}
    if policy.get("version") != "weighted-v1":
        return []
    body = payload.get("body")
    if not isinstance(body, str) or not body.strip():
        return [{"code": "missing_group_body"}]
    if group_id is not None:
        group = (ledger.get("groups") or {}).get(group_id)
        if not isinstance(group, dict) or narrative_evidence_summary(ledger, group, body) is None:
            return [{"code": "group_child_evidence_gap", "group_id": group_id}]
    from cbe.token_budget import count_text_tokens

    used = count_text_tokens(body)
    allotted = int(policy.get("group_body_content_tokens") or 0)
    if allotted <= 0 or used > allotted:
        return [{
            "code": "group_body_over_budget",
            "used_tokens": used, "allotted_tokens": allotted,
        }]
    return []


def _import_raw(
    store: LedgerStore,
    run_dir: Path,
    task: TaskRecord,
    raw: dict[str, Any],
    *,
    replay: bool,
    call_id: str | None = None,
) -> dict[str, Any]:
    text = raw.get("result_text") or ""
    call_id = call_id or raw.get("call_id")
    owner = raw.get("owner") or owner_name()

    def mutate(ledger: dict[str, Any]) -> dict[str, Any] | None:
        calls = ledger.get("calls") or {}
        call_record = calls.get(str(call_id)) if call_id else None
        existing_disp = (call_record.get("extra") or {}).get("disposition") if isinstance(call_record, dict) else None
        if existing_disp in PROCESSED_DISPOSITIONS:
            return None
        current_task = TaskRecord.from_dict(ledger["tasks"][task.task_id])
        packet_map = load_packet_map(ledger)
        packet = packet_map.get(current_task.packet_id or "")

        def set_call_disposition(code: str, **fields: Any) -> None:
            if not call_id or call_id not in (ledger.get("calls") or {}):
                return
            extra = {"disposition": code, "processed": True}
            extra.update(fields)
            mark_call(ledger, str(call_id), extra=extra)

        if is_not_sent_bootstrap(raw):
            current_task.state = "needs_repair"
            current_task.residual = [
                {
                    "code": "empty_or_failed_provider",
                    "disposition": "bootstrap_failed",
                    "returncode": raw.get("returncode"),
                    "replay": replay,
                }
            ]
            ledger["tasks"][task.task_id] = current_task.to_dict()
            if existing_disp == "bootstrap_failed" and current_task.state == "needs_repair":
                return None
            set_call_disposition("bootstrap_failed", send_evidence="not_sent_bootstrap")
            return ledger
        if not text.strip() or raw.get("returncode") not in (0, None):
            current_task.state = "needs_repair"
            current_task.residual = [
                {
                    "code": "empty_or_failed_provider",
                    "returncode": raw.get("returncode"),
                    "replay": replay,
                }
            ]
            ledger["tasks"][task.task_id] = current_task.to_dict()
            if existing_disp == "provider_failed":
                return None
            set_call_disposition("provider_failed")
            return ledger
        try:
            parsed = parse_json_result(text)
        except RunnerError as exc:
            current_task.state = "needs_repair"
            current_task.residual = [{"code": "unparseable_result", "message": str(exc), "replay": replay}]
            ledger["tasks"][task.task_id] = current_task.to_dict()
            if existing_disp == "rejected":
                return None
            set_call_disposition("rejected")
            return ledger
        if current_task.kind in {"detail", "merge"}:
            items = parsed.get("details")
            if not isinstance(items, list):
                current_task.state = "needs_repair"
                current_task.residual = [{"code": "missing_details_array", "replay": replay}]
                ledger["tasks"][task.task_id] = current_task.to_dict()
                set_call_disposition("rejected")
                return ledger
            submit_details(
                ledger,
                task_id=current_task.task_id,
                owner=current_task.owner or owner,
                generation=current_task.generation,
                items=items,
                packet=packet,
                call_id=call_id if not replay else None,
            )
            now_task = TaskRecord.from_dict(ledger["tasks"][task.task_id])
            disp = "partial" if now_task.state == "needs_repair" else "accepted"
            if replay and call_id and call_id in (ledger.get("calls") or {}):
                mark_call(ledger, call_id, state="imported", extra={"replay": True, "disposition": disp, "processed": True})
            else:
                set_call_disposition(disp)
        elif current_task.kind == "group_body":
            body = parsed.get("body")
            group_id = (current_task.extra or {}).get("group_id")
            groups = ledger.setdefault("groups", {})
            weighted_errors = _weighted_group_body_errors(ledger, parsed, group_id=group_id)
            if not isinstance(body, str) or not body.strip() or group_id not in groups or weighted_errors:
                current_task.state = "needs_repair"
                current_task.residual = weighted_errors or [{"code": "missing_group_body"}]
                set_call_disposition("rejected")
            else:
                groups[group_id]["body"] = body.strip()
                extra = dict(groups[group_id].get("extra") or {})
                if (ledger.get("documentation_policy") or {}).get("version") == "weighted-v1":
                    extra["evidence_summary"] = narrative_evidence_summary(ledger, groups[group_id], body)
                extra.pop("stale", None)
                extra.pop("body_stale", None)
                groups[group_id]["extra"] = extra
                current_task.state = "committed"
                current_task.output_refs = [group_id]
                current_task.residual = []
                invalidate_group_bodies(ledger, ancestor_group_ids(ledger, group_id))
                set_call_disposition("accepted")
            ledger["tasks"][task.task_id] = current_task.to_dict()
        return ledger

    ledger = store.mutate(mutate)
    task_now = TaskRecord.from_dict(ledger["tasks"][task.task_id])
    return {
        "task_id": task.task_id,
        "state": task_now.state,
        "residual": task_now.residual,
        "replay": replay,
        "call_id": call_id,
        "mocked": raw.get("mocked"),
    }


def _run_merge(store: LedgerStore, ledger: dict[str, Any], task: TaskRecord) -> dict[str, Any]:
    parent = (task.extra or {}).get("parent_symbol_id") or (task.input_ids[0] if task.input_ids else None)
    slice_ids = list((task.extra or {}).get("fragment_ids") or (task.extra or {}).get("slice_ids") or [])
    details = ledger.get("details") or {}
    slices = [details[item] for item in slice_ids if item in details]
    if parent is None or len(slices) != len(slice_ids) or not slice_ids:
        def mark(current: dict[str, Any]) -> dict[str, Any]:
            record = TaskRecord.from_dict(current["tasks"][task.task_id])
            record.state = "needs_repair"
            record.residual = [{"code": "merge_missing_slices", "parent": parent, "slice_ids": slice_ids}]
            current["tasks"][task.task_id] = record.to_dict()
            return current

        store.mutate(mark)
        return {"task_id": task.task_id, "state": "needs_repair"}

    ordered = sorted(
        slices,
        key=lambda item: (
            int(((item.get("source_spans") or [{}])[0] or {}).get("start") or 0),
            str(item.get("symbol_id") or ""),
        ),
    )
    behavior = "\n\n".join(str(item.get("behavior") or "") for item in ordered if item.get("behavior"))

    def merged_values(field: str) -> list[Any]:
        """Keep every fragment fact, removing only byte-identical duplicates."""
        values: list[Any] = []
        seen: set[str] = set()
        for item in ordered:
            raw = item.get(field)
            for value in raw if isinstance(raw, list) else ([raw] if raw is not None else []):
                key = json.dumps(value, sort_keys=True, ensure_ascii=False)
                if key not in seen:
                    seen.add(key)
                    values.append(value)
        return values

    source_spans = [span for item in ordered for span in (item.get("source_spans") or [])]

    def commit(current: dict[str, Any]) -> dict[str, Any]:
        submit_details(
            current,
            task_id=task.task_id,
            owner=task.owner or owner_name(),
            generation=task.generation,
            items=[
                {
                    "symbol_id": parent,
                    "behavior": behavior or "Merged from non-overlapping fragment Details.",
                    "inputs_outputs": merged_values("inputs_outputs"),
                    "effects": merged_values("effects"),
                    "failures": merged_values("failures"),
                    "dependencies": list(dict.fromkeys(slice_ids)) + [
                        value for value in merged_values("dependencies") if value not in slice_ids
                    ],
                    "unresolved": merged_values("unresolved"),
                    "source_spans": source_spans,
                    "provenance": {
                        "merged_from_fragments": slice_ids,
                        "merged_from_slices": slice_ids,
                        "source_reread": False,
                        "role": "canonical",
                        "complete": True,
                    },
                }
            ],
            packet=None,
            call_id=None,
        )
        return current

    merged_ledger = store.mutate(commit)
    merged_task = TaskRecord.from_dict(merged_ledger["tasks"][task.task_id])
    if (
        merged_task.state == "needs_repair"
        and (task.extra or {}).get("policy_version") == "weighted-v1"
    ):
        def expose_consolidation(current: dict[str, Any]) -> dict[str, Any]:
            record = TaskRecord.from_dict(current["tasks"][task.task_id])
            record.residual = [{
                "code": "merge_requires_consolidation",
                "parent_symbol_id": parent,
                "fragment_ids": slice_ids,
                "detail_errors": record.residual,
            }]
            current["tasks"][task.task_id] = record.to_dict()
            return current

        merged_ledger = store.mutate(expose_consolidation)
        merged_task = TaskRecord.from_dict(merged_ledger["tasks"][task.task_id])
    return {
        "task_id": task.task_id,
        "state": merged_task.state,
        "residual": merged_task.residual,
        "merge": True,
        "source_reread": False,
    }


def _fail_task(store: LedgerStore, task: TaskRecord, owner: str, code: str) -> dict[str, Any]:
    def mutate(ledger: dict[str, Any]) -> dict[str, Any]:
        record = TaskRecord.from_dict(ledger["tasks"][task.task_id])
        record.state = "needs_repair"
        record.residual = [{"code": code}]
        ledger["tasks"][task.task_id] = record.to_dict()
        return ledger

    store.mutate(mutate)
    return {"task_id": task.task_id, "state": "needs_repair", "error": code}


def _group_documents(ledger: dict[str, Any], group: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict]]:
    docs: list[dict[str, Any]] = []
    missing: list[dict] = []
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    for member in group.get("member_ids") or []:
        rec = details.get(member)
        if rec is None:
            missing.append({"code": "missing_direct_detail", "id": member})
            continue
        if (rec.get("provenance") or {}).get("stale"):
            missing.append({"code": "stale_direct_detail", "id": member})
            continue
        if not str(rec.get("behavior") or "").strip():
            missing.append({"code": "empty_direct_detail", "id": member})
            continue
        docs.append({"type": "detail", "id": member, "record": rec})
    for child in group.get("children") or []:
        rec = groups.get(child)
        if rec is None:
            missing.append({"code": "missing_direct_group", "id": child})
            continue
        if (rec.get("extra") or {}).get("stale") or (rec.get("extra") or {}).get("body_stale"):
            missing.append({"code": "stale_direct_group", "id": child})
            continue
        navigation = (
            (ledger.get("documentation_policy") or {}).get("version") == "weighted-v1"
            and (rec.get("extra") or {}).get("presentation") == "navigation"
        )
        if not navigation and not str(rec.get("body") or "").strip():
            missing.append({"code": "child_body_not_fresh", "id": child})
            continue
        docs.append(
            {
                "type": "group",
                "id": child,
                "record": {
                    "group_id": rec.get("group_id", child),
                    "body": rec.get("body"),
                    "version": rec.get("version"),
                    "question_answered": rec.get("question_answered"),
                    "grouping_reason": rec.get("grouping_reason"),
                    "member_ids": rec.get("member_ids"),
                    "children": rec.get("children"),
                    "entry_routes": rec.get("entry_routes"),
                    "relations": rec.get("relations"),
                    "partial": rec.get("partial"),
                    "extra": rec.get("extra"),
                },
            }
        )
    return docs, missing


def _bootstrap_raw_projection(run_dir: Path, record: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    raw_path = record.get("raw_path")
    if raw_path:
        loaded = _load_raw_file(Path(str(raw_path)))
        if isinstance(loaded, dict):
            payload.update(loaded)
    extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
    call_dir = run_dir / "provider" / str(record.get("call_id") or "")
    if not payload.get("stderr"):
        err_path = call_dir / "cli_stderr.log"
        if err_path.exists():
            payload["stderr"] = err_path.read_text(encoding="utf-8")
    protocol = payload.get("protocol") if isinstance(payload.get("protocol"), dict) else {}
    proto_file = _read_json(call_dir / "protocol.json")
    if isinstance(proto_file, dict):
        protocol = {**proto_file, **protocol}
    if extra.get("returncode") is not None:
        payload.setdefault("returncode", extra.get("returncode"))
    payload.setdefault("route", record.get("route"))
    payload.setdefault("native_path", record.get("native_path"))
    payload["protocol"] = protocol
    return payload


def _call_accounting_fingerprint(record: dict[str, Any]) -> str:
    extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
    payload = {
        "exposures": record.get("source_exposures"),
        "exposure_evidence": record.get("exposure_evidence"),
        "actual_model": record.get("actual_model"),
        "disposition": extra.get("disposition"),
        "processed": extra.get("processed"),
        "send_evidence": extra.get("send_evidence"),
        "presentation_audit": extra.get("presentation_audit"),
        "instruction_audit_format": extra.get("instruction_audit_format"),
        "route_model_evidence": extra.get("route_model_evidence"),
        "chat_presentation": extra.get("chat_presentation"),
        "chat_pairing": extra.get("chat_pairing"),
        "instruction_resource_hashes": [
            item.get("content_hash") for item in extra.get("instruction_resources") or [] if isinstance(item, dict)
        ],
    }
    return json.dumps(payload, sort_keys=True, default=str)


def reconcile_unprocessed_calls(store: LedgerStore, run_dir: Path) -> list[dict[str, Any]]:
    done: list[dict[str, Any]] = []

    def mutate(ledger: dict[str, Any]) -> dict[str, Any] | None:
        changed = False
        for call_id, record in list((ledger.get("calls") or {}).items()):
            extra = dict(record.get("extra") or {})
            raw = _bootstrap_raw_projection(run_dir, record)
            if is_not_sent_bootstrap(raw):
                before = _call_accounting_fingerprint(record)
                extra["disposition"] = "bootstrap_failed"
                extra["processed"] = True
                extra["send_evidence"] = "not_sent_bootstrap"
                extra["reconciled"] = extra.get("reconciled") or "historical_bootstrap_not_sent"
                extra["reconcile_basis"] = "cli_predispatch_bootstrap_exception_and_terminated"
                record["extra"] = extra
                promote_initial_for_state(record)
                finalize_not_sent_presentation(record)
                after = _call_accounting_fingerprint(record)
                if before != after:
                    ledger["calls"][call_id] = record
                    changed = True
                    done.append(
                        {
                            "call_id": call_id,
                            "action": "historical_bootstrap_not_sent",
                            "send_evidence": "not_sent_bootstrap",
                        }
                    )
                continue
        if not changed:
            return None
        sync_budget(ledger)
        return ledger

    store.mutate(mutate)
    return done


def _provider_pids(run_dir: Path, call: dict[str, Any]) -> list[int]:
    pids: list[int] = []
    extra = call.get("extra") if isinstance(call.get("extra"), dict) else {}
    for key in ("provider_pid", "llm_pid"):
        try:
            pids.append(int(extra[key]))
        except (KeyError, TypeError, ValueError):
            pass
    call_dir = run_dir / "provider" / str(call.get("call_id") or "")
    pid_file = call_dir / "provider.pid"
    if pid_file.exists():
        try:
            pids.append(int(pid_file.read_text(encoding="utf-8").strip()))
        except ValueError:
            pass
    for name in ("runtime.json", "progress.json"):
        payload = _read_json(call_dir / name) or {}
        for key in ("pid", "child_pid", "llm_pid", "popen_pid"):
            try:
                pids.append(int(payload[key]))
            except (KeyError, TypeError, ValueError):
                pass
    return [item for item in pids if item > 0]


def _harvest_raw_from_provider(run_dir: Path, task: TaskRecord, call: dict[str, Any]) -> dict[str, Any] | None:
    call_dir = run_dir / "provider" / str(call.get("call_id") or "")
    result_path = Path(str(call.get("result_path") or (call_dir / "result.txt")))
    if not result_path.exists():
        return None
    text = result_path.read_text(encoding="utf-8")
    if not text.strip():
        return None
    stderr = ""
    err_path = call_dir / "cli_stderr.log"
    if err_path.exists():
        stderr = err_path.read_text(encoding="utf-8")
    stdout = ""
    out_path = call_dir / "cli_stdout.txt"
    if out_path.exists():
        stdout = out_path.read_text(encoding="utf-8")
    protocol = _read_json(call_dir / "protocol.json") or {}
    return {
        "call_id": call.get("call_id"),
        "task_id": task.task_id,
        "input_hash": task.input_hash,
        "generation": task.generation,
        "owner": task.owner,
        "returncode": 0,
        "stdout": stdout,
        "stderr": stderr,
        "result_text": text,
        "route": call.get("route"),
        "mocked": bool((call.get("extra") or {}).get("mocked")),
        "packet_id": task.packet_id,
        "native_path": call.get("native_path"),
        "prompt_path": call.get("prompt_path"),
        "result_path": str(result_path),
        "protocol": protocol,
        "raw_path": call.get("raw_path"),
    }


def recover_orphaned_leases(
    store: LedgerStore,
    run_dir: Path,
    *,
    owner: str,
    owner_pid: int,
) -> list[dict[str, Any]]:
    recovered: list[dict[str, Any]] = []
    ledger = store.open()
    for task_raw in list((ledger.get("tasks") or {}).values()):
        task = TaskRecord.from_dict(task_raw)
        if is_historical_task(task) or task.state != "leased":
            continue
        if pid_alive(task.owner_pid):
            continue
        if task.kind not in {"detail", "group_body", "merge"}:
            continue
        related = [
            call
            for call in (ledger.get("calls") or {}).values()
            if call.get("task_id") == task.task_id
        ]
        in_flight = [call for call in related if call.get("state") in {"sent", "uncertain"}]
        active = None
        for call in in_flight:
            if any(pid_alive(pid) for pid in _provider_pids(run_dir, call)):
                active = call
                break
        if active is not None:
            recovered.append(
                {
                    "task_id": task.task_id,
                    "action": "provider_still_active",
                    "call_id": active.get("call_id"),
                }
            )
            continue
        harvested = None
        for call in related:
            extra = call.get("extra") if isinstance(call.get("extra"), dict) else {}
            if extra.get("disposition") in PROCESSED_DISPOSITIONS:
                continue
            payload = _harvest_raw_from_provider(run_dir, task, call)
            if payload:
                harvested = payload
                break
        if harvested is not None:
            imported = _import_raw(store, run_dir, task, harvested, replay=True)
            recovered.append(
                {
                    "task_id": task.task_id,
                    "action": "harvested_provider_result",
                    "call_id": harvested.get("call_id"),
                    "import": imported,
                }
            )
            ledger = store.open()
            continue

        def reclaim(current: dict[str, Any]) -> dict[str, Any]:
            claim_task(
                current,
                task_id=task.task_id,
                owner=owner,
                owner_pid=owner_pid,
                lease_seconds=int(os.environ.get("CBE_LEASE_SECONDS") or 3600),
                raw_exists=False,
            )
            rec = TaskRecord.from_dict(current["tasks"][task.task_id])
            rec.state = "needs_repair"
            rec.residual = list(rec.residual or []) + [
                {"code": "owner_dead_no_harvestable_result", "previous_owner_pid": task.owner_pid}
            ]
            current["tasks"][task.task_id] = rec.to_dict()
            for call in (current.get("calls") or {}).values():
                if call.get("task_id") != task.task_id:
                    continue
                if call.get("state") == "sent":
                    call["state"] = "uncertain"
                extra = dict(call.get("extra") or {})
                extra.setdefault("send_evidence", extra.get("send_evidence") or "unknown")
                call["extra"] = extra
            return current

        store.mutate(reclaim)
        recovered.append({"task_id": task.task_id, "action": "reclaimed_dead_lease"})
        ledger = store.open()
    return recovered


def _fragment_plan_signature(packets: list[Packet], tasks: dict[str, TaskRecord]) -> str:
    payload = {
        "packets": [
            {
                "id": packet.packet_id,
                "spans": [[span.start, span.end] for span in packet.spans],
                "fragments": [
                    [
                        fragment.fragment_id,
                        fragment.symbol_id,
                        [[span.start, span.end] for span in fragment.owned_spans],
                        fragment.fragment_count,
                    ]
                    for fragment in packet.fragments
                ],
            }
            for packet in sorted(packets, key=lambda item: item.packet_id)
        ],
        "merges": {
            task_id: list((task.extra or {}).get("fragment_ids") or (task.extra or {}).get("slice_ids") or [])
            for task_id, task in sorted(tasks.items())
            if task.kind == "merge" and not is_historical_task(task)
        },
        "pending_inputs": {
            task_id: list(task.input_ids)
            for task_id, task in sorted(tasks.items())
            if task.kind == "detail"
            and task.state in {"pending", "needs_repair"}
            and not is_historical_task(task)
        },
    }
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _live_task_ids(ledger: dict[str, Any]) -> set[str]:
    live: set[str] = set()
    for raw in (ledger.get("tasks") or {}).values():
        task = TaskRecord.from_dict(raw)
        if task.state == "leased" and pid_alive(task.owner_pid):
            live.add(task.task_id)
    for call in (ledger.get("calls") or {}).values():
        state = str(call.get("state") or "")
        if state not in {"sent", "prepared", "durable"}:
            continue
        extra = call.get("extra") or {}
        pid = extra.get("owner_pid")
        task_raw = (ledger.get("tasks") or {}).get(call.get("task_id") or "")
        if pid is None and isinstance(task_raw, dict):
            pid = task_raw.get("owner_pid")
        if state == "sent" and pid_alive(pid if isinstance(pid, int) else None):
            live.add(str(call.get("task_id") or ""))
        elif state == "durable" and pid_alive(pid if isinstance(pid, int) else None):
            live.add(str(call.get("task_id") or ""))
    live.discard("")
    return live


def _details_from_raw_payload(raw: dict[str, Any]) -> list[dict[str, Any]]:
    text = str(raw.get("result_text") or raw.get("text") or "")
    if not text.strip():
        return []
    try:
        parsed = parse_json_result(text)
    except RunnerError:
        return []
    items = parsed.get("details")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _canonical_is_current_complete_merge(
    canonical: dict[str, Any] | None,
    fragment_ids: list[str],
    details: dict[str, Any],
) -> bool:
    """Keep a live canonical only with current fragment identity evidence. Do not guess."""

    if not isinstance(canonical, dict) or not fragment_ids:
        return False
    provenance = canonical.get("provenance") or {}
    if provenance.get("historical") or provenance.get("incomplete") or provenance.get("stale"):
        return False
    if not str(canonical.get("behavior") or "").strip():
        return False
    merged = [
        str(item)
        for item in (provenance.get("merged_from_fragments") or provenance.get("merged_from_slices") or [])
        if item
    ]
    if not merged or set(merged) != set(fragment_ids):
        return False
    if provenance.get("complete") is False:
        return False
    for fragment_id in fragment_ids:
        record = details.get(fragment_id)
        if not isinstance(record, dict) or not str(record.get("behavior") or "").strip():
            return False
        fragment_provenance = record.get("provenance") or {}
        if fragment_provenance.get("historical") or fragment_provenance.get("stale"):
            return False
    return True


def apply_fragment_plan_migration(ledger: dict[str, Any], *, run_dir: Path) -> tuple[bool, dict[str, Any]]:
    """Rebuild fragment obligations on a frozen inventory. Keep budget, calls, and raw bytes."""

    report: dict[str, Any] = {
        "changed": False,
        "kept_run": True,
        "live_tasks_skipped": [],
        "affected_detail_ids": [],
        "historical_detail_ids": [],
        "restored_fragment_ids": [],
        "ambiguous": [],
        "new_merge_tasks": 0,
        "new_detail_tasks": 0,
        "pending_first_round": 0,
        "pending_merge": 0,
        "residuals": [],
        "error": None,
    }
    live = _live_task_ids(ledger)
    report["live_tasks_skipped"] = sorted(live)
    inventory_payload = ledger.get("inventory") or {}
    repo_root = ledger.get("repo_root") or inventory_payload.get("repo_root")
    if not repo_root:
        report["error"] = "missing_repo_root"
        return False, report
    repo = Path(str(repo_root))
    try:
        inventory = Inventory.from_dict(inventory_payload)
    except (KeyError, TypeError, ValueError) as exc:
        report["error"] = f"inventory_unreadable:{exc}"
        return False, report
    window = int((ledger.get("packets") or {}).get("window_chars") or packet_window())
    try:
        rebuilt = pack_inventory(inventory, repo=repo, window_chars=window)
    except (PacketSourceError, DuplicateIdentityError, RuntimeError) as exc:
        report["error"] = str(exc)
        return False, report

    old_payloads = list((ledger.get("packets") or {}).get("packets") or [])
    try:
        old_packets = [Packet.from_dict(item) for item in old_payloads]
        unique_by_id(old_packets, id_of=lambda packet: packet.packet_id, kind="packet")
    except DuplicateIdentityError as exc:
        report["error"] = str(exc)
        report["ambiguous"].append({"code": "duplicate_old_packet_id", "message": str(exc)})
        return False, report

    old_by_span: dict[tuple[str, tuple[tuple[int, int], ...]], Packet] = {}
    for packet in old_packets:
        key = span_key(packet)
        if key in old_by_span:
            report["error"] = "ambiguous_old_packet_spans"
            report["ambiguous"].append({"code": "duplicate_old_span_set", "path": packet.path})
            return False, report
        old_by_span[key] = packet
    new_by_span = unique_by_id(rebuilt.packets, id_of=span_key, kind="packet-span")

    migrated: list[Packet] = []
    unmatched_new = 0
    for packet in old_packets:
        rebuilt_packet = new_by_span.get(span_key(packet))
        if rebuilt_packet is None:
            migrated.append(packet)
            continue
        fragments = tuple(retarget_fragment(item, packet.packet_id) for item in rebuilt_packet.fragments)
        packet.fragments = fragments
        packet.symbol_ids = rebuilt_packet.symbol_ids
        packet.parent_symbol_id = rebuilt_packet.parent_symbol_id
        migrated.append(packet)
    for key, rebuilt_packet in new_by_span.items():
        if key not in old_by_span:
            migrated.append(rebuilt_packet)
            unmatched_new += 1
    unique_by_id(migrated, id_of=lambda packet: packet.packet_id, kind="packet")

    tasks = ledger.setdefault("tasks", {})
    details = ledger.setdefault("details", {})
    before_task_ids = set(tasks)
    before_detail_ids = set(details)
    record_tasks: dict[str, TaskRecord] = {key: TaskRecord.from_dict(value) for key, value in tasks.items()}
    before_sig = _fragment_plan_signature(old_packets, record_tasks)
    for packet in migrated:
        task_id = f"task:detail:{packet.packet_id}"
        symbol_policies = (ledger.get("documentation_policy") or {}).get("symbols")
        built = build_detail_task(packet, symbol_policies=symbol_policies)
        if task_id in live:
            continue
        existing = record_tasks.get(task_id)
        if existing is None:
            record_tasks[task_id] = built
            report["new_detail_tasks"] += 1
            continue
        extra = dict(existing.extra or {})
        extra["fragments"] = [item.to_dict() for item in packet.fragments]
        existing.extra = extra
        existing.packet_id = packet.packet_id
        if existing.state == "committed":
            record_tasks[task_id] = existing
            continue
        existing.input_ids = list(built.input_ids)
        existing.input_hash = built.input_hash
        record_tasks[task_id] = existing
    _register_merge_tasks(
        record_tasks, migrated,
        symbol_policies=(ledger.get("documentation_policy") or {}).get("symbols"),
    )

    fragments_by_symbol: dict[str, list[str]] = {}
    for packet in migrated:
        for fragment in packet.fragments:
            fragments_by_symbol.setdefault(fragment.symbol_id, []).append(fragment.fragment_id)
    historical = 0
    for symbol_id, symbol_fragment_ids in fragments_by_symbol.items():
        unique_ids = list(dict.fromkeys(symbol_fragment_ids))
        if len(unique_ids) <= 1:
            continue
        canonical = details.get(symbol_id)
        if not isinstance(canonical, dict):
            continue
        if (canonical.get("provenance") or {}).get("historical"):
            continue
        if _canonical_is_current_complete_merge(canonical, unique_ids, details):
            continue
        details[symbol_id] = mark_detail_historical(
            canonical, reason="cross_packet_incomplete_canonical"
        )
        historical += 1
        report["historical_detail_ids"].append(symbol_id)
        report["affected_detail_ids"].append(symbol_id)
        merge_id = f"task:merge:{symbol_id}"
        merge = record_tasks.get(merge_id)
        if merge is not None and merge.state == "committed":
            merge.state = "pending"
            record_tasks[merge_id] = merge

    calls = ledger.get("calls") or {}
    restored = 0
    ambiguous_restore = 0
    for packet in migrated:
        if packet.packet_id in {record_tasks[tid].packet_id for tid in live if tid in record_tasks}:
            continue
        for fragment in packet.fragments:
            if fragment.writes_canonical:
                continue
            if fragment.fragment_id in details:
                continue
            task_id = f"task:detail:{packet.packet_id}"
            candidates: list[dict[str, Any]] = []
            seen_raw: set[str] = set()
            for call in calls.values():
                if call.get("task_id") != task_id:
                    continue
                if (call.get("extra") or {}).get("disposition") in {"bootstrap_failed", "provider_failed", "rejected"}:
                    continue
                path = call.get("raw_path")
                if not path or path in seen_raw:
                    continue
                seen_raw.add(str(path))
                payload = _load_raw_file(Path(str(path)))
                if payload is None:
                    continue
                for item in _details_from_raw_payload(payload):
                    symbol_id = item.get("symbol_id")
                    if symbol_id in {fragment.symbol_id, fragment.fragment_id}:
                        candidates.append(item)
            if len(candidates) > 1:
                ambiguous_restore += 1
                report["ambiguous"].append(
                    {
                        "code": "ambiguous_raw_fragment",
                        "packet_id": packet.packet_id,
                        "symbol_id": fragment.symbol_id,
                    }
                )
                continue
            if len(candidates) != 1:
                continue
            item = dict(candidates[0])
            item["symbol_id"] = fragment.fragment_id
            provenance = dict(item.get("provenance") or {})
            provenance.update(
                {
                    "role": "fragment",
                    "fragment_id": fragment.fragment_id,
                    "canonical_symbol_id": fragment.symbol_id,
                    "fragment_identity": fragment.identity_hash,
                    "restored_from_raw": True,
                    "fresh": False,
                    "source_reread": False,
                }
            )
            item["provenance"] = provenance
            item["packet_id"] = packet.packet_id
            item["source_spans"] = [
                {"path": packet.path, **span.to_dict()} for span in fragment.owned_spans
            ]
            existing_frag = details.get(fragment.fragment_id)
            if isinstance(existing_frag, dict):
                continue
            from cbe.models import DetailRecord, nav_sentence

            record = DetailRecord(
                symbol_id=fragment.fragment_id,
                behavior=str(item.get("behavior") or "").strip(),
                inputs_outputs=item.get("inputs_outputs"),
                effects=item.get("effects"),
                failures=item.get("failures"),
                dependencies=item.get("dependencies"),
                unresolved=item.get("unresolved"),
                nav_sentence=nav_sentence(str(item.get("behavior") or ""), fragment.fragment_id),
                source_spans=list(item.get("source_spans") or []),
                packet_id=packet.packet_id,
                input_hash=str((record_tasks.get(task_id).input_hash if task_id in record_tasks else "")),
                revision=1,
                provenance=provenance,
            )
            if not record.behavior:
                continue
            details[fragment.fragment_id] = record.to_dict()
            restored += 1
            report["restored_fragment_ids"].append(fragment.fragment_id)

    for key, value in record_tasks.items():
        tasks[key] = value.to_dict()
    ledger["packets"] = {
        "window_chars": window,
        "packets": [packet.to_dict() for packet in migrated],
    }
    report["new_merge_tasks"] = sum(1 for key in tasks if key.startswith("task:merge:") and key not in before_task_ids)
    report["restored_fragment_count"] = restored
    report["historical_count"] = historical
    report["unmatched_new_packets"] = unmatched_new
    report["pending_first_round"] = sum(
        1
        for task in record_tasks.values()
        if task.kind == "detail" and task.state in {"pending", "needs_repair"} and not is_historical_task(task)
    )
    report["pending_merge"] = sum(
        1
        for task in record_tasks.values()
        if task.kind == "merge" and task.state in {"pending", "needs_repair"} and not is_historical_task(task)
    )
    report["task_count"] = len(tasks)
    report["detail_count"] = len(details)
    report["merge_count"] = sum(1 for task in record_tasks.values() if task.kind == "merge")
    report["residuals"] = fragment_plan_residuals(ledger)
    after_sig = _fragment_plan_signature(migrated, record_tasks)
    changed = (
        before_sig != after_sig
        or set(tasks) != before_task_ids
        or set(details) != before_detail_ids
        or historical > 0
        or restored > 0
    )
    report["changed"] = changed
    report["plan_signature"] = after_sig
    return changed, report


def resume(
    run_dir: Path,
    *,
    model: str = "grok",
    jobs: int = 1,
    limit: int | None = None,
) -> dict[str, Any]:
    store = LedgerStore(run_dir)
    initial = store.open()
    if (initial.get("documentation_policy") or {}).get("version") == "module-first-v2":
        from cbe.render import render as render_run

        manifest = render_run(run_dir)
        return {
            "imported_raw": [],
            "reconciled_calls": [],
            "recovered_leases": [],
            "fragment_plan_migration": None,
            "render_error": None,
            "render": {
                "page_count": manifest["page_count"],
                "token_budget": manifest["token_budget"],
                "accepted_group_explanation_count": manifest["accepted_group_explanation_count"],
            },
            "work": {"ran": [], "status": derived_status(store.open())},
        }
    reconciled = reconcile_unprocessed_calls(store, run_dir)
    recovered = recover_orphaned_leases(store, run_dir, owner=owner_name(), owner_pid=os.getpid())
    migration_report: dict[str, Any] | None = None

    def migrate(current: dict[str, Any]) -> dict[str, Any] | None:
        nonlocal migration_report
        try:
            changed, migration_report = apply_fragment_plan_migration(current, run_dir=run_dir)
        except DuplicateIdentityError as exc:
            migration_report = {"changed": False, "error": str(exc), "kept_run": True, "ambiguous": [str(exc)]}
            return None
        if not changed:
            return None
        log = list(current.get("fragment_plan_log") or [])
        log.append({key: value for key, value in migration_report.items() if key != "residuals"})
        current["fragment_plan_log"] = log
        return current

    store.mutate(migrate)
    ledger = store.open()
    imported = []
    for task_raw in (ledger.get("tasks") or {}).values():
        task = TaskRecord.from_dict(task_raw)
        if is_historical_task(task):
            continue
        if task.state not in {"leased", "returned", "needs_repair"}:
            continue
        raw, kind = matching_raw_payload(run_dir, task, ledger)
        if kind == "none" or raw is None:
            continue
        imported.append(_import_raw(store, run_dir, task, raw, replay=True))
        ledger = store.open()
    ledger = store.open()
    from cbe.render import projection_fingerprint, render as render_run
    from cbe.token_budget import RenderBudgetExceeded

    fingerprint = projection_fingerprint(ledger)
    render_error: str | None = None
    if str(ledger.get("render_revision") or "") != fingerprint:
        failpoint("after_commit_before_render")
        try:
            render_run(run_dir)
        except RenderBudgetExceeded as exc:
            if (ledger.get("documentation_policy") or {}).get("version") != "weighted-v1":
                raise
            render_error = str(exc)
    if limit == 0:
        return {
            "imported_raw": imported,
            "reconciled_calls": reconciled,
            "recovered_leases": recovered,
            "fragment_plan_migration": migration_report,
            "render_error": render_error,
            "work": {"ran": [], "status": derived_status(store.open())},
        }
    worked = work(run_dir, model=model, jobs=jobs, limit=limit)
    return {
        "imported_raw": imported,
        "reconciled_calls": reconciled,
        "recovered_leases": recovered,
        "fragment_plan_migration": migration_report,
        "render_error": render_error,
        "work": worked,
    }


def _load_id_list(path: Path | None) -> list[str]:
    if path is None:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list) or any(not isinstance(item, str) for item in payload):
        raise RunnerError("id file must be a JSON array of strings")
    return list(payload)


def edges_for_selection(ledger: dict[str, Any], input_ids: list[str]) -> tuple[list[dict], list[dict], set[str]]:
    leaves: set[str] = set()
    for ident in input_ids:
        leaves |= leaf_member_ids(ledger, ident)
    internal: list[dict] = []
    boundary: list[dict] = []
    endpoints: set[str] = set()
    for edge in (ledger.get("graph") or {}).get("edges") or []:
        subject = edge.get("subject_id")
        target = edge.get("target_id")
        sub_in = subject in leaves
        tgt_in = target in leaves
        if sub_in and tgt_in:
            internal.append(edge)
        elif sub_in or tgt_in:
            boundary.append(edge)
            if subject and not sub_in:
                endpoints.add(subject)
            if target and not tgt_in:
                endpoints.add(target)
    return internal, boundary, endpoints


def group_claim_input_hash(ledger: dict[str, Any], input_ids: list[str]) -> str:
    internal, boundary, _ = edges_for_selection(ledger, input_ids)
    edges = internal + boundary
    if (ledger.get("documentation_policy") or {}).get("version") == "weighted-v1":
        leaves = set().union(*(leaf_member_ids(ledger, ident) for ident in input_ids))
        edges += [
            edge for edge in ((ledger.get("graph") or {}).get("unknown_edges") or [])
            if edge.get("subject_id") in leaves or edge.get("target_id") in leaves
        ]
        return sha256_text(group_selection_input_hash(ledger, input_ids, edges) + GROUP_PROJECTION_VERSION)
    return group_selection_input_hash(ledger, input_ids, edges)


def _short_card(ledger: dict[str, Any], ident: str) -> dict[str, Any]:
    detail = (ledger.get("details") or {}).get(ident)
    if detail:
        symbol = ((ledger.get("inventory") or {}).get("symbols") or {}).get(ident) or {}
        return {
            "id": ident,
            "type": "detail",
            "kind": symbol.get("kind"),
            "name": symbol.get("name"),
            "revision": detail.get("revision"),
        }
    group = (ledger.get("groups") or {}).get(ident)
    if group:
        return {
            "id": ident,
            "type": "group",
            "question_answered": group.get("question_answered"),
            "version": group.get("version"),
            "partial": group.get("partial"),
        }
    symbol = ((ledger.get("inventory") or {}).get("symbols") or {}).get(ident) or {}
    return {"id": ident, "type": "symbol", "kind": symbol.get("kind"), "name": symbol.get("name")}


def _child_document(ledger: dict[str, Any], ident: str) -> dict[str, Any] | None:
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    if ident in details:
        rec = details[ident]
        return {
            "type": "detail",
            "id": ident,
            "version": rec.get("revision"),
            "fingerprint": content_fingerprint(rec),
            "record": rec,
        }
    if ident in groups:
        rec = groups[ident]
        return {
            "type": "group",
            "id": ident,
            "version": rec.get("version"),
            "fingerprint": content_fingerprint(rec),
            "record": {
                "group_id": rec.get("group_id", ident),
                "body": rec.get("body"),
                "version": rec.get("version"),
                "question_answered": rec.get("question_answered"),
                "grouping_reason": rec.get("grouping_reason"),
                "member_ids": rec.get("member_ids"),
                "children": rec.get("children"),
                "entry_routes": rec.get("entry_routes"),
                "relations": rec.get("relations"),
                "partial": rec.get("partial"),
                "parent_id": rec.get("parent_id"),
                "extra": rec.get("extra"),
            },
        }
    return None


def _parent_chain(ledger: dict[str, Any], ident: str) -> list[str]:
    chain: list[str] = []
    groups = ledger.get("groups") or {}
    owned_by = None
    for gid, group in groups.items():
        if ident in (group.get("member_ids") or []) or ident in (group.get("children") or []):
            owned_by = gid
            break
    cursor = owned_by
    seen: set[str] = set()
    while cursor and cursor not in seen:
        seen.add(cursor)
        chain.append(cursor)
        cursor = (groups.get(cursor) or {}).get("parent_id")
    return chain


def _weighted_group_evidence(ledger: dict[str, Any], input_ids: list[str]) -> dict[str, Any]:
    """Prepare a bounded, loss-aware group packet from direct child facts."""
    from cbe.token_budget import count_text_tokens

    internal, boundary, _ = edges_for_selection(ledger, input_ids)
    leaves = set().union(*(leaf_member_ids(ledger, ident) for ident in input_ids))
    graph = ledger.get("graph") or {}
    unknown = [
        edge for edge in (graph.get("unknown_edges") or [])
        if edge.get("subject_id") in leaves or edge.get("target_id") in leaves
    ]
    documents = [_child_document(ledger, ident) for ident in input_ids]
    if any(document is None for document in documents):
        raise RunnerError("weighted group selection contains a missing direct child")
    result = project_group_evidence(
        documents,
        edges={"internal": internal, "boundary": boundary, "unknown": unknown},
        child_members={ident: sorted(leaf_member_ids(ledger, ident)) for ident in input_ids},
        max_chars=min(group_packet_window(), 20_000),
        max_tokens=4_800,
        count_tokens=count_text_tokens,
    )
    if result.payload is None:
        raise RunnerError(json.dumps({
            "error": "group_evidence_does_not_fit",
            "residual": result.residual,
            "input_ids": input_ids,
        }, ensure_ascii=False))
    return {
        "projection": result.payload,
        "evidence_residual": list(result.residual),
        "evidence_chars": result.chars,
        "evidence_tokens": result.tokens,
    }


def _write_group_packet(
    run_dir: Path,
    ledger: dict[str, Any],
    task: TaskRecord,
    *,
    replace_group_id: str | None,
) -> Path:
    if (ledger.get("documentation_policy") or {}).get("version") == "weighted-v1":
        evidence = _weighted_group_evidence(ledger, task.input_ids)
        policy = ledger["documentation_policy"]
        payload = {
            "task_id": task.task_id,
            "kind": task.kind,
            "documentation_profile": "weighted-v1",
            "envelope": {
                "task_id": task.task_id,
                "generation": task.generation,
                "owner": task.owner,
                "input_hash": task.input_hash,
            },
            "input_ids": task.input_ids,
            "replace_group_id": replace_group_id,
            "group_limit": policy.get("group_limit"),
            **evidence,
            "rules": [
                "Group by coherent behavior at feature/module scale. Avoid pass-through groups and duplicate summaries.",
                "Use only the supplied direct-child facts and graph evidence; request exact edge pages if the residual says edges were summarized.",
                "Return groups that partition every selected input exactly once, or defer it explicitly.",
                "A Detail ID belongs only in member_ids. children contains existing/new group IDs only; never repeat an ID across the two arrays.",
                "Choose presentation=navigation for a directory that adds no combined behavior; narrative only when a short explanation changes understanding.",
                "Preserve behavior-changing failures, effects, and unresolved facts in each group's evidence_summary.",
            ],
            "import_schema": {
                "groups": [{
                    "group_id": "str", "member_ids": "list[str] direct Detail IDs only",
                    "children": "list[str] direct group IDs only; [] for leaf groups",
                    "question_answered": "str", "grouping_reason": "str",
                    "presentation": "navigation|narrative",
                    "evidence_summary": {
                        "behavior": "str", "effects": "list[str]",
                        "failures": "list[str]", "unresolved": "list[str]",
                    },
                }],
                "deferred_ids": "list[str]",
            },
        }
        review_feedback = (task.extra or {}).get("review_feedback")
        if review_feedback:
            payload["review_feedback"] = review_feedback
            payload["rules"].append(
                "The prior group was rejected by independent source review. "
                "Address each listed issue in one replacement group with the same group_id and no deferred inputs; "
                "do not reuse the rejected title or summary verbatim."
            )
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(encoded) > group_packet_window():
            raise RunnerError("weighted group packet exceeds the configured character window")
        from cbe.token_budget import count_text_tokens
        if count_text_tokens(encoded) > 5_500:
            raise RunnerError("weighted group packet exceeds the 5500-token input window")
        digest = sha256_text(encoded)
        path = run_dir / "packets" / f"group-{digest}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded, encoding="utf-8")
        return path
    internal, boundary, endpoints = edges_for_selection(ledger, task.input_ids)
    children = []
    for ident in task.input_ids:
        doc = _child_document(ledger, ident)
        if doc is None:
            raise RunnerError(f"selected input {ident} has no fresh child document")
        children.append(doc)
    graph = ledger.get("graph") or {}
    leaves: set[str] = set()
    for ident in task.input_ids:
        leaves |= leaf_member_ids(ledger, ident)
    relevant = set(leaves) | set(endpoints)
    related_entries = [item for item in (graph.get("entries") or []) if item in relevant]
    related_sccs = [
        component
        for component in (graph.get("sccs") or [])
        if relevant.intersection(component)
    ]
    related_shared = [
        item
        for item in (graph.get("shared_callees") or [])
        if item.get("symbol_id") in relevant
    ]
    related_unknown = [
        edge
        for edge in (graph.get("unknown_edges") or [])
        if edge.get("subject_id") in leaves or edge.get("target_id") in leaves
    ]
    payload = {
        "task_id": task.task_id,
        "kind": task.kind,
        "envelope": {
            "task_id": task.task_id,
            "generation": task.generation,
            "owner": task.owner,
            "input_hash": task.input_hash,
        },
        "input_ids": task.input_ids,
        "replace_group_id": replace_group_id,
        "children": children,
        "edges": {
            "internal": internal,
            "boundary": boundary,
            "internal_total": len(internal),
            "boundary_total": len(boundary),
        },
        "boundary_cards": [_short_card(ledger, ident) for ident in sorted(endpoints)],
        "parent_chain": {ident: _parent_chain(ledger, ident) for ident in task.input_ids},
        "graph": {
            "entries": page_list(related_entries, page=0, page_size=40),
            "entries_total": graph.get("entries_total", len(graph.get("entries") or [])),
            "sccs": page_list(related_sccs, page=0, page_size=20),
            "sccs_total": graph.get("sccs_total", len(graph.get("sccs") or [])),
            "shared_callees": page_list(related_shared, page=0, page_size=40),
            "shared_callees_total": graph.get("shared_callees_total", len(graph.get("shared_callees") or [])),
            "unknown_edges": page_list(related_unknown, page=0, page_size=40),
            "unknown_edges_total": graph.get("unknown_edges_total", len(graph.get("unknown_edges") or [])),
            "edges_total": graph.get("edges_total", len(graph.get("edges") or [])),
            "nodes_total": graph.get("nodes_total", len(graph.get("nodes") or [])),
            "structural_hints_total": graph.get(
                "structural_hints_total", len(graph.get("structural_hints") or [])
            ),
            "hint_disclaimer": "structural_hints are evidence only; do not import them as architecture",
        },
        "clean_context": "Load skill clean-context. This packet is the necessary input.",
        "import_schema": {
            "envelope": {"task_id": "str", "generation": "int", "owner": "str", "input_hash": "str"},
            "groups": [
                {
                    "group_id": "str",
                    "children": "list[str] direct groups only",
                    "member_ids": "list[str] direct details only",
                    "question_answered": "str",
                    "grouping_reason": "str",
                    "entry_routes": "list[str]",
                    "relations": "list",
                    "body": "str optional",
                    "parent_id": "str|null derived",
                    "partial": "bool",
                }
            ],
            "deferred_ids": "list[str] remaining selected inputs, still ungrouped",
        },
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2)
    digest = sha256_text(encoded)
    path = run_dir / "packets" / f"group-{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")
    return path


def _merge_intervals(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not spans:
        return []
    ordered = sorted(spans)
    out = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = out[-1]
        if start <= last_end:
            out[-1] = (last_start, max(last_end, end))
        else:
            out.append((start, end))
    return out


def extract_review_source(ledger: dict[str, Any], target_ids: list[str]) -> tuple[str, list[dict], int]:
    files = (ledger.get("inventory") or {}).get("files") or {}
    symbols = (ledger.get("inventory") or {}).get("symbols") or {}
    details = ledger.get("details") or {}
    repo = Path(ledger["repo_root"])
    by_file: dict[str, list[tuple[int, int]]] = {}
    for ident in target_ids:
        detail = details.get(ident)
        symbol = symbols.get(ident)
        if detail:
            spans = detail.get("source_spans") or []
            path = None
            if symbol:
                path = symbol.get("path")
            for span in spans:
                if isinstance(span, dict):
                    path = span.get("path") or path
                    start = int(span.get("start") or 0)
                    end = int(span.get("end") or 0)
                    if path:
                        by_file.setdefault(path, []).append((start, end))
            if not spans and symbol and path:
                span = symbol.get("span") or {}
                by_file.setdefault(path, []).append((int(span.get("start") or 0), int(span.get("end") or 0)))
        elif symbol:
            span = symbol.get("span") or {}
            by_file.setdefault(symbol["path"], []).append((int(span.get("start") or 0), int(span.get("end") or 0)))
    chunks: list[str] = []
    used: list[dict] = []
    total = 0
    for path, spans in sorted(by_file.items()):
        record = files.get(path) or {}
        offsets = load_frozen_offsets(repo, path, record)
        for start, end in _merge_intervals(spans):
            piece = offsets.text[start:end]
            chunks.append(piece)
            used.append({"path": path, "start": start, "end": end, "chars": end - start})
            total += end - start
    return "".join(chunks), used, total


def _write_review_packet(
    run_dir: Path,
    ledger: dict[str, Any],
    task: TaskRecord,
    *,
    include_source: bool,
    source: str,
    spans: list[dict],
) -> Path:
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    selected_details = {key: details[key] for key in task.input_ids if key in details}
    selected_groups = {key: groups[key] for key in task.input_ids if key in groups}
    payload = {
        "task_id": task.task_id,
        "kind": "review",
        "envelope": {
            "task_id": task.task_id,
            "generation": task.generation,
            "owner": task.owner,
            "input_hash": task.input_hash,
            "call_id": (task.extra or {}).get("call_id"),
        },
        "target_ids": task.input_ids,
        "details": selected_details,
        "groups": {
            key: {
                "group_id": rec.get("group_id", key),
                "body": rec.get("body"),
                "version": rec.get("version"),
                "question_answered": rec.get("question_answered"),
                "member_ids": rec.get("member_ids"),
                "children": rec.get("children"),
            }
            for key, rec in selected_groups.items()
        },
        "include_source": include_source,
        "source_spans": spans if include_source else [],
        "source": source if include_source else "",
        "packed_source_chars": len(source) if include_source else 0,
        "protected_attributes": {
            "source_fact_reviewer": "may see the documents and necessary source slices; must not see author process or completion narrative",
            "fresh_reader": "questions and generated docs only; do not reuse this task after seeing answers",
        },
        "import_schema": {
            "envelope": {"task_id": "str", "generation": "int", "owner": "str", "input_hash": "str", "call_id": "str"},
            "review_id": "str",
            "verdict": "str",
            "notes": "str",
            "source_chars": "ignored self-report; authority is packed payload + trace",
        },
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2)
    digest = sha256_text(encoded)
    path = run_dir / "packets" / f"review-{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")
    return path


def release_tasks(run_dir: Path, task_ids: list[str], *, reason: str = "released_by_orchestrator", cancel: bool = False) -> dict[str, Any]:
    """Return dead-leased tasks to pending, or cancel them as stale.

    Bumping the generation invalidates any outstanding claim envelope, so a
    late-arriving stale result is rejected instead of double-committed.
    Cancel marks the task stale (superseded claims, aborted plans); the record
    stays queryable and never re-enters the runnable set.
    """
    store = LedgerStore(run_dir)
    released: list[str] = []

    def mutate(ledger: dict[str, Any]) -> dict[str, Any]:
        for tid in task_ids:
            raw = (ledger.get("tasks") or {}).get(tid)
            if raw is None:
                continue
            task = TaskRecord.from_dict(raw)
            if task.state not in {"leased", "pending"}:
                continue
            if pid_alive(task.owner_pid):
                continue
            task.state = "stale" if cancel else "pending"
            task.owner = None
            task.owner_pid = None
            task.lease_until = None
            task.generation += 1
            extra = dict(task.extra or {})
            extra["release_reason"] = reason
            task.extra = extra
            if cancel:
                task.residual = [{"code": "cancelled", "reason": reason}]
            ledger["tasks"][tid] = task.to_dict()
            released.append(tid)
        return ledger

    store.mutate(mutate)
    return {"released": released}


def produce_external(
    run_dir: Path,
    *,
    task_id: str | None = None,
    count: int = 1,
    owner: str | None = None,
    task_kind: str = "detail",
) -> dict[str, Any]:
    """Claim detail/group_body tasks for session-dispatched sub-agent production.

    Each claimed task gets a budget-reserved call and a self-contained prompt
    (source injected once, claim envelope embedded, explicit result path).
    The session hands the prompt to a sub-agent of whatever model the host
    provides; the sub-agent writes the result JSON; `import-result` consumes it.
    """
    if task_kind not in {"detail", "group_body", "merge"}:
        raise RunnerError(f"produce_external supports detail/group_body/merge, got {task_kind}")
    store = LedgerStore(run_dir)
    ledger = store.open()
    tasks: list[TaskRecord] = []
    if task_id is not None:
        raw_task = (ledger.get("tasks") or {}).get(task_id)
        if raw_task is None:
            raise RunnerError(f"unknown task {task_id}")
        candidate = TaskRecord.from_dict(raw_task)
        if candidate.kind != task_kind:
            raise RunnerError(f"claim --kind {task_kind} only opens {task_kind} tasks, got {candidate.kind}")
        tasks.append(candidate)
    else:
        skipped: set[tuple[str, str]] = set()
        while len(tasks) < max(1, count):
            candidate = _next_runnable(ledger, skipped, kind=task_kind)
            if candidate is None:
                break
            tasks.append(candidate)
            skipped.add((candidate.task_id, candidate.input_hash))
    if not tasks:
        return {"kind": task_kind, "claimed": [], "note": f"no runnable {task_kind} task"}
    claimed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for candidate in tasks:
        prep = _prepare_call(store, run_dir, candidate, model="external", external=True, owner_override=owner)
        if prep["status"] != "ready":
            errors.append(prep["result"])
            continue
        claimed.append(
            {
                "task_id": prep["task"].task_id,
                "kind": prep["task"].kind,
                "call_id": prep["call_id"],
                "envelope": prep["envelope"],
                "prompt_path": str(prep["prompt_path"]),
                "result_path": str(prep["result_path"]),
                "packet_id": prep["packet"].packet_id if prep["packet"] is not None else None,
                "source_chars": prep["source_chars"],
            }
        )
    return {"kind": task_kind, "claimed": claimed, "errors": errors}


def claim_kind(
    run_dir: Path,
    *,
    kind: str,
    task_id: str | None = None,
    owner: str | None = None,
    input_ids_file: Path | None = None,
    target_ids_file: Path | None = None,
    replace_group_id: str | None = None,
    include_source: bool = False,
    page: int = 0,
    page_size: int = DEFAULT_FRONTIER_PAGE,
    count: int = 1,
) -> dict[str, Any]:
    if kind == "detail":
        return produce_external(run_dir, task_id=task_id, count=count, owner=owner, task_kind="detail")
    if kind == "group_body":
        return produce_external(run_dir, task_id=task_id, count=count, owner=owner, task_kind="group_body")
    if kind == "merge":
        return produce_external(run_dir, task_id=task_id, count=count, owner=owner, task_kind="merge")
    if kind not in {"group", "review"}:
        raise RunnerError("claim --kind must be detail, merge, group_body, group or review")
    store = LedgerStore(run_dir)
    owner = owner or owner_name()
    if kind == "review" and target_ids_file is None:
        raise RunnerError("claim --kind review requires --target-ids-file")
    if kind == "group" and input_ids_file is None:
        ledger = store.open()
        existing = (ledger.get("tasks") or {}).get(task_id or "")
        if isinstance(existing, dict) and existing.get("kind") == "group":
            selected = list(existing.get("input_ids") or [])
        else:
            return {
                "kind": "group",
                "task_id": None,
                "opened_task": False,
                "frontier": frontier_payload(
                    ledger, page=page, page_size=page_size, replace_group_id=replace_group_id
                ),
            }
    else:
        selected = _load_id_list(input_ids_file if kind == "group" else target_ids_file)
    if not selected:
        raise RunnerError("selected id list is empty")

    created_id = {"id": task_id}
    budget_reject: dict[str, Any] = {}

    def mutate(ledger: dict[str, Any]) -> dict[str, Any] | None:
        tasks = ledger.setdefault("tasks", {})
        existing_raw = tasks.get(created_id["id"] or "")
        stored_replace = (existing_raw.get("extra") or {}).get("replace_group_id") if isinstance(existing_raw, dict) else None
        if replace_group_id and stored_replace and replace_group_id != stored_replace:
            raise RunnerError("replace_group_id conflicts with the existing group task")
        effective_replace = replace_group_id or stored_replace
        if kind == "group":
            allowed = frontier_ids(ledger, replace_group_id=effective_replace)
            allowed_ids = set(allowed["details"]) | set(allowed["groups"])
            missing = [ident for ident in selected if ident not in allowed_ids]
            if missing:
                raise RunnerError(f"group inputs are not fresh ungrouped documents: {missing}")
            if (ledger.get("documentation_policy") or {}).get("version") == "weighted-v1":
                _weighted_group_evidence(ledger, selected)
            else:
                children = [_child_document(ledger, ident) for ident in selected]
                encoded = json.dumps(children, ensure_ascii=False)
                needed = len(encoded)
                limit = group_packet_window()
                if needed > limit:
                    raise RunnerError(
                        json.dumps(
                            {
                                "error": "inputs_do_not_fit",
                                "needed_chars": needed,
                                "limit": limit,
                                "input_ids": selected,
                                "note": "split the work slice; do not silently truncate",
                            }
                        )
                    )
            input_hash = group_claim_input_hash(ledger, selected)
        else:
            input_hash = sha256_text(
                json.dumps(
                    {"targets": selected, "include_source": include_source, "rev": ledger.get("source_revision")},
                    sort_keys=True,
                )
            )
        chosen = created_id["id"]
        if chosen is None:
            chosen = f"task:{kind}:design-{uuid.uuid4().hex[:8]}"
            created_id["id"] = chosen
        if chosen not in tasks:
            tasks[chosen] = TaskRecord(
                task_id=chosen,
                kind=kind,
                input_ids=selected,
                input_hash=input_hash,
                state="pending",
                extra={
                    "created_by": "claim",
                    "replace_group_id": effective_replace,
                    "include_source": include_source,
                },
            ).to_dict()
        else:
            existing_task = TaskRecord.from_dict(tasks[chosen])
            if existing_task.kind != kind or existing_task.input_ids != selected:
                raise RunnerError("existing task kind or input IDs differ from this claim")
            if existing_task.input_hash != input_hash and existing_task.state in {"pending", "needs_repair"}:
                existing_task.input_hash = input_hash
                existing_task.generation += 1
                existing_task.residual = []
                tasks[chosen] = existing_task.to_dict()
        claim_task(
            ledger,
            task_id=chosen,
            owner=owner,
            owner_pid=os.getpid(),
            lease_seconds=int(os.environ.get("CBE_LEASE_SECONDS") or 7200),
            raw_exists=False,
        )
        task_now = TaskRecord.from_dict(ledger["tasks"][chosen])
        if kind == "review" and include_source:
            try:
                source, spans, chars = extract_review_source(ledger, selected)
            except PacketSourceError as exc:
                raise RunnerError(f"source_conflict:{exc}") from exc
            call_id = f"call-review-{uuid.uuid4().hex}"
            try:
                reserve_call(
                    ledger,
                    CallRecord(
                        call_id=call_id,
                        task_id=chosen,
                        input_hash=task_now.input_hash,
                        source_spans=spans,
                        source_chars=0,
                        state="prepared",
                        delivery=DELIVERY_PACKET,
                        extra={
                            "review": True,
                            "include_source": True,
                            "delivery": DELIVERY_PACKET,
                            "packed_source_chars": chars,
                            "reservation_chars": chars,
                            "source_spans": spans,
                        },
                    ),
                )
            except BudgetError as exc:
                budget_reject.update(
                    {
                        "error": "source_budget_exceeded",
                        "message": str(exc),
                        "needed": chars,
                        "input_ids": selected,
                    }
                )
                return None
            extra = dict(ledger["tasks"][chosen].get("extra") or {})
            extra.update(
                {
                    "call_id": call_id,
                    "packed_source_chars": chars,
                    "source_spans": spans,
                    "include_source": True,
                    "delivery": DELIVERY_PACKET,
                }
            )
            ledger["tasks"][chosen]["extra"] = extra
        return ledger

    try:
        ledger = store.mutate(mutate)
    except RunnerError:
        raise
    if budget_reject:
        return {**budget_reject, "packet": None, "exposed_source": False}
    task = TaskRecord.from_dict(ledger["tasks"][created_id["id"]])
    if kind == "group":
        try:
            packet_path = _write_group_packet(
                run_dir, ledger, task,
                replace_group_id=(task.extra or {}).get("replace_group_id"),
            )
        except RunnerError as exc:
            # The bounded child projection can fit while the complete
            # envelope/rules/schema packet does not. Never strand a live lease
            # after that post-claim serialization failure.
            def release_failed_packet(current: dict[str, Any]) -> dict[str, Any]:
                record = TaskRecord.from_dict(current["tasks"][task.task_id])
                if record.state == "leased" and record.generation == task.generation:
                    record.state = "needs_repair"
                    record.owner = None
                    record.owner_pid = None
                    record.lease_until = None
                    record.generation += 1
                    record.residual = [{"code": "group_packet_failed", "message": str(exc)}]
                    current["tasks"][task.task_id] = record.to_dict()
                return current

            store.mutate(release_failed_packet)
            raise RunnerError(f"group packet for {task.task_id} failed and lease was released: {exc}") from exc
        return {
            "task_id": task.task_id,
            "generation": task.generation,
            "owner": task.owner,
            "input_hash": task.input_hash,
            "envelope": {
                "task_id": task.task_id,
                "generation": task.generation,
                "owner": task.owner,
                "input_hash": task.input_hash,
            },
            "packet": str(packet_path),
            "kind": kind,
            "input_ids": task.input_ids,
            "opened_task": True,
        }
    source = ""
    spans: list[dict] = []
    if include_source:
        extra = task.extra or {}
        source_chars = int(extra.get("packed_source_chars") or 0)
        spans = list(extra.get("source_spans") or [])
        if source_chars:
            source, spans, source_chars = extract_review_source(ledger, task.input_ids)
    packet_path = _write_review_packet(
        run_dir, ledger, task, include_source=include_source, source=source, spans=spans
    )
    extra = task.extra or {}
    extra["packet_hash"] = packet_path.stem
    def persist_hash(current: dict[str, Any]) -> dict[str, Any]:
        current["tasks"][task.task_id]["extra"] = extra
        call_id = extra.get("call_id")
        if call_id and call_id in (current.get("calls") or {}):
            mark_call(
                current,
                call_id,
                packet_hash=packet_path.stem,
                extra={"packet_hash": packet_path.stem, "packet_path": str(packet_path)},
            )
        return current

    store.mutate(persist_hash)
    return {
        "task_id": task.task_id,
        "generation": task.generation,
        "owner": task.owner,
        "input_hash": task.input_hash,
        "call_id": extra.get("call_id"),
        "envelope": {
            "task_id": task.task_id,
            "generation": task.generation,
            "owner": task.owner,
            "input_hash": task.input_hash,
            "call_id": extra.get("call_id"),
        },
        "packet": str(packet_path),
        "kind": kind,
        "input_ids": task.input_ids,
        "include_source": include_source,
        "packed_source_chars": extra.get("packed_source_chars") or 0,
        "delivery": DELIVERY_PACKET if include_source else None,
        "opened_task": True,
    }


def _plans_from_payload(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    envelope = payload.get("envelope") if isinstance(payload.get("envelope"), dict) else {}
    deferred = list(payload.get("deferred_ids") or [])
    if isinstance(payload.get("groups"), list):
        return [item for item in payload["groups"] if isinstance(item, dict)], deferred, envelope
    if isinstance(payload.get("group"), dict):
        return [payload["group"]], deferred, envelope
    if payload.get("group_id"):
        return [payload], deferred, envelope
    return [], deferred, envelope


def _bind_external_call(
    ledger: dict[str, Any],
    task: TaskRecord,
    envelope: dict[str, Any],
    payload: dict[str, Any],
    *,
    kind: str,
) -> None:
    """Settle an external sub-agent call on import: store its self-report and close it.

    The mechanical check is intentionally light (2026-09-21 ruling): the report
    must exist, name what was read, and reference this assignment's packet or
    path. Findings are recorded on the call, never silently dropped, and do not
    block already-validated business records.
    """
    bound_call = envelope.get("call_id") or (task.extra or {}).get("call_id")
    if not bound_call:
        return
    calls = ledger.get("calls") or {}
    record = calls.get(str(bound_call))
    if not isinstance(record, dict):
        return
    if not (record.get("extra") or {}).get("external_subagent"):
        return
    report = payload.get("report") if isinstance(payload.get("report"), dict) else None
    status = "present"
    if report is None:
        status = "missing"
        report = {}
    read_items = report.get("read") if isinstance(report.get("read"), list) else []
    read_text = " ".join(str(item) for item in read_items)
    anchors = [item for item in [task.packet_id, (task.extra or {}).get("path")] if item]
    if status == "present" and (not read_items or (anchors and not any(str(a) in read_text for a in anchors))):
        status = "incomplete"
    now_task = TaskRecord.from_dict((ledger.get("tasks") or {})[task.task_id])
    disposition = "partial" if now_task.state == "needs_repair" else "accepted"
    mark_call(
        ledger,
        str(bound_call),
        state="imported",
        extra={
            "disposition": disposition,
            "processed": True,
            "self_report": report,
            "self_report_status": status,
        },
    )


def _invalidate_reviewed(ledger: dict[str, Any], payload: dict[str, Any]) -> None:
    """Invalidate source-flagged Details or Group bodies and their readers."""
    findings = [f for f in (payload.get("findings") or []) if isinstance(f, dict)]
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    tasks = ledger.get("tasks") or {}
    affected_symbols: set[str] = set()
    affected_groups: set[str] = set()
    for finding in findings:
        issue_full = (
            str(finding.get("issue") or "")
            or " ".join(
                part
                for part in (
                    str(finding.get("field") or ""),
                    str(finding.get("claim") or ""),
                    str(finding.get("correction") or ""),
                )
                if part
            )
        )
        group_id = finding.get("group_id")
        if isinstance(group_id, str) and group_id in groups:
            group = groups[group_id]
            extra = dict(group.get("extra") or {})
            feedback = list(extra.get("review_feedback") or [])
            item = {
                "issue": issue_full[:500],
                "evidence": str(finding.get("evidence") or "")[:500],
                "correction": str(finding.get("correction") or "")[:500],
            }
            if item not in feedback:
                feedback.append(item)
            extra["review_feedback"] = feedback
            if (
                (ledger.get("documentation_policy") or {}).get("version") == "weighted-v1"
                and extra.get("presentation") == "navigation"
            ):
                extra["review_hold"] = True
                inputs = list(group.get("member_ids") or []) + list(group.get("children") or [])
                regroup_id = f"task:group:review:{group_id}"
                previous = tasks.get(regroup_id) or {}
                tasks[regroup_id] = TaskRecord(
                    task_id=regroup_id,
                    kind="group",
                    input_ids=inputs,
                    input_hash=group_claim_input_hash(ledger, inputs),
                    state="pending",
                    generation=int(previous.get("generation") or 0) + 1,
                    extra={
                        "replace_group_id": group_id,
                        "review_feedback": feedback,
                        "created_by": "source_review",
                    },
                ).to_dict()
            group["extra"] = extra
            groups[group_id] = group
            affected_groups.add(group_id)
            affected_groups.update(ancestor_group_ids(ledger, group_id))
        sid = finding.get("symbol_id")
        if not sid or sid not in details:
            continue
        record = details[sid]
        provenance = dict(record.get("provenance") or {})
        provenance["stale"] = True
        provenance["review_flag"] = issue_full[:500]
        record["provenance"] = provenance
        details[sid] = record
        affected_symbols.add(sid)
        canonical = provenance.get("canonical_symbol_id")
        if isinstance(canonical, str) and canonical:
            affected_symbols.add(canonical)
        for raw in tasks.values():
            if raw.get("kind") != "detail" or raw.get("state") not in {"committed", "needs_repair", "pending"}:
                continue
            ids = list(raw.get("input_ids") or []) + list((raw.get("extra") or {}).get("original_input_ids") or [])
            if sid not in ids:
                continue
            task = TaskRecord.from_dict(raw)
            issue_text = issue_full[:500]
            existing = list(task.residual or [])
            already = any(
                r.get("code") == "review_revision" and r.get("symbol_id") == sid and r.get("issue") == issue_text
                for r in existing
            )
            if already:
                continue
            extra = dict(task.extra or {})
            repair_ids = list(extra.get("repair_ids") or [])
            if sid not in repair_ids:
                repair_ids.append(sid)
            extra["repair_ids"] = repair_ids
            task.extra = extra
            if task.state == "committed":
                task.generation += 1
            task.state = "needs_repair"
            task.owner = None
            task.owner_pid = None
            task.lease_until = None
            existing.append(
                {
                    "code": "review_revision",
                    "symbol_id": sid,
                    "issue": issue_text,
                    "evidence": str(finding.get("evidence") or "")[:500],
                }
            )
            task.residual = existing
            ledger["tasks"][task.task_id] = task.to_dict()

    if affected_symbols:
        for group_id, group in (ledger.get("groups") or {}).items():
            if affected_symbols.intersection(group.get("member_ids") or []):
                affected_groups.add(group_id)
                affected_groups.update(ancestor_group_ids(ledger, group_id))
    if affected_groups:
        invalidate_group_bodies(ledger, sorted(affected_groups))

def import_result(
    run_dir: Path,
    task_id: str,
    result_file: Path,
    *,
    call_id: str | None = None,
    external: bool = False,
) -> dict[str, Any]:
    store = LedgerStore(run_dir)
    payload = json.loads(Path(result_file).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RunnerError("import result must be a JSON object")
    if external:
        payload = dict(payload)
        payload["external_subagent"] = True
    envelope = payload.get("envelope") if isinstance(payload.get("envelope"), dict) else {}
    if not envelope or any(envelope.get(key) in (None, "") for key in ("task_id", "generation", "owner", "input_hash")):
        raise RunnerError("import-result requires envelope {task_id, generation, owner, input_hash}")
    if envelope.get("task_id") != task_id:
        raise RunnerError(f"envelope task_id {envelope.get('task_id')} does not match {task_id}")

    def mutate(ledger: dict[str, Any]) -> dict[str, Any]:
        task = TaskRecord.from_dict((ledger.get("tasks") or {})[task_id])
        bound_call = call_id or envelope.get("call_id") or (task.extra or {}).get("call_id")
        already_committed = (
            task.state == "committed"
            and task.generation == int(envelope["generation"])
            and task.owner == envelope.get("owner")
            and task.input_hash == envelope.get("input_hash")
        )
        if already_committed and task.kind != "review":
            if task.kind == "group":
                current_hash = group_claim_input_hash(ledger, list(task.input_ids))
                if current_hash != str(envelope["input_hash"]):
                    raise StaleWriteError(
                        f"child documents changed since claim: envelope {envelope['input_hash']} current {current_hash}"
                    )
            return ledger
        if task.kind == "group":
            plans, deferred, _env = _plans_from_payload(payload)
            current_hash = group_claim_input_hash(ledger, list(task.input_ids))
            if current_hash != str(envelope["input_hash"]):
                raise StaleWriteError(
                    f"child documents changed since claim: envelope {envelope['input_hash']} current {current_hash}"
                )
            submit_groups(
                ledger,
                task_id=task_id,
                owner=str(envelope["owner"]),
                generation=int(envelope["generation"]),
                input_hash=str(envelope["input_hash"]),
                plans=plans,
                deferred_ids=deferred,
                replace_group_id=(task.extra or {}).get("replace_group_id"),
            )
        elif task.kind == "review":
            reported = payload.get("source_chars")
            extra = dict(task.extra or {})
            if reported not in (None, extra.get("packed_source_chars")):
                extra["ignored_self_reported_source_chars"] = reported
                ledger["tasks"][task_id]["extra"] = extra
            include_source = bool(extra.get("include_source") or extra.get("delivery") == DELIVERY_PACKET)
            review_residuals = [
                item
                for item in list(payload.get("residual") or [])
                if item.get("code") != "needs_evidence"
            ]
            if bound_call and bound_call in (ledger.get("calls") or {}):
                crec = ledger["calls"][bound_call]
                crec_extra = dict(crec.get("extra") or {})
                if any(
                    item.get("reason") == "tool_use_without_result"
                    for item in (crec.get("source_exposures") or [])
                ):
                    review_residuals.append({"code": "needs_evidence", "missing": "tool_result"})
                mocked = bool(crec_extra.get("mocked")) or crec.get("actual_model") == "mock"
                packed = int(extra.get("packed_source_chars") or crec_extra.get("packed_source_chars") or 0)
                source0_mock = mocked and packed <= 0
                external_review = bool(payload.get("external_subagent")) or bool(
                    crec_extra.get("external_subagent")
                )
                if include_source and external_review and not source0_mock:
                    # 2026-09-21 ruling: external reviewer reads the packet per the task
                    # contract and self-reports; settle the reservation mechanically.
                    exposures = list(crec.get("source_exposures") or [])
                    _release_matching_reservation(
                        exposures, packet_hash=crec.get("packet_hash"), call_id=str(bound_call)
                    )
                    event_id = f"{bound_call}:external_packet_read"
                    if packed > 0 and not any(e.get("event_id") == event_id for e in exposures):
                        exposures.append(
                            {
                                "event_id": event_id,
                                "role_session_id": str(bound_call),
                                "event_kind": "tool_read",
                                "evidence_ref": "external_review_self_report",
                                "source_chars": packed,
                                "counted_as": COUNTED_KNOWN,
                                "reason": "external reviewer read the packet per task contract",
                            }
                        )
                    crec["source_exposures"] = exposures
                    ledger["calls"][bound_call] = crec
                    sync_budget(ledger)
                evidence_gap = any(item.get("code") == "needs_evidence" for item in review_residuals)
                history = list(crec_extra.get("review_evidence_history") or [])
                if evidence_gap:
                    if crec_extra.get("disposition") not in {None, "needs_evidence"} or already_committed:
                        history.append(
                            {
                                "previous_disposition": crec_extra.get("disposition"),
                                "previous_state": crec.get("state"),
                                "cleared": [],
                                "reason": "review_evidence_incomplete",
                            }
                        )
                    crec_extra["review_evidence_history"] = history
                    crec_extra["disposition"] = "needs_evidence"
                    crec_extra["review_evidence_incomplete"] = True
                else:
                    if crec_extra.get("review_evidence_incomplete") or crec_extra.get("disposition") == "needs_evidence":
                        history.append(
                            {
                                "cleared": ["needs_evidence", "review_evidence_incomplete"],
                                "previous_disposition": crec_extra.get("disposition"),
                            }
                        )
                        crec_extra["review_evidence_history"] = history
                    crec_extra["review_evidence_incomplete"] = False
                    crec_extra["disposition"] = "accepted"
                    crec["state"] = "imported"
                crec["extra"] = crec_extra
                ledger["calls"][bound_call] = crec
            review_payload = dict(payload)
            review_payload["residual"] = review_residuals
            submit_review(
                ledger,
                task_id=task_id,
                owner=str(envelope["owner"]),
                generation=int(envelope["generation"]),
                payload=review_payload,
                expected_input_hash=str(envelope["input_hash"]),
                expected_call_id=envelope.get("call_id") or extra.get("call_id"),
            )
            if str(payload.get("verdict") or "") == "revision_required":
                _invalidate_reviewed(ledger, payload)
        elif task.kind in {"detail", "merge"}:
            items = payload.get("details")
            if not isinstance(items, list):
                raise RunnerError("detail import requires details array")
            packet_map = load_packet_map(ledger)
            submit_details(
                ledger,
                task_id=task_id,
                owner=str(envelope["owner"]),
                generation=int(envelope["generation"]),
                items=items,
                packet=packet_map.get(task.packet_id or ""),
                call_id=None,
            )
            _bind_external_call(ledger, task, envelope, payload, kind="detail")
        elif task.kind == "group_body":
            body = payload.get("body")
            group_id = (task.extra or {}).get("group_id") or (task.input_ids[0] if task.input_ids else None)
            groups = ledger.setdefault("groups", {})
            weighted_errors = _weighted_group_body_errors(ledger, payload, group_id=group_id)
            if not isinstance(body, str) or not body.strip() or group_id not in groups:
                raise RunnerError("group_body import requires nonempty body for the claimed group")
            if task.state == "committed":
                return ledger
            if weighted_errors:
                task_record = TaskRecord.from_dict(ledger["tasks"][task_id])
                task_record.state = "needs_repair"
                task_record.residual = weighted_errors
                ledger["tasks"][task_id] = task_record.to_dict()
                _bind_external_call(ledger, task, envelope, payload, kind="group_body")
                return ledger
            groups[group_id]["body"] = body.strip()
            group_extra = dict(groups[group_id].get("extra") or {})
            if (ledger.get("documentation_policy") or {}).get("version") == "weighted-v1":
                group_extra["evidence_summary"] = narrative_evidence_summary(ledger, groups[group_id], body)
            group_extra.pop("stale", None)
            group_extra.pop("body_stale", None)
            groups[group_id]["extra"] = group_extra
            task_record = TaskRecord.from_dict(ledger["tasks"][task_id])
            if task_record.owner != str(envelope["owner"]) or task_record.generation != int(envelope["generation"]):
                raise StaleWriteError("group_body import envelope does not match the active lease")
            task_record.state = "committed"
            task_record.output_refs = [group_id]
            task_record.residual = []
            ledger["tasks"][task_id] = task_record.to_dict()
            invalidate_group_bodies(ledger, ancestor_group_ids(ledger, group_id))
            _bind_external_call(ledger, task, envelope, payload, kind="group_body")
        else:
            raise RunnerError(f"cannot import into kind {task.kind}")
        return ledger

    try:
        ledger = store.mutate(mutate)
    except StaleWriteError as exc:
        raise RunnerError(str(exc)) from exc
    task = TaskRecord.from_dict(ledger["tasks"][task_id])
    return {"task_id": task_id, "state": task.state, "residual": task.residual, "output_refs": task.output_refs}


def refresh(run_dir: Path, repo: Path) -> dict[str, Any]:
    store = LedgerStore(run_dir)
    if (store.open().get("documentation_policy") or {}).get("version") == "module-first-v2":
        raise RunnerError(
            "module-first-v2 refresh requires a new frozen run; existing plan and reviewed explanations were kept"
        )
    new_inventory = build_inventory(repo.resolve())
    try:
        new_packets = pack_inventory(new_inventory, repo=repo.resolve(), window_chars=packet_window())
    except PacketSourceError as exc:
        raise RunnerError(str(exc)) from exc
    new_graph = build_graph(new_inventory)

    def mutate(ledger: dict[str, Any]) -> dict[str, Any]:
        if (
            (ledger.get("documentation_policy") or {}).get("version") == "weighted-v1"
            and Path(str(ledger.get("repo_root") or "")).resolve() != repo.resolve()
        ):
            raise RunnerError("weighted refresh repo does not match the frozen ledger repo_root")
        old_inv = ledger.get("inventory") or {}
        old_files = old_inv.get("files") or {}
        old_symbols = old_inv.get("symbols") or {}
        changed_files = []
        for path, record in new_inventory.files.items():
            previous = old_files.get(path) or {}
            if previous.get("content_hash") != record.content_hash:
                changed_files.append(path)
        def identity_key(record: dict) -> tuple[str, str, str]:
            return (
                str(record.get("path") or ""),
                str(record.get("kind") or ""),
                str(record.get("qualified_name") or ""),
            )

        old_by_key = {identity_key(record): sid for sid, record in old_symbols.items()}
        new_by_key = {
            identity_key(symbol.to_dict()): sid
            for sid, symbol in new_inventory.symbols.items()
        }
        id_map = {
            old_id: new_by_key[key]
            for key, old_id in old_by_key.items()
            if key in new_by_key
        }
        deleted_symbols = {
            old_id
            for old_id, record in old_symbols.items()
            if identity_key(record) not in new_by_key
        }
        new_symbol_ids = {
            new_id
            for new_id, symbol in new_inventory.symbols.items()
            if identity_key(symbol.to_dict()) not in old_by_key
        }
        changed_symbols = set()
        for old_id, new_id in id_map.items():
            previous = old_symbols[old_id]
            symbol = new_inventory.symbols[new_id]
            old_hash = (previous.get("extra") or {}).get("exclusive_sha256")
            new_hash = symbol.extra.get("exclusive_sha256")
            if old_hash != new_hash:
                changed_symbols.add(new_id)
        weighted = (ledger.get("documentation_policy") or {}).get("version") == "weighted-v1"
        policy_changed_symbols: set[str] = set()
        symbol_policies: dict[str, dict[str, Any]] | None = None
        refreshed_documentation: dict[str, Any] | None = None
        if weighted:
            from cbe.documentation_budget import DocumentationBudgetInfeasible, allocate_symbol_tokens
            from cbe.render import estimate_weighted_navigation_tokens
            from cbe.token_budget import count_source_tokens
            from cbe.weighting import REQUIRED_FIELDS_BY_TIER, assign_detail_priorities

            old_documentation = ledger["documentation_policy"]
            old_policies = old_documentation.get("symbols") or {}
            symbol_policies = assign_detail_priorities(new_inventory, new_graph, repo.resolve())
            if set(symbol_policies) != set(new_inventory.symbols):
                raise RunnerError("weighted refresh must assign every frozen symbol exactly once")
            tier_order = {"brief": 0, "standard": 1, "deep": 2}
            for old_id, new_id in id_map.items():
                previous = old_symbols[old_id]
                current = new_inventory.symbols[new_id]
                old_hash = (previous.get("extra") or {}).get("exclusive_sha256")
                if not old_hash or old_hash != current.extra.get("exclusive_sha256"):
                    continue
                prior = old_policies.get(old_id)
                if not isinstance(prior, dict) or not prior.get("promotion_history"):
                    continue
                policy = symbol_policies[new_id]
                prior_tier = str(prior.get("tier") or "")
                if prior_tier not in tier_order or policy.get("tier") not in tier_order:
                    raise RunnerError(f"invalid promoted tier for {old_id}")
                if tier_order[prior_tier] > tier_order[str(policy["tier"])]:
                    policy["tier"] = prior_tier
                    policy["required_fields"] = list(REQUIRED_FIELDS_BY_TIER[prior_tier])
                policy["promotion_history"] = list(prior["promotion_history"])
                policy["signals"] = sorted(
                    set(policy.get("signals") or [])
                    | {signal for signal in (prior.get("signals") or []) if str(signal).startswith("promotion:")}
                )

            source_tokens = count_source_tokens(new_inventory, repo.resolve())
            group_limit = max(12, min(400, (len(new_inventory.files) * 3 + 3) // 4))
            if len(ledger.get("groups") or {}) > group_limit:
                raise DocumentationBudgetInfeasible(
                    f"existing {len(ledger.get('groups') or {})} groups exceed refreshed group_limit {group_limit}"
                )
            refreshed_documentation = {
                "version": "weighted-v1",
                "tokenizer": "o200k_base",
                "source_tokens": source_tokens,
                "published_cap_tokens": source_tokens // 2,
                "group_limit": group_limit,
                "symbols": symbol_policies,
            }
            preflight_ledger = dict(ledger)
            preflight_ledger["repo_root"] = new_inventory.repo_root
            preflight_ledger["inventory"] = new_inventory.to_dict()
            preflight_ledger["graph"] = new_graph.to_dict()
            preflight_ledger["groups"] = {}  # Group pages are charged to the group reserve below.
            preflight_ledger["documentation_policy"] = refreshed_documentation
            preflight = estimate_weighted_navigation_tokens(preflight_ledger)
            allocation = allocate_symbol_tokens(
                symbol_policies,
                source_tokens=source_tokens,
                navigation_tokens=int(preflight["navigation_tokens"]),
            )
            refreshed_documentation.update(allocation)
            refreshed_documentation["group_body_content_tokens"] = max(
                24, allocation["group_reserve_tokens"] // (3 * group_limit)
            )
            refreshed_documentation["repair_reserve_initial_tokens"] = allocation["repair_reserve_tokens"]
            refreshed_documentation["repair_reserve_spent_tokens"] = 0
            for old_id, new_id in id_map.items():
                if old_policies.get(old_id) != symbol_policies[new_id]:
                    policy_changed_symbols.add(new_id)
            ledger["documentation_policy"] = refreshed_documentation

        stale_details = set(changed_symbols) | deleted_symbols | policy_changed_symbols
        if weighted:
            # A function may read a module constant while its own exclusive
            # bytes stay unchanged. Revisit all symbols in changed files so a
            # syntactically stable body cannot keep a stale behavioral claim.
            stale_details.update(
                sid for sid, symbol in new_inventory.symbols.items()
                if symbol.path in changed_files
            )
        details = ledger.get("details") or {}
        remapped: dict[str, dict] = {}
        for old_id, detail in list(details.items()):
            new_id = id_map.get(old_id, old_id)
            detail = dict(detail)
            detail["symbol_id"] = new_id
            if weighted:
                provenance = dict(detail.get("provenance") or {})
                canonical_id = provenance.get("canonical_symbol_id")
                if canonical_id in id_map:
                    provenance["canonical_symbol_id"] = id_map[canonical_id]
                if new_id != old_id:
                    previous_fragment = provenance.pop("fragment_id", None)
                    if previous_fragment:
                        provenance["prior_fragment_id"] = previous_fragment
                detail["provenance"] = provenance
            remapped[new_id] = detail
        details.clear()
        details.update(remapped)
        old_edges = list((ledger.get("graph") or {}).get("edges") or [])
        remapped_old_edges = []
        for edge in old_edges:
            item = dict(edge)
            if item.get("subject_id") in id_map:
                item["subject_id"] = id_map[item["subject_id"]]
            if item.get("target_id") in id_map:
                item["target_id"] = id_map[item["target_id"]]
            remapped_old_edges.append(item)
        new_edges = list(new_graph.to_dict().get("edges") or [])
        changed = True
        while changed:
            changed = False
            for symbol_id, detail in details.items():
                deps = detail.get("dependencies") or []
                if not isinstance(deps, list):
                    continue
                for dep in deps:
                    dep_id = dep if isinstance(dep, str) else (dep.get("symbol_id") if isinstance(dep, dict) else None)
                    dep_id = id_map.get(dep_id, dep_id) if dep_id else None
                    if dep_id in stale_details and symbol_id not in stale_details:
                        stale_details.add(symbol_id)
                        changed = True
            for caller in callers_of(remapped_old_edges, stale_details) | callers_of(new_edges, stale_details):
                mapped = id_map.get(caller, caller)
                if mapped not in stale_details:
                    stale_details.add(mapped)
                    changed = True
            for caller in callers_of(old_edges, deleted_symbols):
                mapped = id_map.get(caller, caller)
                if mapped not in stale_details:
                    stale_details.add(mapped)
                    changed = True
        for symbol_id in list(stale_details):
            if symbol_id in details:
                if weighted:
                    details[symbol_id] = mark_detail_historical(
                        details[symbol_id], reason="weighted_refresh_source_or_policy_changed"
                    )
                    details[symbol_id]["provenance"]["stale"] = True
                else:
                    details[symbol_id]["provenance"] = dict(details[symbol_id].get("provenance") or {})
                    details[symbol_id]["provenance"]["stale"] = True
        if weighted:
            for detail_id, detail in list(details.items()):
                if detail_id in stale_details:
                    continue
                canonical_id = (detail.get("provenance") or {}).get("canonical_symbol_id")
                if canonical_id in stale_details:
                    details[detail_id] = mark_detail_historical(
                        detail, reason="weighted_refresh_canonical_changed"
                    )
                    details[detail_id]["provenance"]["stale"] = True
        groups = ledger.get("groups") or {}
        affected_groups: list[str] = []
        for group_id, group in groups.items():
            old_members = list(group.get("member_ids") or [])
            group["member_ids"] = [id_map.get(item, item) for item in (group.get("member_ids") or [])]
            group["children"] = [id_map.get(item, item) for item in (group.get("children") or [])]
            if weighted:
                group["entry_routes"] = [id_map.get(item, item) for item in (group.get("entry_routes") or [])]
                for relation in group.get("relations") or []:
                    if not isinstance(relation, dict):
                        continue
                    for key in ("subject_id", "target_id", "source_id", "destination_id"):
                        if relation.get(key) in id_map:
                            relation[key] = id_map[relation[key]]
            members = set(group.get("member_ids") or []) | set(group.get("children") or [])
            quota_invalid = (
                weighted
                and (group.get("extra") or {}).get("presentation", "narrative") == "narrative"
                and bool(str(group.get("body") or "").strip())
                and (
                    not isinstance((group.get("extra") or {}).get("evidence_summary"), dict)
                    or bool(_weighted_group_body_errors(ledger, {"body": group.get("body")}))
                )
            )
            if members & stale_details or (weighted and group["member_ids"] != old_members) or quota_invalid:
                group.setdefault("extra", {})["stale"] = True
                affected_groups.append(group_id)
                affected_groups.extend(ancestor_group_ids(ledger, group_id))
        if affected_groups:
            unique_groups = []
            seen_g: set[str] = set()
            for group_id in affected_groups:
                if group_id in seen_g:
                    continue
                seen_g.add(group_id)
                if (groups.get(group_id) or {}).get("extra", {}).get("replaced_by"):
                    continue
                unique_groups.append(group_id)
            if unique_groups:
                invalidate_group_bodies(ledger, unique_groups)
        affected_group_ids = set(affected_groups)
        if weighted:
            # Re-keying group claims below must see the new graph and revision.
            ledger["graph"] = new_graph.to_dict()
            ledger["source_revision"] = new_inventory.source_revision
        tasks = ledger.setdefault("tasks", {})
        current_symbol_ids = set(new_inventory.symbols)
        new_packet_ids = {packet.packet_id for packet in new_packets.packets}
        for task in tasks.values():
            extra = dict(task.get("extra") or {})
            inputs = set(task.get("input_ids") or [])
            if inputs & stale_details:
                if task.get("state") == "committed":
                    task["state"] = "stale"
                    if task.get("kind") == "group":
                        extra["superseded"] = True
                        extra["superseded_reason"] = "group_inputs_invalidated_after_refresh"
                        extra["replaced_by"] = extra.get("replaced_by")
                        task["extra"] = extra
                elif task.get("kind") == "group" and task.get("state") == "leased":
                    extra["superseded"] = True
                    extra["superseded_reason"] = "claim_input_expired_after_refresh"
                    extra["tombstone_reason"] = "claim_input_expired_after_refresh"
                    extra["replaced_by"] = extra.get("replaced_by")
                    task["extra"] = extra
                    task["state"] = "stale"
            if task.get("kind") == "detail":
                packet_id = task.get("packet_id")
                if packet_id and packet_id not in new_packet_ids:
                    extra["tombstone"] = True
                    extra["tombstone_reason"] = "packet_removed_after_refresh"
                    task["extra"] = extra
                    if task.get("state") in {"pending", "needs_repair", "leased"}:
                        task["state"] = "stale"
                elif inputs and not (inputs & current_symbol_ids) and not any(
                    ident in current_symbol_ids for ident in inputs
                ):
                    if inputs <= deleted_symbols or not (inputs & set(id_map.values())):
                        extra["tombstone"] = True
                        extra["tombstone_reason"] = "symbol_deleted"
                        task["extra"] = extra
                        if task.get("state") in {"pending", "needs_repair", "leased"}:
                            task["state"] = "stale"
            if task.get("kind") == "group_body":
                group_id = extra.get("group_id") or (task.get("input_ids") or [None])[0]
                group = groups.get(group_id or "")
                if isinstance(group, dict) and (group.get("extra") or {}).get("replaced_by"):
                    extra["superseded"] = True
                    extra["replaced_by"] = (group.get("extra") or {}).get("replaced_by")
                    task["extra"] = extra
                    if task.get("state") in {"pending", "needs_repair"}:
                        task["state"] = "stale"
        record_tasks: dict[str, TaskRecord] = {
            key: TaskRecord.from_dict(value) if not isinstance(value, TaskRecord) else value
            for key, value in tasks.items()
        }
        if weighted:
            assert symbol_policies is not None and refreshed_documentation is not None
            rebuilt_tasks: dict[str, TaskRecord] = {}
            for packet in new_packets.packets:
                _register_packet_tasks(rebuilt_tasks, packet, symbol_policies=symbol_policies)
            _register_merge_tasks(
                rebuilt_tasks, list(new_packets.packets), symbol_policies=symbol_policies
            )
            affected_packet_ids = {
                packet.packet_id
                for packet in new_packets.packets
                if set(packet.symbol_ids) & stale_details
                or any(fragment.symbol_id in stale_details for fragment in packet.fragments)
            }
            for task_id, old_task in list(record_tasks.items()):
                if old_task.kind not in {"detail", "merge"} or task_id in rebuilt_tasks:
                    continue
                old_task.generation += 1
                old_task.state = "stale"
                old_task.owner = None
                old_task.owner_pid = None
                old_task.lease_until = None
                extra = dict(old_task.extra or {})
                extra["tombstone"] = True
                extra["tombstone_reason"] = "task_removed_after_weighted_refresh"
                old_task.extra = extra
                record_tasks[task_id] = old_task
            for task_id, built in rebuilt_tasks.items():
                existing = record_tasks.get(task_id)
                if existing is None:
                    record_tasks[task_id] = built
                    continue
                affected = (
                    built.packet_id in affected_packet_ids if built.kind == "detail"
                    else bool(set(built.input_ids) & stale_details)
                )
                changed_contract = (
                    existing.input_ids != built.input_ids
                    or existing.input_hash != built.input_hash
                    or existing.packet_id != built.packet_id
                    or existing.state == "stale"
                    or affected
                )
                if not changed_contract:
                    existing.output_refs = [id_map.get(item, item) for item in existing.output_refs]
                    record_tasks[task_id] = existing
                    continue
                built.generation = existing.generation + 1
                built.state = "pending"
                record_tasks[task_id] = built
            for task_id, task in list(record_tasks.items()):
                if task.kind == "group":
                    remapped_inputs = [id_map.get(item, item) for item in task.input_ids]
                    changed_claim = (
                        remapped_inputs != task.input_ids
                        or bool(set(remapped_inputs) & stale_details)
                        or bool(set(task.output_refs) & affected_group_ids)
                        or ledger.get("source_revision") != old_inv.get("source_revision")
                    )
                    if changed_claim:
                        task.generation += 1
                        task.state = "stale"
                        task.owner = None
                        task.owner_pid = None
                        task.lease_until = None
                        task.input_ids = remapped_inputs
                        extra = dict(task.extra or {})
                        extra["superseded"] = True
                        extra["superseded_reason"] = "weighted_refresh_changed_claim_source"
                        task.extra = extra
                        if all(item in details or item in groups for item in remapped_inputs):
                            task.input_hash = group_claim_input_hash(ledger, remapped_inputs)
                        record_tasks[task_id] = task
                elif task.kind == "group_body":
                    group_id = (task.extra or {}).get("group_id") or (task.input_ids[0] if task.input_ids else None)
                    if group_id not in affected_group_ids:
                        continue
                    if (groups.get(group_id) or {}).get("extra", {}).get("presentation") == "navigation":
                        task.state = "stale"
                        extra = dict(task.extra or {})
                        extra["superseded"] = True
                        task.extra = extra
                    else:
                        task.state = "pending"
                        if isinstance(groups.get(group_id), dict):
                            task.input_hash = group_body_input_hash(ledger, groups[group_id])
                    task.generation += 1
                    task.owner = None
                    task.owner_pid = None
                    task.lease_until = None
                    record_tasks[task_id] = task
                elif task.kind == "review":
                    remapped_inputs = [id_map.get(item, item) for item in task.input_ids]
                    if (
                        remapped_inputs != task.input_ids
                        or bool(set(remapped_inputs) & stale_details)
                        or bool(set(remapped_inputs) & affected_group_ids)
                        or ledger.get("source_revision") != old_inv.get("source_revision")
                    ):
                        task.generation += 1
                        task.state = "stale"
                        task.owner = None
                        task.owner_pid = None
                        task.lease_until = None
                        task.input_ids = remapped_inputs
                        task.input_hash = sha256_text(json.dumps({
                            "targets": remapped_inputs,
                            "include_source": bool((task.extra or {}).get("include_source")),
                            "rev": ledger.get("source_revision"),
                        }, sort_keys=True))
                        extra = dict(task.extra or {})
                        extra["superseded"] = True
                        extra["superseded_reason"] = "weighted_refresh_changed_review_source"
                        task.extra = extra
                        record_tasks[task_id] = task
        else:
            for packet in new_packets.packets:
                task_id = f"task:detail:{packet.packet_id}"
                built = build_detail_task(packet)
                if task_id not in record_tasks:
                    record_tasks[task_id] = built
                elif record_tasks[task_id].state == "stale":
                    record_tasks[task_id].state = "pending"
                    record_tasks[task_id].input_ids = list(built.input_ids)
                    record_tasks[task_id].input_hash = built.input_hash
                    record_tasks[task_id].extra = dict(built.extra or {})
            _register_merge_tasks(record_tasks, list(new_packets.packets))
        for key, value in record_tasks.items():
            tasks[key] = value.to_dict()
        ledger["inventory"] = new_inventory.to_dict()
        ledger["packets"] = new_packets.to_dict()
        ledger["graph"] = new_graph.to_dict()
        ledger["source_revision"] = new_inventory.source_revision
        ledger["git_head"] = new_inventory.git_head
        ledger.setdefault("budget", {})["s_chars"] = new_inventory.s_chars
        if weighted:
            ledger["budget"]["cap_chars"] = 2 * new_inventory.s_chars
        ledger.setdefault("refresh_log", []).append(
            {
                "at": iso(),
                "changed_files": changed_files,
                "deleted_symbols": sorted(deleted_symbols)[:50],
                "new_symbols": sorted(new_symbol_ids)[:50],
                "stale_details": sorted(stale_details)[:50],
                **({
                    "policy_changed_symbols": sorted(policy_changed_symbols)[:50],
                    "source_tokens": refreshed_documentation["source_tokens"],
                    "published_cap_tokens": refreshed_documentation["published_cap_tokens"],
                } if weighted and refreshed_documentation is not None else {}),
            }
        )
        return ledger

    ledger = store.mutate(mutate)
    return {
        "source_revision": ledger.get("source_revision"),
        "refresh_log": (ledger.get("refresh_log") or [])[-1],
        "status": derived_status(ledger),
    }


def _design_hint(run_dir: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    status = derived_status(ledger)
    ready = status.get("design_ready") or {}
    return {
        "claim": f"python -m cbe claim --run-dir {run_dir} --kind group --input-ids-file ABS.json",
        "frontier": f"python -m cbe claim --run-dir {run_dir} --kind group",
        "import": f"python -m cbe import-result --run-dir {run_dir} --task-id <id> --result <file>",
        "uncovered_symbol_count": ready.get("uncovered_symbol_count"),
        "ungrouped_fresh_detail_count": ready.get("ungrouped_fresh_detail_count"),
        "note": "Runner will not invent architecture groups. Import a plan with the claim envelope to continue layers.",
    }


def query(run_dir: Path, ident: str) -> dict[str, Any]:
    ledger = LedgerStore(run_dir).open()
    module_first = (ledger.get("documentation_policy") or {}).get("version") == "module-first-v2"
    if module_first:
        from cbe.module_workflow import accepted_package

        modules = accepted_package(ledger)["modules"] if ledger.get("module_workflow_version") else {}
        if ident in modules:
            return {"type": "module_explanation", "module_id": ident,
                    "explanation_state": "accepted", "record": modules[ident]}
        symbols = (ledger.get("inventory") or {}).get("symbols") or {}
        if ident in symbols:
            from cbe.module_first_render import _source_line_numbers
            from cbe.callable_contracts import contracts_for, reader_references

            syntax = contracts_for(ledger, [ident]).get(ident)
            references = reader_references(ledger, [ident]).get(ident)

            plan = json.loads((Path(run_dir) / "module_plan.json").read_text(encoding="utf-8"))
            owner = next((gid for gid, group in plan["groups"].items()
                          if ident in (group.get("member_ids") or [])), None)
            source_path = symbols[ident]["path"]
            source_line = _source_line_numbers(ledger, {ident: symbols[ident]})[ident]
            detail = (ledger.get("details") or {}).get(ident)
            review = (ledger.get("fact_reviews") or {}).get(ident) or {}
            state = review.get("state") or "catalogued"
            current = isinstance(detail, dict) and review.get("content_sha256") == sha256_text(
                json.dumps(detail, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            )
            if current and state in {"source_checked", "batch_accepted", "syntax_evidenced", "mechanically_validated"}:
                from cbe.syntax_facts import reader_facts
                from cbe.static_literals import accepted_numeric_literals, accepted_return_keys
                from cbe.behavior_contracts import accepted_projection, reader_detail

                return {"type": "fact", "symbol_id": ident, "module_id": owner,
                        **({"behavior_contract": accepted_projection(ledger, ident)}
                           if (detail.get("provenance") or {}).get("behavior_contract") else {}),
                        **({"callable_syntax": syntax} if syntax else {}),
                        **({"syntax_references": references} if references else {}),
                        "source_path": source_path, "source_line": source_line,
                        "explanation_state": state, "individually_source_checked": state == "source_checked",
                        "source_literals": accepted_numeric_literals(ledger).get(ident, []),
                        **({"syntax_facts": facts} if (facts := reader_facts(ledger, ident)) else {}),
                        "return_keys": accepted_return_keys(ledger).get(ident),
                        "record": reader_detail(detail)}
            return {"type": "symbol", "module_id": owner,
                    **({"callable_syntax": syntax} if syntax else {}),
                    **({"syntax_references": references} if references else {}),
                    "source_path": source_path, "source_line": source_line,
                    "explanation_state": state if current else "catalogued",
                    "record": symbols[ident]}
    if ident in (ledger.get("details") or {}):
        from cbe.callable_contracts import contracts_for
        syntax = contracts_for(ledger, [ident]).get(ident)
        return {"type": "detail", "record": ledger["details"][ident],
                **({"callable_syntax": syntax} if syntax else {})}
    if ident in (ledger.get("groups") or {}):
        return {"type": "group", "record": ledger["groups"][ident]}
    if ident in (ledger.get("tasks") or {}):
        return {"type": "task", "record": ledger["tasks"][ident]}
    if ident in (ledger.get("calls") or {}):
        return {"type": "call", "record": ledger["calls"][ident]}
    if ident in (ledger.get("reviews") or {}):
        return {"type": "review", "record": ledger["reviews"][ident]}
    symbols = (ledger.get("inventory") or {}).get("symbols") or {}
    if ident in symbols:
        from cbe.callable_contracts import contracts_for
        syntax = contracts_for(ledger, [ident]).get(ident)
        return {"type": "symbol", "record": symbols[ident],
                **({"callable_syntax": syntax} if syntax else {})}
    raise RunnerError(f"id not found: {ident}")
