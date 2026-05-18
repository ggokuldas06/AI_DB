import os
import psycopg2
import psycopg2.extras
import json
from datetime import date, datetime
from decimal import Decimal
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

DSN = os.environ["DATABASE_URL"]


# def serialize(obj):
#     """JSON-serialize types psycopg2 returns that json.dumps can't handle."""
#     if isinstance(obj, (date, datetime)):
#         return obj.isoformat()
#     if isinstance(obj, Decimal):
#         return float(obj)
#     raise TypeError(f"Cannot serialize {type(obj)}")

# def pretty(rows: list[dict]) -> str:
#     return json.dumps(rows, indent=2, default=serialize)

# def run_query(sql: str, params=None) -> list[dict]:
#     with psycopg2.connect(DSN) as conn:
#         with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
#             cur.execute(sql, params)
#             return [dict(row) for row in cur.fetchall()]


QUERY = """
    SELECT
        c.table_name,
        c.column_name,
        c.data_type,
        COALESCE(
          (SELECT string_agg(tc.constraint_type, ',' ORDER BY tc.constraint_type)
           FROM information_schema.key_column_usage kcu
           JOIN information_schema.table_constraints tc
             ON tc.constraint_name = kcu.constraint_name
            AND tc.table_name      = kcu.table_name
           WHERE kcu.table_name  = c.table_name
             AND kcu.column_name = c.column_name
          ), ''
        ) AS constraints,
        (SELECT ccu.table_name
         FROM information_schema.referential_constraints rc
         JOIN information_schema.key_column_usage kcu
           ON kcu.constraint_name = rc.constraint_name
         JOIN information_schema.constraint_column_usage ccu
           ON ccu.constraint_name = rc.unique_constraint_name
         WHERE kcu.table_name  = c.table_name
           AND kcu.column_name = c.column_name
         LIMIT 1
        ) AS fk_table
    FROM information_schema.columns c
    WHERE c.table_schema = 'public'
    ORDER BY c.table_name, c.ordinal_position;
"""

def get_schema() -> str:
    with psycopg2.connect(DSN) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(QUERY)
            rows = cur.fetchall()

    tables = {}
    for row in rows:
        t = row["table_name"]
        col = row["column_name"]
        typ = row["data_type"]
        constraints = row["constraints"] or ""
        fk = row["fk_table"]

        label = col
        if "PRIMARY KEY" in constraints:
            label += " PK"
        if fk:
            label += f" FK->{fk}"
        label += f":{typ}"

        tables.setdefault(t, []).append(label)

    return "\n".join(f"{t}({', '.join(cols)})" for t, cols in tables.items())
        