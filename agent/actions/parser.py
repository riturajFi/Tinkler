from __future__ import annotations

from agent.actions.schemas import DecisionModel
from agent.state import AgentAction


def parse_decision(raw: DecisionModel | dict) -> tuple[str, AgentAction]:
    # Accept either a validated model or a raw dict from the model layer.
    decision = raw if isinstance(raw, DecisionModel) else DecisionModel.model_validate(raw)
    # Convert the action model to a plain dict and drop empty optional fields.
    action = decision.action.model_dump(exclude_none=True)
    # Read the action kind once because the normalization depends on it.
    kind = action["kind"]

    if kind == "list_dir":

        # Default directory listings to the repo root when no path is given.
        action.setdefault("path", ".")
        
        # Keep depth within a small safe range so traversal stays bounded.
        action["max_depth"] = max(0, min(int(action.get("max_depth", 2)), 5))

    if kind == "read_file":

        # File reads use 1-based lines, so clamp the start line to at least 1.
        start_line = max(1, int(action.get("start_line", 1)))

        # Default to a roughly 250-line window when the model omits the end line.
        end_line = int(action.get("end_line", start_line + 249))

        # Write the normalized start line back into the action payload.
        action["start_line"] = start_line
        
        # Ensure the end line is never before the start line.
        action["end_line"] = max(start_line, end_line)

    if kind == "search_files":

        # Default searches to the repo root when no path is given.
        action.setdefault("path", ".")

    if kind == "write_file":
        
        # Keep content explicitly present in the normalized action payload.
        action["content"] = action["content"]

    # Trim whitespace so the summary is clean for later prompts and output.
    summary = decision.summary.strip()
    
    # Rebuild the typed action so downstream nodes get the expected shape.
    return summary, AgentAction(**action)
