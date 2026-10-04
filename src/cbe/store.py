"""Single JSON ledger with flock+thread lock, CAS, atomic write, and replay."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
import threading
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, Sequence

import orjson

from cbe.accounting import (
    DELIVERY_PACKET,
    can_reserve,
    delivery_evidence_is_positive,
    ensure_initial_exposure,
    overall_token_budget,
    possibly_sent,
    promote_initial_for_state,
    sync_budget,
)
from cbe.graph import GraphSnapshot
from cbe.inventory import Inventory
from cbe.graph import page_list
from cbe.ir import CharSpan, sha256_bytes, sha256_text
from cbe.models import (
    LEDGER_SCHEMA,
    CallRecord,
    DetailRecord,
    GroupRecord,
    ReviewRecord,
    TaskRecord,
    nav_sentence,
)
from cbe.packets import (
    DuplicateIdentityError,
    FragmentRef,
    Packet,
    PacketIndex,
    is_fragment_output_id,
    merge_char_spans,
    unique_by_id,
)

LEDGER_NAME = "semantic_ledger.json"
PREV_NAME = "semantic_ledger.json.prev"
RECEIPT_NAME = "commit_receipt.json"
LOCK_NAME = "semantic_ledger.json.lock"

_THREAD_LOCKS: dict[str, threading.RLock] = {}
_THREAD_GUARD = threading.Lock()


class StoreError(RuntimeError):
    pass


class LedgerCorruptError(StoreError):
    pass


class StaleWriteError(StoreError):
    pass


class LeaseError(StoreError):
    pass


class BudgetError(StoreError):
    pass


def _thread_lock(path: Path) -> threading.RLock:
    key = str(path)
    with _THREAD_GUARD:
        lock = _THREAD_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _THREAD_LOCKS[key] = lock
        return lock


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(ts: datetime | None = None) -> str:
    return (ts or utc_now()).isoformat()


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():
        raise StoreError(f"ledger path must not be a symlink: {path}")
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


class LedgerStore:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = Path(run_dir).resolve()
        self.path = self.run_dir / LEDGER_NAME
        self.lock_path = self.run_dir / LOCK_NAME
        self.prev_path = self.run_dir / PREV_NAME
        self.receipt_path = self.run_dir / RECEIPT_NAME

    @contextmanager
    def locked(self) -> Iterator[None]:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        thread_lock = _thread_lock(self.path)
        thread_lock.acquire()
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.lock_path, flags, 0o600)
        except OSError as exc:
            thread_lock.release()
            raise StoreError(f"cannot open ledger lock: {exc}") from exc
        lock_file = os.fdopen(descriptor, "a+b")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            finally:
                lock_file.close()
                thread_lock.release()

    def empty_ledger(
        self,
        *,
        run_id: str,
        inventory: Inventory,
        graph: GraphSnapshot,
        packets: PacketIndex,
        tasks: dict[str, TaskRecord],
    ) -> dict[str, Any]:
        return {
            "schema": LEDGER_SCHEMA,
            "run_id": run_id,
            "repo_root": inventory.repo_root,
            "source_revision": inventory.source_revision,
            "git_head": inventory.git_head,
            "ledger_revision": 0,
            "render_revision": 0,
            "inventory": inventory.to_dict(),
            "graph": graph.to_dict(),
            "packets": packets.to_dict(),
            "tasks": {key: value.to_dict() for key, value in tasks.items()},
            "details": {},
            "groups": {},
            "calls": {},
            "reviews": {},
            "budget": {
                "s_chars": inventory.s_chars,
                "source_exposure_chars": 0,
                "known_source_chars": 0,
                "possible_source_upper_chars": 0,
                "exposure_upper_chars": 0,
                "reserved_chars": 0,
                "source_read_chars": 0,
                "source_read_chars_meaning": "occupancy alias of source_exposure_chars (L+U+reserve)",
                "logical_exposure_status": "within_upper_bound",
                "evidence_completeness": "run_packets",
                "provider_source_input_chars": None,
                "cap_chars": 2 * inventory.s_chars,
                "budget_evidence": "run_packets",
            },
        }

    def read_unlocked(self) -> dict[str, Any]:
        if not self.path.exists():
            raise StoreError(f"ledger does not exist: {self.path}")
        try:
            payload = self.path.read_bytes()
            if b'"documentation_policy"' in payload:
                # A matching commit receipt authenticates bytes produced by our
                # dict serializer, which cannot contain duplicate object keys.
                # This lets large weighted runs use the much faster parser.
                try:
                    receipt = json.loads(self.receipt_path.read_text(encoding="utf-8"))
                except FileNotFoundError:
                    inspected = json.loads(payload, object_pairs_hook=_strict_object)
                    if int(inspected.get("ledger_revision") or 0) == 0:
                        return inspected
                    raise
                if receipt.get("ledger_sha256") == sha256_bytes(payload):
                    return orjson.loads(payload)
                # A crash after ledger replacement but before the tiny receipt
                # update leaves a valid next revision. Inspect it strictly.
                inspected = json.loads(payload, object_pairs_hook=_strict_object)
                if int(inspected.get("ledger_revision") or 0) == int(receipt.get("ledger_revision") or 0) + 1:
                    return inspected
                raise LedgerCorruptError(f"ledger receipt mismatch; file kept at {self.path}")
            return json.loads(payload, object_pairs_hook=_strict_object)
        except (json.JSONDecodeError, orjson.JSONDecodeError, UnicodeError, TypeError, ValueError, OSError) as exc:
            raise LedgerCorruptError(
                f"ledger is corrupt; file kept at {self.path}: {exc}"
            ) from exc

    def write_unlocked(self, ledger: dict[str, Any]) -> dict[str, Any]:
        weighted = (ledger.get("documentation_policy") or {}).get("version") in {"weighted-v1", "module-first-v2"}
        if not weighted:
            ledger = json.loads(json.dumps(ledger))
        ledger["ledger_revision"] = int(ledger.get("ledger_revision") or 0) + 1
        encoded = (
            orjson.dumps(ledger) if weighted
            else json.dumps(ledger, ensure_ascii=False, indent=2).encode("utf-8")
        )
        if self.path.exists():
            try:
                if self.path.is_symlink():
                    raise StoreError(f"ledger path must not be a symlink: {self.path}")
                link = self.prev_path.with_name(f".{self.prev_path.name}.{uuid.uuid4().hex}.tmp")
                os.link(self.path, link)
                os.replace(link, self.prev_path)
            except OSError:
                try:
                    atomic_write_bytes(self.prev_path, self.path.read_bytes())
                except OSError:
                    pass
        atomic_write_bytes(self.path, encoded)
        receipt = {
            "ledger_revision": ledger["ledger_revision"],
            "ledger_sha256": sha256_bytes(encoded),
            "source_revision": ledger.get("source_revision"),
            "committed_at": iso(),
        }
        atomic_write_bytes(self.receipt_path, json.dumps(receipt, indent=2).encode("utf-8"))
        return ledger

    def create(self, ledger: dict[str, Any]) -> dict[str, Any]:
        with self.locked():
            if self.path.exists():
                raise StoreError(f"ledger already exists: {self.path}")
            ledger = dict(ledger)
            ledger["ledger_revision"] = -1
            return self.write_unlocked(ledger)

    def open(self) -> dict[str, Any]:
        with self.locked():
            return self.read_unlocked()

    def mutate(self, mutator) -> dict[str, Any]:
        with self.locked():
            current = self.read_unlocked()
            updated = mutator(current)
            if updated is None:
                return current
            return self.write_unlocked(updated)


def pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    except SystemError:
        return False
    return True


def parse_lease(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def claim_task(
    ledger: dict[str, Any],
    *,
    task_id: str,
    owner: str,
    owner_pid: int,
    lease_seconds: int,
    now: datetime | None = None,
    raw_exists: bool = False,
) -> TaskRecord:
    tasks = ledger.setdefault("tasks", {})
    raw = tasks.get(task_id)
    if raw is None:
        raise LeaseError(f"unknown task {task_id}")
    task = TaskRecord.from_dict(raw)
    timestamp = now or utc_now()
    extra = task.extra or {}
    if extra.get("tombstone") or extra.get("superseded"):
        raise LeaseError(f"task {task_id} is historical (tombstone/superseded) and not currently runnable")
    if task.state in {"committed"}:
        raise LeaseError(f"task {task_id} is already committed")
    if task.state == "leased":
        if pid_alive(task.owner_pid):
            if task.owner == owner and int(task.owner_pid or 0) == int(owner_pid):
                return task
            raise LeaseError(
                f"task {task_id} lease clock elapsed but owner pid {task.owner_pid} is alive"
            )
        if raw_exists:
            raise LeaseError(
                f"task {task_id} has durable raw; resume import instead of stealing the lease"
            )
        if task.owner and task.owner != owner:
            expires = parse_lease(task.lease_until)
            still_held = expires is None or expires > timestamp
            if still_held and pid_alive(task.owner_pid):
                raise LeaseError(f"task {task_id} is leased by {task.owner} until {task.lease_until}")
    task.owner = owner
    task.owner_pid = owner_pid
    task.lease_until = iso(timestamp + timedelta(seconds=lease_seconds))
    task.generation = int(task.generation) + 1
    task.state = "leased"
    tasks[task_id] = task.to_dict()
    return task


def reserve_call(
    ledger: dict[str, Any],
    call: CallRecord,
) -> CallRecord:
    calls = ledger.setdefault("calls", {})
    if call.call_id in calls and calls[call.call_id].get("state") in {"durable", "imported"}:
        existing = CallRecord.from_dict(calls[call.call_id])
        return existing
    if (ledger.get("documentation_policy") or {}).get("version") == "module-first-v2":
        # An unproven delivery protects its task from a duplicate send.
        for existing_id, existing in sorted(calls.items()):
            if existing.get("task_id") != call.task_id:
                continue
            from cbe.native_abandon import retry_authorized
            if possibly_sent(existing) and not delivery_evidence_is_positive(existing) and not retry_authorized(existing):
                raise BudgetError(
                    f"task {call.task_id} still has call {existing_id} with unproven "
                    f"delivery; reconcile its receipt/raw before claiming a new call"
                )
    s_chars = int(ledger.get("inventory", {}).get("s_chars") or 0)
    extra = call.extra or {}
    needed = int(call.source_chars or 0)
    delivery = call.delivery or extra.get("delivery")
    if delivery == DELIVERY_PACKET:
        needed = int(extra.get("reservation_chars") or extra.get("packed_source_chars") or 0)
    policy = ledger.get("budget_policy") or {}
    raw_multiplier = policy.get("source_read_cap_multiplier")
    cap_multiplier = (
        float(raw_multiplier) if isinstance(raw_multiplier, (int, float)) and raw_multiplier > 0
        else None
    )
    strict = (ledger.get("budget_policy") or {}).get("source_read_mode") == "strict" or (
        (ledger.get("documentation_policy") or {}).get("budget_mode") != "report"
    )
    ok, reason = can_reserve(s_chars, calls, needed, cap_multiplier=cap_multiplier,
                             strict=strict)
    if not ok:
        raise BudgetError(reason)
    call.state = "prepared"
    payload = call.to_dict()
    ensure_initial_exposure(payload)
    promote_initial_for_state(payload)
    calls[call.call_id] = payload
    sync_budget(ledger)
    return CallRecord.from_dict(payload)


def set_budget_policy(run_dir: Path, *, multiplier: float, reason: str,
                      set_by: str | None = None) -> dict[str, Any]:
    """Record the run's source-read dispatch ceiling with provenance.

    A policy may tighten the hard 2*S source ceiling but cannot relax it.
    """
    multiplier = float(multiplier)
    if not 0.5 <= multiplier <= 2.0:
        raise StoreError(f"source_read_cap_multiplier out of range [0.5, 2.0]: {multiplier}")
    reason = str(reason or "").strip()
    if len(reason) < 20:
        raise StoreError("reason must state the on-record authorization (>= 20 chars)")
    store = LedgerStore(run_dir)
    entry = {
        "set_at": iso(utc_now()),
        "set_by": set_by,
        "source_read_cap_multiplier": multiplier,
        "reason": reason,
    }

    def mutate(current: dict[str, Any]) -> dict[str, Any]:
        policy = current.setdefault("budget_policy", {})
        policy.update(entry)
        history = policy.setdefault("history", [])
        history.append(entry)
        sync_budget(current)
        return current

    store.mutate(mutate)
    ledger = store.open()
    policy = dict(ledger.get("budget_policy") or {})
    policy["history"] = list(policy.get("history") or [])
    return policy


def show_budget_policy(run_dir: Path) -> dict[str, Any]:
    store = LedgerStore(run_dir)
    ledger = store.open()
    policy = dict(ledger.get("budget_policy") or {})
    policy.setdefault("history", [])
    return policy


def mark_call(ledger: dict[str, Any], call_id: str, **fields: Any) -> CallRecord:
    calls = ledger.setdefault("calls", {})
    raw = calls.get(call_id)
    if raw is None:
        raise StoreError(f"unknown call {call_id}")
    extra_update = fields.pop("extra", None)
    raw.update(fields)
    if extra_update is not None:
        merged = dict(raw.get("extra") or {})
        merged.update(extra_update)
        raw["extra"] = merged
    promote_initial_for_state(raw)
    calls[call_id] = raw
    sync_budget(ledger)
    return CallRecord.from_dict(raw)


def reconcile_call_delivery(
    ledger: dict[str, Any],
    call_id: str,
    *,
    conclusion: str,
    searched: list[str],
    note: str = "",
    now: datetime | None = None,
) -> CallRecord:
    """Finalize an uncertain call as not delivered after an explicit evidence search.

    Unknown delivery is not resolved by the product alone: the operator records
    where receipts/raw/provider evidence was searched. Only a call that is
    possibly sent, has no positive delivery marker, and is still ``uncertain``
    can be reconciled this way. Usage history, proven calls, and their costs are
    untouched; the released reservation stops occupying the reading budget.
    """
    calls = ledger.setdefault("calls", {})
    raw = calls.get(call_id)
    if raw is None:
        raise StoreError(f"unknown call {call_id}")
    if conclusion != "no_delivery_evidence":
        raise ValueError("supported conclusion is no_delivery_evidence; import or dispute positive evidence instead")
    if not searched or not all(isinstance(item, str) and item.strip() for item in searched):
        raise ValueError("record the nonempty evidence locations searched")
    if delivery_evidence_is_positive(raw):
        raise BudgetError("call already has positive delivery evidence; use import/reject paths")
    if raw.get("state") != "uncertain" or not possibly_sent(raw):
        raise StoreError("only an uncertain possibly-sent call can be reconciled to not-delivered")
    record = {
        "conclusion": conclusion,
        "searched": list(searched),
        "note": note,
        "recorded_at": iso(now or utc_now()),
    }
    return mark_call(
        ledger, call_id, state="released",
        extra={"disposition": "reconciled_no_delivery_evidence",
               "reconciliation": record},
    )


DETAIL_FIELDS = (
    "behavior",
    "inputs_outputs",
    "effects",
    "failures",
    "dependencies",
    "unresolved",
)


def _looks_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return False
    return False


def parse_detail_item(item: dict[str, Any], *, expected_ids: set[str]) -> tuple[DetailRecord | None, dict | None]:
    symbol_id = item.get("symbol_id")
    if not isinstance(symbol_id, str) or not symbol_id:
        return None, {"code": "missing_symbol_id", "item": item}
    if symbol_id not in expected_ids:
        return None, {"code": "unknown_id", "symbol_id": symbol_id}
    behavior = item.get("behavior")
    if not isinstance(behavior, str) or not behavior.strip():
        return None, {"code": "empty_behavior", "symbol_id": symbol_id}
    record = DetailRecord(
        symbol_id=symbol_id,
        behavior=behavior.strip(),
        inputs_outputs=item.get("inputs_outputs"),
        effects=item.get("effects"),
        failures=item.get("failures"),
        dependencies=item.get("dependencies"),
        unresolved=item.get("unresolved"),
        nav_sentence=nav_sentence(behavior, symbol_id),
        source_spans=list(item.get("source_spans") or []),
        packet_id=item.get("packet_id"),
        input_hash=str(item.get("input_hash") or ""),
        revision=int(item.get("revision") or 1),
        provenance=dict(item.get("provenance") or {}),
    )
    return record, None


def task_fragment_refs(task: TaskRecord, packet: Packet | None = None) -> list[FragmentRef]:
    raw_items = list((task.extra or {}).get("fragments") or [])
    if raw_items:
        return [FragmentRef.from_dict(item) if isinstance(item, dict) else item for item in raw_items]
    if packet is not None:
        return list(packet.fragments)
    return []


def fragment_for_output(task: TaskRecord, output_id: str, packet: Packet | None = None) -> FragmentRef | None:
    for fragment in task_fragment_refs(task, packet):
        if output_id in {fragment.output_id, fragment.fragment_id, fragment.symbol_id, fragment.identity_hash}:
            if output_id == fragment.symbol_id and not fragment.writes_canonical:
                continue
            return fragment
    return None


def split_canonical_ids(task: TaskRecord, packet: Packet | None = None) -> set[str]:
    return {
        fragment.symbol_id
        for fragment in task_fragment_refs(task, packet)
        if fragment.fragment_count > 1
    }


def _existing_fragment_id(existing: dict[str, Any]) -> str:
    provenance = existing.get("provenance") or {}
    return str(provenance.get("fragment_id") or existing.get("symbol_id") or "")


def _same_fragment_idempotent(
    existing: dict[str, Any] | None,
    *,
    fragment: FragmentRef | None,
    output_id: str,
    input_hash: str,
) -> bool:
    if not isinstance(existing, dict):
        return False
    provenance = existing.get("provenance") or {}
    if provenance.get("stale") or provenance.get("historical") or provenance.get("incomplete"):
        return False
    if not str(existing.get("behavior") or "").strip():
        return False
    existing_frag = _existing_fragment_id(existing)
    expected_frag = fragment.fragment_id if fragment is not None else output_id
    if existing_frag != expected_frag and existing_frag != output_id:
        return False
    if str(existing.get("input_hash") or "") != str(input_hash or ""):
        return False
    existing_ident = str(provenance.get("fragment_identity") or "")
    if fragment is not None and existing_ident and existing_ident != fragment.identity_hash:
        return False
    return True


def _same_preserved_promotion_output(
    existing: dict[str, Any] | None,
    *,
    task: TaskRecord,
    packet: Packet | None,
    output_id: str,
) -> bool:
    """A tier change in one packet does not invalidate its other frozen facts."""
    extra = task.extra or {}
    if extra.get("policy_version") != "weighted-v1" or packet is None:
        return False
    if not any(
        isinstance(policy, dict) and policy.get("promotion_history")
        for policy in (extra.get("output_policy") or {}).values()
    ):
        return False
    if not isinstance(existing, dict) or existing.get("packet_id") != packet.packet_id:
        return False
    provenance = existing.get("provenance") or {}
    if any(provenance.get(flag) for flag in ("stale", "historical", "incomplete")):
        return False
    if not str(existing.get("behavior") or "").strip():
        return False
    fragment = fragment_for_output(task, output_id, packet)
    expected_fragment = fragment.fragment_id if fragment is not None else output_id
    if _existing_fragment_id(existing) not in {expected_fragment, output_id}:
        return False
    if fragment is not None and provenance.get("fragment_identity") not in {None, "", fragment.identity_hash}:
        return False
    return True


def mark_detail_historical(existing: dict[str, Any], *, reason: str) -> dict[str, Any]:
    payload = dict(existing)
    provenance = dict(payload.get("provenance") or {})
    history = list(provenance.get("history") or [])
    snapshot = {
        "revision": payload.get("revision"),
        "input_hash": payload.get("input_hash"),
        "packet_id": payload.get("packet_id"),
        "behavior_sha256": sha256_text(str(payload.get("behavior") or "")),
        "reason": reason,
    }
    history.append(snapshot)
    provenance["history"] = history
    provenance["historical"] = True
    provenance["incomplete"] = True
    provenance["fresh"] = False
    provenance["historical_reason"] = reason
    payload["provenance"] = provenance
    return payload


def submit_details(
    ledger: dict[str, Any],
    *,
    task_id: str,
    owner: str,
    generation: int,
    items: list[dict[str, Any]],
    packet: Packet | None,
    call_id: str | None,
) -> TaskRecord:
    tasks = ledger.setdefault("tasks", {})
    raw = tasks.get(task_id)
    if raw is None:
        raise StoreError(f"unknown task {task_id}")
    task = TaskRecord.from_dict(raw)
    if task.generation != generation:
        raise StaleWriteError(
            f"stale generation for {task_id}: have {generation} current {task.generation}"
        )
    if task.owner != owner:
        raise StaleWriteError(f"owner mismatch for {task_id}")
    if task.state not in {"leased", "needs_repair", "returned"}:
        raise StaleWriteError(f"task {task_id} is not writable in state {task.state}")
    expected = set(task.input_ids)
    details = ledger.setdefault("details", {})
    accepted: list[str] = []
    residuals: list[dict] = []
    seen: set[str] = set()
    extra_task = task.extra or {}
    repair_ids = set(extra_task.get("repair_ids") or [])
    # A canonical rewrite deliberately changes prose for the same frozen
    # fragment/source hash. Source identity alone cannot make it a replay.
    repair_ids.update((extra_task.get("canonical_composition") or {}).get("fragment_ids") or [])
    split_ids = split_canonical_ids(task, packet)
    for item in items:
        if not isinstance(item, dict):
            residuals.append({"code": "non_object_item"})
            continue
        symbol_id = item.get("symbol_id")
        if (
            extra_task.get("policy_version") == "weighted-v1"
            and isinstance(symbol_id, str)
            and symbol_id in expected
        ):
            if item.get("needs_promotion"):
                evidence = item.get("needs_promotion")
                if not isinstance(evidence, dict) or not evidence.get("source_line") or not evidence.get("missing_fact"):
                    residuals.append({
                        "code": "invalid_promotion_evidence", "symbol_id": symbol_id,
                    })
                    continue
                residuals.append({
                    "code": "promotion_requested",
                    "symbol_id": symbol_id,
                    "evidence": evidence,
                })
                continue
            output_policy = (extra_task.get("output_policy") or {}).get(symbol_id)
            if not isinstance(output_policy, dict):
                residuals.append({"code": "missing_output_policy", "symbol_id": symbol_id})
                continue
            array_fields = ("inputs_outputs", "effects", "failures", "dependencies", "unresolved")
            invalid_fields = [
                field for field in array_fields
                if item.get(field) is not None
                and (
                    not isinstance(item[field], list)
                    or any(not isinstance(value, str) for value in item[field])
                )
            ]
            if invalid_fields:
                residuals.append({
                    "code": "invalid_detail_field_type", "symbol_id": symbol_id,
                    "fields": invalid_fields,
                })
                continue
            required = set(output_policy.get("required_fields") or [])
            missing_required = [
                field for field in sorted(required - {"behavior"})
                if field not in item
                or (item[field] is None and not item.get("unresolved"))
            ]
            if missing_required:
                residuals.append({
                    "code": "required_field_missing", "symbol_id": symbol_id,
                    "fields": missing_required,
                })
                continue
            from cbe.token_budget import count_text_tokens

            content_fields = ("behavior", "inputs_outputs", "effects", "failures", "dependencies", "unresolved")
            content_text = "\n".join(
                value
                for field in content_fields
                for value in (
                    item.get(field) if isinstance(item.get(field), list)
                    else [item.get(field)]
                )
                if isinstance(value, str) and value.strip()
            )
            used_tokens = count_text_tokens(content_text)
            allotted = int(output_policy.get("suggested_output_tokens") or 0)
            if allotted <= 0 or used_tokens > allotted:
                residuals.append({
                    "code": "detail_output_over_budget", "symbol_id": symbol_id,
                    "used_tokens": used_tokens, "allotted_tokens": allotted,
                })
                continue
        if isinstance(symbol_id, str) and symbol_id and symbol_id not in expected and symbol_id in split_ids:
            residuals.append({"code": "cross_fragment_canonical", "symbol_id": symbol_id})
            continue
        record, error = parse_detail_item(item, expected_ids=expected)
        if error is not None:
            residuals.append(error)
            continue
        assert record is not None
        fragment = fragment_for_output(task, record.symbol_id, packet)
        provenance = dict(record.provenance or {})
        if extra_task.get("policy_version") == "weighted-v1":
            output_policy = (extra_task.get("output_policy") or {}).get(record.symbol_id) or {}
            provenance["documentation_tier"] = output_policy.get("tier")
            provenance["policy_version"] = "weighted-v1"
        if fragment is not None:
            provenance.setdefault("fragment_id", fragment.fragment_id)
            provenance.setdefault("canonical_symbol_id", fragment.symbol_id)
            provenance.setdefault("fragment_identity", fragment.identity_hash)
            provenance.setdefault("fragment_count", fragment.fragment_count)
            provenance.setdefault("role", "canonical" if fragment.writes_canonical else "fragment")
            if fragment.writes_canonical:
                provenance.setdefault("complete", True)
            else:
                provenance["fresh"] = False
        record.provenance = provenance
        if packet is not None:
            record.packet_id = packet.packet_id
            if fragment is not None and fragment.owned_spans:
                record.source_spans = [
                    {"path": packet.path, **span.to_dict()} for span in fragment.owned_spans
                ]
            else:
                record.source_spans = [span.to_dict() for span in packet.spans]
            record.input_hash = task.input_hash
        existing = details.get(record.symbol_id)
        if record.symbol_id in repair_ids:
            already_ok = False
        else:
            already_ok = _same_fragment_idempotent(
                existing if isinstance(existing, dict) else None,
                fragment=fragment,
                output_id=record.symbol_id,
                input_hash=task.input_hash,
            )
        if not already_ok:
            already_ok = _same_preserved_promotion_output(
                existing if isinstance(existing, dict) else None,
                task=task, packet=packet, output_id=record.symbol_id,
            )
        if already_ok:
            seen.add(record.symbol_id)
            accepted.append(record.symbol_id)
            continue
        if isinstance(existing, dict):
            existing_prov = existing.get("provenance") or {}
            existing_frag = _existing_fragment_id(existing)
            expected_frag = fragment.fragment_id if fragment is not None else record.symbol_id
            if existing_frag not in {expected_frag, record.symbol_id} and not is_fragment_output_id(record.symbol_id):
                residuals.append({"code": "cross_fragment_canonical", "symbol_id": record.symbol_id})
                continue
            if (
                str(existing.get("input_hash") or "")
                and str(existing.get("input_hash") or "") != str(task.input_hash or "")
                and not existing_prov.get("historical")
                and not existing_prov.get("incomplete")
                and not (record.symbol_id in repair_ids and existing_prov.get("stale"))
                and task.kind != "merge"
            ):
                residuals.append({"code": "stale_input", "symbol_id": record.symbol_id})
                continue
            if existing_prov.get("historical") or existing_prov.get("incomplete") or task.kind == "merge" or extra_task.get("canonical_composition"):
                history = list(existing_prov.get("history") or [])
                history.append(
                    {
                        "revision": existing.get("revision"),
                        "input_hash": existing.get("input_hash"),
                        "packet_id": existing.get("packet_id"),
                        "behavior_sha256": sha256_text(str(existing.get("behavior") or "")),
                    }
                )
                record.provenance = dict(record.provenance or {})
                record.provenance["history"] = history
                if task.kind == "merge":
                    record.provenance["role"] = "canonical"
                    record.provenance["complete"] = True
                    record.provenance["fresh"] = True
                    record.provenance.pop("historical", None)
                    record.provenance.pop("incomplete", None)
            record.revision = int(existing.get("revision") or 1) + 1
        else:
            record.revision = 1
        details[record.symbol_id] = record.to_dict()
        accepted.append(record.symbol_id)
        seen.add(record.symbol_id)
    already_canonical = {
        sid
        for sid in expected
        if sid not in seen
        and (
            (sid not in repair_ids and _same_fragment_idempotent(
                details.get(sid) if isinstance(details.get(sid), dict) else None,
                fragment=fragment_for_output(task, sid, packet),
                output_id=sid,
                input_hash=task.input_hash,
            ))
            or _same_preserved_promotion_output(
                details.get(sid) if isinstance(details.get(sid), dict) else None,
                task=task, packet=packet, output_id=sid,
            )
        )
    }
    seen |= already_canonical
    accepted.extend(sid for sid in sorted(already_canonical) if sid not in accepted)
    missing = sorted(expected - seen)
    for symbol_id in missing:
        residuals.append({"code": "missing_item", "symbol_id": symbol_id})
    task.output_refs = accepted
    task.residual = residuals
    extra = dict(task.extra or {})
    repair_ids = [
        str(item.get("symbol_id"))
        for item in residuals
        if item.get("symbol_id") and str(item.get("symbol_id")) in expected
    ]
    if repair_ids:
        extra["repair_ids"] = repair_ids
        extra["original_input_ids"] = list(task.input_ids)
    else:
        extra.pop("repair_ids", None)
    task.extra = extra
    if residuals:
        task.state = "needs_repair"
    else:
        task.state = "committed"
        task.owner = owner
    tasks[task_id] = task.to_dict()
    if call_id:
        mark_call(ledger, call_id, state="imported")
    if accepted:
        affected = []
        for group_id, group in (ledger.get("groups") or {}).items():
            members = set(group.get("member_ids") or []) | set(group.get("children") or [])
            if members & set(accepted):
                affected.append(group_id)
                affected.extend(ancestor_group_ids(ledger, group_id))
        if affected:
            invalidate_group_bodies(ledger, list(dict.fromkeys(affected)))
    return task


GROUP_PLAN_KEYS = {
    "group_id",
    "children",
    "member_ids",
    "question_answered",
    "grouping_reason",
    "entry_routes",
    "relations",
    "body",
    "version",
    "parent_id",
    "partial",
}


def _fresh_detail(ledger: dict[str, Any], symbol_id: str) -> dict | None:
    if is_fragment_output_id(symbol_id):
        return None
    record = (ledger.get("details") or {}).get(symbol_id)
    if not isinstance(record, dict):
        return None
    provenance = record.get("provenance") or {}
    if provenance.get("stale"):
        return None
    if provenance.get("historical") or provenance.get("incomplete"):
        return None
    if provenance.get("role") == "fragment":
        return None
    if provenance.get("fresh") is False:
        return None
    if not str(record.get("behavior") or "").strip():
        return None
    merge = (ledger.get("tasks") or {}).get(f"task:merge:{symbol_id}")
    if isinstance(merge, dict) and not is_historical_task(merge) and merge.get("state") != "committed":
        return None
    return record


def _fresh_group_body(ledger: dict[str, Any], group_id: str) -> dict | None:
    record = (ledger.get("groups") or {}).get(group_id)
    if not isinstance(record, dict):
        return None
    extra = record.get("extra") or {}
    if extra.get("stale") or extra.get("review_hold"):
        return None
    if (
        (ledger.get("documentation_policy") or {}).get("version") == "weighted-v1"
        and extra.get("presentation") == "navigation"
    ):
        if not isinstance(extra.get("evidence_summary"), dict):
            return None
        if extra.get("navigation_input_hash") != group_body_input_hash(ledger, record):
            return None
        for member_id in record.get("member_ids") or []:
            if _fresh_detail(ledger, member_id) is None:
                return None
        for child_id in record.get("children") or []:
            if _fresh_group_body(ledger, child_id) is None:
                return None
        return record
    if not str(record.get("body") or "").strip():
        return None
    return record


def owned_primary_parents(ledger: dict[str, Any], *, skip_group_id: str | None = None) -> dict[str, str]:
    owned: dict[str, str] = {}
    for existing_id, existing in (ledger.get("groups") or {}).items():
        if skip_group_id and existing_id == skip_group_id:
            continue
        for member in existing.get("member_ids") or []:
            owned[member] = existing_id
        for child in existing.get("children") or []:
            owned[child] = existing_id
    return owned


def frontier_ids(
    ledger: dict[str, Any],
    *,
    replace_group_id: str | None = None,
) -> dict[str, list[str]]:
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    owned = owned_primary_parents(ledger, skip_group_id=replace_group_id)
    replace_children: set[str] = set()
    if replace_group_id and replace_group_id in groups:
        existing = groups[replace_group_id]
        replace_children.update(existing.get("member_ids") or [])
        replace_children.update(existing.get("children") or [])
        replace_children.add(replace_group_id)
    ungrouped_details = sorted(
        sid
        for sid in details
        if _fresh_detail(ledger, sid) is not None
        and (sid not in owned or sid in replace_children)
    )
    fresh_groups = sorted(
        gid
        for gid in groups
        if _fresh_group_body(ledger, gid) is not None
        and (gid not in owned or gid in replace_children)
        and gid != replace_group_id
    )
    return {"details": ungrouped_details, "groups": fresh_groups}


def frontier_payload(
    ledger: dict[str, Any],
    *,
    page: int = 0,
    page_size: int = 40,
    replace_group_id: str | None = None,
) -> dict[str, Any]:
    ids = frontier_ids(ledger, replace_group_id=replace_group_id)
    detail_page = page_list(ids["details"], page=page, page_size=page_size)
    group_page = page_list(ids["groups"], page=page, page_size=page_size)
    graph = ledger.get("graph") or {}
    return {
        "kind": "group_frontier",
        "replace_group_id": replace_group_id,
        "ungrouped_details": detail_page,
        "fresh_groups": group_page,
        "graph": {
            "entries": page_list(list(graph.get("entries") or []), page=page, page_size=page_size),
            "sccs_total": graph.get("sccs_total", len(graph.get("sccs") or [])),
            "shared_callees": page_list(list(graph.get("shared_callees") or []), page=page, page_size=page_size),
            "unknown_edges_total": graph.get("unknown_edges_total", len(graph.get("unknown_edges") or [])),
            "edges_total": graph.get("edges_total", len(graph.get("edges") or [])),
            "nodes_total": graph.get("nodes_total", len(graph.get("nodes") or [])),
            "structural_hints_total": graph.get(
                "structural_hints_total", len(graph.get("structural_hints") or [])
            ),
            "hint_disclaimer": "structural_hints are evidence only; do not import them as architecture",
        },
        "note": (
            "Empty claim returns frontier metadata only. Pass --input-ids-file with fresh "
            "ungrouped Details or groups that already have a body. Pagination is display only."
        ),
    }


def content_fingerprint(record: dict[str, Any] | None) -> str:
    if not record:
        return ""
    payload = {
        "behavior": record.get("behavior"),
        "body": record.get("body"),
        "version": record.get("version") or record.get("revision"),
        "member_ids": record.get("member_ids"),
        "children": record.get("children"),
        "inputs_outputs": record.get("inputs_outputs"),
        "effects": record.get("effects"),
        "failures": record.get("failures"),
        "dependencies": record.get("dependencies"),
        "unresolved": record.get("unresolved"),
        "nav_sentence": record.get("nav_sentence"),
        "question_answered": record.get("question_answered"),
        "grouping_reason": record.get("grouping_reason"),
        "entry_routes": record.get("entry_routes"),
        "partial": record.get("partial"),
        "evidence_summary": (record.get("extra") or {}).get("evidence_summary"),
        "presentation": (record.get("extra") or {}).get("presentation"),
        "navigation_input_hash": (record.get("extra") or {}).get("navigation_input_hash"),
        "group_stale": (record.get("extra") or {}).get("stale"),
        "stale": (record.get("provenance") or {}).get("stale"),
    }
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def group_selection_input_hash(
    ledger: dict[str, Any],
    input_ids: list[str],
    edges: list[dict],
) -> str:
    children = []
    for ident in input_ids:
        detail = (ledger.get("details") or {}).get(ident)
        group = (ledger.get("groups") or {}).get(ident)
        kind = "detail" if detail is not None else "group" if group is not None else "unknown"
        record = detail or group or {}
        children.append(
            {
                "id": ident,
                "kind": kind,
                "version": record.get("version") or record.get("revision"),
                "fingerprint": content_fingerprint(record),
                "fresh": (
                    _fresh_detail(ledger, ident) is not None if kind == "detail"
                    else _fresh_group_body(ledger, ident) is not None if kind == "group"
                    else False
                ),
            }
        )
    payload = {
        "source_revision": ledger.get("source_revision"),
        "children": children,
        "edges": edges,
    }
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def group_body_input_hash(ledger: dict[str, Any], group: dict[str, Any]) -> str:
    children = []
    for ident in list(group.get("member_ids") or []) + list(group.get("children") or []):
        record = (ledger.get("details") or {}).get(ident) or (ledger.get("groups") or {}).get(ident) or {}
        children.append({"id": ident, "fingerprint": content_fingerprint(record)})
    payload = {
        "group_id": group.get("group_id"),
        "version": group.get("version"),
        "presentation": (group.get("extra") or {}).get("presentation"),
        "member_ids": group.get("member_ids"),
        "children": children,
    }
    feedback = (group.get("extra") or {}).get("review_feedback")
    if feedback:
        payload["review_feedback"] = feedback
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def ancestor_group_ids(ledger: dict[str, Any], group_id: str) -> list[str]:
    found: list[str] = []
    groups = ledger.get("groups") or {}
    cursor = (groups.get(group_id) or {}).get("parent_id")
    seen = {group_id}
    while cursor:
        if cursor in seen:
            break
        seen.add(cursor)
        found.append(cursor)
        cursor = (groups.get(cursor) or {}).get("parent_id")
    return found


def invalidate_group_bodies(ledger: dict[str, Any], group_ids: list[str]) -> None:
    groups = ledger.setdefault("groups", {})
    tasks = ledger.setdefault("tasks", {})
    ordered = sorted(
        dict.fromkeys(group_ids),
        key=lambda group_id: len(ancestor_group_ids(ledger, group_id)),
        reverse=True,
    )
    for group_id in ordered:
        group = groups.get(group_id)
        if not isinstance(group, dict):
            continue
        if (
            (ledger.get("documentation_policy") or {}).get("version") == "weighted-v1"
            and (group.get("extra") or {}).get("presentation") == "navigation"
        ):
            _refresh_navigation_group(ledger, group_id)
            continue
        extra = dict(group.get("extra") or {})
        extra["stale"] = True
        extra["body_stale"] = True
        group["extra"] = extra
        groups[group_id] = group
        body_id = f"task:group_body:{group_id}"
        body_hash = group_body_input_hash(ledger, group)
        existing = tasks.get(body_id)
        payload = TaskRecord(
            task_id=body_id,
            kind="group_body",
            input_ids=[group_id],
            input_hash=body_hash,
            state="pending",
            extra={"group_id": group_id, "requeued": True},
        ).to_dict()
        if isinstance(existing, dict):
            payload["generation"] = int(existing.get("generation") or 0)
            payload["owner"] = None
            payload["lease_until"] = None
        tasks[body_id] = payload


def _navigation_evidence_summary(ledger: dict[str, Any], group: dict[str, Any]) -> dict[str, Any] | None:
    """Copy direct child facts verbatim into a deterministic navigation summary.

    Every value retains its source ID, including ``None`` for an unresolved
    check. An unavailable child makes the navigation group unavailable rather
    than silently omitting that child's evidence.
    """
    child_records: list[tuple[str, dict[str, Any], bool]] = []
    for member_id in group.get("member_ids") or []:
        detail = _fresh_detail(ledger, member_id)
        if detail is None:
            return None
        child_records.append((member_id, detail, False))
    for child_id in group.get("children") or []:
        child = _fresh_group_body(ledger, child_id)
        if child is None or not isinstance((child.get("extra") or {}).get("evidence_summary"), dict):
            return None
        child_records.append((child_id, child, True))
    if not child_records:
        return None
    behaviors: list[str] = []
    summary: dict[str, Any] = {field: [] for field in ("effects", "failures", "unresolved")}
    for child_id, record, is_group in child_records:
        source = (record.get("extra") or {}).get("evidence_summary") if is_group else record
        assert isinstance(source, dict)
        behavior = source.get("behavior") if is_group else record.get("nav_sentence") or record.get("behavior")
        if not isinstance(behavior, str) or not behavior.strip():
            return None
        behaviors.append(f"{child_id}: {behavior.strip()}")
        for field in ("effects", "failures", "unresolved"):
            if field not in source:
                return None
            summary[field].append({"source_id": child_id, "value": source[field]})
    title = str(group.get("question_answered") or group.get("group_id") or "Navigation").strip()
    summary["behavior"] = f"{title}: " + "; ".join(behaviors)
    return summary


def narrative_evidence_summary(
    ledger: dict[str, Any], group: dict[str, Any], body: str,
) -> dict[str, Any] | None:
    """Reuse direct-child facts without asking a writer to emit them twice."""
    if not isinstance(body, str) or not body.strip():
        return None
    summary = _navigation_evidence_summary(ledger, group)
    if summary is None:
        return None
    summary["behavior"] = body.strip()
    return summary


def _refresh_navigation_group(ledger: dict[str, Any], group_id: str) -> None:
    group = (ledger.get("groups") or {}).get(group_id)
    if not isinstance(group, dict):
        return
    extra = dict(group.get("extra") or {})
    summary = _navigation_evidence_summary(ledger, group)
    if summary is None or extra.get("review_hold"):
        extra.pop("evidence_summary", None)
        extra.pop("navigation_input_hash", None)
        extra["stale"] = True
        extra["body_stale"] = True
    else:
        extra["evidence_summary"] = summary
        extra["navigation_input_hash"] = group_body_input_hash(ledger, group)
        extra.pop("stale", None)
        extra.pop("body_stale", None)
    group["extra"] = extra
    ledger["groups"][group_id] = group


def _has_cycle(child_map: dict[str, list[str]]) -> str | None:
    visiting: set[str] = set()
    seen: set[str] = set()

    def walk(node: str) -> str | None:
        if node in visiting:
            return node
        if node in seen:
            return None
        visiting.add(node)
        for child in child_map.get(node) or []:
            hit = walk(child)
            if hit:
                return hit
        visiting.remove(node)
        seen.add(node)
        return None

    for node in child_map:
        hit = walk(node)
        if hit:
            return hit
    return None


def validate_group_evidence_summary(value: object) -> bool:
    """Validate the authored summary that makes a narrative group reusable.

    ``None`` means the author could not establish that category, while an
    empty list means the author checked it and found none. Navigation groups
    derive a richer, source-attributed summary mechanically instead.
    """
    if not isinstance(value, dict):
        return False
    behavior = value.get("behavior")
    if not isinstance(behavior, str) or not behavior.strip():
        return False
    for field in ("effects", "failures", "unresolved"):
        if field not in value:
            return False
        items = value[field]
        if items is not None and (
            not isinstance(items, list)
            or any(not isinstance(item, str) or not item.strip() for item in items)
        ):
            return False
    return True


def validate_group_plans(
    plans: list[dict[str, Any]],
    deferred_ids: list[str],
    ledger: dict[str, Any],
    *,
    input_ids: list[str],
    replace_group_id: str | None = None,
) -> list[dict]:
    residuals: list[dict] = []
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    selected = list(input_ids)
    selected_set = set(selected)
    if len(selected_set) != len(selected):
        residuals.append({"code": "duplicate_input_id"})
    if not plans and not deferred_ids:
        residuals.append({"code": "empty_claim"})
        return residuals

    policy = ledger.get("documentation_policy") or {}
    weighted = policy.get("version") == "weighted-v1"
    if weighted:
        limit = policy.get("group_limit")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            residuals.append({"code": "invalid_group_limit", "configured": limit})
        else:
            incoming = {plan.get("group_id") for plan in plans if isinstance(plan.get("group_id"), str)}
            active = {
                group_id for group_id, record in groups.items()
                if not ((record.get("extra") or {}).get("replaced_by"))
            }
            if replace_group_id and replace_group_id not in incoming:
                active.discard(replace_group_id)
            count_after = len(active | incoming)
            if count_after > limit:
                residuals.append(
                    {"code": "group_limit_exceeded", "limit": limit, "count_after": count_after}
                )

    new_ids: list[str] = []
    assigned: dict[str, str] = {}
    child_map: dict[str, list[str]] = {}
    for plan in plans:
        group_id = plan.get("group_id")
        if not isinstance(group_id, str) or not group_id.strip():
            residuals.append({"code": "missing_group_id"})
            continue
        if group_id in new_ids or (group_id in groups and group_id != replace_group_id):
            residuals.append({"code": "duplicate_group_id", "group_id": group_id})
        new_ids.append(group_id)
        members = plan.get("member_ids") or []
        children = plan.get("children") or []
        if not isinstance(members, list) or not isinstance(children, list):
            residuals.append({"code": "members_or_children_not_list", "group_id": group_id})
            continue
        presentation = plan.get("presentation", "narrative")
        if weighted:
            if presentation not in {"navigation", "narrative"}:
                residuals.append({"code": "invalid_group_presentation", "group_id": group_id})
            elif presentation == "navigation":
                if str(plan.get("body") or "").strip():
                    residuals.append({"code": "navigation_body_forbidden", "group_id": group_id})
                if len(members) + len(children) == 1:
                    residuals.append(
                        {"code": "empty_pass_through_chain", "group_id": group_id, "child_id": (members + children)[0]}
                    )
            elif str(plan.get("body") or "").strip():
                residuals.append({"code": "weighted_group_body_must_use_task", "group_id": group_id})
        elif "presentation" in plan and presentation != "narrative":
            residuals.append({"code": "presentation_requires_weighted_policy", "group_id": group_id})
        if not members and not children:
            residuals.append({"code": "empty_group", "group_id": group_id})
        if len(children) == 1 and not members:
            residuals.append({"code": "empty_pass_through_chain", "group_id": group_id, "child_id": children[0]})
        for member in members:
            if member in groups or member in {item.get("group_id") for item in plans}:
                residuals.append({"code": "member_must_be_detail", "group_id": group_id, "member_id": member})
            elif member not in details:
                residuals.append({"code": "unknown_member", "group_id": group_id, "member_id": member})
            elif _fresh_detail(ledger, member) is None:
                residuals.append({"code": "input_not_fresh", "group_id": group_id, "member_id": member})
            if member not in selected_set:
                residuals.append({"code": "member_not_in_input", "group_id": group_id, "member_id": member})
            previous = assigned.get(member)
            if previous:
                residuals.append(
                    {
                        "code": "duplicate_primary_parent",
                        "member_id": member,
                        "existing": previous,
                        "incoming": group_id,
                    }
                )
            else:
                assigned[member] = group_id
        for child in children:
            child_is_new = any(item.get("group_id") == child for item in plans)
            if child in details:
                residuals.append({"code": "child_must_be_group", "group_id": group_id, "child_id": child})
            elif child not in groups and not child_is_new:
                residuals.append({"code": "unknown_child", "group_id": group_id, "child_id": child})
            elif child in groups and _fresh_group_body(ledger, child) is None and child != replace_group_id:
                residuals.append({"code": "child_body_not_fresh", "group_id": group_id, "child_id": child})
            if child not in selected_set and not child_is_new:
                residuals.append({"code": "child_not_in_input", "group_id": group_id, "child_id": child})
            previous = assigned.get(child)
            if previous:
                residuals.append(
                    {
                        "code": "duplicate_primary_parent",
                        "member_id": child,
                        "existing": previous,
                        "incoming": group_id,
                    }
                )
            else:
                assigned[child] = group_id
        child_map[group_id] = list(children)
        declared_parent = plan.get("parent_id")
        derived = None
        for other in plans:
            if group_id in (other.get("children") or []):
                derived = other.get("group_id")
                break
        if derived is None:
            derived = owned_primary_parents(ledger, skip_group_id=replace_group_id).get(group_id)
        if declared_parent not in {None, "", derived}:
            residuals.append(
                {
                    "code": "parent_id_mismatch",
                    "group_id": group_id,
                    "declared": declared_parent,
                    "derived": derived,
                }
            )

    owned = owned_primary_parents(ledger, skip_group_id=replace_group_id)
    for ident, parent in assigned.items():
        existing = owned.get(ident)
        if existing and existing != parent and existing != replace_group_id:
            residuals.append(
                {
                    "code": "duplicate_primary_group",
                    "member_id": ident,
                    "existing": existing,
                    "incoming": parent,
                }
            )

    deferred_set = set(deferred_ids)
    if len(deferred_set) != len(deferred_ids):
        residuals.append({"code": "duplicate_deferred_id"})
    for ident in deferred_ids:
        if ident not in selected_set:
            residuals.append({"code": "deferred_not_in_input", "id": ident})
        if ident in assigned:
            residuals.append({"code": "deferred_and_grouped", "id": ident})
        if ident in details and _fresh_detail(ledger, ident) is None:
            residuals.append({"code": "deferred_not_fresh", "id": ident})
        if ident in groups and _fresh_group_body(ledger, ident) is None:
            residuals.append({"code": "deferred_not_fresh", "id": ident})

    leftover = selected_set - set(assigned) - deferred_set
    for ident in sorted(leftover):
        residuals.append({"code": "input_not_partitioned", "id": ident})

    cycle = _has_cycle(child_map)
    if cycle:
        residuals.append({"code": "group_children_cycle", "node": cycle})

    existing_child_map = {
        gid: list(item.get("children") or [])
        for gid, item in groups.items()
        if gid != replace_group_id
    }
    existing_child_map.update(child_map)
    existing_cycle = _has_cycle(existing_child_map)
    if existing_cycle:
        residuals.append({"code": "group_children_cycle", "node": existing_cycle})
    return residuals


def validate_group_plan(plan: dict[str, Any], ledger: dict[str, Any]) -> list[dict]:
    """Single-plan adapter used by older callers; prefers input_ids from the plan."""

    members = list(plan.get("member_ids") or [])
    children = list(plan.get("children") or [])
    input_ids = list(plan.get("input_ids") or (members + children))
    return validate_group_plans([plan], list(plan.get("deferred_ids") or []), ledger, input_ids=input_ids)


def _queue_group_body(ledger: dict[str, Any], group: dict[str, Any]) -> None:
    tasks = ledger.setdefault("tasks", {})
    group_id = group["group_id"]
    body_id = f"task:group_body:{group_id}"
    body_hash = group_body_input_hash(ledger, group)
    payload = TaskRecord(
        task_id=body_id,
        kind="group_body",
        input_ids=[group_id],
        input_hash=body_hash,
        state="pending",
        extra={"group_id": group_id},
    ).to_dict()
    existing = tasks.get(body_id)
    if isinstance(existing, dict):
        payload["generation"] = int(existing.get("generation") or 0)
        payload["owner"] = None
        payload["lease_until"] = None
    tasks[body_id] = payload


def submit_groups(
    ledger: dict[str, Any],
    *,
    task_id: str,
    owner: str,
    generation: int,
    input_hash: str,
    plans: list[dict[str, Any]],
    deferred_ids: list[str] | None = None,
    replace_group_id: str | None = None,
) -> TaskRecord:
    tasks = ledger.setdefault("tasks", {})
    raw = tasks.get(task_id)
    if raw is None:
        raise StoreError(f"unknown task {task_id}")
    task = TaskRecord.from_dict(raw)
    if task.generation != generation:
        raise StaleWriteError(f"stale generation for {task_id}: have {generation} current {task.generation}")
    if task.owner != owner:
        raise StaleWriteError(f"owner mismatch for {task_id}")
    if input_hash and task.input_hash and input_hash != task.input_hash:
        raise StaleWriteError(
            f"stale input_hash for {task_id}: envelope {input_hash} current {task.input_hash}"
        )
    deferred_ids = list(deferred_ids or [])
    residuals = validate_group_plans(
        plans,
        deferred_ids,
        ledger,
        input_ids=list(task.input_ids),
        replace_group_id=replace_group_id or (task.extra or {}).get("replace_group_id"),
    )
    if (task.extra or {}).get("created_by") == "source_review":
        reviewed_id = (task.extra or {}).get("replace_group_id")
        if len(plans) != 1 or plans[0].get("group_id") != reviewed_id or deferred_ids:
            residuals.append({
                "code": "review_regroup_requires_same_id",
                "group_id": reviewed_id,
            })
    task.residual = residuals
    if residuals:
        task.state = "needs_repair"
        task.output_refs = []
        tasks[task_id] = task.to_dict()
        return task

    groups = ledger.setdefault("groups", {})
    accepted: list[str] = []
    replace_id = replace_group_id or (task.extra or {}).get("replace_group_id")
    child_to_parent: dict[str, str] = {}
    for plan in plans:
        policy = ledger.get("documentation_policy") or {}
        weighted = policy.get("version") == "weighted-v1"
        presentation = plan.get("presentation", "narrative") if weighted else "narrative"
        extra = {k: v for k, v in plan.items() if k not in GROUP_PLAN_KEYS}
        if weighted:
            extra["presentation"] = presentation
        record = GroupRecord(
            group_id=str(plan["group_id"]),
            children=list(plan.get("children") or []),
            member_ids=list(plan.get("member_ids") or []),
            question_answered=str(plan.get("question_answered") or ""),
            grouping_reason=str(plan.get("grouping_reason") or ""),
            entry_routes=list(plan.get("entry_routes") or []),
            relations=list(plan.get("relations") or []),
            body=str(plan.get("body") or ""),
            version=int(plan.get("version") or 1),
            parent_id=plan.get("parent_id"),
            partial=bool(plan.get("partial", False)),
            extra=extra,
        )
        existing = groups.get(record.group_id)
        if isinstance(existing, dict):
            record.version = int(existing.get("version") or 1) + 1
        for child in record.children:
            child_to_parent[child] = record.group_id
        groups[record.group_id] = record.to_dict()
        accepted.append(record.group_id)
    if replace_id and replace_id not in accepted and replace_id in groups:
        extra = dict(groups[replace_id].get("extra") or {})
        extra["replaced_by"] = accepted
        extra["stale"] = True
        extra["body_stale"] = True
        groups[replace_id]["extra"] = extra
        body_id = f"task:group_body:{replace_id}"
        existing_body = tasks.get(body_id)
        if isinstance(existing_body, dict):
            body_extra = dict(existing_body.get("extra") or {})
            body_extra["superseded"] = True
            body_extra["replaced_by"] = accepted
            existing_body["extra"] = body_extra
            if existing_body.get("state") in {"pending", "needs_repair", "leased", "returned"}:
                existing_body["state"] = "stale"
            tasks[body_id] = existing_body
        invalidate_group_bodies(ledger, ancestor_group_ids(ledger, replace_id))
    for child_id, parent_id in child_to_parent.items():
        child = groups.get(child_id)
        if isinstance(child, dict):
            child["parent_id"] = parent_id
            groups[child_id] = child
    for group_id in sorted(accepted, key=lambda ident: len(ancestor_group_ids(ledger, ident)), reverse=True):
        group = groups[group_id]
        presentation = (group.get("extra") or {}).get("presentation", "narrative")
        body_id = f"task:group_body:{group_id}"
        if weighted and presentation == "navigation":
            _refresh_navigation_group(ledger, group_id)
            old_body = tasks.get(body_id)
            if isinstance(old_body, dict):
                old_body_extra = dict(old_body.get("extra") or {})
                old_body_extra["superseded"] = True
                old_body_extra["superseded_reason"] = "navigation_group_needs_no_body"
                old_body["extra"] = old_body_extra
                if old_body.get("state") in {"pending", "needs_repair", "leased", "returned"}:
                    old_body["state"] = "stale"
                tasks[body_id] = old_body
        elif not str(group.get("body") or "").strip():
            _queue_group_body(ledger, group)
        elif weighted and isinstance(tasks.get(body_id), dict):
            old_body = tasks[body_id]
            old_body_extra = dict(old_body.get("extra") or {})
            old_body_extra["superseded"] = True
            old_body_extra["superseded_reason"] = "group_plan_includes_body"
            old_body["extra"] = old_body_extra
            if old_body.get("state") in {"pending", "needs_repair", "leased", "returned"}:
                old_body["state"] = "stale"
            tasks[body_id] = old_body
    ancestors = [
        ancestor
        for group_id in accepted
        for ancestor in ancestor_group_ids(ledger, group_id)
        if ancestor not in accepted
    ]
    if ancestors:
        invalidate_group_bodies(ledger, ancestors)
    extra = dict(task.extra or {})
    extra["deferred_ids"] = deferred_ids
    task.extra = extra
    task.output_refs = accepted
    task.residual = []
    task.state = "committed"
    tasks[task_id] = task.to_dict()
    return task


def submit_group(
    ledger: dict[str, Any],
    *,
    task_id: str,
    owner: str,
    generation: int,
    plan: dict[str, Any],
) -> TaskRecord:
    return submit_groups(
        ledger,
        task_id=task_id,
        owner=owner,
        generation=generation,
        input_hash=str(plan.get("input_hash") or ""),
        plans=[plan],
        deferred_ids=list(plan.get("deferred_ids") or []),
        replace_group_id=plan.get("replace_group_id"),
    )


def submit_review(
    ledger: dict[str, Any],
    *,
    task_id: str,
    owner: str,
    generation: int,
    payload: dict[str, Any],
    expected_input_hash: str | None = None,
    expected_call_id: str | None = None,
) -> TaskRecord:
    tasks = ledger.setdefault("tasks", {})
    raw = tasks.get(task_id)
    if raw is None:
        raise StoreError(f"unknown task {task_id}")
    task = TaskRecord.from_dict(raw)
    if task.generation != generation or task.owner != owner:
        raise StaleWriteError(f"stale review submit for {task_id}")
    if expected_input_hash and expected_input_hash != task.input_hash:
        raise StaleWriteError(
            f"stale review input_hash for {task_id}: envelope {expected_input_hash} current {task.input_hash}"
        )
    claimed_call = (task.extra or {}).get("call_id")
    if expected_call_id and claimed_call and expected_call_id != claimed_call:
        raise StaleWriteError(f"review call_id mismatch: envelope {expected_call_id} task {claimed_call}")
    reviews = ledger.setdefault("reviews", {})
    review_id = str(payload.get("review_id") or f"review:{uuid.uuid4().hex}")
    packed_chars = int((task.extra or {}).get("packed_source_chars") or 0)
    record = ReviewRecord(
        review_id=review_id,
        task_id=task_id,
        target_ids=list(payload.get("target_ids") or task.input_ids),
        packet_hash=payload.get("packet_hash") or (task.extra or {}).get("packet_hash"),
        source_chars=packed_chars,
        verdict=payload.get("verdict"),
        notes=str(payload.get("notes") or ""),
        extra={
            **dict(payload.get("extra") or {}),
            "self_reported_source_chars": payload.get("source_chars"),
            "self_report_ignored": True,
            "call_id": claimed_call or expected_call_id,
        },
    )
    reviews[review_id] = record.to_dict()
    task.output_refs = [review_id]
    task.residual = list(payload.get("residual") or [])
    task.state = "needs_repair" if task.residual else "committed"
    tasks[task_id] = task.to_dict()
    return task


def is_historical_task(task: TaskRecord | dict[str, Any]) -> bool:
    extra = task.extra if isinstance(task, TaskRecord) else (task.get("extra") or {})
    return bool(extra.get("tombstone") or extra.get("superseded") or extra.get("superseded_by"))


def is_current_open_task(task: TaskRecord) -> bool:
    if is_historical_task(task):
        return False
    return task.state in {"pending", "leased", "needs_repair", "stale"}


def derived_status(ledger: dict[str, Any]) -> dict[str, Any]:
    tasks = [TaskRecord.from_dict(item) for item in (ledger.get("tasks") or {}).values()]
    counts: dict[str, int] = {}
    for task in tasks:
        counts[task.state] = counts.get(task.state, 0) + 1
        counts[f"kind:{task.kind}"] = counts.get(f"kind:{task.kind}", 0) + 1
        if is_historical_task(task):
            counts["historical"] = counts.get("historical", 0) + 1
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    budget = ledger.get("budget") or {}
    documentation = ledger.get("documentation_policy") or {}
    module_first = documentation.get("version") == "module-first-v2"
    pending = [task.task_id for task in tasks if is_current_open_task(task)]
    frontier = frontier_payload(ledger, page=0, page_size=20)
    native_usage_totals = {key: 0 for key in (
        "input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens",
    )}
    native_usage_call_count = 0
    native_sent_without_usage_count = 0
    for call in (ledger.get("calls") or {}).values():
        if (call.get("extra") or {}).get("send_evidence") != "sent_native":
            continue
        usage = call.get("usage")
        if not isinstance(usage, dict):
            native_sent_without_usage_count += 1
            continue
        native_usage_call_count += 1
        for key in native_usage_totals:
            native_usage_totals[key] += int(usage.get(key) or 0)
    return {
        "schema": ledger.get("schema"),
        "run_id": ledger.get("run_id"),
        "source_revision": ledger.get("source_revision"),
        "ledger_revision": ledger.get("ledger_revision"),
        "render_revision": ledger.get("render_revision"),
        "task_counts": counts,
        "native_usage_totals": native_usage_totals,
        "native_usage_call_count": native_usage_call_count,
        "native_sent_without_usage_count": native_sent_without_usage_count,
        "overall_token_budget": overall_token_budget(ledger),
        "detail_count": len(details),
        "group_count": len(groups),
        "s_chars": budget.get("s_chars"),
        "source_read_chars": budget.get("source_read_chars"),
        "source_exposure_chars": budget.get("source_exposure_chars", budget.get("source_read_chars")),
        "known_source_chars": budget.get("known_source_chars"),
        "possible_source_upper_chars": budget.get("possible_source_upper_chars"),
        "exposure_upper_chars": budget.get("exposure_upper_chars"),
        "reserved_chars": budget.get("reserved_chars"),
        "logical_exposure_status": budget.get("logical_exposure_status"),
        "evidence_completeness": budget.get("evidence_completeness"),
        "unbounded_source_gap": budget.get("unbounded_source_gap"),
        "provider_source_input_chars": budget.get("provider_source_input_chars"),
        "cap_chars": 2 * int(budget.get("s_chars") or 0),
        "dispatch_cap_multiplier": budget.get("dispatch_cap_multiplier"),
        "dispatch_cap_chars": budget.get("dispatch_cap_chars"),
        "documentation_budget": ({
            key: documentation.get(key)
            for key in (
                "version", "tokenizer", "source_tokens", "published_cap_tokens",
                "fixed_navigation_tokens", "detail_allocated_tokens",
                "group_reserve_tokens", "repair_reserve_tokens", "group_limit",
            )
        } if documentation.get("version") in {"weighted-v1", "module-first-v2"} else None),
        "open_tasks": pending,
        "fragment_plan_residuals": fragment_plan_residuals(ledger),
        "design_ready": ({
            "catalogued_symbol_count": len((ledger.get("inventory") or {}).get("symbols") or {}),
            "module_plan_state": "structural_candidate",
            "individually_explained_count": sum(
                value.get("state") == "source_checked"
                and value.get("content_sha256") == hashlib.sha256(json.dumps(
                    details.get(sid), ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()).hexdigest()
                for sid, value in (ledger.get("fact_reviews") or {}).items()
                if isinstance(details.get(sid), dict) and isinstance(value, dict)
                and ((ledger.get("inventory") or {}).get("symbols") or {}).get(sid, {}).get("kind") in {"function", "method", "lambda"}
            ),
            "batch_accepted_count": sum(
                value.get("state") == "batch_accepted"
                and value.get("content_sha256") == hashlib.sha256(json.dumps(
                    details.get(sid), ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()).hexdigest()
                for sid, value in (ledger.get("fact_reviews") or {}).items()
                if isinstance(details.get(sid), dict) and isinstance(value, dict)
                and ((ledger.get("inventory") or {}).get("symbols") or {}).get(sid, {}).get("kind") in {"function", "method", "lambda"}
            ),
            "note": "Use module_plan.json, fact review states, and source evidence; catalogue membership alone is not explanation",
        } if module_first else _design_ready(ledger)),
        "frontier": frontier,
        "layering": _layering_health(ledger),
    }


def _layering_health(ledger: dict[str, Any]) -> dict[str, Any]:
    """MOC-style hierarchy health signals for the reviewer (not a hard gate)."""
    groups = ledger.get("groups") or {}
    current = {
        gid: g
        for gid, g in groups.items()
        if not ((g.get("extra") or {}).get("replaced_by"))
    }
    if not current:
        return {"groups": 0}
    depth: dict[str, int] = {}

    def depth_of(gid: str) -> int:
        if gid in depth:
            return depth[gid]
        group = current.get(gid)
        if group is None:
            return 0
        parent = group.get("parent_id")
        if not parent or parent not in current or parent == gid:
            depth[gid] = 1
            return 1
        depth[gid] = depth_of(parent) + 1
        return depth[gid]

    depths = {gid: depth_of(gid) for gid in current}
    single_child = sorted(
        gid
        for gid, g in current.items()
        if (g.get("children") or []) and len(g.get("children") or []) + len(g.get("member_ids") or []) < 2
    )
    heavy = sorted(
        (gid for gid, g in current.items() if len(g.get("member_ids") or []) > 40),
        key=lambda gid: -len(current[gid].get("member_ids") or []),
    )
    return {
        "groups": len(current),
        "max_depth": max(depths.values()) if depths else 0,
        "single_child_chain_groups": single_child[:30],
        "heavy_groups_over_40_members": heavy[:30],
        "note": "signals for the reviewer's nesting judgment; not a hard gate",
    }


def _design_ready(ledger: dict[str, Any]) -> dict[str, Any]:
    symbols = set(((ledger.get("inventory") or {}).get("symbols") or {}))
    covered = {sid for sid in symbols if _fresh_detail(ledger, sid) is not None}
    uncovered = sorted(symbols - covered)
    ids = frontier_ids(ledger)
    return {
        "uncovered_symbol_count": len(uncovered),
        "uncovered_sample": uncovered[:30],
        "groups": len(ledger.get("groups") or {}),
        "ungrouped_fresh_details": ids["details"][:30],
        "fresh_groups_without_parent": ids["groups"][:30],
        "ungrouped_fresh_detail_count": len(ids["details"]),
        "fresh_group_count": len(ids["groups"]),
        "note": (
            "grouping is imported by the Astra architecture role via claim --input-ids-file; "
            "runner does not invent folders or connected buckets as architecture"
        ),
    }


def load_unique_packets(ledger: dict[str, Any]) -> dict[str, Packet]:
    index = PacketIndex.from_dict(ledger.get("packets") or {"window_chars": 0, "packets": []})
    return unique_by_id(index.packets, id_of=lambda packet: packet.packet_id, kind="packet")


_NOT_SENT_EVIDENCE = frozenset({"not_sent_bootstrap", "bootstrap_failed"})
_REJECTED_DISPOSITIONS = frozenset({"provider_failed", "rejected"})
_PRESENTED_SEND = frozenset({"presented", "sent_native", "sent_http"})
_PRESENTED_STATES = frozenset({"imported", "durable", "sent"})


def _call_extra(call: dict[str, Any]) -> dict[str, Any]:
    extra = call.get("extra")
    return extra if isinstance(extra, dict) else {}


def _call_is_not_sent(call: dict[str, Any]) -> bool:
    extra = _call_extra(call)
    send = str(extra.get("send_evidence") or extra.get("disposition") or "")
    return send in _NOT_SENT_EVIDENCE or extra.get("disposition") in _NOT_SENT_EVIDENCE


def _call_counts_as_presented(call: dict[str, Any]) -> bool:
    """Persisted presentation evidence only. Planned source_chars and not_sent do not count."""

    if _call_is_not_sent(call):
        return False
    extra = _call_extra(call)
    if extra.get("disposition") in _REJECTED_DISPOSITIONS:
        return False
    state = str(call.get("state") or "")
    send = str(extra.get("send_evidence") or "")
    disposition = str(extra.get("disposition") or "")
    if send in _PRESENTED_SEND and state in _PRESENTED_STATES:
        return True
    return disposition == "accepted" and state in {"imported", "durable"}


def _file_char_length(ledger: dict[str, Any], path: str) -> int | None:
    record = ((ledger.get("inventory") or {}).get("files") or {}).get(path)
    if not isinstance(record, dict) or record.get("char_length") is None:
        return None
    try:
        return int(record["char_length"])
    except (TypeError, ValueError):
        return None


def _parse_span_dict(item: dict[str, Any]) -> tuple[str, CharSpan] | None:
    try:
        span = CharSpan(int(item["start"]), int(item["end"]))
    except (KeyError, TypeError, ValueError):
        return None
    if span.length <= 0:
        return None
    return str(item.get("path") or ""), span


def _subtract_span_sets(left: Sequence[CharSpan], right: Sequence[CharSpan]) -> tuple[CharSpan, ...]:
    remaining = list(merge_char_spans(left))
    for hole in merge_char_spans(right):
        next_remaining: list[CharSpan] = []
        for span in remaining:
            if hole.end <= span.start or hole.start >= span.end:
                next_remaining.append(span)
                continue
            if span.start < hole.start:
                next_remaining.append(CharSpan(span.start, hole.start))
            if hole.end < span.end:
                next_remaining.append(CharSpan(hole.end, span.end))
        remaining = [item for item in next_remaining if item.length > 0]
    return tuple(remaining)


def _presented_spans_for_call(
    call: dict[str, Any],
    packet: Packet,
    char_length: int | None,
    residuals: list[dict[str, Any]],
) -> list[CharSpan]:
    call_id = str(call.get("call_id") or "")
    raw_spans = [item for item in (call.get("source_spans") or []) if item is not None]
    if not raw_spans:
        residuals.append(
            {
                "code": "missing_call_source_spans",
                "call_id": call_id,
                "task_id": call.get("task_id"),
                "packet_id": packet.packet_id,
                "source_chars": call.get("source_chars"),
            }
        )
        return []
    valid: list[CharSpan] = []
    for item in raw_spans:
        if not isinstance(item, dict):
            residuals.append(
                {
                    "code": "invalid_call_source_span",
                    "call_id": call_id,
                    "packet_id": packet.packet_id,
                }
            )
            continue
        parsed = _parse_span_dict(item)
        if parsed is None:
            residuals.append(
                {
                    "code": "invalid_call_source_span",
                    "call_id": call_id,
                    "packet_id": packet.packet_id,
                    "span": item,
                }
            )
            continue
        path, span = parsed
        path = path or packet.path
        if path != packet.path:
            residuals.append(
                {
                    "code": "invalid_call_source_path",
                    "call_id": call_id,
                    "path": path,
                    "expected_path": packet.path,
                    "packet_id": packet.packet_id,
                }
            )
            continue
        if char_length is not None and (span.start < 0 or span.end > char_length):
            residuals.append(
                {
                    "code": "call_source_span_out_of_bounds",
                    "call_id": call_id,
                    "path": path,
                    "start": span.start,
                    "end": span.end,
                    "char_length": char_length,
                    "packet_id": packet.packet_id,
                }
            )
            continue
        valid.append(span)
    return valid


def fragment_plan_residuals(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate persisted packets/tasks/calls against the fragment plan. Not list-only."""

    residuals: list[dict[str, Any]] = []
    packet_list = list((ledger.get("packets") or {}).get("packets") or [])
    try:
        packet_map = unique_by_id(
            [Packet.from_dict(item) for item in packet_list],
            id_of=lambda packet: packet.packet_id,
            kind="packet",
        )
    except DuplicateIdentityError as exc:
        residuals.append({"code": "duplicate_packet_id", "message": str(exc)})
        packet_map = {}
    tasks = ledger.get("tasks") or {}
    try:
        unique_by_id(tasks.values(), id_of=lambda item: str(item.get("task_id") or ""), kind="task")
    except DuplicateIdentityError as exc:
        residuals.append({"code": "duplicate_task_id", "message": str(exc)})
    fragment_ids: list[str] = []
    expected_by_symbol: dict[str, list[str]] = {}
    for packet in packet_map.values():
        for fragment in packet.fragments:
            fragment_ids.append(fragment.fragment_id)
            expected_by_symbol.setdefault(fragment.symbol_id, []).append(fragment.fragment_id)
    try:
        unique_by_id(fragment_ids, id_of=lambda item: item, kind="fragment")
    except DuplicateIdentityError as exc:
        residuals.append({"code": "duplicate_fragment_id", "message": str(exc)})
    details = ledger.get("details") or {}
    calls = ledger.get("calls") or {}
    fact_batches = ledger.get("fact_batches") or {}
    packet_fact_task = {
        packet_id: f"task:fact_author:{batch_id}"
        for batch_id, batch in fact_batches.items()
        if not batch.get("superseded") and not batch.get("attribution")
        for packet_id in batch.get("packet_ids") or []
    }
    symbols = (ledger.get("inventory") or {}).get("symbols") or {}
    for packet_id, packet in packet_map.items():
        if not packet.first_round:
            continue
        task_id = packet_fact_task.get(packet_id) or (
            f"task:fact_author:{packet_id}" if ledger.get("fact_workflow_version")
            else f"task:detail:{packet_id}"
        )
        raw_task = tasks.get(task_id)
        if fact_batches and packet_id not in packet_fact_task:
            continue
        if ledger.get("fact_workflow_version") and packet_id not in packet_fact_task and not packet.fragments:
            continue
        if raw_task is None:
            residuals.append({"code": "missing_packet_task", "packet_id": packet_id})
            continue
        task = TaskRecord.from_dict(raw_task)
        expected_outputs = [fragment.output_id for fragment in packet.fragments
                            if not fact_batches or symbols[fragment.symbol_id]["kind"] in {"function", "method", "lambda"}]
        if not ledger.get("fact_workflow_version") and not expected_outputs:
            expected_outputs = [packet.packet_id]
        if fact_batches and not expected_outputs:
            continue
        if not is_historical_task(task) and not set(expected_outputs) <= set(task.input_ids) and task.state != "committed":
            residuals.append(
                {
                    "code": "task_fragment_mismatch",
                    "task_id": task_id,
                    "expected": expected_outputs,
                    "actual": list(task.input_ids),
                }
            )
        if task.state == "committed" and not is_historical_task(task):
            missing_outputs = [
                output_id
                for output_id in expected_outputs
                if not (
                    isinstance(details.get(output_id), dict)
                    and str((details.get(output_id) or {}).get("behavior") or "").strip()
                )
            ]
            if missing_outputs:
                residuals.append(
                    {
                        "code": "committed_missing_fragments",
                        "task_id": task_id,
                        "missing": missing_outputs,
                    }
                )
    for symbol_id, fragment_ids_for_symbol in expected_by_symbol.items():
        if fact_batches and symbols[symbol_id]["kind"] not in {"function", "method", "lambda"}:
            continue
        unique_ids = list(dict.fromkeys(fragment_ids_for_symbol))
        if len(unique_ids) <= 1:
            continue
        merge_id = f"task:merge:{symbol_id}"
        raw_merge = tasks.get(merge_id)
        if raw_merge is None:
            residuals.append({"code": "missing_merge_task", "symbol_id": symbol_id})
            continue
        extra = raw_merge.get("extra") or {}
        consume = list(extra.get("fragment_ids") or extra.get("slice_ids") or [])
        if set(consume) != set(unique_ids):
            residuals.append(
                {
                    "code": "merge_fragment_mismatch",
                    "symbol_id": symbol_id,
                    "expected": unique_ids,
                    "actual": consume,
                }
            )
        missing_frags = [item for item in unique_ids if item not in details]
        if raw_merge.get("state") == "committed" and missing_frags:
            residuals.append({"code": "merge_missing_slices", "symbol_id": symbol_id, "missing": missing_frags})
        canonical = details.get(symbol_id)
        if isinstance(canonical, dict) and not (canonical.get("provenance") or {}).get("historical"):
            if missing_frags:
                residuals.append(
                    {
                        "code": "canonical_before_merge",
                        "symbol_id": symbol_id,
                    }
                )
    for packet_id, packet in packet_map.items():
        if not packet.first_round:
            continue
        task_id = packet_fact_task.get(packet_id) or (
            f"task:fact_author:{packet_id}" if ledger.get("fact_workflow_version")
            else f"task:detail:{packet_id}"
        )
        raw_task = tasks.get(task_id)
        if raw_task is None or is_historical_task(raw_task):
            continue
        presented_spans: list[CharSpan] = []
        char_length = _file_char_length(ledger, packet.path)
        for call in calls.values():
            if not isinstance(call, dict):
                continue
            if str(call.get("task_id") or "") != task_id:
                continue
            bound_task = tasks.get(str(call.get("task_id") or ""))
            if not isinstance(bound_task, dict) or bound_task.get("kind") not in {"detail", "fact_author"}:
                continue
            if not _call_counts_as_presented(call):
                continue
            scoped_call = call
            if packet_fact_task.get(packet_id):
                relevant = [span for span in call.get("source_spans") or []
                            if isinstance(span, dict) and span.get("path") == packet.path]
                if not relevant:
                    continue
                scoped_call = {**call, "source_spans": relevant}
            presented_spans.extend(_presented_spans_for_call(scoped_call, packet, char_length, residuals))
        if raw_task.get("state") != "committed":
            continue
        uncovered = _subtract_span_sets(packet.spans, presented_spans)
        if uncovered:
            residuals.append(
                {
                    "code": "committed_first_round_uncovered",
                    "task_id": task_id,
                    "packet_id": packet_id,
                    "path": packet.path,
                    "uncovered": [span.to_dict() for span in uncovered],
                    "uncovered_chars": sum(span.length for span in uncovered),
                }
            )
    return residuals
