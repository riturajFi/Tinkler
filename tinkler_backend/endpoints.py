from __future__ import annotations

from fastapi import FastAPI

from tinkler_backend.handlers.agent_runs import create_agent_run, stream_agent_run
from tinkler_backend.handlers.health import healthcheck


def register_endpoints(app: FastAPI) -> None:
    app.add_api_route("/health", healthcheck, methods=["GET"], tags=["health"])
    app.add_api_route("/api/v1/agent/runs", create_agent_run, methods=["POST"], tags=["agent"])
    app.add_api_route(
        "/api/v1/agent/runs/stream",
        stream_agent_run,
        methods=["POST"],
        tags=["agent"],
    )

