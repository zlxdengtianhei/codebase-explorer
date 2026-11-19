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

from cbe.token_budget import count_text_tokens


def json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped).strip()
    value = json.loads(stripped)
    if not isinstance(value, dict):
        raise ValueError("completion must be one JSON object")
    return value


UNIT_KINDS = {"class", "function", "method", "group", "module_region", "module_residual",
              "type_alias", "interface"}
EXTRA_TOPICS = {"condition", "failure", "side_effect", "field", "contract"}


def overview_limit() -> int:
    """The overview (L0) is the whole-repository page: at most this many tokens."""
    return 500


def check_overview(value: dict[str, Any], limit: int = 500) -> None:
    text = value.get("overview")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("overview must be a nonempty string")
    if count_text_tokens(text) > limit:
        raise ValueError(f"overview must be at most {limit} tokens")


def normalize_overview(value: Any, limit: int = 500) -> list[str]:
    if not isinstance(value, dict):
        raise ValueError("overview result is not a JSON object")
    flags: list[str] = []
    text = value.get("overview")
    if not isinstance(text, str):
        text = _as_text(text)
        flags.append("overview was not a string; converted to text")
    text = text.strip()
    if not text:
        raise ValueError("overview result has no overview")
    if count_text_tokens(text) > limit:
        words = text.split()
        while words and count_text_tokens(" ".join(words) + "…") > limit:
            words.pop()
        flags.append(f"overview trimmed to {limit} tokens")
        text = " ".join(words).rstrip(",;:") + "…"
    value["overview"] = text
    return flags


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

#: Every function, method and class must have a detail; a symbol of these kinds that
#: no unit explains is a gap to re-ask (a tiny one gets a one-phrase unit).
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


def _group_id(title: Any, rows: list[dict], taken: set[str]) -> str:
    """A group unit's id, readable at a glance: the member symbols it explains.

    ``grp:debounce-and-debounced`` says what the page is about; the file-stem slug
    (``grp:general.ts-debounce-helpers``) did not. Falls back to the author's title, then
    to the first symbol, when the members have no name."""
    names = [_kebab(row.get("name") or "") for row in rows]
    names = [name for name in names if name]
    # ``Pool`` and ``Pool.submit`` are one reading, not two: keep the longer name.
    names = [name for name in names
             if not any(name != other and name in other.split("-") and len(other) > len(name)
                        for other in names)]
    names = list(dict.fromkeys(names))
    parts = [name.split("-") for name in names]
    # ``cJSON_CreateNull``/``cJSON_CreateTrue`` share a prefix that says nothing new.
    shared = 0
    while len(parts) > 1 and all(len(part) > shared + 1 for part in parts) \
            and len({part[shared] for part in parts}) == 1:
        shared += 1
    base = "-and-".join("-".join(part[shared:]) for part in parts[:3]) if names else ""
    if len(base) > 48:  # a long type name still has to read as a name, not a fragment
        base = base[:48].rsplit("-", 1)[0] or base[:48]
        if base.endswith("-and"):
            base = base[:-4]
    if not base:
        base = _kebab(title) if isinstance(title, str) else ""
    base = base or _kebab(rows[0]["name"]) or "group"
    stem = f"grp:{base}"
    uid, count = stem, 1
    while uid in taken:
        count += 1
        uid = f"{stem}-{count}"
    return uid


def _decode_unit(raw: dict[str, Any], rows: list[dict], taken: set[str]) -> dict[str, Any]:
    """The internal unit for one answer unit whose ``h`` and ``explain`` are valid.

    ``folded`` holds the other inventory ids of the same symbol: the grammar's parts
    of one declaration, and a file's leftover regions (design 2.1: one detail per
    symbol, one per file for what is left)."""
    first = rows[0]
    if len(rows) == 1:
        unit: dict[str, Any] = {"id": first["id"], "kind": first["kind"]}
        if len(first.get("ids") or []) > 1:
            unit["folded"] = [sid for sid in first["ids"] if sid != first["id"]]
    else:
        unit = {"id": _group_id(raw.get("title"), rows, taken), "kind": "group",
                "members": [row["id"] for row in rows]}
        folded = [sid for row in rows for sid in row.get("ids") or [] if sid not in unit["members"]]
        if folded:
            unit["folded"] = folded
    unit["explain"] = raw["explain"].strip()
    unit["extras"] = [{"topic": _normalize_choice(extra.get("topic"), EXTRA_TOPICS, "contract")[0],
                       "note": extra["note"].strip()}
                      for extra in raw.get("extras") or []
                      if isinstance(extra, dict) and isinstance(extra.get("note"), str) and extra["note"].strip()]
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
        unit = _decode_unit(raw, symbols, taken_ids)
        taken_symbols |= {row["id"] for row in symbols}
        taken_ids.add(unit["id"])
        out.units.append(unit)
    if isinstance(payload.get("notes"), str):
        out.notes = payload["notes"].strip()
    return out


