"""Language dispatch over real AST backends. No regex fallback."""

from __future__ import annotations

from pathlib import Path

from cbe.adapters.javascript import JavaScriptAdapter
from cbe.adapters.python import PythonAdapter
from cbe.adapters.typescript import TypeScriptAdapter
from cbe.ir import (
    FailureCode,
    FileIR,
    FileRecord,
    OffsetMap,
    SourceUnitState,
    TypedFailure,
    sha256_bytes,
)

ENROLLED_SUFFIXES = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
}


class ParserSet:
    def __init__(self) -> None:
        self.python = PythonAdapter()
        self.typescript = TypeScriptAdapter()
        self.javascript = JavaScriptAdapter()

    def parse_file(self, repo: Path, relative: str, raw: bytes) -> FileIR | TypedFailure:
        suffix = Path(relative).suffix.lower()
        language = ENROLLED_SUFFIXES.get(suffix)
        if language is None:
            return TypedFailure(
                code=FailureCode.UNSUPPORTED_LANGUAGE,
                message=f"not an enrolled language: {relative}",
                backend_id="parser_set",
                language=suffix or "unknown",
            )
        try:
            offsets = OffsetMap.from_bytes(raw)
        except UnicodeDecodeError as exc:
            return TypedFailure(
                code=FailureCode.DECODE_ERROR,
                message=f"UTF-8 decode failed for {relative}: {exc}",
                backend_id="parser_set",
                language=language,
            )
        digest = sha256_bytes(raw)
        if language == "python":
            return self.python.parse(relative, offsets, digest)
        if language == "typescript":
            return self.typescript.parse(relative, offsets, digest, language=language)
        return self.javascript.parse(relative, offsets, digest, language=language)


def failure_record(
    relative: str,
    language: str,
    raw: bytes,
    failure: TypedFailure,
    *,
    enrolled: bool = True,
) -> FileRecord:
    try:
        char_length = len(raw.decode("utf-8"))
        decode = "utf-8"
    except UnicodeDecodeError:
        char_length = 0
        decode = "failed"
    return FileRecord(
        path=relative,
        language=language,
        byte_length=len(raw),
        char_length=char_length,
        content_hash=sha256_bytes(raw),
        decode=decode,
        state=SourceUnitState.PARSE_ERROR if failure.code is FailureCode.PARSE_ERROR else SourceUnitState.UNSUPPORTED,
        parser_id=failure.backend_id,
        parser_version="",
        parse_failure=failure.to_dict(),
        diagnostics=failure.details,
        enrolled=enrolled,
    )
