"""
Sample query runner — will be moved into the MCP agent.

Requires: pip install psycopg2-binary (or psycopg[binary])
Start the DB first: cd db && bash setup.sh
"""

import psycopg2
import psycopg2.extras
import json
from datetime import date, datetime
from decimal import Decimal

DSN = "postgresql://aidb_user:aidb_pass@localhost:5432/sales_db"


def serialize(obj):
    """JSON-serialize types psycopg2 returns that json.dumps can't handle."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Cannot serialize {type(obj)}")


def run_query(sql: str, params=None) -> list[dict]:
    with psycopg2.connect(DSN) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


def pretty(rows: list[dict]) -> str:
    return json.dumps(rows, indent=2, default=serialize)


# ---------------------------------------------------------------------------
# Sample queries
# ---------------------------------------------------------------------------

QUERIES = {
    # 0. Full database schema: tables, columns, types, constraints, foreign keys
    "db_schema": """
        WITH columns AS (
            SELECT
                c.table_name,
                c.ordinal_position                          AS col_pos,
                c.column_name,
                c.data_type,
                c.character_maximum_length,
                c.numeric_precision,
                c.numeric_scale,
                c.is_nullable,
                c.column_default,
                COALESCE(
                  (SELECT string_agg(tc.constraint_type, ', ' ORDER BY tc.constraint_type)
                   FROM information_schema.key_column_usage kcu
                   JOIN information_schema.table_constraints tc
                     ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_name      = kcu.table_name
                   WHERE kcu.table_name   = c.table_name
                     AND kcu.column_name  = c.column_name
                  ), ''
                )                                           AS constraints
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
        ),
        fkeys AS (
            SELECT
                kcu.table_name                              AS from_table,
                kcu.column_name                             AS from_column,
                ccu.table_name                              AS to_table,
                ccu.column_name                             AS to_column,
                rc.delete_rule
            FROM information_schema.referential_constraints rc
            JOIN information_schema.key_column_usage kcu
              ON kcu.constraint_name = rc.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = rc.unique_constraint_name
            WHERE kcu.table_schema = 'public'
        ),
        row_counts AS (
            SELECT
                relname                                     AS table_name,
                reltuples::bigint                           AS estimated_rows
            FROM pg_class
            JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
            WHERE nspname = 'public'
              AND relkind = 'r'
        )
        SELECT
            col.table_name,
            rc.estimated_rows,
            col.col_pos,
            col.column_name,
            col.data_type ||
              CASE
                WHEN col.character_maximum_length IS NOT NULL
                  THEN '(' || col.character_maximum_length || ')'
                WHEN col.numeric_precision IS NOT NULL AND col.data_type NOT IN ('integer','bigint','smallint')
                  THEN '(' || col.numeric_precision || ',' || col.numeric_scale || ')'
                ELSE ''
              END                                           AS full_type,
            col.is_nullable,
            col.column_default,
            col.constraints,
            fk.to_table                                     AS fk_references_table,
            fk.to_column                                    AS fk_references_column,
            fk.delete_rule                                  AS fk_on_delete
        FROM columns col
        LEFT JOIN fkeys fk
          ON fk.from_table  = col.table_name
         AND fk.from_column = col.column_name
        LEFT JOIN row_counts rc ON rc.table_name = col.table_name
        ORDER BY col.table_name, col.col_pos;
    """,

    # 1. Monthly revenue summary for the last 12 months
    "monthly_revenue": """
        SELECT
            DATE_TRUNC('month', o.order_date)::date   AS month,
            COUNT(DISTINCT o.order_id)                 AS total_orders,
            COUNT(DISTINCT o.customer_id)              AS unique_customers,
            ROUND(SUM(o.total_amount), 2)              AS gross_revenue,
            ROUND(SUM(o.discount_amount), 2)           AS total_discounts,
            ROUND(SUM(o.tax_amount), 2)                AS total_tax
        FROM orders o
        WHERE o.status NOT IN ('cancelled', 'refunded')
          AND o.order_date >= NOW() - INTERVAL '12 months'
        GROUP BY DATE_TRUNC('month', o.order_date)
        ORDER BY month DESC;
    """,

    # 2. Top 10 products by revenue
    "top_products": """
        SELECT
            p.product_id,
            p.sku,
            p.name                                         AS product_name,
            cat.name                                       AS category,
            SUM(oi.quantity)                               AS units_sold,
            ROUND(SUM(oi.line_total), 2)                   AS total_revenue,
            ROUND(AVG(oi.discount_pct), 2)                 AS avg_discount_pct
        FROM order_items oi
        JOIN products   p   ON p.product_id   = oi.product_id
        JOIN categories cat ON cat.category_id = p.category_id
        JOIN orders     o   ON o.order_id      = oi.order_id
        WHERE o.status NOT IN ('cancelled', 'refunded')
        GROUP BY p.product_id, p.sku, p.name, cat.name
        ORDER BY total_revenue DESC
        LIMIT 10;
    """,

    # 3. Sales rep performance: revenue + order count + average deal size
    "rep_performance": """
        SELECT
            e.employee_id,
            e.first_name || ' ' || e.last_name           AS sales_rep,
            e.job_title,
            r.name                                        AS region,
            COUNT(DISTINCT o.order_id)                    AS orders_closed,
            COUNT(DISTINCT o.customer_id)                 AS customers_served,
            ROUND(SUM(o.total_amount), 2)                 AS total_revenue,
            ROUND(AVG(o.total_amount), 2)                 AS avg_deal_size,
            ROUND(SUM(o.total_amount) * e.commission_pct / 100, 2) AS estimated_commission
        FROM employees e
        JOIN orders    o ON o.employee_id = e.employee_id
        JOIN regions   r ON r.region_id   = e.region_id
        WHERE o.status NOT IN ('cancelled', 'refunded')
        GROUP BY e.employee_id, e.first_name, e.last_name, e.job_title, r.name, e.commission_pct
        ORDER BY total_revenue DESC
        LIMIT 20;
    """,

    # 4. Customer lifetime value with order history summary
    "customer_ltv": """
        SELECT
            c.customer_id,
            c.first_name || ' ' || c.last_name           AS customer_name,
            c.company_name,
            c.industry,
            c.status,
            c.customer_since,
            COUNT(o.order_id)                             AS total_orders,
            ROUND(SUM(o.total_amount), 2)                 AS lifetime_value,
            ROUND(AVG(o.total_amount), 2)                 AS avg_order_value,
            MAX(o.order_date)::date                       AS last_order_date,
            c.credit_limit
        FROM customers c
        LEFT JOIN orders o ON o.customer_id = c.customer_id
                           AND o.status NOT IN ('cancelled', 'refunded')
        GROUP BY c.customer_id, c.first_name, c.last_name, c.company_name,
                 c.industry, c.status, c.customer_since, c.credit_limit
        ORDER BY lifetime_value DESC NULLS LAST
        LIMIT 25;
    """,

    # 5. Inventory health: stock vs reorder level + supplier info
    "inventory_health": """
        SELECT
            p.product_id,
            p.sku,
            p.name,
            cat.name                                      AS category,
            s.company_name                                AS supplier,
            s.lead_time_days,
            p.stock_quantity,
            p.reorder_level,
            p.stock_quantity - p.reorder_level            AS buffer_units,
            CASE
              WHEN p.stock_quantity = 0            THEN 'OUT OF STOCK'
              WHEN p.stock_quantity < p.reorder_level THEN 'REORDER NOW'
              WHEN p.stock_quantity < p.reorder_level * 1.5 THEN 'LOW STOCK'
              ELSE 'OK'
            END                                           AS stock_status,
            ROUND(p.unit_price * p.stock_quantity, 2)    AS inventory_value
        FROM products   p
        JOIN categories cat ON cat.category_id = p.category_id
        JOIN suppliers  s   ON s.supplier_id   = p.supplier_id
        WHERE p.is_active = TRUE
        ORDER BY buffer_units ASC
        LIMIT 30;
    """,

    # 6. Payment success rate by method and gateway
    "payment_analysis": """
        SELECT
            payment_method,
            gateway,
            COUNT(*)                                      AS total_transactions,
            COUNT(*) FILTER (WHERE status = 'completed')  AS successful,
            COUNT(*) FILTER (WHERE status = 'failed')     AS failed,
            COUNT(*) FILTER (WHERE status = 'refunded')   AS refunded,
            ROUND(
              100.0 * COUNT(*) FILTER (WHERE status = 'completed') / COUNT(*), 2
            )                                             AS success_rate_pct,
            ROUND(SUM(amount) FILTER (WHERE status = 'completed'), 2) AS collected_amount
        FROM payments
        GROUP BY payment_method, gateway
        ORDER BY total_transactions DESC;
    """,

    # 7. Orders with their items (flat, first 10 orders)
    "order_detail_sample": """
        SELECT
            o.order_id,
            o.order_date::date,
            o.status,
            c.first_name || ' ' || c.last_name           AS customer,
            c.company_name,
            p.name                                        AS product,
            p.sku,
            oi.quantity,
            oi.unit_price,
            oi.discount_pct,
            oi.line_total,
            o.total_amount                                AS order_total
        FROM orders      o
        JOIN customers   c  ON c.customer_id  = o.customer_id
        JOIN order_items oi ON oi.order_id    = o.order_id
        JOIN products    p  ON p.product_id   = oi.product_id
        WHERE o.order_id <= 10
        ORDER BY o.order_id, oi.order_item_id;
    """,
}


if __name__ == "__main__":
    for name, sql in QUERIES.items():
        print(f"\n{'='*60}")
        print(f"Query: {name}")
        print("=" * 60)
        try:
            rows = run_query(sql)
            print(f"Rows returned: {len(rows)}")
            print(pretty(rows[:5]))          # preview first 5 rows
            if len(rows) > 5:
                print(f"  ... and {len(rows) - 5} more rows")
        except Exception as exc:
            print(f"ERROR: {exc}")
