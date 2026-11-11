"""Check whether identifier-like words in an explanation occur in its unit's source."""
from __future__ import annotations

import re


IDENT = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
STOP = {"true", "false", "null", "none", "nil", "self", "this", "void", "int", "str", "string", "bool",
        "boolean", "dict", "list", "tuple", "set", "object", "async", "await", "return", "yield", "if",
        "else", "for", "while", "try", "except", "catch", "finally", "raise", "throw", "class", "def",
        "function", "fn", "func", "import", "from", "export", "const", "let", "var", "static", "public",
        "private", "new", "in", "is", "not", "and", "or", "id", "args", "kwargs", "i.e", "e.g"}


#: An answer is rejected when at least this many of its explanations, and at least this share of
#: them, are suspect. Measured on seven runs: the one wrong answer had 59% suspect, the other 56
#: answers at most 14%.
BATCH_MIN = 3
BATCH_SHARE = 0.3


def idents(text):
    return {t for t in IDENT.findall(text)}


def codey(tok):
    return "_" in tok.strip("_") or re.search(r"[a-z0-9][A-Z]", tok) is not None


def mentions(explain, repo_names):
    ticks = set()
    for span in re.findall(r"`([^`]+)`", explain):
        ticks |= idents(span)
    plain = re.sub(r"`[^`]+`", " ", explain)
    code = {t for t in idents(plain) if codey(t)}
    code |= {m for m in re.findall(r"([A-Za-z_$][A-Za-z0-9_$]*)\(", plain)}
    names = {t for t in idents(plain) if t in repo_names and len(t) >= 3}
    return ticks, code, names


def repo_names(symbol_names) -> frozenset[str]:
    """The valid final dotted name segments in this run's symbol inventory."""
    names = set()
    for symbol_name in symbol_names:
        name = (symbol_name or "").split(".")[-1]
        if IDENT.fullmatch(name or ""):
            names.add(name)
    return frozenset(names)


def ungrounded(explain, source_text, repo_names) -> list[str]:
    """Return missing names only when no mentioned identifier occurs in the source."""
    ok = {t.lower() for t in idents(source_text)}
    ticks, code, names = mentions(explain, repo_names)
    mentioned = {t for t in ticks | code | names if t.lower() not in STOP}
    missing = sorted(t for t in mentioned if t.lower() not in ok)
    return missing if mentioned and len(missing) == len(mentioned) else []
