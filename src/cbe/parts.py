"""Long files: a file over the read limit is read in parts, one reading batch per part.

One rule applies at three levels. A sequence of pieces is cut into consecutive groups
that each fit the budget and are about equal in size. The pieces are the file's units;
a unit over the budget is cut into its slices; a slice over it is cut into its lines
(a line over it, into character spans). A piece of a cut unit is a unit of its own,
named ``<name> (part k of N)``, and no unit is ever split across two parts otherwise.

Each part carries a note for the author: which file, which part, and the names of the
units in the other parts. The note counts against the same limit as the source.

When every piece of a cut unit is explained, one more task writes the whole unit's short
explanation from those pieces alone (the same rule as a tree node reading only its direct
children); the whole is a group unit whose members are the pieces.
"""

from __future__ import annotations

import hashlib
import re

from cbe import batching, checks, symbols
from cbe.token_budget import count_text_tokens

NOTE_SHARE = 20      # the note may take at most 1/20 of the limit
MARGIN_SHARE = 50    # room for token merges across a joint: 1/50 of the limit
MORE = 4             # names left in a note's list when it has to be cut


def even_groups(costs: list[int], budget: int) -> list[list[int]]:
    """Cut indexes into consecutive groups, each within ``budget`` (a lone piece may pass it),
    as equal in size as the pieces allow: the fewest groups that an equal share can fill.
    The same input always gives the same groups."""
    total = sum(costs)
    base = max(1, -(-total // budget))
    for want in range(base, max(base, len(costs)) + 1):
        groups, current, size, closed = [], [], 0, 0
        for index, cost in enumerate(costs):
            aim = (total - closed) / max(1, want - len(groups))
            if current and (size + cost > budget or (len(groups) + 1 < want and size + cost / 2 > aim)):
                groups.append(current)
                closed, current, size = closed + size, [], 0
            current.append(index)
            size += cost
        groups += [current] if current else []
        if len(groups) <= want:
            break
    return groups


def _header(path: str, chunk: dict, last: dict | None = None) -> str:
    return f"==== {path} lines {chunk['start_line']}-{(last or chunk)['end_line']} ====\n"


def source_text(path: str, chunks: list[dict], ids: set[str]) -> str:
    """The source one part puts before the author: its chunks in file order, a header before
    each run of touching chunks so that the line numbers of the symbol list can be found."""
    rows = sorted((c for c in chunks if c["path"] == path and c["id"] in ids),
                  key=lambda c: (c.get("start_byte") or 0, c["start_line"]))
    runs: list[list[dict]] = []
    for chunk in rows:
        if runs and runs[-1][-1].get("end_byte") == chunk.get("start_byte"):
            runs[-1].append(chunk)
        else:
            runs.append([chunk])
    return "".join(_header(path, run[0], run[-1]) + "".join(c["text"] for c in run) + "\n" for run in runs)


def _pieces(text: str, budget: int) -> list[str]:
    """Lines of ``text`` (a line over the budget becomes character spans)."""
    lines = text.split("\n")
    out = []
    for number, line in enumerate(lines):
        line += "\n" if number + 1 < len(lines) else ""
        cost = count_text_tokens(line)
        size = max(1, len(line) * budget // cost) if cost > budget else len(line)
        out += [line[start:start + size] for start in range(0, len(line), size)] if line else []
    return out


def _cut(chunk: dict, budget: int) -> list[dict]:
    """A chunk over the budget as exclusive slices at line ends; others unchanged."""
    if count_text_tokens(chunk["text"]) <= budget:
        return [chunk]
    pieces = _pieces(chunk["text"], budget)
    groups = even_groups([count_text_tokens(p) for p in pieces], budget)
    out, offset, line = [], chunk.get("start_byte") or 0, chunk["start_line"]
    for number, group in enumerate(groups, 1):
        text = "".join(pieces[i] for i in group)
        size, rows = len(text.encode("utf-8")), text.count("\n")
        last = number == len(groups)
        sid = f"{chunk['id']}::p{number}"
        out.append({**chunk, "id": sid, "symbol_id": sid, "name": f"{chunk['name']} (part {number} of {len(groups)})",
                    "text": text, "start_line": line, "start_byte": offset, "end_byte": offset + size,
                    "end_line": chunk["end_line"] if last else line + rows - (text.endswith("\n")),
                    "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
        offset, line = offset + size, line + rows
    return out


def _note(path: str, index: int, count: int, others: list[tuple[int, list[str]]], cap: int) -> str:
    """The author's note for one part; the names of other parts are cut (to ``MORE`` at the
    least per part) until the note fits ``cap`` tokens."""
    def build(shown: int) -> str:
        lists = []
        for number, names in others:
            more = f" (+{len(names) - shown} more)" if len(names) > shown else ""
            lists.append(f"part {number}: {', '.join(names[:shown])}{more}")
        return (f"PART {index} OF {count}: {path} is over the read limit, so it is read in {count} parts, "
                f"each its own task. This task has part {index} only: explain only the symbols listed "
                f"below. A symbol named \"(part i of m)\" is one unit cut for length; explain only its "
                f"piece. Units of the other parts: {'; '.join(lists) or 'none'}.\n")
    shown = max((len(names) for _, names in others), default=0)
    note = build(shown)
    while count_text_tokens(note) > cap and shown > MORE:
        shown = max(MORE, shown // 2)
        note = build(shown)
    return note


def _names(chunks: list[dict], path: str) -> list[str]:
    rows = symbols.symbol_rows(path, symbols.inventory_from_context({"chunks": chunks}, [path])[path]["symbols"])
    return list(dict.fromkeys("module code" if row["kind"] == "module_residual" else row["name"]
                              for row in rows))


def _plan(path: str, chunks: list[dict], limit: int, margin: int) -> tuple[list[dict], list[dict]] | None:
    """(the file's chunks after cutting, its parts) for one margin; ``None`` when one part is enough."""
    probe = _note(path, 1, 99, [(2, _names(chunks, path))], limit // NOTE_SHARE)
    budget = max(1, limit - min(limit // NOTE_SHARE, count_text_tokens(probe)) - margin)
    chunks = [piece for chunk in chunks for piece in _cut(chunk, budget)]

    def cost(chunk: dict) -> int:
        return count_text_tokens(chunk["text"]) + count_text_tokens(_header(path, chunk))
    by_id = {c["id"]: c for c in chunks}
    rows = symbols.symbol_rows(path, symbols.inventory_from_context({"chunks": chunks}, [path])[path]["symbols"])
    atoms: list[tuple[int, int, int, list[str]]] = []  # (row, piece, pieces of the row, chunk ids)
    for number, row in enumerate(rows):
        sizes = [cost(by_id[sid]) for sid in row["ids"]]
        pieces = ([row["ids"]] if sum(sizes) <= budget else
                  [[row["ids"][i] for i in group] for group in even_groups(sizes, budget // 4)])
        atoms += [(number, piece, len(pieces), ids) for piece, ids in enumerate(pieces, 1)]
    atoms.sort(key=lambda atom: min(by_id[sid].get("start_byte") or 0 for sid in atom[3]))
    groups = even_groups([sum(cost(by_id[sid]) for sid in atom[3]) for atom in atoms], budget)
    if len(groups) < 2:
        return None
    for group in groups:  # name each piece of a cut unit; pieces of one unit in one part share a name
        pieces: dict[int, list[int]] = {}
        for i in group:
            pieces.setdefault(atoms[i][0], []).append(atoms[i][1])
        for i in group:
            number, piece, count, ids = atoms[i]
            if count > 1:
                label = f"{min(pieces[number])}-{max(pieces[number])}" if len(pieces[number]) > 1 else f"{piece}"
                for sid in ids:
                    by_id[sid]["name"] = f"{by_id[sid]['name']} (part {label} of {count})"
    members = [[sid for i in group for sid in atoms[i][3]] for group in groups]
    names = [_names([by_id[sid] for sid in ids], path) for ids in members]
    parts = []
    for number, ids in enumerate(members, 1):
        others = [(i, names[i - 1]) for i in range(1, len(members) + 1) if i != number]
        note = _note(path, number, len(members), others, limit // NOTE_SHARE)
        text = source_text(path, chunks, set(ids))
        parts.append({"index": number, "count": len(members), "ids": ids, "note": note,
                      "tokens": count_text_tokens(text) + count_text_tokens(note)})
    return chunks, parts


def split_file(path: str, context: dict, limit: int) -> list[dict]:
    """The parts of one file; its chunks in ``context`` are replaced by the cut ones.

    Part tokens (source text with headers plus note) are at most ``limit``: if a joint
    merges tokens and one part passes it, the budget shrinks by the excess and the file
    is planned again. Returns ``[]`` when the file fits one part."""
    own = [dict(c) for c in context["chunks"] if c["path"] == path]
    margin = limit // MARGIN_SHARE
    for _ in range(50):
        planned = _plan(path, [dict(c) for c in own], limit, margin)
        if planned is None:
            return []
        chunks, parts = planned
        excess = max(part["tokens"] for part in parts) - limit
        if excess <= 0:
            first = next(i for i, c in enumerate(context["chunks"]) if c["path"] == path)
            rest = [c for c in context["chunks"] if c["path"] != path]
            context["chunks"] = rest[:first] + chunks + rest[first:]
            return parts
        margin += excess + 1
    raise batching.BatchingError(f"cannot fit the parts of {path} within {limit} tokens")


def covered_files(modules: list[dict], inventory: dict) -> list[str]:
    """One entry per batch file; a file in parts counts once, and only when its parts hold every
    inventory id exactly once (a file in two batches shows twice)."""
    out, held = [], {}
    for module in modules:
        for path in module["files"]:
            if "part" in module:
                held.setdefault(path, []).extend(module["part"]["ids"])
            else:
                out.append(path)
    return out + [path for path, ids in held.items() if sorted(ids) == sorted(
        symbol["id"] for symbol in inventory[path]["symbols"])]


def split_modules(modules: list[batching.Module], context: dict, limit: int) -> list[batching.Module]:
    """Replace each batch that is one file over ``limit`` by one batch per part."""
    out: list[batching.Module] = []
    for module in modules:
        parts = split_file(module.files[0].path, context, limit) if (
            module.tokens > limit and len(module.files) == 1) else []
        for part in parts or [None]:
            out.append(batching.Module(len(out), module.files, module.bucket, module.title, part))
    return out


# ------------------------------------------------------------ the whole of a cut unit

PIECE = re.compile(r"^(.*) \(part (\d+)(?:-(\d+))? of (\d+)\)$")
WHOLE_CAP = checks.DETAIL_MAX_TOKENS


def find_wholes(units: dict, inventory: dict) -> list[dict]:
    """Cut units whose pieces are all explained: ``{path, kind, name, pieces: [unit ids]}`` each."""
    symbol_of = {s["id"]: s for entry in inventory.values() for s in entry["symbols"]}
    found: dict[tuple, dict] = {}
    for uid, unit in units.items():
        symbol = symbol_of.get(uid)
        match = PIECE.match(symbol["name"]) if symbol and unit.get("kind") != "group" else None
        if match:
            first, last = int(match[2]), int(match[3] or match[2])
            row = found.setdefault((uid.split("::")[0], symbol["kind"], match[1], int(match[4])),
                                   {"labels": set(), "pieces": []})
            row["labels"] |= set(range(first, last + 1))
            row["pieces"].append((first, uid))
    return [{"path": key[0], "kind": key[1], "name": key[2], "pieces": [uid for _, uid in sorted(row["pieces"])]}
            for key, row in sorted(found.items()) if row["labels"] == set(range(1, key[3] + 1))]


def whole_tasks(units: dict, inventory: dict) -> list[dict]:
    """The fields of one ``whole`` task per cut unit that is fully explained: the id of the
    whole (a group unit, never an existing id), its member pieces and what to call it."""
    taken, out = set(units), []
    for whole in find_wholes(units, inventory):
        stem = "grp:" + checks._kebab(whole["name"]) + "-whole"
        uid = next(name for name in (stem, *(f"{stem}-{n}" for n in range(2, 10_000))) if name not in taken)
        taken.add(uid)
        out.append({"unit": uid, "members": whole["pieces"], "path": whole["path"], "name": whole["name"],
                    "symbol_kind": whole["kind"],
                    "title": whole["name"] + (" (module code)" if whole["kind"] == "module_residual" else "")})
    return out


def whole_prompt(task: dict, units: dict, inventory: dict) -> str:
    """The task that writes a cut unit's whole explanation from its pieces' explanations only."""
    symbol_of = {s["id"]: s for entry in inventory.values() for s in entry["symbols"]}
    what = "the code of the file outside its functions and classes" if task["symbol_kind"] == "module_residual" \
        else f"{task['symbol_kind']} {task['name']}"
    lines = [f"You write the overall detail of one unit of {task['path']}: {what}. It was too long to read "
             f"at once, so it was read and explained in {len(task['members'])} pieces. Use ONLY the piece "
             "explanations below; never invent behavior.", "",
             'OUTPUT: exactly one JSON object, no Markdown fences: {"explain":"..."}',
             "Length: 1 to 3 sentences, about 25 to 60 tokens, hard ceiling 100. Start with the subject; say what "
             "the whole does and what it returns or changes, then the one or two conditions that matter most. "
             "Do not list the pieces or retell them.", "", "PIECES (in file order):"]
    for number, uid in enumerate(task["members"], 1):
        symbol = symbol_of[uid]
        lines.append(f"{number}. {symbol['name']} L{symbol['lines'][0][0]}-{symbol['lines'][0][1]}: "
                     + " ".join(units[uid]["explain"].split()))
    return "\n".join(lines)


def check_whole(value: dict) -> None:
    if not isinstance(value.get("explain"), str) or not value["explain"].strip():
        raise ValueError("answer needs a non-empty explain")
    if count_text_tokens(value["explain"]) > WHOLE_CAP:
        raise ValueError(f"explain is over {WHOLE_CAP} tokens; write it shorter")


def normalize_whole(value: dict) -> list[str]:
    """The last attempt's answer, cut at a sentence end when still over the cap."""
    text = value.get("explain")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("answer needs a non-empty explain")
    cut = checks.cut_at_sentence(text, WHOLE_CAP)
    value["explain"] = cut
    return ["explain cut to the length cap"] if cut != text.strip() else []


def whole_unit(task: dict, explain: str) -> dict:
    return {"id": task["unit"], "kind": "group", "title": task["title"], "members": task["members"],
            "explain": explain.strip(), "extras": [], "uncertainties": []}
