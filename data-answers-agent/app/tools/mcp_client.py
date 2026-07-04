"""MCP client transport for the grounded warehouse tool."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Callable, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import get_settings
from app.models import ExecutionContext, WarehouseResult
from app.tools.warehouse_core import ReadOnlyViolationError

_mcp_client_factory: Optional[
    Callable[
        [str, dict[str, str], ExecutionContext, str],
        WarehouseResult,
    ]
] = None


def set_mcp_client_factory(
    factory: Optional[
        Callable[
            [str, dict[str, str], ExecutionContext, str],
            WarehouseResult,
        ]
    ],
) -> None:
    """Test hook: inject fake MCP transport."""
    global _mcp_client_factory
    _mcp_client_factory = factory


def _server_params() -> StdioServerParameters:
    settings = get_settings()
    python = settings.mcp_python or sys.executable
    env = _warehouse_env()
    return StdioServerParameters(
        command=python,
        args=["-m", "app.mcp.warehouse_server"],
        env=env,
    )


def _warehouse_env() -> dict[str, str]:
    """Pass warehouse config into the MCP server subprocess."""
    from mcp.client.stdio import get_default_environment

    env = get_default_environment()
    for key in (
        "DATABASE_URL",
        "WAREHOUSE_BACKEND",
        "BQ_PROJECT_ID",
        "BQ_DATASET",
        "BQ_USE_MOCK",
        "MAX_BYTES_BILLED",
        "IDENTITY_MODE",
    ):
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


async def _call_mcp_async(
    template_sql: str,
    params: dict[str, str],
    execution_context: ExecutionContext,
    metric_id: str,
) -> WarehouseResult:
    payload = {
        "template_sql": template_sql,
        "params": params,
        "metric_id": metric_id,
        "execution_context": execution_context.model_dump(),
    }
    async with stdio_client(_server_params()) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            response = await session.call_tool("query_warehouse", arguments=payload)
            if response.isError:
                message = ""
                if response.content and response.content[0].type == "text":
                    message = response.content[0].text
                raise RuntimeError(f"MCP query_warehouse failed: {message or 'unknown error'}")
            if not response.content:
                raise RuntimeError("MCP query_warehouse returned empty content")
            block = response.content[0]
            if block.type != "text":
                raise RuntimeError(f"Unexpected MCP content type: {block.type}")
            raw = block.text.strip()
            if not raw:
                raise RuntimeError("MCP query_warehouse returned empty text payload")
            data = json.loads(raw)
            if "error_type" in data:
                if data["error_type"] == "ReadOnlyViolationError":
                    raise ReadOnlyViolationError(data["error"])
                raise RuntimeError(data.get("error", "MCP warehouse error"))
            return WarehouseResult.model_validate(data)


def query_warehouse_via_mcp(
    template_sql: str,
    params: dict[str, str],
    execution_context: ExecutionContext,
    *,
    metric_id: str = "unknown",
) -> WarehouseResult:
    """Invoke query_warehouse over MCP stdio transport."""
    if _mcp_client_factory is not None:
        return _mcp_client_factory(template_sql, params, execution_context, metric_id)
    return asyncio.run(
        _call_mcp_async(template_sql, params, execution_context, metric_id),
    )
