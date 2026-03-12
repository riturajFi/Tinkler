from __future__ import annotations

from agent.prompts.context_builder import render_state_context
from agent.state import AgentState


def build_agent_context(state: AgentState) -> dict:
    return {"agent_context": render_state_context(state)}
