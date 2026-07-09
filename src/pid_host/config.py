from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppConfig:
    port: str = ""
    baudrate: int = 115200
    ch: int = 0
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0
    sp: float = 50.0
    window_seconds: float = 60.0
    raw_frames_visible: bool = False

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> AppConfig:
        source = Path(path)
        if not source.exists():
            return cls()
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return cls()
        allowed: dict[str, Any] = {field: data[field] for field in cls.__dataclass_fields__ if field in data}
        return cls(**allowed)
