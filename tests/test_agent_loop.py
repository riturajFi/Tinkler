from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent.graph import build_graph
from agent.state import create_initial_state


class _SequentialModel:
    def __init__(self, responses):
        self._responses = list(responses)

    def with_structured_output(self, _schema):
        return self

    def invoke(self, *_args, **_kwargs):
        if not self._responses:
            raise AssertionError("No more fake model responses configured.")
        return self._responses.pop(0)


class AgentLoopTests(unittest.TestCase):
    def test_tool_result_is_appended_and_loop_returns_to_model(self):
        graph = build_graph()
        model = _SequentialModel(
            [
                {
                    "type": "tool_call",
                    "tool_name": "list_dir",
                    "args": {"path": ".", "max_depth": 1},
                },
                {
                    "type": "final_answer",
                    "message": "Repository inspection complete.",
                },
            ]
        )

        with tempfile.TemporaryDirectory() as repo_dir:
            repo_root = Path(repo_dir)
            (repo_root / "src").mkdir()
            (repo_root / "README.md").write_text("hello\n", encoding="utf-8")
            state = create_initial_state(
                request="Inspect the repository",
                cwd=str(repo_root),
                repo_root=str(repo_root),
                max_turns=4,
            )

            result = graph.invoke(
                state,
                config={
                    "recursion_limit": 40,
                    "configurable": {
                        "model": model,
                        "allowed_tools": ("list_dir", "read_file", "search_files", "shell_command"),
                    },
                },
            )

        self.assertEqual(result["final_answer"], "Repository inspection complete.")
        self.assertEqual(result["tool_history"][0]["tool_name"], "list_dir")
        self.assertIn("README.md", result["last_tool_result"])
        self.assertEqual(result["messages"][-1]["content"], "Repository inspection complete.")

    def test_apply_patch_runs_inside_loop(self):
        graph = build_graph()
        patch = "\n".join(
            [
                "*** Begin Patch",
                "*** Add File: notes.txt",
                "+hello from patch",
                "*** End Patch",
            ]
        )
        model = _SequentialModel(
            [
                {
                    "type": "tool_call",
                    "tool_name": "apply_patch",
                    "args": {"patch": patch},
                },
                {
                    "type": "final_answer",
                    "message": "Patched the repository.",
                },
            ]
        )

        with tempfile.TemporaryDirectory() as repo_dir:
            repo_root = Path(repo_dir)
            state = create_initial_state(
                request="Add notes.txt",
                cwd=str(repo_root),
                repo_root=str(repo_root),
                max_turns=4,
            )

            result = graph.invoke(
                state,
                config={
                    "recursion_limit": 40,
                    "configurable": {
                        "model": model,
                        "allowed_tools": ("apply_patch",),
                    },
                },
            )

            self.assertEqual((repo_root / "notes.txt").read_text(encoding="utf-8"), "hello from patch\n")

        self.assertEqual(result["tool_history"][0]["tool_name"], "apply_patch")
        self.assertIn("notes.txt", result["changed_files"])
        self.assertEqual(result["final_answer"], "Patched the repository.\n\nChanged files: notes.txt")
