from __future__ import annotations

import argparse
import os
from pathlib import Path

from langchain_openai import ChatOpenAI

from agent.graph import build_graph
from agent.state import create_initial_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LangGraph repo agent.")
    parser.add_argument("request", help="Task for the agent to complete.")
    parser.add_argument("--cwd", default=".", help="Repository root to inspect.")
    parser.add_argument("--max-turns", type=int, default=12, help="Maximum agent turns.")
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        help="OpenAI model name.",
    )
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required.")

    repo_root = str(Path(args.cwd).resolve())
    graph = build_graph()
    model = ChatOpenAI(model=args.model, temperature=0)
    state = create_initial_state(
        request=args.request,
        cwd=repo_root,
        repo_root=repo_root,
        max_turns=args.max_turns,
    )
    result = graph.invoke(state, config={"configurable": {"model": model}})
    print(result.get("final_response", ""))


if __name__ == "__main__":
    main()
