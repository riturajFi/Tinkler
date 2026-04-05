from __future__ import annotations

import shlex

ALLOWED_COMMANDS = {
    "pwd",
    "ls",
    "find",
    "rg",
    "git",
    "cat",
    "sed",
    "head",
    "tail",
    "wc",
    "tree",
    "python",
    "python3",
    "pytest",
    "uv",
    "pnpm",
    "npm",
    "yarn",
    "go",
    "cargo",
    "make",
}

SAFE_GIT_SUBCOMMANDS = {
    "status",
    "log",
    "rev-parse",
    "branch",
    "remote",
    "show",
    "ls-files",
    "diff",
}

FORBIDDEN_TOKENS = {"|", "&&", "||", ";", ">", ">>", "<"}


def validate_command(command: str) -> list[str]:
    tokens = shlex.split(command)
    if not tokens:
        raise ValueError("Shell command cannot be empty.")

    if any(token in FORBIDDEN_TOKENS for token in tokens):
        raise ValueError("Shell command cannot use pipes, chaining, or redirection. Use apply_patch for file writes.")

    if tokens[0] == "cd":
        raise ValueError("Use the workdir argument instead of cd.")

    root = tokens[0]
    if root not in ALLOWED_COMMANDS:
        raise ValueError(f"Unsupported shell command: {root}. Use apply_patch for creating or editing files.")

    if root == "git":
        if len(tokens) < 2 or tokens[1] not in SAFE_GIT_SUBCOMMANDS:
            raise ValueError("Unsupported git subcommand.")

    return tokens
