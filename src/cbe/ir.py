"""Canonical IR for enrolled Python/TS/JS source.

Knowledge taken from the old cbe-ir/3 SourceUnit/Symbol/Relation/TypedFailure
surface (read in full for the types actually reused) and rewritten onto UTF-8
character spans. The old protocol's capability cells, verification receipts,
and ir_* identity hashes are not carried forward.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class FailureCode(StrEnum):
    BACKEND_UNAVAILABLE = "backend_unavailable"
    INCOMPATIBLE_API = "incompatible_api"
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    INVALID_INPUT = "invalid_input"
    SOURCE_UNAVAILABLE = "source_unavailable"
    CONTENT_HASH_MISMATCH = "content_hash_mismatch"
    PARSE_ERROR = "parse_error"
    BACKEND_ERROR = "backend_error"
    DECODE_ERROR = "decode_error"


class SourceUnitState(StrEnum):
    DISCOVERED = "discovered"
    EXCLUDED = "excluded"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"
    PARSE_ERROR = "parse_error"
    INDEXED = "indexed"


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"
    EXTERNAL = "external"
    UNSUPPORTED = "unsupported"


class ResolutionMethod(StrEnum):
    EXACT = "exact"
    HEURISTIC = "heuristic"
    COMPILER = "compiler"
    DATAFLOW = "dataflow"


@dataclass(frozen=True)
class TypedFailure:
    code: FailureCode
    message: str
    backend_id: str
    language: str
    retryable: bool = False
    details: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "backend_id": self.backend_id,
            "language": self.language,
            "retryable": self.retryable,
            "details": list(self.details),
        }


@dataclass(frozen=True)
class CharSpan:
    """Half-open UTF-8 character interval on the decoded source. CRLF is not rewritten."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"invalid span {self.start}:{self.end}")

    @property
    def length(self) -> int:
        return self.end - self.start

    def overlaps(self, other: CharSpan) -> bool:
        return self.start < other.end and other.start < self.end

    def contains(self, other: CharSpan) -> bool:
        return self.start <= other.start and other.end <= self.end

    def to_dict(self) -> dict[str, int]:
        return {"start": self.start, "end": self.end}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CharSpan:
        return cls(int(payload["start"]), int(payload["end"]))


@dataclass(frozen=True)
class OffsetMap:
    """Byte offset (parser) ↔ character offset (ledger) for one frozen file.

    Original bytes are kept. Decoding is UTF-8. CRLF stays two characters.
    """

    raw: bytes
    text: str
    byte_to_char: tuple[int, ...]
    char_to_byte: tuple[int, ...]

    @classmethod
    def from_bytes(cls, raw: bytes) -> OffsetMap:
        text = raw.decode("utf-8")
        byte_to_char: list[int] = [0] * (len(raw) + 1)
        char_to_byte: list[int] = [0] * (len(text) + 1)
        byte_index = 0
        for char_index, char in enumerate(text):
            encoded = char.encode("utf-8")
            char_to_byte[char_index] = byte_index
            for _ in encoded:
                byte_to_char[byte_index] = char_index
                byte_index += 1
        char_to_byte[len(text)] = len(raw)
        byte_to_char[len(raw)] = len(text)
        return cls(raw=raw, text=text, byte_to_char=tuple(byte_to_char), char_to_byte=tuple(char_to_byte))

    def char_of_byte(self, byte_index: int) -> int:
        if byte_index < 0 or byte_index > len(self.raw):
            raise ValueError(f"byte offset {byte_index} out of range")
        return self.byte_to_char[byte_index]

    def byte_of_char(self, char_index: int) -> int:
        if char_index < 0 or char_index > len(self.text):
            raise ValueError(f"char offset {char_index} out of range")
        return self.char_to_byte[char_index]

    def span_from_bytes(self, start_byte: int, end_byte: int) -> CharSpan:
        return CharSpan(self.char_of_byte(start_byte), self.char_of_byte(end_byte))

    def slice(self, span: CharSpan) -> str:
        return self.text[span.start : span.end]


def line_starts(text: str) -> tuple[int, ...]:
    """Character offsets of each 1-indexed line, keeping CRLF as two characters."""

    starts = [0]
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == "\r" and index + 1 < length and text[index + 1] == "\n":
            index += 2
            starts.append(index)
        elif char in "\n\r":
            index += 1
            starts.append(index)
        else:
            index += 1
    return tuple(starts)


def char_offset(starts: tuple[int, ...], lineno: int, col_offset: int, text_len: int) -> int:
    """Line/column → character offset when ``col_offset`` is already in characters."""

    if lineno < 1:
        return 0
    if lineno - 1 >= len(starts):
        return text_len
    return min(text_len, starts[lineno - 1] + max(0, col_offset))


