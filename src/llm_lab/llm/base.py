from __future__ import annotations

from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    """
    Abstract interface for LLM backends.
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate a response for the given prompt.
        """
        raise NotImplementedError