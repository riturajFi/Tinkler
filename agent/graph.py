from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.nodes.agent_decide import agent_decide
from agent.nodes.apply_file_write import apply_file_write
from agent.nodes.build_agent_context import build_agent_context
from agent.nodes.check_termination import check_termination
from agent.nodes.finalize_answer import finalize_answer
from agent.nodes.init_turn import init_turn
from agent.nodes.record_observation import record_observation
from agent.nodes.route_agent_action import route_agent_action
from agent.state import AgentState
from agent.tools.list_dir import run_list_dir
from agent.tools.read_file import run_read_file
from agent.tools.search_files import run_search_files
from agent.tools.shell_command import run_shell_command
from agent.tools.write_file import stage_write_file


def _route_action(state: AgentState) -> str:
    return state["route"] or "finish"


def _route_termination(state: AgentState) -> str:
    return "stop" if state["should_stop"] else "loop"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("init_turn", init_turn)
    graph.add_node("build_agent_context", build_agent_context)
    graph.add_node("agent_decide", agent_decide)
    graph.add_node("route_agent_action", route_agent_action)
    graph.add_node("shell_command", run_shell_command)
    graph.add_node("read_file", run_read_file)
    graph.add_node("list_dir", run_list_dir)
    graph.add_node("search_files", run_search_files)
    graph.add_node("write_file", stage_write_file)
    graph.add_node("record_observation", record_observation)
    graph.add_node("check_termination", check_termination)
    graph.add_node("finalize_answer", finalize_answer)
    graph.add_node("apply_file_write", apply_file_write)

    graph.add_edge(START, "init_turn")
    graph.add_edge("init_turn", "build_agent_context")
    graph.add_edge("build_agent_context", "agent_decide")
    graph.add_edge("agent_decide", "route_agent_action")

    graph.add_conditional_edges(
        "route_agent_action",
        _route_action,
        {
            "shell_command": "shell_command",
            "read_file": "read_file",
            "list_dir": "list_dir",
            "search_files": "search_files",
            "write_file": "write_file",
            "finish": "check_termination",
        },
    )

    graph.add_edge("shell_command", "record_observation")
    graph.add_edge("read_file", "record_observation")
    graph.add_edge("list_dir", "record_observation")
    graph.add_edge("search_files", "record_observation")
    graph.add_edge("write_file", "record_observation")
    graph.add_edge("record_observation", "check_termination")

    graph.add_conditional_edges(
        "check_termination",
        _route_termination,
        {
            "loop": "agent_decide",
            "stop": "finalize_answer",
        },
    )

    graph.add_edge("finalize_answer", "apply_file_write")
    graph.add_edge("apply_file_write", END)

    return graph.compile()
