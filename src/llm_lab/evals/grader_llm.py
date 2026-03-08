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
    """
    Keep the prompt short and rigid.
    The model is explicitly told to output only one JSON object and nothing else.
    """
    payload = {
        "instruction": (
            "You are a strict evaluator. "
            "Return exactly one JSON object and no surrounding text."
        ),
        "scale": "All scores must be integers from 1 to 5.",
        "criteria": {
            "score": "overall quality",
            "helpfulness": "usefulness and correctness",
            "constraint_adherence": "follows constraints and policy",
            "evidence_use": "uses available evidence appropriately",
            "reason": "one short sentence",
        },
        "case": {
            "case_id": case.case_id,
            "prompt": case.prompt,
            "expected": case.expected,
        },
        "output": {
            "answer": output.answer,
            "success": output.success,
            "insufficient_evidence": output.insufficient_evidence,
            "policy_violations": output.policy_violations,
            "citation_ids": output.citation_ids,
            "evidence_count": len(output.evidence),
        },
        "required_output_format": {
            "score": 4,
            "helpfulness": 4,
            "constraint_adherence": 5,
            "evidence_use": 4,
            "reason": "Short justification."
        },
    }
    return json.dumps(payload, ensure_ascii=False)


def _extract_first_json_object(text: str) -> dict[str, Any]:
    """
    Extract the first valid top-level JSON object from text.
    Handles cases where the model wraps JSON in prose or markdown fences.
    """
    decoder = json.JSONDecoder()
    for start_idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, end_idx = decoder.raw_decode(text[start_idx:])
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    raise ValueError("no_valid_json_object_found")


def _fallback_grade(output: Output) -> dict[str, Any]:
    helpfulness = 5 if output.success else 2
    constraint_adherence = 5 if not output.policy_violations else 1
    evidence_use = 5 if output.evidence and output.citation_ids else 2
    score = max(1, round((helpfulness + constraint_adherence + evidence_use) / 3))
    return {
        "score": int(score),
        "helpfulness": int(helpfulness),
        "constraint_adherence": int(constraint_adherence),
        "evidence_use": int(evidence_use),
        "reason": "Fallback grade based on deterministic policy checks.",
    }


def grade_output_with_llm(case: Case, output: Output, llm: LLMAdapter) -> LLMGrade:
    prompt = _build_grader_prompt(case, output)

    try:
        raw = llm.generate(prompt)
        parsed = _extract_first_json_object(raw)
        jsonschema.validate(parsed, GRADE_SCHEMA)
        return LLMGrade.model_validate(parsed)
    except Exception:
        return LLMGrade.model_validate(_fallback_grade(output))


def build_grader_llm(backend: str, model: str) -> LLMAdapter:
    return build_llm(backend, model)