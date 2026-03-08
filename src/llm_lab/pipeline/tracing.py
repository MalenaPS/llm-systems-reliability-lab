from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Tracer:
    events_path: Path
    run_id: str

    def emit(
        self,
        step: str,
        *,
        event_type: str,
        latency_ms: int | None = None,
        success: bool | None = None,
        error_type: str | None = None,
        **fields: Any,
    ) -> None:
        evt = {
            "timestamp_ms": int(time.time() * 1000),
            "run_id": self.run_id,
            "step": step,
            "event_type": event_type,
            "latency_ms": latency_ms,
            "success": success,
            "error_type": error_type,
            **fields,
        }
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")