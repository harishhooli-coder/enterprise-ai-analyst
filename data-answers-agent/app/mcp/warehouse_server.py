"""MCP stdio server exposing the grounded read-only warehouse tool."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from app.models import ExecutionContext, WarehouseResult
from app.tools.warehouse_core import ReadOnlyViolationError, execute_warehouse_direct

server = Server("data-answers-warehouse")


def _json_dumps(payload: dict) -> str:
    def _default(value: object) -> object:
        if isinstance(value, Decimal):
            return float(value)
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    return json.dumps(payload, default=_default)

QUERY_WAREHOUSE_SCHEMA = {
    "type": "object",
    "properties": {
        "template_sql": {
            "type": "string",
            "description": "Vetted SQL template from the grounding registry (not user text).",
        },
        "params": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Registry-resolved parameter bindings only.",
        },
        "metric_id": {"type": "string"},
        "execution_context": {
            "type": "object",
            "description": "Identity and row-filter context for the calling principal.",
        },
    },
    "required": ["template_sql", "params", "metric_id", "execution_context"],
}


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="query_warehouse",
            description=(
                "Execute a vetted, parameterized warehouse query. "
                "Read-only; accepts registry template + params only — never raw SQL from users."
            ),
            inputSchema=QUERY_WAREHOUSE_SCHEMA,
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if name != "query_warehouse":
        raise ValueError(f"Unknown tool: {name}")

    args = arguments or {}
    try:
        execution_context = ExecutionContext.model_validate(args["execution_context"])
        result = execute_warehouse_direct(
            args["template_sql"],
            args.get("params") or {},
            execution_context,
            metric_id=args.get("metric_id", "unknown"),
        )
        return [types.TextContent(type="text", text=_json_dumps(result.model_dump()))]
    except ReadOnlyViolationError as exc:
        payload = {"error": str(exc), "error_type": "ReadOnlyViolationError"}
        return [types.TextContent(type="text", text=json.dumps(payload))]
    except Exception as exc:
        payload = {"error": str(exc), "error_type": type(exc).__name__}
        return [types.TextContent(type="text", text=json.dumps(payload))]


async def run_server() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="data-answers-warehouse",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
