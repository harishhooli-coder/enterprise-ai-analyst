---
name: mcp-typed-tools
description: >-
  MCP-shaped typed tool boundary for the Data-Answers Agent. Use when
  implementing tools/warehouse.py, tools/grounding retrieval, or preparing
  real MCP server transport in Phase 2.
---

# MCP Typed Tools Boundary

## Skeleton vs target

| Phase | Implementation |
|-------|----------------|
| Phase 0 | Typed Python functions in `app/tools/` |
| Phase 2 | Real MCP servers with per-request identity |

Keep the function signatures identical so MCP transport is a drop-in swap.

## Tool surface (bounded, read-only)

```python
# tools/warehouse.py
async def query_warehouse(
    template_id: str,
    params: dict[str, str],
    principal: UserPrincipal,
    audit_ctx: AuditContext,
) -> WarehouseResult: ...

# tools/grounding.py (optional split from grounding_service)
async def retrieve_grounding(
    question: str,
    audit_ctx: AuditContext,
) -> GroundingResult: ...
```

Only these tools reach data. No ad-hoc tool registration.

## Policy gate wrapper

```python
async def invoke_tool(tool_name: str, fn, principal, resource, metadata, audit_ctx):
    decision = policy.authorize(principal, resource, metadata)
    audit_ctx.record_policy(decision)
    if not decision.allowed:
        raise PolicyDeniedError(decision.reason)
    return await fn()
```

## MCP Phase 2 migration

Package: `mcp` Python SDK. Pattern:

1. Stand up MCP server exposing `query_warehouse` and `retrieve_grounding`
2. Agent service becomes MCP client; attach user credential per request
3. Tool schemas match Pydantic models (JSON Schema export)

```python
# TODO(harden): replace typed-function stub with MCP client transport
```

## MCP resource naming

- `warehouse://query` — read-only BigQuery execution
- `grounding://registry` — metric/template retrieval

## Rules

- Tools are typed; inputs/outputs are Pydantic models
- Every invocation is audited and policy-gated
- No tool accepts raw SQL from the model — only template_id + params
- Read-only: warehouse tool has no write/mutate operations
