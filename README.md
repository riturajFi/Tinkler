# Tinkler

<p align="center">
  <strong>A repo agent that thinks in loops, not scripts.</strong>
</p>

<p align="center">
  Tinkler uses LangGraph to inspect a codebase, choose one action at a time, collect evidence, and only write once it has enough signal.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-0f172a?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/LangGraph-Agent%20Loop-1d4ed8?style=for-the-badge" alt="LangGraph Agent Loop">
  <img src="https://img.shields.io/badge/OpenAI-Structured%20Decisions-16a34a?style=for-the-badge" alt="OpenAI Structured Decisions">
</p>

---

## The Pitch

Most repo agents still behave like this:

```text
inspect -> summarize -> write
```

That looks neat, but it breaks as soon as the repo stops being neat.

Tinkler is built around a tighter loop:

```text
context -> decide -> tool -> observe -> loop -> finalize
```

It does not assume where the truth lives. It finds it.

---

## Why It Feels Different

| Traditional Repo Agent | Tinkler |
| --- | --- |
| follows a fixed inspection order | adapts every turn |
| plans too much up front | chooses one action at a time |
| writes early | stages writes and applies them at the end |
| treats tool output as terminal | turns tool output into new context |
| fragile on odd repo layouts | works better on uneven, real-world codebases |

---

## Architecture At A Glance

```mermaid
flowchart TD
    A([User Request]) --> B[init_turn]
    B --> C[build_agent_context]
    C --> D[agent_decide]
    D --> E{route_agent_action}

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
    N --> O([Done])

    classDef core fill:#0b1220,stroke:#60a5fa,color:#eff6ff,stroke-width:1.5px;
    classDef tools fill:#1f2937,stroke:#f59e0b,color:#fff7ed,stroke-width:1.5px;
    classDef gates fill:#14532d,stroke:#4ade80,color:#f0fdf4,stroke-width:1.5px;

    class B,C,D,M core;
    class F,G,H,I,J tools;
    class E,K,L,N gates;
```

---

## The Core Loop

```mermaid
flowchart LR
    A[Build Context] --> B[Choose One Action]
    B --> C[Run Tool]
    C --> D[Capture Result]
    D --> E[Update Working Summary]
    E --> F{Stop Yet?}
    F -->|No| B
    F -->|Yes| G[Generate Final Answer]
    G --> H[Apply Staged Write]

    classDef dark fill:#111827,stroke:#93c5fd,color:#f9fafb,stroke-width:1.5px;
    classDef accent fill:#3f3f46,stroke:#fbbf24,color:#fffbeb,stroke-width:1.5px;

    class A,B,D,E,F dark;
    class C,G,H accent;
```

This is the whole design: every action earns the next action.

---

## Agent Surface

```mermaid
flowchart TD
    A[Decision Model] --> B[shell_command]
    A --> C[read_file]
    A --> D[list_dir]
    A --> E[search_files]
    A --> F[write_file]
    A --> G[finish]

    B --> B1[terminal exploration]
    C --> C1[targeted file inspection]
    D --> D1[structured tree discovery]
    E --> E1[text and symbol lookup]
    F --> F1[stage artifact for later write]
    G --> G1[exit loop]

    classDef root fill:#172554,stroke:#60a5fa,color:#eff6ff,stroke-width:1.5px;
    classDef leaf fill:#1f2937,stroke:#f97316,color:#fff7ed,stroke-width:1.5px;

    class A,B,C,D,E,F,G root;
    class B1,C1,D1,E1,F1,G1 leaf;
```

Types and routing live in [`agent/state.py`](agent/state.py), [`agent/actions/schemas.py`](agent/actions/schemas.py), and [`agent/graph.py`](agent/graph.py).

---

## Repo Layout

```text
Tinkler/
├── agent/
│   ├── __main__.py
│   ├── graph.py
│   ├── state.py
│   ├── actions/
│   │   ├── parser.py
│   │   └── schemas.py
│   ├── nodes/
│   │   ├── agent_decide.py
│   │   ├── build_agent_context.py
│   │   ├── check_termination.py
│   │   ├── finalize_answer.py
│   │   ├── init_turn.py
│   │   ├── record_observation.py
│   │   └── route_agent_action.py
│   ├── prompts/
│   └── tools/
├── pyproject.toml
└── README.md
```

---

## What Happens In One Run

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant CLI as CLI
    participant G as Graph
    participant M as Model
    participant T as Tool
    participant R as Repo

    U->>CLI: "document this repository"
    CLI->>G: create initial state
    G->>M: provide context
    M-->>G: structured next action
    G->>T: run selected tool
    T->>R: inspect files or stage output
    R-->>T: result
    T-->>G: tool result
    G->>G: record observation
    G->>G: check termination
    loop until enough evidence
        G->>M: updated context
        M-->>G: next action
        G->>T: run tool
        T->>R: inspect
        R-->>T: result
        T-->>G: observation
    end
    G->>M: finalize response
    G->>R: apply staged write
    G-->>CLI: final response
```

---

## Quick Start

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure

```bash
export OPENAI_API_KEY=your_key_here
export OPENAI_MODEL=gpt-4o-mini
```

### 3. Run

```bash
python -m agent "write a repo summary" --cwd .
```

With an explicit turn limit:

```bash
python -m agent "document this codebase" --cwd . --max-turns 12
```

Entrypoint: [`agent/__main__.py`](agent/__main__.py)

---

## Design Choices

### One Action Per Turn

The model is forced to stay grounded. It does not invent a long multi-step script and hope it still makes sense three tool calls later.

### Deferred Writes

`write_file` prepares content first. The actual write is applied later by [`agent/nodes/apply_file_write.py`](agent/nodes/apply_file_write.py), after the answer is finalized. That keeps mutation controlled.

### Structured Decisions

The model emits typed decisions, parsed through [`agent/actions/parser.py`](agent/actions/parser.py) and [`agent/actions/schemas.py`](agent/actions/schemas.py), before the graph routes execution.

---

## Stack

- Python 3.11+
- LangGraph
- LangChain OpenAI
- setuptools

Dependency source: [`pyproject.toml`](pyproject.toml)

---

## Key Files

- [`agent/graph.py`](agent/graph.py): graph assembly and routing
- [`agent/nodes/agent_decide.py`](agent/nodes/agent_decide.py): structured action selection
- [`agent/state.py`](agent/state.py): typed runtime state
- [`agent/tools/write_file.py`](agent/tools/write_file.py): deferred write staging
- [`agent/__main__.py`](agent/__main__.py): CLI entrypoint

---

## Summary

Tinkler is a small repo agent with a strong constraint: it must learn from each step before taking the next one. That single choice makes the rest of the architecture make sense.
