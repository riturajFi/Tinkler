from __future__ import annotations

from agent.observability import get_logger, log_node_end, log_node_start
from agent.state import AgentState

logger = get_logger(__name__)


def _build_fallback_answer(state: AgentState) -> str:
    stop_reason = state.get("stop_reason") or "stopped"
    parts = [f"Stopped after {state['turn_count']} turn(s) because {stop_reason}."]
    if state["changed_files"]:
        parts.append("Changed files: " + ", ".join(state["changed_files"]))
    elif state["important_files"]:
        parts.append("Relevant files: " + ", ".join(state["important_files"][:8]))
    if state["last_tool_name"] and state["last_tool_result"]:
        parts.append(f"Last tool {state['last_tool_name']}: {state['last_tool_result']}")
    return "\n\n".join(parts)


def finalize_turn(state: AgentState) -> dict:
    log_node_start(logger, "finalize_turn", state)
    action = state.get("model_action") or {}
    if action.get("type") == "final_answer" and str(action.get("message", "")).strip():
        answer = str(action["message"]).strip()
    else:
        answer = _build_fallback_answer(state)

    if state["changed_files"]:
        changed_suffix = "Changed files: " + ", ".join(state["changed_files"])
        if changed_suffix not in answer:
            answer = f"{answer}\n\n{changed_suffix}".strip()

    state_update = {
        "final_answer": answer,
        "done": True,
    }
    log_node_end(logger, "finalize_turn", {**state, **state_update}, response_chars=len(answer))
    return state_update
