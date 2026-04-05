from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "tinkler_backend.app:app",
        host=os.environ.get("TINKLER_BACKEND_HOST", "127.0.0.1"),
        port=int(os.environ.get("TINKLER_BACKEND_PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()

