from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.service import AgentEvent, AgentRun
from tinkler_backend.app import create_app
from tinkler_backend.handlers.agent_runs import create_agent_run, stream_agent_run
from tinkler_backend.handlers.health import healthcheck
from tinkler_backend.schemas import AgentRunRequest, serialize_event
from tinkler_backend.sse import encode_sse


class BackendApiTests(unittest.TestCase):
    def test_create_app_registers_expected_routes(self):
        app = create_app()
        paths = {route.path for route in app.routes}

        self.assertIn("/health", paths)
        self.assertIn("/api/v1/agent/runs", paths)
        self.assertIn("/api/v1/agent/runs/stream", paths)

    def test_health_handler(self):
        self.assertEqual(healthcheck(), {"status": "ok"})

    @patch("tinkler_backend.handlers.agent_runs.run_agent")
    def test_create_agent_run_returns_json(self, mock_run_agent):
        mock_run_agent.return_value = AgentRun(
            repo_root="/tmp/repo",  # type: ignore[arg-type]
            request="Inspect the repo",
            response="Done",
            model_name="gpt-4o-mini",
            max_turns=12,
            stop_reason="model_finished",
            turn_count=2,
            tool_trace=["1. list . depth=1 [ok] -> Listed .: 1 dirs, 1 files"],
            changed_files=[],
        )

        response = create_agent_run(AgentRunRequest(cwd="/tmp/repo", request="Inspect the repo"))

        self.assertEqual(response.response, "Done")
        self.assertEqual(response.changed_files, [])

    @patch("tinkler_backend.handlers.agent_runs.iter_agent_events")
    def test_stream_agent_run_returns_sse_response(self, mock_iter_agent_events):
        mock_iter_agent_events.return_value = iter(
            [
                AgentEvent(
                    type="run.started",
                    run_id="run-1",
                    sequence=1,
                    turn_count=0,
                    max_turns=10,
                    payload={"request": "Inspect"},
                ),
                AgentEvent(
                    type="run.completed",
                    run_id="run-1",
                    sequence=2,
                    turn_count=1,
                    max_turns=10,
                    payload={"response": "Done", "changed_files": []},
                ),
            ]
        )

        response = stream_agent_run(AgentRunRequest(cwd="/tmp/repo", request="Inspect"))

        self.assertEqual(response.media_type, "text/event-stream")
        self.assertEqual(response.headers["Cache-Control"], "no-cache")

    def test_encode_sse_formats_event_payload(self):
        event = AgentEvent(
            type="run.completed",
            run_id="run-1",
            sequence=2,
            turn_count=1,
            max_turns=10,
            payload={"response": "Done"},
        )

        rendered = encode_sse(serialize_event(event))

        self.assertIn("event: run.completed", rendered)
        self.assertIn('"response": "Done"', rendered)
