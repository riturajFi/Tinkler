from __future__ import annotations

from agent.observability import get_logger, log_node_end, log_node_start
from agent.state import AgentState

logger = get_logger(__name__)


# Reset all per-run working fields before the graph starts making decisions.
# This keeps request/repo inputs from create_initial_state(), but clears
# summaries, tool results, observations, routing, and stop state.
def init_turn(_: AgentState) -> dict:
    state_update = {
        "turn_index": 0,
        "working_summary": "",
        "tool_history": [],
        "observations": [],
        "discovered_files": [],
        "discovered_dirs": [],
        "likely_entrypoints": [],
        "repo_facts": {},
        "pending_write_path": None,
        "pending_write_content": None,
        "final_response": None,
        "agent_context": "",
        "next_action": None,
        "route": None,
        "last_tool_result": None,
        "should_stop": False,
        "stop_reason": None,
    }
    log_node_start(logger, "init_turn", state_update)
    log_node_end(logger, "init_turn", state_update)
    return state_update
