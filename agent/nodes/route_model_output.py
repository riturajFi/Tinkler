from __future__ import annotations

from agent.observability import get_logger, log_node_end, log_node_start
from agent.policies.loop_guard import should_stop_after_model_step
from agent.state import AgentState

logger = get_logger(__name__)


def route_model_output(state: AgentState) -> dict:
    log_node_start(logger, "route_model_output", state)
    action = state.get("model_action")
    if action is None:
        state_update = {
            "route": "finalize_turn",
            "done": True,
            "stop_reason": state.get("stop_reason") or "missing_model_action",
        }
        log_node_end(logger, "route_model_output", {**state, **state_update}, route="finalize_turn")
        return state_update

    should_stop, reason = should_stop_after_model_step(state, action)
    if action.get("type") == "final_answer":
        state_update = {
            "route": "finalize_turn",
            "done": True,
            "stop_reason": state.get("stop_reason") or "model_finished",
        }
    elif should_stop:
        state_update = {
            "route": "finalize_turn",
            "done": True,
            "stop_reason": reason,
        }
    else:
        state_update = {
            "route": action.get("tool_name"),
            "done": False,
            "stop_reason": None,
        }

    log_node_end(
        logger,
        "route_model_output",
        {**state, **state_update},
        route=state_update["route"],
    )
    return state_update