def find_gaps(table: list[dict], units: list[dict[str, Any]]) -> list[dict]:
    """Symbols no unit mentions: every function, method and class (a tiny one gets a
    one-phrase unit). Constants and module regions are indexed without prose."""
    done = covered_ids(units, table)
    return [row for row in table if row["id"] not in done and row["kind"] in GAP_KINDS]


def assemble_details(table: list[dict], units: list[dict[str, Any]], *, notes: str = "") -> dict[str, Any]:
    """The internal payload: units plus a complete ``dispositions`` map.

    A symbol inside a unit is ``unit`` (the unit is the symbol) or ``grouped``;
    every other symbol is ``index_only``."""
    dispositions: dict[str, dict[str, Any]] = {}
    for unit in units:
        if unit["kind"] == "group":
            for sid in [*unit["members"], *(unit.get("folded") or [])]:
                dispositions[sid] = {"how": "grouped", "unit": unit["id"]}
        else:
            for sid in [unit["id"], *(unit.get("folded") or [])]:
                dispositions[sid] = {"how": "unit", "unit": unit["id"]}
    for row in table:
        # A row may stand for several inventory ids (one symbol's parts, a file's leftover
        # regions); every one of them gets the row's disposition, explained or not.
        for sid in [row["id"], *(row.get("ids") or [])]:
            dispositions.setdefault(sid, {"how": "index_only", "unit": None, "reason": NOT_EXPLAINED})
    payload: dict[str, Any] = {"units": units, "dispositions": dispositions}
    if notes:
        payload["batch_notes"] = notes
    return payload


# ------------------------------------------------------- detail length caps

DETAIL_MAX_TOKENS = 100        # hard ceiling for one unit's explanation that has branches
DETAIL_PLAIN_MAX_TOKENS = 60   # ceiling for a unit whose own source shows no branch
DETAIL_MIN_TOKENS = 25         # a small function still gets about this much room
DETAIL_TARGET = (25, 60)       # the range a normal detail should fall in

#: What counts as a branch in one language: a construct that makes the unit do different
#: things on different input. Each pattern is matched against the unit's own source text.
#: A language missing here gets ``DETAIL_MAX_TOKENS``: the program cannot tell whether that
#: source branches, so it does not hold the answer to the plain cap.
BRANCH_PATTERNS: dict[str, tuple[str, ...]] = {
    "python": (
        r"^[ \t]*(?:if|elif|else|except|finally|match|case)\b",
        r"\bif\b[^:\n]*\belse\b",                          # a conditional expression
        r"def[ \t]+[A-Za-z_]\w*[ \t]*\([^)]*=[^)=]",           # a default argument
    ),
    "javascript": (
        r"^[ \t]*(?:if|else|switch|case|catch|finally|try|for|while|do)\b",
        r"\?[^\n:]*:",                                       # a conditional expression
        r"\?\?",                                             # nullish choice
        r"\([^)]*=[^)=,]",                                   # a default parameter
    ),
    "typescript": (
        r"^[ \t]*(?:if|else|switch|case|catch|finally|try|for|while|do)\b",
        r"\?[^\n:]*:",
        r"\?\?",
        r"\([^)]*=[^)=,]",
    ),
    "java": (
        r"^[ \t]*(?:if|else|switch|case|catch|finally|try|for|while|do)\b",
        r"\?[^\n:]*:",
    ),
    "go": (
        r"^[ \t]*(?:if|else|switch|case|select|for)\b",
    ),
    "ruby": (
        r"^[ \t]*(?:if|elsif|else|unless|case|when|rescue|ensure)\b",
        r"\?[^\n:]*:",
        r"def[ \t]+[\w.]+[ \t]*\([^)]*=[^)=]",
    ),
    "c": (
        r"^[ \t]*(?:if|else|switch|case|catch|try|do)\b",
        r"\?[^\n:]*:",
        r"\([^)]*=[^)=,]",
    ),
    "cpp": (
        r"^[ \t]*(?:if|else|switch|case|catch|try|do)\b",
        r"\?[^\n:]*:",
        r"\([^)]*=[^)=,]",
    ),
    "c_sharp": (
        r"^[ \t]*(?:if|else|switch|case|catch|finally|try|for|foreach|while|do)\b",
        r"\?[^\n:]*:",
        r"\?\?",
        r"\([^)]*=[^)=,]",
    ),
    "kotlin": (
        r"^[ \t]*(?:if|else|when|try|catch|finally|for|while|do)\b",
        r"\?:",                                             # the Elvis operator
        r"\([^)]*=[^)=,]",
    ),
    "rust": (
        r"^[ \t]*(?:if|else|match|while|for|loop)\b",
        r"\.\s*(?:unwrap_or|unwrap_or_else|unwrap_or_default)\b",
    ),
    "php": (
        r"^[ \t]*(?:if|else|elseif|switch|case|catch|finally|try|foreach|for|while)\b",
        r"\?[^\n:]*:",
        r"\([^)]*=[^)=,]",
    ),
    "swift": (
        r"^[ \t]*(?:if|else|switch|case|guard|catch|defer|for|while)\b",
        r"\?[^\n:]*:",
        r"\?\?",
        r"\([^)]*=[^)=,]",
    ),
}
BRANCH_PATTERNS["tsx"] = BRANCH_PATTERNS["typescript"]


