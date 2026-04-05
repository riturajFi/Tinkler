from __future__ import annotations

import json

from tinkler_backend.schemas import AgentStreamEventPayload


def encode_sse(event: AgentStreamEventPayload) -> str:
    payload = json.dumps(event.model_dump(), ensure_ascii=True)
    return f"event: {event.type}\ndata: {payload}\n\n"

