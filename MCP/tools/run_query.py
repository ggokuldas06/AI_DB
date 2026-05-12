import psycopg2
import psycopg2.extras
import json
from datetime import date, datetime
from decimal import Decimal

DSN = "postgresql://aidb_user:aidb_pass@localhost:5432/sales_db"


# def serialize(obj):
#     """JSON-serialize types psycopg2 returns that json.dumps can't handle."""
#     if isinstance(obj, (date, datetime)):
#         return obj.isoformat()
#     if isinstance(obj, Decimal):
#         return float(obj)
#     raise TypeError(f"Cannot serialize {type(obj)}")


def run_query(sql: str, params=None) -> list[dict]:
    with psycopg2.connect(DSN) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


# def pretty(rows: list[dict]) -> str:
#     return json.dumps(rows, indent=2, default=serialize)