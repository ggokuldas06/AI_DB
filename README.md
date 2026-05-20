# aidb

Natural language interface over a PostgreSQL database using an agentic workflow.

## Branches

**`main`** — proper agentic workflow. Each agent receives tools and calls them dynamically. The query agent discovers the schema itself via `get_schema_tool` before writing SQL. The planner agent does the same before generating a query plan. No schema is injected manually into any prompt.

**`low-token-usage`** — reduced token consumption via prompt injection. The schema is fetched once and injected directly into the system prompt, so the agent skips the `get_schema_tool` call. Use this branch if token cost matters more than clean agentic behavior.

## Architecture

```
frontend (Vite)
    |
    v
API (FastAPI :8001)
    |-- /api/query  -> query_agent  (single-turn Q&A)
    |-- /api/report -> graph        (multi-step report)
    |
    v
MCP server (FastMCP :8000)
    |-- get_schema_tool  -> information_schema query
    |-- run_query_tool   -> raw SQL execution
    |
    v
PostgreSQL
```

### Guardrails middleware

Applied on every request before it reaches the agent:

- **Input**: blocks DDL patterns (`DROP`, `DELETE`, `TRUNCATE`, etc.) and prompt injection attempts. Rejects requests that are not about sales, customers, orders, products, or reports.
- **Output**: strips sensitive fields (`email`, `phone`, `credit_limit`, `notes`, `assigned_rep`) from JSON responses.

### Query agent (`AGENT/query_agent.py`)

Single-turn agent. Receives both MCP tools, calls `get_schema_tool` to read the live schema, then calls `run_query_tool` with the generated SQL. Returns a markdown-formatted answer.

### Report graph (`AGENT/graph.py` + `AGENT/report_agents.py`)

LangGraph state machine with three nodes:

```
planner -> executor (loop) -> reporter
```

- **planner**: agent with `get_schema_tool`. Discovers the schema, then returns a JSON array of `{name, sql}` pairs.
- **executor**: agent with `run_query_tool`. Executes one query per invocation, can fix and retry on failure. Loops until all planned queries are done.
- **reporter**: no tools. Synthesizes query results into a structured markdown report.

## Setup

**Database**

```bash
cd db
./setup.sh        # creates schema, seeds data, creates materialized views
```

Requires `DATABASE_URL` in `.env`.

**MCP server**

```bash
cd MCP
uvicorn server:app --port 8000
```

**API**

```bash
cd API
uvicorn main:app --port 8001
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `MCP_SERVER_URL` | URL of the MCP server (e.g. `http://localhost:8000/mcp`) |
| `GROQ_API_KEY` | Groq API key for the LLM |

## Dependencies

- `fastmcp` — MCP server
- `fastapi` + `uvicorn` — HTTP API
- `langchain` + `langchain-mcp-adapters` — agent and tool wiring
- `langgraph` — report graph state machine
- `psycopg2-binary` — PostgreSQL driver

