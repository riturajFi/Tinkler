from __future__ import annotations

from fastapi.responses import StreamingResponse

from agent.service import iter_agent_events, run_agent
from tinkler_backend.schemas import AgentRunRequest, AgentRunResponse, serialize_event, serialize_run
from tinkler_backend.sse import encode_sse


def create_agent_run(payload: AgentRunRequest) -> AgentRunResponse:
    run = run_agent(
        payload.cwd,
        request=payload.request,
        max_turns=payload.max_turns,
        model_name=payload.model,
        allow_writes=payload.allow_writes,
    )
    return serialize_run(run)


def stream_agent_run(payload: AgentRunRequest) -> StreamingResponse:
    def event_stream():
        for event in iter_agent_events(
            payload.cwd,
            request=payload.request,
            max_turns=payload.max_turns,
            model_name=payload.model,
            allow_writes=payload.allow_writes,
        ):
            yield encode_sse(serialize_event(event))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
