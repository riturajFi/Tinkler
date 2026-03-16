from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from acorn_notes.service import NoteService
from acorn_notes.storage import JsonNoteStore


class NoteServiceTests(unittest.TestCase):
    def test_add_note_and_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "notes.json"
            service = NoteService(JsonNoteStore(store_path))

            service.add_note("Buy coffee", ["home", "errands", "home"])
            service.add_note("Read design doc", ["work"])
            service.mark_done("Buy coffee")

            stats = service.stats()

        self.assertEqual(stats["total_notes"], 2)
        self.assertEqual(stats["completed_notes"], 1)
        self.assertEqual(dict(stats["top_tags"])["home"], 1)

    def test_store_saves_json_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / "notes.json"
            service = NoteService(JsonNoteStore(store_path))
            service.add_note("Draft release notes", ["work"])

            raw = json.loads(store_path.read_text(encoding="utf-8"))

        self.assertEqual(raw[0]["title"], "Draft release notes")
        self.assertEqual(raw[0]["tags"], ["work"])
