from __future__ import annotations

import hashlib

from llm_lab.llm.base import LLMAdapter


class MockLLM(LLMAdapter):
    """
    Deterministic mock LLM used for CI and local testing.
    Produces reproducible outputs from prompts.
    """

    def generate(self, prompt: str) -> str:
        h = hashlib.sha256(prompt.encode()).hexdigest()[:8]

        # simple deterministic logic
        if "insufficient_evidence" in prompt.lower():
            return (
                '{"answer":"Cannot answer with available evidence.",'
                '"insufficient_evidence":true,'
                '"mock_hash":"' + h + '"}'
            )

        return (
            '{"answer":"Mock response for prompt.",'
            '"insufficient_evidence":false,'
            '"mock_hash":"' + h + '"}'
        )