from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from agent.observability import get_logger, log_node_end, log_node_start
from agent.prompts.context_builder import build_prompt_messages
from agent.prompts.system_prompt import ALL_TOOLS, build_model_system_prompt, build_tool_schemas
from agent.state import AgentState, ToolName

logger = get_logger(__name__)


def _get_allowed_tools(config: RunnableConfig) -> tuple[ToolName, ...]:
    configurable = config.get("configurable", {})
    raw_allowed = configurable.get("allowed_tools")
    if raw_allowed is None:
        return ALL_TOOLS
    allowed = tuple(tool for tool in raw_allowed if tool in ALL_TOOLS)
    return allowed or ("shell_command",)


def build_prompt_and_tools(state: AgentState, config: RunnableConfig) -> dict:
    log_node_start(logger, "build_prompt_and_tools", state)
    allowed_tools = _get_allowed_tools(config)
    tool_schemas = build_tool_schemas(allowed_tools)
    system_prompt = build_model_system_prompt(allowed_tools)
    prompt_messages = build_prompt_messages(
        state,
        system_prompt=system_prompt,
        tool_schemas=tool_schemas,
    )
    state_update = {
        "tool_schemas": tool_schemas,
        "prompt_messages": prompt_messages,
        "route": None,
    }
    log_node_end(
        logger,
        "build_prompt_and_tools",
        {**state, **state_update},
        tools=len(tool_schemas),
    )
    return state_update

