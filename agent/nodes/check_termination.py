from __future__ import annotations

from agent.state import AgentAction, AgentState


def _action_signature(action: AgentAction) -> str:
    kind = action["kind"]
    if kind == "shell_command":
        return f"shell:{action.get('command', '')}"
    if kind == "read_file":
        return f"read:{action.get('path', '')}:{action.get('start_line', 1)}-{action.get('end_line', 250)}"
    if kind == "list_dir":
        return f"list:{action.get('path', '.')}:{action.get('max_depth', 2)}"
    if kind == "search_files":
        return f"search:{action.get('path', '.')}:{action.get('query', '')}"
    if kind == "write_file":
        return f"write:{action.get('path', '')}"
    return "finish"


def _is_repeated_tool_action(state: AgentState) -> bool:
    if not state["tool_history"]:
        return False

    last_action = state["tool_history"][-1]["action"]
    last_signature = _action_signature(last_action)
    matches = [
        entry
        for entry in state["tool_history"]
        if _action_signature(entry["action"]) == last_signature
    ]

    if last_action["kind"] == "read_file":
        return len(matches) >= 2
    return len(matches) >= 3


def check_termination(state: AgentState) -> dict:
    next_action = state["next_action"] or {"kind": "finish"}

    if next_action["kind"] == "finish":
        return {"should_stop": True, "stop_reason": "agent_finished"}

    if state["pending_write_path"] and state["pending_write_content"] is not None:
        return {"should_stop": True, "stop_reason": "write_ready"}

    if state["turn_index"] >= state["max_turns"]:
        return {"should_stop": True, "stop_reason": "max_turns_reached"}

    if _is_repeated_tool_action(state):
        return {"should_stop": True, "stop_reason": "repeated_action"}

    return {"should_stop": False, "stop_reason": None}
