from __future__ import annotations

import os
from pathlib import Path

from agent.state import AgentState, ToolResult

ENTRY_LIMIT = 300


def _resolve_dir(repo_root: str, raw_path: str) -> Path:
    root = Path(repo_root).resolve()
    candidate = (root / raw_path).resolve()
    candidate.relative_to(root)
    if not candidate.exists():
        raise FileNotFoundError(f"Directory not found: {raw_path}")
    if not candidate.is_dir():
        raise ValueError(f"Not a directory: {raw_path}")
    return candidate


def run_list_dir(state: AgentState) -> dict:
    action = state["next_action"] or {}
    raw_path = str(action.get("path", ".")).strip() or "."
    max_depth = max(0, min(int(action.get("max_depth", 2)), 5))

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

        result: ToolResult = {
            "tool": "list_dir",
            "ok": True,
            "summary": f"Listed {raw_path}: {len(dirs)} dirs, {len(files)} files",
            "input": {"path": raw_path, "max_depth": max_depth},
            "data": {
                "path": str(target.relative_to(repo_root)),
                "dirs": dirs[:ENTRY_LIMIT],
                "files": files[:ENTRY_LIMIT],
            },
        }
    except Exception as exc:
        result = {
            "tool": "list_dir",
            "ok": False,
            "summary": str(exc),
            "input": {"path": raw_path, "max_depth": max_depth},
            "data": {},
            "error": str(exc),
        }

    return {"last_tool_result": result}
