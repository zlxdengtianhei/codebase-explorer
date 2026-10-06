"""Bounded, loss-aware evidence sent to weighted functional grouping roles.

The ledger owns the complete records. This projection drops administrative
metadata and recursive group prose, while retaining behavior-changing facts.
An unstructured group or an oversized packet is a dependency gap, not a reason
to truncate text or guess what an omitted sentence meant.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping, Sequence


PROJECTION_VERSION = "group-evidence-v1"


@dataclass(frozen=True)
class ProjectionResult:
    payload: dict[str, Any] | None
    residual: tuple[dict[str, Any], ...]
    chars: int
    tokens: int | None

    @property
    def ok(self) -> bool:
        return self.payload is not None and not self.residual


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _project_detail(ident: str, record: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    behavior = record.get("behavior")
    if not isinstance(behavior, str) or not behavior.strip():
        return None, {"code": "missing_detail_behavior", "id": ident}
    if record.get("symbol_id", ident) != ident:
        return None, {"code": "detail_identity_mismatch", "id": ident}
    return {
        "type": "detail",
        "id": ident,
        "revision": record.get("revision"),
        "behavior": behavior.strip(),
        # The six fields are reading checks, not six required prose sections.
        # Preserve unknown (None) distinctly from an evidenced absence ([]).
        "inputs_outputs": record.get("inputs_outputs"),
        "effects": record.get("effects"),
        "failures": record.get("failures"),
        "dependencies": record.get("dependencies"),
        "unresolved": record.get("unresolved"),
    }, None


def _project_group(ident: str, record: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if record.get("group_id", ident) != ident:
        return None, {"code": "group_identity_mismatch", "id": ident}
    extra = record.get("extra") or {}
    summary = extra.get("evidence_summary") if isinstance(extra, Mapping) else None
    if not isinstance(summary, Mapping):
        return None, {"code": "missing_group_evidence_summary", "id": ident}
    needed = ("behavior", "effects", "failures", "unresolved")
    missing = [field for field in needed if field not in summary]
    if missing:
        return None, {"code": "incomplete_group_evidence_summary", "id": ident, "fields": missing}
    behavior = summary["behavior"]
    if not isinstance(behavior, str) or not behavior.strip():
        return None, {"code": "empty_group_evidence_behavior", "id": ident}
    relations = record.get("relations") or []
    if not isinstance(relations, list) or any(not isinstance(item, Mapping) for item in relations):
        return None, {"code": "invalid_group_relations", "id": ident}
    members = record.get("member_ids") or []
    children = record.get("children") or []
    if not isinstance(members, list) or not isinstance(children, list):
        return None, {"code": "invalid_group_membership", "id": ident}
    routes = record.get("entry_routes") or []
    if not isinstance(routes, list):
        return None, {"code": "invalid_group_entry_routes", "id": ident}
    return {
        "type": "group",
        "id": ident,
        "version": record.get("version"),
        "question_answered": record.get("question_answered"),
        "behavior": behavior.strip(),
        "effects": summary["effects"],
        "failures": summary["failures"],
        "unresolved": summary["unresolved"],
        "entry_routes": list(routes),
        "relations": _project_edge_list(relations),
        "member_count": len(members),
        "child_count": len(children),
        "partial": bool(record.get("partial", False)),
    }, None


def _project_edge_list(edges: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Collapse identical graph facts while retaining their multiplicity.

    No unknown edge field is dropped. The graph can add a new evidence key
    without making this projection silently discard it.
    """
    counts: dict[str, int] = {}
    items: dict[str, dict[str, Any]] = {}
    for edge in edges:
        item = {key: value for key, value in edge.items() if value is not None or key == "target_id"}
        encoded = _json_text(item)
        counts[encoded] = counts.get(encoded, 0) + 1
        items[encoded] = item
    projected = []
    for encoded in sorted(items):
        item = dict(items[encoded])
        if counts[encoded] > 1:
            item["count"] = counts[encoded]
        projected.append(item)
    return {"total": len(edges), "items": projected}


