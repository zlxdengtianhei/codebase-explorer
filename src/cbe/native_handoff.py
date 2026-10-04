"""Host-owned subagent handoff over the existing CBE claim and import ledger.

CBE prepares work and records observable host events. It never starts a model,
reads credentials, or treats a requested model as an observed one.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from cbe import module_facts, module_workflow, system_workflow
from cbe.accounting import COUNTED_KNOWN, COUNTED_UPPER, overall_token_budget, sync_budget
from cbe.store import LedgerStore, LeaseError, StaleWriteError, atomic_write_bytes, iso, mark_call
from cbe.token_budget import count_text_tokens

SCHEMA = "native_handoff_v1"
OPEN_STATES = {"pending", "needs_repair"}
NATIVE_INPUT_TARGET = 8000


class NativeChildHandleConflict(ValueError):
    """An already recorded status cannot be rebound to another child."""
PACKET_END = "END_CBE_NATIVE_PACKET"


class _ResultFormatError(ValueError):
    """A completed child's business output is retryable; bindings are untouched."""


def _check_result_shape(payload: dict, task_id: str) -> None:
    if task_id.startswith("task:fact_author:") and not isinstance(payload.get("items"), list):
        raise _ResultFormatError("fact result requires items array")
    if task_id.startswith("task:fact_author:"):
        for item in payload["items"]:
            if not isinstance(item, dict):
                raise _ResultFormatError("fact item must be an object")
            if not isinstance(item.get("behavior", item.get("concise_behavior")), str):
                raise _ResultFormatError("fact item requires behavior string")
            if not isinstance(item.get("source_refs"), list):
                raise _ResultFormatError("fact item requires source_refs array")
    if "_review" in task_id:
        verdicts = {"accepted", "revision_required"}
        if task_id.startswith("task:fact_review:"):
            verdicts.add("needs_context")
        if payload.get("verdict") not in verdicts:
            raise _ResultFormatError("review result requires a valid verdict")
        if not isinstance(payload.get("findings"), list):
            raise _ResultFormatError("review result requires findings array")
        if task_id.startswith("task:fact_review:") and not isinstance(payload.get("checked_ids"), list):
            raise _ResultFormatError("fact review requires checked_ids array")
    if task_id.startswith("task:module_author:"):
        content = payload.get("content", payload)
        if not isinstance(content, dict) or any(key not in content for key in
            ("summary", "flow", "uncertainties", "key_symbols", "source_refs")):
            raise _ResultFormatError("module result requires summary, flow, uncertainties, key_symbols and source_refs")
    if task_id == "task:system_author" and any(not isinstance(payload.get(key), str) for key in
        ("overview", "entry_points", "lifecycle", "data_flow", "uncertainties")):
        raise _ResultFormatError("system result requires overview, entry_points, lifecycle, data_flow and uncertainties strings")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() and path.read_bytes() != data:
        raise StaleWriteError(f"native evidence already differs: {path}")
    atomic_write_bytes(path, data)


def _canonical_host(host: Any) -> Any:
    if not isinstance(host, str):
        return host
    value = host.strip().lower().replace("_", "-")
    return {"claude": "claude-code", "codex-app": "codex", "codex-cli": "codex"}.get(value, value)


def _task_scope(task_id: str) -> str:
    if task_id.startswith("task:fact_"):
        return "fact"
    if task_id.startswith("task:module_"):
        return "module"
    if task_id.startswith("task:system_"):
        return "system"
    raise ValueError(f"unsupported native task: {task_id}")


READ_LINE_LIMIT = 2000  # OpenCode Read uses JS UTF-16 code units, not code points.


def _read_line_units(text: str) -> int:
    return len(text.encode('utf-16-le', errors='surrogatepass')) // 2


def _display_json(value: Any) -> str:
    compact = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    if _read_line_units(compact) <= READ_LINE_LIMIT:
        return compact
    # Standard JSON whitespace preserves every value and schema. A single
    # long string cannot be split without changing it; the file-wide warning
    # below directs the consumer to its already-authorized complete reader.
    return json.dumps(value, ensure_ascii=False, indent=2)


def _readable_instruction(text: str) -> str:
    lines = []
    for line in text.split('\n'):
        if _read_line_units(line) <= READ_LINE_LIMIT:
            lines.append(line)
            continue
        words, units = [], 0
        for word in line.split():
            size = _read_line_units(word)
            if words and units + 1 + size > READ_LINE_LIMIT:
                lines.append(' '.join(words)); words, units = [], 0
            units += size + (1 if words else 0)
            words.append(word)
        lines.append(' '.join(words))
    return '\n'.join(lines)


def _dispatch_prompt(packet: dict[str, Any], scope: str) -> bytes:
    instruction = (
        "One-use dispatch: pair this fresh ready item's call_id/task_id/generation/prompt_path. "
        "Cached ready is not retry; ledger active means protected calls, not host running children. "
        "Fresh CBE subagent: use only this frozen task. Return final business JSON; "
        "the controller supplies envelope/hash/evidence/model/usage, so omit them "
        "even if legacy instructions request them. Read the file once through "
        "END_CBE_NATIVE_PACKET; legacy no-tools applies after this read. Continue "
        "only missing ranges after truncation, never restart. Then return immediately; "
        "selected result-file fallback means write once and return its path. No separate "
        "messages or verification files. Name exact missing evidence/unsupported claims. "
        "Permission denial or missing approval client: stop the affected action and "
        "return terminal host_blocked with exact error, tool/action, "
        "call/task, artifacts and dispatch/write status or unknown. This report is not business JSON. "
        "Do not repeat the denied action, spawn a diagnostic child, change sandbox settings "
        "or paths to bypass permission. The parent resolves "
        "the official permission channel before retry."
    )
    if scope == "fact":
        assignments = module_facts.compact_assignments(packet["assignments"])
        required = ("Every assigned ID must be returned with symbol_id, source_refs, short behavior and "
                    "behavior_contract containing claims, claim_refs, local_view_gaps and current_unresolved. "
                    "Put source-backed maintenance conditions/effects/failures in owned claims; behavior is the "
                    "short role and unique delta. Do not return only a visible prefix of assignments.\n"
                    if packet.get("behavior_contract_required") else "")
        parts = [instruction, required + _readable_instruction(packet["instruction"]),
                 "Assignments (canonical ID equals symbol_id unless explicit):\n" + _display_json(assignments),
                 "Frozen source:\n" + packet["source"]]
        if packet.get("draft") is not None:
            parts.append("Assigned draft facts:\n" + _display_json(
                packet.get("draft_projection") or packet["draft"]))
        for key, label in (("repair_findings", "Prior review findings"),
                           ("composition_prior", "Prior source-bound obligations (retain original acceptance states)"),
                           ("composition_prior_states", "Original obligation acceptance states"),
                           ("composition_findings", "Original unresolved findings whose mappings need independent review"),
                           ("accepted_dependencies", "Bound accepted dependency facts (static links do not prove runtime binding)"),
                           ("review_question", "Review question"),
                           ("context_limits", "Context limits")):
            if packet.get(key):
                value = packet[key]
                parts.append(label + ":\n" + (
                    _readable_instruction(value) if isinstance(value, str) else _display_json(value)))
    elif scope == "module":
        parts = [instruction, packet["prompt"]]
        if str(packet.get("envelope", {}).get("task_id", "")).startswith("task:module_author:"):
            parts.append("Module author business content schema: " + module_workflow.MODULE_CONTENT_SCHEMA
                         + ". Return these five business keys (no envelope). summary, flow and uncertainties "
                           "must be strings, never arrays or objects; preserve all uncertainty clauses in the string.")
        if packet.get("validation_findings"):
            parts.append("Current validation findings:\n" + _display_json(packet["validation_findings"]))
    else:
        parts = [instruction, _readable_instruction(packet["instruction"]),
                 "Accepted module evidence:\n" + packet["source"]]
        if packet.get("repair_findings"):
            parts.append("Current validation findings:\n" + _display_json(packet["repair_findings"]))
    rendered = "\n\n".join(parts)
    long_lines = [(number, line) for number, line in enumerate(rendered.split('\n'), 1)
                  if _read_line_units(line) > READ_LINE_LIMIT]
    if long_lines:
        # Preserve source and JSON string values, rather than invent another
        # representation. Reaching END in Read does not prove these lines
        # were received in full.
        rendered = (f'Read long-line boundary: {len(long_lines)} original lines exceed the observed '
                    f'{READ_LINE_LIMIT}-UTF-16-code-unit Read limit; Read shows only their prefixes. '
                    'Source and JSON values remain unchanged below. Use the existing authorized '
                    'complete-file reader (for example Python print of this prompt), and verify '
                    'its output is not truncated. A permission denial is host_blocked; do not bypass '
                    'it with another tool. Do not treat a Read prefix as complete source evidence.\n\n' + rendered)
    return (rendered + "\n\n" + PACKET_END + "\n").encode("utf-8")


def _item(run_dir: Path, task_id: str, call: dict[str, Any]) -> dict[str, Any]:
    extra = call.get("extra") or {}
    handoff = extra.get("native_handoff") or {}
    path = Path(handoff["dispatch_prompt_path"])
    return {
        "call_id": call["call_id"], "task_id": task_id,
        "role": (task_id.split(":", 2)[1]),
        "dispatch_prompt_path": str(path),
        "result_path": str(run_dir / "raw" / f"{call['call_id']}.json"),
        "requested_model": extra.get("requested_model"),
        "source_chars": call.get("source_chars") or 0,
        "prompt_tokens": count_text_tokens(path.read_text(encoding="utf-8")),
        "prompt_sha256": handoff["prompt_sha256"],
        "generation": handoff["generation"],
        "child_handle": handoff.get("child_handle"),
        "host": handoff.get("host"),
    }


def _empty_review_packet(call: dict[str, Any]) -> bool:
    extra = call.get("extra") or {}
    if extra.get("assigned_ids") != []:
        return False
    path = Path(extra["packet_path"])
    raw = path.read_bytes()
    if _sha(raw) != call.get("packet_hash"):
        raise StaleWriteError("empty review packet hash differs from its bound claim")
    packet = json.loads(raw)
    return packet.get("assigned_ids") == [] and packet.get("assignments") == [] and packet.get("source") == ""


