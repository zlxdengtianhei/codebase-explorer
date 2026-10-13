"""Offline text token accounting shared by generation and its usage reports."""

from __future__ import annotations

import hashlib
import base64
from functools import lru_cache
from importlib.metadata import version
from importlib.resources import files

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
