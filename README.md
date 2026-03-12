# Tinkler

Minimal LangGraph repo agent for inspecting a codebase, deciding one action at a time, collecting observations, and writing a final artifact only after the loop is complete.

## Why This Repo Exists

Most repo agents are too rigid:

- inspect in a fixed order
- summarize too early
- write before they have enough evidence

Tinkler is built around a tighter control loop:

`think -> act -> observe -> decide again`

That makes it better suited to uneven repositories where the important clue might be in `pyproject.toml`, a test file, a shell script, or a nested package.

## Visual Overview

```mermaid
flowchart TD
    A([Start]) --> B[init_turn]
    B --> C[build_agent_context]
    C --> D[agent_decide]
    D --> E[route_agent_action]

    E -->|shell_command| F[shell_command]
    E -->|read_file| G[read_file]
    E -->|list_dir| H[list_dir]
    E -->|search_files| I[search_files]
    E -->|write_file| J[write_file]
    E -->|finish| L[check_termination]

    F --> K[record_observation]
    G --> K
    H --> K
    I --> K
    J --> K

    K --> L
    L -->|loop| D
    L -->|stop| M[finalize_answer]
    M --> N[apply_file_write]
    N --> O([End])

    classDef phase fill:#0f172a,stroke:#38bdf8,color:#e2e8f0,stroke-width:1.5px;
    classDef tool fill:#1e293b,stroke:#f59e0b,color:#f8fafc,stroke-width:1.5px;
    classDef gate fill:#3f3f46,stroke:#34d399,color:#f8fafc,stroke-width:1.5px;

    class B,C,D,M phase;
    class F,G,H,I,J tool;
    class E,K,L,N gate;
```

## Control Loop

```mermaid
flowchart LR
    A[Build Context] --> B[Model Chooses One Action]
    B --> C[Run Tool]
    C --> D[Record Observation]
    D --> E{Enough Information?}
    E -->|No| B
    E -->|Yes| F[Finalize Answer]
    F --> G[Apply Staged Write]

    classDef loop fill:#111827,stroke:#60a5fa,color:#f9fafb,stroke-width:1.5px;
    classDef result fill:#1f2937,stroke:#f97316,color:#f9fafb,stroke-width:1.5px;

    class A,B,D,E loop;
    class C,F,G result;
```

## Architecture

### State

The agent keeps a typed state object with:

- request and repo root
- turn counters and stop conditions
- working summary
- tool history
- observations
- discovered files and directories
- likely entrypoints
- repo facts
- pending write path and content
- final response

Core definition: [`agent/state.py`](agent/state.py)

### Graph

The graph is compiled in [`agent/graph.py`](agent/graph.py) and wires the execution order like this:

1. Initialize turn state.
2. Build prompt context from everything learned so far.
3. Ask the model for exactly one next action.
4. Route that action to the correct tool node.
5. Record the result as an observation.
6. Decide whether to loop or stop.
7. Generate the final answer.
8. Apply the staged file write.

### Available Actions

```mermaid
flowchart TD
    A[Agent Actions] --> B[shell_command]
    A --> C[read_file]
    A --> D[list_dir]
    A --> E[search_files]
    A --> F[write_file]
    A --> G[finish]

    B --> B1[terminal exploration]
    C --> C1[targeted file reads]
    D --> D1[structured directory scan]
    E --> E1[symbol and text discovery]
    F --> F1[stage content]
    F --> F2[defer write until end]
    G --> G1[stop the loop]

    classDef core fill:#111827,stroke:#60a5fa,color:#f9fafb,stroke-width:1.5px;
    classDef detail fill:#1f2937,stroke:#f59e0b,color:#f9fafb,stroke-width:1.5px;

    class A,B,C,D,E,F,G core;
    class B1,C1,D1,E1,F1,F2,G1 detail;
```

Tool implementations live under [`agent/tools`](agent/tools).

## Project Layout

```text
Tinkler/
├── agent/
│   ├── __main__.py           # CLI entrypoint
│   ├── graph.py              # LangGraph assembly
│   ├── state.py              # Typed agent state
│   ├── actions/              # decision schema + parser
│   ├── nodes/                # graph nodes
│   ├── prompts/              # system and context prompts
│   └── tools/                # filesystem and shell tools
├── pyproject.toml
└── README.md
```

## Execution Flow

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant CLI as CLI
    participant G as LangGraph
    participant M as Model
    participant T as Tool Node
    participant FS as Filesystem

    U->>CLI: run request
    CLI->>G: create initial state
    G->>M: build context + ask for next action
    M-->>G: structured decision
    G->>T: execute selected tool
    T->>FS: inspect or stage write
    FS-->>T: result
    T-->>G: tool result
    G->>M: updated context
    loop until stop
        M-->>G: next action or finish
        G->>T: run tool
        T->>FS: inspect
        FS-->>T: result
        T-->>G: observation
    end
    G->>M: finalize answer
    G-->>CLI: final response
    CLI-->>U: printed output
```

## Quick Start

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Configure

```bash
export OPENAI_API_KEY=your_key_here
export OPENAI_MODEL=gpt-4o-mini
```

### Run

```bash
python -m agent "write a repo summary" --cwd .
```

Example with a turn limit:

```bash
python -m agent "document this codebase" --cwd . --max-turns 12
```

Entrypoint: [`agent/__main__.py`](agent/__main__.py)

## Design Decisions

### One Action Per Turn

The model does not plan a long script. It picks one action, sees the result, and adapts. That keeps the loop grounded in repo reality instead of speculative planning.

### Deferred Writes

`write_file` stages output first. The actual write happens later in `apply_file_write`, after the final response is ready. This reduces premature mutations and keeps the run easier to reason about.

Related nodes:

- [`agent/tools/write_file.py`](agent/tools/write_file.py)
- [`agent/nodes/apply_file_write.py`](agent/nodes/apply_file_write.py)

### Structured Decisions

The model output is parsed into a typed action schema before routing. That keeps tool execution narrow and explicit.

Related files:

- [`agent/actions/schemas.py`](agent/actions/schemas.py)
- [`agent/actions/parser.py`](agent/actions/parser.py)
- [`agent/nodes/agent_decide.py`](agent/nodes/agent_decide.py)

## Current Stack

- Python 3.11+
- LangGraph
- LangChain OpenAI
- setuptools build backend

Source of truth: [`pyproject.toml`](pyproject.toml)

## What Makes It Different

```text
Fixed pipeline agents:
  inspect -> summarize -> write

Tinkler:
  context -> decide -> tool -> observe -> loop -> finalize
```

That difference is the whole architecture.
