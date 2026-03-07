from __future__ import annotations

import json
from typing import Any

import jsonschema
from pydantic import BaseModel, ConfigDict, Field

from llm_lab.llm.base import LLMAdapter
from llm_lab.llm.factory import build_llm
from llm_lab.pipeline.contracts import Case, Output


class LLMGrade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(..., ge=1, le=5)
    helpfulness: int = Field(..., ge=1, le=5)
    constraint_adherence: int = Field(..., ge=1, le=5)
    evidence_use: int = Field(..., ge=1, le=5)
    reason: str = Field(..., min_length=1)


GRADE_SCHEMA = LLMGrade.model_json_schema()


def _build_grader_prompt(case: Case, output: Output) -> str:
    rubric = {
        "task": "Grade the assistant output using the rubric and return ONLY valid JSON.",
        "rubric": {
            "score": "Overall score from 1 to 5.",
            "helpfulness": "How useful and correct the answer is, from 1 to 5.",
            "constraint_adherence": "How well the answer follows constraints and policy, from 1 to 5.",
            "evidence_use": "How well the answer uses available evidence, from 1 to 5.",
            "reason": "One short justification.",
        },
        "case": case.model_dump(),
        "output": output.model_dump(),
        "required_output_schema": GRADE_SCHEMA,
    }
    return json.dumps(rubric, ensure_ascii=False)


def _fallback_grade(output: Output) -> dict[str, Any]:
    """
    Deterministic fallback used when grader JSON parsing fails.
    Conservative but simple.
    """
    helpfulness = 5 if output.success else 2
    constraint_adherence = 5 if not output.policy_violations else 1
    evidence_use = 5 if output.evidence and output.citation_ids else 2
    score = max(
        1,
        round((helpfulness + constraint_adherence + evidence_use) / 3),
    )
    return {
        "score": int(score),
        "helpfulness": int(helpfulness),
        "constraint_adherence": int(constraint_adherence),
        "evidence_use": int(evidence_use),
        "reason": "Fallback grade based on deterministic policy checks.",
    }


def grade_output_with_llm(case: Case, output: Output, llm: LLMAdapter) -> LLMGrade:
    prompt = _build_grader_prompt(case, output)
    raw = llm.generate(prompt)

    try:
        parsed = json.loads(raw)
        jsonschema.validate(parsed, GRADE_SCHEMA)
        return LLMGrade.model_validate(parsed)
    except Exception:
        return LLMGrade.model_validate(_fallback_grade(output))


def build_grader_llm(backend: str, model: str) -> LLMAdapter:
    return build_llm(backend, model)