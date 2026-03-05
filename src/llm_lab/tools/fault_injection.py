from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class FaultSpec:
    mode: str  # none|error|timeout|invalid_output|transient_error
    transient_failures: int = 0
    sleep_s: float = 0.0


class FaultInjectedTool:
    """
    Wrap a tool callable and inject failures.
    Keeps internal state per instance (for transient failures).
    """

    def __init__(self, func: Callable[..., Any], spec: FaultSpec):
        self.func = func
        self.spec = spec
        self._calls = 0

    def __call__(self, **kwargs: Any) -> Any:
        self._calls += 1

        if self.spec.sleep_s > 0:
            time.sleep(self.spec.sleep_s)

        mode = self.spec.mode

        if mode == "none":
            return self.func(**kwargs)

        if mode == "timeout":
            time.sleep(2.0)
            raise TimeoutError("injected_timeout")

        if mode == "error":
            raise RuntimeError("injected_error")

        if mode == "invalid_output":
            return "NOT_A_LIST_OF_CHUNKS"

        if mode == "transient_error":
            if self._calls <= max(0, self.spec.transient_failures):
                raise RuntimeError("injected_transient_error")
            return self.func(**kwargs)

        raise ValueError(f"unknown fault mode: {mode}")
