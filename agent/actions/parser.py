from __future__ import annotations

from agent.actions.schemas import DecisionModel
from agent.state import AgentAction


def parse_decision(raw: DecisionModel | dict) -> tuple[str, AgentAction]:
    decision = raw if isinstance(raw, DecisionModel) else DecisionModel.model_validate(raw)
    action = decision.action.model_dump(exclude_none=True)
    kind = action["kind"]

    if kind == "list_dir":
        action.setdefault("path", ".")
        action["max_depth"] = max(0, min(int(action.get("max_depth", 2)), 5))
    if kind == "read_file":
        start_line = max(1, int(action.get("start_line", 1)))
        end_line = int(action.get("end_line", start_line + 249))
        action["start_line"] = start_line
        action["end_line"] = max(start_line, end_line)
    if kind == "search_files":
        action.setdefault("path", ".")
    if kind == "write_file":
        action["content"] = action["content"]

    summary = decision.summary.strip()
    return summary, AgentAction(**action)
