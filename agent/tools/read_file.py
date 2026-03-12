from __future__ import annotations

from pathlib import Path

from agent.state import AgentState, ToolResult

OUTPUT_LIMIT = 8000


def _truncate(text: str, limit: int = OUTPUT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n... [truncated]"


def _resolve_file(repo_root: str, raw_path: str) -> Path:
    root = Path(repo_root).resolve()
    candidate = (root / raw_path).resolve()
    candidate.relative_to(root)
    if not candidate.exists():
        raise FileNotFoundError(f"File not found: {raw_path}")
    if not candidate.is_file():
        raise ValueError(f"Not a file: {raw_path}")
    return candidate


def _render_with_line_numbers(lines: list[str], start_line: int) -> str:
    return "\n".join(f"{start_line + index}: {line}" for index, line in enumerate(lines))


def run_read_file(state: AgentState) -> dict:
    action = state["next_action"] or {}
    raw_path = str(action.get("path", "")).strip()
    start_line = max(1, int(action.get("start_line", 1)))
    end_line = max(start_line, int(action.get("end_line", start_line + 249)))

    try:
        path = _resolve_file(state["repo_root"], raw_path)
        raw_text = path.read_text(encoding="utf-8", errors="ignore")
        lines = raw_text.splitlines()
        total_lines = len(lines)
        bounded_end = min(end_line, total_lines) if total_lines else 0
        slice_lines = lines[start_line - 1 : bounded_end] if total_lines else []
        rendered = _truncate(_render_with_line_numbers(slice_lines, start_line))
        rel_path = str(path.relative_to(Path(state["repo_root"]).resolve()))
        result: ToolResult = {
            "tool": "read_file",
            "ok": True,
            "summary": f"Read {rel_path}:{start_line}-{bounded_end or 0}",
            "input": {
                "path": raw_path,
                "start_line": start_line,
                "end_line": end_line,
            },
            "data": {
                "path": rel_path,
                "start_line": start_line,
                "end_line": bounded_end,
                "total_lines": total_lines,
                "content": rendered,
                "raw_content": "\n".join(slice_lines),
            },
        }
    except Exception as exc:
        result = {
            "tool": "read_file",
            "ok": False,
            "summary": str(exc),
            "input": {
                "path": raw_path,
                "start_line": start_line,
                "end_line": end_line,
            },
            "data": {},
            "error": str(exc),
        }

    return {"last_tool_result": result}
