"""The default detail instructions every model author receives (design 2.1)."""

import pytest

from cbe.prompts import detail_prompt, gap_detail_prompt


@pytest.fixture
def model_instructions():
    return detail_prompt(["example.py"], {"example.py": {"symbols": []}})


def test_one_detail_for_every_function_method_and_class(model_instructions):
    assert "Write one detail for every function, method and class" in model_instructions
    assert "A tiny one (a getter, a setter, a one-line predicate) gets one short phrase" in model_instructions
    assert "do not skip it" in model_instructions


def test_length_is_bounded_and_follows_the_source(model_instructions):
    assert "1 to 3 sentences, about 25 to 60 tokens" in model_instructions
    assert "Hard ceiling: 100 tokens" in model_instructions
    assert "never more than half the symbol's own source tokens" in model_instructions
    assert "a small symbol still gets about 25 tokens of room" in model_instructions


def test_the_sentence_starts_with_the_subject_and_skips_the_signature(model_instructions):
    assert "Start with the subject" in model_instructions
    assert "Do not restate the signature, parameter names or types" in model_instructions


def test_grouped_units_name_every_member(model_instructions):
    assert "the sentence must name every symbol it covers" in model_instructions
    assert "A grouped unit needs a short `title`" in model_instructions


def test_call_relations_are_not_model_written(model_instructions):
    assert "Do not write call relations" in model_instructions
    assert "never from you" in model_instructions
    assert '"relations"' not in model_instructions


def test_uncertainties_and_extras_need_real_evidence(model_instructions):
    assert "only a real boundary the source does not settle" in model_instructions
    assert '"topic": condition|failure|side_effect|field|contract' in model_instructions


@pytest.mark.parametrize("embed", [True, False])
def test_both_drivers_get_the_same_contract(embed):
    text = detail_prompt(["example.py"], {"example.py": {"symbols": []}}, embed=embed,
                         chunks=[{"id": "example.py::<file>", "path": "example.py",
                                  "text": "answer = 42\n", "start_line": 1, "end_line": 1}])
    assert "DETAIL STYLE:" in text and "Hard ceiling: 100 tokens" in text
    assert ("answer = 42" in text) is embed
    if not embed:
        assert "SOURCE FILES (read each listed file completely" in text


def test_a_gap_fill_prompt_carries_only_the_missing_symbols_and_their_source():
    table = [{"n": 3, "id": "example.py::function::run::0", "path": "example.py",
              "kind": "function", "name": "run", "lines": [[1, 4]]}]
    prompt = gap_detail_prompt(["example.py"], {"example.py": {"symbols": []}}, table,
                               chunks=[{"id": "example.py::function::run::0", "path": "example.py",
                                        "text": "def run():\n    return 1\n",
                                        "start_line": 1, "end_line": 4}])
    assert "SYMBOLS STILL WITHOUT A DETAIL" in prompt
    assert "3 function run" in prompt
    assert "def run():\n    return 1" in prompt
    assert "SOURCE OF THESE SYMBOLS" in prompt
