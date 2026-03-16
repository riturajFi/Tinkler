from __future__ import annotations

from pathlib import Path

from agent.observability import get_logger, log_node_end, log_node_start
from agent.state import AgentState

logger = get_logger(__name__)


def apply_file_write(state: AgentState) -> dict:
    log_node_start(logger, "apply_file_write", state, path=state.get("pending_write_path"))
    if not state["pending_write_path"] or state["pending_write_content"] is None:
        log_node_end(logger, "apply_file_write", state, applied=False)
        return {}

    repo_root = Path(state["repo_root"]).resolve()
    target = (repo_root / state["pending_write_path"]).resolve()
    target.relative_to(repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(state["pending_write_content"], encoding="utf-8")

    final_response = (state["final_response"] or "").rstrip()
    suffix = f"Wrote file: {state['pending_write_path']}"
    if suffix not in final_response:
        final_response = f"{final_response}\n\n{suffix}".strip()
    state_update = {"final_response": final_response}
    log_node_end(logger, "apply_file_write", {**state, **state_update}, applied=True)
    return state_update
