"""Strict checks and shape repair for every task result.

A strict miss is re-asked once with the exact error. If the second answer still
misses, the normalizer makes a usable answer compliant and returns flags that
describe every change; it raises only when nothing usable is left. Retained
obligations: the model never emits line numbers (the program derives published
ranges from the inventory); every inventory id gets exactly one disposition
(unit / grouped / index_only), so nothing is silently dropped; length and count
are never repair triggers; the ownership tree is single-rooted and acyclic for
containment while dependency cycles stay allowed; each unit has exactly one
primary owner.
"""

from __future__ import annotations

import json
import re
from typing import Any

from cbe.batching import Module, fallback_title


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
DISPOSITION_HOW = {"unit", "grouped", "index_only"}
RELATION_KINDS = {"call", "inherit", "override", "import", "raise", "use",
                  "contract", "group"}
EXTRA_TOPICS = {"condition", "failure", "side_effect", "field", "contract"}


def check_naming(value: dict[str, Any], modules: list[Module]) -> None:
    rows = value.get("names")
    if not isinstance(rows, list) or len(rows) != len(modules):
        raise ValueError("names must contain one entry per module")
    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, dict) or type(row.get("module")) is not int or not isinstance(row.get("title"), str):
            raise ValueError("each name needs integer module and string title")
        if row["module"] in seen or not row["title"].strip():
            raise ValueError("duplicate or empty module title")
        title = row["title"].strip()
        if len(title) > 80:
            title = title[:80].rsplit(" ", 1)[0] or title[:80]
        row["title"] = title
        seen.add(row["module"])
    if seen != {module.number for module in modules}:
        raise ValueError("module title IDs do not match planned modules")


def system_limit(node_count: int) -> int:
    """Overview and navigation name semantic nodes, independent of reading batches."""
    return max(2000, min(12000, 250 * node_count))


def check_system(value: dict[str, Any], limit: int = 2000) -> None:
    for key in ("overview", "maintenance_navigation"):
        if not isinstance(value.get(key), str) or not value[key].strip() or len(value[key]) > limit:
            raise ValueError(f"{key} must be a nonempty concise string of at most {limit} characters")


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


def normalize_naming(value: Any, modules: list[Module]) -> list[str]:
    if not isinstance(value, dict):
        raise ValueError("naming result is not a JSON object")
    rows = value.get("names") if isinstance(value.get("names"), list) else []
    titles: dict[int, str] = {}
    for row in rows:
        if (isinstance(row, dict) and type(row.get("module")) is int and isinstance(row.get("title"), str)
                and row["title"].strip() and row["module"] not in titles
                and 0 <= row["module"] < len(modules)):
            titles[row["module"]] = row["title"]
    if not titles:
        raise ValueError("naming result has no usable titles")
    flags = []
    for module in modules:
        if module.number not in titles:
            titles[module.number] = fallback_title(module)
            flags.append(f"module {module.number + 1} had no title; used {titles[module.number]!r}")
    value["names"] = [{"module": number, "title": titles[number]} for number in sorted(titles)]
    check_naming(value, modules)
    return flags


def normalize_system(value: Any, limit: int) -> list[str]:
    if not isinstance(value, dict):
        raise ValueError("overview result is not a JSON object")
    flags: list[str] = []
    for key in ("overview", "maintenance_navigation"):
        _fit(value, key, limit, flags)
    if not value["overview"].strip():
        raise ValueError("overview result has no overview")
    if not value["maintenance_navigation"].strip():
        value["maintenance_navigation"] = "See the subsystem list below."
        flags.append("maintenance_navigation was empty")
    check_system(value, limit)
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


def _detail_identity(uid: str) -> tuple[str, ...]:
    """Ignore only the generated final offset, retaining path/kind/qualified name."""
    stem = re.sub(r"::\d+[\w-]*(?:::s\d+)*$", "", uid)
    return tuple(stem.split("::", 2))


