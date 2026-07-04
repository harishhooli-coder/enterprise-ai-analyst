# Cursor Skills — Data-Answers Agent (IF-RES-2026-061)

Project-scoped skills for building the enterprise-ai-analyst walking skeleton and beyond.

## Phase 0 — Start here

| Skill | Use when |
|-------|----------|
| **data-answers-build** | Any work in this repo; read first |
| **fastapi-pydantic-stack** | API routes, models, config, pyproject.toml |
| **grounding-verified-queries** | registry.yaml, grounding_service.py |
| **agent-orchestration** | orchestrator, model_router, policy, audit, guardrails |
| **bigquery-readonly-warehouse** | warehouse tool, bytes cap, read-only guard |
| **mcp-typed-tools** | tools/ module, MCP-shaped boundaries |
| **skeleton-testing** | pytest happy/clarify/decline/readonly tests |
| **anthropic-claude-api** | Frontier model tier in model_router |

## Phase 1+ — Hardening backlog

| Skill | Use when |
|-------|----------|
| **semantic-layer-dbt-cube** | Replace YAML with dbt/Cube |
| **embeddings-retrieval-tier** | Semantic metric matching |
| **identity-bigquery-rls** | WIF, impersonation, BQ RLS |
| **guardrails-presidio** | Production input/output guardrails |
| **opentelemetry-observability** | Traces, metrics, eval hooks |

## How to use

1. Skills live in `.cursor/skills/` and load automatically when relevant (via description matching).
2. Paste `BUILD-PROMPT.md` into Composer Agent mode to scaffold Stage 1.
3. Reference a skill explicitly: e.g. "follow the fastapi-pydantic-stack skill."

## Also in repo root

- `.cursorrules` — non-negotiables (always in context)
- `BUILD-PROMPT.md` — 8-stage build order
- `SPEC.md` — full architecture