def source_branches(text: str, language: str) -> bool:
    """Does this source text show a branch, in a language the program can read?

    An unknown language answers True, so its cap stays ``DETAIL_MAX_TOKENS``."""
    patterns = BRANCH_PATTERNS.get(language)
    if patterns is None:
        return True
    return any(re.search(pattern, text, re.MULTILINE) for pattern in patterns)


def detail_cap(text: str, language: str) -> int:
    """A unit's explanation ceiling: 60 tokens when its source has no branch, else 100."""
    return DETAIL_MAX_TOKENS if source_branches(text, language) else DETAIL_PLAIN_MAX_TOKENS


def cut_to_tokens(text: str, cap: int) -> str:
    """Cut prose to ``cap`` tokens at a sentence end when one fits, else at a word end."""
    if count_text_tokens(text) <= cap:
        return text
    best = None
    for match in re.finditer(r"[.!?。！？](?=\s|$)", text):
        if count_text_tokens(text[:match.end()]) <= cap:
            best = match.end()
    if best is not None and best >= len(text) // 3:
        return text[:best].strip()
    words = text.split()
    while words and count_text_tokens(" ".join(words) + "…") > cap:
        words.pop()
    cut = " ".join(words).rstrip(",;:")
    # Prefer dropping the unfinished last clause over ending mid-phrase with "…".
    boundary = max((cut.rfind(mark) for mark in (", ", "; ", " — ")), default=-1)
    if boundary >= len(cut) // 2:
        return cut[:boundary].rstrip() + "."
    return cut + "…"


def cut_at_sentence(text: str, cap: int) -> str:
    """Last-resort cut: the last complete sentence that fits, else a word end with a period.

    It never ends in "…": a reader must not have to guess whether the model stopped or the
    program did. A source sentence longer than the cap has no complete sentence to keep, so
    that case ends at the last whole word."""
    if count_text_tokens(text) <= cap:
        return text.strip()
    best = None
    for match in re.finditer(r"[.!?。！？](?=\s|$)", text):
        if count_text_tokens(text[:match.end()]) <= cap:
            best = match.end()
    if best is not None:
        return text[:best].strip()
    words = text.split()
    while words and count_text_tokens(" ".join(words) + ".") > cap:
        words.pop()
    return " ".join(words).rstrip(",;:—-") + "."


def _covered_ids(unit: dict[str, Any]) -> list[str]:
    """The inventory ids a unit's explanation covers (its own symbol, or its members)."""
    members = [sid for sid in unit.get("members") or [] if sid]
    folded = [sid for sid in unit.get("folded") or [] if sid]
    return ([unit["id"]] if not members else []) + members + folded