def _detail_id_problem(uid: str, scope_ids: set[str]) -> str:
    parts = _detail_identity(uid)
    name = parts[2] if len(parts) >= 3 else uid
    candidates = sorted(candidate for candidate in scope_ids
                        if len(_detail_identity(candidate)) >= 3
                        and _detail_identity(candidate)[2] == name)
    if not candidates and scope_ids:
        def prefix_length(candidate: str) -> int:
            other = _detail_identity(candidate)
            other_name = other[2] if len(other) >= 3 else candidate
            return next((i for i, (a, b) in enumerate(zip(name, other_name)) if a != b),
                        min(len(name), len(other_name)))
        longest = max(map(prefix_length, scope_ids))
        candidates = sorted(candidate for candidate in scope_ids
                            if prefix_length(candidate) == longest)
    return (f"unit id {uid} is not in this batch's inventory; candidates: {candidates[:12]}. "
            "Unit ids must come only from this batch's inventory; use grp: for self-created groups.")


def validate_details(payload: Any, paths: list[str], inventory: dict[str, dict],
                     known_unit_ids: set[str]) -> list[str]:
    """Hard problems only (empty list = acceptable).

    Hard means structure, symbol identity, references, coverage, and nonempty
    required content. Length and count are never checked here and never trigger
    a model repair. The function never mutates its input."""
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["result is not a JSON object"]
    units = payload.get("units")
    if not isinstance(units, list):
        return ["units must be a list"]
    scope_ids = {row["id"] for path in paths for row in inventory[path]["symbols"]}
    if not units and scope_ids:
        # An empty batch (every file known-empty, no inventory id) may validly
        # return no units; a batch with ids must explain them.
        return ["units must be a nonempty list"]
    seen: set[str] = set()
    for unit in units:
        if not isinstance(unit, dict):
            problems.append("unit is not an object")
            continue
        uid = unit.get("id")
        if not isinstance(uid, str) or not uid.strip():
            problems.append("unit without id")
            continue
        if uid in seen or uid in known_unit_ids:
            problems.append(f"duplicate unit id {uid}")
        seen.add(uid)
        if not uid.startswith("grp:") and uid not in scope_ids:
            problems.append(_detail_id_problem(uid, scope_ids))
        kind = unit.get("kind")
        if not isinstance(kind, str) or kind not in UNIT_KINDS:
            problems.append(f"{uid}: kind must be one of {sorted(UNIT_KINDS)}; got {kind!r}")
        explain = unit.get("explain")
        if not isinstance(explain, str) or not explain.strip():
            problems.append(f"{uid}: explain must be a nonempty paragraph")
        summary = unit.get("summary")
        if summary is not None and not isinstance(summary, str):
            problems.append(f"{uid}: summary must be a string when supplied")
        extras = unit.get("extras", [])
        if not isinstance(extras, list):
            problems.append(f"{uid}: extras must be a list")
        else:
            for extra in extras:
                topic = extra.get("topic") if isinstance(extra, dict) else None
                if not isinstance(topic, str) or topic not in EXTRA_TOPICS:
                    problems.append(f"{uid}: extra topic must be one of {sorted(EXTRA_TOPICS)}; "
                                    f"got {topic!r}")
                    continue
                note = extra.get("note")
                if not isinstance(note, str) or not note.strip():
                    problems.append(f"{uid}: extra note must be a nonempty string")
        relations = unit.get("relations", [])
        if not isinstance(relations, list):
            problems.append(f"{uid}: relations must be a list")
        else:
            for rel in relations:
                if not isinstance(rel, dict) or not isinstance(rel.get("target"), str) \
                        or not rel["target"].strip():
                    problems.append(f"{uid}: relation needs a nonempty target")
                    continue
                rel_kind = rel.get("kind", "use")
                if not isinstance(rel_kind, str) or rel_kind not in RELATION_KINDS:
                    problems.append(f"{uid}: relation kind must be one of {sorted(RELATION_KINDS)}; "
                                    f"got {rel_kind!r}")
        uncertainties = unit.get("uncertainties", [])
        if not isinstance(uncertainties, list) or any(not isinstance(item, str) for item in uncertainties):
            problems.append(f"{uid}: uncertainties must be a list of strings")
        members = unit.get("members", [])
        if members and not isinstance(members, list):
            problems.append(f"{uid}: members must be a list")
    dispositions = payload.get("dispositions")
    if not isinstance(dispositions, dict):
        return problems + ["dispositions must be an object keyed by inventory id"]
    missing = sorted(scope_ids - set(dispositions))
    extra = sorted(set(dispositions) - scope_ids)
    if missing:
        problems.append(f"dispositions missing inventory ids: {missing[:12]}")
    if extra:
        problems.append(f"dispositions has non-scope keys: {extra[:12]}")
    for key, entry in dispositions.items():
        if key not in scope_ids:
            continue
        how = entry.get("how") if isinstance(entry, dict) else None
        if not isinstance(how, str) or how not in DISPOSITION_HOW:
            problems.append(f"disposition {key}: how must be one of {sorted(DISPOSITION_HOW)}; "
                            f"got {how!r}")
            continue
        target = entry.get("unit")
        if how in {"unit", "grouped"}:
            if not isinstance(target, str) or target not in seen:
                problems.append(f"disposition {key}: unit target {target!r} is not a unit "
                                "defined in this result")
        if how == "unit" and target != key:
            problems.append(f"disposition {key}: how=unit requires target == the same id")
        reason = entry.get("reason")
        if how == "index_only" and (not isinstance(reason, str) or not reason.strip()):
            problems.append(f"disposition {key}: index_only requires a reason")
        if reason is not None and not isinstance(reason, str):
            problems.append(f"disposition {key}: reason must be a string")
    notes = payload.get("batch_notes")
    if not isinstance(notes, str) or not notes.strip():
        problems.append("batch_notes must be a nonempty string")
    return problems


