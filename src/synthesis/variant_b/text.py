"""Deterministic one-liner / behavior cuts. No LLM."""

from __future__ import annotations

import hashlib
import re
import unicodedata

from src.semantic.models import SemanticLedger, SemanticSymbolRecord

_SENTENCE_END_CN = frozenset("。！？")
_SENTENCE_END_EN = frozenset(".!?")
_IDENT_CONTINUE = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
)
_NON_SLUG = re.compile(r"[^a-z0-9]+")


def clip_visible_prefix(text: str, limit: int = 240) -> str:
    if len(text) <= limit:
        return text
    clipped = text[: limit - 1].rstrip()
    if clipped.count("`") % 2 == 1:
        clipped = clipped.rsplit("`", 1)[0].rstrip()
    return clipped + "…"


def first_sentence(text: str) -> str:
    """Cut at a real sentence end, not a qualifier dot or inline-code fragment."""

    normalized = " ".join(text.split())
    in_backtick = False
    cut: int | None = None
    for index, char in enumerate(normalized):
        if char == "`":
            in_backtick = not in_backtick
            continue
        if in_backtick:
            continue
        if char in _SENTENCE_END_CN:
            cut = index + 1
            break
        if char not in _SENTENCE_END_EN:
            continue
        nxt = normalized[index + 1] if index + 1 < len(normalized) else ""
        if char == "." and nxt in _IDENT_CONTINUE:
            continue
        cut = index + 1
        break
    summary = normalized if cut is None else normalized[:cut]
    return clip_visible_prefix(summary)


def one_liner(record: SemanticSymbolRecord) -> str:
    if record.explanation and record.explanation.text.strip():
        return first_sentence(record.explanation.text)
    return "stale/uncovered"


def behavior(record: SemanticSymbolRecord) -> str:
    if not record.explanation or not record.explanation.text.strip():
        return ""
    return record.explanation.text.strip()


def symbol_one_liners(ledger: SemanticLedger) -> dict[str, str]:
    return {symbol_id: one_liner(record) for symbol_id, record in ledger.symbols.items()}


def slug_base(raw: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode()
    slug = _NON_SLUG.sub("-", ascii_value.lower()).strip("-")
    return slug or "module"


def module_slugs(raw_module_ids: set[str]) -> dict[str, str]:
    by_base: dict[str, list[str]] = {}
    for raw in sorted(raw_module_ids):
        by_base.setdefault(slug_base(raw), []).append(raw)
    result: dict[str, str] = {}
    for base, raw_ids in sorted(by_base.items()):
        for raw in raw_ids:
            suffix = ""
            if len(raw_ids) > 1:
                suffix = "-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
            result[raw] = base + suffix
    return result


def symbol_anchor(symbol_id: str) -> str:
    digest = hashlib.sha256(symbol_id.encode("utf-8")).hexdigest()[:16]
    return f"symbol-{digest}"


def tail(symbol_id: str) -> str:
    qualified = symbol_id.split("::", 1)[-1]
    return qualified.rsplit(".", 1)[-1]


def package_docstring(repo_root, relative: str = "__init__.py") -> str:
    from pathlib import Path
    import ast

    path = Path(repo_root) / relative
    if not path.is_file():
        return ""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return ""
    text = ast.get_docstring(tree) or ""
    return first_sentence(text) if text.strip() else ""
