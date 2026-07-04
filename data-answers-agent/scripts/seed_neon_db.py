#!/usr/bin/env python3
"""Create analytics schema and seed demo data into Neon PostgreSQL.

Usage:
    cd data-answers-agent
    pip install -e ".[postgres]"
    DATABASE_URL=postgresql://... python scripts/seed_neon_db.py

Seeds row-level orders/customers so registry SQL (COUNT, AVG, COUNT DISTINCT)
returns the same golden values as mock_data/*.json.
"""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOCK_DATA = ROOT / "mock_data"
SCHEMA = os.getenv("BQ_DATASET", "analytics")
BATCH = 2000


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


def _load(name: str) -> list[dict]:
    with (MOCK_DATA / f"{name}.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _distribute_amounts(count: int, total: Decimal) -> list[Decimal]:
    if count <= 0:
        return []
    unit = (total / count).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    amounts = [unit] * (count - 1)
    amounts.append(total - unit * (count - 1))
    return amounts


def _ddl(conn, schema: str) -> None:
    conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
    conn.execute(f"CREATE SCHEMA {schema}")

    conn.execute(
        f"""
        CREATE TABLE {schema}.sales (
            month       CHAR(7) NOT NULL,
            region      TEXT NOT NULL CHECK (region IN ('US', 'EU', 'APAC')),
            amount      NUMERIC(18, 2) NOT NULL,
            net_amount  NUMERIC(18, 2) NOT NULL,
            PRIMARY KEY (month, region)
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE {schema}.orders (
            order_id     BIGSERIAL PRIMARY KEY,
            month        CHAR(7) NOT NULL,
            region       TEXT NOT NULL CHECK (region IN ('US', 'EU', 'APAC')),
            order_amount NUMERIC(12, 2) NOT NULL
        )
        """
    )
    conn.execute(
        f"CREATE INDEX idx_orders_month_region ON {schema}.orders (month, region)"
    )
    conn.execute(
        f"""
        CREATE TABLE {schema}.customers (
            customer_id  TEXT NOT NULL,
            month        CHAR(7) NOT NULL,
            region       TEXT NOT NULL CHECK (region IN ('US', 'EU', 'APAC')),
            PRIMARY KEY (customer_id, month, region)
        )
        """
    )
    conn.execute(
        f"CREATE INDEX idx_customers_month_region ON {schema}.customers (month, region)"
    )


def _executemany(conn, sql: str, rows: list[tuple]) -> None:
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def _seed_sales(conn, schema: str) -> None:
    rows = [
        (r["month"], r["region"], r["amount"], r["net_amount"])
        for r in _load("sales")
    ]
    _executemany(
        conn,
        f"""
        INSERT INTO {schema}.sales (month, region, amount, net_amount)
        VALUES (%s, %s, %s, %s)
        """,
        rows,
    )


def _seed_orders(conn, schema: str) -> None:
    order_rows: list[tuple[str, str, Decimal]] = []
    for rollup in _load("orders"):
        month = rollup["month"]
        region = rollup["region"]
        count = int(rollup["order_count"])
        total = Decimal(str(rollup["total_order_amount"]))
        for amount in _distribute_amounts(count, total):
            order_rows.append((month, region, amount))

    for start in range(0, len(order_rows), BATCH):
        batch = order_rows[start : start + BATCH]
        _executemany(
            conn,
            f"""
            INSERT INTO {schema}.orders (month, region, order_amount)
            VALUES (%s, %s, %s)
            """,
            batch,
        )


def _seed_customers(conn, schema: str) -> None:
    customer_rows: list[tuple[str, str, str]] = []
    for rollup in _load("customers"):
        month = rollup["month"]
        region = rollup["region"]
        count = int(rollup["active_customers"])
        prefix = f"{region}-{month.replace('-', '')}"
        for seq in range(1, count + 1):
            customer_rows.append((f"{prefix}-{seq:06d}", month, region))

    for start in range(0, len(customer_rows), BATCH):
        batch = customer_rows[start : start + BATCH]
        _executemany(
            conn,
            f"""
            INSERT INTO {schema}.customers (customer_id, month, region)
            VALUES (%s, %s, %s)
            """,
            batch,
        )


def _verify(conn, schema: str) -> None:
    checks = [
        (
            "total_revenue US+EU 2026-06",
            f"""
            SELECT SUM(amount)::float AS v FROM {schema}.sales
            WHERE month = '2026-06' AND region IN ('US', 'EU')
            """,
            1_250_000.00,
        ),
        (
            "net_revenue US+EU 2026-06",
            f"""
            SELECT SUM(net_amount)::float AS v FROM {schema}.sales
            WHERE month = '2026-06' AND region IN ('US', 'EU')
            """,
            980_000.00,
        ),
        (
            "order_count US+EU 2026-06",
            f"""
            SELECT COUNT(*)::int AS v FROM {schema}.orders
            WHERE month = '2026-06' AND region IN ('US', 'EU')
            """,
            18_400,
        ),
        (
            "average_order_value US+EU 2026-06",
            f"""
            SELECT ROUND(AVG(order_amount)::numeric, 2)::float AS v FROM {schema}.orders
            WHERE month = '2026-06' AND region IN ('US', 'EU')
            """,
            67.93,
        ),
        (
            "active_customers US+EU 2026-06",
            f"""
            SELECT COUNT(DISTINCT customer_id)::int AS v FROM {schema}.customers
            WHERE month = '2026-06' AND region IN ('US', 'EU')
            """,
            42_500,
        ),
    ]
    for label, sql, expected in checks:
        row = conn.execute(sql).fetchone()
        actual = row["v"] if isinstance(row, dict) else row[0]
        if abs(float(actual) - float(expected)) > 0.02:
            raise RuntimeError(f"{label}: expected {expected}, got {actual}")
        print(f"  OK  {label} = {actual}")


def main() -> int:
    _load_env()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        print("Install postgres extras: pip install -e '.[postgres]'", file=sys.stderr)
        return 1

    print(f"Seeding schema '{SCHEMA}' ...")
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.transaction():
            _ddl(conn, SCHEMA)
            print("  sales ...")
            _seed_sales(conn, SCHEMA)
            print("  orders (row-level, ~42k rows) ...")
            _seed_orders(conn, SCHEMA)
            print("  customers (row-level, ~97k rows) ...")
            _seed_customers(conn, SCHEMA)

        print("Verifying golden metrics:")
        _verify(conn, SCHEMA)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
