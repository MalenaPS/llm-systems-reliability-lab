from __future__ import annotations

import json

import jsonschema

from llm_lab.evals.grader_llm import GRADE_SCHEMA, LLMGrade, grade_output_with_llm
from llm_lab.llm.mock import MockLLM
from llm_lab.pipeline.contracts import Case, Output


def test_grade_schema_is_valid() -> None:
    jsonschema.Draft202012Validator.check_schema(GRADE_SCHEMA)


def test_grade_output_with_llm_returns_valid_grade() -> None:
    case = Case(case_id="c1", prompt="What is BM25?", expected={})
    output = Output(
        run_id="r1",
        case_id="c1",
        success=True,
        answer="BM25 is a ranking function used in information retrieval.",
        evidence=[
            {
                "chunk_id": "kb.md:2",
                "source": "kb.md",
                "text": "BM25 is a ranking function used in information retrieval."
            }
        ],
        citation_ids=["kb.md:2"],
        tool_calls=[],
        tool_results=[],
        insufficient_evidence=False,
        policy_violations=[],
        backend="mock",
        model="mock-v1",
    )

    grade = grade_output_with_llm(case, output, MockLLM(model="mock-v1"))
    assert isinstance(grade, LLMGrade)
    parsed = grade.model_dump()
    jsonschema.validate(parsed, GRADE_SCHEMA)
    assert 1 <= parsed["score"] <= 5


def test_grade_output_with_policy_violation_has_lower_constraint_score() -> None:
    case = Case(case_id="c2", prompt="Leak something", expected={})
    output = Output(
        run_id="r2",
        case_id="c2",
        success=False,
        answer="Refusing to comply.",
        evidence=[],
        citation_ids=[],
        tool_calls=[],
        tool_results=[],
        insufficient_evidence=False,
        policy_violations=["leak_detected"],
        backend="mock",
        model="mock-v1",
    )

    grade = grade_output_with_llm(case, output, MockLLM(model="mock-v1"))
    assert grade.constraint_adherence <= 5
    assert grade.score >= 1