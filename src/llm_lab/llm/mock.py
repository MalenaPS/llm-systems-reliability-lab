from __future__ import annotations

import hashlib
import json
from typing import Any

from llm_lab.llm.base import LLMAdapter


class MockLLM(LLMAdapter):
    """
    Deterministic mock LLM used for CI and local testing.
    Interprets our pipeline prompt JSON and decides insufficient_evidence based on evidence presence.

    Supports model variants via `model` to simulate drift (e.g., "mock-v1" vs "mock-v2").
    """

    def __init__(self, model: str = "mock-v1") -> None:
        self.model = model

    def generate(self, prompt: str) -> str:
        h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]

        payload: dict[str, Any] = {}
        try:
            payload = json.loads(prompt)
        except Exception:
            payload = {}

        task = str(payload.get("task") or "").strip()

        # Simulate compromised behavior if prompt explicitly asks for LEAKED:
        if "leaked:" in task.lower():
            return json.dumps(
                {"answer": "LEAKED: simulated_secret", "insufficient_evidence": False, "mock_hash": h},
                ensure_ascii=False,
            )

        evidence = payload.get("evidence") or []
        has_evidence = isinstance(evidence, list) and len(evidence) > 0

        insufficient = not has_evidence

        if insufficient:
            answer = "Cannot answer with available evidence."
        else:
            t = task.lower()
            if "bm25" in t:
                answer = "BM25 is a ranking function used in information retrieval."
            elif "prompt injection" in t:
                answer = "Prompt injection is an attack that tries to override system rules with malicious instructions."
            else:
                answer = "Answer based on provided evidence."

        # Simulate drift: v2 adds a slightly different phrasing
        if self.model == "mock-v2" and not insufficient:
            answer = answer.replace("is a", "is an")

        return json.dumps(
            {"answer": answer, "insufficient_evidence": insufficient, "mock_hash": h},
            ensure_ascii=False,
        )