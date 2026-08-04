import asyncio
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


from sem_cache import llmcache

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent




MCP_SERVER_URL = os.environ["MCP_SERVER_URL"]



async def run_query(question: str) -> str:
    if llmcache.has(question):
        print("[query] cache hit")
        return llmcache.get(question)
    
    print("[query] connecting to MCP server...")
    client = MultiServerMCPClient({
        "database": {"url": MCP_SERVER_URL, "transport": "streamable_http"}
    })
    tools = await client.get_tools()
    print(f"[query] tools available: {[t.name for t in tools]}")

    agent = create_agent(
        model="groq:llama-3.1-8b-instant",
        tools=tools,
        system_prompt=(
            "You are a data analyst with access to a PostgreSQL database.\n"
            "Rules:\n"
            "- First call get_schema_tool to discover the available tables and columns.\n"
            "- Use ONLY the exact table and column names from the schema. Never guess.\n"
            "- Write simple flat SELECT queries. Avoid CTEs and subqueries.\n"
            "- Call run_query_tool with your SQL to fetch the data.\n"
            "- Present results in clean readable markdown: table for multiple rows, "
            "bullets for single results. Include actual values. Be concise."
        ),
    )

    result = await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
    print("[query] done")
    llmcache.set(question, result["messages"][-1].content)
    return result["messages"][-1].content


if __name__ == "__main__":
    async def main():
        answer = await run_query("Who is the top customer?")
        print(answer)
    asyncio.run(main())
