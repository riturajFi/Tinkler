from __future__ import annotations

import json
import re
from pathlib import Path

from agent.state import AgentState

ENTRYPOINT_RE = re.compile(
    r"(^|/)(main|app|server|cli|index|__main__|graph)\.(py|ts|tsx|js|jsx|rs)$"
)


def _merge_unique(existing: list[str], new_items: list[str]) -> list[str]:
    seen = set(existing)
    merged = list(existing)
    for item in new_items:
        if item and item not in seen:
            merged.append(item)
            seen.add(item)
    return merged


def _extract_matched_paths(matches: list[str]) -> list[str]:
    paths: list[str] = []
    for match in matches:
        path = match.split(":", 1)[0].strip()
        if path:
            paths.append(path)
    return paths


def _update_name_facts(repo_facts: dict, files: list[str]) -> None:
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
    if any(path.endswith("poetry.lock") for path in files):
        repo_facts["package_manager"] = "poetry"
    if any(path.endswith("docker-compose.yml") or path.endswith("docker-compose.yaml") for path in files):
        repo_facts.setdefault("runtime", "docker-compose")


def _update_content_facts(repo_facts: dict, path: str, raw_content: str) -> None:
    file_name = Path(path).name

    if file_name == "pyproject.toml":
        repo_facts["language"] = "python"
        if "[tool.poetry]" in raw_content:
            repo_facts["package_manager"] = "poetry"
        elif "hatchling" in raw_content:
            repo_facts["package_manager"] = "hatch"
        elif "setuptools" in raw_content:
            repo_facts.setdefault("package_manager", "setuptools")
        name_match = re.search(r'(?m)^name\s*=\s*["\']([^"\']+)["\']', raw_content)
        if name_match:
            repo_facts["package_name"] = name_match.group(1)

    if file_name == "package.json":
        try:
            package_data = json.loads(raw_content)
        except json.JSONDecodeError:
            package_data = {}
        if package_data.get("name"):
            repo_facts["package_name"] = package_data["name"]
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

    if file_name == "Cargo.toml":
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


def _build_summary(repo_facts: dict, likely_entrypoints: list[str], current: str) -> str:
    parts: list[str] = []
    if repo_facts.get("language"):
        parts.append(str(repo_facts["language"]))
    if repo_facts.get("package_manager"):
        parts.append(str(repo_facts["package_manager"]))
    if repo_facts.get("package_name"):
        parts.append(f"package {repo_facts['package_name']}")
    if repo_facts.get("product_shape"):
        parts.append(str(repo_facts["product_shape"]))
    if repo_facts.get("entrypoint"):
        parts.append(f"entrypoint {repo_facts['entrypoint']}")
    elif likely_entrypoints:
        parts.append(f"candidate entrypoints: {', '.join(likely_entrypoints[:3])}")
    return "; ".join(parts) if parts else current


def record_observation(state: AgentState) -> dict:
    result = state["last_tool_result"]
    if result is None:
        return {}

    action = state["next_action"] or {"kind": "finish"}
    tool_history = state["tool_history"] + [
        {"turn": state["turn_index"], "action": action, "result": result}
    ]
    observation_text = result.get("summary") or result.get("error") or "No observation recorded."
    observations = state["observations"] + [
        {"turn": state["turn_index"], "text": observation_text}
    ]

    discovered_files = list(state["discovered_files"])
    discovered_dirs = list(state["discovered_dirs"])
    likely_entrypoints = list(state["likely_entrypoints"])
    repo_facts = dict(state["repo_facts"])
    data = result.get("data", {})
    tool_name = result.get("tool")

    if tool_name == "list_dir":
        discovered_files = _merge_unique(discovered_files, data.get("files", []))
        discovered_dirs = _merge_unique(discovered_dirs, data.get("dirs", []))

    if tool_name == "search_files":
        matched_paths = _extract_matched_paths(data.get("matches", []))
        discovered_files = _merge_unique(discovered_files, matched_paths)

    if tool_name in {"read_file", "write_file"}:
        path = data.get("path")
        if path:
            discovered_files = _merge_unique(discovered_files, [path])

    _update_name_facts(repo_facts, discovered_files)

    if tool_name == "read_file":
        path = data.get("path", "")
        raw_content = data.get("raw_content", "")
        _update_content_facts(repo_facts, path, raw_content)
        if path and (ENTRYPOINT_RE.search(path) or repo_facts.get("entrypoint") == path):
            likely_entrypoints = _merge_unique(likely_entrypoints, [path])

    if tool_name == "search_files":
        matches = _extract_matched_paths(data.get("matches", []))
        entrypoints = [path for path in matches if ENTRYPOINT_RE.search(path)]
        likely_entrypoints = _merge_unique(likely_entrypoints, entrypoints)

    if repo_facts.get("entrypoint"):
        likely_entrypoints = _merge_unique(likely_entrypoints, [str(repo_facts["entrypoint"])])

    working_summary = _build_summary(repo_facts, likely_entrypoints, state["working_summary"])
    return {
        "tool_history": tool_history,
        "observations": observations,
        "discovered_files": discovered_files,
        "discovered_dirs": discovered_dirs,
        "likely_entrypoints": likely_entrypoints,
        "repo_facts": repo_facts,
        "working_summary": working_summary,
    }
