"""Layered clustering: the model groups detail, one level at a time, into a module tree.

The program freezes the source once, writes one detail per function, method and
class (``checks``, ``prompts``), and then never sends source again. This module
turns the detail into a tree:

* ``candidate_groups`` - the program grouping (``skeleton``) used only as a hint;
* ``leaf_chunks`` / ``group_chunks`` - about ``LAYER_BATCH_TOKENS`` of detail per
  layer task;
* ``blocks`` - what one task sees: members, candidate groups, call counts;
* ``decode`` - one layer answer into groups, with the program checks of design
  2.3 (each member once, 2-12 members, summary length caps); a group above 12
  members is sent back once so its author can divide it by function;
* ``fallback_groups`` - what the program makes of a chunk whose answer stays
  unusable (design 2.3: fall back to the candidate grouping, not to a re-ask);
* ``assemble`` - the layers into the published tree.

Layers are numbered from the leaves: layer 1 groups units into modules, layer 2
groups modules into systems, and so on. How many layers exist is decided while
the run goes on: a layer whose groups are at most ``TOP_MAX`` is the top, and the
overview (L0) is written from it.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

from cbe import mustlink, skeleton, treename
from cbe.records import summary_sentence
from cbe.treename import normalize_title
from cbe.token_budget import count_text_tokens

LAYER_BATCH_TOKENS = 12_000
#: Design 2.3: one leaf chunk holds about this many members, so one author can group it.
MAX_CHUNK_MEMBERS = 120
MIN_GROUP = 2
MAX_GROUP = 12
TOP_MAX = 8
#: Summary caps by the layer above the leaves (design 2.3: 150 / 300 / 500 tokens).
SUMMARY_CAPS = {1: 150, 2: 300}
SUMMARY_CAP_TOP = 500
CAPABILITY_WORDS = 45
TITLE_WORDS = 9
#: Design 2.3: a chunk of N members is expected to become about N/8 groups.
MEMBERS_PER_GROUP = 8


class LayerError(ValueError):
    """A layer answer cannot be used at all."""


class LayerShapeError(LayerError):
    """A group is below two or above twelve members: the same author is asked to fix its shape."""


def summary_cap(level: int) -> int:
    return SUMMARY_CAPS.get(level, SUMMARY_CAPS[2] if level == 2 else SUMMARY_CAP_TOP)


def expected_groups(members: int) -> int:
    """The count the chunk hint names (design 2.3: about one group per eight members)."""
    return max(1, round(members / MEMBERS_PER_GROUP))


def leaf_plan(units: dict, edges: list[dict]) -> dict:
    """What the leaf layer starts from: the candidate grouping, and the linked unit sets.

    ``skeleton`` gives candidate groups (a hint only, design 2.3). ``mustlink`` then
    merges the candidates that hold units which must be grouped together - a declaration
    and its implementation, a test and what it tests, a header and its source - so that
    chunking cannot put them in front of two different authors. The merged candidates
    are still only a hint; the model may split them."""
    nodes = skeleton.build(units, edges)["nodes"]
    hinted = [sorted(node["unit_ids"]) for node in nodes if node.get("unit_ids")]
    merged = mustlink.merge(hinted, mustlink.links(units, edges)["pairs"], max_group=MAX_GROUP)
    return merged


def candidate_groups(units: dict, edges: list[dict]) -> list[list[str]]:
    """The program's leaf grouping, a hint only (``skeleton`` output, merged by ``mustlink``)."""
    return leaf_plan(units, edges)["candidates"]


def _member_tokens(unit: dict) -> int:
    return count_text_tokens(summary_sentence(unit)) + 8


def leaf_chunks(units: dict, candidates: list[list[str]],
                linked: list[list[str]] | None = None) -> list[dict]:
    """Cut the detail into chunks of about ``LAYER_BATCH_TOKENS`` and ``MAX_CHUNK_MEMBERS``,
    keeping candidates whole (design 2.3: a chunk small enough for the model to group).

    A candidate is never split, so a ``mustlink`` set inside it is never split either.
    Each chunk carries the linked sets it holds (``linked``), for the answer check."""
    chunks, current, used, members = [], [], 0, 0
    for candidate in candidates:
        inside = [uid for uid in candidate if uid in units]
        size = sum(_member_tokens(units[uid]) for uid in inside) + 60
        too_big = current and (used + size > LAYER_BATCH_TOKENS
                              or members + len(inside) > MAX_CHUNK_MEMBERS)
        if too_big:
            chunks.append({"members": [uid for group in current for uid in group],
                           "candidates": list(current)})
            current, used, members = [], 0, 0
        current.append(list(candidate))
        used += size
        members += len(inside)
    if current:
        chunks.append({"members": [uid for group in current for uid in group],
                       "candidates": list(current)})
    for chunk in chunks:
        members_here = set(chunk["members"])
        chunk["linked"] = [list(group) for group in linked or [] if set(group) <= members_here]
    return chunks


