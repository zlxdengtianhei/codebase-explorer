"""Explicit controller abandonment: retry obligations, retain unknown delivery.

This is an operator decision, never evidence that an old call was not sent.
The old call stays uncertain; its original offer, usage and raw are preserved.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cbe.store import LedgerStore, StaleWriteError, pid_alive, sync_budget, utc_now, iso


def retry_authorized(call: dict) -> bool:
    decision = (call.get("extra") or {}).get("controller_abandonment") or {}
    return (decision.get("schema") == "native-controller-abandonment/1"
            and decision.get("call_id") == call.get("call_id")
            and decision.get("input_hash") == call.get("input_hash")
            and decision.get("retry_unaccepted_obligations") is True)


def abandon(run_dir: Path, call_id: str, decision_path: Path) -> dict:
    """CAS a single operator-authorized current offer into historical uncertainty."""
    run_dir = Path(run_dir).resolve()
    encoded = Path(decision_path).read_bytes()
    decision = json.loads(encoded)
    if not isinstance(decision, dict):
        raise ValueError("controller abandonment decision must be an object")
    if (decision.get("schema") != "native-controller-abandonment/1"
        or decision.get("controller_stopped") is not True
        or type(decision.get("active_child_count")) is not int or decision.get("active_child_count") != 0
        or decision.get("retry_unaccepted_obligations") is not True
        or decision.get("permission_blocked") is not False
        or not isinstance(decision.get("operator"), str) or not decision["operator"].strip()
        or not isinstance(decision.get("reason"), str) or len(decision["reason"].strip()) < 20):
        raise ValueError("explicit operator/stopped controller/no active child/no permission denial/retry authorization required")
    digest = hashlib.sha256(encoded).hexdigest()
    store = LedgerStore(run_dir)
    def mutate(ledger):
        call = ledger.get("calls", {}).get(call_id)
        if not call:
            raise StaleWriteError("unknown native call")
        prior = (call.get("extra") or {}).get("controller_abandonment")
        if prior:
            if prior.get("decision_sha256") != digest:
                raise StaleWriteError("controller abandonment decision changed")
            return None
        task = ledger.get("tasks", {}).get(call["task_id"]) or {}
        handoff = call.get("extra", {}).get("native_handoff") or {}
        expected = {"run_id": ledger["run_id"], "source_revision": ledger["source_revision"],
                    "ledger_revision": ledger["ledger_revision"], "call_id": call_id,
                    "task_id": call["task_id"], "input_hash": call["input_hash"],
                    "generation": task.get("generation"), "owner": task.get("owner")}
        if any(decision.get(k) != v for k, v in expected.items()):
            raise StaleWriteError("abandonment CAS run/source/revision/call/task/input/generation/owner differs")
        if (task.get("state") != "leased" or task.get("output_refs")
            or task.get("extra", {}).get("call_id") != call_id
            or call.get("state") not in {"prepared", "uncertain"}
            or handoff.get("status") != "offered" or handoff.get("child_handle")
            or handoff.get("invocation_id") or handoff.get("generation") != task.get("generation")
            or pid_alive(task.get("owner_pid"))):
            raise StaleWriteError("only a current unresolved unaccepted offer without a live owner or bound child can be abandoned")
        if any(other_id != call_id and other.get("task_id") == call["task_id"]
               and other.get("state") in {"prepared", "sent", "uncertain", "durable"}
               and not retry_authorized(other) for other_id, other in ledger.get("calls", {}).items()):
            raise StaleWriteError("another unresolved current call protects this task")
        packet = Path(call["extra"]["packet_path"])
        prompt = Path(handoff["dispatch_prompt_path"])
        packet_bytes = packet.read_bytes()
        frozen_packet = json.loads(packet_bytes)
        envelope = frozen_packet.get("envelope") or {}
        if (hashlib.sha256(packet_bytes).hexdigest() != call.get("packet_hash")
            or hashlib.sha256(prompt.read_bytes()).hexdigest() != handoff.get("prompt_sha256")
            or any(envelope.get(k) != expected[k] for k in ("call_id", "task_id", "input_hash", "generation", "owner"))
            or (frozen_packet.get("source_revision") or frozen_packet.get("metadata", {}).get("source_revision")) != ledger["source_revision"]):
            raise StaleWriteError("original packet/prompt/envelope changed")
        if (run_dir / "raw" / f"{call_id}.json").exists() or call.get("raw_path") or call.get("result_path"):
            raise StaleWriteError("existing raw/result requires reconciliation before abandonment")
        call["state"] = "uncertain"
        call["extra"]["controller_abandonment"] = {
            **decision, "decision_sha256": digest, "recorded_at": iso(utc_now()),
            "model_delivery": "unknown", "business_acceptance": "none"}
        task.update(state="pending", owner=None, owner_pid=None, lease_until=None,
                    generation=int(task["generation"]) + 1)
        task["extra"].pop("call_id", None)
        # Source obligations, assigned IDs and input hash remain exactly intact.
        sync_budget(ledger)
        return ledger
    updated = store.mutate(mutate)
    return {"call_id": call_id, "status": "controller_abandoned", "delivery": "unknown",
            "usage": "preserved_or_unknown", "ledger_revision": updated["ledger_revision"],
            "next_action": "native-next"}
