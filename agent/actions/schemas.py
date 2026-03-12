from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from agent.state import ActionKind


class AgentActionModel(BaseModel):
    kind: ActionKind
    command: str | None = None
    path: str | None = None
    query: str | None = None
    max_depth: int | None = None
    start_line: int | None = None
    end_line: int | None = None
    content: str | None = None

    @model_validator(mode="after")
    def validate_for_kind(self) -> "AgentActionModel":
        if self.kind == "shell_command" and not self.command:
            raise ValueError("shell_command requires command")
        if self.kind in {"read_file", "write_file"} and not self.path:
            raise ValueError(f"{self.kind} requires path")
        if self.kind == "search_files" and not self.query:
            raise ValueError("search_files requires query")
        if self.kind == "write_file" and self.content is None:
            raise ValueError("write_file requires content")
        return self


class DecisionModel(BaseModel):
    summary: str = Field(
        ...,
        description="Current understanding of the repo and task in one or two sentences.",
    )
    action: AgentActionModel
