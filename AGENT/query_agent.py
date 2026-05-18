import asyncio
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

MCP_SERVER_URL = os.environ["MCP_SERVER_URL"]

SYSTEM_PROMPT = (
    "You are a PostgreSQL expert. Follow these rules strictly:\n"
    "1. ALWAYS call get_schema_tool first before writing any SQL.\n"
    "2. Use ONLY the exact table names and column names returned by get_schema_tool. Never guess or invent column names.\n"
    "3. After getting the schema, call run_query_tool to execute the SQL and return the results.\n"
    "4. Do not make up columns. If unsure, re-read the schema."
)

async def run_query(question: str) -> str:
    print(f"[query] connecting to MCP server...")
    client = MultiServerMCPClient({
        "database": {"url": MCP_SERVER_URL, "transport": "streamable_http"}
    })
    tools = await client.get_tools()
    print(f"[query] tools: {[t.name for t in tools]}")

    agent = create_agent(model="google_genai:gemini-2.0-flash-lite", tools=tools, system_prompt=SYSTEM_PROMPT)
    print(f"[query] running agent...")

    result = await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
    answer = result["messages"][-1].content
    print(f"[query] done")
    return answer


if __name__ == "__main__":
    async def main():
        answer = await run_query("What are the top 5 customers by total amount spent?")
        print(answer)
    asyncio.run(main())
