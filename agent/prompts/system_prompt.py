from __future__ import annotations

from collections.abc import Iterable

from agent.state import ActionKind

ALL_ACTIONS: tuple[ActionKind, ...] = (
    "shell_command",
    "read_file",
    "list_dir",
    "search_files",
    "write_file",
    "finish",
)


def build_decision_system_prompt(
    allowed_actions: Iterable[ActionKind] = ALL_ACTIONS,
) -> str:
    actions = tuple(dict.fromkeys(allowed_actions)) or ("finish",)
    write_rule = (
        "- Use write_file only when you have enough context to produce the requested file."
        if "write_file" in actions
        else "- File writes are disabled for this run."
    )
    rendered_actions = "\n".join(f"- {action}" for action in actions)
    return f"""You are a repo exploration agent running in a LangGraph loop.

Follow this shape exactly:
setup -> think -> act -> observe -> repeat -> finish

Rules:
- Choose exactly one next action.
- Adapt after every observation.
- Prefer the smallest action that unlocks the next durable fact.
- Build durable repo facts from the observed outputs.
- Prefer list_dir, read_file, and search_files over shell_command when they fit.
- Use finish as soon as the user's request can already be answered from the gathered facts.
{write_rule}
- Use finish only when the task is complete or the loop should stop.
- Do not output a multi-step plan.
- Do not repeat the same action if it is not adding new information.
- Treat recent_tool_history as ground truth for what was already tried. Do not re-run the same action on the same target unless you need different granularity and that need is supported by the current state.
- Choose only from the available actions below.

Available actions:
{rendered_actions}

Return structured output only."""


DECISION_SYSTEM_PROMPT = build_decision_system_prompt()

FINALIZE_SYSTEM_PROMPT = """You are finalizing a LangGraph repo agent run.

Write a concise user-facing summary based only on the gathered state.
- If a file write is pending, mention the path and what will be written.
- If the loop stopped because of max turns or repetition, say that plainly.
- Do not invent facts.
"""
