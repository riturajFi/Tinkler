from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent.service import build_analysis_request, run_analysis
from tinkler_cli.__main__ import build_parser


class _FakeModel:
    def __init__(self, response=None):
        self._response = response

    def with_structured_output(self, _schema):
        return self

    def invoke(self, *_args, **_kwargs):
        return self._response


class _FakeGraph:
    def __init__(self, response):
        self._response = response
        self.received_state = None
        self.received_config = None

    def invoke(self, state, config):
        self.received_state = state
        self.received_config = config
        return self._response


class TinklerCliTests(unittest.TestCase):
    def test_build_analysis_request_includes_read_only_guard(self):
        request = build_analysis_request("/tmp/example-repo", focus="architecture")
        self.assertIn("example-repo", request)
        self.assertIn("Read-only mode", request)
        self.assertIn("Analyze the repository architecture", request)

    def test_run_analysis_passes_read_only_allowed_actions(self):
        fake_result = {
            "final_response": "Repository summary",
            "stop_reason": "agent_finished",
            "turn_index": 2,
            "tool_history": [],
            "pending_write_path": None,
        }
        fake_graph = _FakeGraph(fake_result)

        with tempfile.TemporaryDirectory() as repo_dir:
            run_analysis(
                repo_dir,
                question="Summarize this repo",
                model=_FakeModel(),
                graph=fake_graph,
            )

        allowed_actions = fake_graph.received_config["configurable"]["allowed_actions"]
        self.assertNotIn("write_file", allowed_actions)
        self.assertIn("finish", allowed_actions)

    def test_parser_uses_analyze_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["analyze", "/tmp/repo"])

        self.assertEqual(args.command, "analyze")
        self.assertEqual(args.focus, "overview")
        self.assertEqual(args.max_turns, 12)
        self.assertFalse(args.trace)
        self.assertFalse(args.json_output)

    def test_run_analysis_uses_agent_service_request_and_graph(self):
        fake_result = {
            "final_response": "Repository summary",
            "stop_reason": "agent_finished",
            "turn_index": 2,
            "tool_history": [
                {
                    "turn": 1,
                    "action": {"kind": "list_dir", "path": ".", "max_depth": 2},
                    "result": {"ok": True, "summary": "Listed .: 1 dirs, 2 files"},
                }
            ],
            "pending_write_path": None,
        }
        fake_graph = _FakeGraph(fake_result)

        with tempfile.TemporaryDirectory() as repo_dir:
            run = run_analysis(
                repo_dir,
                question="Summarize this repo",
                model=_FakeModel(),
                graph=fake_graph,
            )

        self.assertEqual(run.response, "Repository summary")
        self.assertEqual(run.stop_reason, "agent_finished")
        self.assertIn("list . depth=2", run.tool_trace[0])
        self.assertIn("Read-only mode", fake_graph.received_state["request"])
        self.assertEqual(fake_graph.received_state["repo_root"], str(Path(repo_dir).resolve()))
