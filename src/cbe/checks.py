"""Strict checks and shape repair for every task result.

Detail answers are decoded, not validated: see ``decode_details``. Other tasks
allow 2 answers; on the final invalid answer, the normalizer makes usable content
compliant and returns flags describing every change, or fails when the answer
cannot be accepted. Retained obligations: the model never emits line numbers (the
program derives published ranges from the inventory); every inventory id gets
exactly one disposition (unit / grouped / index_only), written by the program, so
nothing is silently dropped; length and count are never repair triggers; the
ownership tree is single-rooted and acyclic for containment while dependency
cycles stay allowed; each unit has exactly one primary owner.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


def json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped).strip()
    value = json.loads(stripped)
    if not isinstance(value, dict):
        raise ValueError("completion must be one JSON object")
    return value


UNIT_KINDS = {"class", "function", "method", "group", "module_region"}
RELATION_KINDS = {"call", "inherit", "override", "import", "raise", "use",
                  "contract", "group"}
EXTRA_TOPICS = {"condition", "failure", "side_effect", "field", "contract"}


def system_limit() -> int:
    """The overview is 2 to 4 sentences; the entry page has a token budget."""
    return 1200


DEPENDENCY_EVIDENCE_WORDS = re.compile(
    r"\b(?:graph[-_ ]?(?:confirmed|only)|model[-_ ]?inferred)\b"
    r"|\bresolved\s+(?:calls?|edges?|imports?)\b"
    r"|\b\d+\s+(?:(?:static|resolved|call|import)\s+)*(?:calls?|edges?)\b"
    r"|\b(?:within[-_ ]containment|containment)\b"
    r"|图确认|模型推断|图有未描述|包含关系|包含内|\d+\s*条(?:调用|边)", re.IGNORECASE)


def check_system(value: dict[str, Any], limit: int = 2000, *, unit_ids=None, dependencies=None,
                 has_candidates: bool = False, normalized: bool = False) -> None:
    errors = []
    if not isinstance(value.get("overview"), str) or not value["overview"].strip() or len(value["overview"]) > limit:
        errors.append(f"overview must be a nonempty concise string of at most {limit} characters")
    descriptions = value.get("dependency_descriptions")
    flows = value.get("key_flows")
    if not isinstance(descriptions, list):
        errors.append("dependency_descriptions must be a list")
        descriptions = []
    if not isinstance(flows, list):
        errors.append("key_flows must be a list")
        flows = []
    pairs = None if dependencies is None else {(e["from"], e["to"]) for e in dependencies}
    for row in descriptions:
        if (not isinstance(row, dict) or not isinstance(row.get("from"), str)
                or not isinstance(row.get("to"), str) or not isinstance(row.get("description"), str)
                or not row["description"].strip() or len(row["description"]) > 300
                or (pairs is not None and (row["from"], row["to"]) not in pairs)):
            errors.append("dependency description must name an existing pair and one sentence (<=300 characters)")
            continue
        if DEPENDENCY_EVIDENCE_WORDS.search(row["description"]):
            errors.append(f"dependency {row['from']} -> {row['to']}: describe who uses whom for what; "
                          "omit evidence/source words and edge counts (the program supplies them)")
    if pairs and not descriptions and not normalized:
        errors.append("describe at least one existing dependency")
    if (has_candidates and not (normalized and len(flows) <= 7) and not 3 <= len(flows) <= 7) or (not has_candidates and flows):
        errors.append("key_flows must contain 3-7 flows when candidates exist, otherwise []")
    flow_errors = []
    flow_ids = []
    for index, row in enumerate(flows):
        if (not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip()
                                           or len(row[k]) > 300 for k in ("name", "description"))
                or not isinstance(row.get("steps"), list) or not 2 <= len(row["steps"]) <= 8
                or any(not isinstance(uid, str) or (unit_ids is not None and uid not in unit_ids)
                       for uid in row["steps"])):
            bad_ids = ([uid for uid in row.get("steps", [])
                        if not isinstance(uid, str) or (unit_ids is not None and uid not in unit_ids)]
                       if isinstance(row, dict) and isinstance(row.get("steps"), list) else [])
            name = row.get("name", "") if isinstance(row, dict) else ""
            flow_errors.append(f"key flow {index + 1} {name!r}: invalid unit ids {bad_ids!r}")
            flow_ids.append(f"key flow {index + 1}: invalid unit ids {bad_ids!r}")
    if flow_errors:
        hint = ("each flow needs name, one sentence, and 2-8 existing unit ids; "
                "steps are unit ids from candidates, not node ids")
        # The host returns only the first 2,000 characters to the model. Put all
        # offending ids first; drop names before losing a later flow's ids.
        if len("; ".join(flow_errors + [hint] + errors)) > 2000:
            flow_errors = flow_ids
        errors = flow_errors + [hint] + errors
    if errors:
        raise ValueError("; ".join(errors))


def check_review(value: dict[str, Any]) -> None:
    if value.get("decision") not in {"accepted", "needs_repair"}:
        raise ValueError("review decision must be accepted or needs_repair")
    if not isinstance(value.get("issues"), list) or any(not isinstance(x, str) for x in value["issues"]):
        raise ValueError("issues must be a list of strings")


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:max(1, limit - 1)]
    floor = int(limit * 0.7)
    boundary = max((cut.rfind(mark) + len(mark) for mark in (". ", "。", "\n", "; ")
                    if cut.rfind(mark) >= floor), default=-1)
    if boundary < 0:
        boundary = cut.rfind(" ") if cut.rfind(" ") >= floor else len(cut)
    return cut[:boundary].rstrip() + "…"


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def _fit(value: dict[str, Any], key: str, limit: int, flags: list[str], *, label: str | None = None) -> None:
    label = label or key
    text = value.get(key)
    if not isinstance(text, str):
        if text is not None:
            flags.append(f"{label} was {type(text).__name__}; converted to text")
        text = _as_text(text)
    if len(text) > limit:
        flags.append(f"{label} truncated from {len(text)} to {limit} characters")
        text = truncate(text, limit)
    value[key] = text


def normalize_system(value: Any, limit: int, *, unit_ids=None, dependencies=None,
                     has_candidates: bool = False) -> list[str]:
    if not isinstance(value, dict):
        raise ValueError("overview result is not a JSON object")
    flags: list[str] = []
    _fit(value, "overview", limit, flags)
    if not value["overview"].strip():
        raise ValueError("overview result has no overview")
    # Preserve each independently valid row after the final rejected answer.
    for key in ("dependency_descriptions", "key_flows"):
        rows = value.get(key)
        if not isinstance(rows, list):
            value[key] = []
            flags.append(f"{key} normalized to empty: must be a list")
            continue
        retained = []
        for index, row in enumerate(rows):
            probe = {**value, "dependency_descriptions": [], "key_flows": []}
            probe[key] = [row]
            try:
                check_system(probe, limit, unit_ids=unit_ids, dependencies=dependencies,
                             has_candidates=has_candidates, normalized=True)
            except ValueError as exc:
                if key == "key_flows":
                    reason = str(exc).replace("key flow 1 ", f"key flow {index + 1} ")
                    flags.append(f"key_flows[{index + 1}] removed: {reason}")
                else:
                    flags.append(f"{key}[{index + 1}] removed: {exc}")
            else:
                retained.append(row)
        if key == "key_flows" and len(retained) > 7:
            flags.append(f"key_flows trimmed from {len(retained)} to 7")
            retained = retained[:7]
        value[key] = retained
        if key == "key_flows" and has_candidates and len(retained) < 3:
            flags.append(f"key_flows retained {len(retained)} valid flows (fewer than 3) after final invalid answer")
        elif not retained and dependencies and key == "dependency_descriptions":
            flags.append("dependency_descriptions empty after final invalid answer")
    check_system(value, limit, unit_ids=unit_ids, dependencies=dependencies,
                 has_candidates=has_candidates, normalized=True)
    return flags


def normalize_review(value: Any) -> list[str]:
    if not isinstance(value, dict):
        raise ValueError("review result is not a JSON object")
    flags: list[str] = []
    issues = value.get("issues")
    if not isinstance(issues, list):
        issues = [] if issues in (None, "") else [_as_text(issues)]
        flags.append("issues was not a list")
    value["issues"] = [_as_text(item) for item in issues]
    if value.get("decision") not in {"accepted", "needs_repair"}:
        value["decision"] = "needs_repair" if value["issues"] else "accepted"
        flags.append(f"decision was invalid; treated as {value['decision']}")
    check_review(value)
    return flags


def _normalize_choice(value: Any, allowed: "set[str] | frozenset[str]",
                      default: str) -> tuple[str, bool]:
    """Conservative enum repair: keep a valid value, unwrap a one-element list
    the model sometimes emits (``["use"]``), otherwise fall back to a safe
    default. Returns (value, changed)."""
    if isinstance(value, str) and value in allowed:
        return value, False
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str) \
            and value[0] in allowed:
        return value[0], True
    return default, True


# ---------------------------------------------------------------- detail answers
#
# A detail answer names symbols by the short numbers of its batch table
# (``symbols.batch_table``) and never writes an inventory id. ``decode_details``
# turns it into the internal shape every later stage reads: ``units`` with
# ``id``/``kind``/``members`` and a complete ``dispositions`` map. It accepts
# what it can, unit by unit; only a non-object answer or a missing ``units``
# list voids the whole answer.

#: A function, method or class whose own source has at least this many tokens and
#: that no unit mentions is a gap to re-ask, not an automatic index_only entry.
GAP_MIN_TOKENS = 40
GAP_KINDS = {"function", "method", "class"}
NOT_EXPLAINED = "not explained; indexed without prose"


@dataclass
class Decoded:
    """What one answer added: accepted units, notes on repairs, units rejected."""
    units: list[dict[str, Any]] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    invalid: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""


def _number(value: Any) -> int | None:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def covered_ids(units: list[dict[str, Any]], table: list[dict]) -> set[str]:
    """Inventory ids that some unit explains (its own id or a member)."""
    scope = {row["id"] for row in table}
    return {sid for unit in units for sid in [unit["id"], *(unit.get("members") or [])] if sid in scope}


def _kebab(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _group_id(title: Any, first: dict, taken: set[str]) -> str:
    base = _kebab(title) if isinstance(title, str) else ""
    base = base or _kebab(first["name"]) or "group"
    stem = f"grp:{first['path'].rsplit('/', 1)[-1]}-{base}"
    uid, count = stem, 1
    while uid in taken:
        count += 1
        uid = f"{stem}-{count}"
    return uid


def _decode_unit(raw: dict[str, Any], rows: list[dict], by_number: dict[int, dict], taken: set[str]) -> dict[str, Any]:
    """The internal unit for one answer unit whose ``h`` and ``explain`` are valid."""
    first = rows[0]
    if len(rows) == 1:
        unit: dict[str, Any] = {"id": first["id"], "kind": first["kind"]}
    else:
        unit = {"id": _group_id(raw.get("title"), first, taken), "kind": "group",
                "members": [row["id"] for row in rows]}
    unit["explain"] = raw["explain"].strip()
    unit["extras"] = [{"topic": _normalize_choice(extra.get("topic"), EXTRA_TOPICS, "contract")[0],
                       "note": extra["note"].strip()}
                      for extra in raw.get("extras") or []
                      if isinstance(extra, dict) and isinstance(extra.get("note"), str) and extra["note"].strip()]
    relations = []
    for rel in raw.get("relations") or []:
        if not isinstance(rel, dict):
            continue
        number = _number(rel.get("to"))
        target = by_number[number]["id"] if number in by_number else (
            rel["to"].strip() if number is None and isinstance(rel.get("to"), str) and rel["to"].strip() else None)
        if target is None:
            continue
        relation = {"target": target, "kind": _normalize_choice(rel.get("kind", "use"), RELATION_KINDS, "use")[0]}
        if isinstance(rel.get("basis"), str):
            relation["basis"] = rel["basis"]
        relations.append(relation)
    unit["relations"] = relations
    unit["uncertainties"] = [item for item in raw.get("uncertainties") or [] if isinstance(item, str)]
    return unit


def decode_details(payload: Any, table: list[dict], *, have: list[dict[str, Any]] | None = None,
                   known_ids: set[str] | frozenset[str] = frozenset()) -> Decoded:
    """Decode one detail answer against its batch table.

    ``have`` holds units accepted from earlier answers of the same task; their
    symbols and ids stay taken. A unit with an unknown short number loses that
    number; a number already in an earlier unit stays with the first (a unit whose
    symbols are all taken is ignored); a unit left without any valid number or
    without an explanation is returned in ``invalid`` and the other units are kept. Raises ``ValueError`` only when the whole answer is unusable."""
    if not isinstance(payload, dict):
        raise ValueError("answer is not a JSON object")
    rows = payload.get("units")
    if not isinstance(rows, list):
        raise ValueError("answer has no units list")
    have = have or []
    by_number = {row["n"]: row for row in table}
    by_id = {row["id"]: row for row in table}
    taken_symbols = covered_ids(have, table)
    taken_ids = {unit["id"] for unit in have} | set(known_ids)
    out = Decoded()
    for index, raw in enumerate(rows):
        label = f"unit {index + 1}"
        if not isinstance(raw, dict):
            out.invalid.append({"h": [], "why": f"{label} is not an object"})
            continue
        listed = raw.get("h")
        numbers: list[int] = []
        for item in listed if isinstance(listed, list) else []:
            number = _number(item)
            if number not in by_number:
                out.flags.append(f"{label}: unknown symbol number {item!r} removed")
            elif number not in numbers:
                numbers.append(number)
        symbols = []
        for number in numbers:
            row = by_number[number]
            if row["id"] in taken_symbols:
                out.flags.append(f"{label}: symbol {number} is already in an earlier unit; kept there")
            else:
                symbols.append(row)
        shown = [row["n"] for row in symbols]
        if not numbers:
            out.invalid.append({"h": [], "why": f"{label} lists no symbol number of this batch"})
            continue
        if not symbols:  # a repeat of explained symbols loses nothing; it is not worth a re-ask
            out.flags.append(f"{label}: every symbol is already in an earlier unit; ignored")
            continue
        if not isinstance(raw.get("explain"), str) or not raw["explain"].strip():
            out.invalid.append({"h": shown, "why": f"{label} has an empty explain"})
            continue
        unit = _decode_unit(raw, symbols, by_number, taken_ids)
        taken_symbols |= {row["id"] for row in symbols}
        taken_ids.add(unit["id"])
        out.units.append(unit)
    if isinstance(payload.get("notes"), str):
        out.notes = payload["notes"].strip()
    return out


def find_gaps(table: list[dict], units: list[dict[str, Any]], tokens: dict[str, int]) -> list[dict]:
    """Symbols with logic that no unit mentions: functions, methods and classes
    outside test files whose own source is at least ``GAP_MIN_TOKENS`` tokens.
    Everything else that no unit mentions is simply indexed without prose."""
    done = covered_ids(units, table)
    return [row for row in table
            if row["id"] not in done and row["kind"] in GAP_KINDS
            and tokens.get(row["id"], 0) >= GAP_MIN_TOKENS]


def assemble_details(table: list[dict], units: list[dict[str, Any]], *, notes: str = "") -> dict[str, Any]:
    """The internal payload: units plus a complete ``dispositions`` map.

    A symbol inside a unit is ``unit`` (the unit is the symbol) or ``grouped``;
    every other symbol is ``index_only``."""
    dispositions: dict[str, dict[str, Any]] = {}
    for unit in units:
        if unit["kind"] == "group":
            dispositions.update({sid: {"how": "grouped", "unit": unit["id"]} for sid in unit["members"]})
        else:
            dispositions[unit["id"]] = {"how": "unit", "unit": unit["id"]}
    for row in table:
        dispositions.setdefault(row["id"], {"how": "index_only", "unit": None, "reason": NOT_EXPLAINED})
    payload: dict[str, Any] = {"units": units, "dispositions": dispositions}
    if notes:
        payload["batch_notes"] = notes
    return payload


_NODE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def validate_tree(payload: Any, unit_universe: set[str]) -> list[str]:
    """Hard problems only: one root, an acyclic contains graph, every node
    reachable, every unit assigned to exactly one primary owner, and a real
    capability text on any node with children. Dependency cycles stay allowed."""
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["tree result is not a JSON object"]
    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return ["nodes must be a nonempty list"]
    by_id: dict[str, dict] = {}
    roots: list[str] = []
    for node in nodes:
        if not isinstance(node, dict):
            problems.append("node is not an object")
            continue
        nid = node.get("id")
        if not isinstance(nid, str) or not _NODE_ID.match(nid):
            problems.append(f"bad node id {nid!r}")
            continue
        if nid in by_id:
            problems.append(f"duplicate node id {nid}")
        by_id[nid] = node
        if node.get("parent") is None:
            roots.append(nid)
    if len(roots) != 1:
        problems.append(f"exactly one root required, found {roots}")
    for nid, node in by_id.items():
        parent = node.get("parent")
        if parent is not None and (not isinstance(parent, str) or parent not in by_id):
            problems.append(f"node {nid}: parent {parent!r} does not exist")
        for field in ("title", "capability", "summary"):
            if not isinstance(node.get(field), str) or not node[field].strip():
                problems.append(f"node {nid}: {field} must be a nonempty string")
        unit_ids = node.get("unit_ids")
        if not isinstance(unit_ids, list) or any(not isinstance(item, str) for item in unit_ids):
            problems.append(f"node {nid}: unit_ids must be a list of strings")
    children: dict[str, list[str]] = {nid: [] for nid in by_id}
    for nid, node in by_id.items():
        parent = node.get("parent")
        if isinstance(parent, str) and parent in by_id:
            children[parent].append(nid)
    root = roots[0] if len(roots) == 1 else None
    if root is not None:
        seen: set[str] = set()
        stack = [root]
        while stack:
            nid = stack.pop()
            if nid in seen:
                problems.append(f"node {nid} reachable twice: contains graph has a cycle")
                continue
            seen.add(nid)
            stack.extend(children.get(nid, []))
        unreachable = sorted(set(by_id) - seen)
        if unreachable:
            problems.append(f"nodes unreachable from root: {unreachable[:12]}")
    owner: dict[str, str] = {}
    for nid, node in by_id.items():
        for uid in node.get("unit_ids") or []:
            if not isinstance(uid, str):
                continue  # already reported as a bad unit_ids list above
            if uid not in unit_universe:
                problems.append(f"node {nid}: unknown unit id {uid}")
            elif uid in owner:
                problems.append(f"unit {uid} assigned to both {owner[uid]} and {nid}")
            else:
                owner[uid] = nid
    unassigned = sorted(unit_universe - set(owner))
    if unassigned:
        problems.append(f"units with no primary owner: {unassigned[:12]}")
    for nid, node in by_id.items():
        capability = node.get("capability")
        if children.get(nid) and isinstance(capability, str) and len(capability) < 40:
            problems.append(f"node {nid} has children but capability text is not a real "
                            "explanation (<40 chars)")
    if unit_universe:
        empty = sorted(nid for nid, node in by_id.items() if not node.get("unit_ids") and not children.get(nid))
        if empty:
            problems.append(f"nodes with no units and no children: {empty[:12]}")
        for nid, kids in children.items():
            titles: dict[str, str] = {}
            for kid in kids:
                title = by_id[kid].get("title")
                key = re.sub(r"\W+", " ", title.lower()).strip() if isinstance(title, str) else None
                if key and key in titles:
                    problems.append(f"nodes {titles[key]} and {kid} are siblings with the same title {title!r}")
                elif key:
                    titles[key] = kid
    members: dict[str, set[str]] = {}

    def subtree(nid: str) -> set[str]:
        if nid not in members:
            members[nid] = {u for u in by_id[nid].get("unit_ids") or [] if isinstance(u, str)}
            for kid in children.get(nid, []):
                members[nid] |= subtree(kid)
        return members[nid]

    if root is not None and not any(p.startswith("node ") and "reachable twice" in p for p in problems):
        for nid, node in by_id.items():
            evidence = node.get("evidence_units")
            if evidence is not None and (not isinstance(evidence, list)
                                         or any(not isinstance(u, str) or u not in subtree(nid) for u in evidence)):
                problems.append(f"node {nid}: evidence_units must be members of the node's subtree")
    edges = payload.get("depends_on")
    if not isinstance(edges, list):
        problems.append("depends_on must be a list")
    else:
        for edge in edges:
            if not isinstance(edge, dict) or edge.get("from") not in by_id \
                    or edge.get("to") not in by_id:
                problems.append(f"depends_on edge with unknown endpoint: {edge!r}"[:200])
                continue
            if not isinstance(edge.get("basis"), str) or not edge["basis"].strip():
                problems.append(f"depends_on {edge.get('from')}->{edge.get('to')}: "
                                "basis (evidence) is required")
    return problems
