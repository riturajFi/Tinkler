from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent.state import ToolName


class ModelActionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["tool_call", "final_answer"]
    tool_name: ToolName | None = None
    command: str | None = None
    workdir: str | None = None
    timeout_ms: int | None = None
    path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    max_depth: int | None = None
    pattern: str | None = None
    mode: str | None = None
    patch: str | None = None
    message: str | None = Field(
        default=None,
        description="User-facing final answer when no more tool work is needed.",
    )

    @model_validator(mode="after")
    def validate_shape(self) -> "ModelActionModel":
        if self.type == "tool_call":
            if self.tool_name is None:
                raise ValueError("tool_call requires tool_name")
        if self.type == "final_answer" and not (self.message or "").strip():
            raise ValueError("final_answer requires message")
        return self
