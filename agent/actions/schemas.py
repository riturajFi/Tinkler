from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from agent.state import ToolName


class ModelActionModel(BaseModel):
    type: Literal["tool_call", "final_answer"]
    tool_name: ToolName | None = None
    args: dict[str, Any] | None = None
    message: str | None = Field(
        default=None,
        description="User-facing final answer when no more tool work is needed.",
    )

    @model_validator(mode="after")
    def validate_shape(self) -> "ModelActionModel":
        if self.type == "tool_call":
            if self.tool_name is None:
                raise ValueError("tool_call requires tool_name")
            if self.args is None:
                raise ValueError("tool_call requires args")
        if self.type == "final_answer" and not (self.message or "").strip():
            raise ValueError("final_answer requires message")
        return self
