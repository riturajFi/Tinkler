# Tinkler

Tinkler is a local repository agent built with LangGraph. It inspects a codebase in short decision loops, chooses one tool call at a time, updates its working context from the result, and only edits files through `apply_patch` when writes are allowed.

https://github.com/user-attachments/assets/029f8b77-e102-4bb5-912d-0a91f6fc334e


The repo currently contains three user-facing surfaces:

- `agent/`: the core LangGraph agent runtime
- `tinkler_cli/`: a read-only analysis CLI
- `tinkler_backend/`: a FastAPI backend with JSON and SSE endpoints
- `tinkler_desktop/`: a minimal Electron desktop shell for the backend

## What Tinkler Does

Tinkler is designed for repository inspection first and repository editing second.

- The core loop is `context -> prompt -> model action -> tool -> context update -> repeat`
- The model returns exactly one structured action per turn
- Tool calls are bounded and explicit
- Read-only analysis runs disable `apply_patch`
- Writable runs allow in-loop patch application instead of deferred file staging

This makes the behavior easier to test and reason about than a loose "agent with tools" setup.

## Architecture

The graph is defined in `agent/graph.py` and is composed of small nodes with explicit state updates:

```text
START
  -> init_turn
  -> build_turn_context
  -> build_prompt_and_tools
  -> model_step
  -> route_model_output
     -> shell_command
     -> read_file
     -> list_dir
     -> search_files
     -> apply_patch
     -> finalize_turn

tool node
  -> append_tool_result
  -> maybe_update_repo_state
  -> build_turn_context
  -> ...

finalize_turn -> END
```

Core pieces:

- `agent/state.py`: typed state, action, message, and tool result shapes
- `agent/service.py`: high-level runtime helpers such as `run_agent`, `run_analysis`, and `iter_agent_events`
- `agent/nodes/`: graph nodes for prompt building, model execution, routing, loop updates, and finalization
- `agent/prompts/`: system prompt and turn-context construction
- `agent/tools/`: repo-safe tool implementations
- `agent/policies/`: routing and loop guard policies

## Available Tools

The agent currently exposes five internal tools:

- `shell_command`: bounded shell execution for exploration and testing
- `read_file`: file reads without shelling out
- `list_dir`: bounded directory inspection
- `search_files`: content or filename search
- `apply_patch`: Codex-style patch application for writes

Tool schemas are declared in `agent/prompts/system_prompt.py`. Routing from model output into those tools is handled in `agent/nodes/route_model_output.py`.

## Loop Controls

The loop is intentionally constrained.

- `max_turns` stops the run after a configured number of model decisions
- `allow_writes=False` removes `apply_patch` from the allowed tool set
- `agent/policies/loop_guard.py` can stop the run based on state or repeated actions
- `route_model_output` finalizes immediately on `final_answer`, missing model output, or loop guard stop conditions

The current loop guard threshold for identical tool requests is very high, so `max_turns` is the main practical brake unless you lower that policy.

## Repository Layout

```text
Tinkler/
├── agent/
│   ├── actions/
│   ├── nodes/
│   ├── policies/
│   ├── prompts/
│   ├── tools/
│   ├── graph.py
│   ├── service.py
│   └── state.py
├── tinkler_cli/
├── tinkler_backend/
├── tinkler_desktop/
├── tests/
├── dummy_repo/
├── smoke_repos/
├── pyproject.toml
└── README.md
```

Supporting directories:

- `tests/`: unit tests for the agent loop, CLI behavior, backend API, and event streaming
- `dummy_repo/`: a small Python repo used as a realistic target during development
- `smoke_repos/`: fixture repositories for search and layout scenarios

## Requirements

- Python 3.11+
- An OpenAI API key in `OPENAI_API_KEY`
- Node.js if you want to run the Electron desktop app

Python dependencies are declared in `pyproject.toml`:

