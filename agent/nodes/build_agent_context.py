from __future__ import annotations

from agent.observability import get_logger, log_node_end, log_node_start
from agent.prompts.context_builder import render_state_context
from agent.state import AgentState

logger = get_logger(__name__)


def build_agent_context(state: AgentState) -> dict:
    log_node_start(logger, "build_agent_context", state)
    context = render_state_context(state)
    log_node_end(logger, "build_agent_context", state, context_chars=len(context))
    return {"agent_context": context}