def group_chunks(groups: list[dict]) -> list[dict]:
    """Cut one layer's groups into chunks of about ``LAYER_BATCH_TOKENS`` of summaries."""
    chunks, current, used = [], [], 0
    for group in groups:
        size = count_text_tokens(group.get("title") or "") + count_text_tokens(group.get("capability") or "") \
            + count_text_tokens(group.get("summary") or "") + 24
        if current and used + size > LAYER_BATCH_TOKENS:
            chunks.append({"members": [row["id"] for row in current]})
            current, used = [], 0
        current.append(group)
        used += size
    if current:
        chunks.append({"members": [row["id"] for row in current]})
    return chunks


def labels_for(members: list[str], *, unit_layer: bool) -> dict[str, str]:
    """``{member: label}``: u1, u2 ... for a unit layer, g1, g2 ... above it."""
    prefix = "u" if unit_layer else "g"
    return {member: f"{prefix}{i + 1}" for i, member in enumerate(members)}


def _edge_table(edges: list[dict], membership: dict[str, str]) -> dict[tuple[str, str], int]:
    counts: Counter = Counter()
    for edge in edges:
        a, b = membership.get(edge["from"]), membership.get(edge["to"])
        if a and b and a != b:
            counts[a, b] += edge.get("count") or 1
    return dict(counts)


def leaf_blocks(units: dict, chunk: dict, labels: dict[str, str], edges: list[dict]) -> list[str]:
    """One block per candidate group: its member detail, and calls in and out of it.

    A candidate that holds a ``mustlink`` set says so in its heading, because the model
    may split a candidate group and must not split that set."""
    candidate_of = {uid: f"C{i + 1}" for i, group in enumerate(chunk["candidates"]) for uid in group}
    ties = _edge_table(edges, candidate_of)
    linked = [set(group) for group in chunk.get("linked") or []]
    blocks = []
    for index, group in enumerate(chunk["candidates"]):
        label = f"C{index + 1}"
        kept = sum(1 for group_units in linked if group_units <= set(group))
        note = f"; keep {kept} linked set(s) in one group" if kept else ""
        lines = [f"## {label}  ({len(group)} units; candidate group, not fixed{note})"]
        for uid in group:
            unit = units.get(uid)
            if unit is None:
                continue
            # The file name keeps the locality hint; the directory does not, because the
            # answer follows the work and not the tree. The symbol name is skipped when the
            # detail already opens with it (design 2.1 starts every detail with its subject).
            path = Path((skeleton.unit_paths(unit) or ["?"])[0]).name
            name = skeleton.symbol_words(uid).strip()
            text = " ".join((summary_sentence(unit) or "").split())
            head = f"  {labels[uid]}: {path} · " + (f"{name} · " if name and name.lower() not in text.lower() else "")
            lines.append(head + text)
        out = sorted(((b, n) for (a, b), n in ties.items() if a == label), key=lambda t: (-t[1], t[0]))
        into = sorted(((a, n) for (a, b), n in ties.items() if b == label), key=lambda t: (-t[1], t[0]))
        if out:
            lines.append("  calls out: " + ", ".join(f"C{int(b[1:])} x{n}" for b, n in out[:6]))
        if into:
            lines.append("  called from: " + ", ".join(f"C{int(a[1:])} x{n}" for a, n in into[:6]))
        inside = sum(n for (a, b), n in ties.items() if a == b == label)
        if inside:
            lines.append(f"  calls inside this candidate: {inside}")
        blocks.append("\n".join(lines))
    return blocks


def group_blocks(groups: list[dict], labels: dict[str, str], edges: list[dict],
                 membership: dict[str, str]) -> list[str]:
    """One block per child group of the layer below, plus the calls between them."""
    ties = _edge_table(edges, membership)
    blocks = []
    for group in groups:
        label = labels[group["id"]]
        lines = [f"## {label} — {group.get('title') or group['id']}"]
        if group.get("capability"):
            lines.append(f"capability: {' '.join(group['capability'].split())}")
        if group.get("summary"):
            lines.append(f"summary: {' '.join(group['summary'].split())}")
        out = sorted(((b, n) for (a, b), n in ties.items() if a == label), key=lambda t: (-t[1], t[0]))
        into = sorted(((a, n) for (a, b), n in ties.items() if b == label), key=lambda t: (-t[1], t[0]))
        if out:
            lines.append("calls out: " + ", ".join(f"{b} x{n}" for b, n in out[:6]))
        if into:
            lines.append("called from: " + ", ".join(f"{a} x{n}" for a, n in into[:6]))
        blocks.append("\n".join(lines))
    return blocks