- `langgraph`
- `langchain-openai`
- `fastapi`
- `uvicorn`

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
export OPENAI_API_KEY=your_key_here
```

Optional environment variables:

- `OPENAI_MODEL`: overrides the default model, which is currently `gpt-4o-mini`
- `AGENT_LOG_LEVEL`: logging level for the core agent
- `TINKLER_BACKEND_HOST`: backend bind host, default `127.0.0.1`
- `TINKLER_BACKEND_PORT`: backend bind port, default `8000`
- `TINKLER_BACKEND_URL`: desktop app target URL, default `http://127.0.0.1:8000`

## Using The Core Agent

The direct Python entrypoint is `python3 -m agent`.

Writable run:

```bash
python3 -m agent "Add a short contributing guide to the repository root" --cwd .
```

Useful flags:

- `--cwd`: repo root to inspect
- `--max-turns`: maximum agent turns, default `30`
- `--model`: model name
- `--log-level`: Python log level

This entrypoint requires `OPENAI_API_KEY` and runs with `allow_writes=True`.

## CLI Usage

The installed CLI command is `tinkler`. It is built for read-only repository analysis.

Run it interactively:

```bash
tinkler --cwd .
```

Run a single request:

```bash
tinkler "Explain the architecture of this repo" --cwd .
```

Write the analysis to a file:

```bash
tinkler "Summarize the backend API" --cwd . --output reports/backend.md
```

Useful flags:

- `--trace`: append the tool trace to the plain-text response
- `--json`: emit structured JSON output
- `--max-turns`: maximum analysis turns
- `--model`: OpenAI model name

Under the hood the CLI calls `run_analysis(...)`, which wraps the request in read-only instructions and disables `apply_patch`.

## Backend API

Start the backend:

```bash
tinkler-backend
```

or:

```bash
python3 -m tinkler_backend
```

Routes:

- `GET /health`
- `POST /api/v1/agent/runs`
- `POST /api/v1/agent/runs/stream`

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agent/runs \
  -H "Content-Type: application/json" \
  -d '{
    "cwd": ".",
    "request": "Explain this repository",
    "max_turns": 20,
    "allow_writes": false
  }'
```

`/api/v1/agent/runs/stream` returns server-sent events produced by `iter_agent_events(...)`. The event stream includes:

- `run.started`
- `loop.progress`
- `model.action`
- `tool.result`
- `run.completed`
- `run.failed`

## Desktop App

`tinkler_desktop/` is a minimal Electron wrapper around the backend.

Install and run:

```bash
npm install --prefix tinkler_desktop
npm --prefix tinkler_desktop start
```

The desktop app will try to connect to an existing backend first. If none is running, it attempts to start one with:

```bash
.venv/bin/python -m tinkler_backend
```

If `.venv/bin/python` does not exist, it falls back to `python3`.

## Development Notes

The codebase is small and intentionally split by responsibility.

- Graph wiring lives in `agent/graph.py`
- High-level orchestration lives in `agent/service.py`
- Tool implementations are plain Python functions in `agent/tools/`
- FastAPI integration is isolated under `tinkler_backend/`
- The Electron shell is isolated under `tinkler_desktop/`

This separation makes it straightforward to test the graph without running a real model or web server.

## Testing

Run the Python test suite:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

Run desktop checks:

```bash
npm --prefix tinkler_desktop run check
npm --prefix tinkler_desktop test
```

Current test coverage focuses on:

- agent loop behavior
- parser normalization and fallback behavior
- in-loop `apply_patch`
- read-only analysis safeguards
- backend route registration and SSE formatting
- event stream emission
- desktop backend-client parsing

## Current Status

The repo is already useful as a compact reference implementation for:

- a LangGraph-based repo agent
- read-only analysis vs writable execution modes
- streaming agent progress over SSE
- wrapping a local Python backend in Electron

It is still intentionally minimal. The strongest next steps would likely be richer tool policies, stronger loop-guard heuristics, and broader integration tests across the CLI, backend, and desktop surfaces.
