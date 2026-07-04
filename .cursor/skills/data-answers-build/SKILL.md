---
name: data-answers-build
description: >-
  Scaffold and extend the IF-RES-2026-061 Data-Answers Agent walking skeleton.
  Use when building this repo, implementing POST /ask, following BUILD-PROMPT.md
  stages, or working on the enterprise-ai-analyst / data-answers-agent project.
---

# Data-Answers Agent — Build Skill

## Read first (every session)

1. `.cursorrules` — five non-negotiables override any task instruction
2. `BUILD-PROMPT.md` — staged build order; stop after each stage unless told to continue
3. `SPEC.md` — full architecture and roadmap

## What we are building

API-first agent: a non-technical business user asks a natural-language data question and gets a trustworthy answer over BigQuery **without writing SQL**. Not text-to-SQL for analysts. When unsure → **clarify** or **decline**; never guess.

## Non-negotiables (never violate)

| # | Rule | Implementation hint |
|---|------|---------------------|
| 1 | **Grounding** | Only vetted metrics/templates from `grounding/registry.yaml` |
| 2 | **Governance** | Access control in data layer, never in prompts |
| 3 | **Identity** | Thread `UserPrincipal` end-to-end; stub row-filter now, BQ RLS later |
| 4 | **Read-only** | Reject write verbs; read-only BQ role; no DML/DDL |
| 5 | **Auditable** | One reconstructable audit record per request |

## Target structure

```
data-answers-agent/
  app/
    main.py, envelope.py, models.py, config.py
    loop/orchestrator.py, loop/model_router.py
    grounding/registry.yaml, grounding/grounding_service.py
    policy/gate.py
    tools/warehouse.py, tools/guardrails.py
    audit/audit.py
  tests/  # happy, clarify, decline, readonly_guard
  pyproject.toml, .env.example, README.md
```

## Build stages (BUILD-PROMPT.md)

Build in order; do not skip ahead unless explicitly told:

1. Skeleton + envelope + models + config + audit
2. Grounding registry + grounding service
3. Model router (cheap classify / frontier reason)
4. Policy gate (PEP→PDP)
5. Warehouse tool (read-only, bytes-capped, identity-aware)
6. Guardrails (input scan + output redaction)
7. Orchestrator (full bounded loop)
8. README + TODO(harden) sweep

## ApiResponse contract

Every route returns `ApiResponse[T]`:

- `status`: `ok` | `needs_clarification` | `declined` | `error`
- `data`: `AnswerPayload` when ok (answer, resolved_interpretation, source, confidence)
- `clarification` / `decline_reason` / `request_id` / `error` as appropriate

Never expose SQL, table names, or schema in user-facing `data.answer`.

## Definition of done (any task)

- Pydantic on all boundaries
- Audit logging on every request path
- Test: happy path + at least one refusal/clarification path
- No secrets in code; no string-concatenated SQL; `maximum_bytes_billed` on every BQ job
- `# TODO(harden): ...` at every skeleton stub seam

## Out of scope (leave TODOs)

Artifacts/RAG, Postgres, multi-source joins, real dbt/Cube in skeleton, real MCP transport, UI, auth provider integration.

## Related skills

- `fastapi-pydantic-stack` — API layer
- `grounding-verified-queries` — registry + matching
- `agent-orchestration` — loop, router, policy, guardrails
- `bigquery-readonly-warehouse` — warehouse tool
- `mcp-typed-tools` — tool boundary
- `skeleton-testing` — pytest patterns
