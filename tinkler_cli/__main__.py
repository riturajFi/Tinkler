from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

from agent.service import AgentRun, run_analysis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simple CLI for running the Tinkler agent on a repository."
    )
    parser.add_argument(
        "request",
        nargs="?",
        help="Optional initial instruction to send to the agent.",
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Repository path to inspect. Defaults to the current directory.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Maximum decision turns for the agent.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model name.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Append the agent tool trace to the output.",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Emit structured JSON instead of plain text.",
    )
    parser.add_argument(
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


def _run_request(args: argparse.Namespace, request: str) -> str:
    run = run_analysis(
        args.cwd,
        question=request,
        max_turns=args.max_turns,
        model_name=args.model,
    )
    return _render_json_output(run) if args.json_output else _render_plain_output(
        run, args.trace
    )


def _run_repl(args: argparse.Namespace) -> None:
    print(f"Tinkler CLI attached to: {Path(args.cwd).expanduser().resolve()}")
    print("Enter a request. Commands: /exit, /quit")

    if args.request:
        try:
            output = _run_request(args, args.request)
            if args.output:
                _write_output(args.output, output)
            print(output)
            print()
        except Exception as exc:
            print(f"Error: {exc}")

    while True:
        try:
            request = input("tinkler> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\nInterrupted. Use /exit to quit.")
            continue

        if not request:
            continue
        if request in {"/exit", "/quit"}:
            break

        try:
            output = _run_request(args, request)
            if args.output:
                _write_output(args.output, output)
            print(output)
            print()
        except Exception as exc:
            print(f"Error: {exc}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        _run_repl(args)
    except Exception as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
