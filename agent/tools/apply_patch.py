from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent.observability import get_logger, log_node_end, log_node_start
from agent.state import AgentState, ToolExecutionResult

logger = get_logger(__name__)


@dataclass(slots=True)
class PatchOperation:
    kind: str
    path: str
    move_to: str | None = None
    add_lines: list[str] | None = None
    hunks: list[list[str]] | None = None


def _resolve_repo_path(repo_root: str, raw_path: str) -> Path:
    root = Path(repo_root).resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = (root / raw_path).resolve()
    else:
        candidate = candidate.resolve()
    candidate.relative_to(root)
    return candidate


def _parse_patch(patch: str) -> list[PatchOperation]:
    lines = patch.splitlines()
    if not lines or lines[0] != "*** Begin Patch":
        raise ValueError("Patch must start with '*** Begin Patch'")

    operations: list[PatchOperation] = []
    index = 1
    while index < len(lines):
        line = lines[index]
        if line == "*** End Patch":
            return operations

        if line.startswith("*** Add File: "):
            path = line[len("*** Add File: ") :].strip()
            index += 1
            add_lines: list[str] = []
            while index < len(lines) and not lines[index].startswith("*** "):
                current = lines[index]
                if not current.startswith("+"):
                    raise ValueError("Add file lines must start with '+'")
                add_lines.append(current[1:])
                index += 1
            operations.append(PatchOperation(kind="add", path=path, add_lines=add_lines))
            continue

        if line.startswith("*** Delete File: "):
            path = line[len("*** Delete File: ") :].strip()
            operations.append(PatchOperation(kind="delete", path=path))
            index += 1
            continue

        if line.startswith("*** Update File: "):
            path = line[len("*** Update File: ") :].strip()
            index += 1
            move_to: str | None = None
            if index < len(lines) and lines[index].startswith("*** Move to: "):
                move_to = lines[index][len("*** Move to: ") :].strip()
                index += 1

            hunks: list[list[str]] = []
            current_hunk: list[str] = []
            saw_hunk = False
            while index < len(lines) and not lines[index].startswith("*** "):
                current = lines[index]
                if current.startswith("@@"):
                    saw_hunk = True
                    if current_hunk:
                        hunks.append(current_hunk)
                        current_hunk = []
                elif current == "*** End of File":
                    pass
                else:
                    if current[:1] not in {" ", "+", "-"}:
                        raise ValueError(f"Invalid patch line: {current}")
                    current_hunk.append(current)
                index += 1

            if current_hunk:
                hunks.append(current_hunk)
            if not saw_hunk and not hunks:
                raise ValueError(f"Update for {path} has no hunks")
            operations.append(PatchOperation(kind="update", path=path, move_to=move_to, hunks=hunks))
            continue

        raise ValueError(f"Unexpected patch header: {line}")

    raise ValueError("Patch is missing '*** End Patch'")


def _original_lines_for_hunk(hunk: list[str]) -> list[str]:
    return [line[1:] for line in hunk if line[:1] in {" ", "-"}]


def _find_hunk_position(original_lines: list[str], hunk: list[str], start_index: int) -> int:
    anchor = _original_lines_for_hunk(hunk)
    if not anchor:
        return min(start_index, len(original_lines))

    max_index = len(original_lines) - len(anchor)
    for index in range(start_index, max_index + 1):
        if original_lines[index : index + len(anchor)] == anchor:
            return index

    for index in range(0, max_index + 1):
        if original_lines[index : index + len(anchor)] == anchor:
            return index

    raise ValueError("Could not match patch hunk against file contents")


def _apply_hunks(original_lines: list[str], hunks: list[list[str]]) -> list[str]:
    output: list[str] = []
    cursor = 0
    for hunk in hunks:
        hunk_start = _find_hunk_position(original_lines, hunk, cursor)
        output.extend(original_lines[cursor:hunk_start])
        current_index = hunk_start
        for patch_line in hunk:
            prefix = patch_line[:1]
            text = patch_line[1:]
            if prefix == " ":
                if current_index >= len(original_lines) or original_lines[current_index] != text:
                    raise ValueError("Patch context did not match file contents")
                output.append(original_lines[current_index])
                current_index += 1
            elif prefix == "-":
                if current_index >= len(original_lines) or original_lines[current_index] != text:
                    raise ValueError("Patch deletion did not match file contents")
                current_index += 1
            elif prefix == "+":
                output.append(text)
            else:
                raise ValueError(f"Invalid patch line prefix: {prefix}")
        cursor = current_index
    output.extend(original_lines[cursor:])
    return output


def _join_lines(lines: list[str]) -> str:
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def run_apply_patch(state: AgentState) -> dict:
    action = state["model_action"] or {}
    args = dict(action.get("args") or {})
    patch = str(args.get("patch", ""))
    log_node_start(logger, "apply_patch", state, patch_chars=len(patch))

    try:
        repo_root = Path(state["repo_root"]).resolve()
        operations = _parse_patch(patch)
        changed_files: list[str] = []

        for operation in operations:
            source_path = _resolve_repo_path(state["repo_root"], operation.path)
            if operation.kind == "add":
                if source_path.exists():
                    raise ValueError(f"File already exists: {operation.path}")
                source_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_text(_join_lines(operation.add_lines or []), encoding="utf-8")
                changed_files.append(str(source_path.relative_to(repo_root)))
                continue

            if operation.kind == "delete":
                if not source_path.exists():
                    raise FileNotFoundError(f"File not found: {operation.path}")
                if not source_path.is_file():
                    raise ValueError(f"Not a file: {operation.path}")
                source_path.unlink()
                changed_files.append(str(source_path.relative_to(repo_root)))
                continue

            if operation.kind != "update":
                raise ValueError(f"Unsupported operation: {operation.kind}")

            if not source_path.exists():
                raise FileNotFoundError(f"File not found: {operation.path}")
            if not source_path.is_file():
                raise ValueError(f"Not a file: {operation.path}")

            original_text = source_path.read_text(encoding="utf-8", errors="ignore")
            original_lines = original_text.splitlines()
            updated_lines = _apply_hunks(original_lines, operation.hunks or [])
            target_path = source_path
            if operation.move_to:
                target_path = _resolve_repo_path(state["repo_root"], operation.move_to)
                target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(_join_lines(updated_lines), encoding="utf-8")
            if operation.move_to and target_path != source_path and source_path.exists():
                source_path.unlink()
                changed_files.append(str(source_path.relative_to(repo_root)))
            changed_files.append(str(target_path.relative_to(repo_root)))

        unique_changed = list(dict.fromkeys(changed_files))
        result: ToolExecutionResult = {
            "tool_name": "apply_patch",
            "args": {"patch": patch},
            "ok": True,
            "result": f"Applied patch touching {len(unique_changed)} file(s)",
            "raw_output": "\n".join(unique_changed) if unique_changed else "Patch applied",
            "exit_code": 0,
            "metadata": {"changed_files": unique_changed},
        }
    except Exception as exc:
        result = {
            "tool_name": "apply_patch",
            "args": args,
            "ok": False,
            "result": str(exc),
            "raw_output": str(exc),
            "exit_code": None,
            "metadata": {},
        }

    state_update = {"current_tool_result": result}
    log_node_end(logger, "apply_patch", {**state, **state_update}, ok=result.get("ok"))
    return state_update
