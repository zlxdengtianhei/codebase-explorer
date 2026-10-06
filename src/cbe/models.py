"""Ledger records. Status is derived; producers cannot write PASS."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


LEDGER_SCHEMA = "cbe-semantic-ledger/1"
TASK_STATES = (
    "pending",
    "leased",
    "returned",
    "committed",
    "needs_repair",
    "stale",
)
TASK_KINDS = ("detail", "group", "review", "group_body", "merge", "module_author", "module_review")
CALL_STATES = ("prepared", "sent", "durable", "imported", "uncertain", "released")


def _require(value: Any, name: str) -> Any:
    if value is None or value == "":
        raise ValueError(f"{name} is required")
    return value


@dataclass
class TaskRecord:
    task_id: str
    kind: str
    input_ids: list[str]
    input_hash: str
    state: str
    owner: str | None = None
    owner_pid: int | None = None
    lease_until: str | None = None
    generation: int = 0
    output_refs: list[str] = field(default_factory=list)
    residual: list[dict] = field(default_factory=list)
    packet_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "kind": self.kind,
            "input_ids": list(self.input_ids),
            "input_hash": self.input_hash,
            "state": self.state,
            "owner": self.owner,
            "owner_pid": self.owner_pid,
            "lease_until": self.lease_until,
            "generation": self.generation,
            "output_refs": list(self.output_refs),
            "residual": list(self.residual),
            "packet_id": self.packet_id,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TaskRecord:
        return cls(
            task_id=str(_require(payload.get("task_id"), "task_id")),
            kind=str(payload["kind"]),
            input_ids=list(payload.get("input_ids") or []),
            input_hash=str(payload.get("input_hash") or ""),
            state=str(payload.get("state") or "pending"),
            owner=payload.get("owner"),
            owner_pid=payload.get("owner_pid"),
            lease_until=payload.get("lease_until"),
            generation=int(payload.get("generation") or 0),
            output_refs=list(payload.get("output_refs") or []),
            residual=list(payload.get("residual") or []),
            packet_id=payload.get("packet_id"),
            extra=dict(payload.get("extra") or {}),
        )


@dataclass
class DetailRecord:
    symbol_id: str
    behavior: str
    inputs_outputs: Any
    effects: Any
    failures: Any
    dependencies: Any
    unresolved: Any
    nav_sentence: str
    source_spans: list[dict]
    packet_id: str | None
    input_hash: str
    revision: int
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol_id": self.symbol_id,
            "behavior": self.behavior,
            "inputs_outputs": self.inputs_outputs,
            "effects": self.effects,
            "failures": self.failures,
            "dependencies": self.dependencies,
            "unresolved": self.unresolved,
            "nav_sentence": self.nav_sentence,
            "source_spans": list(self.source_spans),
            "packet_id": self.packet_id,
            "input_hash": self.input_hash,
            "revision": self.revision,
            "provenance": dict(self.provenance),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DetailRecord:
        return cls(
            symbol_id=str(payload["symbol_id"]),
            behavior=str(payload.get("behavior") or ""),
            inputs_outputs=payload.get("inputs_outputs"),
            effects=payload.get("effects"),
            failures=payload.get("failures"),
            dependencies=payload.get("dependencies"),
            unresolved=payload.get("unresolved"),
            nav_sentence=str(payload.get("nav_sentence") or ""),
            source_spans=list(payload.get("source_spans") or []),
            packet_id=payload.get("packet_id"),
            input_hash=str(payload.get("input_hash") or ""),
            revision=int(payload.get("revision") or 1),
            provenance=dict(payload.get("provenance") or {}),
        )


@dataclass
class GroupRecord:
    group_id: str
    children: list[str]
    member_ids: list[str]
    question_answered: str
    grouping_reason: str
    entry_routes: list[str]
    relations: list[dict]
    body: str
    version: int
    parent_id: str | None = None
    partial: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "children": list(self.children),
            "member_ids": list(self.member_ids),
            "question_answered": self.question_answered,
            "grouping_reason": self.grouping_reason,
            "entry_routes": list(self.entry_routes),
            "relations": list(self.relations),
            "body": self.body,
            "version": self.version,
            "parent_id": self.parent_id,
            "partial": self.partial,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> GroupRecord:
        return cls(
            group_id=str(payload["group_id"]),
            children=list(payload.get("children") or []),
            member_ids=list(payload.get("member_ids") or []),
            question_answered=str(payload.get("question_answered") or ""),
            grouping_reason=str(payload.get("grouping_reason") or ""),
            entry_routes=list(payload.get("entry_routes") or []),
            relations=list(payload.get("relations") or []),
            body=str(payload.get("body") or ""),
            version=int(payload.get("version") or 1),
            parent_id=payload.get("parent_id"),
            partial=bool(payload.get("partial", False)),
            extra=dict(payload.get("extra") or {}),
        )


@dataclass
class CallRecord:
    call_id: str
    task_id: str
    input_hash: str
    source_spans: list[dict]
    source_chars: int
    state: str
    packet_hash: str | None = None
    route: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    result_path: str | None = None
    raw_path: str | None = None
    native_path: str | None = None
    prompt_chars: int = 0
    output_chars: int = 0
    actual_model: str | None = None
    residual: list[dict] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    source_exposures: list[dict] = field(default_factory=list)
    role_session_id: str | None = None
    exposure_evidence: str | None = None
    context_replay: dict[str, Any] | None = None
    usage_reconciliation: dict[str, Any] | None = None
    delivery: str | None = None
    native_session_id: str | None = None
    parent_session_id: str | None = None
    trace_format: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "task_id": self.task_id,
            "input_hash": self.input_hash,
            "source_spans": list(self.source_spans),
            "source_chars": self.source_chars,
            "state": self.state,
            "packet_hash": self.packet_hash,
            "route": self.route,
            "usage": self.usage,
            "result_path": self.result_path,
            "raw_path": self.raw_path,
            "native_path": self.native_path,
            "prompt_chars": self.prompt_chars,
            "output_chars": self.output_chars,
            "actual_model": self.actual_model,
            "residual": list(self.residual),
            "extra": dict(self.extra),
            "source_exposures": list(self.source_exposures),
            "role_session_id": self.role_session_id,
            "exposure_evidence": self.exposure_evidence,
            "context_replay": self.context_replay,
            "usage_reconciliation": self.usage_reconciliation,
            "delivery": self.delivery,
            "native_session_id": self.native_session_id,
            "parent_session_id": self.parent_session_id,
            "trace_format": self.trace_format,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CallRecord:
        return cls(
            call_id=str(payload["call_id"]),
            task_id=str(payload.get("task_id") or ""),
            input_hash=str(payload.get("input_hash") or ""),
            source_spans=list(payload.get("source_spans") or []),
            source_chars=int(payload.get("source_chars") or 0),
            state=str(payload.get("state") or "prepared"),
            packet_hash=payload.get("packet_hash"),
            route=payload.get("route"),
            usage=payload.get("usage"),
            result_path=payload.get("result_path"),
            raw_path=payload.get("raw_path"),
            native_path=payload.get("native_path"),
            prompt_chars=int(payload.get("prompt_chars") or 0),
            output_chars=int(payload.get("output_chars") or 0),
            actual_model=payload.get("actual_model"),
            residual=list(payload.get("residual") or []),
            extra=dict(payload.get("extra") or {}),
            source_exposures=list(payload.get("source_exposures") or []),
            role_session_id=payload.get("role_session_id"),
            exposure_evidence=payload.get("exposure_evidence"),
            context_replay=payload.get("context_replay"),
            usage_reconciliation=payload.get("usage_reconciliation"),
            delivery=payload.get("delivery"),
            native_session_id=payload.get("native_session_id"),
            parent_session_id=payload.get("parent_session_id"),
            trace_format=payload.get("trace_format"),
        )


@dataclass
class ReviewRecord:
    review_id: str
    task_id: str
    target_ids: list[str]
    packet_hash: str | None
    source_chars: int
    verdict: str | None = None
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "task_id": self.task_id,
            "target_ids": list(self.target_ids),
            "packet_hash": self.packet_hash,
            "source_chars": self.source_chars,
            "verdict": self.verdict,
            "notes": self.notes,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReviewRecord:
        return cls(
            review_id=str(payload["review_id"]),
            task_id=str(payload.get("task_id") or ""),
            target_ids=list(payload.get("target_ids") or []),
            packet_hash=payload.get("packet_hash"),
            source_chars=int(payload.get("source_chars") or 0),
            verdict=payload.get("verdict"),
            notes=str(payload.get("notes") or ""),
            extra=dict(payload.get("extra") or {}),
        )


def nav_sentence(behavior: str, symbol_id: str) -> str:
    text = " ".join(behavior.strip().split())
    if not text:
        return f"{symbol_id}: (empty behavior)"
    if len(text) <= 180:
        return text
    return text[:177] + "..."


def _product_root() -> str:
    """Runtime discovery: env override first, then source-tree derivation.

    Installed deployments set CBE_PRODUCT_ROOT (or ship their own .dsh skills);
    source-tree runs derive it from this file's location.
    """
    env = os.environ.get("CBE_PRODUCT_ROOT")
    if env:
        return env
    return str(Path(__file__).resolve().parents[2])


PRODUCT_ROOT = _product_root()
CBE_SKILL_PATH = f"{PRODUCT_ROOT}/.dsh/skills/codebase-explorer/SKILL.md"
DETAIL_REFERENCE_PATH = f"{PRODUCT_ROOT}/.dsh/skills/codebase-explorer/references/detail.md"
AGGREGATION_REFERENCE_PATH = f"{PRODUCT_ROOT}/.dsh/skills/codebase-explorer/references/aggregation.md"
RECOVERY_REFERENCE_PATH = f"{PRODUCT_ROOT}/.dsh/skills/codebase-explorer/references/recovery-acceptance.md"
# Clean Context is optional outside the authoring environment. Set
# CBE_CLEAN_CONTEXT_PATH to point at the shared contract; empty means "no CC resource".
CLEAN_CONTEXT_PATH = os.environ.get("CBE_CLEAN_CONTEXT_PATH", "")

DETAIL_PRODUCTION_FIELDS: tuple[dict[str, str], ...] = (
    {
        "name": "symbol_id",
        "type": "string",
        "rule": "copy the supplied id exactly; one record per assigned symbol_id; use the given fragment or slice id, do not write another packet's canonical",
    },
    {
        "name": "behavior",
        "type": "nonempty string",
        "rule": "locally evidenced execution cause and effect",
    },
    {
        "name": "inputs_outputs",
        "type": "string[]",
        "rule": "input/output and condition; [] only when that aspect is absent",
    },
    {
        "name": "effects",
        "type": "string[]",
        "rule": "evidenced state/IO/external effect; [] only when absent",
    },
    {
        "name": "failures",
        "type": "string[]",
        "rule": "evidenced error/cancel/retry; [] only when absent",
    },
    {
        "name": "dependencies",
        "type": "string[]",
        "rule": "supplied dependency id and supported role; [] only when absent",
    },
    {
        "name": "unresolved",
        "type": "string[]",
        "rule": "specific unknown; [] only when none; do not use [] for uncertainty",
    },
)
DETAIL_PRODUCTION_FIELD_NAMES = tuple(item["name"] for item in DETAIL_PRODUCTION_FIELDS)
DETAIL_PLACEHOLDER_EXAMPLE: dict[str, Any] = {
    "details": [
        {
            "symbol_id": "<copy supplied id>",
            "behavior": "<locally evidenced behavior>",
            "inputs_outputs": ["<input/output and condition, or [] if absent>"],
            "effects": ["<evidenced effect, or [] if absent>"],
            "failures": ["<evidenced failure, or [] if absent>"],
            "dependencies": ["<supplied dependency id and supported role, or []>"],
            "unresolved": ["<specific unknown, or [] if none>"],
        }
    ]
}
GROUP_BODY_PLACEHOLDER_EXAMPLE: dict[str, str] = {
    "body": "<combined behavior with supplied child links>",
}
LEDGER_FIELDS_FILLED_BY_PROGRAM = (
    "nav_sentence",
    "source_spans",
    "packet_id",
    "input_hash",
    "revision",
    "provenance",
)


def detail_production_contract() -> dict[str, Any]:
    return {
        "fields": [dict(item) for item in DETAIL_PRODUCTION_FIELDS],
        "example": json_ready(DETAIL_PLACEHOLDER_EXAMPLE),
        "example_note": (
            "Format metadata only. Replace every placeholder with locally evidenced text "
            "or a whole empty array. Do not copy placeholders, mock answers, or source."
        ),
        "result_file": (
            "Write valid UTF-8 JSON to the unique result file this CLI attempt injects. "
            "Do not invent a second destination, and do not only put JSON in the final reply."
        ),
        "parser_accepts_any_for_arrays": True,
        "ledger_fields_filled_by_program": list(LEDGER_FIELDS_FILLED_BY_PROGRAM),
    }


def group_body_production_contract() -> dict[str, Any]:
    return {
        "schema": {"body": "nonempty string"},
        "example": dict(GROUP_BODY_PLACEHOLDER_EXAMPLE),
        "result_file": (
            "Write valid UTF-8 JSON to the unique result file this CLI attempt injects. "
            "Do not invent a second destination."
        ),
    }


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    return value
