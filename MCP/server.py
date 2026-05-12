from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
from tools.get_schema import get_schema
from tools.run_query import run_query

mcp=FastMCP("database")

@mcp.tool()
def get_schema_tool() -> dict:
    """Returns the database schema as a list of tables, columns, and relationships."""
    return get_schema()

@mcp.tool()
def run_query_tool(sql: str) -> list[dict]:
    """Runs a SQL query and returns the results as a list of dictionaries."""
    return run_query(sql)

app=mcp.streamable_http_app()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],    
)

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

    