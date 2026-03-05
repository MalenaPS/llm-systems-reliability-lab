from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from llm_lab.llm.base import LLMAdapter


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    timeout_s: float = float(os.getenv("OLLAMA_TIMEOUT_S", "60"))
    model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")


class OllamaLLM(LLMAdapter):
    """
    Ollama backend (local, cost 0).
    Assumes Ollama server is available at base_url (default http://localhost:11434).
    """

    def __init__(self, model: str | None = None, base_url: str | None = None, timeout_s: float | None = None):
        cfg = OllamaConfig()
        self.model = model or cfg.model
        self.base_url = (base_url or cfg.base_url).rstrip("/")
        self.timeout_s = timeout_s or cfg.timeout_s

    def generate(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            # Force determinism as much as possible
            "options": {"temperature": 0},
        }

        with httpx.Client(timeout=self.timeout_s) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()

        # Ollama returns {"response": "...", ...}
        if "response" not in data or not isinstance(data["response"], str):
            raise RuntimeError(f"Unexpected Ollama response shape: keys={list(data.keys())}")

        return data["response"]