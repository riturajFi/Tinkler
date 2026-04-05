from __future__ import annotations

from typing import Any

from agent.actions.schemas import ModelActionModel
from agent.state import ModelAction, ToolName


def _require_text(args: dict[str, Any], key: str) -> str:
    value = str(args.get(key, "")).strip()
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _normalize_shell_command(args: dict[str, Any]) -> dict[str, Any]:
    command = _require_text(args, "command")
    workdir = _require_text(args, "workdir")
    timeout_ms = max(1000, min(int(args.get("timeout_ms", 10000)), 60000))
    return {
        "command": command,
        "workdir": workdir,
        "timeout_ms": timeout_ms,
    }


def _normalize_read_file(args: dict[str, Any]) -> dict[str, Any]:
    path = _require_text(args, "path")
    start_line = max(1, int(args.get("start_line", 1)))
    end_line = max(start_line, int(args.get("end_line", start_line + 249)))
    return {
        "path": path,
        "start_line": start_line,
        "end_line": end_line,
    }


def _normalize_list_dir(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path", ".")).strip() or "."
    max_depth = max(0, min(int(args.get("max_depth", 2)), 5))
    return {"path": path, "max_depth": max_depth}


def _normalize_search_files(args: dict[str, Any]) -> dict[str, Any]:
    pattern = _require_text(args, "pattern")
    path = str(args.get("path", ".")).strip() or "."
    mode = str(args.get("mode", "content")).strip() or "content"
    if mode not in {"content", "files"}:
        raise ValueError("mode must be 'content' or 'files'")
    return {
        "pattern": pattern,
        "path": path,
        "mode": mode,
    }


def _normalize_apply_patch(args: dict[str, Any]) -> dict[str, Any]:
    patch = _require_text(args, "patch")
    return {"patch": patch}


def parse_model_action(
    raw: ModelActionModel | dict[str, Any],
    *,
    allowed_tools: tuple[ToolName, ...],
) -> ModelAction:
    action = raw if isinstance(raw, ModelActionModel) else ModelActionModel.model_validate(raw)
    if action.type == "final_answer":
        return {"type": "final_answer", "message": action.message.strip()}

    tool_name = action.tool_name
    if tool_name is None:
        raise ValueError("tool_call requires tool_name")
    if tool_name not in allowed_tools:
        raise ValueError(f"Tool {tool_name!r} is disabled for this run.")

    args = dict(action.args or {})
    if tool_name == "shell_command":
        normalized_args = _normalize_shell_command(args)
    elif tool_name == "read_file":
        normalized_args = _normalize_read_file(args)
    elif tool_name == "list_dir":
        normalized_args = _normalize_list_dir(args)
    elif tool_name == "search_files":
        normalized_args = _normalize_search_files(args)
    elif tool_name == "apply_patch":
        normalized_args = _normalize_apply_patch(args)
    else:
        raise ValueError(f"Unsupported tool: {tool_name}")

    return {
        "type": "tool_call",
        "tool_name": tool_name,
        "args": normalized_args,
    }