def unit_source(unit: dict[str, Any], sources: dict[str, dict]) -> tuple[int, str, str]:
    """(source tokens, source text, language) of one unit, from its covered symbols.

    A unit whose symbols span two languages reports ``""``, which keeps the loose cap."""
    rows = [sources[sid] for sid in _covered_ids(unit) if sid in sources]
    tokens = sum(row.get("tokens") or 0 for row in rows)
    text = "".join(row.get("text") or "" for row in rows)
    languages = {row.get("language") for row in rows if row.get("language")}
    language = languages.pop() if len(languages) == 1 else ""
    return tokens, text, language


def unit_cap(unit: dict[str, Any], sources: dict[str, dict]) -> int:
    """The length ceiling of one unit, from its own source."""
    _, text, language = unit_source(unit, sources)
    return detail_cap(text, language)


def over_long_units(units: list[dict[str, Any]], sources: dict[str, dict]) -> list[dict[str, Any]]:
    """Units whose explanation is above its own cap, longest overage first."""
    over = []
    for unit in units:
        cap = unit_cap(unit, sources)
        used = count_text_tokens(unit.get("explain") or "")
        if used > cap:
            over.append({"id": unit["id"], "cap": cap, "tokens": used})
    return sorted(over, key=lambda row: row["tokens"] - row["cap"], reverse=True)


def apply_shortened(units: list[dict[str, Any]], shortened: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Put a shortened answer in place of the units it rewrites.

    Units are matched by the symbols they cover, not by id: a group's id is program-made
    and the answer only carries symbol numbers. A rewrite for a unit that was not sent
    back is ignored and flagged, so it cannot slip in a change to another unit."""
    by_key = {frozenset(_covered_ids(unit)): unit for unit in units}
    flags: list[str] = []
    for new in shortened:
        old = by_key.get(frozenset(_covered_ids(new)))
        if old is None:
            flags.append(f"shortened answer ignored: no unit covers {', '.join(_covered_ids(new))[:120]}")
            continue
        old["explain"] = new["explain"]
        if new.get("extras"):
            old["extras"] = new["extras"]
        if new.get("uncertainties"):
            old["uncertainties"] = new["uncertainties"]
    return units, flags


def _names_member(name: str, text: str) -> bool:
    """Does the sentence name this member? A method's short name counts too (``Pool.submit``)."""
    lowered = name.lower()
    if lowered in text:
        return True
    tail = lowered.rsplit(".", 1)[-1].split("(")[0].strip()
    return len(tail) >= 4 and tail in text


def cap_details(units: list[dict[str, Any]], sources: dict[str, dict],
                table: list[dict] | None = None) -> tuple[list[str], list[str]]:
    """Last-resort program check on length and named members; it never sends the answer back.

    The cap comes from the source a unit covers (``detail_cap``: 60 tokens without a branch,
    100 with one). A unit still longer than its cap -- the shorter re-ask did not fit it, or
    there was no re-ask -- is cut at the last complete sentence that fits and flagged. A
    grouped unit must name each member in its sentence (the user reads one sentence per
    symbol); a member left unnamed is flagged for RUN.md.

    Returns ``(flags, cut_ids)`` so the run can count how many explanations the program cut."""
    flags: list[str] = []
    cut_ids: list[str] = []
    names = {row["id"]: row["name"] for row in table or []}
    for unit in units:
        members = [sid for sid in unit.get("members") or [] if sid]
        cap = unit_cap(unit, sources)
        text = unit.get("explain") or ""
        called = [names[sid] for sid in members if names.get(sid)]
        sentence = " ".join(text.split()).lower()
        missing = [name for name in called if not _names_member(name, sentence)]
        if count_text_tokens(text) > cap:
            unit["explain"] = cut_at_sentence(text, cap)
            cut_ids.append(unit["id"])
            note = f"{unit['id']}: explain cut at a sentence end to the {cap}-token length cap"
            after = " ".join(unit["explain"].split()).lower()
            dropped = [name for name in called if name not in missing and not _names_member(name, after)]
            if dropped:
                note += f"; the cut dropped the name(s) {', '.join(dropped[:6])}"
            flags.append(note)
        if missing:
            flags.append(f"{unit['id']}: grouped unit does not name {', '.join(missing[:6])}")
    return flags, cut_ids
