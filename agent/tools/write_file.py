from __future__ import annotations

from pathlib import Path

from agent.observability import get_logger, log_node_end, log_node_start
from agent.state import AgentState, ToolResult

logger = get_logger(__name__)


def _resolve_target(repo_root: str, raw_path: str) -> Path:
    root = Path(repo_root).resolve()
    candidate = (root / raw_path).resolve()
    candidate.relative_to(root)
    return candidate


def stage_write_file(state: AgentState) -> dict:
    action = state["next_action"] or {}
    raw_path = str(action.get("path", "")).strip()
    content = str(action.get("content", ""))
    log_node_start(logger, "write_file", state, path=raw_path, chars=len(content))

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
        state_update = {
            "pending_write_path": rel_path,
            "pending_write_content": content,
            "last_tool_result": result,
        }
        log_node_end(logger, "write_file", {**state, **state_update}, staged=True)
        return state_update
    except Exception as exc:
        result = {
            "tool": "write_file",
            "ok": False,
            "summary": str(exc),
            "input": {"path": raw_path},
            "data": {},
            "error": str(exc),
        }
        state_update = {"last_tool_result": result}
        log_node_end(logger, "write_file", {**state, **state_update}, staged=False)
        return state_update
