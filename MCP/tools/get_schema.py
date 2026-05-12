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

# def pretty(rows: list[dict]) -> str:
#     return json.dumps(rows, indent=2, default=serialize)

# def run_query(sql: str, params=None) -> list[dict]:
#     with psycopg2.connect(DSN) as conn:
#         with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
#             cur.execute(sql, params)
#             return [dict(row) for row in cur.fetchall()]


def get_schema(sql : str=QUERY, params=None) -> list[dict]:
    with psycopg2.connect(DSN) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]
        
QUERY="""
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
    """
