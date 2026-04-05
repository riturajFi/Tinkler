from __future__ import annotations

import re
import subprocess
from pathlib import Path

from agent.observability import get_logger, log_node_end, log_node_start
from agent.policies.truncation import truncate_text
from agent.state import AgentState, ToolExecutionResult

MATCH_LIMIT = 80
OUTPUT_LIMIT = 10000

logger = get_logger(__name__)


def _resolve_target(repo_root: str, raw_path: str) -> Path:
    root = Path(repo_root).resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (root / raw_path).resolve()
    else:
        candidate = candidate.resolve()
    candidate.relative_to(root)
    if not candidate.exists():
        raise FileNotFoundError(f"Search target not found: {raw_path}")
    return candidate


def _search_file_names(pattern: str, target: Path, repo_root: Path) -> list[str]:
    regex = re.compile(pattern)
    if target.is_file():
        candidates = [target]
    else:
        candidates = [path for path in target.rglob("*") if path.is_file() and ".git" not in path.parts]
    matches: list[str] = []
    for path in candidates:
        rel_path = str(path.relative_to(repo_root))
        if regex.search(rel_path):
            matches.append(rel_path)
        if len(matches) >= MATCH_LIMIT:
            break
    return matches


def _search_content(pattern: str, target: Path, repo_root: Path) -> list[str]:
    target_arg = str(target.relative_to(repo_root))
    completed = subprocess.run(
        [
            "rg",
            "-n",
            "--hidden",
            "--glob",
            "!.git",
            "--max-count",
            str(MATCH_LIMIT),
            pattern,
            target_arg,
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        raise RuntimeError(completed.stderr.strip() or "rg failed")
    return completed.stdout.strip().splitlines()[:MATCH_LIMIT] if completed.stdout.strip() else []


def run_search_files(state: AgentState) -> dict:
    action = state["model_action"] or {}
    args = dict(action.get("args") or {})
    pattern = str(args.get("pattern", "")).strip()
    raw_path = str(args.get("path", ".")).strip() or "."
    mode = str(args.get("mode", "content")).strip() or "content"
    log_node_start(logger, "search_files", state, pattern=pattern, path=raw_path, mode=mode)

    try:
        if not pattern:
            raise ValueError("Search pattern cannot be empty.")

        repo_root = Path(state["repo_root"]).resolve()
        target = _resolve_target(state["repo_root"], raw_path)
        if mode == "files":
            matches = _search_file_names(pattern, target, repo_root)
        else:
            matches = _search_content(pattern, target, repo_root)

        preview = "\n".join(matches)
        result: ToolExecutionResult = {
            "tool_name": "search_files",
            "args": {"pattern": pattern, "path": raw_path, "mode": mode},
            "ok": True,
            "result": f"Search returned {len(matches)} matches for {pattern!r}",
            "raw_output": truncate_text(preview or "No matches", OUTPUT_LIMIT),
            "exit_code": 0,
            "metadata": {
                "path": str(target.relative_to(repo_root)),
                "matches": matches,
                "mode": mode,
                "pattern": pattern,
            },
        }
    except Exception as exc:
        result = {
            "tool_name": "search_files",
            "args": args,
            "ok": False,
            "result": str(exc),
            "raw_output": str(exc),
            "exit_code": None,
            "metadata": {},
        }

    state_update = {"current_tool_result": result}
    log_node_end(logger, "search_files", {**state, **state_update}, ok=result.get("ok"))
    return state_update

