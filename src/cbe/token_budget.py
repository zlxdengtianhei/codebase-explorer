"""Exact, per-file token accounting for a frozen source and a staged render."""

from __future__ import annotations

import hashlib
import base64
import json
from functools import lru_cache
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
from typing import Any

import tiktoken

TOKENIZER = "o200k_base"
# Official OpenAI encoding bytes; matches tiktoken's o200k_base expected_hash.
# Source: https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken
ENCODING_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
O200K_PATTERN = "|".join([
    r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
    r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
    r"\p{N}{1,3}", r" ?[^\s\p{L}\p{N}]+[\r\n/]*", r"\s*[\r\n]+",
    r"\s+(?!\S)", r"\s+",
])


class RenderBudgetExceeded(ValueError):
    """The staged reader projection exceeds its frozen-source token cap."""


def tokenizer_version() -> str:
    return version("tiktoken")


@lru_cache(maxsize=1)
def _encoding() -> tiktoken.Encoding:
    """Load the official BPE resource without network or user-cache writes.

    Encoding and ordinary-token algorithms remain tiktoken's. The official
    o200k regex, special token IDs and merge ranks are pinned together so an
    empty cache in a network-restricted host gives the same frozen denominator.
    """
    raw = files("cbe").joinpath("data", "o200k_base.tiktoken").read_bytes()
    if hashlib.sha256(raw).hexdigest() != ENCODING_SHA256:
        raise ValueError("bundled o200k_base encoding data hash mismatch")
    # This is the same base64/rank serialization consumed by
    # tiktoken.load.load_tiktoken_bpe, with no implicit cache/network layer.
    ranks = {base64.b64decode(token): int(rank)
             for token, rank in (line.split() for line in raw.splitlines() if line)}
    return tiktoken.Encoding(name=TOKENIZER, pat_str=O200K_PATTERN,
                             mergeable_ranks=ranks,
                             special_tokens={"<|endoftext|>": 199999, "<|endofprompt|>": 200018})


def count_text_tokens(text: str) -> int:
    return len(_encoding().encode_ordinary(text))


def count_source_tokens(inventory: Any, repo: Path) -> int:
    """Count each enrolled file separately after verifying its frozen byte hash.

    The current checkout must still match the inventory. A changed or missing
    source cannot silently change the denominator used to publish a render.
    """

    files = inventory.files if hasattr(inventory, "files") else inventory["files"]
    root = Path(repo).resolve()
    encoding = _encoding()
    total = 0
    for relative, record in sorted(files.items()):
        enrolled = record.enrolled if hasattr(record, "enrolled") else record.get("enrolled", True)
        if not enrolled:
            continue
        expected = record.content_hash if hasattr(record, "content_hash") else record.get("content_hash")
        if not expected:
            raise ValueError(f"missing frozen content_hash for {relative}")
        path = root / relative
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or not path.is_file() or path.is_symlink():
            raise ValueError(f"frozen source file unavailable or outside repo: {relative}")
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise ValueError(f"frozen source hash mismatch for {relative}: expected {expected}, got {actual}")
        try:
            source = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"frozen source is not UTF-8: {relative}") from exc
        total += len(encoding.encode_ordinary(source))
    return total


def count_frozen_source_tokens(ledger: dict) -> int:
    inventory = ledger.get("inventory") or {}
    repo = ledger.get("repo_root") or inventory.get("repo_root")
    if not repo:
        raise ValueError("ledger has no frozen repo_root")
    actual = count_source_tokens(inventory, Path(repo))
    declared = (ledger.get("documentation_policy") or {}).get("source_tokens")
    if declared is not None and int(declared) != actual:
        raise ValueError(f"frozen source token count mismatch: policy={declared}, actual={actual}")
    return actual


def count_markdown_tokens(root: Path) -> int:
    encoding = _encoding()
    return sum(
        len(encoding.encode_ordinary(path.read_text(encoding="utf-8")))
        for path in sorted(Path(root).rglob("*.md"))
    )


def count_published_text_tokens(root: Path) -> int:
    """Count every reader-visible Markdown and JSON file, one file at a time."""
    encoding = _encoding()
    return sum(
        len(encoding.encode_ordinary(path.read_text(encoding="utf-8")))
        for path in sorted(Path(root).rglob("*"))
        if path.is_file() and path.suffix.lower() in {".md", ".json"}
    )


def count_ledger_semantic_tokens(ledger: dict) -> dict[str, int]:
    """Count queryable authored prose, including fragments and historical records.

    Every nonempty field is encoded separately with the same tokenizer as the
    publication gate. Non-string facts use compact, sorted JSON so nested text,
    object keys, and relationships remain visible in this accounting.
    """
    encoding = _encoding()

    def field_tokens(value: Any) -> int:
        if value is None or value == "" or value == [] or value == {}:
            return 0
        text = value if isinstance(value, str) else json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return len(encoding.encode_ordinary(text))

    detail_fields = (
        "behavior", "inputs_outputs", "effects", "failures", "dependencies", "unresolved"
    )
    detail_tokens = sum(
        field_tokens(record.get(field))
        for record in (ledger.get("details") or {}).values()
        for field in detail_fields
    )
    group_body_tokens = sum(
        field_tokens(record.get("body"))
        for record in (ledger.get("groups") or {}).values()
    )
    group_evidence_tokens = sum(
        field_tokens((record.get("extra") or {}).get("evidence_summary"))
        for record in (ledger.get("groups") or {}).values()
    )
    module_tokens = sum(
        field_tokens((item.get("record") or {}).get(field))
        for item in (ledger.get("module_records") or {}).values()
        for field in ("summary", "flow", "uncertainties")
    )
    return {
        "ledger_semantic_tokens": detail_tokens + group_body_tokens + group_evidence_tokens + module_tokens,
        "detail_tokens": detail_tokens,
        "group_body_tokens": group_body_tokens,
        "group_evidence_tokens": group_evidence_tokens,
        "module_tokens": module_tokens,
    }


def describe_render_budget(source_tokens: int, published_tokens: int) -> dict[str, int | float | str]:
    if source_tokens < 0 or published_tokens < 0:
        raise ValueError("token counts must be nonnegative")
    limit = source_tokens // 2
    report: dict[str, int | float | str] = {
        "tokenizer": TOKENIZER,
        "tokenizer_version": tokenizer_version(),
        "source_tokens": source_tokens,
        "published_tokens": published_tokens,
        "limit_tokens": limit,
        "ratio": published_tokens / source_tokens if source_tokens else (0.0 if not published_tokens else float("inf")),
    }
    return report


def check_render_budget(source_tokens: int, published_tokens: int, *,
                        strict: bool = True) -> dict[str, int | float | str]:
    report = describe_render_budget(source_tokens, published_tokens)
    ratio = report["ratio"]
    report["policy"] = "strict" if strict else "report"
    report["target_status"] = (
        "within_target" if ratio <= 0.5 else
        "explainable_overage" if ratio <= 0.55 else "above_guidance"
    )
    if strict and published_tokens > report["limit_tokens"]:
        raise RenderBudgetExceeded(
            f"render token budget exceeded: {published_tokens} published {TOKENIZER} tokens "
            f"> {report['limit_tokens']} allowed (source={source_tokens}); staged render was not published"
        )
    return report