def _offer(run_dir: Path, task_id: str, claimed: dict[str, Any], model: str | None) -> dict[str, Any]:
    call_id = claimed["call_id"]
    packet_path = Path(claimed["packet_path"])
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    prompt = _dispatch_prompt(packet, _task_scope(task_id))
    complete_tokens = count_text_tokens(prompt.decode())
    input_cap = claimed.get("effective_max_input_tokens", NATIVE_INPUT_TARGET)
    if _task_scope(task_id) == "fact" and type(input_cap) is int and complete_tokens > input_cap:
        current = LedgerStore(run_dir).open()["calls"][call_id]
        if current.get("state") != "prepared" or (current.get("extra") or {}).get("native_handoff"):
            raise StaleWriteError("oversize layout cannot release an offered or delivered call")
    module_facts.validate_input_limit(input_cap)
    if _task_scope(task_id) == "fact" and complete_tokens > input_cap:
        # This private offer is reached synchronously from the fresh claim;
        # validation rejected it before any native prompt/offer was published.
        # The public release verb cannot infer this from prepared alone.
        def reject_local_offer(ledger):
            task, call = module_facts.verify_prepared_delivery_binding(
                ledger, task_id, call_id, (call_id, claimed["prompt_sha256"]))
            if (call.get("extra") or {}).get("native_handoff"):
                raise StaleWriteError("cannot reject an already offered layout")
            raw = ledger["tasks"][task_id]
            raw.update(state="pending", owner=None, lease_until=None, generation=task.generation + 1)
            raw["extra"].pop("call_id", None)
            mark_call(ledger, call_id, state="released", extra={"send_evidence": "not_sent_bootstrap",
                "disposition": "synchronous_native_offer_layout_rejected"})
            return ledger
        LedgerStore(run_dir).mutate(reject_local_offer)
        raise module_facts.PromptLayoutError(scope="native_fact_complete",
            ids=list(packet.get("assigned_ids") or []), tokens=complete_tokens,
            cap=input_cap)
    dispatch_path = run_dir / "prompts" / f"{call_id}.native.txt"
    if dispatch_path.exists() and dispatch_path.read_bytes() != prompt:
        raise StaleWriteError("native dispatch prompt changed for a prepared call")
    atomic_write_bytes(dispatch_path, prompt)
    prompt_hash = _sha(prompt)

    def mutate(ledger: dict[str, Any]) -> dict[str, Any]:
        task, call = module_facts.verify_prepared_delivery_binding(
            ledger, task_id, call_id, (call_id, claimed["prompt_sha256"]))
        extra = call.get("extra") or {}
        if extra.get("effective_max_input_tokens", NATIVE_INPUT_TARGET) != input_cap:
            raise StaleWriteError("native input limit differs from its immutable fresh claim")
        if _task_scope(task_id) == "fact":
            envelope = packet["envelope"]
            if any(envelope.get(key) != value for key, value in (
                ("task_id", task_id), ("call_id", call_id),
                ("generation", task.generation), ("owner", task.owner),
                ("input_hash", task.input_hash),
            )) or call.get("input_hash") != task.input_hash:
                raise StaleWriteError("native offer claim identity changed before finalization")
            if packet.get("source_revision") != ledger["source_revision"]:
                raise StaleWriteError("native offer source revision changed before finalization")
            for path in {span["path"] for span in call.get("source_spans") or []}:
                module_facts.load_frozen_offsets(Path(ledger["repo_root"]), path,
                                                ledger["inventory"]["files"][path])
        if dispatch_path.read_bytes() != prompt:
            raise StaleWriteError("native dispatch artifact changed before finalization")
        previous = extra.get("native_handoff")
        if previous and (previous.get("prompt_sha256") != prompt_hash
                         or previous.get("generation") != task.generation):
            raise StaleWriteError("native offer differs from its current generation")
        if model and extra.get("requested_model") not in (None, model):
            raise StaleWriteError("native requested model changed after claim")
        mark_call(ledger, call_id, extra={
            **({"preparation_stage": "local_artifacts_ready"}
               if _task_scope(task_id) == "fact" else {}),
            "requested_model": model or extra.get("requested_model"),
            "native_handoff": previous or {
                "status": "offered", "generation": task.generation,
                "dispatch_prompt_path": str(dispatch_path),
                "prompt_sha256": prompt_hash,
            },
        })
        ledger["native_scheduler_last_role"] = "review" if "_review" in task_id else "author"
        return ledger

    ledger = LedgerStore(run_dir).mutate(mutate)
    return _item(run_dir, task_id, ledger["calls"][call_id])


def _candidates(ledger: dict[str, Any], scope: str, audit_tasks=()) -> list[tuple[str, str, str]]:
    prefixes = {"fact": ("fact_author", "fact_review"),
                "module": ("module_author", "module_review"),
                "system": ("system_author", "system_review")}[scope]
    selected = []
    from cbe.review_policy import mode
    from cbe.native_abandon import retry_authorized
    protected_tasks = {call.get("task_id") for call in ledger.get("calls", {}).values()
                       if call.get("state") in {"prepared", "sent", "uncertain"} and not retry_authorized(call)}
    protected_tasks.update(tid for tid, raw in ledger.get("tasks", {}).items() if raw.get("state") == "leased")
    for task_id, raw in (ledger.get("tasks") or {}).items():
        if raw.get("kind") not in prefixes or raw.get("state") not in OPEN_STATES:
            continue
        if mode(ledger) == "none" and str(raw.get("kind", "")).endswith("review") and task_id not in audit_tasks:
            continue  # Known findings remain visible, never auto-launch a semantic reviewer in none.
        if task_id in protected_tasks:
            continue  # Historical uncertain delivery cannot be bypassed by a pending task.
        extra = raw.get("extra") or {}
        if extra.get("tombstone") or extra.get("superseded"):
            continue
        delegated = {sid for sid, delegated_id in (extra.get("canonical_delegations") or {}).items()
                     if (ledger.get("tasks", {}).get(delegated_id) or {}).get("state") != "committed"
                     or module_facts.accepted_fact(ledger, sid)}
        scope_ids = set(extra.get("repair_ids") or raw.get("input_ids") or [])
        if raw.get("kind") == "fact_review" and delegated:
            required = set(extra.get("required_review_ids") or []) | set(extra.get("audit_review_ids") or [])
            if task_id in audit_tasks:
                # A manual audit of this pending batch must reach its unaccepted
                # members, even when an old sample set contains only delegates.
                required.update(sid for sid in raw.get("input_ids") or []
                                if not module_facts.accepted_fact(ledger, sid))
            required.update(item.get("symbol_id") for item in raw.get("residual") or [] if isinstance(item, dict))
            if extra.get("required_review_ids") is not None:
                scope_ids &= required
            reviews = ledger.get("fact_reviews") or {}
            details = ledger.get("details") or {}
            scope_ids = {sid for sid in scope_ids if (sid in required or not module_facts.accepted_fact(ledger, sid))
                         and not ((reviews.get(sid) or {}).get("state") == "source_checked"
                                  and (reviews.get(sid) or {}).get("content_sha256") == module_facts._sha_json(details.get(sid)))}
        if scope_ids and scope_ids <= delegated:
            continue
        if delegated and not scope_ids:
            continue
        kind = str(raw["kind"])
        ident = task_id.removeprefix(f"task:{kind}:") if scope != "system" else "system"
        if scope == "module" and protected_tasks & {
            f"task:module_author:{ident}", f"task:module_review:{ident}"}:
            continue
        if kind == "fact_review" and (ledger["tasks"].get(f"task:fact_author:{ident}") or {}).get("state") != "committed":
            continue
        if kind == "module_review" and (ledger.get("module_records") or {}).get(ident, {}).get("state") != "draft":
            continue
        if kind == "system_review" and (ledger.get("system_record") or {}).get("state") != "draft":
            continue
        selected.append((task_id, ident, kind))
    # Repair and source review precede new author work. This also prevents a
    # pending review from silently becoming batch acceptance by omission.
    selected.sort(key=lambda row: (
        0 if ledger["tasks"][row[0]]["state"] == "needs_repair" or
        (ledger["tasks"][row[0]].get("extra") or {}).get("canonical_composition") else 1,
        0 if row[2].endswith("review") else 1, row[0]))
    return selected


def _fair_candidates(ledger: dict, scope: str, audit_tasks=()) -> list[tuple[str, str, str]]:
    """Alternate ready author/review work without a whole-wave barrier."""
    rows = _candidates(ledger, scope, audit_tasks)
    authors = [row for row in rows if not row[2].endswith("review")]
    reviews = [row for row in rows if row[2].endswith("review")]
    want_review = ledger.get("native_scheduler_last_role") != "review"
    ordered = []
    while authors or reviews:
        queue = reviews if want_review else authors
        if not queue:
            queue = authors if want_review else reviews
        ordered.append(queue.pop(0))
        want_review = not want_review
    return ordered


def _claim(run_dir: Path, task_id: str, ident: str, kind: str, owner: str, max_input_tokens=None) -> dict[str, Any]:
    scoped_owner = f"{owner}/{kind}"
    if kind.startswith("fact_"):
        return module_facts.claim(run_dir, ident, owner=scoped_owner,
                                  kind=kind.removeprefix("fact_"), require_behavior_contract=True,
                                  _workflow_initialized=True, _defer_local_ready=True,
                                  max_input_tokens=max_input_tokens)
    if kind.startswith("module_"):
        return module_workflow.claim(run_dir, ident, owner=scoped_owner, kind=kind,
                                     _workflow_initialized=True)
    return system_workflow.claim(run_dir, owner=scoped_owner, kind=kind)


def _accepted_facts(ledger: dict[str, Any]) -> bool:
    return all(module_facts.accepted_fact(ledger, sid)
               for sid in (ledger.get("inventory") or {}).get("symbols") or {})


