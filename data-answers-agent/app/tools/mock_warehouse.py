"""Seed-data mock BigQuery executor for local dev and CI without GCP."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models import ExecutionContext

_MOCK_DATA_DIR = Path(__file__).resolve().parents[2] / "mock_data"

# Simulated bytes scanned per metric query (for cost audit realism in mock mode)
_MOCK_BYTES_BY_METRIC: dict[str, int] = {
    "total_revenue": 512_000,
    "net_revenue": 512_000,
    "order_count": 384_000,
    "average_order_value": 384_000,
    "active_customers": 256_000,
}


@lru_cache
def _load_table(name: str) -> list[dict[str, Any]]:
    path = _MOCK_DATA_DIR / f"{name}.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _allowed_regions(execution_context: ExecutionContext) -> list[str] | None:
    regions = execution_context.requesting_principal.allowed_regions
    if execution_context.uses_warehouse_rls:
        # WIF mode: warehouse RLS applies; mock returns all seed regions for the month.
        return ["US", "EU", "APAC"]
    if not regions:
        return None
    return regions


def _filter_rows(
    rows: list[dict[str, Any]],
    *,
    month: str | None,
    regions: list[str] | None,
) -> list[dict[str, Any]]:
    if regions is None:
        return []
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if month is not None and row.get("month") != month:
            continue
        if regions and row.get("region") not in regions:
            continue
        filtered.append(row)
    return filtered


def _month_from_params(params: dict[str, str]) -> str | None:
    return params.get("month")


def execute_mock_query(
    *,
    metric_id: str,
    params: dict[str, str],
    execution_context: ExecutionContext,
) -> tuple[list[dict[str, Any]], int]:
    """
    Run a registry metric against seed tables.

    Returns (rows, bytes_scanned). Applies month param and principal region filter
    (stub mode) the same way the real warehouse would via {region_filter}.
    """
    month = _month_from_params(params)
    regions = _allowed_regions(execution_context)

    if metric_id == "total_revenue":
        rows = _filter_rows(_load_table("sales"), month=month, regions=regions)
        total = sum(float(r["amount"]) for r in rows)
        return [{"total_revenue": round(total, 2)}], _MOCK_BYTES_BY_METRIC[metric_id]

    if metric_id == "net_revenue":
        rows = _filter_rows(_load_table("sales"), month=month, regions=regions)
        total = sum(float(r["net_amount"]) for r in rows)
        return [{"net_revenue": round(total, 2)}], _MOCK_BYTES_BY_METRIC[metric_id]

    if metric_id == "order_count":
        rows = _filter_rows(_load_table("orders"), month=month, regions=regions)
        count = sum(int(r["order_count"]) for r in rows)
        return [{"order_count": count}], _MOCK_BYTES_BY_METRIC[metric_id]

    if metric_id == "average_order_value":
        rows = _filter_rows(_load_table("orders"), month=month, regions=regions)
        count = sum(int(r["order_count"]) for r in rows)
        amount = sum(float(r["total_order_amount"]) for r in rows)
        avg = round(amount / count, 2) if count else 0.0
        return [{"average_order_value": avg}], _MOCK_BYTES_BY_METRIC[metric_id]

    if metric_id == "active_customers":
        rows = _filter_rows(_load_table("customers"), month=month, regions=regions)
        total = sum(int(r["active_customers"]) for r in rows)
        return [{"active_customers": total}], _MOCK_BYTES_BY_METRIC[metric_id]

    return [{"value": 0}], 0


def reload_mock_data() -> None:
    """Clear cached seed tables (for tests)."""
    _load_table.cache_clear()
