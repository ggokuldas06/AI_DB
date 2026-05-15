from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langchain.agents import create_agent
import asyncio

from report_agents import make_planner_node, make_executor_node, ReportState, make_reporter_node

MCP_SERVER_URL = "http://localhost:8000/mcp"

def should_continue(state: ReportState) -> str:
    if state["current_index"] < len(state["planned_queries"]):
        return "executor"
    else:
        return "reporter"
    
async def run_report(user_request : str):
    client = MultiServerMCPClient(
        {
            "database": {
                "url": MCP_SERVER_URL,
                "transport": "streamable_http",
            }
        }
    )
    tools = await client.get_tools()
    print(f"Connected. Tools: {[t.name for t in tools]}")

    planner=make_planner_node(tools)
    executor=make_executor_node(tools)
    reporter=make_reporter_node()
    
    graph=StateGraph(ReportState)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("reporter", reporter)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("reporter", END)

    graph.add_conditional_edges(
        "executor",
        should_continue,
        {
            "executor": "executor",
            "reporter": "reporter",
        }
    )

    app=graph.compile()
    
    final_state=await app.ainvoke(
        {
            "user_request": user_request,
            "planned_queries": [],
            "current_index": 0,
            "results": [],
            "report": "",
        }
    )
    print("\n" + final_state["report"])

if __name__=="__main__":
    asyncio.run(run_report("generate a sales report across all regions"))
