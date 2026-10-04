"""An installed runtime must count official o200k tokens without network/cache."""

import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import tiktoken
import tiktoken_ext.openai_public as official

from cbe.token_budget import ENCODING_SHA256, _encoding


def test_offline_fresh_process_matches_official_constructor(tmp_path: Path, monkeypatch) -> None:
    resource = Path(__file__).parents[1] / "src/cbe/data/o200k_base.tiktoken"
    raw = resource.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ENCODING_SHA256
    ranks = {base64.b64decode(token): int(rank)
             for token, rank in (line.split() for line in raw.splitlines())}
    def official_resource(path, expected_hash):
        assert path.endswith("/o200k_base.tiktoken")
        assert expected_hash == ENCODING_SHA256
        return ranks
    monkeypatch.setattr(official, "load_tiktoken_bpe", official_resource)
    expected = tiktoken.Encoding(**official.o200k_base())
    assert _encoding()._pat_str == expected._pat_str
    assert _encoding()._special_tokens == expected._special_tokens
    texts = ["", "def twice(value):\n    return value * 2\n", "中文源码与文档预算。",
             "Unicode 🧪 café svenska åäö 日本語 العربية", "\r\n tabs\t123456789 <|endoftext|>",
             Path(__file__).read_text()]
    reference = [expected.encode_ordinary(text) for text in texts]
    empty_cache = tmp_path / "empty-cache"
    empty_cache.mkdir()
    script = """
import json, socket, sys, tempfile
import tiktoken.load
payload = json.loads(sys.stdin.read())
tempfile.tempdir = payload['empty_cache']
def forbidden(*args, **kwargs):
    raise AssertionError('implicit network/cache dependency')
socket.socket = forbidden
tiktoken.load.read_file_cached = forbidden
from cbe.token_budget import _encoding, count_text_tokens
enc = _encoding()
tokens = [enc.encode_ordinary(text) for text in payload['texts']]
assert [count_text_tokens(text) for text in payload['texts']] == [len(row) for row in tokens]
print(json.dumps(tokens))
"""
    child = subprocess.run([sys.executable, "-c", script],
                           input=json.dumps({"empty_cache": str(empty_cache), "texts": texts}),
                           text=True, capture_output=True, check=True)
    assert json.loads(child.stdout) == reference
    assert list(empty_cache.iterdir()) == []


def test_corrupt_official_resource_is_rejected(monkeypatch) -> None:
    class BrokenResource:
        def joinpath(self, *parts):
            return self
        def read_bytes(self):
            return b"corrupted"
    monkeypatch.setattr("cbe.token_budget.files", lambda package: BrokenResource())
    _encoding.cache_clear()
    try:
        import pytest
        with pytest.raises(ValueError, match="encoding data hash mismatch"):
            _encoding()
    finally:
        _encoding.cache_clear()
