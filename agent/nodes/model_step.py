from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from agent.actions.parser import parse_model_action
from agent.actions.schemas import ModelActionModel
from agent.observability import get_logger, log_node_end, log_node_start
from agent.prompts.system_prompt import ALL_TOOLS
from agent.state import AgentState, MessageRecord, ToolName

logger = get_logger(__name__)


def _get_model(config: RunnableConfig):
    configurable = config.get("configurable", {})
    model = configurable.get("model")
    if model is None:
        raise ValueError("config.configurable['model'] is required")
    return model


def _get_allowed_tools(config: RunnableConfig) -> tuple[ToolName, ...]:
    configurable = config.get("configurable", {})
    raw_allowed = configurable.get("allowed_tools")
    if raw_allowed is None:
        return ALL_TOOLS
    allowed = tuple(tool for tool in raw_allowed if tool in ALL_TOOLS)
    return allowed or ("shell_command",)


def _to_langchain_message(message: MessageRecord):
    role = message.get("role")
    content = str(message.get("content", ""))
    if role == "system":
        return SystemMessage(content=content)
    if role == "assistant":
        return AIMessage(content=content)
    if role == "tool":
        return ToolMessage(content=content, tool_call_id=str(message.get("name", "tool")))
    return HumanMessage(content=content)


def _assistant_message_for_action(action: dict) -> str:
    if action.get("type") == "final_answer":
        return str(action.get("message", "")).strip()
    tool_name = action.get("tool_name", "tool")
    args = json.dumps(action.get("args", {}), ensure_ascii=True, sort_keys=True)
    return f"Requested tool {tool_name} with args {args}"


def _fallback_read_path(state: AgentState) -> str | None:
    for record in reversed(state.get("tool_history", [])):
        if record.get("tool_name") == "read_file":
            path = str(record.get("args", {}).get("path", "")).strip()
            if path:
                return path

    for path in reversed(state.get("important_files", [])):
        candidate = str(path).strip()
        if candidate:
            return candidate

    for path in state.get("discovered_files", []):
        candidate = str(path).strip()
        if candidate:
            return candidate

    return None


def model_step(state: AgentState, config: RunnableConfig) -> dict:
    log_node_start(logger, "model_step", state)
    allowed_tools = _get_allowed_tools(config)
    model = _get_model(config).with_structured_output(ModelActionModel)
    prompt_messages = [_to_langchain_message(message) for message in state["prompt_messages"]]

    try:
        raw_action = model.invoke(prompt_messages)
        model_action = parse_model_action(
            raw_action,
            allowed_tools=allowed_tools,
            fallback_read_path=_fallback_read_path(state),
        )
        assistant_message = _assistant_message_for_action(model_action)
        state_update = {
            "turn_count": state["turn_count"] + 1,
            "model_action": model_action,
            "messages": state["messages"] + [{"role": "assistant", "content": assistant_message}],
            "turn_history": state["turn_history"]
            + [{"turn": state["turn_count"] + 1, "action": model_action}],
            "pending_patch": (
                model_action.get("args", {}).get("patch")
                if model_action.get("tool_name") == "apply_patch"
                else None
            ),
        }
    except Exception as exc:
        fallback_action = {
            "type": "final_answer",
            "message": f"Stopping because the model action could not be parsed: {exc}",
        }
        state_update = {
            "turn_count": state["turn_count"] + 1,
            "model_action": fallback_action,
            "messages": state["messages"] + [{"role": "assistant", "content": fallback_action["message"]}],
            "turn_history": state["turn_history"]
            + [{"turn": state["turn_count"] + 1, "action": fallback_action}],
            "stop_reason": "invalid_model_action",
        }

    merged_state = {**state, **state_update}
    chosen = state_update["model_action"].get("tool_name") or state_update["model_action"].get("type")
    log_node_end(logger, "model_step", merged_state, chosen=chosen)
    return state_update
