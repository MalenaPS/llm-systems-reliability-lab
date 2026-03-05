from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Tracer:
    events_path: Path

    def emit(self, name: str, **fields: Any) -> None:
        evt = {"ts_ms": int(time.time() * 1000), "name": name, **fields}
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")
