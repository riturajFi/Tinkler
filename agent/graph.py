from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.observability import get_logger
from agent.nodes.agent_decide import agent_decide
from agent.nodes.apply_file_write import apply_file_write
from agent.nodes.build_agent_context import build_agent_context
from agent.nodes.check_termination import check_termination
from agent.nodes.finalize_answer import finalize_answer
from agent.nodes.init_turn import init_turn
from agent.nodes.record_observation import record_observation
from agent.nodes.route_agent_action import route_agent_action
from agent.state import AgentState, ToolResult
from agent.tools.list_dir import run_list_dir
from agent.tools.read_file import run_read_file
from agent.tools.search_files import run_search_files
from agent.tools.shell_command import run_shell_command
from agent.tools.write_file import stage_write_file

logger = get_logger(__name__)


def _route_action(state: AgentState) -> str:
    route = state["route"] or "finish"
    logger.info("route_action turn=%s route=%s", state["turn_index"], route)
    return route


def _route_termination(state: AgentState) -> str:
    route = "stop" if state["should_stop"] else "loop"
    logger.info(
        "route_termination turn=%s should_stop=%s route=%s reason=%r",
        state["turn_index"],
        state["should_stop"],
        route,
        state["stop_reason"],
    )
    return route


def _block_write_file(state: AgentState) -> dict:
    action = state["next_action"] or {}
    raw_path = str(action.get("path", "")).strip() or "<unknown>"
    result: ToolResult = {
        "tool": "write_file",
        "ok": False,
        "summary": f"Blocked write to {raw_path} because writes are disabled",
        "input": {"path": raw_path},
        "data": {"path": raw_path},
        "error": "write_file is disabled for this run",
    }
    return {
        "pending_write_path": None,
        "pending_write_content": None,
        "last_tool_result": result,
        "should_stop": True,
        "stop_reason": "write_blocked",
    }


def build_graph(*, allow_writes: bool = True):
    logger.info("build_graph allow_writes=%s", allow_writes)
    graph = StateGraph(AgentState)
    write_file_node = stage_write_file if allow_writes else _block_write_file

    graph.add_node("init_turn", init_turn)
    graph.add_node("build_agent_context", build_agent_context)
    graph.add_node("agent_decide", agent_decide)
    graph.add_node("route_agent_action", route_agent_action)
    graph.add_node("shell_command", run_shell_command)
    graph.add_node("read_file", run_read_file)
    graph.add_node("list_dir", run_list_dir)
    graph.add_node("search_files", run_search_files)
    graph.add_node("write_file", write_file_node)
    graph.add_node("record_observation", record_observation)
    graph.add_node("check_termination", check_termination)
    graph.add_node("finalize_answer", finalize_answer)

    # The graph always starts by resetting the agent's working state.
    graph.add_edge(START, "init_turn")
    
    # build context from - repo path + request
    graph.add_edge("init_turn", "build_agent_context")

    # Pass the built context and stored results from earlier tool calls into agent_decide.
    graph.add_edge("build_agent_context", "agent_decide")

    # Parse the decision and route to the right tool
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

    # Route back from the tool after execution to the record observation
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

    if allow_writes:
        graph.add_node("apply_file_write", apply_file_write)
        graph.add_edge("finalize_answer", "apply_file_write")
        graph.add_edge("apply_file_write", END)
    else:
        graph.add_edge("finalize_answer", END)

    return graph.compile()
