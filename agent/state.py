from __future__ import annotations

from typing import Any, Literal

from typing_extensions import TypedDict

ToolName = Literal[
    "shell_command",
    "read_file",
    "list_dir",
    "search_files",
    "apply_patch",
]

MessageRole = Literal["system", "user", "assistant", "tool"]
ActionType = Literal["tool_call", "final_answer"]


class ToolRecord(TypedDict, total=False):
    tool_name: ToolName
    args: dict[str, Any]
    result: str
    exit_code: int | None
    ok: bool


class MessageRecord(TypedDict, total=False):
    role: MessageRole
    content: str
    name: str
    metadata: dict[str, Any]


class ModelAction(TypedDict, total=False):
    type: ActionType
    tool_name: ToolName | None
    args: dict[str, Any] | None
    message: str | None


class ToolExecutionResult(TypedDict, total=False):
    tool_name: ToolName
    args: dict[str, Any]
    ok: bool
    result: str
    raw_output: str
    exit_code: int | None
    metadata: dict[str, Any]


class AgentState(TypedDict):
    user_request: str
    cwd: str
    repo_root: str
    messages: list[MessageRecord]
    turn_history: list[dict[str, Any]]
    tool_history: list[ToolRecord]
    last_tool_result: str | None
    last_tool_name: ToolName | None
    discovered_files: list[str]
    discovered_dirs: list[str]
    important_files: list[str]
    repo_facts: dict[str, Any]
    pending_patch: str | None
    final_answer: str | None
    turn_count: int
    max_turns: int
    done: bool
    stop_reason: str | None
    turn_context: str
    prompt_messages: list[MessageRecord]
    tool_schemas: list[dict[str, Any]]
    model_action: ModelAction | None
    current_tool_result: ToolExecutionResult | None
    route: str | None
    changed_files: list[str]


def create_initial_state(
    request: str,
    cwd: str,
    repo_root: str,
    max_turns: int = 12,
) -> AgentState:
    return {
        "user_request": request,
        "cwd": cwd,
        "repo_root": repo_root,
        "messages": [{"role": "user", "content": request}],
        "turn_history": [],
        "tool_history": [],
        "last_tool_result": None,
        "last_tool_name": None,
        "discovered_files": [],
        "discovered_dirs": [],
        "important_files": [],
        "repo_facts": {},
        "pending_patch": None,
        "final_answer": None,
        "turn_count": 0,
        "max_turns": max_turns,
        "done": False,
        "stop_reason": None,
        "turn_context": "",
        "prompt_messages": [],
        "tool_schemas": [],
        "model_action": None,
        "current_tool_result": None,
        "route": None,
        "changed_files": [],
    }
