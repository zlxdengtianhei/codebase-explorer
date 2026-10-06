"""Explicit public launch identity proof and cost-preserving pairing correction."""
import hashlib
import json
from pathlib import Path

from cbe.store import LedgerStore, StaleWriteError, atomic_write_bytes


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def launch_proof(ledger, call, metadata_path, parent_path, *, completed=False):
    """No host discovery: verify caller-provided public launch and frozen packet."""
    sha = lambda raw: hashlib.sha256(raw).hexdigest()
    metadata_path, parent_path = Path(metadata_path).resolve(), Path(parent_path).resolve()
    mb, pb = metadata_path.read_bytes(), parent_path.read_bytes()
    metadata, parent = json.loads(mb), json.loads(pb)
    fields = {k: metadata.get(k) for k in ("agentId", "parentSessionId", "parentToolUseId",
        "childSessionId", "status", "completedAt", "prompt", "outputFile")}
    parts = [p for p in parent.get("public_tool_parts", []) if p.get("tool") == "Agent"
             and p.get("call_id") == fields["parentToolUseId"]]
    handoff = call.get("extra", {}).get("native_handoff") or {}
    prompt = Path(handoff["dispatch_prompt_path"])
    packet = Path(call["extra"]["packet_path"])
    packet_bytes = packet.read_bytes()
    payload = json.loads(packet_bytes)
    envelope = payload.get("envelope") or {}
    source = payload.get("source_revision") or payload.get("metadata", {}).get("source_revision")
    raw = prompt.parent.parent / "raw" / (call["call_id"] + ".json")
    launch = parts[0].get("input") if len(parts) == 1 else None
    launch = json.loads(launch) if isinstance(launch, str) else launch
    if (not fields["agentId"] or fields["childSessionId"] != "sess_subagent_" + fields["agentId"]
        or metadata_path.parent.name != fields["agentId"]
        or metadata_path.parent.parent.name != fields["parentSessionId"]
        or parent.get("parent_session_id") != fields["parentSessionId"]
        or len(parts) != 1 or parts[0].get("status") != "completed"
        or "agentId: " + fields["agentId"] not in str(parts[0].get("output"))
        or not isinstance(launch, dict) or launch.get("prompt") != fields["prompt"]
        or str(prompt) not in fields["prompt"] or str(raw) not in fields["prompt"]
        or sha(prompt.read_bytes()) != handoff.get("prompt_sha256")
        or sha(packet_bytes) != call.get("packet_hash") or source != ledger.get("source_revision")
        or any(envelope.get(k) != v for k, v in {"call_id": call["call_id"],
            "task_id": call["task_id"], "input_hash": call["input_hash"],
            "generation": handoff["generation"]}.items()) or not envelope.get("owner")):
        raise StaleWriteError("public launch/metadata/frozen input does not bind this original call")
    output_path = Path(fields["outputFile"] or "").resolve()
    if output_path.parent != metadata_path.parent:
        raise StaleWriteError("host output path differs from original child")
    raw_hash = None
    output_hash = None
    if completed:
        if fields["status"] != "completed" or not fields["completedAt"] or not raw.is_file():
            raise StaleWriteError("pairing correction requires actual completed child and original raw")
        output = output_path.read_bytes()
        if output.decode().strip() != str(raw):
            raise StaleWriteError("actual child final differs from original reserved result path")
        raw_bytes = raw.read_bytes()
        original = prompt.parent.parent / "native" / (call["call_id"] + ".response.txt")
        if original.exists():
            immutable = original.read_bytes()
            if raw_bytes != immutable:
                from cbe.native_handoff import _normalized_bytes
                if raw_bytes != _normalized_bytes(immutable, call["task_id"], payload, envelope):
                    raise StaleWriteError("reserved raw differs from immutable response normalization")
            raw_bytes = immutable
        raw_payload = json.loads(raw_bytes)
        if raw_payload.get("envelope") is not None and raw_payload["envelope"] != envelope:
            raise StaleWriteError("raw envelope differs from original frozen call")
        raw_hash, output_hash = sha(raw_bytes), sha(output)
    proof = {"call_id": call["call_id"], "task_id": call["task_id"], "envelope": envelope,
        "child_handle": fields["agentId"], "host": "zcode", "public_host_fields": fields,
        "metadata_ref": str(metadata_path), "metadata_sha256": sha(mb),
        "parent_ref": str(parent_path), "parent_sha256": sha(pb),
        "prompt_sha256": handoff["prompt_sha256"], "packet_sha256": call["packet_hash"],
        "raw_ref": str(raw), "raw_sha256": raw_hash, "output_ref": str(output_path),
        "output_sha256": output_hash}
    correction = call.get("extra", {}).get("native_binding_correction")
    if completed and correction:
        receipt = Path(correction)
        saved_bytes = receipt.read_bytes()
        saved = json.loads(saved_bytes)
        originals = [p for p in saved.get("proofs", []) if p.get("call_id") == call["call_id"]]
        if sha(saved_bytes) not in receipt.name or len(originals) != 1 or originals[0] != proof:
            raise StaleWriteError("actual response/launch differs from original pairing correction proof")
    return proof


