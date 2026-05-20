import json
from typing import TypedDict

from langchain.agents import create_agent


class ReportState(TypedDict):
    user_request: str
    planned_queries: list[dict]
    current_index: int
    results: list[dict]
    report: str


def make_planner_node(tools):
    schema_tool = [t for t in tools if t.name == "get_schema_tool"]

    agent = create_agent(
        model="groq:llama-3.1-8b-instant",
        tools=schema_tool,
        system_prompt=(
            "You are a PostgreSQL expert. "
            "Call get_schema_tool to discover the available tables and columns, "
            "then plan 3 to 5 useful SQL queries to answer the user's request.\n"
            "Rules:\n"
            "- Use ONLY the exact table and column names returned by get_schema_tool.\n"
            "- Prefer pre-aggregated materialized views (mv_*) over raw tables when available.\n"
            "- Write simple SELECT queries — no CTEs, no JOINs between MV tables.\n"
            "Return ONLY a valid JSON array, no explanation, no markdown:\n"
            '[{"name": "metric name", "sql": "SELECT ..."}, ...]'
        ),
    )

    async def planner_node(state: ReportState) -> dict:
        print(f"[planner] {state['user_request']}")
        r = await agent.ainvoke({"messages": [{"role": "user", "content": state["user_request"]}]})
        c = r["messages"][-1].content
        planned_queries = json.loads(c[c.find("["):c.rfind("]") + 1])
        print(f"[planner] {len(planned_queries)} queries planned")
        return {"planned_queries": planned_queries, "current_index": 0, "results": []}

    return planner_node


def make_executor_node(tools):
    run_tool = [t for t in tools if t.name == "run_query_tool"]

    agent = create_agent(
        model="groq:llama-3.1-8b-instant",
        tools=run_tool,
        system_prompt=(
            "You are a SQL executor. "
            "Run the given SQL query using run_query_tool and return the raw results as JSON. "
            "If the query fails, try to fix the SQL and retry once."
        ),
    )

    async def executor_node(state: ReportState) -> dict:
        idx = state["current_index"]
        task = state["planned_queries"][idx]
        print(f"[executor] {idx + 1}/{len(state['planned_queries'])} {task['name']}")

        try:
            r = await agent.ainvoke({
                "messages": [{"role": "user", "content": f"Execute this SQL and return the results:\n{task['sql']}"}]
            })
            summary = r["messages"][-1].content
            print(f"[executor] - pass - {task['name']}")
        except Exception as e:
            summary = f"Query failed: {str(e)[:120]}"
            print(f"[executor] - fail - {task['name']} — {str(e)[:80]}")

        return {
            "results": state["results"] + [{"name": task["name"], "data": summary}],
            "current_index": idx + 1,
        }

    return executor_node


def make_reporter_node():
    agent = create_agent(model="groq:llama-3.1-8b-instant", tools=[])

    async def reporter_node(state: ReportState) -> dict:
        print("[reporter] generating final report...")
        results_block = "\n\n".join(
            f"### {r['name']}\n{r['data']}" for r in state["results"]
        )
        prompt = f"""
You are a senior business analyst. Write a sharp, data-driven report. No filler, no generic advice.

User request: {state["user_request"]}

Raw query results:
{results_block}

Rules:
- Every claim must reference a specific number from the data above.
- Compare values: name the top, name the bottom, calculate the gap or %.
- Highlight anomalies or surprising patterns if any.
- Recommendations must be specific and tied to the numbers, not generic.
- Use markdown: ## for sections, **bold** for key numbers, bullet points for lists.
- Be concise. No padding sentences.

Sections to include:
## Executive Summary
## Key Metrics (table or bullets with actual numbers)
## Insights (comparative, specific)
## Recommendations (data-backed)
        """
        response = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})
        return {"report": response["messages"][-1].content}

    return reporter_node
