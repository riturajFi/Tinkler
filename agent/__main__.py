from __future__ import annotations

import argparse
import os

from agent.observability import configure_logging
from agent.service import run_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LangGraph repo agent.")
    parser.add_argument("request", help="Task for the agent to complete.")
    parser.add_argument("--cwd", default=".", help="Repository root to inspect.")
    parser.add_argument("--max-turns", type=int, default=30, help="Maximum agent turns.")
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model name.",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("AGENT_LOG_LEVEL", "INFO"),
        help="Python logging level for agent observability.",
    )
    args = parser.parse_args()
    configure_logging(args.log_level)

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required.")

    result = run_agent(
        args.cwd,
        request=args.request,
        max_turns=args.max_turns,
        model_name=args.model,
        allow_writes=True,
    )
    print(result.response)


if __name__ == "__main__":
    main()