def _trim_words(text: str, limit: int) -> str:
    words = text.split()
    return " ".join(words[:limit])


def _trim_tokens(text: str, cap: int) -> str:
    from cbe.checks import cut_to_tokens
    return cut_to_tokens(text, cap)


def _gid(subtree: list[str]) -> str:
    return "g" + hashlib.sha1("\n".join(sorted(subtree)).encode()).hexdigest()[:10]


def _record(row: dict, subtree: list[str], members: list[str], level: int) -> tuple[dict, list[str]]:
    """A checked group record, plus what the program had to trim."""
    flags = []
    title = " ".join(str(row.get("title") or "").split())
    capability = " ".join(str(row.get("capability") or "").split())
    summary = " ".join(str(row.get("summary") or "").split())
    if len(title.split()) > TITLE_WORDS:
        title = _trim_words(title, TITLE_WORDS)
        flags.append(f"title trimmed to {TITLE_WORDS} words")
    if len(capability.split()) > CAPABILITY_WORDS:
        capability = _trim_words(capability, CAPABILITY_WORDS)
        flags.append("capability trimmed to one sentence")
    if count_text_tokens(summary) > summary_cap(level):
        summary = _trim_tokens(summary, summary_cap(level))
        flags.append(f"summary trimmed to {summary_cap(level)} tokens")
    group = {"id": _gid(subtree), "title": title, "capability": capability, "summary": summary,
             "members": members, "subtree": subtree}
    if isinstance(row.get("why"), str) and row["why"].strip():
        group["why"] = " ".join(row["why"].split())[:240]
    return group, flags


def decode(answer: dict, chunk: dict, labels: dict[str, str], level: int,
           subtrees: dict[str, list[str]], *, allow_split: bool = False,
           names: dict[str, str] | None = None,
           edges: list[dict] | None = None) -> tuple[list[dict], list[str]]:
    """Decode one layer answer against its chunk (see design 2.3's program checks).

    ``subtrees`` maps a member id above the leaf layer to the units it covers.
    A group above ``MAX_GROUP`` members, or one below two, is sent back once
    (``LayerShapeError``) so the same author can divide or merge it; only when it comes
    back wrong again (``allow_split``) does the program cut it, by the candidate grouping.
    Raises ``LayerError`` when the answer does not partition the members."""
    rows = answer.get("groups") if isinstance(answer, dict) else None
    if not isinstance(rows, list):
        raise LayerError('answer needs {"groups": [...]}')
    by_label = {label: member for member, label in labels.items()}
    unit_layer = level == 1
    seen: Counter = Counter()
    groups: list[dict] = []
    flags: list[str] = []
    problems: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            problems.append(f"group {index + 1} is not an object")
            continue
        listed = row.get("members")
        members = []
        for label in listed if isinstance(listed, list) else []:
            member = by_label.get(label) if isinstance(label, str) else None
            if member is None:
                problems.append(f"group {index + 1} names an unknown member {label!r}")
            elif member not in members:
                members.append(member)
        if not members:
            problems.append(f"group {index + 1} has no member of this chunk")
            continue
        if not all(isinstance(row.get(key), str) and row[key].strip()
                   for key in ("title", "capability", "summary")):
            problems.append(f"group {index + 1} needs title, capability and summary")
            continue
        for member in members:
            seen[member] += 1
        subtree = members if unit_layer else [u for member in members for u in subtrees.get(member, [])]
        group, trimmed = _record(row, subtree, members, level)
        flags += [f"group {index + 1}: {flag}" for flag in trimmed]
        groups.append(group)
    missing = [label for member, label in labels.items() if member not in seen]
    repeated = [label for member, label in labels.items() if seen[member] > 1]
    if missing and not allow_split:
        problems.append(f"modules without a group: {', '.join(missing[:20])}")
    if repeated:
        problems.append(f"modules in more than one group: {', '.join(repeated[:20])}")
    if problems:
        raise LayerError("; ".join(problems))
    left_out = [member for member in members_in_order(labels) if seen[member] == 0]
    if left_out:
        groups, placed, still = _place_left_out(groups, left_out, list(chunk.get("candidates") or []),
                                               level, subtrees, names or {})
        flags += placed
        if still:
            raise LayerError("modules without a group: "
                             + ", ".join(labels[uid] for uid in still[:20]))
    minimum = MIN_GROUP if len(labels) >= MIN_GROUP else 1
    split = _split_links(groups, list(chunk.get("linked") or []))
    if split and not allow_split:
        listed = ", ".join(labels.get(uid, uid) for uid in split[0][:6])
        more = f" ({len(split)} set(s) in all)" if len(split) > 1 else ""
        raise LayerShapeError(
            "the program linked these units in the source (a declaration and its implementation, "
            "a test and what it tests, a header and its source) and they must stay in one group: "
            f"{listed}{more}. Put each linked set in one group, keep every other group as it is, "
            "and answer with the same JSON shape.")
    if split:
        flags.append("the program linked " + ", ".join(
            " ".join(labels.get(uid, uid) for uid in group[:4]) for group in split[:3])
            + " but the answer put them in different groups; the answer was kept as it came back")
    oversized = [group for group in groups if len(group["members"]) > MAX_GROUP]
    undersized = [group for group in groups if len(group["members"]) < minimum] if minimum > 1 else []
    if oversized and not allow_split:
        listed = "; ".join(f"{group['title']!r} has {len(group['members'])}" for group in oversized[:6])
        more = f" and {len(oversized) - 6} more" if len(oversized) > 6 else ""
        raise LayerShapeError(
            f"the limit is {MAX_GROUP} members and these groups are larger: {listed}{more}. "
            f"Divide each of them by function into groups of 4 to {MAX_GROUP} members, keep every other "
            "group as it is, and answer with the same JSON shape.")
    if undersized and not allow_split:
        listed = ", ".join(repr(group["title"]) for group in undersized[:6])
        raise LayerShapeError(
            f"every group needs 2 to {MAX_GROUP} members and these have one: {listed}. "
            "Merge each of them with its closest neighbour, keep every other group as it is, "
            "and answer with the same JSON shape.")
    groups, shaped = _shape_groups(groups, minimum, level, subtrees,
                                   list(chunk.get("candidates") or []), names or {}, edges)
    return groups, flags + shaped


