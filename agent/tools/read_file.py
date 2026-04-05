from __future__ import annotations

from pathlib import Path

from agent.observability import get_logger, log_node_end, log_node_start
from agent.policies.truncation import truncate_text
from agent.state import AgentState, ToolExecutionResult

OUTPUT_LIMIT = 10000

logger = get_logger(__name__)


def _resolve_file(repo_root: str, raw_path: str) -> Path:
    root = Path(repo_root).resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (root / raw_path).resolve()
    else:
        candidate = candidate.resolve()
    candidate.relative_to(root)
    if not candidate.exists():
        raise FileNotFoundError(f"File not found: {raw_path}")
    if not candidate.is_file():
        raise ValueError(f"Not a file: {raw_path}")
    return candidate


def _render_with_line_numbers(lines: list[str], start_line: int) -> str:
    return "\n".join(f"{start_line + index}: {line}" for index, line in enumerate(lines))


def run_read_file(state: AgentState) -> dict:
    action = state["model_action"] or {}
    args = dict(action.get("args") or {})
    raw_path = str(args.get("path", "")).strip()
    start_line = max(1, int(args.get("start_line", 1)))
    end_line = max(start_line, int(args.get("end_line", start_line + 249)))
    log_node_start(
        logger,
        "read_file",
        state,
        path=raw_path,
        start_line=start_line,
        end_line=end_line,
    )

    try:
        path = _resolve_file(state["repo_root"], raw_path)
        raw_text = path.read_text(encoding="utf-8", errors="ignore")
        lines = raw_text.splitlines()
        total_lines = len(lines)
        bounded_end = min(end_line, total_lines) if total_lines else 0
        slice_lines = lines[start_line - 1 : bounded_end] if total_lines else []
        rendered = _render_with_line_numbers(slice_lines, start_line)
        rel_path = str(path.relative_to(Path(state["repo_root"]).resolve()))
        result: ToolExecutionResult = {
            "tool_name": "read_file",
            "args": {
                "path": raw_path,
                "start_line": start_line,
                "end_line": end_line,
            },
            "ok": True,
            "result": f"Read {rel_path}:{start_line}-{bounded_end or 0}",
            "raw_output": truncate_text(rendered, OUTPUT_LIMIT),
            "exit_code": 0,
            "metadata": {
                "path": rel_path,
                "start_line": start_line,
                "end_line": bounded_end,
                "total_lines": total_lines,
                "raw_content": "\n".join(slice_lines),
            },
        }
    except Exception as exc:
        result = {
            "tool_name": "read_file",
            "args": args,
            "ok": False,
            "result": str(exc),
            "raw_output": str(exc),
            "exit_code": None,
            "metadata": {},
        }

    state_update = {"current_tool_result": result}
    log_node_end(logger, "read_file", {**state, **state_update}, ok=result.get("ok"))
    return state_update

