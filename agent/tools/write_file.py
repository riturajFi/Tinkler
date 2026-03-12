from __future__ import annotations

from pathlib import Path

from agent.state import AgentState, ToolResult


def _resolve_target(repo_root: str, raw_path: str) -> Path:
    root = Path(repo_root).resolve()
    candidate = (root / raw_path).resolve()
    candidate.relative_to(root)
    return candidate


def stage_write_file(state: AgentState) -> dict:
    action = state["next_action"] or {}
    raw_path = str(action.get("path", "")).strip()
    content = str(action.get("content", ""))

    try:
        if not raw_path:
            raise ValueError("Write path cannot be empty.")

        target = _resolve_target(state["repo_root"], raw_path)
        rel_path = str(target.relative_to(Path(state["repo_root"]).resolve()))
        result: ToolResult = {
            "tool": "write_file",
            "ok": True,
            "summary": f"Prepared write for {rel_path}",
            "input": {"path": raw_path},
            "data": {"path": rel_path, "chars": len(content)},
        }
        return {
            "pending_write_path": rel_path,
            "pending_write_content": content,
            "last_tool_result": result,
        }
    except Exception as exc:
        result = {
            "tool": "write_file",
            "ok": False,
            "summary": str(exc),
            "input": {"path": raw_path},
            "data": {},
            "error": str(exc),
        }
        return {"last_tool_result": result}
