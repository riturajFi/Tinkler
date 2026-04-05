from __future__ import annotations

from collections.abc import Iterable

from agent.state import ToolName

ALL_TOOLS: tuple[ToolName, ...] = (
    "shell_command",
    "read_file",
    "list_dir",
    "search_files",
    "apply_patch",
)

TOOL_SCHEMAS: dict[ToolName, dict[str, object]] = {
    "shell_command": {
        "name": "shell_command",
        "description": "Run a bounded shell command for exploration, testing, or inspection.",
        "args": {
            "command": "str",
            "workdir": "str",
            "timeout_ms": "int",
        },
    },
    "read_file": {
        "name": "read_file",
        "description": "Read a file or line range without shelling out.",
        "args": {
            "path": "str",
            "start_line": "int | null",
            "end_line": "int | null",
        },
    },
    "list_dir": {
        "name": "list_dir",
        "description": "Inspect repository structure in a bounded way.",
        "args": {
            "path": "str",
            "max_depth": "int",
        },
    },
    "search_files": {
        "name": "search_files",
        "description": "Search file contents or file names. Prefer this over slower shell scans.",
        "args": {
            "pattern": "str",
            "path": "str",
            "mode": '"content" | "files"',
        },
    },
    "apply_patch": {
        "name": "apply_patch",
        "description": "Apply Codex-style patches inside the same loop when file edits are needed.",
        "args": {
            "patch": "str",
        },
    },
}


def build_tool_schemas(allowed_tools: Iterable[ToolName]) -> list[dict[str, object]]:
    unique_tools = tuple(dict.fromkeys(allowed_tools))
    return [TOOL_SCHEMAS[tool_name] for tool_name in unique_tools if tool_name in TOOL_SCHEMAS]


def build_model_system_prompt(allowed_tools: Iterable[ToolName]) -> str:
    tools = tuple(dict.fromkeys(allowed_tools))
    rendered_tools = "\n".join(f"- {tool}" for tool in tools) or "- none"
    edit_rule = (
        "- If files must change, use apply_patch inside the loop after you have enough context."
        if "apply_patch" in tools
        else "- File edits are disabled for this run."
    )
    return f"""You are a repository agent running in a single adaptive LangGraph loop.

Core loop:
1. inspect the repo and current turn state
2. choose exactly one next action
3. if a tool is needed, call one tool
4. after each tool result, decide the next best action
5. stop only when the task is complete

Rules:
- Inspect the repo before making changes.
- Prefer rg-backed search for discovery.
- Read only useful files and the smallest useful slices.
- Always use workdir for shell commands.
- Do not use cd unless there is no reasonable alternative.
- Gather enough context before editing.
- Continue until the task is complete.
- Return exactly one structured action.
- Use final_answer only when no more tool work is needed.
- Do not invent tool results.
{edit_rule}

Available tools:
{rendered_tools}
"""
