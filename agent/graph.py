from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.nodes.append_tool_result import append_tool_result
from agent.nodes.build_prompt_and_tools import build_prompt_and_tools
from agent.nodes.build_turn_context import build_turn_context
from agent.nodes.finalize_turn import finalize_turn
from agent.nodes.init_turn import init_turn
from agent.nodes.maybe_update_repo_state import maybe_update_repo_state
from agent.nodes.model_step import model_step
from agent.nodes.route_model_output import route_model_output
from agent.state import AgentState
from agent.tools.apply_patch import run_apply_patch
from agent.tools.list_dir import run_list_dir
from agent.tools.read_file import run_read_file
from agent.tools.search_files import run_search_files
from agent.tools.shell_command import run_shell_command


def _route_from_state(state: AgentState) -> str:
    return state["route"] or "finalize_turn"


def build_graph(*, allow_writes: bool = True):
    graph = StateGraph(AgentState)

    graph.add_node("init_turn", init_turn)
    graph.add_node("build_turn_context", build_turn_context)
    graph.add_node("build_prompt_and_tools", build_prompt_and_tools)
    graph.add_node("model_step", model_step)
    graph.add_node("route_model_output", route_model_output)
    graph.add_node("shell_command", run_shell_command)
    graph.add_node("read_file", run_read_file)
    graph.add_node("list_dir", run_list_dir)
    graph.add_node("search_files", run_search_files)
    graph.add_node("apply_patch", run_apply_patch)
    graph.add_node("append_tool_result", append_tool_result)
    graph.add_node("maybe_update_repo_state", maybe_update_repo_state)
    graph.add_node("finalize_turn", finalize_turn)

    graph.add_edge(START, "init_turn")
    graph.add_edge("init_turn", "build_turn_context")
    graph.add_edge("build_turn_context", "build_prompt_and_tools")
    graph.add_edge("build_prompt_and_tools", "model_step")
    graph.add_edge("model_step", "route_model_output")

    graph.add_conditional_edges(
        "route_model_output",
        _route_from_state,
        {
            "shell_command": "shell_command",
            "read_file": "read_file",
            "list_dir": "list_dir",
            "search_files": "search_files",
            "apply_patch": "apply_patch",
            "finalize_turn": "finalize_turn",
        },
    )

    graph.add_edge("shell_command", "append_tool_result")
    graph.add_edge("read_file", "append_tool_result")
    graph.add_edge("list_dir", "append_tool_result")
    graph.add_edge("search_files", "append_tool_result")
    graph.add_edge("apply_patch", "append_tool_result")

    graph.add_edge("append_tool_result", "maybe_update_repo_state")
    graph.add_edge("maybe_update_repo_state", "build_turn_context")
    graph.add_edge("finalize_turn", END)

    return graph.compile()
