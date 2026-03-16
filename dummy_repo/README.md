# Acorn Notes

Acorn Notes is a small Python CLI for managing plain-text notes stored in a
JSON file.

## What It Does

- creates notes with tags
- lists all notes
- filters notes by tag
- prints a short stats summary

## Run It

```bash
python3 -m acorn_notes add "Buy coffee beans" --tags errands,home
python3 -m acorn_notes list
python3 -m acorn_notes stats
```

## Project Shape

- `acorn_notes/cli.py`: CLI argument parsing and command dispatch
- `acorn_notes/storage.py`: JSON persistence layer
- `acorn_notes/service.py`: application logic
- `tests/`: basic storage and service checks