def normalize_details(payload: Any, paths: list[str], inventory: dict[str, dict],
                      known_unit_ids: set[str]) -> list[str]:
    """Make a usable answer compliant without dropping facts.

    Identity is repaired only when path, kind and qualified name identify one
    batch inventory id. All rewritten identity fields receive flags. Shape
    repairs retain facts; a strict check at submission still decides acceptance.
    Raises when nothing usable is left or identity correction would collide."""
    if not isinstance(payload, dict):
        raise ValueError("module result is not a JSON object")
    if not isinstance(payload.get("units"), list):
        raise ValueError("module result has no units list")
    if not payload["units"] and any(inventory.get(path, {}).get("symbols") for path in paths):
        raise ValueError("module result has no units")
    flags: list[str] = []
    scope_ids = {row["id"] for path in paths for row in inventory[path]["symbols"]}
    # Only structural identity fields are rewritten; prose is never searched.
    # Include references as well as definitions, since either can contain a typo.
    def corrected(uid: Any, location: str) -> Any:
        if not isinstance(uid, str) or uid in scope_ids or uid.startswith("grp:"):
            return uid
        matches = [candidate for candidate in scope_ids
                   if _detail_identity(candidate) == _detail_identity(uid)]
        if len(matches) == 1:
            flags.append(f"id_corrected: {uid} -> {matches[0]} ({location})")
            return matches[0]
        return uid

    for index, unit in enumerate(payload["units"]):
        if not isinstance(unit, dict):
            continue
        unit["id"] = corrected(unit.get("id"), f"units[{index}].id")
        relations = unit.get("relations")
        for rel_index, rel in enumerate(relations if isinstance(relations, list) else []):
            if isinstance(rel, dict) and "target" in rel:
                rel["target"] = corrected(rel["target"], f"units[{index}].relations[{rel_index}].target")
        if isinstance(unit.get("members"), list):
            unit["members"] = [corrected(member, f"units[{index}].members[{member_index}]")
                               for member_index, member in enumerate(unit["members"])]
    dispositions = payload.get("dispositions")
    if isinstance(dispositions, dict):
        for key in list(dispositions):
            entry = dispositions[key]
            if isinstance(entry, dict) and "unit" in entry:
                entry["unit"] = corrected(entry["unit"], f"dispositions[{key}].unit")
            target_key = corrected(key, f"dispositions[{key}] key")
            if target_key != key:
                if target_key in dispositions:
                    raise ValueError(f"duplicate disposition after id correction: {key} -> {target_key}")
                dispositions[target_key] = dispositions.pop(key)
    units = [unit for unit in payload["units"] if isinstance(unit, dict)
             and isinstance(unit.get("id"), str) and unit["id"].strip()]
    if len(units) != len(payload["units"]):
        flags.append(f"dropped {len(payload['units']) - len(units)} malformed unit(s)")
    for unit in units:
        kind, changed = _normalize_choice(unit.get("kind"), UNIT_KINDS, "module_region")
        if changed:
            flags.append(f"{unit['id']}: kind rewritten to {kind}")
            unit["kind"] = kind
        if not isinstance(unit.get("explain"), str) or not unit["explain"].strip():
            flags.append(f"{unit['id']}: explain was empty; wrote a placeholder")
            unit["explain"] = "No explanation was returned for this unit."
        if "summary" in unit and not isinstance(unit["summary"], str):
            unit["summary"] = _as_text(unit["summary"])
            flags.append(f"{unit['id']}: summary was not a string; converted to text")
        if not isinstance(unit.get("extras"), list):
            flags.append(f"{unit['id']}: extras was not a list; dropped")
            unit["extras"] = []
        for extra in unit["extras"]:
            if not isinstance(extra, dict):
                continue
            topic, changed = _normalize_choice(extra.get("topic"), EXTRA_TOPICS, "contract")
            if changed:
                extra["topic"] = topic
        relations = unit.get("relations")
        if relations is not None and not isinstance(relations, list):
            flags.append(f"{unit['id']}: relations was not a list; dropped")
            unit["relations"] = []
        for rel in unit.get("relations") or []:
            if not isinstance(rel, dict):
                continue
            rel_kind, changed = _normalize_choice(rel.get("kind", "use"), RELATION_KINDS, "use")
            if changed:
                flags.append(f"{unit['id']}: relation kind rewritten to {rel_kind}")
                rel["kind"] = rel_kind
        if not isinstance(unit.get("uncertainties"), list):
            flags.append(f"{unit['id']}: uncertainties was not a list; dropped")
            unit["uncertainties"] = []
    payload["units"] = units
    scope_ids = {row["id"] for path in paths for row in inventory[path]["symbols"]}
    dispositions = payload.get("dispositions")
    if not isinstance(dispositions, dict):
        dispositions = {}
        flags.append("dispositions was missing; rebuilt as index_only")
    for key in sorted(scope_ids - set(dispositions)):
        dispositions[key] = {"how": "index_only", "unit": None,
                             "reason": "no disposition returned; indexed without prose"}
        flags.append(f"{key}: disposition missing; treated as index_only")
    for key in sorted(set(dispositions) - scope_ids):
        dispositions.pop(key)
        flags.append(f"{key}: disposition key was not in this batch; dropped")
    for key, entry in dispositions.items():
        how = entry.get("how") if isinstance(entry, dict) else None
        if not isinstance(how, str) or how not in DISPOSITION_HOW:
            dispositions[key] = {"how": "index_only", "unit": None,
                                 "reason": "invalid disposition; indexed without prose"}
            flags.append(f"{key}: invalid disposition; treated as index_only")
    payload["dispositions"] = dispositions
    if not isinstance(payload.get("batch_notes"), str) or not payload["batch_notes"].strip():
        payload["batch_notes"] = "No batch notes returned."
        flags.append("batch_notes was empty")
    return flags


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


