"""Expand aggregated mock_data JSON into row-level NDJSON for BigQuery load."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOCK = ROOT / "mock_data"
OUT = ROOT / "scripts" / "bq_seed"


def write_ndjson(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def expand_sales() -> None:
    rows = json.loads((MOCK / "sales.json").read_text(encoding="utf-8"))
    write_ndjson(OUT / "sales.ndjson", rows)


def expand_orders() -> None:
    aggregated = json.loads((MOCK / "orders.json").read_text(encoding="utf-8"))
    rows: list[dict] = []
    order_id = 1
    for bucket in aggregated:
        count = int(bucket["order_count"])
        total = float(bucket["total_order_amount"])
        per_order = round(total / count, 2) if count else 0.0
        remainder = round(total - (per_order * count), 2)
        for i in range(count):
            amount = per_order + (remainder if i == count - 1 else 0.0)
            rows.append(
                {
                    "order_id": f"ord-{order_id:06d}",
                    "month": bucket["month"],
                    "region": bucket["region"],
                    "order_amount": amount,
                }
            )
            order_id += 1
    write_ndjson(OUT / "orders.ndjson", rows)


def expand_customers() -> None:
    aggregated = json.loads((MOCK / "customers.json").read_text(encoding="utf-8"))
    rows: list[dict] = []
    customer_id = 1
    for bucket in aggregated:
        count = int(bucket["active_customers"])
        for _ in range(count):
            rows.append(
                {
                    "customer_id": f"cust-{customer_id:06d}",
                    "month": bucket["month"],
                    "region": bucket["region"],
                }
            )
            customer_id += 1
    write_ndjson(OUT / "customers.ndjson", rows)


def main() -> None:
    expand_sales()
    expand_orders()
    expand_customers()
    print(f"Wrote seed files under {OUT}")


if __name__ == "__main__":
    main()
