from __future__ import annotations

import os
from pathlib import Path

from agent.observability import get_logger, log_node_end, log_node_start
from agent.policies.truncation import truncate_text
from agent.state import AgentState, ToolExecutionResult

ENTRY_LIMIT = 300
OUTPUT_LIMIT = 8000

logger = get_logger(__name__)


def _resolve_dir(repo_root: str, raw_path: str) -> Path:
    root = Path(repo_root).resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (root / raw_path).resolve()
    else:
        candidate = candidate.resolve()
    candidate.relative_to(root)
    if not candidate.exists():
        raise FileNotFoundError(f"Directory not found: {raw_path}")
    if not candidate.is_dir():
        raise ValueError(f"Not a directory: {raw_path}")
    return candidate


def run_list_dir(state: AgentState) -> dict:
    action = state["model_action"] or {}
    args = dict(action.get("args") or {})
    raw_path = str(args.get("path", ".")).strip() or "."
    max_depth = max(0, min(int(args.get("max_depth", 2)), 5))
    log_node_start(logger, "list_dir", state, path=raw_path, max_depth=max_depth)

    try:
        repo_root = Path(state["repo_root"]).resolve()
        target = _resolve_dir(state["repo_root"], raw_path)
        base_depth = len(target.parts)
        dirs: list[str] = []
        files: list[str] = []

        for current_root, current_dirs, current_files in os.walk(target):
            current_path = Path(current_root)
            depth = len(current_path.parts) - base_depth
            if depth >= max_depth:
                current_dirs[:] = []

            for directory in sorted(current_dirs):
                dirs.append(str((current_path / directory).relative_to(repo_root)))
            for file_name in sorted(current_files):
                files.append(str((current_path / file_name).relative_to(repo_root)))

            if len(dirs) + len(files) >= ENTRY_LIMIT:
                break

        preview = {
            "path": str(target.relative_to(repo_root)),
            "dirs": dirs[:ENTRY_LIMIT],
            "files": files[:ENTRY_LIMIT],
        }
        result: ToolExecutionResult = {
            "tool_name": "list_dir",
            "args": {"path": raw_path, "max_depth": max_depth},
            "ok": True,
            "result": f"Listed {raw_path}: {len(dirs)} dirs, {len(files)} files",
            "raw_output": truncate_text(str(preview), OUTPUT_LIMIT),
            "exit_code": 0,
            "metadata": preview,
        }
    except Exception as exc:
        result = {
            "tool_name": "list_dir",
            "args": args,
            "ok": False,
            "result": str(exc),
            "raw_output": str(exc),
            "exit_code": None,
            "metadata": {},
        }

    state_update = {"current_tool_result": result}
    log_node_end(logger, "list_dir", {**state, **state_update}, ok=result.get("ok"))
    return state_update

