from __future__ import annotations

from agent.state import AgentState


def init_turn(_: AgentState) -> dict:
    return {
        "turn_index": 0,
        "working_summary": "",
        "tool_history": [],
        "observations": [],
        "discovered_files": [],
        "discovered_dirs": [],
        "likely_entrypoints": [],
        "repo_facts": {},
        "pending_write_path": None,
        "pending_write_content": None,
        "final_response": None,
        "agent_context": "",
        "next_action": None,
        "route": None,
        "last_tool_result": None,
        "should_stop": False,
        "stop_reason": None,
    }
