"""Cost-preserving terminal disposition of obsolete native call generations.

No business output is imported and no current task, source binding or model
usage is replaced. A stopped host is not evidence of no dispatch.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from cbe.store import LedgerStore, StaleWriteError, mark_call, atomic_write_bytes


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _codex_completion(call, ledger, child_path: Path, parent_path: Path) -> dict:
    """Read only public session identity, final answer, completion and spawn IDs."""
    child_bytes, parent_bytes = child_path.read_bytes(), parent_path.read_bytes()
    child = [json.loads(line) for line in child_bytes.decode().splitlines() if line.strip()]
    parent = [json.loads(line) for line in parent_bytes.decode().splitlines() if line.strip()]
    meta = [row["payload"] for row in child if row.get("type") == "session_meta"]
    parent_meta = [row["payload"] for row in parent if row.get("type") == "session_meta"]
    handoff = call["extra"]["native_handoff"]
    if len(meta) != 1 or len(parent_meta) != 1:
        raise StaleWriteError("Codex public sessions require unique actual session identities")
    spawn = meta[0].get("source", {}).get("subagent", {}).get("thread_spawn") or {}
    handle = handoff["child_handle"]
    if (spawn.get("agent_path") != handle or spawn.get("parent_thread_id") != parent_meta[0].get("id")
        or meta[0].get("parent_thread_id") != parent_meta[0].get("id")
        or Path(meta[0].get("cwd") or "").resolve() != Path(ledger["repo_root"]).resolve()):
        raise StaleWriteError("Codex child/parent/workspace differs from the original bound call")
    result_path = str(Path(handoff["dispatch_prompt_path"]).parent.parent / "raw" / f"{call['call_id']}.json")
    finals = []
    terminals = []
    for row in child:
        payload = row.get("payload") or {}
        if (row.get("type") == "response_item" and payload.get("role") == "assistant"
            and payload.get("phase") == "final_answer"):
            text = "".join(part.get("text", "") for part in payload.get("content", []) if part.get("type") == "output_text").strip()
            finals.append((row, text))
        if row.get("type") == "event_msg" and payload.get("type") == "task_complete":
            terminals.append(row)
    if (len(finals) != 1 or finals[0][1] != result_path or len(terminals) != 1
        or not terminals[0].get("payload", {}).get("turn_id")
        or terminals[0].get("ordinal", -1) <= finals[0][0].get("ordinal", -1)):
        raise StaleWriteError("Codex public child lacks the exact original result-path final and subsequent task completion")
    calls = {}
    pairs = []
    for row in parent:
        payload = row.get("payload") or {}
        if row.get("type") != "response_item":
            continue
        if payload.get("type") == "function_call" and payload.get("name") == "spawn_agent":
            args = json.loads(payload.get("arguments") or "{}")
            if args.get("task_name") == handle.rsplit("/", 1)[-1]:
                calls[payload["call_id"]] = row
        elif payload.get("type") == "function_call_output" and payload.get("call_id") in calls:
            output = json.loads(payload.get("output") or "{}")
            if output.get("task_name") == handle:
                pairs.append((calls[payload["call_id"]], row))
    if len(pairs) != 1:
        raise StaleWriteError("Codex original parent spawn/result does not uniquely bind this actual child")
    return {"host_session_ref": str(child_path.resolve()), "host_session_sha256": _sha(child_bytes),
            "parent_session_ref": str(parent_path.resolve()), "parent_session_sha256": _sha(parent_bytes),
            "child_session_id": meta[0]["id"], "parent_session_id": parent_meta[0]["id"],
            "host_final_ordinal": finals[0][0]["ordinal"], "host_terminal_ordinal": terminals[0]["ordinal"],
            "host_spawn_call_id": pairs[0][0]["payload"]["call_id"], "host_final_path": result_path}


def reconcile_terminal(run_dir: Path, call_id: str, *, event: Path | None = None,
                       host_metadata: Path | None = None, host_output: Path | None = None,
                       parent_public_evidence: Path | None = None,
                       host_session: Path | None = None,
                       acknowledge_misbound_prompt: bool = False) -> dict:
    run_dir = Path(run_dir).resolve()
    store = LedgerStore(run_dir)
    ledger = store.open()
    call = ledger.get("calls", {}).get(call_id)
    if not call:
        raise ValueError("unknown historical native call")
    handoff = call.get("extra", {}).get("native_handoff") or {}
    if host_session and handoff.get("host") != "codex":
        raise ValueError("public host-session completion is supported for the original Codex host only")
    packet_path = Path(call.get("extra", {}).get("packet_path") or "")
    packet_bytes = packet_path.read_bytes() if packet_path.is_file() else b""
    if not packet_bytes or _sha(packet_bytes) != call.get("packet_hash"):
        raise StaleWriteError("historical call packet/source-input bytes changed")
    packet = json.loads(packet_bytes)
    envelope = packet.get("envelope")
    revision = packet.get("source_revision") or (packet.get("metadata") or {}).get("source_revision")
    expected = {"task_id": call.get("task_id"), "call_id": call_id,
                "input_hash": call.get("input_hash"), "generation": handoff.get("generation")}
    if (not isinstance(envelope, dict) or any(envelope.get(key) != value for key, value in expected.items())
        or not isinstance(envelope.get("owner"), str) or not envelope["owner"].strip()
        or revision != ledger.get("source_revision")):
        raise StaleWriteError("historical call frozen envelope/input/source identity differs from the original packet")
    raw = run_dir / "raw" / f"{call_id}.json"
    if raw.is_file():
        try:
            raw_payload = json.loads(raw.read_bytes())
        except (json.JSONDecodeError, UnicodeDecodeError):
            raw_payload = None  # Invalid business bytes remain evidence, never acceptance.
        raw_envelope = raw_payload.get("envelope") if isinstance(raw_payload, dict) else None
        if raw_envelope is not None and raw_envelope != envelope:
            raise StaleWriteError("historical raw result envelope differs from its original frozen packet")
    task = ledger.get("tasks", {}).get(call.get("task_id")) or {}
    if call.get("state") == "released" and call.get("extra", {}).get("historical_terminal_receipt"):
        receipt = Path(call["extra"]["historical_terminal_receipt"])
        proof_bytes = receipt.read_bytes()
        proof = json.loads(proof_bytes)
        if (_sha(proof_bytes) not in receipt.name or proof.get("call_id") != call_id
            or proof.get("input_hash") != call["input_hash"]
            or proof.get("child_handle") != handoff.get("child_handle")):
            raise StaleWriteError("historical terminal receipt no longer binds the original call")
        return {"call_id": call_id, "status": "historical_terminal", "idempotent": True,
                "receipt": call["extra"]["historical_terminal_receipt"], "current_task_unchanged": True}
    if (call.get("state") not in {"uncertain", "sent"} or not handoff.get("child_handle")
        or task.get("generation") == handoff.get("generation")
        or task.get("extra", {}).get("call_id") == call_id):
        raise StaleWriteError("historical terminal requires an obsolete call generation; current leases use native-record")
    prompt = Path(handoff["dispatch_prompt_path"])
    if _sha(prompt.read_bytes()) != handoff.get("prompt_sha256"):
        raise StaleWriteError("historical native prompt bytes changed")
    proof = {"schema": "native-historical-terminal/1", "call_id": call_id,
             "task_id": call["task_id"], "original_generation": handoff["generation"],
             "input_hash": call["input_hash"], "prompt_sha256": handoff["prompt_sha256"],
             "packet_sha256": call["packet_hash"], "source_revision": ledger["source_revision"],
             "original_owner": envelope["owner"], "original_envelope": envelope,
             "raw_sha256": _sha(raw.read_bytes()) if raw.exists() else None,
             "host": handoff.get("host"), "child_handle": handoff["child_handle"]}
    if event:
        if host_metadata or host_output or acknowledge_misbound_prompt or parent_public_evidence and not host_session:
            raise ValueError("choose original completed event or original host stop evidence")
        event_bytes = Path(event).read_bytes()
        value = json.loads(event_bytes)
        if any(key in value and value[key] != envelope[key]
               for key in ("call_id", "task_id", "generation", "owner", "input_hash")):
            raise StaleWriteError("historical terminal event envelope differs from its original frozen packet")
        digest = _sha(event_bytes)
        known_digest = call.get("extra", {}).get("native_events", {}).get("completed")
        codex = handoff.get("host") == "codex" and host_session is not None and parent_public_evidence is not None
        if ((known_digest != digest and not (codex and known_digest is None and digest in Path(event).name))
            or value.get("schema") != "native_handoff_v1" or value.get("status") != "completed"
            or value.get("call_id") != call_id or value.get("task_id") != call["task_id"]
            or value.get("generation") != handoff["generation"]
            or value.get("prompt_sha256") != handoff["prompt_sha256"]
            or value.get("child_handle") != handoff["child_handle"]
            or value.get("host") != handoff.get("host")
            or value.get("evidence_level") == "controller_attested" and not codex or not raw.is_file()):
            raise StaleWriteError("original completed terminal evidence does not bind this obsolete call/result")
        proof.update(terminal="completed_superseded_unaccepted", event_ref=str(Path(event).resolve()),
                     event_sha256=digest)
        if codex:
            proof.update(_codex_completion(call, ledger, Path(host_session), Path(parent_public_evidence)))
        else:
            evidence = Path(value.get("evidence_ref") or "")
            if not evidence.is_absolute() or not evidence.is_file():
                raise StaleWriteError("original host completion evidence is missing")
            proof.update(evidence_ref=str(evidence), evidence_sha256=_sha(evidence.read_bytes()))
    else:
        if host_session:
            raise ValueError("host-session applies only to an original Codex completed event")
        if not host_metadata or not host_output or not parent_public_evidence or handoff.get("host") != "zcode":
            raise ValueError("stopped historical ZCode calls need metadata/output and original public parent Agent launch evidence")
        metadata_bytes = Path(host_metadata).read_bytes()
        metadata = json.loads(metadata_bytes)
        public = {key: metadata.get(key) for key in ("agentId", "parentSessionId", "parentToolUseId",
                  "childSessionId", "status", "completedAt", "prompt", "outputFile")}
        output_bytes = Path(host_output).read_bytes()
        metadata_path = Path(host_metadata).resolve()
        parent_bytes = Path(parent_public_evidence).read_bytes()
        parent = json.loads(parent_bytes)
        parts = parent.get("public_tool_parts") or []
        matches = [p for p in parts if p.get("call_id") == public["parentToolUseId"] and p.get("tool") == "Agent"]
        if (public["status"] != "stopped" or output_bytes.decode().strip() != "Background agent task stopped."
            or public["agentId"] != handoff["child_handle"] or not public["completedAt"]
            or public["childSessionId"] != "sess_subagent_" + public["agentId"]
            or metadata_path.parent.name != public["agentId"]
            or metadata_path.parent.parent.name != public["parentSessionId"]
            or parent.get("parent_session_id") != public["parentSessionId"]
            or len(matches) != 1 or matches[0].get("status") != "completed"
            or "agentId: " + public["agentId"] not in str(matches[0].get("output"))
            or Path(public["outputFile"] or "").resolve() != Path(host_output).resolve()):
            raise StaleWriteError("historical host stop does not bind the original child/parent/tool launch")
        launch_input = matches[0].get("input")
        launch_input = json.loads(launch_input) if isinstance(launch_input, str) else launch_input
        if not isinstance(launch_input, dict) or launch_input.get("prompt") != public["prompt"]:
            raise StaleWriteError("historical launch prompt differs from original host metadata")
        matched = str(prompt) in public["prompt"]
        if not matched and not acknowledge_misbound_prompt:
            raise StaleWriteError("old call child received a different prompt; preserve identity conflict or explicitly acknowledge historical misbinding")
        if raw.exists():
            raise StaleWriteError("stopped historical call has a late raw result; inspect completion evidence before disposition")
        proof.update(terminal="stopped_superseded" if matched else "stopped_misbound_child",
            model_delivery="unknown", identity_conflict=None if matched else "original recorded child received a different prompt; this does not prove delivery of the call source",
            metadata_ref=str(metadata_path), metadata_sha256=_sha(metadata_bytes), public_host_fields=public,
            output_ref=str(Path(host_output).resolve()), output_sha256=_sha(output_bytes),
            parent_public_ref=str(Path(parent_public_evidence).resolve()), parent_public_sha256=_sha(parent_bytes))
    encoded = json.dumps(proof, sort_keys=True, ensure_ascii=False).encode()
    receipt = run_dir / "native" / f"{call_id}.historical-terminal.{_sha(encoded)}.json"
    if receipt.exists() and receipt.read_bytes() != encoded:
        raise StaleWriteError("historical terminal receipt changed")
    atomic_write_bytes(receipt, encoded)
    original = _sha(json.dumps(call, sort_keys=True).encode())
    def mutate(current):
        bound = current.get("calls", {}).get(call_id)
        if _sha(json.dumps(bound, sort_keys=True).encode()) != original:
            raise StaleWriteError("historical call changed while collecting terminal evidence")
        current_task = current.get("tasks", {}).get(call["task_id"]) or {}
        if current_task.get("generation") == handoff["generation"] or current_task.get("extra", {}).get("call_id") == call_id:
            raise StaleWriteError("historical call unexpectedly became current")
        if (_sha(raw.read_bytes()) if raw.exists() else None) != proof["raw_sha256"]:
            raise StaleWriteError("late raw result appeared during terminal reconciliation")
        mark_call(current, call_id, state="released", extra={"disposition": proof["terminal"],
            "historical_terminal_receipt": str(receipt), "historical_identity_conflict": proof.get("identity_conflict")})
        return current
    store.mutate(mutate)
    return {"call_id": call_id, "status": "historical_terminal", "receipt": str(receipt),
            "terminal": proof["terminal"], "current_task_unchanged": True, "usage": "preserved_or_unknown",
            "business_acceptance": "none", "next_action": "native-next"}
