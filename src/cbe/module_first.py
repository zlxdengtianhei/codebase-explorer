"""Build a bounded module grouping *candidate* from a legacy CBE ledger.

The legacy tree supplies ownership and short labels only. Its descriptions and
review state are never promoted to evidence for a new documentation run.
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Mapping
from typing import Any


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _id_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{label} must be a list of nonempty IDs")
    if len(value) != len(set(value)):
        raise ValueError(f"{label} contains duplicate IDs")
    return value


def _symbols(inventory: Mapping[str, Any], label: str) -> set[str]:
    records = _mapping(inventory.get("symbols"), f"{label}.symbols")
    ids = set(records)
    if any(not isinstance(symbol_id, str) or not symbol_id for symbol_id in ids):
        raise ValueError(f"{label} contains an invalid canonical symbol ID")
    for symbol_id, record in records.items():
        symbol = _mapping(record, f"{label}.symbols[{symbol_id}]")
        if symbol.get("id", symbol_id) != symbol_id:
            raise ValueError(f"{label} canonical symbol ID disagrees with its record: {symbol_id}")
    return ids


def _support_kind(symbol: Mapping[str, Any]) -> str | None:
    path = symbol.get("path")
    if not isinstance(path, str):
        return None
    if path.startswith(("t/", "tests/")):
        return "tests"
    if path.startswith("examples/"):
        return "examples"
    if path.startswith(("docs/", "extra/")):
        return "docs"
    return None


def _checked_groups(legacy: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw = _mapping(legacy.get("groups"), "legacy groups")
    if not raw:
        raise ValueError("legacy groups must contain one root")
    groups: dict[str, dict[str, Any]] = {}
    for group_id, value in raw.items():
        if not isinstance(group_id, str) or not group_id:
            raise ValueError("legacy group ID must be a nonempty string")
        record = _mapping(value, f"legacy group {group_id}")
        if record.get("group_id") != group_id:
            raise ValueError(f"legacy group identity mismatch: {group_id}")
        parent_id = record.get("parent_id")
        if parent_id is not None and (not isinstance(parent_id, str) or not parent_id):
            raise ValueError(f"legacy group {group_id} has an invalid parent")
        children = _id_list(record.get("children"), f"children of {group_id}")
        members = _id_list(record.get("member_ids"), f"member_ids of {group_id}")
        question = record.get("question_answered")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"legacy group {group_id} needs a candidate question")
        title = record.get("title", group_id)
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"legacy group {group_id} has an invalid candidate title")
        groups[group_id] = {
            "parent_id": parent_id,
            "children": children,
            "member_ids": members,
            "title": title,
            "question_answered": question,
        }
    return groups


def _reject_cycles(groups: Mapping[str, dict[str, Any]]) -> None:
    """Detect cycles even in components disconnected from the apparent root."""
    state: dict[str, int] = {}
    for first in sorted(groups):
        if state.get(first) == 2:
            continue
        stack: list[tuple[str, bool]] = [(first, False)]
        while stack:
            group_id, leaving = stack.pop()
            if leaving:
                state[group_id] = 2
                continue
            if state.get(group_id) == 1:
                raise ValueError(f"legacy group cycle at {group_id}")
            if state.get(group_id) == 2:
                continue
            state[group_id] = 1
            stack.append((group_id, True))
            stack.extend((child, False) for child in reversed(groups[group_id]["children"]))


def _tree_order(groups: Mapping[str, dict[str, Any]]) -> tuple[list[str], dict[str, int]]:
    for group_id, record in groups.items():
        parent_id = record["parent_id"]
        if parent_id is not None and parent_id not in groups:
            raise ValueError(f"legacy group {group_id} has missing parent {parent_id}")
        for child_id in record["children"]:
            if child_id not in groups:
                raise ValueError(f"legacy group {group_id} has missing child {child_id}")

    _reject_cycles(groups)
    roots = [group_id for group_id, record in groups.items() if record["parent_id"] is None]
    if len(roots) != 1:
        raise ValueError(f"legacy groups must have exactly one root, found {len(roots)}")
    for group_id, record in groups.items():
        for child_id in record["children"]:
            if groups[child_id]["parent_id"] != group_id:
                raise ValueError(f"legacy group parent/child mismatch: {group_id} -> {child_id}")
        parent_id = record["parent_id"]
        if parent_id is not None and group_id not in groups[parent_id]["children"]:
            raise ValueError(f"legacy group {group_id} is missing from parent {parent_id} children")

    order: list[str] = []
    depth: dict[str, int] = {}
    queue = deque([(roots[0], 0)])
    while queue:
        group_id, level = queue.popleft()
        if group_id in depth:
            raise ValueError(f"legacy group {group_id} has duplicate parent ownership")
        depth[group_id] = level
        order.append(group_id)
        queue.extend((child_id, level + 1) for child_id in groups[group_id]["children"])
    if len(order) != len(groups):
        raise ValueError("legacy group tree is disconnected")
    return order, depth


def _check_ownership(
    groups: Mapping[str, dict[str, Any]], order: list[str], canonical_ids: set[str]
) -> None:
    owner: dict[str, str] = {}
    for group_id in order:
        for symbol_id in groups[group_id]["member_ids"]:
            if symbol_id not in canonical_ids:
                raise ValueError(f"legacy group {group_id} owns unknown canonical symbol {symbol_id}")
            if symbol_id in owner:
                raise ValueError(
                    f"duplicate symbol ownership: {symbol_id} in {owner[symbol_id]} and {group_id}"
                )
            owner[symbol_id] = group_id
    missing = canonical_ids - owner.keys()
    if missing:
        raise ValueError(f"missing symbol ownership: {len(missing)}; first={min(missing)}")


def build_collapsed_module_plan(
    legacy_ledger: Mapping[str, Any],
    current_inventory: Mapping[str, Any],
    max_depth: int = 2,
    group_limit: int = 312,
) -> dict[str, Any]:
    """Return an unreviewed plan; every symbol must map to an existing module.

    The retained root and intermediate groups are navigation. Groups at
    ``max_depth`` own the canonical symbols of their entire former subtree.
    The function neither mutates its inputs nor reads or writes run files.
    """
    if type(max_depth) is not int or max_depth < 1:
        raise ValueError("max_depth must be a positive integer")
    if type(group_limit) is not int or group_limit < 1:
        raise ValueError("group_limit must be a positive integer")
    legacy = _mapping(legacy_ledger, "legacy_ledger")
    current = _mapping(current_inventory, "current_inventory")
    previous = _mapping(legacy.get("inventory"), "legacy inventory")
    revision = legacy.get("source_revision")
    if not isinstance(revision, str) or not revision or any(
        inventory.get("source_revision") != revision for inventory in (previous, current)
    ):
        raise ValueError("source_revision must match exactly across legacy ledger and both inventories")
    previous_ids = _symbols(previous, "legacy inventory")
    current_ids = _symbols(current, "current inventory")
    if previous_ids != current_ids:
        raise ValueError(
            "canonical symbol IDs differ between legacy and current inventory: "
            f"legacy_only={len(previous_ids - current_ids)}, current_only={len(current_ids - previous_ids)}"
        )

    groups = _checked_groups(legacy)
    order, depth = _tree_order(groups)
    _check_ownership(groups, order, current_ids)
    retained = [group_id for group_id in order if depth[group_id] <= max_depth]
    if len(retained) > group_limit:
        raise ValueError(f"collapsed group count {len(retained)} exceeds group_limit {group_limit}")

    modules = [group_id for group_id in retained if depth[group_id] == max_depth]
    members_by_module: dict[str, list[str]] = {group_id: [] for group_id in modules}
    assigned_symbols: set[str] = set()
    stack: list[tuple[str, str | None]] = [(order[0], None)]
    while stack:
        group_id, module_id = stack.pop()
        if depth[group_id] == max_depth:
            module_id = group_id
        for symbol_id in groups[group_id]["member_ids"]:
            if module_id is None:
                raise ValueError(
                    f"symbol {symbol_id} is owned above depth {max_depth}; no existing module ancestor"
                )
            members_by_module[module_id].append(symbol_id)
            assigned_symbols.add(symbol_id)
        stack.extend((child_id, module_id) for child_id in reversed(groups[group_id]["children"]))

    result_groups: dict[str, dict[str, Any]] = {}
    for group_id in retained:
        level = depth[group_id]
        source = groups[group_id]
        extra = {
            "review_state": "candidate",
            "legacy_group_id": group_id,
            "candidate_source": "legacy_group_tree",
        }
        if level < max_depth:
            extra["presentation"] = "navigation"
        result_groups[group_id] = {
            "group_id": group_id,
            "parent_id": source["parent_id"],
            "children": list(source["children"]) if level < max_depth else [],
            "member_ids": members_by_module[group_id] if level == max_depth else [],
            "title": source["title"],
            # The legacy question may assert behavior that has never been reviewed.
            # A neutral locator question is safe to publish as a candidate.
            "question_answered": f"Where is {source['title'].replace('-', ' ')} in the source tree?",
            "body": "",
            "extra": extra,
        }
    # Tests, examples and docs are useful source locators, but do not form
    # implementation modules merely because old questions had those labels.
    support_modules: dict[str, list[str]] = {kind: [] for kind in ("tests", "examples", "docs")}
    for group_id in modules:
        members = result_groups[group_id]["member_ids"]
        kinds = {
            _support_kind(_mapping(current["symbols"][sid], f"symbol {sid}"))
            for sid in members
        }
        if members and len(kinds) == 1:
            kind = next(iter(kinds))
            if kind in support_modules:
                support_modules[kind].append(group_id)
    support_members = {
        kind: [sid for group_id in group_ids for sid in result_groups[group_id]["member_ids"]]
        for kind, group_ids in support_modules.items()
    }
    if any(support_members.values()):
        for group_id in [gid for gids in support_modules.values() for gid in gids]:
            parent_id = result_groups[group_id]["parent_id"]
            result_groups[parent_id]["children"].remove(group_id)
            del result_groups[group_id]
        root_id = order[0]
        for group_id in reversed(retained):
            if group_id == root_id or group_id not in result_groups:
                continue
            group = result_groups[group_id]
            if not group["children"] and not group["member_ids"]:
                result_groups[group["parent_id"]]["children"].remove(group_id)
                del result_groups[group_id]
        area_id = "support-catalogue-area"
        names = {
            "tests": ("test-support-catalogue", "test cases and fixtures"),
            "examples": ("example-source-catalogue", "example programs"),
            "docs": ("docs-and-release-catalogue", "documentation and release helpers"),
        }
        synthetic_ids = {area_id, *(name for name, _ in names.values())}
        if synthetic_ids & groups.keys():
            raise ValueError("synthetic support catalogue group ID conflicts with legacy groups")
        children = [names[kind][0] for kind, members in support_members.items() if members]
        result_groups[root_id]["children"].append(area_id)
        result_groups[area_id] = {
            "group_id": area_id,
            "parent_id": root_id,
            "children": children,
            "member_ids": [],
            "title": "tests examples and docs",
            "question_answered": "Where are the test, example and documentation sources?",
            "body": "",
            "extra": {"review_state": "candidate", "candidate_source": "synthetic_support_catalogue", "presentation": "navigation"},
        }
        for kind, members in support_members.items():
            if not members:
                continue
            module_id, title = names[kind]
            result_groups[module_id] = {
                "group_id": module_id,
                "parent_id": area_id,
                "children": [],
                "member_ids": members,
                "title": f"{kind} source catalogue",
                "question_answered": f"Where are {title} located?",
                "body": "",
                "extra": {"review_state": "candidate", "candidate_source": "synthetic_support_catalogue"},
            }
    if len(result_groups) > group_limit:
        raise ValueError(f"collapsed group count {len(result_groups)} exceeds group_limit {group_limit}")
    depth_counts = Counter(depth.values())
    retained_legacy_count = sum(group_id in groups for group_id in result_groups)
    return {
        "source_revision": revision,
        "groups": result_groups,
        "stats": {
            "legacy_group_count": len(groups),
            "retained_group_count": len(result_groups),
            "collapsed_group_count": len(groups) - retained_legacy_count,
            "module_count": sum(bool(group["member_ids"]) for group in result_groups.values()),
            "symbol_count": len(assigned_symbols),
            "test_only_modules_collapsed": len(support_modules["tests"]),
            "test_symbol_count": len(support_members["tests"]),
            "example_symbol_count": len(support_members["examples"]),
            "docs_symbol_count": len(support_members["docs"]),
            "legacy_max_depth": max(depth.values()),
            "depth_counts": {str(level): depth_counts[level] for level in sorted(depth_counts)},
            "group_limit": group_limit,
        },
    }