def _split_links(groups: list[dict], linked: list[list[str]]) -> list[list[str]]:
    """The linked sets an answer put in more than one group (``mustlink``)."""
    split = []
    for units in linked:
        wanted = set(units)
        homes = sum(1 for group in groups if wanted & set(group["members"]))
        if homes > 1:
            split.append(list(units))
    return split


def members_in_order(labels: dict[str, str]) -> list[str]:
    """The chunk's members in the order the prompt lists them (labels are u1, u2 ... or g1 ...)."""
    return [member for member, _ in sorted(labels.items(), key=lambda item: int(item[1][1:]))]


def _place_left_out(groups: list[dict], left_out: list[str], candidates: list[list[str]], level: int,
                    subtrees: dict[str, list[str]],
                    names: dict[str, str]) -> tuple[list[dict], list[str], list[str]]:
    """Put members a final answer left out into the group that holds their candidate.

    Design 2.3 asks once more for an answer that does not partition the members; when the
    last answer still leaves some out, its own groups are kept and the leftovers join the
    groups that already hold most of their candidate group. A leftover with no such home
    keeps the program's candidate grouping (the whole-chunk fallback)."""
    flags: list[str] = []
    remaining = list(left_out)
    for candidate in candidates:
        piece = [uid for uid in candidate if uid in remaining]
        if not piece:
            continue
        home, overlap = None, 0
        for group in groups:
            shared = len(set(group["members"]) & set(candidate))
            if shared > overlap:
                home, overlap = group, shared
        if home is None:
            continue  # no model group follows this candidate: the caller falls back per chunk
        home["members"] = home["members"] + piece
        home["subtree"] = _subtree_for(home["members"], level, subtrees)
        home["id"] = _gid(home["subtree"])
        _add_holds(home, [names.get(uid) or uid for uid in piece], level)
        remaining = [uid for uid in remaining if uid not in set(piece)]
        flags.append(f"member(s) the answer left out were placed in {home['title']!r}: "
                     + ", ".join(names.get(uid) or uid for uid in piece[:6]))
    return groups, flags, remaining


def _subtree_for(members: list[str], level: int, subtrees: dict[str, list[str]]) -> list[str]:
    return list(members) if level == 1 else [u for member in members for u in subtrees.get(member, [])]


def _units_under(group: dict, level: int, subtrees: dict[str, list[str]]) -> list[str]:
    """The inventory ids a group covers, one level up or down."""
    return _subtree_for(group["members"], level, subtrees)


def _group_ties(groups: list[dict], level: int, subtrees: dict[str, list[str]],
                edges: list[dict] | None) -> dict[tuple[int, int], int]:
    """Call edges between two groups, both directions, keyed by their answer positions."""
    owner: dict[str, int] = {}
    for index, group in enumerate(groups):
        for uid in _units_under(group, level, subtrees):
            owner.setdefault(uid, index)
    counted: Counter = Counter()
    for edge in edges or []:
        a, b = owner.get(edge.get("from")), owner.get(edge.get("to"))
        if a is None or b is None or a == b:
            continue
        counted[a, b] += edge.get("count") or 1
        counted[b, a] += edge.get("count") or 1
    return dict(counted)


