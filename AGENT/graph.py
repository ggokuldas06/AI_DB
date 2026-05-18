import asyncio
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END

from report_agents import make_planner_node, make_executor_node, make_reporter_node, ReportState

MCP_SERVER_URL = os.environ["MCP_SERVER_URL"]


def _should_continue(state: ReportState) -> str:
    if state["current_index"] < len(state["planned_queries"]):
        return "executor"
    return "reporter"


def _build_graph(tools):
    g = StateGraph(ReportState)
    g.add_node("planner", make_planner_node(tools))
    g.add_node("executor", make_executor_node(tools))
    g.add_node("reporter", make_reporter_node())
    g.add_edge(START, "planner")
    g.add_edge("planner", "executor")
    g.add_edge("reporter", END)
    g.add_conditional_edges("executor", _should_continue, {"executor": "executor", "reporter": "reporter"})
    return g.compile()


async def run_report(user_request: str) -> str:
    print(f"[report] connecting to MCP server...")
    client = MultiServerMCPClient({
        "database": {"url": MCP_SERVER_URL, "transport": "streamable_http"}
    })
    tools = await client.get_tools()
    print(f"[report] tools: {[t.name for t in tools]}")

    app = _build_graph(tools)
    print(f"[report] running graph...")

    final_state = await app.ainvoke({
        "user_request": user_request,
        "planned_queries": [],
        "current_index": 0,
        "results": [],
        "report": "",
    })

    report = final_state["report"]
    print(f"[report] done")
    return report


if __name__ == "__main__":
    async def main():
        report = await run_report("generate a sales report across all regions")
        print(report)
    asyncio.run(main())
