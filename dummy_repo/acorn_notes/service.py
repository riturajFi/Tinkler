from __future__ import annotations

from collections import Counter

from acorn_notes.storage import JsonNoteStore, Note


class NoteService:
    def __init__(self, store: JsonNoteStore) -> None:
        self.store = store

    def add_note(self, title: str, tags: list[str]) -> Note:
        notes = self.store.load()
        note = Note(title=title.strip(), tags=sorted({tag.strip() for tag in tags if tag.strip()}))
        notes.append(note)
        self.store.save(notes)
        return note

    def list_notes(self, tag: str | None = None) -> list[Note]:
        notes = self.store.load()
        if not tag:
            return notes
        return [note for note in notes if tag in note.tags]

    def mark_done(self, title: str) -> bool:
        notes = self.store.load()
        updated = False
        for note in notes:
            if note.title == title:
                note.done = True
                updated = True
                break
        if updated:
            self.store.save(notes)
        return updated

    def stats(self) -> dict[str, object]:
        notes = self.store.load()
        tag_counts = Counter(tag for note in notes for tag in note.tags)
        completed = sum(1 for note in notes if note.done)
        return {
            "total_notes": len(notes),
            "completed_notes": completed,
            "top_tags": tag_counts.most_common(3),
        }