def quality_handoff(ledger: dict[str, Any]) -> dict[str, Any]:
    """Explain existing quality evidence to the fresh doc-only consumer."""
    symbols = ledger["inventory"]["symbols"]
    reviews = ledger.get("fact_reviews") or {}
    details = ledger.get("details") or {}
    evidence_states = Counter(
        reviews[sid].get("state", "unexplained")
        if sid in reviews and sid in details
        and reviews[sid].get("content_sha256") == module_facts._sha_json(details[sid])
        else "stale_evidence" if sid in reviews else "unexplained"
        for sid in symbols)
    usage = overall_token_budget(ledger)
    current_tasks = {tid: task for tid, task in ledger.get("tasks", {}).items()
                     if task.get("state") in {"pending", "leased", "needs_repair", "committed"}
                     and not (task.get("extra") or {}).get("superseded")}
    required = {sid for task in current_tasks.values()
                for sid in (task.get("extra") or {}).get("required_review_ids", [])}
    outstanding = sorted(sid for sid in required if not (
        reviews.get(sid, {}).get("state") == "source_checked"
        and sid in ledger.get("details", {})
        and reviews[sid].get("content_sha256") == module_facts._sha_json(ledger["details"][sid])))
    return {"source_revision": ledger["source_revision"], "symbol_count": len(symbols),
            "review_policy": __import__("cbe.review_policy", fromlist=["summary"]).summary(ledger),
            "accepted_symbol_count": sum(module_facts.accepted_fact(ledger, sid) for sid in symbols),
            "evidence_states": dict(evidence_states),
            "required_source_check_count": len(required), "outstanding_required_ids": outstanding,
            "unresolved_tasks": [{"task_id": tid, "state": task["state"], "findings": task.get("residual", [])}
                                 for tid, task in current_tasks.items()
                                 if task.get("state") not in {"committed", "stale", "historical"}],
            "usage_report": "native_usage", "usage_status": usage["status"],
            "unknown_usage_call_count": len(usage.get("unknown_usage_call_ids", [])),
            "unknown_delivery_call_count": len(usage.get("unknown_delivery_call_ids", [])),
            "next_action": "fresh_doc_only_reader",
            "finding_action": "native-feedback --run-dir RUN --findings ABS_JSON",
            "finding_schema": {"target_id": "canonical symbol/module ID or system", "reason": "concrete unsupported maintenance conclusion"},
            "reader_contract": "Use current rendered docs only. Report unsupported answers and evidence limits. "
                               "Use concrete reader findings for targeted source audits or repairs; "
                               "batch acceptance and program syntax do not mean individually source-checked. "
                               "Full-source question setters and graders are not part of the default generation loop."}


def _parent_usage_summary(ledger: dict, run_dir: Path) -> dict:
    """Default action output keeps totals/unknowns, with full history in status."""
    report = overall_token_budget(ledger)
    summary = {key: value for key, value in report.items() if not isinstance(value, (list, dict))}
    for key, value in report.items():
        if isinstance(value, list):
            summary[key.removesuffix("_ids") + "_count"] = len(value)
        elif isinstance(value, dict):
            summary[key.removesuffix("_ids") + "_counts"] = {name: len(ids) for name, ids in value.items()}
    summary["details_command"] = f"cbe status --run-dir {run_dir}"
    return summary


def reconciliation_actions(run_dir: Path, call: dict) -> dict:
    """Give real commands with the actual call, without guessing delivery."""
    import shlex
    run = shlex.quote(str(run_dir))
    cid = shlex.quote(call["call_id"])
    tid = shlex.quote(call["task_id"])
    scope = _task_scope(call["task_id"])
    handoff = (call.get("extra") or {}).get("native_handoff") or {}
    invocation_id = handoff.get("invocation_id")
    return {"call_state": call.get("state"),
        **({"cancelled_launch_command": f"cbe native-cancelled --run-dir {run} --invocation-id {shlex.quote(invocation_id)} --host-metadata ABS_ZCODE_METADATA --host-output ABS_HOST_OUTPUT --parent-public-evidence ABS_PARENT_CAPTURE",
            "cancelled_launch_precondition": "ZCode public Agent metadata confirms original task path, actual identity and terminal cancellation; dispatched cost stays unknown. For a recorded started child use native-record."}
           if invocation_id and not handoff.get("child_handle") else {}),
        "reconciliation_command": f"cbe call-reconcile --run-dir {run} --call-id {cid} --searched-file ABS_SEARCH_LOCATIONS_JSON",
        "reconciliation_precondition": "Explicitly inspect original host receipts/raw evidence. No-delivery reconciliation rejects positive delivery; prepared does not mean unsent.",
        "completed_result_command": f"cbe {scope}-import --run-dir {run} --task-id {tid} --result {shlex.quote(str(run_dir / 'raw' / (call['call_id'] + '.json')))}"}


def reconcile_existing_call(ledger: dict, call_id: str, *, searched: list[str], note: str = "") -> None:
    """Operator evidence-search disposition; clear only the bound task lease."""
    from cbe.store import delivery_evidence_is_positive, reconcile_call_delivery, mark_call
    call = ledger.get("calls", {}).get(call_id) or {}
    if not call or not searched or not all(isinstance(s, str) and s.strip() for s in searched):
        raise ValueError("an existing call and nonempty evidence locations searched are required")
    if delivery_evidence_is_positive(call):
        raise ValueError("positive delivery evidence remains: use the completed result import or rejection path")
    if call.get("state") == "prepared":
        mark_call(ledger, call_id, state="uncertain", extra={"disposition": "operator_evidence_search_requested"})
    reconcile_call_delivery(ledger, call_id, conclusion="no_delivery_evidence", searched=searched, note=note)
    task = ledger.get("tasks", {}).get(call.get("task_id")) or {}
    if task.get("state") == "leased" and (task.get("extra") or {}).get("call_id") == call_id:
        task.update(state="pending", owner=None, lease_until=None, generation=task.get("generation", 0) + 1)
        task["extra"].pop("call_id", None)
        task["extra"].pop("packet_hash", None)


def _resolution_action(run_dir, owner, ledger):
    from cbe import review_policy
    import shlex
    if review_policy.mode(ledger) != "none":
        return None
    unresolved = [{"task_id": tid, "state": task.get("state"),
                   "findings": task.get("residual") or [],
                   "reader_question": (task.get("extra") or {}).get("reader_question"),
                   "required_ids": (task.get("extra") or {}).get("required_review_ids") or [],
                   "target_action": shlex.join(["cbe", "native-next", "--run-dir", str(run_dir),
                       "--owner", owner, "--audit-task", tid])}
                  for tid, task in ledger.get("tasks", {}).items()
                  if str(task.get("kind", "")).endswith("review") and task.get("state") in OPEN_STATES
                  and not (task.get("extra") or {}).get("superseded")
                  and not (task.get("extra") or {}).get("tombstone")]
    if not unresolved:
        return None
    return {"status": "needs_resolution", "items": [], "unresolved": unresolved,
            "reason": "known semantic findings remain; explicitly choose a listed manual target audit without changing run policy",
            "next_action": unresolved[0]["target_action"],
            "finding_action": shlex.join(["cbe", "native-feedback", "--run-dir", str(run_dir), "--findings", "ABS_JSON"]),
            "render_action": shlex.join(["cbe", "render", "--run-dir", str(run_dir)]),
            "reader_grade": "partial scope; known findings remain unadjudicated; inspect published per-object grades",
            "native_usage": _parent_usage_summary(ledger, run_dir)}


