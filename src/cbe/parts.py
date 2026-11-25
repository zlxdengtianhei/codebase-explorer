"""Long files: a file over the read limit is read in parts, one reading batch per part.

One rule applies at three levels. A sequence of pieces is cut into consecutive groups
that each fit the budget and are about equal in size. The pieces are the file's units;
a unit over the budget is cut into its slices; a slice over it is cut into its lines
(a line over it, into character spans). A piece of a cut unit is a unit of its own,
named ``<name> (part k of N)``, and no unit is ever split across two parts otherwise.

Each part carries a fixed note for the author (which file, which part). The note counts
against the same limit as the source.

A cut unit's pieces point back to it: each piece's chunks carry ``piece = {of, name, first,
last, count}``, ``of`` being the id of the whole (a group unit ``grp:<name>-whole``).

When every piece of a cut unit is explained, one more task writes the whole unit's short
explanation from those pieces alone (the same rule as a tree node reading only its direct
children); the whole is a group unit whose members are the pieces.
"""

from __future__ import annotations

import hashlib

from cbe import batching, checks, symbols
from cbe.token_budget import count_text_tokens

MARGIN_SHARE = 50    # room for token merges across a joint: 1/50 of the limit


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


def _whole_id(name: str, taken: set[str]) -> str:
    """``grp:<name>-whole``, numbered when the name is taken; adds the id to ``taken``."""
    stem = f"grp:{checks._kebab(name) or 'unit'}-whole"
    uid = next(n for n in (stem, *(f"{stem}-{k}" for k in range(2, 100_000))) if n not in taken)
    taken.add(uid)
    return uid


def _with_suffix(chunk: dict, suffix: str) -> dict:
    """The chunk's names with ``suffix`` added: the pieces of one unit stay apart as symbols
    (the inventory merges by qualified name, so that carries the piece label too)."""
    named = {"name": f"{chunk['name']}{suffix}"}
    if chunk.get("qualified_name"):
        named["qualified_name"] = f"{chunk['qualified_name']}{suffix}"
    return named


