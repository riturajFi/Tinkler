from __future__ import annotations

import json

from agent.policies.truncation import truncate_text
from agent.state import AgentState, MessageRecord


def _render_items(items: list[str], limit: int = 12) -> str:
    if not items:
        return "[]"
    trimmed = items[:limit]
    if len(items) > limit:
        trimmed = trimmed + [f"... (+{len(items) - limit} more)"]
    return json.dumps(trimmed, ensure_ascii=True, indent=2)


def _render_messages(messages: list[MessageRecord], limit: int = 8) -> str:
    recent = messages[-limit:]
    if not recent:
        return "[]"
    rendered: list[dict[str, object]] = []
    for entry in recent:
        rendered.append(
            {
                "role": entry.get("role", "unknown"),
                "name": entry.get("name"),
                "content": truncate_text(str(entry.get("content", "")), 1200),
            }
        )
    return json.dumps(rendered, ensure_ascii=True, indent=2)


def _render_tool_history(state: AgentState, limit: int = 6) -> str:
    recent = state["tool_history"][-limit:]
    if not recent:
        return "[]"
    return json.dumps(recent, ensure_ascii=True, indent=2)


def build_turn_context_text(state: AgentState) -> str:
    facts = json.dumps(state["repo_facts"], ensure_ascii=True, indent=2, sort_keys=True)
    return "\n".join(
        [
            f"user_request: {state['user_request']}",
            f"cwd: {state['cwd']}",
            f"repo_root: {state['repo_root']}",
            f"turn_count: {state['turn_count']}",
            f"max_turns: {state['max_turns']}",
            f"last_tool_name: {state['last_tool_name'] or 'none'}",
            f"last_tool_result: {truncate_text(state['last_tool_result'] or 'none', 1200)}",
            f"important_files: {_render_items(state['important_files'])}",
            f"discovered_dirs: {_render_items(state['discovered_dirs'])}",
            f"discovered_files: {_render_items(state['discovered_files'])}",
            f"changed_files: {_render_items(state['changed_files'])}",
            f"repo_facts: {facts}",
            f"recent_tool_history: {_render_tool_history(state)}",
        ]
    )


def build_prompt_messages(
    state: AgentState,
    *,
    system_prompt: str,
    tool_schemas: list[dict[str, object]],
) -> list[MessageRecord]:
    prompt_content = "\n\n".join(
        [
            "Current turn context",
            state["turn_context"],
            "Conversation history",
            _render_messages(state["messages"]),
            "Available tool schemas",
            json.dumps(tool_schemas, ensure_ascii=True, indent=2),
            "Return exactly one structured action.",
        ]
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt_content},
    ]
