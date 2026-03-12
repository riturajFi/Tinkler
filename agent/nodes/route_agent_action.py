from __future__ import annotations

from agent.state import AgentState


def route_agent_action(state: AgentState) -> dict:
    action = state["next_action"] or {"kind": "finish"}
    return {"route": action["kind"]}
