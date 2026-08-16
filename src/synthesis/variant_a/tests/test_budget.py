"""EV-14 budget: doc tokens / src tokens, plus sub-INDEX navigation overhead."""

from __future__ import annotations

from pathlib import Path

from src.synthesis.variant_a.budget import CHARS_PER_TOKEN, estimate_tokens, measure_budget


def test_estimate_tokens_is_chars_over_four() -> None:
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcde") == 1
    assert estimate_tokens("abcdefgh") == 2
    assert estimate_tokens("") == 0
    assert CHARS_PER_TOKEN == 4


def test_ratio_and_nav_share_and_flag(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    src = tmp_path / "src"
    (docs / "clus").mkdir(parents=True)
    src.mkdir()
    # 40 chars docs: root 16 + sub-index 8 + detail 16 → tokens 4 / 2 / 4
    (docs / "INDEX.md").write_text("r" * 16, encoding="utf-8")
    (docs / "clus" / "INDEX.md").write_text("s" * 8, encoding="utf-8")
    (docs / "clus" / "DETAIL.md").write_text("d" * 16, encoding="utf-8")
    # 40 chars src → 10 tokens. docs 40 chars → 10 tokens. ratio 1.0 → FLAG
    (src / "a.py").write_text("p" * 40, encoding="utf-8")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "a.cpython-313.py").write_text("x" * 400, encoding="utf-8")

    out = measure_budget(docs, src)
    assert out["doc_tokens"] == 10
    assert out["src_tokens"] == 10
    assert out["ratio"] == 1.0
    assert out["verdict"] == "FLAG"
    assert out["nav"]["n_sub_index"] == 1
    assert out["nav"]["sub_index_tokens"] == 2
    assert out["nav"]["share_of_docs"] == 0.2


def test_in_band_is_pass(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    src = tmp_path / "src"
    docs.mkdir()
    src.mkdir()
    (docs / "INDEX.md").write_text("d" * 20, encoding="utf-8")  # 5 tokens
    (src / "a.py").write_text("s" * 80, encoding="utf-8")  # 20 tokens → 0.25
    out = measure_budget(docs, src)
    assert out["ratio"] == 0.25
    assert out["verdict"] == "PASS"
    assert out["nav"]["n_sub_index"] == 0
    assert out["nav"]["share_of_docs"] == 0.0
