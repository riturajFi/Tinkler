from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from agent.prompts.context_builder import build_finalize_prompt
from agent.prompts.system_prompt import FINALIZE_SYSTEM_PROMPT
from agent.state import AgentState


def _get_model(config: RunnableConfig):
    configurable = config.get("configurable", {})
    model = configurable.get("model")
    if model is None:
        raise ValueError("config.configurable['model'] is required")
    return model


def finalize_answer(state: AgentState, config: RunnableConfig) -> dict:
    model = _get_model(config)
    response = model.invoke(
        [
            SystemMessage(content=FINALIZE_SYSTEM_PROMPT),
            HumanMessage(content=build_finalize_prompt(state)),
        ]
    )
    return {"final_response": response.content.strip()}
