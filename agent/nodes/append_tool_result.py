from __future__ import annotations

from agent.observability import get_logger, log_node_end, log_node_start
from agent.state import AgentState, ToolRecord

logger = get_logger(__name__)


def append_tool_result(state: AgentState) -> dict:
    log_node_start(logger, "append_tool_result", state)
    result = state.get("current_tool_result")
    if not result:
        log_node_end(logger, "append_tool_result", state, appended=False)
        return {}

    tool_name = result["tool_name"]
    raw_output = result.get("raw_output") or result.get("result", "")
    history_entry: ToolRecord = {
        "tool_name": tool_name,
        "args": dict(result.get("args") or {}),
        "result": str(result.get("result", "")),
        "exit_code": result.get("exit_code"),
        "ok": bool(result.get("ok")),
    }
    state_update = {
        "tool_history": state["tool_history"] + [history_entry],
        "last_tool_result": raw_output,
        "last_tool_name": tool_name,
        "messages": state["messages"]
        + [{"role": "tool", "name": tool_name, "content": raw_output}],
    }
    log_node_end(logger, "append_tool_result", {**state, **state_update}, appended=True)
    return state_update

