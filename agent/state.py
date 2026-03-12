from __future__ import annotations

from typing import Any, Literal

from typing_extensions import TypedDict

ActionKind = Literal[
    "shell_command",
    "read_file",
    "list_dir",
    "search_files",
    "write_file",
    "finish",
]


class AgentAction(TypedDict, total=False):
    kind: ActionKind
    command: str
    path: str
    query: str
    max_depth: int
    start_line: int
    end_line: int
    content: str


class ToolResult(TypedDict, total=False):
    tool: str
    ok: bool
    summary: str
    input: dict[str, Any]
    data: dict[str, Any]
    error: str | None


class ToolHistoryEntry(TypedDict):
    turn: int
    action: AgentAction
    result: ToolResult


class ObservationEntry(TypedDict):
    turn: int
    text: str


class AgentState(TypedDict):
    request: str
    cwd: str
    repo_root: str
    turn_index: int
    max_turns: int
    working_summary: str
    tool_history: list[ToolHistoryEntry]
    observations: list[ObservationEntry]
    discovered_files: list[str]
    discovered_dirs: list[str]
    likely_entrypoints: list[str]
    repo_facts: dict[str, Any]
    pending_write_path: str | None
    pending_write_content: str | None
    final_response: str | None
    agent_context: str
    next_action: AgentAction | None
    route: str | None
    last_tool_result: ToolResult | None
    should_stop: bool
    stop_reason: str | None


def create_initial_state(
    request: str,
    cwd: str,
    repo_root: str,
    max_turns: int = 12,
) -> AgentState:
    return {
        "request": request,
        "cwd": cwd,
        "repo_root": repo_root,
        "turn_index": 0,
        "max_turns": max_turns,
        "working_summary": "",
        "tool_history": [],
        "observations": [],
        "discovered_files": [],
        "discovered_dirs": [],
        "likely_entrypoints": [],
        "repo_facts": {},
        "pending_write_path": None,
        "pending_write_content": None,
        "final_response": None,
        "agent_context": "",
        "next_action": None,
        "route": None,
        "last_tool_result": None,
        "should_stop": False,
        "stop_reason": None,
    }
