from __future__ import annotations

from agent.observability import get_logger, log_node_end, log_node_start
from agent.state import AgentState

logger = get_logger(__name__)


def init_turn(state: AgentState) -> dict:
    state_update = {
        "messages": [{"role": "user", "content": state["user_request"]}],
        "turn_history": [],
        "tool_history": [],
        "last_tool_result": None,
        "last_tool_name": None,
        "discovered_files": [],
        "discovered_dirs": [],
        "important_files": [],
        "repo_facts": {},
        "pending_patch": None,
        "final_answer": None,
        "turn_count": 0,
        "done": False,
        "stop_reason": None,
        "turn_context": "",
        "prompt_messages": [],
        "tool_schemas": [],
        "model_action": None,
        "current_tool_result": None,
        "route": None,
        "changed_files": [],
    }
    merged_state = {**state, **state_update}
    log_node_start(logger, "init_turn", merged_state)
    log_node_end(logger, "init_turn", merged_state)
    return state_update

