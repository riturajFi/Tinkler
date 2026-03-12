from __future__ import annotations

from pathlib import Path

from agent.state import AgentState


def apply_file_write(state: AgentState) -> dict:
    if not state["pending_write_path"] or state["pending_write_content"] is None:
        return {}

    repo_root = Path(state["repo_root"]).resolve()
    target = (repo_root / state["pending_write_path"]).resolve()
    target.relative_to(repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(state["pending_write_content"], encoding="utf-8")

    final_response = (state["final_response"] or "").rstrip()
    suffix = f"Wrote file: {state['pending_write_path']}"
    if suffix not in final_response:
        final_response = f"{final_response}\n\n{suffix}".strip()
    return {"final_response": final_response}
