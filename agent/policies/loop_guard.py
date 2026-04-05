from __future__ import annotations

import json

from agent.state import AgentState, ModelAction


def _action_signature(action: ModelAction | None) -> str:
    if not action:
        return "none"

    if action.get("type") == "final_answer":
        return "final_answer"

    tool_name = action.get("tool_name") or "unknown"
    args = action.get("args") or {}
    return f"{tool_name}:{json.dumps(args, ensure_ascii=True, sort_keys=True)}"


def should_stop_after_model_step(state: AgentState, action: ModelAction | None) -> tuple[bool, str | None]:
    if state.get("done"):
        return True, state.get("stop_reason") or "done"

    if not action:
        return True, "missing_model_action"

    if action.get("type") == "final_answer":
        return False, None

    if int(state.get("turn_count", 0)) >= int(state.get("max_turns", 0)):
        return True, "max_turns_reached"

    signature = _action_signature(action)
    matches = [
        entry
        for entry in state.get("turn_history", [])
        if _action_signature(entry.get("action")) == signature
    ]
    if len(matches) >= 3:
        return True, "repeated_tool_request"

    return False, None
