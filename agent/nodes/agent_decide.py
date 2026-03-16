from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from agent.observability import get_logger, log_node_end, log_node_start
from agent.actions.parser import parse_decision
from agent.actions.schemas import DecisionModel
from agent.prompts.context_builder import build_decision_prompt
from agent.prompts.system_prompt import ALL_ACTIONS, build_decision_system_prompt
from agent.state import ActionKind, AgentState

logger = get_logger(__name__)


def _get_model(config: RunnableConfig):
    configurable = config.get("configurable", {})
    model = configurable.get("model")
    if model is None:
        raise ValueError("config.configurable['model'] is required")
    return model


def _get_allowed_actions(config: RunnableConfig) -> tuple[ActionKind, ...]:
    configurable = config.get("configurable", {})
    raw_allowed = configurable.get("allowed_actions")
    if raw_allowed is None:
        return ALL_ACTIONS

    allowed = tuple(action for action in raw_allowed if action in ALL_ACTIONS)
    return allowed or ("finish",)


def agent_decide(state: AgentState, config: RunnableConfig) -> dict:
    log_node_start(logger, "agent_decide", state)
    allowed_actions = _get_allowed_actions(config)
    model = _get_model(config).with_structured_output(DecisionModel)
    decision = model.invoke(
        [
            SystemMessage(content=build_decision_system_prompt(allowed_actions)),
            HumanMessage(content=build_decision_prompt(state)),
        ]
    )
    summary, action = parse_decision(decision)
    if action["kind"] not in allowed_actions:
        blocked_kind = action["kind"]
        summary = f"{summary} Requested action {blocked_kind!r} is disabled for this run.".strip()
        action = {"kind": "finish"}
    state_update = {
        "turn_index": state["turn_index"] + 1,
        "working_summary": summary,
        "next_action": action,
        "route": None,
        "last_tool_result": None,
    }
    merged_state = {**state, **state_update}
    log_node_end(
        logger,
        "agent_decide",
        merged_state,
        chosen_action=action["kind"],
    )
    return state_update