def _cut(chunk: dict, budget: int, taken: set[str]) -> list[dict]:
    """A chunk over the budget as exclusive slices at line ends, each a piece of the chunk's unit."""
    if count_text_tokens(chunk["text"]) <= budget:
        return [chunk]
    pieces = _pieces(chunk["text"], budget)
    groups = even_groups([count_text_tokens(p) for p in pieces], budget)
    out, offset, line = [], chunk.get("start_byte") or 0, chunk["start_line"]
    whole = _whole_id(chunk["name"], taken)
    for number, group in enumerate(groups, 1):
        text = "".join(pieces[i] for i in group)
        size, rows = len(text.encode("utf-8")), text.count("\n")
        last = number == len(groups)
        sid = f"{chunk['id']}::p{number}"
        out.append({**chunk, "id": sid, "symbol_id": sid,
                    **_with_suffix(chunk, f" (part {number} of {len(groups)})"),
                    "piece": {"of": whole, "name": chunk["name"], "first": number, "last": number, "count": len(groups)},
                    "text": text, "start_line": line, "start_byte": offset, "end_byte": offset + size,
                    "end_line": chunk["end_line"] if last else line + rows - (text.endswith("\n")),
                    "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
        offset, line = offset + size, line + rows
    return out


def _note(path: str, index: int, count: int) -> str:
    """The author's note for one part: fixed text, so its size does not depend on the file."""
    return (f"PART {index} OF {count}: {path} is over the read limit, so it is read in {count} parts, each its "
            f"own task. This task has part {index} only: explain only the symbols listed below; the rest of "
            f"the file is in the other parts. A symbol named \"(part i of m)\" is one unit cut for length; "
            f"explain only its piece.\n")


def _plan(path: str, chunks: list[dict], limit: int, margin: int,
          taken: set[str]) -> tuple[list[dict], list[dict]] | None:
    """(the file's chunks after cutting, its parts) for one margin; ``None`` when one part is enough.
    The ids of the wholes it makes are added to ``taken``."""
    budget = max(1, limit - count_text_tokens(_note(path, 99, 99)) - margin)
    chunks = [piece for chunk in chunks for piece in _cut(chunk, budget, taken)]

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
    wholes: dict[int, str] = {}
    for group in groups:  # name each piece of a cut unit; pieces of one unit in one part are one unit
        pieces: dict[int, list[int]] = {}
        for i in group:
            pieces.setdefault(atoms[i][0], []).append(atoms[i][1])
        for i in group:
            number, _, count, ids = atoms[i]
            if count > 1:
                first, last = min(pieces[number]), max(pieces[number])
                label = f"{first}-{last}" if last > first else f"{first}"
                base = by_id[ids[0]]["name"]
                if number not in wholes:
                    wholes[number] = _whole_id(base, taken)
                whole = wholes[number]
                for sid in ids:
                    by_id[sid].update(_with_suffix(by_id[sid], f" (part {label} of {count})"))
                    by_id[sid]["piece"] = {"of": whole, "name": base, "first": first, "last": last, "count": count}
    members = [[sid for i in group for sid in atoms[i][3]] for group in groups]
    parts = []
    for number, ids in enumerate(members, 1):
        note = _note(path, number, len(members))
        text = source_text(path, chunks, set(ids))
        parts.append({"index": number, "count": len(members), "ids": ids, "note": note,
                      "tokens": count_text_tokens(text) + count_text_tokens(note)})
    return chunks, parts


def split_file(path: str, context: dict, limit: int, taken: set[str] | None = None) -> list[dict]:
    """The parts of one file; its chunks in ``context`` are replaced by the cut ones.

    Part tokens (source text with headers plus note) are at most ``limit``: if a joint
    merges tokens and one part passes it, the budget shrinks by the excess and the file
    is planned again. Returns ``[]`` when the file fits one part."""
    own = [dict(c) for c in context["chunks"] if c["path"] == path]
    margin, taken = limit // MARGIN_SHARE, set() if taken is None else taken
    for _ in range(50):
        used = set(taken)
        planned = _plan(path, [dict(c) for c in own], limit, margin, used)
        if planned is None:
            return []
        chunks, parts = planned
        excess = max(part["tokens"] for part in parts) - limit
        if excess <= 0:
            taken |= used
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
    taken: set[str] = set()  # ids of the wholes made so far, over all files
    for module in modules:
        parts = split_file(module.files[0].path, context, limit, taken) if (
            module.tokens > limit and len(module.files) == 1) else []
        for part in parts or [None]:
            out.append(batching.Module(len(out), module.files, module.bucket, module.title, part))
    return out


# ------------------------------------------------------------ the whole of a cut unit

WHOLE_CAP = checks.DETAIL_MAX_TOKENS


def whole_tasks(units: dict, inventory: dict) -> list[dict]:
    """The fields of one ``whole`` task per cut unit whose pieces are all explained.

    Pieces find their whole through the ``piece`` field their chunks carry (set when the
    unit was cut), never through their names; a whole is asked only when the pieces'
    ``first..last`` labels cover ``1..count``."""
    symbol_of = {s["id"]: s for entry in inventory.values() for s in entry["symbols"]}
    found: dict[str, list[tuple[int, str]]] = {}
    for uid, unit in units.items():
        piece = (symbol_of.get(uid) or {}).get("piece")
        if piece and unit.get("kind") != "group":
            found.setdefault(piece["of"], []).append((piece["first"], uid))
    out = []
    for whole, rows in sorted(found.items()):
        symbol, piece = symbol_of[rows[0][1]], symbol_of[rows[0][1]]["piece"]
        covered = {n for _, uid in rows for n in range(symbol_of[uid]["piece"]["first"], symbol_of[uid]["piece"]["last"] + 1)}
        if covered == set(range(1, piece["count"] + 1)):
            out.append({"unit": whole, "members": [uid for _, uid in sorted(rows)], "path": symbol["id"].split("::")[0],
                        "name": piece["name"], "symbol_kind": symbol["kind"],
                        "title": piece["name"] + (" (module code)" if symbol["kind"] == "module_residual" else "")})
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
    """The whole as a group unit: ``members`` give its source ranges, ``pieces`` mark it as a whole."""
    return {"id": task["unit"], "kind": "group", "title": task["title"], "members": task["members"],
            "pieces": task["members"], "explain": explain.strip(), "extras": [], "uncertainties": []}
