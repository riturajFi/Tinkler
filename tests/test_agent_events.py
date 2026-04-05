from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent.service import iter_agent_events


class _SequentialModel:
    def __init__(self, responses):
        self._responses = list(responses)

    def with_structured_output(self, _schema):
        return self

    def invoke(self, *_args, **_kwargs):
        if not self._responses:
            raise AssertionError("No more fake model responses configured.")
        return self._responses.pop(0)


class AgentEventStreamTests(unittest.TestCase):
    def test_iter_agent_events_emits_progress_tool_and_completion(self):
        model = _SequentialModel(
            [
                {
                    "type": "tool_call",
                    "tool_name": "list_dir",
                    "args": {"path": ".", "max_depth": 1},
                },
                {
                    "type": "final_answer",
                    "message": "Inspection complete.",
                },
            ]
        )

        with tempfile.TemporaryDirectory() as repo_dir:
            repo_root = Path(repo_dir)
            (repo_root / "src").mkdir()
            (repo_root / "README.md").write_text("hello\n", encoding="utf-8")
            events = list(
                iter_agent_events(
                    repo_root,
                    request="Inspect the repository",
                    max_turns=4,
                    model=model,
                    allow_writes=False,
                )
            )

        event_types = [event.type for event in events]
        self.assertIn("run.started", event_types)
        self.assertIn("loop.progress", event_types)
        self.assertIn("model.action", event_types)
        self.assertIn("tool.result", event_types)
        self.assertIn("run.completed", event_types)

        completed_event = next(event for event in events if event.type == "run.completed")
        self.assertEqual(completed_event.payload["response"], "Inspection complete.")
        self.assertEqual(completed_event.payload["changed_files"], [])