def reconcile_binding(run_dir, call_id, *, host_metadata, conflicting_call_id,
                      conflicting_metadata, parent_public_evidence):
    """Correct two proven launch pairings; never accept business results or rewrite usage."""
    store = LedgerStore(Path(run_dir).resolve())
    ledger = store.open()
    ids = [call_id, conflicting_call_id]
    if len(set(ids)) != 2:
        raise ValueError("pairing correction requires two distinct calls")
    calls = [ledger["calls"][cid] for cid in ids]
    proofs = [launch_proof(ledger, call, meta, parent_public_evidence, completed=True)
              for call, meta in zip(calls, [host_metadata, conflicting_metadata])]
    actual = [p["child_handle"] for p in proofs]
    if len(set(actual)) != 2:
        raise StaleWriteError("actual launch identities are not distinct")
    handoffs = [c["extra"]["native_handoff"] for c in calls]
    if handoffs[1].get("child_handle") != actual[0] or handoffs[0].get("child_handle") not in (None, actual[0]):
        if all(h.get("child_handle") == a for h, a in zip(handoffs, actual)) and all(
            c["extra"].get("native_binding_correction") for c in calls):
            refs = {c["extra"]["native_binding_correction"] for c in calls}
            if len(refs) != 1:
                raise StaleWriteError("correction receipt differs across original calls")
            saved = Path(refs.pop())
            saved_bytes = saved.read_bytes()
            if hashlib.sha256(saved_bytes).hexdigest() not in saved.name or json.loads(saved_bytes).get("proofs") != proofs:
                raise StaleWriteError("original correction receipt no longer binds actual launch proofs")
            return {"status": "identity_corrected", "idempotent": True, "business_acceptance": "none"}
        raise StaleWriteError("the two original calls do not exhibit this proven wrong pairing")
    if any(c.get("state") == "released" for c in calls):
        raise StaleWriteError("released calls cannot acquire a corrected active binding")
    for cid, other in ledger["calls"].items():
        if cid not in ids and other.get("extra", {}).get("native_handoff", {}).get("child_handle") in actual:
            raise StaleWriteError("actual child is also bound to another call")
    old = [digest(c) for c in calls]
    tasks = {c["task_id"]: digest(ledger["tasks"][c["task_id"]]) for c in calls}
    receipt_value = {"schema": "native-binding-correction/1", "proofs": proofs,
                     "original_calls": calls,
                     "original_tasks": {tid: ledger["tasks"][tid] for tid in tasks},
                     "business_acceptance": "none", "usage": "unchanged"}
    encoded = json.dumps(receipt_value, sort_keys=True, ensure_ascii=False).encode()
    receipt = Path(run_dir).resolve() / "native" / ("binding-correction." + hashlib.sha256(encoded).hexdigest() + ".json")
    if receipt.exists() and receipt.read_bytes() != encoded:
        raise StaleWriteError("original identity correction receipt changed")
    atomic_write_bytes(receipt, encoded)
    def mutate(current):
        if any(digest(current["calls"].get(cid)) != d for cid, d in zip(ids, old)) or any(
            digest(current["tasks"].get(tid)) != d for tid, d in tasks.items()):
            raise StaleWriteError("call/task changed during pairing correction")
        if any(cid not in ids and c.get("extra", {}).get("native_handoff", {}).get("child_handle") in actual
               for cid, c in current["calls"].items()):
            raise StaleWriteError("actual child acquired a third binding during correction")
        for call, meta, proof in zip(calls, [host_metadata, conflicting_metadata], proofs):
            if launch_proof(current, call, meta, parent_public_evidence, completed=True) != proof:
                raise StaleWriteError("launch/input/raw evidence changed during pairing correction")
        for cid, proof in zip(ids, proofs):
            corrected = current["calls"][cid]
            extra = corrected["extra"]
            extra.setdefault("native_binding_history", []).append({
                "handoff": dict(extra["native_handoff"]), "events": dict(extra.get("native_events") or {}),
                "event_ref": extra.get("native_event_ref"), "reason": "actual public launch disproved parent pairing"})
            extra["native_handoff"].update(host="zcode", child_handle=proof["child_handle"])
            extra["native_binding_correction"] = str(receipt)
            extra["original_usage_attribution"] = "preserved; prior parent pairing conflicted; correction does not reassign usage to another call"
            if corrected.get("native_session_id"):
                corrected["native_session_id"] = proof["child_handle"]
            if corrected.get("role_session_id"):
                corrected["role_session_id"] = "zcode:" + proof["child_handle"]
        return current
    store.mutate(mutate)
    return {"status": "identity_corrected", "call_ids": ids, "receipt": str(receipt),
            "business_acceptance": "none", "current_tasks_unchanged": True, "usage": "unchanged",
            "next_action": "native-record started then completed with launch metadata and original raw; do not reimport an already quarantined old call"}
