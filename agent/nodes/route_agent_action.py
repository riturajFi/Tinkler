from __future__ import annotations

from agent.observability import get_logger, log_node_end, log_node_start
from agent.state import AgentState

logger = get_logger(__name__)


def route_agent_action(state: AgentState) -> dict:
    log_node_start(logger, "route_agent_action", state)
    action = state["next_action"] or {"kind": "finish"}
    state_update = {"route": action["kind"]}
    merged_state = {**state, **state_update}
    log_node_end(logger, "route_agent_action", merged_state, route=action["kind"])
    return state_update
