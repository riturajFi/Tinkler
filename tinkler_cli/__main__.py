from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

from agent.service import AgentRun, FOCUS_GUIDES, run_analysis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only CLI consumer for the Tinkler repo agent."
    )
    subparsers = parser.add_subparsers(dest="command")

    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze a local repository with the Tinkler agent.",
    )
    analyze.add_argument("repo", help="Path to the repository to inspect.")
    analyze.add_argument(
        "--request",
        help="Custom analysis request. If omitted, a built-in focus prompt is used.",
    )
    analyze.add_argument(
        "--focus",
        choices=tuple(FOCUS_GUIDES.keys()),
        default="overview",
        help="Built-in analysis focus when --request is not provided.",
    )
    analyze.add_argument(
        "--max-turns",
        type=int,
        default=12,
        help="Maximum decision turns for the agent.",
    )
    analyze.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model name.",
    )
    analyze.add_argument(
        "--trace",
        action="store_true",
        help="Append the agent tool trace to the output.",
    )
    analyze.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Emit structured JSON instead of plain text.",
    )
    analyze.add_argument(
        "--output",
        help="Optional file path to write the report to.",
    )
    return parser


def _render_plain_output(run: AgentRun, include_trace: bool) -> str:
    text = run.response.strip()
    if not include_trace:
        return text

    trace_lines = run.tool_trace or ["No tool calls recorded."]
    return (
        f"{text}\n\nTrace:\n"
        + "\n".join(trace_lines)
        + f"\n\nStop reason: {run.stop_reason or 'unknown'}"
    ).strip()


def _render_json_output(run: AgentRun) -> str:
    payload = {
        "repo_root": str(run.repo_root),
        "request": run.request,
        "response": run.response,
        "model": run.model_name,
        "max_turns": run.max_turns,
        "turn_count": run.turn_count,
        "stop_reason": run.stop_reason,
        "tool_trace": run.tool_trace,
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _write_output(path: str, text: str) -> None:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{text.rstrip()}\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "analyze":
        parser.print_help()
        return

    try:
        run = run_analysis(
            args.repo,
            question=args.request,
            focus=args.focus,
            max_turns=args.max_turns,
            model_name=args.model,
        )
        output = _render_json_output(run) if args.json_output else _render_plain_output(
            run, args.trace
        )
        if args.output:
            _write_output(args.output, output)
        print(output)
    except Exception as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
