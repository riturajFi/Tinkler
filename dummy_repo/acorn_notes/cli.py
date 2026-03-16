from __future__ import annotations

import argparse

from acorn_notes.service import NoteService
from acorn_notes.storage import JsonNoteStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage small JSON-backed notes.")
    parser.add_argument(
        "--db",
        default="notes.json",
        help="Path to the JSON file used for persistence.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new note.")
    add_parser.add_argument("title")
    add_parser.add_argument("--tags", default="", help="Comma-separated tags.")

    list_parser = subparsers.add_parser("list", help="List notes.")
    list_parser.add_argument("--tag", help="Filter notes by tag.")

    done_parser = subparsers.add_parser("done", help="Mark a note as complete.")
    done_parser.add_argument("title")

    subparsers.add_parser("stats", help="Print summary stats.")
    return parser


def _parse_tags(raw_tags: str) -> list[str]:
    return [tag.strip() for tag in raw_tags.split(",") if tag.strip()]


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    service = NoteService(JsonNoteStore(args.db))

    if args.command == "add":
        note = service.add_note(args.title, _parse_tags(args.tags))
        print(f"Added: {note.title} [{', '.join(note.tags) or 'no tags'}]")
        return

    if args.command == "list":
        notes = service.list_notes(tag=args.tag)
        for note in notes:
            status = "x" if note.done else " "
            tags = ", ".join(note.tags) or "no tags"
            print(f"[{status}] {note.title} ({tags})")
        if not notes:
            print("No notes found.")
        return

    if args.command == "done":
        updated = service.mark_done(args.title)
        print("Marked as done." if updated else "Note not found.")
        return

    if args.command == "stats":
        summary = service.stats()
        print(f"Total notes: {summary['total_notes']}")
        print(f"Completed notes: {summary['completed_notes']}")
        print(f"Top tags: {summary['top_tags']}")


if __name__ == "__main__":
    main()
