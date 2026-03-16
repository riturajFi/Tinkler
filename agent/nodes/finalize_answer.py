from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from agent.observability import get_logger, log_node_end, log_node_start
from agent.prompts.context_builder import build_finalize_prompt
from agent.prompts.system_prompt import FINALIZE_SYSTEM_PROMPT
from agent.state import AgentState

logger = get_logger(__name__)


def _get_model(config: RunnableConfig):
    configurable = config.get("configurable", {})
    model = configurable.get("model")
    if model is None:
        raise ValueError("config.configurable['model'] is required")
    return model


def finalize_answer(state: AgentState, config: RunnableConfig) -> dict:
    log_node_start(logger, "finalize_answer", state)
    model = _get_model(config)
    response = model.invoke(
        [
            SystemMessage(content=FINALIZE_SYSTEM_PROMPT),
            HumanMessage(content=build_finalize_prompt(state)),
        ]
    )
    state_update = {"final_response": response.content.strip()}
    log_node_end(logger, "finalize_answer", {**state, **state_update}, response_chars=len(state_update["final_response"]))
    return state_update
