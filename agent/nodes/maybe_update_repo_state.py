from __future__ import annotations

import json
import re

from agent.observability import get_logger, log_node_end, log_node_start
from agent.state import AgentState

ENTRYPOINT_RE = re.compile(
    r"(^|/)(main|app|server|cli|index|__main__|graph)\.(py|ts|tsx|js|jsx|rs)$"
)

logger = get_logger(__name__)


def _merge_unique(existing: list[str], new_items: list[str]) -> list[str]:
    seen = set(existing)
    merged = list(existing)
    for item in new_items:
        if item and item not in seen:
            merged.append(item)
            seen.add(item)
    return merged


def _extract_match_paths(matches: list[str], *, mode: str) -> list[str]:
    if mode == "files":
        return [match.strip() for match in matches if match.strip()]
    paths: list[str] = []
    for match in matches:
        path = match.split(":", 1)[0].strip()
        if path:
            paths.append(path)
    return paths


def _update_name_facts(repo_facts: dict[str, object], files: list[str]) -> None:
    if any(path.endswith("pyproject.toml") for path in files):
        repo_facts.setdefault("language", "python")
    if any(path.endswith("package.json") for path in files):
        repo_facts.setdefault("language", "javascript")
    if any(path.endswith("tsconfig.json") for path in files):
        repo_facts["language"] = "typescript"
    if any(path.endswith("Cargo.toml") for path in files):
        repo_facts.setdefault("language", "rust")
    if any(path.endswith("pnpm-lock.yaml") for path in files):
        repo_facts["package_manager"] = "pnpm"
    if any(path.endswith("package-lock.json") for path in files):
        repo_facts.setdefault("package_manager", "npm")


def _update_content_facts(repo_facts: dict[str, object], path: str, raw_content: str) -> None:
    if path.endswith("pyproject.toml"):
        repo_facts["language"] = "python"
        name_match = re.search(r'(?m)^name\s*=\s*["\']([^"\']+)["\']', raw_content)
        if name_match:
            repo_facts["package_name"] = name_match.group(1)

    if path.endswith("package.json"):
        try:
            package_data = json.loads(raw_content)
        except json.JSONDecodeError:
            package_data = {}
        if package_data.get("name"):
            repo_facts["package_name"] = str(package_data["name"])
        dependencies = {
            *package_data.get("dependencies", {}).keys(),
            *package_data.get("devDependencies", {}).keys(),
        }
        if "typescript" in dependencies:
            repo_facts["language"] = "typescript"
        elif dependencies:
            repo_facts.setdefault("language", "javascript")
        if package_data.get("packageManager"):
            repo_facts["package_manager"] = str(package_data["packageManager"]).split("@", 1)[0]

    if path.endswith("Cargo.toml"):
        repo_facts["language"] = "rust"
        name_match = re.search(r'(?m)^name\s*=\s*"([^"]+)"', raw_content)
        if name_match:
            repo_facts["package_name"] = name_match.group(1)

    lower_content = raw_content.lower()
    has_api = any(token in lower_content for token in ["fastapi", "flask", "express", "router"])
    has_cli = any(token in lower_content for token in ["typer", "click", "argparse", "commander"])
    if has_api and has_cli:
        repo_facts["product_shape"] = "CLI + API service"
    elif has_api:
        repo_facts.setdefault("product_shape", "API service")
    elif has_cli:
        repo_facts.setdefault("product_shape", "CLI")

    if "__main__" in raw_content or "FastAPI(" in raw_content or "Typer(" in raw_content:
        repo_facts.setdefault("entrypoint", path)


def maybe_update_repo_state(state: AgentState) -> dict:
    log_node_start(logger, "maybe_update_repo_state", state)
    result = state.get("current_tool_result")
    if not result:
        log_node_end(logger, "maybe_update_repo_state", state, updated=False)
        return {}

    discovered_files = list(state["discovered_files"])
    discovered_dirs = list(state["discovered_dirs"])
    important_files = list(state["important_files"])
    repo_facts = dict(state["repo_facts"])
    changed_files = list(state["changed_files"])
    cwd = state["cwd"]
    repo_root = state["repo_root"]

    tool_name = result["tool_name"]
    metadata = dict(result.get("metadata") or {})
    args = dict(result.get("args") or {})

    if tool_name == "shell_command":
        cwd = str(metadata.get("workdir", cwd))
        stdout = str(metadata.get("stdout", ""))
        command = str(metadata.get("command", ""))
        if command == "pwd" and stdout:
            cwd = stdout.splitlines()[0].strip() or cwd
        if command == "git rev-parse --show-toplevel" and stdout:
            repo_root = stdout.splitlines()[0].strip() or repo_root
        if command.startswith("rg --files") and stdout:
            discovered_files = _merge_unique(discovered_files, stdout.splitlines())

    if tool_name == "list_dir":
        discovered_dirs = _merge_unique(discovered_dirs, list(metadata.get("dirs", [])))
        discovered_files = _merge_unique(discovered_files, list(metadata.get("files", [])))
        important_files = _merge_unique(important_files, list(metadata.get("files", []))[:10])

    if tool_name == "search_files":
        matches = list(metadata.get("matches", []))
        mode = str(metadata.get("mode", args.get("mode", "content")))
        matched_paths = _extract_match_paths(matches, mode=mode)
        discovered_files = _merge_unique(discovered_files, matched_paths)
        important_files = _merge_unique(important_files, matched_paths[:10])

    if tool_name == "read_file":
        path = str(metadata.get("path", ""))
        raw_content = str(metadata.get("raw_content", ""))
        if path:
            discovered_files = _merge_unique(discovered_files, [path])
            important_files = _merge_unique(important_files, [path])
        _update_content_facts(repo_facts, path, raw_content)
        if path and ENTRYPOINT_RE.search(path):
            important_files = _merge_unique(important_files, [path])
            repo_facts.setdefault("entrypoint", path)

    if tool_name == "apply_patch":
        patch_changed = list(metadata.get("changed_files", []))
        changed_files = _merge_unique(changed_files, patch_changed)
        discovered_files = _merge_unique(discovered_files, patch_changed)
        important_files = _merge_unique(important_files, patch_changed)

    _update_name_facts(repo_facts, discovered_files)

    if repo_facts.get("entrypoint"):
        important_files = _merge_unique(important_files, [str(repo_facts["entrypoint"])])

    state_update = {
        "cwd": cwd,
        "repo_root": repo_root,
        "discovered_files": discovered_files,
        "discovered_dirs": discovered_dirs,
        "important_files": important_files,
        "repo_facts": repo_facts,
        "changed_files": changed_files,
        "pending_patch": None if tool_name == "apply_patch" else state["pending_patch"],
        "current_tool_result": None,
    }
    log_node_end(
        logger,
        "maybe_update_repo_state",
        {**state, **state_update},
        updated=True,
        discovered_files=len(discovered_files),
    )
    return state_update

