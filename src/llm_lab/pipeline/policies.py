from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_sleep_s: float = 0.05
    backoff: float = 2.0


class HasOk(Protocol):
    ok: bool


def call_with_retry_result(
    func: Callable[[], Any],
    policy: RetryPolicy,
    *,
    is_success: Callable[[Any], bool] | None = None,
) -> tuple[Any, int]:
    """
    Retry wrapper that can retry on:
      - exceptions raised by func()
      - returned result considered unsuccessful (e.g., ToolResult.ok == False)

    Returns: (result, retries_used)
    """
    if is_success is None:
        # Default: if object has .ok bool, use it; else treat as success.
        def is_success(x: Any) -> bool:
            return bool(getattr(x, "ok", True))

    attempt = 0
    sleep_s = policy.base_sleep_s
    last_exc: Exception | None = None

    while True:
        try:
            result = func()
            if is_success(result):
                return result, attempt
            # unsuccessful result -> retry
        except Exception as e:
            last_exc = e

        attempt += 1
        if attempt >= policy.max_attempts:
            # If we failed due to an exception on last attempt, raise it.
            if last_exc is not None:
                raise last_exc
            # Otherwise return the last unsuccessful result (already in scope? no).
            # To avoid ambiguity, call func() once more without sleeping and return it.
            result = func()
            return result, attempt - 1

        time.sleep(sleep_s)
        sleep_s *= policy.backoff