def normalize_tree(payload: Any, unit_universe: set[str]) -> list[str]:
    """Repair shape only: drop bad nodes, reattach orphans under the first root,
    and assign unowned units to a fallback node. Never drops a unit."""
    if not isinstance(payload, dict):
        raise ValueError("tree result is not a JSON object")
    nodes = [node for node in payload.get("nodes") or []
             if isinstance(node, dict) and isinstance(node.get("id"), str)
             and _NODE_ID.match(node["id"])]
    if not nodes:
        raise ValueError("tree result has no usable nodes")
    flags: list[str] = []
    seen: set[str] = set()
    unique: list[dict] = []
    for node in nodes:
        if node["id"] in seen:
            flags.append(f"dropped duplicate node {node['id']}")
            continue
        seen.add(node["id"])
        unique.append(node)
    nodes = unique
    by_id = {node["id"]: node for node in nodes}
    roots = [node for node in nodes if node.get("parent") is None]
    if not roots:
        nodes[0]["parent"] = None
        roots = [nodes[0]]
        flags.append("no root; promoted the first node")
    root = roots[0]["id"]
    for node in nodes:
        parent = node.get("parent")
        if node["id"] != root and (not isinstance(parent, str) or parent not in by_id):
            node["parent"] = root
            flags.append(f"{node['id']}: parent missing; attached to root")
    for field in ("title", "capability", "summary"):
        for node in nodes:
            if not isinstance(node.get(field), str) or not node[field].strip():
                node[field] = node.get("title") or node["id"]
                flags.append(f"{node['id']}: {field} was empty")
    for node in nodes:
        if not isinstance(node.get("unit_ids"), list):
            node["unit_ids"] = []
    owner: set[str] = set()
    for node in nodes:
        kept = [uid for uid in node["unit_ids"] if isinstance(uid, str) and uid in unit_universe
                and uid not in owner]
        if len(kept) != len(node["unit_ids"]):
            flags.append(f"{node['id']}: dropped unknown or duplicate unit ids")
        node["unit_ids"] = kept
        owner.update(kept)
    missing = sorted(unit_universe - owner)
    if missing:
        fallback = by_id.get(root)
        assert fallback is not None
        fallback.setdefault("unit_ids", []).extend(missing)
        flags.append(f"{len(missing)} unit(s) had no owner; assigned to the root")
    if not isinstance(payload.get("depends_on"), list):
        payload["depends_on"] = []
        flags.append("depends_on was not a list; dropped")
    payload["nodes"] = nodes
    return flags


def mechanical_tree(modules: list[dict], units: dict[str, dict]) -> dict:
    """A real structural fallback when the tree task cannot run: one node per
    module/batch under a single root. It is honestly coarse, not a semantic
    grouping, and the renderer says so."""
    nodes = [{"id": "root", "parent": None, "title": "Codebase",
              "capability": "Every source area of the repository. The semantic tree task "
                            "did not produce accepted output, so the program grouped units "
                            "by their reading batch; this is a structural fallback.",
              "summary": "Open the area page for one batch of source files.",
              "unit_ids": []}]
    module_of: dict[str, str] = {}
    for module in modules:
        nid = f"area-{module['number'] + 1}"
        nodes.append({"id": nid, "parent": "root", "title": module.get("title") or nid,
                      "capability": "The source files in this reading batch.",
                      "summary": "Units read from this batch of files.",
                      "unit_ids": []})
        for path in module["files"]:
            module_of[path] = nid
    by_id = {node["id"]: node for node in nodes}
    for uid in units:
        path = uid.split("::", 1)[0]
        nid = module_of.get(path, "root")
        by_id[nid]["unit_ids"].append(uid)
    return {"nodes": nodes, "depends_on": [],
            "fallback": "mechanical batch grouping; the tree task did not complete"}
