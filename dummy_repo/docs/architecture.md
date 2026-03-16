# Architecture Notes

Acorn Notes is intentionally simple:

- `cli.py` handles user input and printing
- `service.py` owns note operations and stats logic
- `storage.py` reads and writes JSON on disk

The design favors readability over scale. There is no validation layer, no
locking around writes, and no abstraction for alternate backends.
