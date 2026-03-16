from __future__ import annotations

import json

from agent.state import AgentState


def _render_items(items: list[str], limit: int = 12) -> str:
    if not items:
        return "[]"
    trimmed = items[:limit]
    if len(items) > limit:
        trimmed.append(f"... (+{len(items) - limit} more)")
    return json.dumps(trimmed, ensure_ascii=True, indent=2)


def _render_observations(state: AgentState, limit: int = 6) -> str:
    recent = state["observations"][-limit:]
    if not recent:
        return "[]"
    return json.dumps(recent, ensure_ascii=True, indent=2)


def _render_tool_history(state: AgentState, limit: int = 6) -> str:
    recent = state["tool_history"][-limit:]
    if not recent:
        return "[]"

    rendered: list[dict[str, object]] = []
    for entry in recent:
        action = entry["action"]
        result = entry["result"]
        rendered.append(
            {
                "turn": entry["turn"],
                "kind": action.get("kind", "unknown"),
                "path": action.get("path"),
                "query": action.get("query"),
                "command": action.get("command"),
                "summary": result.get("summary"),
                "ok": result.get("ok"),
            }
        )
    return json.dumps(rendered, ensure_ascii=True, indent=2)


def render_state_context(state: AgentState) -> str:
    return "\n".join(
        [
            f"request: {state['request']}",
            f"cwd: {state['cwd']}",
            f"repo_root: {state['repo_root']}",
            f"max_turns: {state['max_turns']}",
        ]
    )


def build_decision_prompt(state: AgentState) -> str:
    facts = json.dumps(state["repo_facts"], ensure_ascii=True, indent=2, sort_keys=True)
    return "\n\n".join(
        [
            "Initial context",
            state["agent_context"],
            "Current state",
            "\n".join(
                [
                    f"turn_index: {state['turn_index']}",
                    f"working_summary: {state['working_summary'] or 'none'}",
                    f"pending_write_path: {state['pending_write_path'] or 'none'}",
                    f"stop_reason: {state['stop_reason'] or 'none'}",
                    f"discovered_dir_count: {len(state['discovered_dirs'])}",
                    f"discovered_file_count: {len(state['discovered_files'])}",
                    f"repo_facts: {facts}",
                    f"likely_entrypoints: {_render_items(state['likely_entrypoints'])}",
                    f"discovered_dirs: {_render_items(state['discovered_dirs'])}",
                    f"discovered_files: {_render_items(state['discovered_files'])}",
                    f"recent_tool_history: {_render_tool_history(state)}",
                    f"recent_observations: {_render_observations(state)}",
                ]
            ),
            "Choose the single best next action.",
        ]
    )


def build_finalize_prompt(state: AgentState) -> str:
    facts = json.dumps(state["repo_facts"], ensure_ascii=True, indent=2, sort_keys=True)
    pending = (
        f"path={state['pending_write_path']}, chars={len(state['pending_write_content'] or '')}"
        if state["pending_write_path"]
        else "none"
    )
    return "\n\n".join(
        [
            f"request: {state['request']}",
            f"working_summary: {state['working_summary'] or 'none'}",
            f"stop_reason: {state['stop_reason'] or 'none'}",
            f"pending_write: {pending}",
            f"repo_facts: {facts}",
            f"likely_entrypoints: {_render_items(state['likely_entrypoints'])}",
            f"recent_observations: {_render_observations(state)}",
        ]
    )