def _candidate_index(groups: list[dict], candidates: list[list[str]], level: int) -> dict[str, int]:
    """``{member: candidate number}`` at the leaf layer; empty above it (no candidates there)."""
    if level != 1 or not candidates:
        return {}
    inside = {uid for group in groups for uid in group["members"]}
    return {uid: index for index, candidate in enumerate(candidates)
            for uid in candidate if uid in inside}


def _shared_candidates(a: dict, b: dict, candidate_of: dict[str, int]) -> int:
    first = {candidate_of[uid] for uid in a["members"] if uid in candidate_of}
    second = {candidate_of[uid] for uid in b["members"] if uid in candidate_of}
    return len(first & second)


def _hold_note(held: list[str], shown: int) -> str:
    """``Also holds `a`, `b` and 3 more.`` - bounded, so one bad answer cannot flood a page."""
    listed = ", ".join(f"`{label}`" for label in held[:shown])
    if len(held) > shown:
        listed += f" and {len(held) - shown} more"
    return f"Also holds {listed}."


def _clause_cut(text: str, words: int) -> str:
    """Trim to ``words`` but end a sentence, or the previous comma, never mid-clause."""
    pieces = _trim_words(text, words).split()
    if len(pieces) >= len(text.split()):
        return text
    for mark in (".", ";", ","):
        for index in range(len(pieces) - 1, 2, -1):
            if pieces[index].endswith(mark):
                return " ".join(pieces[:index + 1]).rstrip(",;")
    return " ".join(pieces).rstrip(",;") + "."


def _add_holds(group: dict, labels: list[str], level: int) -> None:
    """Say in the group's own sentence what the program also put in it (design 2.3).

    The author's sentence stays as written; it is not pretended to cover the added
    members, so the page names them instead of claiming the old sentence is enough. A
    summary gets the same sentence, so the reader of index or page is not misled."""
    fresh = [label for label in labels if label]
    if not fresh:
        return
    group.setdefault("_capability_base", group["capability"])
    group.setdefault("_summary_base", group["summary"])
    held: list[str] = group.setdefault("_holds", [])
    for label in fresh:
        if label not in held:
            held.append(label)
    shown = 5
    note = _hold_note(held, shown)
    while shown > 1 and len(note.split()) > CAPABILITY_WORDS - 12:
        shown -= 1
        note = _hold_note(held, shown)
    capability = _clause_cut(group["_capability_base"], max(8, CAPABILITY_WORDS - len(note.split())))
    group["capability"] = f"{capability} {note}"
    summary = group["_summary_base"]
    reserve = count_text_tokens(" " + note)
    cap = summary_cap(level)
    if count_text_tokens(summary) + reserve > cap:
        summary = _trim_tokens(summary, max(1, cap - reserve))
    group["summary"] = f"{summary} {note}"


def _drop_merge_notes(groups: list[dict]) -> list[dict]:
    for group in groups:
        for key in ("_capability_base", "_summary_base", "_holds"):
            group.pop(key, None)
    return groups


def _merge_undersized(groups: list[dict], minimum: int, level: int, subtrees: dict[str, list[str]],
                      candidates: list[list[str]], names: dict[str, str],
                      edges: list[dict] | None) -> tuple[list[dict], list[str]]:
    """Place a group below ``minimum`` in the group it is tied to - never by answer order.

    Design 2.3 and the second judge: a single-member group does not join the group that
    happens to be listed before it. The program prefers the group it shares the most call
    edges with; with no edges it prefers the group that holds members of the same
    candidate group; answer order is only the last tie-break. The host's sentence and
    summary are written again (``_add_holds``) so the page names the added group. When no
    group has room below the ceiling, one member moves instead of merging."""
    flags: list[str] = []
    current = [dict(group) for group in groups]
    while len(current) > 1:
        small = [index for index, group in enumerate(current) if len(group["members"]) < minimum]
        if not small:
            break
        ties = _group_ties(current, level, subtrees, edges)
        candidate_of = _candidate_index(current, candidates, level)
        # Prefer a host that is still below the expected group size, so one bad answer
        # cannot fill a single host to the ceiling while other groups stay alone.
        choices: list[tuple[tuple[int, int, int, int], int, int]] = []
        for index in small:
            for other_index, other in enumerate(current):
                if other_index == index:
                    continue
                if len(current[index]["members"]) + len(other["members"]) > MAX_GROUP:
                    continue
                score = (ties.get((index, other_index), 0),
                         _shared_candidates(current[index], other, candidate_of),
                         len(other["members"]), -abs(other_index - index))
                choices.append((score, index, other_index))
        roomy = [choice for choice in choices
                 if len(current[choice[2]]["members"]) < MEMBERS_PER_GROUP]
        best = max(roomy or choices, default=None)
        if best is None:
            moved = _move_one_member(current, small[0], ties, minimum, level, subtrees, names, flags)
            if not moved:
                break
            continue
        score, index, host_index = best
        host, extra = current[host_index], current[index]
        host["members"] = host["members"] + extra["members"]
        host["subtree"] = _subtree_for(host["members"], level, subtrees)
        host["id"] = _gid(host["subtree"])
        _add_holds(host, [extra.get("title") or extra["id"]], level)
        reason = (f"{score[0]} call edge(s) to it" if score[0]
                  else "same candidate group" if score[1] else "next to it in the answer")
        flags.append(f"group {extra['title']!r} merged into {host['title']!r} "
                     f"(it was too small; {reason})")
        # Keep the earlier position: the published order follows the answer, not the merge.
        current[min(index, host_index)] = host
        current.pop(max(index, host_index))
    return current, flags


