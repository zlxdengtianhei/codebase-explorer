"""Deterministic per-symbol detail tiers for weighted token allocation.

Consumer contract (analyze-stage orchestrator, detail prompt builder, importer):

- call ``assign_detail_priorities(inventory, graph, repo_root)`` once per
  frozen source revision, right after ``build_inventory`` / ``build_graph``;
- key the result by canonical symbol id: fragments spanning several packets
  inherit the canonical tier instead of being re-graded per packet;
- freeze ``tier`` / ``required_fields`` / ``suggested_output_tokens`` /
  ``score`` into the detail task ``extra`` and the task ``input_hash`` so
  recovery or re-dispatch cannot treat an old envelope as the new requirement;
- validate imported details against ``required_fields`` (presence and type;
  only ``behavior`` must be non-empty text — an empty list stays legal when
  the aspect is genuinely absent, matching ``store.DETAIL_FIELDS`` semantics);
- budget output with ``suggested_output_tokens`` (a per-symbol cap hint; the
  run-level ``D_tokens <= S_tokens / 2`` gate stays with the renderer).

Purity: no model calls, no network, no writes. Frozen source text is read
exactly once per file and only after its sha256 matches the inventory record;
any drift raises ``SourceDriftError`` instead of grading stale bytes.

Graph edges are signals, never proof of unimportance: low in-degree adds
nothing, unknown/unresolved call edges can only add score, and risk
behaviours read from the frozen source (explicit exceptions, retry/cancel,
external IO or persistent state, dynamic registration, signal emission) set a ``standard``
floor that test/example identity cannot override — identity may only lower
the default tier. Branch counting is a lexical statement-position
approximation over the frozen exclusive text, which is why it feeds a score
instead of posing as a cyclomatic number.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from cbe.graph import GraphSnapshot
from cbe.inventory import Inventory
from cbe.ir import Symbol

POLICY_VERSION = "weighted-detail-v2"

TIER_BRIEF = "brief"
TIER_STANDARD = "standard"
TIER_DEEP = "deep"

_TIER_ORDER = {TIER_BRIEF: 0, TIER_STANDARD: 1, TIER_DEEP: 2}
_TIER_NAMES = ("brief", "standard", "deep")

# Field names deliberately reuse store.DETAIL_FIELDS so the importer can
# validate tiers without a second schema. brief ⊂ standard ⊂ deep.
REQUIRED_FIELDS_BY_TIER: dict[str, tuple[str, ...]] = {
    TIER_BRIEF: ("behavior",),
    TIER_STANDARD: ("behavior", "effects", "failures"),
    TIER_DEEP: (
        "behavior",
        "inputs_outputs",
        "effects",
        "failures",
        "dependencies",
        "unresolved",
    ),
}

_SUGGESTED_TOKENS_BY_TIER: dict[str, int] = {
    TIER_BRIEF: 120,
    TIER_STANDARD: 300,
    TIER_DEEP: 650,
}
_DEEP_LARGE_LINE_BONUS_TOKENS = 900
_DEEP_LARGE_LINES = 80

STANDARD_SCORE_THRESHOLD = 3
DEEP_SCORE_THRESHOLD = 9

# Containers aggregate their members, so their size signal is the whole span.
_SPAN_SIZED_KINDS = frozenset({"class"})

_PY_BRANCH_RE = re.compile(
    r"(?:^|\n)[ \t]*(?:elif|else|if|for|while|try|except|finally|with|assert|match|case)\b"
)
_JS_BRANCH_RE = re.compile(
    r"(?:^|\n|[;{}(])[ \t]*(?:else|if|for|while|switch|case|catch|finally|try|do)\b"
)

# Risk buckets: any hit floors the tier at `standard` and adds score. Patterns
# are lexical; they only ever raise weight, never lower it. Bare `assert` is a
# guard in production code but the verification mechanism itself inside tests,
# so it counts only for non-test symbols (the always-on patterns are
# `raise`/`throw`).
_RISK_RAISES = (
    re.compile(r"\braise\b"),
    re.compile(r"\bthrow\b"),
)
_RISK_RAISES_ASSERT_ONLY = (
    re.compile(r"\bassert\b"),
)
_RISK_RETRY_CANCEL = (
    re.compile(r"\b(?:retry|retries|retried|cancel|abort|timeout|backoff|deadline)\w*", re.IGNORECASE),
    re.compile(r"\bclear(?:Timeout|Interval)\b"),
    re.compile(r"\bset(?:Timeout|Interval)\b"),
)
_RISK_EXCEPTION_BOUNDARY = (
    re.compile(r"(?:^|\n)[ \t]*(?:except\*?(?:\s|:)|finally\s*:)", re.MULTILINE),
    re.compile(r"\b(?:catch\s*\(|finally\s*\{)"),
)
_RISK_IO_PERSIST = (
    re.compile(r"\bopen\s*\("),
    re.compile(r"\b(?:read|write)_(?:text|bytes)\b"),
    re.compile(r"\bos\.(?:remove|rename|unlink|makedirs|mkdir|write)\b"),
    re.compile(r"\bshutil\b"),
    re.compile(r"\bsubprocess\b"),
    re.compile(r"\bsocket\b"),
    re.compile(r"\brequests\b"),
    re.compile(r"\burllib\b"),
    re.compile(r"\bfetch\s*\("),
    re.compile(r"\blocalStorage\b"),
    re.compile(r"\bsessionStorage\b"),
    re.compile(r"\bindexedDB\b"),
    re.compile(r"\bsqlite"),
    re.compile(r"\bcursor\b"),
    re.compile(r"\bcommit\s*\("),
    re.compile(r"\bflush\s*\("),
    re.compile(r"\bfs\."),
    re.compile(r"\b(?:read|write)File(?:Sync)?\b"),
    re.compile(r"\bprocess\.(?:exit|kill)\b"),
    re.compile(r"\bjson\.(?:dump|load)"),
)
_RISK_DYNAMIC_REGISTRATION = (
    re.compile(r"\bsetattr\b"),
    re.compile(r"\bglobals\s*\("),
    re.compile(r"\blocals\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"\beval\s*\("),
    re.compile(r"\bimportlib\b"),
    re.compile(r"\bregister"),
    re.compile(r"\bregistry\b"),
    re.compile(r"\bplugin"),
    re.compile(r"__getattr__"),
    re.compile(r"__init_subclass__"),
    re.compile(r"\bmetaclass\b"),
    re.compile(r"\bglobalThis\b"),
)
_RISK_SIGNAL_EMIT = (
    re.compile(r"\bsignals\.[A-Za-z_]\w*\.(?:send|send_robust)\s*\("),
)
_RISK_BUCKETS = (
    ("risk:raises", _RISK_RAISES, 1),
    ("risk:exception_boundary", _RISK_EXCEPTION_BOUNDARY, 2),
    ("risk:retry_or_cancel", _RISK_RETRY_CANCEL, 2),
    ("risk:io_or_persist", _RISK_IO_PERSIST, 2),
    ("risk:dynamic_registration", _RISK_DYNAMIC_REGISTRATION, 2),
    ("risk:signal_emit", _RISK_SIGNAL_EMIT, 3),
)


def _combine_patterns(patterns: tuple[re.Pattern[str], ...]) -> re.Pattern[str]:
    """Scan a source interval once per risk bucket instead of once per marker."""
    alternatives = [
        f"(?i:{pattern.pattern})" if pattern.flags & re.IGNORECASE else f"(?:{pattern.pattern})"
        for pattern in patterns
    ]
    return re.compile("|".join(alternatives))


_RISK_BUCKET_SCANNERS = tuple(
    (marker, _combine_patterns(patterns), weight)
    for marker, patterns, weight in _RISK_BUCKETS
)

# Decorators that mark a symbol as a hosted entry point.
_ENTRY_DECORATOR_RE = re.compile(
    r"(?:^|\.)(?:route|get|post|put|patch|delete|command|cli|task|celery_app|app|router|api|endpoint|endpoint_fn)\b",
    re.IGNORECASE,
)

_TEST_PATH_TOKENS = frozenset(
    {
        "tests",
        "test",
        "__tests__",
        "testing",
        "spec",
        "specs",
        "fixtures",
        "fixture",
        "examples",
        "example",
        "samples",
        "sample",
        "testdata",
    }
)


class SourceDriftError(ValueError):
    """Frozen inventory no longer matches the bytes under ``repo_root``."""

    def __init__(self, path: str, detail: str) -> None:
        super().__init__(f"source drift for {path}: {detail}")
        self.path = path
        self.detail = detail


def assign_detail_priorities(
    inventory: Inventory,
    graph: GraphSnapshot,
    repo_root: Path,
) -> dict[str, dict]:
    """Grade every canonical symbol exactly once; pure, deterministic, no model.

    Returns ``{symbol_id: {tier, score, signals, required_fields,
    suggested_output_tokens, policy_version}}`` keyed by the same canonical
    ids as ``inventory.symbols``.
    """

    repo = Path(repo_root).resolve()
    texts = _verified_texts(repo, inventory)
    graph_counts = _graph_counts(graph)
    entries = set(graph.entries or [])
    shared = {item.get("symbol_id") for item in (graph.shared_callees or [])}
    scc_members = {
        symbol_id for component in (graph.sccs or []) for symbol_id in component
    }

    result: dict[str, dict] = {}
    for symbol_id in sorted(inventory.symbols):
        symbol = inventory.symbols[symbol_id]
        result[symbol_id] = _grade_symbol(
            symbol=symbol,
            text=texts.get(symbol.path, ""),
            graph_counts=graph_counts,
            entries=entries,
            shared=shared,
            scc_members=scc_members,
        )
    return result


def _verified_texts(repo: Path, inventory: Inventory) -> dict[str, str]:
    """Decode each symbol-bearing file once, refusing any hash drift."""

    texts: dict[str, str] = {}
    for path in sorted({symbol.path for symbol in inventory.symbols.values()}):
        record = inventory.files.get(path)
        if record is None:
            raise SourceDriftError(path, "path has symbols but no file record in inventory")
        target = repo / path
        if not target.is_file():
            raise SourceDriftError(path, "file is missing under repo_root")
        raw = target.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != record.content_hash:
            raise SourceDriftError(
                path,
                f"content hash mismatch: inventory={record.content_hash} on-disk={digest}",
            )
        texts[path] = raw.decode("utf-8")
    return texts


def _graph_counts(graph: GraphSnapshot) -> dict[str, dict[str, int]]:
    calls_out: dict[str, int] = {}
    calls_in: dict[str, int] = {}
    unknown_calls: dict[str, int] = {}
    for edge in graph.edges or []:
        if edge.get("kind") != "call":
            continue
        subject = edge.get("subject_id")
        target = edge.get("target_id")
        if subject:
            calls_out[str(subject)] = calls_out.get(str(subject), 0) + 1
        if target:
            calls_in[str(target)] = calls_in.get(str(target), 0) + 1
    for edge in graph.unknown_edges or []:
        if edge.get("kind") != "call":
            continue
        if edge.get("status") not in {"unresolved", "ambiguous"}:
            # External builtins/imports are known-outside, not unknown.
            continue
        subject = edge.get("subject_id")
        if subject:
            unknown_calls[str(subject)] = unknown_calls.get(str(subject), 0) + 1
    return {"calls_out": calls_out, "calls_in": calls_in, "unknown_calls": unknown_calls}


def _exclusive_text(symbol: Symbol, text: str) -> str:
    return "".join(text[span.start : span.end] for span in symbol.exclusive_spans)


def _size_text(symbol: Symbol, text: str) -> tuple[str, str]:
    """(text used for sizing, basis name). Containers size by whole span."""

    if symbol.kind in _SPAN_SIZED_KINDS:
        return text[symbol.span.start : symbol.span.end], "span"
    return _exclusive_text(symbol, text), "exclusive"


def _nonblank_lines(chunk: str) -> int:
    return sum(1 for line in chunk.splitlines() if line.strip())


def _branch_count(chunk: str, language: str) -> int:
    if language == "python":
        return len(_PY_BRANCH_RE.findall(chunk))
    return (
        len(_JS_BRANCH_RE.findall(chunk))
        + chunk.count("&&")
        + chunk.count("||")
    )


def _bucket_points(value: int, thresholds: tuple[tuple[int, int], ...]) -> int:
    points = 0
    for floor, points_for_floor in thresholds:
        if value >= floor:
            points = points_for_floor
    return points


def _is_test_identity(symbol: Symbol) -> bool:
    parts = [part.lower() for part in symbol.path.split("/")]
    file_name = parts[-1]
    if file_name == "conftest.py":
        return True
    if any(part in _TEST_PATH_TOKENS for part in parts[:-1]):
        return True
    stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
    if stem.startswith(("test_", "example_")) or stem.endswith(("_test", "_example")):
        return True
    if ".test." in file_name or ".spec." in file_name:
        return True
    return symbol.name.startswith(("test_", "Test"))


def _grade_symbol(
    *,
    symbol: Symbol,
    text: str,
    graph_counts: dict[str, dict[str, int]],
    entries: set[str],
    shared: set,
    scc_members: set[str],
) -> dict:
    size_chunk, basis = _size_text(symbol, text)
    size_lines = _nonblank_lines(size_chunk)
    body = _exclusive_text(symbol, text)
    branches = _branch_count(body, symbol.language)
    calls_out = graph_counts["calls_out"].get(symbol.id, 0)
    calls_in = graph_counts["calls_in"].get(symbol.id, 0)
    unknown_calls = graph_counts["unknown_calls"].get(symbol.id, 0)

    points: dict[str, int] = {}
    points["size"] = _bucket_points(
        size_lines, ((8, 1), (20, 2), (50, 4), (120, 6))
    )
    points["branches"] = _bucket_points(branches, ((3, 1), (6, 2), (12, 4)))
    points["calls_out"] = _bucket_points(calls_out, ((3, 1), (6, 2)))
    points["calls_in"] = _bucket_points(calls_in, ((1, 1), (3, 2)))
    points["unknown_calls"] = _bucket_points(unknown_calls, ((2, 1),))

    test_identity = _is_test_identity(symbol)
    risk_markers: list[str] = []
    risk_points = 0
    for marker, scanner, weight in _RISK_BUCKET_SCANNERS:
        if scanner.search(body):
            risk_markers.append(marker)
            risk_points += weight
    if not test_identity and any(
        pattern.search(body) for pattern in _RISK_RAISES_ASSERT_ONLY
    ):
        risk_markers.append("risk:raises")
        risk_points += 1
    points["risk"] = risk_points

    if symbol.kind == "class":
        points["kind"] = 1
    if symbol.id in entries:
        points["entry"] = 1
        if (
            "risk:exception_boundary" in risk_markers
            and not test_identity
            and symbol.kind in {"function", "method"}
        ):
            points["entry_exception"] = 1
    if symbol.id in scc_members:
        points["cycle"] = 1
    decorator_points = 0
    if symbol.decorators:
        decorator_points = 1
        if any(_ENTRY_DECORATOR_RE.search(name) for name in symbol.decorators):
            decorator_points = 2
    points["decorators"] = decorator_points

    score = sum(points.values())

    raw_tier = (
        TIER_DEEP
        if score >= DEEP_SCORE_THRESHOLD
        else TIER_STANDARD
        if score >= STANDARD_SCORE_THRESHOLD
        else TIER_BRIEF
    )

    signals: set[str] = {
        f"kind={symbol.kind}",
        f"lang={symbol.language}",
        f"size_basis={basis}",
        f"size_lines={size_lines}",
        f"branches={branches}",
    }
    if calls_out:
        signals.add(f"calls_out={calls_out}")
    if calls_in:
        signals.add(f"calls_in={calls_in}")
    if unknown_calls:
        signals.add(f"unknown_call_edges={unknown_calls}")
    if symbol.id in entries:
        signals.add("entry_candidate")
    if symbol.id in shared:
        signals.add("shared_callee")
    if symbol.id in scc_members:
        signals.add("scc_member")
    for decorator in symbol.decorators:
        signals.add(f"decorator={decorator}")
    if symbol.decorators:
        signals.add("decorated")
        if decorator_points >= 2:
            signals.add("entry_decorator")
    for marker in risk_markers:
        signals.add(marker)
    for component, value in points.items():
        if value > 0:
            signals.add(f"points:{component}={value}")

    capped = raw_tier
    if test_identity:
        signals.add("identity:test_or_example")
        capped = _TIER_NAMES[max(0, _TIER_ORDER[raw_tier] - 1)]
        if capped != raw_tier:
            signals.add("test_cap_applied")

    floor = TIER_STANDARD if risk_markers else TIER_BRIEF
    tier = capped if _TIER_ORDER[capped] >= _TIER_ORDER[floor] else floor
    if risk_markers and _TIER_ORDER[tier] < _TIER_ORDER[TIER_STANDARD]:
        # Unreachable by construction; keeps the floor invariant explicit.
        tier = TIER_STANDARD
    if risk_markers:
        signals.add("tier_floor=standard")
        if _TIER_ORDER[tier] > _TIER_ORDER[capped]:
            signals.add("risk_floor_kept")

    tokens = _SUGGESTED_TOKENS_BY_TIER[tier]
    if tier == TIER_DEEP and size_lines >= _DEEP_LARGE_LINES:
        tokens = _DEEP_LARGE_LINE_BONUS_TOKENS

    return {
        "tier": tier,
        "score": int(score),
        "signals": sorted(signals),
        "required_fields": list(REQUIRED_FIELDS_BY_TIER[tier]),
        "suggested_output_tokens": int(tokens),
        "policy_version": POLICY_VERSION,
    }
