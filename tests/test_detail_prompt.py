"""D-41 / p3b: default detail instructions received by every model author."""

import pytest

from cbe.prompts import detail_prompt


@pytest.fixture
def model_instructions():
    return detail_prompt(["example.py"], {"example.py": {"symbols": []}})


def test_first_explanation_sentence_serves_as_summary(model_instructions):
    assert "Do not emit a separate summary field" in model_instructions
    assert "Start explain with a self-contained responsibility sentence of about 25 words or fewer" in model_instructions
    assert "summary (string, optional)" not in model_instructions


def test_length_references_allow_needed_behavior(model_instructions):
    assert "For source under 50 tokens, one or two sentences usually suffice" in model_instructions
    assert "for 50-150 tokens, aim around 70 prose tokens or fewer" in model_instructions
    assert "These are references, not ceilings" in model_instructions
    assert "behavior-changing conditions, failure paths, or side effects" in model_instructions
    assert "for 400-1000, around 240; for larger units, around 330" in model_instructions
    assert "Cover every behavior-changing branch and every failure path" in model_instructions
    assert "let those branches and paths determine the length" in model_instructions
    assert "Information quality takes priority" in model_instructions


def test_classes_explain_responsibility_and_collaboration(model_instructions):
    assert "class-level responsibility and collaboration" in model_instructions
    assert "do not repeat the behavior of members that have their own units in this batch" in model_instructions
    assert "For members folded into the class without their own units, explain their behavior, conditions, and failure paths inside the class unit" in model_instructions
    assert "Include those folded implementations when estimating the class unit's source size" in model_instructions
    assert "never replace behavior with 'see the class unit' or 'see above'" in model_instructions


def test_distinct_cases_and_callee_effects_are_explained(model_instructions):
    assert "State each if/elif branch or distinct case with its own condition and outcome" in model_instructions
    assert "Explain how a called function changes this unit's result, not merely that it is called" in model_instructions
    assert "when that effect is supported by the supplied source" in model_instructions


def test_claims_stay_within_source_evidence_and_unit_scope(model_instructions):
    assert "Do not speculate about callers, decorators, or safety guarantees absent from the source" in model_instructions
    assert "put the specific boundary and its evidence in uncertainties" in model_instructions
    assert "Describe only code within this unit's source scope" in model_instructions
    assert "follow the implementation and point out the discrepancy" in model_instructions
    assert "Keep generation metadata out of prose" in model_instructions


def test_nonbehavioral_regions_are_indexed_without_prose(model_instructions):
    assert "A module region containing only imports or constants must be index_only" in model_instructions


def test_uncertainties_need_source_evidence(model_instructions):
    assert "real boundary supported by specific source evidence" in model_instructions
    assert "omit boilerplate such as 'not visible in this file'" in model_instructions
    assert "An empty uncertainties list is appropriate" in model_instructions


@pytest.mark.parametrize("embed", [True, False])
def test_default_contract_reaches_both_detail_drivers(embed):
    text = detail_prompt(["example.py"], {"example.py": {"symbols": []}}, embed=embed,
                         chunks=[{"path": "example.py", "text": "answer = 42\n",
                                  "start_line": 1, "end_line": 1}],
                         issues=["Preserve the error path"])
    assert "Do not emit a separate summary field" in text
    assert "LENGTH GUIDANCE:" in text
    assert "AVOID DUPLICATION:" in text
    assert "BEHAVIOR AND EVIDENCE:" in text
    assert "For members folded into the class without their own units" in text
    assert "Cover every behavior-changing branch and every failure path" in text
    assert "Preserve the error path" in text
    assert ("answer = 42" in text) is embed