def _move_one_member(groups: list[dict], index: int, ties: dict[tuple[int, int], int],
                     minimum: int, level: int, subtrees: dict[str, list[str]],
                     names: dict[str, str], flags: list[str]) -> bool:
    """No group has room: take one member from the closest group that can spare it."""
    donors = [other for other in range(len(groups))
              if other != index and len(groups[other]["members"]) > minimum]
    if not donors:
        return False
    donor = max(donors, key=lambda other: (ties.get((index, other), 0), len(groups[other]["members"])))
    moved = groups[donor]["members"].pop()
    groups[index]["members"].append(moved)
    for target in (groups[index], groups[donor]):
        target["subtree"] = _subtree_for(target["members"], level, subtrees)
        target["id"] = _gid(target["subtree"])
    label = names.get(moved) or skeleton.symbol_words(moved) or moved
    _add_holds(groups[index], [label], level)
    flags.append(f"group {groups[index]['title']!r} took one member from {groups[donor]['title']!r} "
                 "(it would have been a group of one)")
    return True


def _shape_groups(groups: list[dict], minimum: int, level: int, subtrees: dict[str, list[str]],
                  candidates: list[list[str]], names: dict[str, str],
                  edges: list[dict] | None = None) -> tuple[list[dict], list[str]]:
    """Program checks on size: merge a group of one, cut one above the ceiling by candidates.

    Design 2.3: a model answer that comes back too large a second time is cut by the
    program's candidate grouping, not by member order; each part's responsibility and
    summary are written again from that part's own members, never repeated from the
    parent group. A group of one is merged by its call edges (``_merge_undersized``),
    not by its position in the answer."""
    flags: list[str] = []
    merged = [dict(group) for group in groups]
    if minimum > 1 and len(merged) > 1:
        merged, merge_flags = _merge_undersized(merged, minimum, level, subtrees, candidates,
                                                names, edges)
        flags += merge_flags
    shaped: list[dict] = []
    for group in merged:
        members = group["members"]
        if len(members) <= MAX_GROUP:
            shaped.append(group)
            continue
        parts = (_cut_by_candidates(members, candidates, minimum) if level == 1 and candidates
                 else _pack(members))
        for index, part in enumerate(parts, 1):
            subtree = _subtree_for(part, level, subtrees)
            capability, summary = _segment_texts(group, part, index, len(parts), level, subtrees, names)
            shaped.append({**group, "id": _gid(subtree), "members": part, "subtree": subtree,
                           "title": f"{group['title']} ({index})", "capability": capability,
                           "summary": summary, "note": "program-made part (the group exceeded the member limit twice)"})
        flags.append(f"group {group['title']!r} split into {len(parts)} program groups (the {MAX_GROUP}-member limit)")
    return _drop_merge_notes(shaped), flags


def _cut_by_candidates(members: list[str], candidates: list[list[str]],
                      minimum: int) -> list[list[str]]:
    """Cut an oversized group along the program's candidate grouping (design 2.3)."""
    inside, chosen = set(members), set()
    parts: list[list[str]] = []
    for candidate in candidates:
        piece = [uid for uid in candidate if uid in inside]
        if not piece:
            continue
        chosen |= set(piece)
        parts.extend([piece] if len(piece) <= MAX_GROUP else _pack(piece))
    leftover = [uid for uid in members if uid not in chosen]
    if leftover:
        parts.extend([leftover] if len(leftover) <= MAX_GROUP else _pack(leftover))
    return _fit_sizes(parts, minimum)


