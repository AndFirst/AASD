import json
import os
from pathlib import Path
from typing import Any


class EventRepository:
    def __init__(self, file_path: str | Path) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event_type: str, payload: dict[str, Any]) -> None:
        entry = {
            "type": str(event_type or "unknown"),
            "payload": payload if isinstance(payload, dict) else {"payload": payload},
        }

        line = json.dumps(entry, ensure_ascii=False)

        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
