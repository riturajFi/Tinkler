from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent.service import AgentEvent, AgentRun


class AgentRunRequest(BaseModel):
    request: str = Field(..., min_length=1)
    cwd: str = "."
    max_turns: int = Field(default=30, ge=1, le=250)
    model: str | None = None
    allow_writes: bool = False


class AgentRunResponse(BaseModel):
    repo_root: str
    request: str
    response: str
    model: str | None
    max_turns: int
    turn_count: int
    stop_reason: str | None
    tool_trace: list[str]
    changed_files: list[str]


class AgentStreamEventPayload(BaseModel):
    type: str
    run_id: str
    sequence: int
    turn_count: int
    max_turns: int
    payload: dict[str, Any] = Field(default_factory=dict)
    node: str | None = None


def serialize_run(run: AgentRun) -> AgentRunResponse:
    return AgentRunResponse(
        repo_root=str(run.repo_root),
        request=run.request,
        response=run.response,
        model=run.model_name,
        max_turns=run.max_turns,
        turn_count=run.turn_count,
        stop_reason=run.stop_reason,
        tool_trace=run.tool_trace,
        changed_files=run.changed_files,
    )


def serialize_event(event: AgentEvent) -> AgentStreamEventPayload:
    return AgentStreamEventPayload(
        type=event.type,
        run_id=event.run_id,
        sequence=event.sequence,
        turn_count=event.turn_count,
        max_turns=event.max_turns,
        payload=event.payload,
        node=event.node,
    )