def next_work(run_dir: Path, *, owner: str, model: str | None = None,
              count: int = 1, adopt_review_efficiency: bool = False,
              review_bundles: bool | None = None, review_mode: str | None = None,
              audit_tasks=(), max_input_tokens: int | None = None) -> dict[str, Any]:
    """Prepare at most ``count`` new calls; an offered call is never resent."""
    run_dir = Path(run_dir).resolve()
    if not owner.strip() or count < 1 or count > 32:
        raise ValueError("owner is required and count must be within 1..32")
    if model is not None and not model.strip():
        raise ValueError("model must be nonempty when supplied")
    store = LedgerStore(run_dir)
    module_facts.validate_input_limit(max_input_tokens)
    from cbe import review_policy
    ledger = review_policy.configure(run_dir, review_mode, preview=store.open())
    audit_tasks = set(audit_tasks)
    for tid in audit_tasks:
        task = ledger.get("tasks", {}).get(tid) or {}
        if not str(task.get("kind", "")).endswith("review") or not (
            task.get("residual") or (task.get("extra") or {}).get("reader_question")
            or (task.get("extra") or {}).get("audit_mode")
            or (task.get("extra") or {}).get("audit_review_ids")):
            raise ValueError("audit-task must name an existing review with a known finding or reader audit")
    if review_bundles is True or (review_bundles is None and not ledger.get("fact_workflow_version")):
        def adopt_transport(current):
            current["native_review_transport"] = "bounded-bundles-v1"
            return current
        store.mutate(adopt_transport)
        ledger = store.open()
    review_bundles = ledger.get("native_review_transport") == "bounded-bundles-v1" if review_bundles is None else review_bundles
    # Reuse only pure workflow flags while no local mutation has occurred.
    flags = ledger
    if (ledger.get("documentation_policy") or {}).get("version") != "module-first-v2":
        raise ValueError("native handoff requires module-first-v2")
    if (ledger.get("documentation_policy") or {}).get("budget_mode") != "report":
        # Calling native-next is the explicit migration of an older run. Keep
        # all historical calls and costs; change only future admission policy.
        def adopt(current: dict[str, Any]) -> dict[str, Any]:
            policy = current["documentation_policy"]
            policy["budget_mode"] = "report"
            policy["budget_policy_version"] = "native-report-v1"
            budget_policy = current.setdefault("budget_policy", {})
            budget_policy["source_read_mode"] = "report"
            budget_policy.setdefault("history", []).append({
                "set_at": iso(), "reason": "explicit native-next adoption",
                "source_read_mode": "report",
            })
            sync_budget(current)
            return current
        store.mutate(adopt)
        flags = None
    if not ledger.get("fact_workflow_version"):
        # Leave room below the common 10k outer tool-output window. The existing
        # planner keeps every fact/review obligation and splits source as needed;
        # this is an input-layout target, not a document/source admission gate.
        module_facts.initialize(run_dir, batched=True, auto_budget=True,
                                auto_input_cap=NATIVE_INPUT_TARGET)
        flags = None
    if flags is None:
        flags = store.open()
    if not flags.get("attribution_workflow_version"):
        try:
            module_facts.register_attribution_batches(run_dir)
        except module_facts.PromptLayoutError as exc:
            return {"status": "needs_layout", "items": [], "diagnostic": exc.diagnostic}
    if adopt_review_efficiency:
        module_facts.adopt_review_efficiency(run_dir)
    review_policy.apply(run_dir, preview=flags)
    # Do not retain the first large snapshot alongside every subsequent locked
    # read. Claims still open the latest ledger under the existing transaction.
    flags = None
    ledger = None
    module_facts.merge_ready(run_dir, limit=count)
    ledger = store.open()
    if module_facts.activate_reader_audits(run_dir, preview=ledger)["activated"]:
        ledger = store.open()
    for call_id, call in (ledger.get("calls") or {}).items():
        extra = call.get("extra") or {}
        handoff = extra.get("native_handoff") or {}
        current_task = (ledger.get("tasks") or {}).get(call.get("task_id")) or {}
        if (current_task.get("kind") == "fact_review" and current_task.get("state") == "leased"
            and (current_task.get("extra") or {}).get("call_id") == call_id
            and _empty_review_packet(call) and handoff.get("status") == "completed"):
            digest = (extra.get("native_events") or {}).get("completed")
            event = run_dir / "native" / f"{call_id}.completed.{digest}.json"
            if not digest or not event.is_file() or _sha(event.read_bytes()) != digest:
                raise StaleWriteError("completed empty review lacks its original bound event")
            record_event(run_dir, call_id, event)
        if call.get("state") == "prepared" and not extra.get("native_handoff") and extra.get("preparation_stage") == "local_artifacts_pending":
            module_facts.abort_local_preparation(run_dir, call["task_id"], call_id)
    ledger = store.open()

    active: list[dict[str, Any]] = []
    for task_id, raw in sorted((ledger.get("tasks") or {}).items()):
        if raw.get("state") != "leased" or not (raw.get("extra") or {}).get("call_id"):
            continue
        call_id = raw["extra"]["call_id"]
        call = (ledger.get("calls") or {}).get(call_id) or {}
        if not task_id.startswith(("task:fact_", "task:module_", "task:system_")):
            continue
        handoff = (call.get("extra") or {}).get("native_handoff") or {}
        invocation = (ledger.get("native_invocations") or {}).get(handoff.get("invocation_id"), {})
        if invocation.get("host_blocked"):
            active.append({"task_id": task_id, "call_id": call_id,
                           "invocation_id": handoff["invocation_id"],
                           "child_handle": handoff.get("child_handle"), "host": handoff.get("host"),
                           "status": "needs_reconciliation", "host_blocked": True,
                           "lease_owner": raw.get("owner"), "recovery_action": "after_official_permission_restore_fact_release_then_native_next",
                           "reason": "child ended with permission denial; restore official host channel and reconcile preserved member obligations"})
        elif not handoff:
            # An old external claim may have been dispatched without a native
            # event. Local artifacts, prepared state and absent child handles
            # cannot establish never-sent delivery. Preserve this claim and
            # enumerate every active obligation before offering independent work.
            active.append({"task_id": task_id, "call_id": call_id,
                           "status": "needs_reconciliation",
                           "lease_owner": raw.get("owner"),
                           "recovery_action": "inspect_original_host_window_and_reconcile_existing_call",
                           "reason": "claim has no native offer; delivery is unknown, including when local artifacts are ready"})
        elif handoff.get("status") == "started":
            active.append({"task_id": task_id, "call_id": call_id,
                            **({"invocation_id": handoff["invocation_id"]} if handoff.get("invocation_id") else {}),
                           "status": "waiting", "child_handle": handoff.get("child_handle"),
                           "host": handoff.get("host")})
        else:
            active.append({"task_id": task_id, "call_id": call_id,
                            **({"invocation_id": handoff["invocation_id"]} if handoff.get("invocation_id") else {}),
                           "status": "needs_reconciliation",
                           "reason": "offered or failed call; inspect host result before any resend"})

    active_ids = {item["call_id"] for item in active}
    from cbe.native_abandon import retry_authorized
    for call_id, call in (ledger.get("calls") or {}).items():
        if (call_id not in active_ids and not retry_authorized(call) and call.get("state") in {"prepared", "sent", "uncertain"}
            and str(call.get("task_id", "")).startswith(("task:fact_", "task:module_", "task:system_"))):
            active.append({"call_id": call_id, "task_id": call["task_id"],
                           "status": "needs_reconciliation", "reason": "historical unresolved delivery remains bound to this task"})
    for item in active:
        item.update(reconciliation_actions(run_dir, ledger["calls"][item["call_id"]]))
    scope = "fact"
    module_blockers = []
    if _accepted_facts(ledger) and not _candidates(ledger, "fact", audit_tasks):
        try:
            initialized = module_workflow.initialize(run_dir, _defer_busy=True)
            module_blockers = initialized.get("blocked_dependencies") or []
        except StaleWriteError as exc:
            return {"status": "needs_reconciliation", "items": active, "active": active,
                    "reason": str(exc), "next_action": "reconcile the actual listed calls, then native-next"}
        review_policy.apply(run_dir)
        ledger = store.open()
        scope = "module"
        if not _candidates(ledger, "module", audit_tasks) and not any(
            raw.get("kind") in {"module_author", "module_review"}
            and raw.get("state") == "leased"
            for raw in (ledger.get("tasks") or {}).values()
        ):
            if module_blockers:
                return {"status": "needs_reconciliation", "items": active, "active": active,
                        "blocked_dependencies": module_blockers,
                        "next_action": "reconcile the actual listed module calls/leases; independent ready modules remain schedulable"}
            resolution = _resolution_action(run_dir, owner, ledger)
            if resolution and not module_workflow.accepted_package(ledger)["modules"] == {
                gid: item["record"] for gid, item in (ledger.get("module_records") or {}).items()
            }:
                return {**resolution, "active": active}
            try:
                system_workflow.initialize(run_dir)
            except StaleWriteError as exc:
                return {"status": "needs_reconciliation", "items": active, "active": active,
                        "reason": str(exc), "next_action": "reconcile the actual listed calls, then native-next"}
            review_policy.apply(run_dir)
            ledger = store.open()
            scope = "system"

    ready: list[dict[str, Any]] = []
    claim_blockers: list[dict[str, Any]] = []
    layout_blockers: list[dict[str, Any]] = []
    replanned = False
    candidates = _fair_candidates(ledger, scope, audit_tasks)
    ledger = None
    for task_id, ident, kind in candidates:
        ledger = None
        if len(ready) >= count:
            break
        try:
            claimed = (_claim(run_dir, task_id, ident, kind, owner)
                       if max_input_tokens is None else
                       _claim(run_dir, task_id, ident, kind, owner, max_input_tokens))
        except LeaseError as exc:
            # Another legitimate writer can acquire/finish one candidate after
            # discovery. Keep prior offers and try other independent targets.
            current = store.open()
            task = current.get("tasks", {}).get(task_id) or {}
            cid = (task.get("extra") or {}).get("call_id")
            claim_blockers.append({"task_id": task_id, "state": task.get("state"),
                                   "call_id": cid, "reason": str(exc)})
            if (cid and current.get("calls", {}).get(cid, {}).get("state") in {"prepared", "sent", "uncertain"}
                and cid not in {a.get("call_id") for a in active}):
                handoff = current["calls"][cid].get("extra", {}).get("native_handoff") or {}
                active.append({"task_id": task_id, "call_id": cid,
                    "status": "waiting" if handoff.get("status") == "started" else "needs_reconciliation",
                    **reconciliation_actions(run_dir, current["calls"][cid])})
            current = None
            continue
        except module_facts.PromptLayoutError as exc:
            ledger = store.open()  # Only a layout recovery needs another snapshot.
            if kind == "fact_author" and module_facts.split_pending_repair(run_dir, task_id, allow_pending=True):
                if ready:
                    return {"status": "ready", "items": ready, "active": active,
                            **({"layout_blockers": layout_blockers} if layout_blockers else {})}
                return next_work(run_dir, owner=owner, count=count, model=model,
                                 review_bundles=review_bundles, review_mode=review_mode, audit_tasks=audit_tasks,
                                 max_input_tokens=max_input_tokens)
            if kind == "fact_review":
                # The existing partial-review import keeps required unchecked
                # IDs pending. Reduce only this presentation, never re-author
                # accepted facts or silently drop the remaining review scope.
                original = list((ledger["tasks"][task_id]).get("input_ids") or [])
                # Context errors name only their offending fact. Try the other
                # unresolved facts first; an infeasible first half must not hide
                # a feasible second half forever. Failed previews mutate no CAS.
                ids = list(exc.diagnostic["assigned_ids"])
                if isinstance(exc, (module_facts.ReviewContextWindowError,
                                    module_facts.ReviewNonprogressError)):
                    blocked_ids = set(ids)
                    reviews = ledger.get("fact_reviews") or {}
                    details = ledger.get("details") or {}
                    required = set((ledger["tasks"][task_id].get("extra") or {}).get(
                        "required_review_ids") or [])
                    ids = [sid for sid in original if sid not in blocked_ids
                           and (sid in required or not module_facts.accepted_fact(ledger, sid))
                           and not ((reviews.get(sid) or {}).get("state") == "source_checked"
                                    and (reviews.get(sid) or {}).get("content_sha256")
                                    == module_facts._sha_json(details.get(sid)))]
                    layout_blockers.append({"task_id": task_id, "diagnostic": exc.diagnostic})
                    subsets = [ids] if ids else []
                else:
                    midpoint = max(1, len(ids) // 2)
                    subsets = [ids[:midpoint], ids[midpoint:]] if len(ids) > 1 else []
                while subsets:
                    ids = subsets.pop(0)
                    if not ids:
                        continue
                    try:
                        claimed = module_facts.claim(run_dir, ident,
                            owner=f"{owner}/{kind}", kind="review", review_ids=ids,
                            _defer_local_ready=True, max_input_tokens=max_input_tokens)
                        break
                    except module_facts.PromptLayoutError as smaller:
                        exc = smaller
                        if len(ids) > 1:
                            midpoint = len(ids) // 2
                            subsets.extend([ids[:midpoint], ids[midpoint:]])
                else:
                    replacement = module_facts.queue_uncertainty_reconciliation(
                        run_dir, task_id, list(exc.diagnostic.get("assigned_ids") or []))
                    if replacement:
                        replanned = True
                    layout_blockers.append({"task_id": task_id, "diagnostic": exc.diagnostic,
                                            **({"reconciliation_task": replacement} if replacement else {})})
                    continue
            else:
                layout_blockers.append({"task_id": task_id, "diagnostic": exc.diagnostic})
                continue
        try:
            if task_id in audit_tasks:
                def mark_manual(current):
                    current["calls"][claimed["call_id"]]["extra"]["review_dispatch"] = "manual-target"
                    return current
                store.mutate(mark_manual)
            item = _offer(run_dir, task_id, claimed, model)
            if task_id in audit_tasks:
                item["review_dispatch"] = "manual-target"
            ready.append(item)
        except module_facts.PromptLayoutError as exc:
            layout_blockers.append({"task_id": task_id, "diagnostic": exc.diagnostic})
    if ready:
        if review_bundles:
            from cbe.native_bundles import pack_ready
            ready = pack_ready(run_dir, ready, cap=NATIVE_INPUT_TARGET)
        return {"status": "ready", "items": ready, "active": active,
                **({"claim_blockers": claim_blockers} if claim_blockers else {}),
                **({"blocked_dependencies": module_blockers} if module_blockers else {}),
                **({"layout_blockers": layout_blockers} if layout_blockers else {})}
    if replanned:
        result = next_work(run_dir, owner=owner, count=count, model=model,
                                 review_bundles=review_bundles, review_mode=review_mode, audit_tasks=audit_tasks)
        result["layout_blockers"] = layout_blockers + result.get("layout_blockers", [])
        return result
    if module_blockers:
        return {"status": "needs_reconciliation", "items": active, "active": active,
                "blocked_dependencies": module_blockers,
                "next_action": "reconcile the actual listed module calls/leases; no inferred never-sent delivery"}
    if active:
        status = "needs_reconciliation" if any(
            item["status"] == "needs_reconciliation" for item in active) else "waiting"
        return {"status": status, "items": active, "active": active,
                **({"claim_blockers": claim_blockers} if claim_blockers else {}),
                **({"layout_blockers": layout_blockers} if layout_blockers else {})}
    if layout_blockers:
        return {"status": "needs_layout", "items": [], "active": [],
                "layout_blockers": layout_blockers, **layout_blockers[0]}
    ledger = store.open()
    has_unresolved_optional_review = review_policy.mode(ledger) == "none" and any(
        str(task.get("kind", "")).endswith("review") and task.get("state") in OPEN_STATES
        and not (task.get("extra") or {}).get("superseded") and not (task.get("extra") or {}).get("tombstone")
        for task in ledger.get("tasks", {}).values())
    if scope == "system" and system_workflow.accepted_system(ledger) is not None and not has_unresolved_optional_review:
        from cbe.render import render

        manifest = render(run_dir)
        return {"status": "complete", "items": [],
                "reader_index": str(Path(ledger.get("reader_output_dir") or run_dir / "render") / "INDEX.md"),
                "token_budget": manifest["token_budget"],
                "source_budget": store.open().get("budget"),
                "quality_handoff": quality_handoff(store.open()),
                "native_usage": _parent_usage_summary(store.open(), run_dir)}
    unresolved = [{"task_id": tid, "state": task.get("state"), "findings": task.get("residual") or [],
                   "reader_question": (task.get("extra") or {}).get("reader_question"),
                   "required_ids": (task.get("extra") or {}).get("required_review_ids") or []}
                  for tid, task in ledger.get("tasks", {}).items()
                  if str(task.get("kind", "")).endswith("review") and task.get("state") in OPEN_STATES
                  and not (task.get("extra") or {}).get("superseded") and not (task.get("extra") or {}).get("tombstone")]
    if unresolved and review_policy.mode(ledger) == "none":
        return _resolution_action(run_dir, owner, ledger)
    return {"status": "waiting", "items": [],
            "reason": "no runnable task; inspect pending fact, module or system prerequisites"}


def _host_observation(event: dict[str, Any], prompt_hash: str) -> tuple[str | None, dict[str, Any] | None]:
    """Return only fields actually present in a host artifact."""
    level = event.get("evidence_level")
    if level == "controller_attested":
        return None, None
    path = Path(str(event.get("evidence_ref") or ""))
    if not path.is_absolute() or not path.is_file():
        raise ValueError("host evidence_ref must be an existing absolute file")
    if level == "host_tool_result":
        artifact = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(artifact, dict):
            raise ValueError("host tool result must be a JSON object")
        if event.get("status") == "not_sent":
            if artifact.get("status") not in {"rejected_before_send", "not_sent"}:
                raise ValueError("host tool result does not prove a predispatch rejection")
        else:
            handle = artifact.get("child_handle") or artifact.get("agent_id") or artifact.get("session_id")
            if handle != event.get("child_handle"):
                raise ValueError("host tool result disagrees with child handle")
            if event.get("status") == "failed" and artifact.get("status") not in {
                "failed", "error", "cancelled", "timeout",
            }:
                raise ValueError("host tool result does not prove a terminal child failure")
        return artifact.get("observed_model") or artifact.get("model"), artifact.get("usage")
    if level == "host_transcript":
        session = None
        model = None
        prompts: set[str] = set()
        usage = None
        for line in path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            payload = item.get("payload") or {}
            if item.get("type") == "session_meta":
                session = payload.get("id") or payload.get("session_id")
            elif item.get("type") == "turn_context":
                model = payload.get("model")
            elif item.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") == "user":
                prompts.update(_sha(part["text"].encode()) for part in payload.get("content") or []
                               if isinstance(part, dict) and isinstance(part.get("text"), str))
            elif item.get("type") == "event_msg" and payload.get("type") == "token_count":
                usage = (payload.get("info") or {}).get("total_token_usage")
        if session != event.get("child_handle") or prompt_hash not in prompts:
            raise ValueError("host transcript does not bind child and native dispatch prompt")
        return model, usage
    raise ValueError("evidence_level must be host_tool_result, host_transcript or controller_attested")


def _usage(event: dict[str, Any], host_usage: dict[str, Any] | None,
           prior: dict[str, Any]) -> dict[str, Any] | str:
    if not isinstance(host_usage, dict):
        return "unavailable"
    kind = event.get("usage_kind", "incremental")
    aliases = {"input_tokens": ("input_tokens", "inputTokens"), "output_tokens": ("output_tokens", "outputTokens"),
               "cached_input_tokens": ("cached_input_tokens", "cache_read_input_tokens"),
               "reasoning_output_tokens": ("reasoning_output_tokens",),
               "cache_creation_input_tokens": ("cache_creation_input_tokens",),
               "total_tokens": ("total_tokens", "totalTokens")}
    aliases["cached_input_tokens"] += ("cacheReadTokens",)
    current = {key: next((host_usage[name] for name in names
                          if type(host_usage.get(name)) is int and host_usage[name] >= 0), None)
               for key, names in aliases.items()}
    if kind == "cumulative":
        baseline = prior.get("native_usage_baseline")
        if not isinstance(baseline, dict):
            return "unavailable"
        result = {}
        for key, value in current.items():
            old = baseline.get(key)
            if value is not None and type(old) is int and value >= old:
                result[key] = value - old
        return result if result else "unavailable"
    if kind != "incremental":
        raise ValueError("usage_kind must be incremental or cumulative")
    result = {key: value for key, value in current.items() if value is not None}
    if result and isinstance(host_usage.get("cache_included_in_input"), bool):
        result["cache_included_in_input"] = host_usage["cache_included_in_input"]
    return result or "unavailable"


def _literal_invalid_escapes(text: str) -> tuple[str, list[int]]:
    """Preserve a non-JSON escape as literal backslash; never repair Unicode."""
    offsets = []
    output = []
    in_string = False
    index = 0
    while index < len(text):
        char = text[index]
        if char == '"':
            in_string = not in_string
        if in_string and char == "\\" and index + 1 < len(text):
            following = text[index + 1]
            if following not in '"\\/bfnrtu':
                output.append("\\")
                offsets.append(index)
            output.extend((char, following))
            index += 2
            continue
        output.append(char)
        index += 1
    return "".join(output), offsets


def _normalized_payload(raw: bytes, task_id: str, packet: dict[str, Any], envelope: dict):
    """Pure existing format bridge; also proves the original/normalized relation."""
    transformations = []
    try:
        text = raw.decode("utf-8")
        try:
            payload, _ = module_facts._parse_model_payload(text)
        except ValueError:
            # Recovery is restricted to a direct JSON object, not prose/fences.
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                if exc.msg != "Invalid \\escape":
                    raise
            else:
                raise
            repaired, transformations = _literal_invalid_escapes(text)
            payload, _ = module_facts._parse_model_payload(repaired)
    except (UnicodeDecodeError, ValueError) as exc:
        raise _ResultFormatError("completed child result must be a JSON object") from exc
    if payload.get("envelope") is not None and payload["envelope"] != envelope:
        raise StaleWriteError("model echoed a conflicting native envelope")
    for field in ("model", "session_id", "usage"):
        if field in payload:
            raise ValueError(f"model output must not assert host field {field}")
    _check_result_shape(payload, task_id)
    payload["envelope"] = envelope
    if task_id.endswith("review") or ":review:" in task_id or "_review:" in task_id:
        for field, value in (("content_sha256", packet.get("draft_content_sha256")),
                             ("evidence_ref", packet.get("evidence_path"))):
            if value is not None:
                if payload.get(field) not in (None, value):
                    raise StaleWriteError(f"model echoed conflicting {field}")
                payload[field] = value
    if task_id.startswith("task:module_author:") and "content" not in payload:
        keys = ("summary", "flow", "uncertainties", "key_symbols", "source_refs")
        if all(key in payload for key in keys):
            payload["content"] = {key: payload.pop(key) for key in keys}
    return payload, transformations, repaired if transformations else None


def _normalized_bytes(raw: bytes, task_id: str, packet: dict, envelope: dict) -> bytes:
    payload, _, _ = _normalized_payload(raw, task_id, packet, envelope)
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()


def _normalize_result(run_dir: Path, task_id: str, call_id: str,
                      source: Path, packet: dict[str, Any], task: dict[str, Any]) -> Path:
    raw = source.read_bytes()
    envelope = {key: task.get(key) for key in ("task_id", "generation", "owner", "input_hash")}
    envelope["call_id"] = call_id
    original = run_dir / "native" / f"{call_id}.response.txt"
    result = run_dir / "raw" / f"{call_id}.json"
    if source == result and original.exists() and original.read_bytes() != raw:
        immutable = original.read_bytes()
        if raw != _normalized_bytes(immutable, task_id, packet, envelope):
            raise StaleWriteError("reserved response differs from the original strict normalization")
        raw = immutable
    payload, transformations, repaired = _normalized_payload(raw, task_id, packet, envelope)
    if (task_id.endswith("review") or ":review:" in task_id or "_review:" in task_id) and packet.get("evidence_path"):
        evidence = Path(packet["evidence_path"])
        if evidence.exists() and evidence.read_bytes() != raw:
            raise StaleWriteError("native review evidence path already has different content")
        atomic_write_bytes(evidence, raw)
    if original.exists() and original.read_bytes() != raw:
        raise StaleWriteError("native response changed for a completed call")
    atomic_write_bytes(original, raw)
    if transformations:
        atomic_write_bytes(run_dir / "native" / f"{call_id}.json-transform.json",
                           (json.dumps({"operation": "literalize_invalid_json_escape",
                                        "original_sha256": hashlib.sha256(raw).hexdigest(),
                                        "transformed_sha256": hashlib.sha256(repaired.encode("utf-8")).hexdigest(),
                                        "character_offsets": transformations}, indent=2) + "\n").encode())
    normalized = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    if result.exists() and result.read_bytes() != normalized and result != source:
        raise StaleWriteError("reserved native raw result already differs")
    atomic_write_bytes(result, normalized)
    return result


def _record_invocation_binding(ledger, call, task, event):
    """Shared aggregate/member identity guard for preparation and locked use."""
    handoff = (call.get("extra") or {}).get("native_handoff") or {}
    invocation_id = handoff.get("invocation_id")
    if not invocation_id:
        return None
    from cbe.native_bundles import checked_invocation
    invocation = checked_invocation(ledger, invocation_id)
    if invocation.get("host_blocked"):
        raise StaleWriteError("host-blocked invocation cannot import member business results")
    if (event.get("invocation_id") != invocation_id
        or invocation.get("host") != _canonical_host(event.get("host"))
        or invocation.get("child_handle") != event.get("child_handle")
        or event["status"] not in invocation.get("events", {})):
        raise StaleWriteError("bundled member requires recorded invocation evidence")
    member = next((m for m in invocation["members"] if m["call_id"] == call["call_id"]), None)
    if (invocation["source_revision"] != ledger["source_revision"] or not member
        or member["generation"] != task.get("generation") or member["input_hash"] != task.get("input_hash")):
        raise StaleWriteError("invocation member claim is stale")
    return invocation


def _fresh_zcode_child(call, event):
    """Reject copied placeholders, without upgrading controller evidence."""
    if (_canonical_host(event.get("host")) != "zcode" or event.get("status") != "started"
        or (call.get("extra") or {}).get("native_events", {}).get("started")
        or event.get("launch_binding_proof")):
        return
    handle = event.get("child_handle")
    try:
        valid = isinstance(handle, str) and handle.startswith("agent_") and str(uuid.UUID(handle[6:])) == handle[6:]
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("fresh ZCode binding needs the actual agent_<UUID>, never a placeholder; "
                         "use --host-metadata and --parent-public-evidence to derive its real child handle")


def _record_replay(store, run_dir, call_id, event, event_bytes, preview_call):
    """Linearize duplicate success against current state without another write."""
    status, digest = event["status"], _sha(event_bytes)
    with store.locked():
        current = store.read_unlocked()
        call = current.get("calls", {}).get(call_id)
        if not call:
            raise StaleWriteError("native replay call disappeared")
        extra = call.get("extra") or {}
        handoff = extra.get("native_handoff") or {}
        previous_extra = preview_call.get("extra") or {}
        if any(call.get(k) != preview_call.get(k) for k in
               ("task_id", "input_hash", "packet_hash", "state", "usage", "actual_model")) or any(
               extra.get(k) != previous_extra.get(k) for k in
               ("native_handoff", "native_events", "prompt_sha256", "usage_raw", "usage_status",
                "native_result_rejection", "requested_model")):
            raise StaleWriteError("native replay binding or accounting changed after preview")
        if status != "not_sent" and event.get("child_handle") != handoff.get("child_handle"):
            raise NativeChildHandleConflict("native replay child handle differs from recorded child")
        if extra.get("native_events", {}).get(status) != digest:
            raise StaleWriteError("native event already recorded with different evidence")
        accepted = run_dir / "native" / f"{call_id}.{status}.{digest}.json"
        if accepted.read_bytes() != event_bytes:
            raise StaleWriteError("native replay accepted event bytes changed")
        if any(event.get(k) != v for k,v in (
            ("call_id", call_id), ("task_id", call["task_id"]),
            ("generation", handoff.get("generation")),
            ("prompt_sha256", handoff.get("prompt_sha256")),
        )) or _canonical_host(event.get("host")) != _canonical_host(handoff.get("host")) or (
            status != "not_sent" and event.get("child_handle") != handoff.get("child_handle")):
            raise StaleWriteError("native replay no longer binds its original child and generation")
        if _sha(Path(handoff["dispatch_prompt_path"]).read_bytes()) != handoff["prompt_sha256"]:
            raise StaleWriteError("native replay dispatch prompt changed")
        historical = call.get("state") in {"imported", "released"}
        if historical:
            # Validate the accepted call's original envelope, never a newer
            # task epoch. This view is used only for deterministic byte checks.
            packet = json.loads(Path(extra["packet_path"]).read_bytes())
            envelope = packet.get("envelope") or {}
            revision = packet.get("source_revision") or (packet.get("metadata") or {}).get("source_revision")
            if any(envelope.get(k) != v for k,v in (
                ("call_id", call_id), ("task_id", call["task_id"]),
                ("input_hash", call["input_hash"]), ("generation", handoff["generation"]),
            )) or revision != current["source_revision"] or not envelope.get("owner"):
                raise StaleWriteError("native replay frozen input identity changed")
            task = dict(current["tasks"][call["task_id"]])
            task.update(generation=envelope["generation"], owner=envelope["owner"], input_hash=envelope["input_hash"])
            task["extra"] = {**task.get("extra", {}), "call_id": call_id}
            view = {**current, "tasks": {call["task_id"]: task},
                    "calls": {call_id: {**call, "state": "imported"}}}
        else:
            view = current
            task = current["tasks"][call["task_id"]]
            if task.get("generation") != handoff["generation"]:
                raise StaleWriteError("native replay task generation changed")
        module_facts.verify_prepared_delivery_binding(view, call["task_id"], call_id,
                                                     (call_id, extra["prompt_sha256"]))
        host, handle = _canonical_host(event.get("host")), event.get("child_handle")
        invocation = handoff.get("invocation_id")
        _record_invocation_binding(current, call, task, event)
        if status != "not_sent" and any(other_id != call_id
            and _canonical_host((other.get("extra", {}).get("native_handoff") or {}).get("host")) == host
            and (other.get("extra", {}).get("native_handoff") or {}).get("child_handle") == handle
            and (not invocation or (other.get("extra", {}).get("native_handoff") or {}).get("invocation_id") != invocation)
            for other_id, other in current.get("calls", {}).items()):
            raise StaleWriteError("native replay child is bound to another call")
        observed_model, host_usage = _host_observation(event, handoff["prompt_sha256"])
        if observed_model and call.get("actual_model") != observed_model:
            raise StaleWriteError("native replay observed model evidence changed")
        if not invocation and event.get("usage_raw", host_usage if isinstance(host_usage, dict) else None) != extra.get("usage_raw"):
            raise StaleWriteError("native replay usage evidence changed")
        if event.get("requested_model") not in (None, extra.get("requested_model")):
            raise StaleWriteError("native replay requested model changed")
        if event.get("launch_binding_proof"):
            from cbe.native_binding import launch_proof
            saved = event["launch_binding_proof"]
            if launch_proof(current, call, saved["metadata_ref"], saved["parent_ref"],
                            completed=status == "completed") != saved:
                raise StaleWriteError("native replay launch evidence changed")
        if extra.get("native_result_rejection") and status == "completed":
            return {"call_id": call_id, "task_id": call["task_id"], "status": "result_rejected",
                    "idempotent": True, "next_action": "native-next", "reason": extra["native_result_rejection"]}
        if status == "completed" and not historical and task.get("state") != "committed":
            normalized = run_dir / "raw" / f"{call_id}.json"
            if normalized.is_file():
                return {"retry_import": (call["task_id"], normalized, call.get("actual_model"), call.get("usage") or "unavailable")}
        return {"call_id": call_id, "task_id": call["task_id"], "status": status, "idempotent": True}


def record_event(run_dir: Path, call_id: str, event_path: Path,
                 *, result_path: Path | None = None,
                 _preview: dict | None = None) -> dict[str, Any]:
    """Bind one host event, retaining raw evidence and reusing normal import."""
    run_dir = Path(run_dir).resolve()
    event_path = Path(event_path).resolve()
    event_bytes = event_path.read_bytes()
    event = json.loads(event_bytes)
    if not isinstance(event, dict) or event.get("schema") != SCHEMA:
        raise ValueError("native event needs schema native_handoff_v1")
    status = event.get("status")
    if status not in {"started", "completed", "failed", "not_sent"}:
        raise ValueError("invalid native event status")
    store = LedgerStore(run_dir)
    ledger = _preview if _preview is not None else store.open()
    _preview = None  # Preparation only; final mutate always reads locked current.
    call = (ledger.get("calls") or {}).get(call_id)
    if not call:
        raise ValueError("unknown native call")
    digest = _sha(event_bytes)
    existing_events = (call.get("extra") or {}).get("native_events") or {}
    _fresh_zcode_child(call, event)
    if status in existing_events:
        decision = _record_replay(store, run_dir, call_id, event, event_bytes, call)
        ledger = None
        if "retry_import" in decision:
            task_id, normalized, observed_model, usage = decision["retry_import"]
            return _import_result(run_dir, task_id, call_id, normalized, observed_model, usage)
        return decision
    task_id = call["task_id"]
    task = (ledger.get("tasks") or {}).get(task_id) or {}
    handoff = (call.get("extra") or {}).get("native_handoff") or {}
    if not handoff:
        raise StaleWriteError("call was not offered for native handoff")
    if any((event.get(key) != value) for key, value in (
        ("call_id", call_id), ("task_id", task_id),
        ("generation", task.get("generation")),
        ("prompt_sha256", handoff.get("prompt_sha256")),
    )):
        raise StaleWriteError("native event does not bind this claim generation and prompt")
    host, handle = _canonical_host(event.get("host")), event.get("child_handle")
    invocation_id = handoff.get("invocation_id")
    invocation = _record_invocation_binding(ledger, call, task, event)
    if not isinstance(host, str) or not host or (
        status != "not_sent" and (not isinstance(handle, str) or not handle)
    ):
        raise ValueError("native event needs host and stable child_handle after dispatch")
    if status == "not_sent":
        handle = ""
    elif any(other_id != call_id
             and _canonical_host(((other.get("extra") or {}).get("native_handoff") or {}).get("host")) == host
             and ((other.get("extra") or {}).get("native_handoff") or {}).get("child_handle") == handle
             and (not invocation_id or ((other.get("extra") or {}).get("native_handoff") or {}).get("invocation_id") != invocation_id)
             for other_id, other in (ledger.get("calls") or {}).items()):
        raise ValueError("native work requires a fresh child; this host/child is already bound to another call")
    if _sha(Path(handoff["dispatch_prompt_path"]).read_bytes()) != handoff["prompt_sha256"]:
        raise StaleWriteError("native dispatch prompt changed after offer")
    module_facts.verify_prepared_delivery_binding(
        ledger, task_id, call_id, (call_id, (call.get("extra") or {})["prompt_sha256"]))
    observed_model, host_usage = _host_observation(event, handoff["prompt_sha256"])
    if invocation:
        observed_model = invocation.get("actual_model")
        host_usage = None  # Invocation-level usage is counted once, not allocated.
    observed_model = observed_model or call.get("actual_model")
    if event.get("observed_model") not in (None, observed_model):
        raise ValueError("event observed_model disagrees with host evidence")
    prior = call.get("extra") or {}
    if handoff.get("child_handle") not in (None, handle) or _canonical_host(handoff.get("host")) not in (None, host):
        raise StaleWriteError("native call cannot be rebound to another child")
    requested = prior.get("requested_model")
    if event.get("requested_model") not in (None, requested):
        raise StaleWriteError("native event requested model differs from claim")
    if status == "started" and handoff.get("status") not in {"offered", "started"}:
        raise StaleWriteError("native start is out of order")
    if status == "completed" and handoff.get("status") != "started":
        raise StaleWriteError("native completion requires a recorded child start")
    if status == "not_sent" and (handoff.get("status") != "offered"
                                  or event.get("evidence_level") == "controller_attested"
                                  or not event.get("predispatch_rejection")):
        raise ValueError("not_sent requires host-observed predispatch rejection")
    if status == "failed" and handoff.get("status") != "started":
        raise StaleWriteError("native failure requires a recorded child start")
    event_copy = run_dir / "native" / f"{call_id}.{status}.{digest}.json"
    if event_copy.exists() and event_copy.read_bytes() != event_bytes:
        raise StaleWriteError("native event artifact already differs")
    atomic_write_bytes(event_copy, event_bytes)
    usage = _usage(event, host_usage, prior)
    usage_raw = event.get("usage_raw", host_usage if isinstance(host_usage, dict) else None)
    if status == "completed":
        if result_path is None and event.get("result_path") is None and event.get("result") is not None:
            supplied = event["result"]
            result_bytes = ((json.dumps(supplied, ensure_ascii=False) + "\n").encode()
                            if isinstance(supplied, dict) else str(supplied).encode())
            embedded = run_dir / "native" / f"{call_id}.host-result.txt"
            if embedded.exists() and embedded.read_bytes() != result_bytes:
                raise StaleWriteError("native embedded result differs")
            atomic_write_bytes(embedded, result_bytes)
            result_source = embedded
        else:
            result_source = Path(result_path or event.get("result_path") or "")
        if not result_source.is_absolute() or not result_source.is_file():
            raise ValueError("completed native event needs an existing absolute result")
        packet = json.loads(Path(prior["packet_path"]).read_text(encoding="utf-8"))
        rejection = None
        try:
            normalized = _normalize_result(run_dir, task_id, call_id, result_source, packet, task)
        except _ResultFormatError as exc:
            rejection = str(exc)
            raw = result_source.read_bytes()
            original = run_dir / "native" / f"{call_id}.response.txt"
            _write_once(original, raw)
            normalized = run_dir / "raw" / f"{call_id}.json"
            _write_once(normalized, raw)
    else:
        normalized = None
        rejection = None

    def mutate(current: dict[str, Any]) -> dict[str, Any]:
        current_task, current_call = module_facts.verify_prepared_delivery_binding(
            current, task_id, call_id, (call_id, prior["prompt_sha256"]))
        _fresh_zcode_child(current_call, event)
        _record_invocation_binding(current, current_call, current_task.to_dict(), event)
        if any(other_id != call_id
               and _canonical_host(other.get("extra", {}).get("native_handoff", {}).get("host")) == host
               and other.get("extra", {}).get("native_handoff", {}).get("child_handle") == handle
               and (not invocation_id or other.get("extra", {}).get("native_handoff", {}).get("invocation_id") != invocation_id)
               for other_id, other in current.get("calls", {}).items()):
            raise StaleWriteError("actual child became bound to another call during record")
        if event.get("launch_binding_proof"):
            from cbe.native_binding import launch_proof
            saved = event["launch_binding_proof"]
            if launch_proof(current, current_call, saved["metadata_ref"], saved["parent_ref"],
                            completed=status == "completed") != saved:
                raise StaleWriteError("actual launch evidence changed during record")
        current_extra = current_call.get("extra") or {}
        current_handoff = dict(current_extra.get("native_handoff") or {})
        if current_handoff.get("generation") != current_task.generation:
            raise StaleWriteError("native event arrived for stale generation")
        if current_handoff.get("child_handle") not in (None, handle):
            raise StaleWriteError("native child identity changed during record")
        current_handoff.update({"status": status, "host": host, "child_handle": handle,
                                "evidence_level": event.get("evidence_level")})
        updated_events = dict(current_extra.get("native_events") or {})
        if status in updated_events and updated_events[status] != digest:
            raise StaleWriteError("native event changed during record")
        updated_events[status] = digest
        update = {
            "native_handoff": current_handoff, "native_events": updated_events,
            "native_event_ref": str(event_copy), "delivery_kind": SCHEMA,
            "delivery_evidence": event.get("evidence_level"),
            "usage_raw": usage_raw, "usage_kind": event.get("usage_kind"),
            "usage_status": "reported" if isinstance(usage, dict) and
            type(usage.get("input_tokens")) is int and type(usage.get("output_tokens")) is int
            else "reported_partial" if isinstance(usage, dict) and type(usage.get("total_tokens")) is int
            else "unavailable",
            "observed_model_evidence": event.get("evidence_level") if observed_model else "unavailable",
            "additional_reads": event.get("additional_reads", "unknown"),
            "source_observation": event.get("source_observation"),
        }
        if status == "started":
            update["send_evidence"] = "sent_native"
        if status == "not_sent":
            update["send_evidence"] = "not_sent_bootstrap"
            current["tasks"][task_id]["state"] = "pending"
            current["tasks"][task_id]["owner"] = None
            current["tasks"][task_id]["extra"].pop("call_id", None)
            mark_call(current, call_id, state="released", extra=update)
        elif status == "failed" and event.get("evidence_level") != "controller_attested":
            current["tasks"][task_id]["state"] = "pending"
            current["tasks"][task_id]["owner"] = None
            current["tasks"][task_id]["extra"].pop("call_id", None)
            mark_call(current, call_id, state="released",
                      role_session_id=f"{host}:{handle}", native_session_id=handle,
                      actual_model=observed_model, usage=usage,
                      extra={**update, "send_evidence": "sent_native",
                             "delivery_receipt": str(event_copy)})
        else:
            if status == "started":
                baseline = _usage({**event, "usage_kind": "incremental"}, host_usage, {})
                update["native_usage_baseline"] = baseline if isinstance(baseline, dict) else None
            mark_call(current, call_id, state="sent",
                      role_session_id=f"{host}:{handle}", native_session_id=handle,
                      actual_model=observed_model, usage=usage,
                      exposure_evidence="unverified",
                      extra={**update, "send_evidence": "sent_native",
                             "delivery_receipt": str(event_copy)})
            observation = event.get("source_observation") or {}
            source_chars = int(current_call.get("source_chars") or 0)
            if source_chars and event.get("transport", "inline") == "file":
                exposures = current["calls"][call_id].setdefault("source_exposures", [])
                for exposure in exposures:
                    if exposure.get("event_kind") == "initial":
                        # A stable spawned child does not prove its task file
                        # entered a model request. Promote only when the explicit
                        # transcript shows the complete prompt.
                        exposure["counted_as"] = (
                            COUNTED_KNOWN if observation.get("prompt_presentations_lower", 0) >= 1
                            else COUNTED_UPPER)
                        exposure["reason"] = "native_file_prompt_visible" if observation else "native_file_prompt_visibility_unknown"
                upper = observation.get("prompt_presentations_conditional_upper")
                if type(upper) is int:
                    for index in range(1, upper):
                        exposures.append({
                            "event_id": f"{call_id}:retained-history:{index}",
                            "event_kind": "reinjection", "role_session_id": f"{host}:{handle}",
                            "evidence_ref": str(event_copy),
                            "source_spans": current_call.get("source_spans") or [],
                            "source_chars": source_chars, "counted_as": COUNTED_UPPER,
                            "reason": "conditional_upper_assuming_prompt_history_retained",
                        })
                sync_budget(current)
            # Forwarding the full inline prompt may expose the same frozen
            # spans to the parent. Unknown parent reading is an upper bound.
            if status == "started" and event.get("transport", "inline") == "inline":
                source_chars = int(current_call.get("source_chars") or 0)
                if source_chars:
                    observed = event.get("parent_prompt_read") == "host_observed"
                    exposures = current["calls"][call_id].setdefault("source_exposures", [])
                    exposures.append({
                        "event_id": f"{call_id}:parent-forward", "event_kind": "parent_forward",
                        "role_session_id": f"{host}:controller", "evidence_ref": str(event_copy),
                        "source_spans": current_call.get("source_spans") or [],
                        "source_chars": source_chars,
                        "counted_as": COUNTED_KNOWN if observed else COUNTED_UPPER,
                        "reason": "inline_prompt_forwarded_by_controller",
                    })
                    sync_budget(current)
        return current

    ledger = None  # Keep only this call's frozen bindings, not the whole snapshot.
    store.mutate(mutate)
    if rejection is not None:
        return _reject_completed_result(run_dir, task_id, call_id, normalized, rejection)
    if normalized is not None:
        return _import_result(run_dir, task_id, call_id, normalized, observed_model, usage)
    return {"call_id": call_id, "task_id": task_id, "status": status,
            "observed_model": observed_model, "usage": usage}


def _reject_completed_result(run_dir: Path, task_id: str, call_id: str,
                             raw: Path, reason: str, *, finding_code: str = "invalid_model_result") -> dict[str, Any]:
    """Bind observed completion to retryable format rejection in the same ledger."""
    def reject(ledger: dict) -> dict:
        task, call = module_facts.verify_prepared_delivery_binding(ledger, task_id, call_id,
            (call_id, ledger["calls"][call_id]["extra"]["prompt_sha256"]))
        ids = list((call.get("extra") or {}).get("assigned_ids") or task.input_ids)
        if finding_code == "invalid_review_scope":
            author = ledger["tasks"].get(task_id.replace("task:fact_review:", "task:fact_author:", 1)) or {}
            ids = sorted((set(task.extra.get("required_review_ids") or [])
                          | set(task.extra.get("audit_review_ids") or [])
                          | module_facts.repair_review_ids(ledger, module_facts.TaskRecord.from_dict(author))
                          | {finding["symbol_id"] for finding in task.residual
                             if isinstance(finding, dict) and finding.get("symbol_id")}) & set(task.input_ids))
        pending = [sid for sid in ids if not module_facts.accepted_fact(ledger, sid)]
        task.state = "needs_repair"
        task.generation += 1
        task.owner = None
        task.lease_until = None
        findings = [{"code": finding_code, "reason": reason, "symbol_id": sid}
                    for sid in pending] or [{"code": finding_code, "reason": reason}]
        task.residual = [*task.residual, *findings]
        if task.kind == "fact_author":
            task.extra["repair_ids"] = pending
        ledger["tasks"][task_id] = task.to_dict()
        mark_call(ledger, call_id, state="imported", raw_path=str(raw), extra={
            "disposition": "validation_rejected", "native_result_rejection": reason,
            "validation_error": reason, "raw_result_sha256": _sha(raw.read_bytes())})
        return ledger
    LedgerStore(run_dir).mutate(reject)
    return {"call_id": call_id, "task_id": task_id, "status": "result_rejected",
            "reason": reason, "next_action": "native-next", "model_completed": True,
            "accepted_results_preserved": True}


def record(run_dir: Path, call_id: str, *, status: str, host: str,
           child_handle: str | None = None, host_result: Path | None = None,
           session_file: Path | None = None, result_path: Path | None = None,
           transport: str = "file", host_metadata: Path | None = None,
           parent_public_evidence: Path | None = None) -> dict[str, Any]:
    """Public handoff: derive the mechanical event from the frozen claim.

    Explicit host artifacts bind identity; a result-file fallback is openly
    controller-attested. No host session discovery or model execution occurs.
    """
    run_dir = Path(run_dir).resolve()
    ledger = LedgerStore(run_dir).open()
    call = (ledger.get("calls") or {}).get(call_id)
    if not call:
        raise ValueError("unknown native call")
    task = ledger["tasks"][call["task_id"]]
    handoff = (call.get("extra") or {}).get("native_handoff") or {}
    if not handoff:
        raise StaleWriteError("call was not offered for native handoff")
    if status == "not_sent":
        if child_handle not in (None, ""):
            raise StaleWriteError("not_sent cannot name a dispatched child")
        child_handle = None
        old_digest = (call.get("extra") or {}).get("native_events", {}).get("not_sent")
        if old_digest:
            accepted = run_dir / "native" / f"{call_id}.not_sent.{old_digest}.json"
            original_bytes = accepted.read_bytes()
            original = json.loads(original_bytes)
            if _sha(original_bytes) != old_digest or original.get("child_handle") not in (None, ""):
                raise StaleWriteError("original not_sent child evidence changed")
            child_handle = original.get("child_handle")
    else:
        child_handle = child_handle or handoff.get("child_handle")
    launch_binding_proof = None
    if host_metadata or parent_public_evidence:
        if not host_metadata or not parent_public_evidence or _canonical_host(host) != "zcode":
            raise ValueError("launch metadata requires ZCode metadata and original public parent evidence")
        from cbe.native_binding import launch_proof
        proof = launch_proof(ledger, call, host_metadata, parent_public_evidence,
                             completed=status == "completed")
        if child_handle is not None and child_handle != proof["child_handle"]:
            raise StaleWriteError("supplied child handle differs from actual public launch")
        child_handle = proof["child_handle"]
        launch_binding_proof = proof
    if host_result and session_file:
        raise ValueError("choose host-result or session-file, not both")
    if status not in {"started", "completed", "failed", "not_sent"}:
        raise ValueError("invalid native event status")
    event: dict[str, Any] = {
        "schema": SCHEMA, "call_id": call_id, "task_id": call["task_id"],
        "generation": handoff["generation"], "prompt_sha256": handoff["prompt_sha256"],
        "host": host, "child_handle": child_handle, "status": status,
        "evidence_level": "controller_attested", "additional_reads": "unknown",
        "transport": transport,
    }
    if launch_binding_proof:
        event["launch_binding_proof"] = launch_binding_proof
    _fresh_zcode_child(call, event)
    if host_result:
        artifact = json.loads(Path(host_result).read_text(encoding="utf-8"))
        if not isinstance(artifact, dict):
            raise ValueError("host-result must be an identity-bound JSON object")
        event.update(evidence_level="host_tool_result", evidence_ref=str(Path(host_result).resolve()))
        if status == "completed":
            value = artifact.get("result", artifact.get("final", artifact.get("final_text")))
            if value is None and result_path is None:
                raise ValueError("host-result has no complete final result")
            if value is not None:
                event["result"] = value
        if status == "not_sent":
            event["predispatch_rejection"] = True
    elif session_file:
        if status == "failed":
            raise ValueError("failed record requires a host-result with observed terminal failure status")
        from cbe.native_session import parse_session

        observation = parse_session(Path(session_file), host=host,
                                    child_handle=child_handle,
                                    dispatch_prompt=Path(handoff["dispatch_prompt_path"]).read_bytes(),
                                    dispatch_prompt_path=Path(handoff["dispatch_prompt_path"]))
        # Retain the original pointer and checksum alongside the pure parser's
        # observation. The source file is explicit, never a discovered session.
        artifact = {"child_handle": child_handle, "observed_model": observation["observed_model"],
                    "usage": observation["usage"], "session_file": str(Path(session_file).resolve()),
                    "session_sha256": _sha(Path(session_file).read_bytes()),
                    "parser": observation["parser"], "usage_basis": observation.get("usage_basis")}
        artifact_bytes = (json.dumps(artifact, ensure_ascii=False, sort_keys=True) + "\n").encode()
        evidence = run_dir / "native" / f"{call_id}.{status}.session-{_sha(artifact_bytes)}.json"
        _write_once(evidence, artifact_bytes)
        event.update(evidence_level="host_tool_result", evidence_ref=str(evidence),
                     usage_raw=observation["usage_raw"],
                     source_observation=observation["source_observation"])
        if status == "completed":
            event["result"] = observation["final"]
    elif status == "completed":
        if result_path is None:
            raise ValueError("completed record needs host-result, session-file or result")
        event["result_path"] = str(Path(result_path).resolve())
        event["source_observation"] = {"status": "unknown", "reason": "result-file fallback has no request transcript"}
    # This is transient controller input, not an accepted event. Rejected
    # requests must be correctable without deleting immutable host evidence.
    # record_event persists its own validated event copy and ledger reference.
    path = run_dir / "native" / f"{call_id}.{status}.{uuid.uuid4().hex}.request.pending.json"
    atomic_write_bytes(path, (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode())
    try:
        # Transfer the snapshot without retaining it in this caller while
        # record_event drops its preparation view before the locked commit.
        preview_holder = [ledger]
        ledger = None
        try:
            return record_event(run_dir, call_id, path, result_path=result_path,
                                _preview=preview_holder.pop())
        except NativeChildHandleConflict as exc:
            raise StaleWriteError("native child handle already recorded for this status") from exc
    finally:
        path.unlink(missing_ok=True)


def _import_result(run_dir: Path, task_id: str, call_id: str, result: Path,
                   observed_model: str | None, usage: dict[str, Any] | str) -> dict[str, Any]:
    # Also reconcile completed records written by older versions before the
    # shape bridge existed. Identical rejected output is never dispatched again.
    try:
        parsed, _ = module_facts._parse_model_payload(result.read_text(encoding="utf-8"))
        if task_id.startswith("task:fact_review:") and parsed.get("checked_ids") == []:
            call = LedgerStore(run_dir).open()["calls"][call_id]
            if _empty_review_packet(call):
                return _reject_completed_result(run_dir, task_id, call_id, result,
                    "completed review had no assigned evidence; recover the required repair/audit scope",
                    finding_code="invalid_review_scope")
            raise _ResultFormatError("fact review requires nonempty checked_ids")
        _check_result_shape(parsed, task_id)
    except _ResultFormatError as exc:
        return _reject_completed_result(run_dir, task_id, call_id, result, str(exc))
    if task_id.startswith("task:fact_"):
        try:
            imported = module_facts.import_result(run_dir, task_id, result)
        except module_facts.FactReferenceError as exc:
            return _reject_completed_result(run_dir, task_id, call_id, result, str(exc))
    elif task_id.startswith("task:module_"):
        imported = module_workflow.import_result(run_dir, task_id, result)
    else:
        imported = system_workflow.import_result(run_dir, task_id, result)
    return {**imported, "call_id": call_id, "status": "completed",
            "observed_model": observed_model, "usage": usage}
