from __future__ import annotations

import os
import subprocess
from pathlib import Path

from agent.state import AgentState, ToolResult

MATCH_LIMIT = 50
OUTPUT_LIMIT = 8000


def _truncate(text: str, limit: int = OUTPUT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n... [truncated]"


def _resolve_target(repo_root: str, raw_path: str) -> Path:
    root = Path(repo_root).resolve()
    candidate = (root / raw_path).resolve()
    candidate.relative_to(root)
    if not candidate.exists():
        raise FileNotFoundError(f"Search target not found: {raw_path}")
    return candidate


def _python_fallback(query: str, target: Path, repo_root: Path) -> list[str]:
    matches: list[str] = []
    if target.is_file():
        candidates = [target]
    else:
        candidates = [path for path in target.rglob("*") if path.is_file() and ".git" not in path.parts]

    for path in candidates:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for index, line in enumerate(lines, start=1):
            if query in line:
                matches.append(f"{path.relative_to(repo_root)}:{index}:{line.strip()}")
                break
        if len(matches) >= MATCH_LIMIT:
            break
    return matches


def run_search_files(state: AgentState) -> dict:
    action = state["next_action"] or {}
    query = str(action.get("query", "")).strip()
    raw_path = str(action.get("path", ".")).strip() or "."

    try:
        if not query:
            raise ValueError("Search query cannot be empty.")

        repo_root = Path(state["repo_root"]).resolve()
        target = _resolve_target(state["repo_root"], raw_path)
        target_arg = str(target.relative_to(repo_root))

        try:
            completed = subprocess.run(
                [
                    "rg",
                    "-n",
                    "--hidden",
                    "--glob",
                    "!.git",
                    "--max-count",
                    str(MATCH_LIMIT),
                    query,
                    target_arg,
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            stdout = completed.stdout.strip()
            if completed.returncode not in {0, 1}:
                raise RuntimeError(completed.stderr.strip() or "rg failed")
            matches = stdout.splitlines()[:MATCH_LIMIT] if stdout else []
        except FileNotFoundError:
            matches = _python_fallback(query, target, repo_root)

        summary = f"Search returned {len(matches)} matches for {query!r}"
        result: ToolResult = {
            "tool": "search_files",
            "ok": True,
            "summary": summary,
            "input": {"query": query, "path": raw_path},
            "data": {
                "path": target_arg,
                "matches": matches,
                "preview": _truncate("\n".join(matches)),
            },
        }
    except Exception as exc:
        result = {
            "tool": "search_files",
            "ok": False,
            "summary": str(exc),
            "input": {"query": query, "path": raw_path},
            "data": {},
            "error": str(exc),
        }

    return {"last_tool_result": result}
