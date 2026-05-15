import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient  
from langchain.agents import create_agent

MCP_SERVER_URL = "http://localhost:8000/mcp"

QUERY = "What are the top 5 customers by total amount spent?"


client = MultiServerMCPClient(
    {
        "database":{
            "url": MCP_SERVER_URL,
            "transport": "streamable_http",
        }
    }
)
tool_list=client.get_tools()

print(f"Connected. Tools available: {[t.name for t in tool_list]}\n")

agent=create_agent(
    model="google_genai:gemini-2.0-flash-lite",
    tools=tool_list,
    system_prompt="You are an agent that creates perfect PostgreSQL queries. use the given tools to get teh database " \
    "schema and then write the query to answer the user's question. Always use the tools to get the schema and never try " \
    "to write a query without knowing the schema. Always use the tools to get the schema and never try to write a query without knowing the sc" \
    "hema. Always use the tools to get the schema and never try to write a query without knowing the schema.",
)

result=agent.ainvoke({"messages":[{"role":"user","content":QUERY}]})


