from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict


class Case(BaseModel):
    """
    Minimal benchmark case.
    - prompt: user task/instruction
    - expected: optional expectations used by code-based graders (MVP)
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    expected: dict[str, Any] = Field(default_factory=dict)


class EvidenceChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    ok: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class Output(BaseModel):
    """
    Contract-first output of the SUT pipeline.
    Must be JSON-serializable and JSON Schema-validatable.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)

    success: bool
    answer: str = Field(..., min_length=1)

    # Evidence and tool traces for policy + eval.
    evidence: list[EvidenceChunk] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)

    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)

    # Policy signals
    insufficient_evidence: bool = False
    policy_violations: list[str] = Field(default_factory=list)

    # Metadata
    backend: Literal["mock", "ollama", "bedrock"] = "mock"
    model: str = "mock"