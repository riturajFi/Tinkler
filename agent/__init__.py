from __future__ import annotations

from typing import Any

__all__ = [
    "AgentEvent",
    "AgentRun",
    "build_analysis_request",
    "build_graph",
    "create_initial_state",
    "iter_agent_events",
    "run_agent",
    "run_analysis",
]


def build_graph(*args: Any, **kwargs: Any):
    from agent.graph import build_graph as _build_graph

    return _build_graph(*args, **kwargs)


def create_initial_state(*args: Any, **kwargs: Any):
    from agent.state import create_initial_state as _create_initial_state

    return _create_initial_state(*args, **kwargs)


def build_analysis_request(*args: Any, **kwargs: Any):
    from agent.service import build_analysis_request as _build_analysis_request

    return _build_analysis_request(*args, **kwargs)


def run_agent(*args: Any, **kwargs: Any):
    from agent.service import run_agent as _run_agent

    return _run_agent(*args, **kwargs)


def iter_agent_events(*args: Any, **kwargs: Any):
    from agent.service import iter_agent_events as _iter_agent_events

    return _iter_agent_events(*args, **kwargs)


def run_analysis(*args: Any, **kwargs: Any):
    from agent.service import run_analysis as _run_analysis

    return _run_analysis(*args, **kwargs)


def __getattr__(name: str):
    if name in {"AgentRun", "AgentEvent"}:
        from agent.service import AgentEvent, AgentRun

        return {"AgentRun": AgentRun, "AgentEvent": AgentEvent}[name]
    raise AttributeError(name)
