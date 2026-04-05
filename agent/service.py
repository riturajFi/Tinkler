from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.observability import get_logger
from agent.prompts.system_prompt import ALL_TOOLS
from agent.state import ToolName, create_initial_state

logger = get_logger(__name__)

FOCUS_GUIDES = {
    "overview": (
        "Analyze the repository and explain what it does, the main subsystems, "
        "the tech stack, and the most likely entrypoints."
    ),
    "architecture": (
        "Analyze the repository architecture. Explain the core modules, how "
        "control and data flow between them, and where the main boundaries are."
    ),
    "entrypoints": (
        "Identify the main entrypoints, startup paths, CLI or server surfaces, "
        "and how a new engineer should trace execution from them."
    ),
    "dependencies": (
        "Analyze the external dependencies, package or runtime tooling, and what "
        "they reveal about how this repository is built and run."
    ),
    "quality": (
        "Analyze the repository for engineering quality. Focus on structure, "
        "testing signals, risky areas, and likely maintenance concerns."
    ),
}

READ_ONLY_INSTRUCTIONS = (
    "Read-only mode: inspect the repository and answer from evidence only. "
    "Do not create, modify, or stage files."
)

RESPONSE_SHAPE = (
    "Ground the answer in the repository contents. Keep it concise, concrete, "
    "and useful to an engineer reading the repo for the first time."
)


@dataclass(slots=True)
class AgentRun:
    repo_root: Path
    request: str
    response: str
    model_name: str | None
    max_turns: int
    stop_reason: str | None
    turn_count: int
    tool_trace: list[str]
    changed_files: list[str]
    pending_write_path: str | None = None


def build_analysis_request(
    repo_root: str | Path,
    *,
    focus: str = "overview",
    question: str | None = None,
) -> str:
    root = Path(repo_root).expanduser().resolve()
    focus_key = focus if focus in FOCUS_GUIDES else "overview"
    task = question.strip() if question and question.strip() else FOCUS_GUIDES[focus_key]
    return (
        f"Repository: {root.name}\n"
        f"Path: {root}\n"
        f"{READ_ONLY_INSTRUCTIONS}\n"
        f"{RESPONSE_SHAPE}\n\n"
        f"Task:\n{task}"
    )


def _resolve_repo_root(repo: str | Path) -> Path:
    root = Path(repo).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Repository path not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {root}")
    return root


def _resolve_allowed_tools(allow_writes: bool) -> tuple[ToolName, ...]:
    if allow_writes:
        return ALL_TOOLS
    return tuple(tool for tool in ALL_TOOLS if tool != "apply_patch")


def _create_default_model(model_name: str, temperature: float) -> Any:
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model_name, temperature=temperature)


def _build_graph(*, allow_writes: bool) -> Any:
    from agent.graph import build_graph

    return build_graph(allow_writes=allow_writes)


def _describe_tool_call(tool_name: str, args: dict[str, Any]) -> str:
    if tool_name == "shell_command":
        return f"shell `{args.get('command', '')}` in {args.get('workdir', '.')}"
    if tool_name == "read_file":
        return (
            f"read {args.get('path', '?')}:"
            f"{args.get('start_line', 1)}-{args.get('end_line', 1)}"
        )
    if tool_name == "list_dir":
        return f"list {args.get('path', '.') or '.'} depth={args.get('max_depth', 2)}"
    if tool_name == "search_files":
        return (
            f"search {args.get('path', '.') or '.'} "
            f"mode={args.get('mode', 'content')} for {args.get('pattern', '')!r}"
        )
    if tool_name == "apply_patch":
        return "apply_patch"
    return tool_name


def _build_tool_trace(tool_history: list[dict[str, Any]]) -> list[str]:
    trace: list[str] = []
    for index, entry in enumerate(tool_history, start=1):
        tool_name = str(entry.get("tool_name", "unknown"))
        args = dict(entry.get("args", {}))
        action = _describe_tool_call(tool_name, args)
        status = "ok" if entry.get("ok") else "error"
        summary = str(entry.get("result", "")).strip()
        suffix = f" -> {summary}" if summary else ""
        trace.append(f"{index}. {action} [{status}]{suffix}")
    return trace


def run_agent(
    repo: str | Path,
    *,
    request: str,
    max_turns: int = 100,
    model_name: str | None = None,
    temperature: float = 0.0,
    model: Any | None = None,
    graph: Any | None = None,
    allow_writes: bool = True,
) -> AgentRun:
    repo_root = _resolve_repo_root(repo)
    resolved_model_name = model_name or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not request.strip():
        raise ValueError("request cannot be empty")
    logger.info(
        "run_agent start repo=%s model=%s max_turns=%s allow_writes=%s",
        repo_root,
        resolved_model_name,
        max_turns,
        allow_writes,
    )

    if model is None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required.")
        model = _create_default_model(resolved_model_name, temperature)

    graph = graph or _build_graph(allow_writes=allow_writes)
    state = create_initial_state(
        request=request,
        cwd=str(repo_root),
        repo_root=str(repo_root),
        max_turns=max_turns,
    )
    recursion_limit = max(25, max_turns * 8)
    allowed_tools = _resolve_allowed_tools(allow_writes)
    result = graph.invoke(
        state,
        config={
            "recursion_limit": recursion_limit,
            "configurable": {
                "model": model,
                "allowed_tools": allowed_tools,
            },
        },
    )
    logger.info(
        "run_agent end repo=%s turns=%s stop_reason=%r changed_files=%r",
        repo_root,
        result.get("turn_count"),
        result.get("stop_reason"),
        result.get("changed_files"),
    )

    changed_files = list(result.get("changed_files", []))
    if not allow_writes and changed_files:
        raise RuntimeError("Read-only run unexpectedly changed files.")

    tool_history = list(result.get("tool_history", []))
    return AgentRun(
        repo_root=repo_root,
        request=request,
        response=str(result.get("final_answer", "")).strip(),
        model_name=resolved_model_name,
        max_turns=max_turns,
        stop_reason=result.get("stop_reason"),
        turn_count=int(result.get("turn_count", 0)),
        tool_trace=_build_tool_trace(tool_history),
        changed_files=changed_files,
        pending_write_path=changed_files[0] if changed_files else None,
    )


def run_analysis(
    repo: str | Path,
    *,
    question: str | None = None,
    focus: str = "overview",
    max_turns: int = 30,
    model_name: str | None = None,
    temperature: float = 0.0,
    model: Any | None = None,
    graph: Any | None = None,
) -> AgentRun:
    repo_root = _resolve_repo_root(repo)
    request = build_analysis_request(repo_root, focus=focus, question=question)
    return run_agent(
        repo_root,
        request=request,
        max_turns=max_turns,
        model_name=model_name,
        temperature=temperature,
        model=model,
        graph=graph,
        allow_writes=False,
    )
