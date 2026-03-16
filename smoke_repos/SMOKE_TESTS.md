# Smoke Test Repos

Use these repos to check whether the graph can pick different tools.

## layout_catalog

Goal:
- bias toward `list_dir`

Example prompt:
- `Give me the folder structure of this repo`

Path:
- `smoke_repos/layout_catalog`

## entrypoint_service

Goal:
- bias toward `list_dir`, `search_files`, and `read_file`

Example prompts:
- `Find the entrypoints of this repo`
- `How does this service start?`

Path:
- `smoke_repos/entrypoint_service`

## search_cases

Goal:
- bias toward `search_files` and `read_file`

Example prompts:
- `Find where ISSUE-42 is handled`
- `What is the likely cause of ISSUE-42?`

Path:
- `smoke_repos/search_cases`

## Shell command checks

These are prompt-driven because `shell_command` is not the preferred tool.

Example prompts:
- `Use a shell command to tell me the current repo path`
- `Use a shell command to count files in this repo`
- `Use git status and summarize the result`

Note:
- `git` commands only work if the target repo itself is a git repo.
