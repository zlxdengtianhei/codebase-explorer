"""Recoverable external author and review work for module-first runs.

The ledger owns tasks, calls, drafts, and accepted explanations. A historical
module_explanations.json can be imported once as a compatibility snapshot.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

from cbe.accounting import copy_usage_fields
from cbe.module_author import build_module_author_packet
from cbe.module_explanations import (
    _checked_content,
    _checked_module,
    _frozen_file_lines,
    _dict_with_keys,
    _nonempty_text,
    explanation_content_sha256,
    validate_module_explanations,
)
from cbe.module_first_render import _validate_plan
from cbe.models import CallRecord, TaskRecord
from cbe.store import (
    LedgerStore,
    LeaseError,
    StaleWriteError,
    atomic_write_bytes,
    iso,
    mark_call,
    reserve_call,
    utc_now,
)
from cbe.static_literals import PROJECTION_VERSION, accepted_numeric_literals, accepted_return_keys
from cbe.token_budget import count_text_tokens

SUPPORT_IDS = frozenset({
    "test-support-catalogue", "example-source-catalogue", "docs-and-release-catalogue",
    "example-support-catalogue", "docs-support-catalogue", "extra-support-catalogue",
    "release-support-catalogue",
})
CONTENT_KEYS = frozenset({"summary", "flow", "key_symbols", "source_refs", "uncertainties"})
MODULE_CONTENT_SCHEMA = ('{"summary": string, "flow": string, "uncertainties": string, '
                         '"key_symbols": [member IDs], "source_refs": [{"path": string, "line": integer}]}')


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _plan(run_dir: Path, ledger: dict) -> dict:
    plan = json.loads((run_dir / "module_plan.json").read_text(encoding="utf-8"))
    _validate_plan(ledger, plan)
    return plan


def _module_ids(plan: dict) -> list[str]:
    return sorted(
        gid for gid, group in plan["groups"].items()
        if group.get("member_ids") and not group.get("children") and gid not in SUPPORT_IDS
    )


def _input_hash(ledger: dict, plan: dict, group_id: str, *, _static_projection=None) -> str:
    group = plan["groups"][group_id]
    symbols = ledger["inventory"]["symbols"]
    files = ledger["inventory"]["files"]
    basis = {
        "contract": "module-author/1", "revision": ledger["source_revision"],
        "group": group, "members": [
            (sid, symbols[sid]["path"], files[symbols[sid]["path"]]["content_hash"])
            for sid in group["member_ids"]
        ],
    }
    if ledger.get("fact_workflow_version"):
        facts = _accepted_facts(ledger, group_id, group, require_complete=False)
        attributions = _accepted_attributions(ledger, group_id, group, require_complete=False)
        basis["contract"] = "module-author/fact-synthesis-2"
        basis["fact_hashes"] = [(sid, _digest(record)) for sid, record in sorted(facts.items())]
        basis["fact_pending"] = sorted(
            sid for sid in group["member_ids"]
            if symbols[sid]["kind"] in {"function", "method", "lambda"} and sid not in facts
        )
        if ledger.get("attribution_workflow_version"):
            basis["attribution_hashes"] = [
                (sid, _digest(record)) for sid, record in sorted(attributions.items())]
            basis["attribution_pending"] = sorted(
                sid for sid in group["member_ids"]
                if symbols[sid]["kind"] not in {"function", "method", "lambda"}
                and sid not in attributions
            )
        if _static_projection is None:
            literals = accepted_numeric_literals(ledger)
            return_keys = accepted_return_keys(ledger)
        else:
            literals, return_keys = _static_projection
        basis["literal_projection_version"] = PROJECTION_VERSION
        basis["source_literals"] = {
            sid: literals[sid] for sid in sorted(group["member_ids"]) if sid in literals
        }
        basis["return_keys"] = {
            sid: return_keys[sid] for sid in sorted(group["member_ids"]) if sid in return_keys
        }
    return _digest(basis)


def _accepted_facts(ledger: dict, group_id: str, group: dict, *,
                    require_complete: bool = True) -> dict[str, dict]:
    symbols = ledger["inventory"]["symbols"]
    reviews = ledger.get("fact_reviews") or {}
    details = ledger.get("details") or {}
    facts: dict[str, dict] = {}
    missing: list[str] = []
    for sid in group["member_ids"]:
        if symbols[sid]["kind"] not in {"function", "method", "lambda"}:
            continue
        detail = details.get(sid)
        review = reviews.get(sid) or {}
        if not isinstance(detail, dict) or review.get("state") not in {"source_checked", "batch_accepted", "mechanically_validated"} or (
            review.get("content_sha256") != _digest(detail)
        ):
            missing.append(sid)
        else:
            facts[sid] = detail
    if missing and require_complete:
        raise ValueError(f"module {group_id} has {len(missing)} unexplained executable symbols; first={missing[0]}")
    return facts


def _accepted_attributions(ledger: dict, group_id: str, group: dict, *,
                           require_complete: bool = True) -> dict[str, dict]:
    """Accepted attribution records for non-executable members, when registered.

    Before ``attribution-init`` runs there is no attribution contract in the
    ledger and this returns empty without blocking. Once attribution batches
    exist, a module author claim requires every non-executable member to hold
    an accepted, hash-bound attribution, so classes and module residuals are
    never silently skipped by module synthesis.
    """
    if not ledger.get("attribution_workflow_version"):
        return {}
    symbols = ledger["inventory"]["symbols"]
    reviews = ledger.get("fact_reviews") or {}
    details = ledger.get("details") or {}
    attributions: dict[str, dict] = {}
    missing: list[str] = []
    for sid in group["member_ids"]:
        if symbols[sid]["kind"] in {"function", "method", "lambda"}:
            continue
        detail = details.get(sid)
        review = reviews.get(sid) or {}
        if not isinstance(detail, dict) or review.get("state") not in {"source_checked", "batch_accepted", "syntax_evidenced", "mechanically_validated"} or (
            review.get("content_sha256") != _digest(detail)
        ):
            missing.append(sid)
        else:
            attributions[sid] = detail
    if missing and require_complete:
        raise ValueError(f"module {group_id} has {len(missing)} unattributed non-executable "
                         f"symbols; first={missing[0]}")
    return attributions


def _fact_summary_packet(ledger: dict, plan: dict, group_id: str) -> dict:
    from cbe.behavior_contracts import accepted_projection
    group = plan["groups"][group_id]
    facts = _accepted_facts(ledger, group_id, group)
    attributions = _accepted_attributions(ledger, group_id, group)
    literals = accepted_numeric_literals(ledger)
    return_keys = accepted_return_keys(ledger)
    reviews = ledger.get("fact_reviews") or {}
    rows = [
        {"symbol_id": sid, "behavior": record["behavior"],
         "source_refs": (record.get("provenance") or {}).get("source_refs") or [],
         "review_state": reviews[sid]["state"]}
        for sid, record in sorted(facts.items())
    ]
    attribution_rows = [
        {"symbol_id": sid, "behavior": record["behavior"],
         "source_refs": (record.get("provenance") or {}).get("source_refs") or [],
         "review_state": reviews[sid]["state"], "kind": "attribution",
         **({"canonical_member_ids": record["canonical_member_ids"]}
            if record.get("canonical_member_ids") else {})}
        for sid, record in sorted(attributions.items())
    ]
    edges = [
        {"kind": edge.get("kind"), "subject_id": edge.get("subject_id"),
         "target_id": edge.get("target_id"), "status": edge.get("status")}
        for edge in (ledger.get("graph") or {}).get("edges") or []
        if edge.get("subject_id") in set(group["member_ids"])
    ]
    context = json.dumps({
        "module_id": group_id, "reader_question": group.get("question_answered"),
        "facts": rows, "attributions": attribution_rows, "graph_edges": edges[:250],
        "source_literals": [item for sid in group["member_ids"]
                            for item in literals.get(sid, [])],
        "return_keys": {sid: return_keys[sid] for sid in group["member_ids"]
                        if sid in return_keys},
        "omitted_graph_edges": max(0, len(edges) - 250),
        "behavior_contracts": {
            sid: {key: value for key, value in accepted_projection(ledger, sid).items()
                  if key in {"claims", "claim_refs", "local_view_gaps", "current_unresolved"}}
            for sid, record in sorted(facts.items())
            if (record.get("provenance") or {}).get("behavior_contract")},
    }, ensure_ascii=False)
    module_count = max(1, sum(bool(group.get("member_ids")) for group in plan["groups"].values()))
    relationship_tokens = max(1, int((ledger.get("documentation_policy") or {}).get(
        "group_reserve_tokens", 300)) * 2 // (2 * module_count + 1))
    instruction = (
        "Synthesize a concise implementation-module explanation from the source-bound facts "
        "and partial graph below, respecting each review_state. mechanically_validated means "
        "schema/source/citation checks passed, narrative semantics remain unverified. "
        "`attributions` rows carry their stated semantic or syntax evidence grade. "
        "Add only module-level relationships, execution ordering and genuine cross-boundary "
        "unknowns; reference authoritative canonical facts/shared claims instead of repeating "
        "their algorithms or declarations. behavior_contracts separate local_view_gaps from "
        "current_unresolved; accepted dependency availability is a locator, not proof of a "
        "runtime relation. Do not preserve a local 'not in this packet' gap as a terminal "
        "absence when the bound accepted dependency below supplies the needed behavior. "
        "explicit member attributions for classes and module residuals; cite them like facts. "
        "An attribution labelled syntax_evidenced is program-verified syntax only, not "
        "source_checked or batch_accepted behavioral evidence; do not infer import effects, "
        "runtime bindings, or class construction from it. "
        "`source_literals` are mechanically checked frozen AST syntax, not model-reviewed "
        "runtime values or additional source reading; use them only as literal numeric declarations. "
        "Absent literals may be dynamic or uncertain; do not infer they do not exist or have no effect. "
        "`return_keys` lists only keys of direct frozen return-dict syntax, not every runtime path. "
        "Do not read source again or turn structural edges into proven "
        "runtime behavior. Write the module's behavior for a reader; omit "
        "inventory counts, reviewer process, and ledger mechanics from the prose. If graph_edges "
        "is empty, do not mention graph evidence.\n"
        "Output schema (imports are rejected otherwise): return exactly the five keys "
        "summary, flow, uncertainties, key_symbols, source_refs. key_symbols: a nonempty list of "
        "1 to 8 exact member symbol IDs from the supplied facts or attributions (never empty, "
        "never names). "
        "source_refs: a nonempty list of 1 to 12 objects {path, line} taken from the supplied fact "
        "citations, no duplicates. summary + flow + uncertainties together should aim near "
        f"{relationship_tokens} o200k_base display tokens from the shared relationship pool. "
        "Write only relationships absent from authoritative member rules; use stable member IDs "
        "for those rules. Put each unresolved relationship once in uncertainties; the other fields "
        "may refer to it. Keep necessary ordering/maintenance uncertainty even if the recommendation "
        "is exceeded; report actual size, never drop necessary information to fit."
        " summary, flow and uncertainties must be strings, never arrays or objects. "
        "Keep all uncertainty clauses in one string, separated by sentences or newlines."
    )
    return {
        "instruction": instruction, "source_context": context,
        "prompt": instruction + "\n\n" + context,
        "metadata": {"source_revision": ledger["source_revision"], "group_id": group_id,
                     "selected_sources": [], "omitted_sources": [],
                     "member_count": len(group["member_ids"]),
                     "prompt_token_count": count_text_tokens(instruction + "\n\n" + context),
                     "source_token_count": 0},
    }


def _prompt_projection(packet: dict, kind: str) -> bytes:
    envelope = packet["envelope"]
    if kind == "module_author":
        result_contract = (
            "Return exactly one JSON object without Markdown: "
            '{"envelope": <the envelope above>, '
            '"content": '+MODULE_CONTENT_SCHEMA+'}. '
            "The controller records role identity from the claim and native session; do not guess model identity."
        )
    else:
        result_contract = (
            "Return evidence_ref equal to evidence_path; the controller saves this response as "
            "the independent review record. Do not use tools. Return exactly one JSON "
            'object without Markdown: {"envelope": <the envelope above>, '
            '"verdict": "accepted" or "revision_required", "content_sha256": <draft_content_sha256>, '
            '"findings": [], "evidence_ref": <absolute evidence_path>}. '
            "The controller records role identity from the claim/native session; do not guess model identity."
        )
    prompt = (
        packet["prompt"] + "\n\nEnvelope (copy verbatim):\n"
        + json.dumps(envelope, ensure_ascii=False)
        + ("\nEvidence path: " + packet["evidence_path"]
           + "\nDraft content_sha256: " + packet["draft_content_sha256"]
           if kind == "module_review" else "")
        + "\n\n" + result_contract + "\n"
    )
    return prompt.encode()


def _ensure(ledger: dict, plan: dict, legacy_package: dict | None, *, _static_projection=None) -> None:
    if (ledger.get("documentation_policy") or {}).get("version") != "module-first-v2":
        raise ValueError("module workflow requires module-first-v2")
    if ledger.get("module_workflow_version"):
        return
    accepted = validate_module_explanations(
        ledger, plan, legacy_package or {"source_revision": ledger["source_revision"], "modules": {}}
    )
    ledger["module_workflow_version"] = 1
    ledger["module_records"] = {
        gid: {"state": "accepted", "record": record, "origin": "legacy_package", "usage": "unavailable"}
        for gid, record in accepted.items()
    }
    tasks = ledger.setdefault("tasks", {})
    for gid in _module_ids(plan):
        author_id = f"task:module_author:{gid}"
        review_id = f"task:module_review:{gid}"
        input_hash = _input_hash(ledger, plan, gid, _static_projection=_static_projection)
        done = gid in accepted
        tasks[author_id] = TaskRecord(
            author_id, "module_author", [gid], input_hash,
            "committed" if done else "pending", output_refs=[gid] if done else [],
        ).to_dict()
        tasks[review_id] = TaskRecord(
            review_id, "module_review", [gid],
            explanation_content_sha256(accepted[gid]) if done else "",
            "committed" if done else "pending", output_refs=[gid] if done else [],
        ).to_dict()


def reopen_dependency_tasks(ledger: dict, author: TaskRecord, review: TaskRecord,
                            input_hash: str, reason: str) -> None:
    """Existing task epochs may advance only after all old calls are settled."""
    for task in (author, review):
        if task.state == "leased" or any(
            call.get("task_id") == task.task_id and call.get("state") in {"prepared", "sent", "uncertain"}
            for call in ledger.get("calls", {}).values()
        ):
            raise StaleWriteError(f"{task.task_id} dependency changed with an active or uncertain call; reconcile before rebuilding")
    for task in (author, review):
        task.state = "pending"
        task.generation += 1
        task.owner = task.owner_pid = task.lease_until = None
        task.output_refs = []
        task.input_hash = input_hash if task is author else ""
        for key in ("call_id", "packet_hash", "result_sha256"):
            task.extra.pop(key, None)
        task.residual.append({"code": "dependency_input_changed", "reason": reason})
        ledger["tasks"][task.task_id] = task.to_dict()


def retain_accepted_history(item: dict) -> None:
    if item.get("state") == "accepted":
        snapshot = {key: value for key, value in item.items() if key != "history"}
        item.setdefault("history", []).append(json.loads(json.dumps(snapshot)))
    item["state"] = "stale"


def initialize(run_dir: Path, *, _defer_busy: bool = False) -> dict:
    """Adopt a historical package once, then keep the ledger authoritative."""
    run_dir = Path(run_dir).resolve()
    store = LedgerStore(run_dir)
    legacy_path = run_dir / "module_explanations.json"
    legacy = json.loads(legacy_path.read_text(encoding="utf-8")) if legacy_path.exists() else None
    blocked = []

    def mutate(ledger: dict) -> dict | None:
        plan = _plan(run_dir, ledger)
        # These projections depend only on frozen inventory/source bytes and
        # current details/fact_reviews. This locked loop changes only module
        # tasks/records, so one snapshot suffices for every group's hash.
        # Keep the default _input_hash entry fresh; no persistent/global cache.
        projection = ((accepted_numeric_literals(ledger), accepted_return_keys(ledger))
                      if ledger.get("fact_workflow_version") and _module_ids(plan) else None)
        if ledger.get("module_workflow_version"):
            changed = False
            for gid in _module_ids(plan):
                author = TaskRecord.from_dict(ledger["tasks"][f"task:module_author:{gid}"])
                current_hash = _input_hash(ledger, plan, gid, _static_projection=projection)
                if author.input_hash == current_hash:
                    continue
                review = TaskRecord.from_dict(ledger["tasks"][f"task:module_review:{gid}"])
                try:
                    reopen_dependency_tasks(ledger, author, review, current_hash,
                        "Accepted fact inputs changed; preserve supported module content and update dependent claims.")
                except StaleWriteError as exc:
                    if not _defer_busy:
                        raise
                    tids = {author.task_id, review.task_id}
                    blocked.append({"module_id": gid, "reason": str(exc),
                        "call_ids": [cid for cid, call in ledger.get("calls", {}).items()
                                     if call.get("task_id") in tids and call.get("state") in {"prepared", "sent", "uncertain"}],
                        "leased_task_ids": [t.task_id for t in (author, review) if t.state == "leased"]})
                    continue
                item = ledger.get("module_records", {}).get(gid)
                if item:
                    retain_accepted_history(item)
                changed = True
            return ledger if changed else None
        _ensure(ledger, plan, legacy, _static_projection=projection)
        return ledger

    ledger = store.mutate(mutate)
    return {"run_id": ledger["run_id"], "module_count": len(_module_ids(_plan(run_dir, ledger))),
            "accepted": len(accepted_package(ledger)["modules"]),
            **({"blocked_dependencies": blocked} if blocked else {})}


def accepted_package(ledger: dict) -> dict:
    return {"source_revision": ledger["source_revision"], "modules": {
        gid: item["record"] for gid, item in (ledger.get("module_records") or {}).items()
        if item.get("state") == "accepted" and _fact_dependencies_current(ledger, item)
    }}


def _fact_dependencies_current(ledger: dict, item: dict) -> bool:
    hashes = item.get("fact_hashes")
    if hashes is None:
        return True  # Historical acceptance remains visible, with legacy origin disclosed.
    reviews = ledger.get("fact_reviews") or {}
    details = ledger.get("details") or {}
    return all(
        isinstance(details.get(sid), dict)
        and (reviews.get(sid) or {}).get("state") in {"source_checked", "batch_accepted", "syntax_evidenced", "mechanically_validated"}
        and (reviews.get(sid) or {}).get("content_sha256") == digest
        and _digest(details[sid]) == digest
        for sid, digest in hashes.items()
    )


def _lease(task: TaskRecord, owner: str, seconds: int = 3600) -> TaskRecord:
    now = utc_now()
    if task.state == "committed":
        raise LeaseError(f"{task.task_id} already committed")
    if task.state == "leased" and task.lease_until and task.lease_until > iso(now):
        raise LeaseError(f"{task.task_id} leased by {task.owner} until {task.lease_until}")
    task.generation += 1
    task.state = "leased"
    task.owner = owner
    task.owner_pid = None  # external role lifetime is not the CLI process lifetime
    task.lease_until = iso(now + timedelta(seconds=seconds))
    # Current findings are input to the repair, not discarded lease metadata.
    return task


def claim(run_dir: Path, group_id: str, *, kind: str, owner: str,
          max_source_tokens: int = 24000, _workflow_initialized: bool = False) -> dict:
    """Claim exactly one author or review task and persist its source presentation."""
    if kind not in {"module_author", "module_review"}:
        raise ValueError("kind must be module_author or module_review")
    if not owner.strip():
        raise ValueError("owner is required")
    run_dir = Path(run_dir).resolve()
    if not _workflow_initialized:
        initialize(run_dir)
    store = LedgerStore(run_dir)
    output: dict[str, Any] = {}

    def mutate(ledger: dict) -> dict:
        if not ledger.get("module_workflow_version"):
            raise StaleWriteError("module workflow initialization changed before claim")
        plan = _plan(run_dir, ledger)
        if group_id not in _module_ids(plan):
            raise ValueError(f"unknown implementation module: {group_id}")
        task_id = f"task:{kind}:{group_id}"
        pair = {f"task:module_author:{group_id}", f"task:module_review:{group_id}"}
        if any(ledger["tasks"][tid].get("state") == "leased" for tid in pair) or any(
            call.get("task_id") in pair and call.get("state") in {"prepared", "sent", "uncertain"}
            for call in ledger.get("calls", {}).values()):
            raise LeaseError("requested module has an active or uncertain call; reconcile its original epoch")
        task = TaskRecord.from_dict(ledger["tasks"][task_id])
        draft = (ledger.get("module_records") or {}).get(group_id)
        if kind == "module_review":
            if not draft or draft["state"] != "draft":
                raise ValueError("review requires a current author draft")
            current_hash = explanation_content_sha256(draft["record"])
        else:
            current_hash = _input_hash(ledger, plan, group_id)
        if task.input_hash != current_hash:
            if task.state not in {"pending", "needs_repair"} or kind != "module_author":
                raise StaleWriteError("module task input changed since creation")
            task.input_hash = current_hash
            task.generation += 1
        task = _lease(task, owner)
        fact_mode = bool(ledger.get("fact_workflow_version"))
        packet = (
            _fact_summary_packet(ledger, plan, group_id)
            if fact_mode else build_module_author_packet(
                ledger, plan, group_id, max_source_tokens=max_source_tokens)
        )
        if kind == "module_author" and draft and draft.get("state") == "revision_required":
            repair = {"previous_draft": draft["record"], "review_findings": draft.get("findings") or []}
            packet["repair_context"] = repair
            packet["prompt"] += (
                "\n\nRevise the previous draft against the review findings. Preserve supported "
                "behavior, remove unsupported claims, and omit all claims about inventory counts, "
                "review findings, inspected spans, or reviewer process. Keep only behavior, flow, "
                "and genuine behavioral uncertainty in the prose; source_refs remain structured "
                "fact provenance.\n"
                + json.dumps(repair, ensure_ascii=False)
            )
        metadata = packet["metadata"]
        if kind == "module_review":
            packet["instruction"] = (
                "Check every material assertion in the draft against the supplied accepted facts, "
                "attributions and graph. Accept only supported assertions. Identify the exact "
                "unsupported sentence and missing fact in findings; request revision_required "
                "when a claim adds behavior or failure conditions not in these facts. Distinguish "
                "source_checked, batch_accepted, mechanically_validated (narrative unverified), and program syntax_evidenced provenance. "
                "Syntax evidence proves no runtime import or construction effects. The graph alone does not prove "
                "runtime behavior. This review reads no source: do not claim a source inspection. "
                "Return verdict, findings and content_sha256."
                if fact_mode else
                "Independently check each draft claim against the bounded frozen source sample "
                "in this packet. Report unsupported claims and only spans actually checked. "
                "Return verdict, findings and content_sha256."
            )
            packet["draft"] = draft["record"]
            packet["prompt"] = (
                packet["instruction"] + "\n\n" + packet["source_context"]
                + "\n\nDraft to verify:\n" + json.dumps(draft["record"], ensure_ascii=False)
            )
        if task.residual:
            packet["validation_findings"] = list(task.residual)
            packet["prompt"] += "\n\nCurrent validation findings to correct:\n" + json.dumps(task.residual, ensure_ascii=False)
        if kind == "module_author" and task.extra.get("business_rejection_history"):
            rejected = task.extra["business_rejection_history"][-1]
            original_path = Path(rejected["result_ref"])
            original_bytes = original_path.read_bytes()
            if hashlib.sha256(original_bytes).hexdigest() != rejected["raw_sha256"]:
                raise StaleWriteError("historical rejected business raw changed before repair claim")
            packet["rejected_business_result"] = json.loads(original_bytes).get("content")
            packet["prompt"] += ("\n\nOriginal completed but mechanically rejected business content, for a fresh author revision. "
                "Correct the format; retain every supported module relationship, uncertainty and provenance obligation. "
                "Do not assert a physical/provider failure and do not copy a normalized old raw as a new result.\n"
                + json.dumps(packet["rejected_business_result"],ensure_ascii=False))
        call_id = f"call:module:{uuid.uuid4().hex}"
        envelope = {"task_id": task_id, "generation": task.generation,
                    "owner": owner, "input_hash": task.input_hash, "call_id": call_id}
        packet["envelope"] = envelope
        if kind == "module_review":
            packet["evidence_path"] = str(run_dir / "reviews" / f"{call_id}.md")
            packet["draft_content_sha256"] = explanation_content_sha256(draft["record"])
        encoded = (json.dumps(packet, ensure_ascii=False, indent=2) + "\n").encode()
        packet_path = run_dir / "packets" / f"{call_id}.json"
        packet_hash = hashlib.sha256(encoded).hexdigest()
        prompt = _prompt_projection(packet, kind)
        prompt_path = run_dir / "prompts" / f"{call_id}.txt"
        prompt_hash = hashlib.sha256(prompt).hexdigest()
        # The context also carries source labels and line markers. The 2S
        # source budget counts only the exact presented frozen spans.
        source_chars = sum(s["end_char"] - s["start_char"] for s in metadata["selected_sources"])
        call = CallRecord(call_id, task_id, task.input_hash, [
            {"path": s["path"], "start": s["start_char"], "end": s["end_char"]}
            for s in metadata["selected_sources"]
        ], source_chars, "prepared", packet_hash=packet_hash,
            prompt_chars=len(prompt.decode("utf-8")), extra={
                "external_subagent": True, "group_id": group_id,
                "packet_path": str(packet_path), "prompt_path": str(prompt_path),
                "prompt_sha256": prompt_hash, "prompt_projection": "module-text-v1",
                "preparation_stage": "local_artifacts_pending",
            })
        reserve_call(ledger, call)
        task.extra["call_id"] = call_id
        task.extra["packet_hash"] = packet_hash
        ledger["tasks"][task_id] = task.to_dict()
        output.update({"task_id": task_id, "call_id": call_id, "envelope": envelope,
                       "packet_path": str(packet_path), "packet_sha256": packet_hash,
                       "prompt_path": str(prompt_path), "prompt_sha256": prompt_hash,
                       "result_path": str(run_dir / "raw" / f"{call_id}.json")})
        output["_local_artifacts"] = [(packet_path, encoded), (prompt_path, prompt)]
        return ledger

    store.mutate(mutate)
    from cbe.module_facts import finalize_local_preparation
    finalize_local_preparation(run_dir, output, output.pop("_local_artifacts"))
    return output


def _require_envelope(task: TaskRecord, envelope: dict, ledger: dict, group_id: str,
                      plan: dict) -> None:
    for key, expected in (("task_id", task.task_id), ("owner", task.owner),
                          ("generation", task.generation), ("input_hash", task.input_hash),
                          ("call_id", task.extra.get("call_id"))):
        if envelope.get(key) != expected:
            raise StaleWriteError(f"module envelope {key} mismatch")
    if task.state != "leased":
        raise LeaseError(f"module task is {task.state}, expected leased")
    if task.kind == "module_author" and task.input_hash != _input_hash(ledger, plan, group_id):
        raise StaleWriteError("module source or membership changed")
    if task.kind == "module_review":
        author = ledger["tasks"][f"task:module_author:{group_id}"]
        if author["input_hash"] != _input_hash(ledger, plan, group_id):
            raise StaleWriteError("module fact dependencies changed after review claim")
        draft = (ledger.get("module_records") or {}).get(group_id)
        if not draft or draft.get("state") != "draft" or task.input_hash != explanation_content_sha256(draft["record"]):
            raise StaleWriteError("module draft changed since review claim")


def import_result(run_dir: Path, task_id: str, result_path: Path, *, usage_receipt: Path | None = None) -> dict:
    run_dir = Path(run_dir).resolve()
    result_path = Path(result_path).resolve()
    result_bytes = result_path.read_bytes()
    result_hash = hashlib.sha256(result_bytes).hexdigest()
    payload = json.loads(result_bytes)
    envelope = payload.get("envelope")
    if not isinstance(envelope, dict):
        raise ValueError("module result requires envelope")
    envelope_origin = "model_echo"
    usage: dict | str = "unavailable"
    if usage_receipt is not None:
        receipt = json.loads(Path(usage_receipt).read_text(encoding="utf-8"))
        if not isinstance(receipt, dict) or receipt.get("call_id") != envelope.get("call_id"):
            raise ValueError("usage receipt must bind the claimed call_id")
        usage = copy_usage_fields(receipt.get("usage"))
    store = LedgerStore(run_dir)
    output: dict[str, Any] = {}

    def mutate(ledger: dict) -> dict | None:
        plan = _plan(run_dir, ledger)
        raw = (ledger.get("tasks") or {}).get(task_id)
        if raw is None:
            raise ValueError(f"unknown task: {task_id}")
        task = TaskRecord.from_dict(raw)
        gid = task.input_ids[0]
        if envelope.get("input_hash") != task.input_hash:
            call_id = task.extra.get("call_id")
            bound = (ledger.get("calls") or {}).get(call_id) or {}
            expected_raw = run_dir / "raw" / f"{call_id}.json"
            if (result_path != expected_raw or bound.get("state") != "sent"
                or not (bound.get("extra") or {}).get("delivery_receipt")
                or any(envelope.get(key) != value for key, value in (
                    ("task_id", task.task_id), ("generation", task.generation),
                    ("owner", task.owner), ("call_id", call_id)
                ))):
                raise StaleWriteError("module envelope input_hash mismatch")
            # The controller owns the hash; a model echo typo cannot change
            # the positively delivered call's frozen input binding.
            envelope["input_hash"] = task.input_hash
            payload["envelope"] = envelope
            nonlocal envelope_origin
            envelope_origin = "controller_from_delivered_call"
        if task.state == "committed" and all(envelope.get(key) == value for key, value in (
            ("task_id", task.task_id), ("owner", task.owner), ("generation", task.generation),
            ("input_hash", task.input_hash), ("call_id", task.extra.get("call_id"))
        )) and task.extra.get("result_sha256") == result_hash:
            output.update({"task_id": task_id, "state": "committed", "idempotent": True})
            return None
        _require_envelope(task, envelope, ledger, gid, plan)
        call_id = envelope["call_id"]
        current_call = ledger["calls"][call_id]
        if current_call.get("state") != "sent":
            raise ValueError("module result needs positive host delivery evidence")
        if usage == "unavailable" and isinstance(current_call.get("usage"), dict):
            actual_usage: dict | str = current_call["usage"]
        else:
            actual_usage = usage
        if task.kind == "module_author":
            content = _dict_with_keys(payload.get("content"), CONTENT_KEYS, "module content")
            members = _checked_module(gid, plan["groups"], ledger["inventory"]["symbols"], ledger["inventory"]["files"])
            _checked_content(content, members, _frozen_file_lines(ledger, ledger["inventory"]), gid)
            reported_author = payload.get("author_id")
            author = task.owner
            author_session = current_call.get("role_session_id")
            if not author or not author_session:
                raise ValueError("module author needs a claimed owner and native session")
            record = {"author_id": author, **content}
            fact_hashes = None
            if ledger.get("fact_workflow_version"):
                facts = _accepted_facts(ledger, gid, plan["groups"][gid])
                attributions = _accepted_attributions(ledger, gid, plan["groups"][gid])
                fact_hashes = {sid: _digest(value) for sid, value in {**facts, **attributions}.items()}
            history = (ledger.get("module_records", {}).get(gid) or {}).get("history") or []
            ledger.setdefault("module_records", {})[gid] = {"state": "draft", "record": record,
                **({"history": history} if history else {}), "input_hash": task.input_hash,
                "usage": actual_usage, "result_ref": str(result_path),
                "fact_hashes": fact_hashes, "author_session_id": author_session,
                "reported_author_id": reported_author,
                "reported_author_identity_mismatch": reported_author is not None and reported_author != author}
            review_id = f"task:module_review:{gid}"
            review = TaskRecord.from_dict(ledger["tasks"][review_id])
            review.input_hash = explanation_content_sha256(record)
            review.state = "pending"
            review.generation += 1
            review.owner = None
            review.lease_until = None
            ledger["tasks"][review_id] = review.to_dict()
            task.state = "committed"
            task.output_refs = [gid]
        elif task.kind == "module_review":
            draft = ledger["module_records"][gid]
            reported_reviewer = payload.get("reviewer_id")
            reviewer = task.owner
            reviewer_session = current_call.get("role_session_id")
            author_task = TaskRecord.from_dict(ledger["tasks"][f"task:module_author:{gid}"])
            author_call = (ledger.get("calls") or {}).get(author_task.extra.get("call_id")) or {}
            author_session = draft.get("author_session_id") or author_call.get("role_session_id")
            if not reviewer or not reviewer_session or reviewer == draft["record"]["author_id"] or (
                not author_session or reviewer_session == author_session
            ):
                raise ValueError("module reviewer must be a distinct native session")
            verdict = payload.get("verdict")
            if verdict not in {"accepted", "revision_required"}:
                raise ValueError("review verdict must be accepted or revision_required")
            if payload.get("content_sha256") != explanation_content_sha256(draft["record"]):
                raise StaleWriteError("review content hash mismatch")
            expected_evidence = run_dir / "reviews" / f"{call_id}.md"
            evidence = payload.get("evidence_ref") or str(expected_evidence)
            if not Path(evidence).is_absolute() or not Path(evidence).is_file():
                raise ValueError("review evidence_ref must exist")
            if verdict == "accepted":
                record = {**draft["record"], "review": {
                    "reviewer_id": reviewer, "decision": "accepted",
                    "content_sha256": payload["content_sha256"],
                    "source_revision": ledger["source_revision"], "evidence_ref": evidence,
                }}
                validate_module_explanations(ledger, plan, {"source_revision": ledger["source_revision"], "modules": {gid: record}})
                draft.update({"state": "accepted", "record": record, "review_usage": actual_usage,
                              "review_result_ref": str(result_path),
                              "reviewer_session_id": reviewer_session,
                              "reported_reviewer_id": reported_reviewer,
                              "reported_reviewer_identity_mismatch": reported_reviewer is not None and reported_reviewer != reviewer})
                task.state = "committed"
                task.output_refs = [gid]
            else:
                findings = payload.get("findings")
                if not isinstance(findings, list) or not findings:
                    raise ValueError("revision_required needs findings")
                draft["state"] = "revision_required"
                draft["review_usage"] = actual_usage
                draft["findings"] = findings
                author_task.state = "needs_repair"
                author_task.generation += 1
                author_task.owner = None
                author_task.lease_until = None
                author_task.residual = findings
                ledger["tasks"][author_task.task_id] = author_task.to_dict()
                task.state = "needs_repair"
                task.residual = findings
        else:
            raise ValueError(f"unsupported module task: {task.kind}")
        task.extra["result_sha256"] = result_hash
        ledger["tasks"][task_id] = task.to_dict()
        mark_call(ledger, call_id, state="imported", raw_path=str(result_path), usage=actual_usage if isinstance(actual_usage, dict) else None,
                  extra={"usage_receipt": str(usage_receipt) if usage_receipt else None,
                         "usage_status": "reported" if isinstance(actual_usage, dict) else "unavailable",
                         "envelope_origin": envelope_origin,
                         "raw_result_sha256": result_hash})
        output.update({"task_id": task_id, "state": task.state, "group_id": gid,
                       "accepted": ledger["module_records"][gid]["state"] == "accepted"})
        return ledger

    store.mutate(mutate)
    return output


def release(run_dir: Path, task_id: str, *, owner: str) -> dict:
    store = LedgerStore(run_dir)

    def mutate(ledger: dict) -> dict:
        task = TaskRecord.from_dict(ledger["tasks"][task_id])
        if task.state != "leased" or task.owner != owner:
            raise LeaseError("only the current module owner may release a lease")
        current_id = task.extra.get("call_id")
        if current_id:
            call = ledger["calls"][current_id]
            if call.get("state") in {"prepared", "sent", "uncertain"}:
                raise LeaseError(f"{current_id} delivery is unresolved; use native-record terminal evidence or call-reconcile before releasing")
        task.state = "pending"
        task.generation += 1
        task.owner = None
        task.lease_until = None
        call_id = task.extra.pop("call_id", None)
        ledger["tasks"][task_id] = task.to_dict()
        if call_id:
            state = ledger["calls"][call_id]["state"]
            if state != "released":
                raise LeaseError(f"{call_id} has a completed result; preserve/import it instead of releasing")
        return ledger

    store.mutate(mutate)
    return {"task_id": task_id, "state": "pending"}
