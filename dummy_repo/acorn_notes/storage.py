from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class Note:
    title: str
    tags: list[str]
    done: bool = False


class JsonNoteStore:
    def __init__(self, path: str | Path = "notes.json") -> None:
        self.path = Path(path)

    def load(self) -> list[Note]:
        if not self.path.exists():
            return []

        raw_data = json.loads(self.path.read_text(encoding="utf-8"))
        return [Note(**item) for item in raw_data]

    def save(self, notes: list[Note]) -> None:
        payload = [asdict(note) for note in notes]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
