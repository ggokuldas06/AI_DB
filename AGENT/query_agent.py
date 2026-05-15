import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient  
from langchain.agents import create_agent

MCP_SERVER_URL = "http://localhost:8000/mcp"

QUERY = "Get schema"

async def main():
    client = MultiServerMCPClient(
        {
            "database":{
                "url": MCP_SERVER_URL,
                "transport": "streamable_http",
            }
        }
    )
    tool_list=await client.get_tools()

    print(f"Connected. Tools available: {[t.name for t in tool_list]}\n")

    agent=create_agent(
        model="google_genai:gemini-2.5-flash-lite",
        tools=tool_list,
        system_prompt="You are an agent that returns the schema of a PostgreSQL database. Always use the provided tools to get the data, never make up data on your own.",
    )

    result=await agent.ainvoke({"messages":[{"role":"user","content":QUERY}]})

    final = result["messages"][-1].content
    print("Agent response:\n", final)

asyncio.run(main())