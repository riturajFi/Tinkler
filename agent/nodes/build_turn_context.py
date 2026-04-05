from __future__ import annotations

from agent.observability import get_logger, log_node_end, log_node_start
from agent.prompts.context_builder import build_turn_context_text
from agent.state import AgentState

logger = get_logger(__name__)


def build_turn_context(state: AgentState) -> dict:
    log_node_start(logger, "build_turn_context", state)
    context = build_turn_context_text(state)
    state_update = {"turn_context": context}
    log_node_end(logger, "build_turn_context", {**state, **state_update}, context_chars=len(context))
    return state_update