def ast_point_to_char(
    offsets: OffsetMap,
    starts: tuple[int, ...],
    lineno: int,
    col_offset: int,
) -> int:
    """CPython AST (1-based line, UTF-8 *byte* column) → global character offset.

    ``ast`` stores ``col_offset`` / ``end_col_offset`` as UTF-8 byte offsets on
    that line. Adding them to the line's character start misplaces every
    non-ASCII prefix. Convert through the file byte map instead. CRLF is two
    characters and is not rewritten.
    """

    text_len = len(offsets.text)
    if lineno < 1:
        return 0
    if lineno - 1 >= len(starts):
        return text_len
    line_char_start = starts[lineno - 1]
    line_byte_start = offsets.byte_of_char(line_char_start)
    target_byte = line_byte_start + max(0, col_offset)
    if target_byte >= len(offsets.raw):
        return text_len
    return offsets.char_of_byte(target_byte)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    return sha256_bytes(payload.encode("utf-8"))


def exclusive_sha256(text: str, spans: tuple[CharSpan, ...]) -> str:
    body = "".join(text[span.start:span.end] for span in spans)
    return sha256_text(body)


def canonical_symbol_id(path: str, kind: str, scope: str, anchor: int) -> str:
    """Stable id: path + kind + lexical scope + declaration character anchor.

    Line numbers are not identities. Same-name overloads/closures differ by
    kind and anchor.
    """

    return f"{path}::{kind}::{scope}::{anchor}"


@dataclass
class Symbol:
    id: str
    path: str
    language: str
    kind: str
    name: str
    qualified_name: str
    parent_id: str | None
    span: CharSpan
    exclusive_spans: tuple[CharSpan, ...]
    signature: str
    decorators: tuple[str, ...] = ()
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "language": self.language,
            "kind": self.kind,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "parent_id": self.parent_id,
            "span": self.span.to_dict(),
            "exclusive_spans": [item.to_dict() for item in self.exclusive_spans],
            "signature": self.signature,
            "decorators": list(self.decorators),
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Symbol:
        return cls(
            id=str(payload["id"]),
            path=str(payload["path"]),
            language=str(payload["language"]),
            kind=str(payload["kind"]),
            name=str(payload["name"]),
            qualified_name=str(payload["qualified_name"]),
            parent_id=payload.get("parent_id"),
            span=CharSpan.from_dict(payload["span"]),
            exclusive_spans=tuple(CharSpan.from_dict(item) for item in payload.get("exclusive_spans", [])),
            signature=str(payload.get("signature", "")),
            decorators=tuple(payload.get("decorators") or ()),
            extra=dict(payload.get("extra") or {}),
        )


@dataclass
class Relation:
    id: str
    kind: str
    subject_id: str
    target_id: str | None
    path: str
    span: CharSpan
    status: ResolutionStatus
    method: ResolutionMethod
    confidence: float
    reason: str
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "subject_id": self.subject_id,
            "target_id": self.target_id,
            "path": self.path,
            "span": self.span.to_dict(),
            "status": self.status.value,
            "method": self.method.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Relation:
        return cls(
            id=str(payload["id"]),
            kind=str(payload["kind"]),
            subject_id=str(payload["subject_id"]),
            target_id=payload.get("target_id"),
            path=str(payload["path"]),
            span=CharSpan.from_dict(payload["span"]),
            status=ResolutionStatus(payload["status"]),
            method=ResolutionMethod(payload["method"]),
            confidence=float(payload.get("confidence", 0.0)),
            reason=str(payload.get("reason", "")),
            extra=dict(payload.get("extra") or {}),
        )


@dataclass
class FileRecord:
    path: str
    language: str
    byte_length: int
    char_length: int
    content_hash: str
    decode: str
    state: SourceUnitState
    parser_id: str
    parser_version: str
    parse_failure: dict[str, Any] | None = None
    diagnostics: tuple[str, ...] = ()
    enrolled: bool = True
    exclude_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "language": self.language,
            "byte_length": self.byte_length,
            "char_length": self.char_length,
            "content_hash": self.content_hash,
            "decode": self.decode,
            "state": self.state.value,
            "parser_id": self.parser_id,
            "parser_version": self.parser_version,
            "parse_failure": self.parse_failure,
            "diagnostics": list(self.diagnostics),
            "enrolled": self.enrolled,
            "exclude_reason": self.exclude_reason,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> FileRecord:
        failure = payload.get("parse_failure")
        return cls(
            path=str(payload["path"]),
            language=str(payload["language"]),
            byte_length=int(payload["byte_length"]),
            char_length=int(payload["char_length"]),
            content_hash=str(payload["content_hash"]),
            decode=str(payload.get("decode", "utf-8")),
            state=SourceUnitState(payload["state"]),
            parser_id=str(payload.get("parser_id", "")),
            parser_version=str(payload.get("parser_version", "")),
            parse_failure=dict(failure) if isinstance(failure, dict) else None,
            diagnostics=tuple(payload.get("diagnostics") or ()),
            enrolled=bool(payload.get("enrolled", True)),
            exclude_reason=payload.get("exclude_reason"),
        )


@dataclass
class FileIR:
    record: FileRecord
    symbols: tuple[Symbol, ...]
    relations: tuple[Relation, ...]
    offsets: OffsetMap | None = None
