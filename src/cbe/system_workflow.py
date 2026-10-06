"""System-level synthesis over accepted implementation modules.

One author and one independent reviewer produce the codebase-level semantics
(what the system is, how a request flows, how processes interact) strictly from
accepted module explanations and the frozen graph — never from unevidenced
source claims. The record lives in the same ledger as facts and modules; the
published INDEX page shows it only in its accepted, hash-bound form.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cbe.module_explanations import validate_module_explanations
from cbe.module_workflow import SUPPORT_IDS, accepted_package, reopen_dependency_tasks, retain_accepted_history
from cbe.store import LedgerStore, TaskRecord, StaleWriteError, mark_call, utc_now
from cbe.token_budget import count_text_tokens

SYSTEM_CONTRACT = "system-synthesis/1"
CONTENT_KEYS = ("overview", "entry_points", "lifecycle", "data_flow", "uncertainties")
MAX_NARRATIVE_TOKENS = 480


def _sha_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _content_hash(record: dict[str, Any]) -> str:
    return _sha_json({key: record[key] for key in CONTENT_KEYS})


def system_state(run_dir: Path) -> dict[str, Any]:
    ledger = LedgerStore(run_dir).open()
    record = ledger.get("system_record") or {}
    return {"state": record.get("state") or "none",
            "modules_accepted": len((ledger.get("module_records") or {}))}


def initialize(run_dir: Path, *, require_modules: bool = True) -> dict[str, Any]:
    """Register the system author/review tasks once, idempotently."""
    run_dir = Path(run_dir).resolve()
    store = LedgerStore(run_dir)

    def mutate(ledger: dict) -> dict | None:
        package = accepted_package(ledger)["modules"]
        if require_modules:
            plan = json.loads((run_dir / "module_plan.json").read_text(encoding="utf-8"))
            implementation = [gid for gid, group in plan["groups"].items()
                              if group.get("member_ids") and gid not in SUPPORT_IDS]
            missing = [gid for gid in implementation if gid not in package]
            if missing:
                raise ValueError(
                    f"system synthesis requires every implementation module accepted; "
                    f"{len(missing)} pending, first={missing[0]}")
        input_hash = _input_hash(ledger, package)
        tasks = ledger.setdefault("tasks", {})
        if ledger.get("system_workflow_version"):
            author = TaskRecord.from_dict(tasks["task:system_author"])
            if author.input_hash == input_hash:
                return None
            review = TaskRecord.from_dict(tasks["task:system_review"])
            item = ledger.get("system_record")
            if item:
                item.setdefault("input_hash", author.input_hash)
            reopen_dependency_tasks(ledger, author, review, input_hash,
                "Accepted module inputs changed; preserve supported system content and update dependent claims.")
            if item:
                retain_accepted_history(item)
            return ledger
        tasks["task:system_author"] = TaskRecord(
            "task:system_author", "system_author", ["system"],
            input_hash, "pending", extra={"system_contract": SYSTEM_CONTRACT},
        ).to_dict()
        tasks["task:system_review"] = TaskRecord(
            "task:system_review", "system_review", ["system"],
            "", "pending", extra={"system_contract": SYSTEM_CONTRACT},
        ).to_dict()
        ledger["system_workflow_version"] = 1
        return ledger

    store.mutate(mutate)
    ledger = store.open()
    return {"author_state": ledger["tasks"]["task:system_author"]["state"],
            "review_state": ledger["tasks"]["task:system_review"]["state"],
            "record_state": (ledger.get("system_record") or {}).get("state") or "none"}


def _input_hash(ledger: dict, modules: dict[str, dict]) -> str:
    return _sha_json({
        "contract": SYSTEM_CONTRACT,
        "revision": ledger["source_revision"],
        "module_hashes": sorted((gid, _sha_json(record))
                                for gid, record in modules.items()),
    })


def claim(run_dir: Path, *, kind: str, owner: str) -> dict[str, Any]:
    """Lease the system author or review task and persist its packet."""
    if kind not in {"system_author", "system_review"} or not owner.strip():
        raise ValueError("kind must be system_author or system_review; owner required")
    run_dir = Path(run_dir).resolve()
    store = LedgerStore(run_dir)
    output: dict[str, Any] = {}

    def mutate(ledger: dict) -> dict:
        task_id = f"task:{kind}"
        task = TaskRecord.from_dict(ledger["tasks"][task_id])
        if task.state == "stale":
            raise ValueError("system task was superseded")
        if task.state == "committed":
            raise ValueError(f"{task_id} already committed")
        now = utc_now()
        if task.state == "leased" and task.lease_until and task.lease_until > now:
            raise ValueError(f"{task_id} leased by {task.owner}")
        modules = accepted_package(ledger)["modules"]
        current_hash = _input_hash(ledger, modules)
        if kind == "system_author":
            if task.input_hash != current_hash:
                if task.state != "pending":
                    raise ValueError("system author input changed after claim")
                task.input_hash = current_hash
                task.generation += 1
            relationship_tokens = max(1, int((ledger.get("documentation_policy") or {}).get(
                "group_reserve_tokens", 300)) // (2 * max(1, len(modules)) + 1))
            instruction = (
                "Synthesize the system-level semantics of this codebase strictly from the "
                "accepted module explanations below. Write for a reader who asks: what is this "
                "system, where does execution enter, what lifecycle do key objects follow, and "
                "how does data flow between components. Do not invent behavior no module "
                "explains; name genuine open uncertainties.\n"
                "Describe only relationships between accepted modules, their entry/lifecycle "
                "ordering and genuine cross-boundary unknowns. Reference the authoritative "
                "module or member explanation; do not recopy its algorithm or shared rules.\n"
                "Output schema (otherwise rejected): return exactly the keys overview, "
                "entry_points, lifecycle, data_flow, uncertainties. Each of entry_points, "
                "lifecycle, data_flow is a terse relationship statement or a stable reference to "
                "the authoritative accepted module. Put a shared unknown once in uncertainties, "
                "then refer to it from affected fields. With one module, use its authority for "
                "entry/lifecycle/flow rather than writing the same explanation again. Aim for the "
                f"five fields together near {relationship_tokens} o200k_base display tokens from "
                "the shared relationship pool. Preserve necessary information and report actual "
                "overage; this recommendation is not an admission gate."
            )
            context = json.dumps({
                "modules": [
                    {"module_id": gid,
                     "summary": record["summary"], "flow": record["flow"],
                     "uncertainties": record["uncertainties"],
                     "key_symbols": record["key_symbols"][:4]}
                    for gid, record in sorted(modules.items())
                ],
                "graph_edges": [
                    {"kind": e.get("kind"), "subject": e.get("subject_id"),
                     "target": e.get("target_id")}
                    for e in (ledger.get("graph") or {}).get("edges") or []
                    if e.get("kind") in {"imports", "calls"}
                ][:400],
            }, ensure_ascii=False)
            prompt = instruction + "\n\n" + context
            draft = None
        else:
            record = (ledger.get("system_record") or {})
            if record.get("state") != "draft":
                raise ValueError("system review requires a current author draft")
            current_hash = _content_hash(record["record"])
            if task.input_hash and task.input_hash != current_hash:
                raise ValueError("system draft changed before review")
            task.input_hash = current_hash
            instruction = (
                "Independently check this system-level synthesis against the accepted module "
                "explanations below. Every claim must be supported by some module explanation; "
                "flag unsupported or contradictory claims as findings. Return verdict accepted "
                "or revision_required, findings, content_sha256, and an absolute evidence_ref "
                "path to your report. Do not adopt the author's claims."
            )
            context = json.dumps({
                "draft": record["record"],
                "modules": [
                    {"module_id": gid, "summary": record2["summary"], "flow": record2["flow"]}
                    for gid, record2 in sorted(modules.items())
                ],
            }, ensure_ascii=False)
            prompt = instruction + "\n\n" + context
            draft = record["record"]
        from datetime import timedelta
        task.generation += 1
        task.state = "leased"
        task.owner = owner
        task.lease_until = (utc_now() + timedelta(hours=1)).isoformat(timespec="seconds")
        call_id = f"call:system:{hashlib.sha256(f'{task_id}{task.generation}{owner}'.encode()).hexdigest()[:32]}"
        envelope = {"task_id": task_id, "generation": task.generation, "owner": owner,
                    "input_hash": task.input_hash or current_hash, "call_id": call_id}
        # The prompt is the standard deterministic message projection over this
        # packet, so delivery verification replays the exact bytes.
        payload = {
            "contract": SYSTEM_CONTRACT, "kind": kind,
            "source_revision": ledger["source_revision"],
            "instruction": instruction,
            "envelope": envelope,
            "assignments": [],
            "packet": {"path": "system-synthesis/accepted-modules"},
            "source": context,
        }
        if kind == "system_author" and task.residual:
            previous = (ledger.get("system_record") or {}).get("record")
            repair = {"previous_draft": previous, "review_findings": list(task.residual)}
            payload["repair_context"] = repair
            payload["source"] += (
                "\n\nRevise only the reported unsupported claims or validation errors; "
                "preserve the supported previous synthesis.\n" + json.dumps(repair, ensure_ascii=False))
        if kind == "system_review":
            payload["draft"] = draft
            payload["draft_content_sha256"] = current_hash
            payload["evidence_path"] = str(run_dir / "reviews" / f"{call_id}.md")
            if task.residual:
                payload["repair_findings"] = list(task.residual)
        from cbe.module_facts import _message_projection
        prompt_bytes = _message_projection(payload)
        packet_path = run_dir / "packets" / f"{call_id}.json"
        packet_bytes = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        prompt_path = run_dir / "prompts" / f"{call_id}.txt"
        evidence_path = payload.get("evidence_path")
        from cbe.models import CallRecord
        from cbe.store import reserve_call
        reserve_call(ledger, CallRecord(
            call_id=call_id, task_id=task_id, input_hash=task.input_hash or "",
            source_spans=[], source_chars=0, state="prepared",
            packet_hash=hashlib.sha256(packet_bytes).hexdigest(),
            prompt_chars=len(prompt_bytes.decode("utf-8")),
            extra={"external_subagent": True, "packet_id": task_id,
                   "packet_path": str(packet_path), "prompt_path": str(prompt_path),
                   "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
                   "evidence_path": evidence_path,
                   "preparation_stage": "local_artifacts_pending"},
        ))
        task.extra["call_id"] = call_id
        ledger["tasks"][task_id] = task.to_dict()
        output.update({"task_id": task_id, "call_id": call_id, "envelope": envelope,
                       "packet_path": str(packet_path), "prompt_path": str(prompt_path),
                       "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
                       "result_path": str(run_dir / "raw" / f"{call_id}.json"),
                       "evidence_path": evidence_path})
        output["_local_artifacts"] = [(packet_path, packet_bytes), (prompt_path, prompt_bytes)]
        return ledger

    store.mutate(mutate)
    from cbe.module_facts import finalize_local_preparation
    finalize_local_preparation(run_dir, output, output.pop("_local_artifacts"))
    return output


def import_result(run_dir: Path, task_id: str, result_path: Path) -> dict[str, Any]:
    """Import the system author or review result with delivery evidence."""
    run_dir = Path(run_dir).resolve()
    result_path = Path(result_path).resolve()
    payload = json.loads(result_path.read_bytes().decode("utf-8"))
    envelope = payload.get("envelope")
    if not isinstance(envelope, dict):
        raise ValueError("system result requires an envelope")
    store = LedgerStore(run_dir)
    output: dict[str, Any] = {}

    def mutate(ledger: dict) -> dict:
        task = TaskRecord.from_dict(ledger["tasks"][task_id])
        call = ledger["calls"].get(envelope.get("call_id")) or {}
        if call.get("state") != "sent":
            raise ValueError("system result needs positive delivery evidence")
        if call.get("task_id") != task_id or call.get("input_hash") != task.input_hash:
            raise StaleWriteError("system call no longer binds this task input")
        if task.state != "leased":
            raise StaleWriteError("system result no longer binds a leased task")
        for key in ("task_id", "generation", "owner", "input_hash"):
            if envelope.get(key) != getattr(task, key):
                raise StaleWriteError(f"system envelope {key} mismatch")
        basis = _input_hash(ledger, accepted_package(ledger)["modules"])
        expected_basis = task.input_hash if task.kind == "system_author" else (
            (ledger.get("system_record") or {}).get("input_hash")
            or (ledger.get("tasks", {}).get("task:system_author") or {}).get("input_hash"))
        if expected_basis != basis:
            raise StaleWriteError("accepted module inputs changed after system claim")
        if task.kind == "system_author":
            content = {key: payload.get(key) for key in CONTENT_KEYS}
            for key, value in content.items():
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"system content {key} must be nonempty text")
            # The target guides concise synthesis; final reader token ratio is
            # reported by render without discarding otherwise valid content.
            record = {"author_id": task.owner, **content}
            ledger["system_record"] = {
                "state": "draft", "record": record,
                "input_hash": task.input_hash,
                **({"history": ledger["system_record"]["history"]}
                   if (ledger.get("system_record") or {}).get("history") else {}),
                "result_ref": str(result_path),
                "author_session_id": call.get("role_session_id"),
            }
            review = TaskRecord.from_dict(ledger["tasks"]["task:system_review"])
            review.input_hash = _content_hash(record)
            review.state = "pending"
            review.generation += 1
            review.owner = None
            ledger["tasks"]["task:system_review"] = review.to_dict()
            task.state = "committed"
            output.update({"task_id": task_id, "state": "committed", "system": "draft"})
        elif task.kind == "system_review":
            draft = ledger.get("system_record") or {}
            if draft.get("state") != "draft":
                raise ValueError("no current system draft to review")
            verdict = payload.get("verdict")
            if verdict not in {"accepted", "revision_required"}:
                raise ValueError("system review verdict is invalid")
            if payload.get("content_sha256") != _content_hash(draft["record"]):
                raise ValueError("system review content hash mismatch")
            reviewer = task.owner
            reviewer_session = call.get("role_session_id")
            author_session = draft.get("author_session_id")
            if (reviewer == draft["record"].get("author_id")
                    or not reviewer_session or not author_session
                    or reviewer_session == author_session):
                raise ValueError("system reviewer must be a distinct native session")
            evidence = payload.get("evidence_ref")
            if not isinstance(evidence, str) or not Path(evidence).is_absolute() or not Path(evidence).is_file():
                raise ValueError("system review needs an existing absolute evidence_ref")
            if verdict == "accepted":
                accepted_record = {**draft["record"], "review": {
                    "reviewer_id": reviewer, "decision": "accepted",
                    "content_sha256": payload["content_sha256"],
                    "source_revision": ledger["source_revision"],
                    "evidence_ref": evidence,
                }}
                draft.update({"state": "accepted", "record": accepted_record,
                              "review_result_ref": str(result_path),
                              "reviewer_session_id": reviewer_session})
                task.state = "committed"
                output.update({"task_id": task_id, "state": "committed", "system": "accepted"})
            else:
                findings = payload.get("findings")
                if not isinstance(findings, list) or not findings:
                    raise ValueError("revision_required needs findings")
                draft["state"] = "revision_required"
                draft["findings"] = findings
                author = TaskRecord.from_dict(ledger["tasks"]["task:system_author"])
                author.state = "needs_repair"
                author.generation += 1
                author.owner = None
                author.residual = findings
                ledger["tasks"]["task:system_author"] = author.to_dict()
                task.state = "needs_repair"
                output.update({"task_id": task_id, "state": "needs_repair"})
        else:
            raise ValueError(f"unsupported system task: {task_id}")
        task.extra["result_sha256"] = hashlib.sha256(result_path.read_bytes()).hexdigest()
        ledger["tasks"][task_id] = task.to_dict()
        mark_call(ledger, envelope["call_id"], state="imported", raw_path=str(result_path))
        return ledger

    store.mutate(mutate)
    return output


def accepted_system(ledger: dict) -> dict[str, Any] | None:
    """The accepted system record, hash-consistent with its review."""
    record = (ledger.get("system_record") or {})
    if record.get("state") != "accepted":
        return None
    basis = record.get("input_hash") or (ledger.get("tasks", {}).get("task:system_author") or {}).get("input_hash")
    if basis != _input_hash(ledger, accepted_package(ledger)["modules"]):
        return None
    content = record.get("record") or {}
    review = content.get("review") or {}
    if review.get("decision") not in {"accepted", "mechanically_validated"}:
        return None
    if review.get("content_sha256") != _content_hash(content):
        return None
    return content
