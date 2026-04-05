from __future__ import annotations

import subprocess
from pathlib import Path

from agent.observability import get_logger, log_node_end, log_node_start
from agent.policies.command_policy import validate_command
from agent.policies.truncation import truncate_text
from agent.state import AgentState, ToolExecutionResult

OUTPUT_LIMIT = 8000

logger = get_logger(__name__)


def _resolve_workdir(repo_root: str, raw_workdir: str) -> Path:
    root = Path(repo_root).resolve()
    candidate = Path(raw_workdir)
    if not candidate.is_absolute():
        candidate = (root / raw_workdir).resolve()
    else:
        candidate = candidate.resolve()
    candidate.relative_to(root)
    if not candidate.exists():
        raise FileNotFoundError(f"Working directory not found: {raw_workdir}")
    if not candidate.is_dir():
        raise ValueError(f"Not a directory: {raw_workdir}")
    return candidate


def run_shell_command(state: AgentState) -> dict:
    action = state["model_action"] or {}
    args = dict(action.get("args") or {})
    command = str(args.get("command", "")).strip()
    raw_workdir = str(args.get("workdir", "")).strip()
    timeout_ms = int(args.get("timeout_ms", 10000))
    log_node_start(
        logger,
        "shell_command",
        state,
        command=command,
        workdir=raw_workdir,
        timeout_ms=timeout_ms,
    )

    try:
        tokens = validate_command(command)
        workdir = _resolve_workdir(state["repo_root"], raw_workdir)
        completed = subprocess.run(
            tokens,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=max(1, timeout_ms / 1000),
            check=False,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        combined_parts = []
        if stdout:
            combined_parts.append(stdout)
        if stderr:
            combined_parts.append(f"[stderr]\n{stderr}")
        combined = "\n\n".join(combined_parts) or f"Command exited with {completed.returncode}"
        result: ToolExecutionResult = {
            "tool_name": "shell_command",
            "args": {
                "command": command,
                "workdir": str(workdir),
                "timeout_ms": timeout_ms,
            },
            "ok": completed.returncode == 0,
            "result": stdout.splitlines()[0] if stdout else f"Command exited with {completed.returncode}",
            "raw_output": truncate_text(combined, OUTPUT_LIMIT),
            "exit_code": completed.returncode,
            "metadata": {
                "stdout": stdout,
                "stderr": stderr,
                "workdir": str(workdir),
                "command": command,
            },
        }
    except Exception as exc:
        result = {
            "tool_name": "shell_command",
            "args": args,
            "ok": False,
            "result": str(exc),
            "raw_output": str(exc),
            "exit_code": None,
            "metadata": {},
        }

    state_update = {"current_tool_result": result}
    log_node_end(logger, "shell_command", {**state, **state_update}, ok=result.get("ok"))
    return state_update

