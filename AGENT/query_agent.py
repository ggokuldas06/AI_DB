import asyncio
import json
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from pydantic import BaseModel
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

MCP_SERVER_URL = os.environ["MCP_SERVER_URL"]


def _extract_text(raw) -> str:
    if isinstance(raw, list) and raw and isinstance(raw[0], dict) and "text" in raw[0]:
        return raw[0]["text"]
    return str(raw)


def _mcp_to_string(result) -> str:
    # Groq requires tool content to be a plain string — MCP returns a list
    if isinstance(result, list):
        try:
            rows = [
                json.loads(item["text"]) if isinstance(item, dict) and "text" in item else item
                for item in result
            ]
            return json.dumps(rows, indent=2)
        except Exception:
            return str(result)
    return str(result)


class _SQLInput(BaseModel):
    sql: str


def _wrap_run_tool(mcp_tool) -> StructuredTool:
    async def _run(sql: str) -> str:
        return _mcp_to_string(await mcp_tool.ainvoke({"sql": sql}))

    return StructuredTool.from_function(
        coroutine=_run,
        name="run_query_tool",
        description="Runs a PostgreSQL query and returns the results as JSON.",
        args_schema=_SQLInput,
    )


async def run_query(question: str) -> str:
    print("[query] connecting to MCP server...")
    client = MultiServerMCPClient({
        "database": {"url": MCP_SERVER_URL, "transport": "streamable_http"}
    })
    tools = await client.get_tools()

    schema_tool = next(t for t in tools if t.name == "get_schema_tool")
    run_tool    = _wrap_run_tool(next(t for t in tools if t.name == "run_query_tool"))

    print("[query] fetching schema...")
    schema = _extract_text(await schema_tool.ainvoke({}))
    print("[query] schema fetched, running agent...")

    system_prompt = (
        "You are a data analyst. The full database schema is below.\n"
        "Rules:\n"
        "- Use ONLY the exact table and column names from the schema. Never guess.\n"
        "- Write simple flat SELECT queries. Avoid CTEs and subqueries.\n"
        "- Call run_query_tool with your SQL.\n"
        "- Present results in clean readable markdown: table for multiple rows, "
        "bullets for single results. Include actual values. Be concise.\n\n"
        f"SCHEMA:\n{schema}"
    )

    agent = create_agent(
        model="groq:llama-3.1-8b-instant",
        tools=[run_tool],
        system_prompt=system_prompt,
    )

    result = await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
    print("[query] done")
    return result["messages"][-1].content


if __name__ == "__main__":
    async def main():
        answer = await run_query("Who is the top customer?")
        print(answer)
    asyncio.run(main())
