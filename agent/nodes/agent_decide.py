from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from agent.actions.parser import parse_decision
from agent.actions.schemas import DecisionModel
from agent.prompts.context_builder import build_decision_prompt
from agent.prompts.system_prompt import DECISION_SYSTEM_PROMPT
from agent.state import AgentState


def _get_model(config: RunnableConfig):
    configurable = config.get("configurable", {})
    model = configurable.get("model")
    if model is None:
        raise ValueError("config.configurable['model'] is required")
    return model


def agent_decide(state: AgentState, config: RunnableConfig) -> dict:
    model = _get_model(config).with_structured_output(DecisionModel)
    decision = model.invoke(
        [
            SystemMessage(content=DECISION_SYSTEM_PROMPT),
            HumanMessage(content=build_decision_prompt(state)),
        ]
    )
    summary, action = parse_decision(decision)
    return {
        "turn_index": state["turn_index"] + 1,
        "working_summary": summary,
        "next_action": action,
        "route": None,
        "last_tool_result": None,
    }
