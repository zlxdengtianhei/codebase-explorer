"""L1 输入面：封闭 allowlist 的符号 packet（闸 1 的载体）。

冻结架构 `FIXED_LAYER_ARCHITECTURE.md` §1 引用的 F1 §2.1 逐字要求：底层 packet 是封闭
allowlist，禁止项 = 白名单的补集（自动完备，不写黑名单）。序列化后的字段集必须**恰好等于**
`ALLOWED_PACKET_FIELDS`，不等即 fail-closed 拒绝派发。

为什么是白名单而不是黑名单：黑名单会腐烂——每加一个新字段就得记得去补一条禁令，而
「记得」正是纪律不该落的地方（`CLAUDE.md` 哲学层 2）。白名单的补集自动完备。

这一层禁止出现的东西（穷举，因为它是补集）：`module_id`、`cluster_id`、`scc_id`、
`pagerank`、`fan_in`/`fan_out`、`callee_explanations`、`cycle_peer_ids`、
`sibling_symbol_ids`、`file_symbol_count`、`public_surface`、`repo_name`、README 摘要、
上层已产出的任何簇名或页面文本。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Final, Mapping, Sequence


_SHA256_RE: Final = re.compile(r"^sha256:[0-9a-f]{64}$")

ALLOWED_PACKET_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "symbol_id",
        "path",
        "kind",
        "span",
        "source_body",
        "content_hash",
        "callee_signatures",
        "language",
        "syntax_diagnostics",
    }
)

#: 补集的一份**可读投影**。它不是判据——判据永远是 `ALLOWED_PACKET_FIELDS` 的补集。
#: 留它只为让报错信息能点名常见越界字段，删掉本常量不改变任何一条闸的行为。
KNOWN_FORBIDDEN_FIELDS: Final[tuple[str, ...]] = (
    "module_id",
    "cluster_id",
    "scc_id",
    "pagerank",
    "fan_in",
    "fan_out",
    "callee_explanations",
    "cycle_peer_ids",
    "sibling_symbol_ids",
    "file_symbol_count",
    "public_surface",
    "repo_name",
    "repo_description",
    "readme_summary",
    "draft_explanation",
    "draft_residual",
    "source_revision",
    "batch_id",
)

ALLOWED_KINDS: Final[frozenset[str]] = frozenset({"function", "method", "class"})


class L1PacketError(ValueError):
    """闸 1 拒绝派发。构造期即抛，不留给调用方判断。"""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise L1PacketError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True)
class L1PacketSymbol:
    """交给 L1 生产者的全部输入。字段集封闭，构造期校验。"""

    symbol_id: str
    path: str
    kind: str
    span: tuple[int, int]
    source_body: str
    content_hash: str
    callee_signatures: tuple[tuple[str, str], ...]
    language: str
    syntax_diagnostics: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.symbol_id, "symbol_id")
        _text(self.path, "path")
        _text(self.language, "language")
        if self.kind not in ALLOWED_KINDS:
            raise L1PacketError(f"kind must be one of {sorted(ALLOWED_KINDS)}: {self.kind!r}")
        if (
            not isinstance(self.span, tuple)
            or len(self.span) != 2
            or any(type(item) is not int for item in self.span)
        ):
            raise L1PacketError("span must be a (start, end) integer pair")
        if self.span[0] < 1 or self.span[1] < self.span[0]:
            raise L1PacketError("span must be a positive inclusive line range")
        if not isinstance(self.source_body, str) or not self.source_body:
            raise L1PacketError("source_body must be a non-empty string")
        normalized_hash = _text(self.content_hash, "content_hash").strip().lower()
        if not _SHA256_RE.fullmatch(normalized_hash):
            raise L1PacketError("content_hash must be a sha256:-prefixed lowercase digest")
        if not isinstance(self.callee_signatures, tuple):
            raise L1PacketError("callee_signatures must be a tuple")
        for pair in self.callee_signatures:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise L1PacketError("callee_signatures items must be (callee_id, signature)")
            _text(pair[0], "callee_id")
            _text(pair[1], "callee_signature")
        if not isinstance(self.syntax_diagnostics, tuple) or any(
            not isinstance(item, str) for item in self.syntax_diagnostics
        ):
            raise L1PacketError("syntax_diagnostics must be a tuple of strings")

    def to_payload(self) -> dict[str, Any]:
        """JSON 原生投影。字段集恰等 `ALLOWED_PACKET_FIELDS`，无例外。"""

        return {
            "symbol_id": self.symbol_id,
            "path": self.path,
            "kind": self.kind,
            "span": [self.span[0], self.span[1]],
            "source_body": self.source_body,
            "content_hash": self.content_hash,
            "callee_signatures": [[callee, signature] for callee, signature in self.callee_signatures],
            "language": self.language,
            "syntax_diagnostics": list(self.syntax_diagnostics),
        }


def assert_packet_fields(rows: Sequence[Mapping[str, object]]) -> None:
    """闸 1：序列化后的字段集必须恰好等于白名单。不等即 fail-closed。

    `rows` 是即将写进 stdin 的符号行。检查两侧：多一个字段是泄漏（地位信息偷渡），
    少一个字段是载体缺失（模型拿不到该看的东西）。两向都拒绝派发。
    """

    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise L1PacketError("packet rows must be a sequence of mappings")
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise L1PacketError(f"packet row {index} is not a mapping")
        present = set(row)
        extra = sorted(present - ALLOWED_PACKET_FIELDS)
        missing = sorted(ALLOWED_PACKET_FIELDS - present)
        if extra or missing:
            raise L1PacketError(
                f"L1 packet row {index} field set is not the closed allowlist; "
                f"forbidden={extra} missing={missing}"
            )


def build_packet_payload(symbols: Sequence[L1PacketSymbol]) -> list[dict[str, Any]]:
    """构造 + 自检一步完成：调用方拿到的 payload 已经过闸 1。"""

    rows = [symbol.to_payload() for symbol in symbols]
    assert_packet_fields(rows)
    return rows


def signature_line(source_body: str, *, fallback: str) -> str:
    """取源码第一行非空非注释作为签名。没有就用 fallback。"""

    for line in source_body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:240]
    return fallback[:240]


def kind_from_record(kind: object) -> str:
    value = getattr(kind, "value", kind)
    text = str(value).lower()
    if text in ALLOWED_KINDS:
        return text
    return "function"