def _fit_sizes(parts: list[list[str]], minimum: int) -> list[list[str]]:
    """Keep every part between ``minimum`` and ``MAX_GROUP`` after a cut.

    A part that is too small takes one member from a neighbour that can spare it; when no
    neighbour can spare one, it joins a neighbour that has room. Moving a member is
    preferred to joining, because joining two pieces of twelve would publish thirteen."""
    out = [list(part) for part in parts if part]
    split: list[list[str]] = []
    for part in out:
        split.extend([part] if len(part) <= MAX_GROUP else _pack(part))
    out = split
    for index, part in enumerate(out):
        while len(part) < minimum:
            donors = [i for i in (index - 1, index + 1)
                      if 0 <= i < len(out) and i != index and len(out[i]) > minimum]
            if not donors:
                break
            part.insert(0, out[max(donors, key=lambda i: len(out[i]))].pop())
    merged: list[list[str]] = []
    for part in out:
        if not merged:
            merged.append(part)
            continue
        if len(part) < minimum:
            need = minimum - len(part)
            while need > 0 and len(merged[-1]) > minimum:
                part.insert(0, merged[-1].pop())
                need -= 1
            if len(part) >= minimum:
                merged.append(part)
                continue
            if len(merged[-1]) + len(part) <= MAX_GROUP:
                merged[-1].extend(part)
                continue
        merged.append(part)
    if len(merged) > 1 and len(merged[0]) < minimum:
        first = merged[0]
        need = minimum - len(first)
        while need > 0 and len(merged[1]) > minimum:
            first.append(merged[1].pop(0))
            need -= 1
        if len(first) >= minimum:
            pass
        elif len(merged[1]) + len(first) <= MAX_GROUP:
            first_part = merged.pop(0)
            merged[0][:0] = first_part
    return merged


def _segment_texts(group: dict, part: list[str], index: int, total: int, level: int,
                   subtrees: dict[str, list[str]], names: dict[str, str]) -> tuple[str, str]:
    """A cut part's responsibility and summary, written from its own members (design 2.3).

    Members are named once each, however many inventory ids they cover; the parent
    group's sentence is not repeated, because it describes the whole group."""
    listed: list[str] = []
    for member in part:
        for uid in ([member] if level == 1 else subtrees.get(member) or [member]):
            label = (names.get(uid) or skeleton.symbol_words(uid) or "").strip()
            if label and label not in listed:
                listed.append(label)
    shown = listed[:6]
    listing = ", ".join(f"`{name}`" for name in shown)
    if len(listed) > len(shown):
        listing += f" and {len(listed) - len(shown)} more"
    if not listing:
        listing = f"{len(part)} units"
    return (f"Part {index} of {total} of {group['title']}: it holds {listing}.",
            f"Part {index} of {group['title']}, holding {listing}.")


def _pack(members: list[str], size: int = MAX_GROUP) -> list[list[str]]:
    groups = [members[i:i + size] for i in range(0, len(members), size)]
    while len(groups) > 1 and len(groups[-1]) < MIN_GROUP:
        groups[-1].insert(0, groups[-2].pop())
    return groups


def fallback_groups(chunk: dict, level: int, units: dict, subtrees: dict[str, list[str]],
                    candidates: list[list[str]] | None = None,
                    records: dict[str, dict] | None = None) -> list[dict]:
    """The program's grouping when an answer stays unusable: candidates, else member order.

    Each group gets a program-made title and sentence (``note`` says so)."""
    groups: list[dict] = []
    if level == 1 and candidates:
        parts: list[list[str]] = []
        for candidate in candidates:
            parts.extend([candidate] if len(candidate) <= MAX_GROUP else _pack(candidate))
        merged: list[list[str]] = []
        for part in parts:
            if merged and len(part) < MIN_GROUP:
                merged[-1].extend(part)
            else:
                merged.append(part)
        if len(merged) > 1 and len(merged[-1]) < MIN_GROUP:
            merged[-2].extend(merged.pop())
        for part in merged:
            subtree = [uid for uid in part if uid in units] or part
            record = treename.program_record(units, subtree)
            groups.append({"id": _gid(subtree), "title": record["title"],
                           "capability": record["capability"], "summary": record["summary"],
                           "members": list(part), "subtree": subtree,
                           "note": "program-made group (no usable layer answer)"})
        return groups
    records = records or {}
    for part in _pack(list(chunk["members"])):
        subtree = [u for member in part for u in subtrees.get(member, [])]
        words = skeleton.word_tokens(" ".join(
            f"{records.get(member, {}).get('title') or ''} {records.get(member, {}).get('capability') or ''}"
            for member in part))[:3]
        title = " ".join(word.capitalize() for word in words) or "Group"
        capability = (f"Units around {', '.join(words[:4])} (program-made description)."
                      if words else "A program-made group of neighbouring modules.")
        groups.append({"id": _gid(subtree), "title": title, "capability": capability,
                       "summary": capability, "members": part, "subtree": subtree,
                       "note": "program-made group (no usable layer answer)"})
    return groups