def _project_edges(edges: Mapping[str, Sequence[Mapping[str, Any]]] | None) -> dict[str, Any]:
    if edges is None:
        return {}
    return {section: _project_edge_list(items) for section, items in sorted(edges.items())}


def _edge_summary(
    edges: Mapping[str, Sequence[Mapping[str, Any]]],
    documents: Sequence[Mapping[str, Any]],
    child_members: Mapping[str, Sequence[str]] | None,
) -> dict[str, Any]:
    sections: dict[str, dict[str, Any]] = {}
    per_child: dict[str, dict[str, int | None]] = {}
    member_sets: dict[str, set[str]] = {}
    owners_by_member: dict[str, set[str]] = {}
    unmapped_groups: list[str] = []
    for document in documents:
        ident = str(document["id"])
        if document["type"] == "detail":
            member_sets[ident] = {ident}
        elif child_members is not None and ident in child_members:
            member_sets[ident] = set(child_members[ident])
        else:
            unmapped_groups.append(ident)
        per_child[ident] = {}
    for ident, members in member_sets.items():
        for member in members:
            owners_by_member.setdefault(member, set()).add(ident)
    unattributed: dict[str, int] = {}
    for section, items in sorted(edges.items()):
        by_kind: dict[str, int] = {}
        by_status: dict[str, int] = {}
        unattributed[section] = 0
        for edge in items:
            kind = str(edge.get("kind") or "unknown")
            status = str(edge.get("status") or "unknown")
            by_kind[kind] = by_kind.get(kind, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1
            subject = edge.get("subject_id")
            target = edge.get("target_id")
            owners = owners_by_member.get(subject, set()) | owners_by_member.get(target, set())
            for ident in owners:
                per_child[ident][section] = int(per_child[ident].get(section) or 0) + 1
            if not owners:
                unattributed[section] += 1
        for ident in per_child:
            if ident not in member_sets:
                per_child[ident][section] = None
            else:
                per_child[ident].setdefault(section, 0)
        sections[section] = {
            "total": len(items),
            "by_kind": dict(sorted(by_kind.items())),
            "by_status": dict(sorted(by_status.items())),
        }
    return {
        "mode": "summary",
        "sections": sections,
        "per_child": per_child,
        "unattributed": unattributed,
        "unmapped_group_ids": unmapped_groups,
        "omitted_exact_edges": sum(len(items) for items in edges.values()),
    }


def _measure(payload: dict[str, Any], count_tokens: Callable[[str], int] | None) -> tuple[int, int | None]:
    encoded = _json_text(payload)
    chars = len(encoded)
    tokens = count_tokens(encoded) if count_tokens is not None else None
    if tokens is not None and (not isinstance(tokens, int) or tokens < 0):
        raise ValueError("count_tokens must return a nonnegative integer")
    return chars, tokens


def _fits(chars: int, tokens: int | None, max_chars: int, max_tokens: int | None) -> bool:
    return chars <= max_chars and (max_tokens is None or (tokens is not None and tokens <= max_tokens))


def project_group_evidence(
    documents: Sequence[Mapping[str, Any]],
    *,
    edges: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    child_members: Mapping[str, Sequence[str]] | None = None,
    max_chars: int,
    max_tokens: int | None = None,
    count_tokens: Callable[[str], int] | None = None,
) -> ProjectionResult:
    """Project canonical direct children with explicit preflight budget gaps.

    ``documents`` accepts the runner's ``{type, id, record}`` envelopes.
    The caller must bound the *whole* prompt after embedding this payload; this
    cap protects the evidence portion, including supplied graph edges.
    ``child_members`` maps direct group children to their leaf symbol IDs for
    exact per-child edge incidence when a full graph cannot fit. Without it,
    group incidence is explicitly unknown. ``count_tokens`` is the exact
    tokenizer hook for the run's frozen encoding.
    """
    if not isinstance(max_chars, int) or max_chars <= 0:
        raise ValueError("max_chars must be a positive integer")
    if max_tokens is not None and (not isinstance(max_tokens, int) or max_tokens <= 0):
        raise ValueError("max_tokens must be a positive integer")
    if max_tokens is not None and count_tokens is None:
        raise ValueError("count_tokens is required when max_tokens is set")
    children: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    child_ids: list[str] = []
    for document in documents:
        ident = document.get("id")
        kind = document.get("type")
        record = document.get("record")
        if not isinstance(ident, str) or not ident or not isinstance(record, Mapping):
            gaps.append({"code": "invalid_group_document", "id": ident})
            continue
        child_ids.append(ident)
        if kind == "detail":
            child, gap = _project_detail(ident, record)
        elif kind == "group":
            child, gap = _project_group(ident, record)
        else:
            child, gap = None, {"code": "unknown_group_document_type", "id": ident, "type": kind}
        if gap is not None:
            gaps.append(gap)
        elif child is not None:
            children.append(child)
    if gaps:
        return ProjectionResult(payload=None, residual=tuple(gaps), chars=0, tokens=None)
    if edges is not None and not isinstance(edges, Mapping):
        return ProjectionResult(
            payload=None,
            residual=({"code": "invalid_group_edges"},),
            chars=0,
            tokens=None,
        )
    if edges is not None:
        for section, items in edges.items():
            if not isinstance(section, str) or not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
                return ProjectionResult(
                    payload=None,
                    residual=({"code": "invalid_group_edges", "section": section},),
                    chars=0,
                    tokens=None,
                )
            for index, edge in enumerate(items):
                if not isinstance(edge, Mapping) or any(
                    key in edge and edge[key] is not None and not isinstance(edge[key], str)
                    for key in ("subject_id", "target_id")
                ):
                    return ProjectionResult(
                        payload=None,
                        residual=({"code": "invalid_group_edge", "section": section, "index": index},),
                        chars=0,
                        tokens=None,
                    )
    if child_members is not None and (
        not isinstance(child_members, Mapping)
        or any(
            not isinstance(key, str)
            or not isinstance(value, Sequence)
            or isinstance(value, (str, bytes))
            or any(not isinstance(item, str) for item in value)
            for key, value in child_members.items()
        )
    ):
        return ProjectionResult(payload=None, residual=({"code": "invalid_child_members"},), chars=0, tokens=None)
    edge_counts = {section: len(items) for section, items in sorted((edges or {}).items())}

    def over_budget(chars: int, tokens: int | None, cause: str) -> ProjectionResult:
        return ProjectionResult(
            payload=None,
            residual=({
                "code": "group_projection_over_budget",
                "projection_version": PROJECTION_VERSION,
                "cause": cause,
                "required_chars": chars,
                "max_chars": max_chars,
                "required_tokens": tokens,
                "max_tokens": max_tokens,
                "child_ids": child_ids,
                "edge_counts": edge_counts,
            },),
            chars=chars,
            tokens=tokens,
        )

    base = {"projection_version": PROJECTION_VERSION, "children": children, "edges": {}}
    base_chars, base_tokens = _measure(base, count_tokens)
    if not _fits(base_chars, base_tokens, max_chars, max_tokens):
        return over_budget(base_chars, base_tokens, "child_evidence")

    full = {**base, "edges": _project_edges(edges)}
    full_chars, full_tokens = _measure(full, count_tokens)
    if _fits(full_chars, full_tokens, max_chars, max_tokens):
        return ProjectionResult(payload=full, residual=(), chars=full_chars, tokens=full_tokens)

    assert edges is not None  # Only graph edges can increase the base packet.
    summary = {**base, "edges": _edge_summary(edges, documents, child_members)}
    pages = {
        section: {"offset": 0, "limit": 100, "total": len(items)}
        for section, items in sorted(edges.items())
    }
    residual = {
        "code": "group_edges_summarized",
        "projection_version": PROJECTION_VERSION,
        "omitted_edge_count": sum(edge_counts.values()),
        "edge_counts": edge_counts,
        "unmapped_group_ids": summary["edges"]["unmapped_group_ids"],
        "exact_evidence_request": {
            "kind": "group_edges",
            "input_ids": child_ids,
            "pages": pages,
        },
    }
    # The caller sends both objects; bound their combined canonical JSON size.
    summary_chars, summary_tokens = _measure({"payload": summary, "residual": [residual]}, count_tokens)
    if not _fits(summary_chars, summary_tokens, max_chars, max_tokens):
        return over_budget(summary_chars, summary_tokens, "edge_summary_with_residual")
    return ProjectionResult(payload=summary, residual=(residual,), chars=summary_chars, tokens=summary_tokens)


def leaf_member_ids(ledger: Mapping[str, Any], ident: str) -> set[str]:
    """Resolve a direct Detail or Group to its canonical leaf Detail IDs.

    Missing membership or a cycle is an error for exact evidence retrieval:
    returning a partial set would make a graph page appear complete.
    """
    details = ledger.get("details") or {}
    groups = ledger.get("groups") or {}
    memo: dict[str, set[str]] = {}
    active: set[str] = set()

    def visit(current: str) -> set[str]:
        if current in memo:
            return memo[current]
        if current in active:
            raise ValueError(f"group membership cycle at {current}")
        if current in details:
            memo[current] = {current}
            return memo[current]
        group = groups.get(current)
        if not isinstance(group, Mapping):
            raise ValueError(f"unknown group member or input id: {current}")
        active.add(current)
        leaves: set[str] = set()
        for child in list(group.get("member_ids") or []) + list(group.get("children") or []):
            if not isinstance(child, str):
                raise ValueError(f"invalid group member in {current}")
            leaves.update(visit(child))
        active.remove(current)
        memo[current] = leaves
        return leaves

    return visit(ident)


def page_group_edges(
    ledger: Mapping[str, Any],
    *,
    input_ids: Sequence[str],
    section: Literal["internal", "boundary", "unknown"],
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """Return one stable page of exact frozen graph edges for a selection.

    The same filtering semantics apply to the concise group packet and this
    follow-up read. Counts and ``next_offset`` make incomplete pages explicit.
    """
    if section not in {"internal", "boundary", "unknown"}:
        raise ValueError("section must be internal, boundary, or unknown")
    if not isinstance(input_ids, Sequence) or isinstance(input_ids, (str, bytes)) or not input_ids:
        raise ValueError("input_ids must be a nonempty sequence of IDs")
    if any(not isinstance(ident, str) or not ident for ident in input_ids):
        raise ValueError("input_ids must contain nonempty strings")
    if not isinstance(offset, int) or offset < 0:
        raise ValueError("offset must be a nonnegative integer")
    if not isinstance(limit, int) or limit <= 0 or limit > 1_000:
        raise ValueError("limit must be between 1 and 1000")
    leaves: set[str] = set()
    for ident in input_ids:
        leaves.update(leaf_member_ids(ledger, ident))
    graph = ledger.get("graph") or {}
    source = graph.get("unknown_edges") if section == "unknown" else graph.get("edges")
    source = source or []
    if not isinstance(source, list) or any(not isinstance(item, Mapping) for item in source):
        raise ValueError("graph edge section must be a list of edge objects")
    selected: list[dict[str, Any]] = []
    for edge in source:
        subject_inside = edge.get("subject_id") in leaves
        target_inside = edge.get("target_id") in leaves
        matches = (
            (subject_inside and target_inside) if section == "internal"
            else (subject_inside != target_inside) if section == "boundary"
            else (subject_inside or target_inside)
        )
        if matches:
            selected.append(dict(edge))
    selected.sort(key=_json_text)
    total = len(selected)
    items = selected[offset:offset + limit]
    next_offset = offset + len(items) if offset + len(items) < total else None
    return {
        "projection_version": PROJECTION_VERSION,
        "source_revision": ledger.get("source_revision"),
        "section": section,
        "input_ids": list(input_ids),
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
        "next_offset": next_offset,
    }
