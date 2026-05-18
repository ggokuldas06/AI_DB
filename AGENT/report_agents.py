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
    agent = create_agent(
        model="groq:llama-3.1-8b-instant",
        tools=[],
    )

    async def planner_node(state: ReportState) -> dict:
        print(f"[planner] {state['user_request']}")

        step2_prompt = f"""
        You are a PostgreSQL expert. The user wants: {state["user_request"]}

        Pre-computed summary tables (ALWAYS prefer these — they are fast and return few rows):
        - mv_region_sales: region_id, region_name, country, continent, num_orders, num_customers, total_sales, avg_order_value, total_discounts
        - mv_category_sales: category_id, category_name, num_orders, total_units_sold, total_revenue, avg_unit_price
        - mv_monthly_sales: month, num_orders, num_customers, total_sales, avg_order_value
        - mv_payment_method_sales: payment_method, num_payments, total_amount, avg_amount
        - mv_region_monthly_sales: region_id, region_name, month, num_orders, total_sales, avg_order_value

        Write 3 to 5 useful SQL queries using ONLY the pre-computed summary tables above.
        IMPORTANT rules:
        - ONLY query the mv_ tables listed above. Do NOT use any raw tables.
        - mv_ tables are already aggregated — use simple SELECT, no GROUP BY, no JOINs needed.
        - Each mv_ table is standalone — never JOIN two mv_ tables together.

        Return ONLY a valid JSON array, no explanation, no markdown:
        [
          {{"name": "metric name", "sql": "SELECT ..."}},
          ...
        ]
        """
        r2 = await agent.ainvoke({"messages": [{"role": "user", "content": step2_prompt}]})
        c2 = r2["messages"][-1].content
        planned_queries = json.loads(c2[c2.find("["):c2.rfind("]") + 1])

        print(f"[planner] {len(planned_queries)} queries")

        return {
            "planned_queries": planned_queries,
            "current_index": 0,
            "results": [],
        }

    return planner_node


def make_executor_node(tools):
    run_tool = [t for t in tools if t.name == "run_query_tool"][0]

    async def executor_node(state: ReportState) -> dict:
        idx = state["current_index"]
        task = state["planned_queries"][idx]
        print(f"[executor] {idx + 1}/{len(state['planned_queries'])} {task['name']}")

        try:
            result = await run_tool.ainvoke({"sql": task["sql"]})
            rows = [json.loads(item["text"]) for item in result] if isinstance(result, list) and result and isinstance(result[0], dict) and "text" in result[0] else result
            summary = json.dumps(rows, indent=2)
            print(f"[executor] - pass -  {task['name']} — {len(rows)} rows")
        except Exception as e:
            summary = f"Query failed: {str(e)[:120]}"
            print(f"[executor] - fail - {task['name']} — skipped: {str(e)[:80]}")

        return {
            "results": state["results"] + [{"name": task["name"], "data": summary}],
            "current_index": idx + 1,
        }

    return executor_node


def make_reporter_node():
    agent = create_agent(model="ollama:llama3.1:8b", tools=[])
    async def reporter_node(state: ReportState) -> dict:
        print("[reporter] generating final report...")

        def compact(data_str):
            try:
                rows = json.loads(data_str)
                return "\n".join(
                    ", ".join(f"{k}: {v}" for k, v in row.items()) for row in rows
                )
            except Exception:
                return data_str

        results_block = "\n\n".join(
            f"### {r['name']}\n{compact(r['data'])}" for r in state["results"]
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
