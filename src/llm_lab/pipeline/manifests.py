from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class RunManifest:
    run_id: str
    backend: str
    model: str
    case_id: str
    prompt_hash: str
    config_hash: str
    artifacts: dict[str, str]  # file -> sha256

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "backend": self.backend,
            "model": self.model,
            "case_id": self.case_id,
            "prompt_hash": self.prompt_hash,
            "config_hash": self.config_hash,
            "artifacts": self.artifacts,
        }

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")