def assemble(levels: list[list[dict]], overview: dict | None, repo: str, edges: list[dict]) -> dict:
    """The layers into the published tree: readable ids, parents, and the root page text.

    ``levels[0]`` is the leaf layer (its groups hold units). The top layer's
    groups hang under one root: the repository itself, whose page is the
    overview. A top layer with a single group becomes that root."""
    if not levels or not levels[0]:
        return treename.empty_tree()
    levels = [list(groups) for groups in levels]
    # Design 2.3: a layer whose group has only one child is skipped. Promote the child
    # into the layer above instead of publishing a node with a single child.
    for index in range(1, len(levels)):
        lower = {group["id"]: group for group in levels[index - 1]}
        promoted: set[str] = set()
        kept: list[dict] = []
        for group in levels[index]:
            child_id = group["members"][0] if len(group["members"]) == 1 else None
            if child_id in lower:
                promoted.add(child_id)
                kept.append(lower[child_id])
            else:
                kept.append(group)
        levels[index] = kept
        levels[index - 1] = [group for group in levels[index - 1] if group["id"] not in promoted]
    levels = [groups for groups in levels if groups]
    top = levels[-1]
    records: dict[str, dict] = {}
    parent_of: dict[str, str | None] = {}
    for index, groups in enumerate(levels):
        for group in groups:
            records[group["id"]] = dict(group)
            if index == 0:
                parent_of.setdefault(group["id"], None)
    for groups in levels[1:]:
        for group in groups:
            for child in group["members"]:
                parent_of[child] = group["id"]
    if len(top) == 1:
        root_id = top[0]["id"]
        records[root_id] = {**records[root_id], "capability": "",
                            "summary": (overview or {}).get("overview") or records[root_id]["summary"]}
        parent_of[root_id] = None
    else:
        root_id = "root"
        records[root_id] = {"id": root_id, "title": repo, "capability": "",
                            "summary": (overview or {}).get("overview") or
                            "The whole repository; the groups below divide the work.",
                            "members": [group["id"] for group in top], "subtree": []}
        for group in top:
            parent_of[group["id"]] = root_id
    children: dict[str, list[str]] = {}
    for node_id, parent in parent_of.items():
        if parent:
            children.setdefault(parent, []).append(node_id)
    for parent, kids in children.items():
        used: set[str] = set()
        for kid in kids:
            record = records[kid]
            title = record.get("title") or kid
            if normalize_title(title) in used:
                hint = next((records[member]["title"] for member in record.get("members") or []
                             if member in records), "")
                if not hint and record.get("subtree"):
                    hint = skeleton.symbol_words(record["subtree"][0])
                base = f"{title} ({hint})" if hint else title
                candidate, extra = base, 2
                while normalize_title(candidate) in used:
                    candidate, extra = f"{base} {extra}", extra + 1
                record["title"] = candidate
                record["note"] = "program-made title (a sibling had the same title)"
                title = candidate
            used.add(normalize_title(title))
    # A promoted child can carry its parent's title; the reader needs two names, not one twice.
    for parent, kids in children.items():
        parent_title = normalize_title(records[parent].get("title") or "")
        if not parent_title:
            continue
        for kid in kids:
            record = records[kid]
            if normalize_title(record.get("title")) != parent_title:
                continue
            hint = next((records[member]["title"] for member in record.get("members") or []
                         if member in records), "")
            if not hint and record.get("subtree"):
                hint = skeleton.symbol_words(record["subtree"][0])
            record["title"] = f"{record['title']} ({hint})" if hint else f"{record['title']} (part)"
            record["note"] = "program-made title (the parent had the same title)"
    nodes = []
    leaf_ids = {group["id"] for group in levels[0]}
    order = [group for groups in levels for group in groups] + ([records[root_id]]
                                                              if root_id == "root" else [])
    for group in order:
        row = {"id": group["id"], "parent": parent_of.get(group["id"]),
               "title": records[group["id"]].get("title") or group["id"],
               "capability": records[group["id"]].get("capability") or "",
               "summary": records[group["id"]].get("summary") or "",
               "unit_ids": sorted(group.get("subtree") or []) if group["id"] in leaf_ids else []}
        if group.get("note"):
            row["note"] = group["note"]
        nodes.append(row)
    tree = treename.Tree(nodes)
    dependencies = treename.dependencies(tree, edges)
    ids = treename.slugs(tree, {node: records[node]["title"] for node in tree.order})
    for node in nodes:
        node["id"], node["parent"] = ids[node["id"]], ids[node["parent"]] if node["parent"] else None
    return {"nodes": nodes, "depends_on": [{**dep, "from": ids[dep["from"]], "to": ids[dep["to"]]}
                                           for dep in dependencies]}
