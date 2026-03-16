from __future__ import annotations

import shlex
import subprocess

from agent.observability import get_logger, log_node_end, log_node_start
from agent.state import AgentState, ToolResult

ALLOWED_COMMANDS = {"pwd", "ls", "find", "rg", "git", "cat", "sed", "head", "tail", "wc", "tree"}
SAFE_GIT_SUBCOMMANDS = {"status", "log", "rev-parse", "branch", "remote", "show", "ls-files", "diff"}
OUTPUT_LIMIT = 6000

logger = get_logger(__name__)


def _truncate(text: str, limit: int = OUTPUT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n... [truncated]"


def _validate_command(command: str) -> list[str]:
    tokens = shlex.split(command)
    if not tokens:
        raise ValueError("Shell command cannot be empty.")
    root = tokens[0]
    if root not in ALLOWED_COMMANDS:
        raise ValueError(f"Unsupported shell command: {root}")
    if root == "git":
        if len(tokens) < 2 or tokens[1] not in SAFE_GIT_SUBCOMMANDS:
            raise ValueError("Unsupported git subcommand.")
    return tokens


def run_shell_command(state: AgentState) -> dict:
    action = state["next_action"] or {}
    command = str(action.get("command", "")).strip()
    log_node_start(logger, "shell_command", state, command=command)

    try:
        tokens = _validate_command(command)
        completed = subprocess.run(
            tokens,
            cwd=state["repo_root"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        stdout = _truncate(completed.stdout.strip())
        stderr = _truncate(completed.stderr.strip())
        ok = completed.returncode == 0
        logger.info(
            "shell_command output command=%r returncode=%s stdout=%r stderr=%r",
            command,
            completed.returncode,
            stdout,
            stderr,
        )
        summary = stdout.splitlines()[0] if stdout else f"Command exited with {completed.returncode}"
        result: ToolResult = {
            "tool": "shell_command",
            "ok": ok,
            "summary": summary,
            "input": {"command": command},
            "data": {
                "stdout": stdout,
                "stderr": stderr,
                "returncode": completed.returncode,
            },
        }
        if not ok and stderr:
            result["error"] = stderr
    except Exception as exc:
        result = {
            "tool": "shell_command",
            "ok": False,
            "summary": str(exc),
            "input": {"command": command},
            "data": {},
            "error": str(exc),
        }

    state_update = {"last_tool_result": result}
    log_node_end(logger, "shell_command", {**state, **state_update})
    return state_update
