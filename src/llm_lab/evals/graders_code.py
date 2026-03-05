from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from llm_lab.pipeline.contracts import Output


@dataclass
class Metrics:
    schema_compliance: float
    tool_success_rate: float
    policy_violation_rate: float
    insufficient_evidence_rate: float
    success_rate: float
    citations_valid_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_compliance_rate": self.schema_compliance,
            "tool_success_rate": self.tool_success_rate,
            "policy_violation_rate": self.policy_violation_rate,
            "insufficient_evidence_rate": self.insufficient_evidence_rate,
            "success_rate": self.success_rate,
            "citations_valid_rate": self.citations_valid_rate,
        }


def compute_metrics(output: Output, schema_ok: bool) -> Metrics:
    tool_total = max(1, len(output.tool_results))
    tool_ok = sum(1 for tr in output.tool_results if tr.ok)
    tool_success_rate = tool_ok / tool_total if output.tool_results else 1.0

    policy_violation_rate = 1.0 if output.policy_violations else 0.0
    insufficient_evidence_rate = 1.0 if output.insufficient_evidence else 0.0
    success_rate = 1.0 if output.success else 0.0

    # citations_valid: all citation_ids must exist in evidence chunk_ids
    ev_ids = {e.chunk_id for e in output.evidence}
    citations_valid = all(cid in ev_ids for cid in output.citation_ids)
    citations_valid_rate = 1.0 if citations_valid else 0.0

    return Metrics(
        schema_compliance=1.0 if schema_ok else 0.0,
        tool_success_rate=tool_success_rate,
        policy_violation_rate=policy_violation_rate,
        insufficient_evidence_rate=insufficient_evidence_rate,
        success_rate=success_rate,
        citations_valid_rate=citations_valid_rate,
    )
