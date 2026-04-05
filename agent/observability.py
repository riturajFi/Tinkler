from __future__ import annotations

import logging
from typing import Any

from agent.state import AgentState, ModelAction, ToolExecutionResult


def configure_logging(level: str = "INFO") -> None:
    resolved_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=resolved_level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    root_logger.setLevel(resolved_level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def _turn(state: AgentState) -> int:
    return int(state.get("turn_count", 0))


def _action_name(action: ModelAction | None) -> str:
    if not action:
        return "none"
    if action.get("type") == "final_answer":
        return "final_answer"
    return str(action.get("tool_name", "tool_call"))


def _tool_summary(result: ToolExecutionResult | None) -> str:
    if not result:
        return "none"
    summary = str(result.get("result", "")).strip()
    if summary:
        return summary
    return "ok" if result.get("ok") else "error"


def log_node_start(logger: logging.Logger, node_name: str, state: AgentState, **extra: Any) -> None:
    details = " ".join(f"{key}={value!r}" for key, value in extra.items() if value is not None)
    suffix = f" {details}" if details else ""
    logger.info(
        "node=%s event=start turn=%s action=%s%s",
        node_name,
        _turn(state),
        _action_name(state.get("model_action")),
        suffix,
    )


def log_node_end(logger: logging.Logger, node_name: str, state: AgentState, **extra: Any) -> None:
    details = " ".join(f"{key}={value!r}" for key, value in extra.items() if value is not None)
    suffix = f" {details}" if details else ""
    logger.info(
        "node=%s event=end turn=%s done=%s stop_reason=%r last_tool=%r%s",
        node_name,
        _turn(state),
        state.get("done"),
        state.get("stop_reason"),
        _tool_summary(state.get("current_tool_result")),
        suffix,
    )
