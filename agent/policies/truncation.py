from __future__ import annotations


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 16:
        return text[:limit]
    return f"{text[:limit]}\n... [truncated]"

