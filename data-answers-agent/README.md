# Data-Answers Agent — Walking Skeleton

API-first agent that lets a **non-technical business user** ask a natural-language data question and get a trustworthy answer over BigQuery — without writing SQL. This is the v1 **walking skeleton** for IF-RES-2026-061: one grounded question, one user, end-to-end through every architectural layer.

## What it does

`POST /ask` accepts a question and a user principal, then returns an `ApiResponse` with one of:

- **ok** — answer with provenance (metric id, resolved interpretation, confidence)
- **needs_clarification** — ambiguous question; asks a specific follow-up
- **declined** — out of scope or policy denied; routed to human
- **error** — step cap or token budget exceeded

Every path writes exactly one reconstructable audit record.

## Non-negotiables

1. **Grounding** — Only vetted metrics/templates from `app/grounding/registry.yaml`. No improvised SQL.
2. **Governance** — Access control in the data layer, never in prompts.
3. **Identity** — `UserPrincipal` threads end-to-end; stub row-filter now, BigQuery RLS later.
4. **Read-only** — Write verbs rejected; `maximum_bytes_billed` on every query.
5. **Auditable** — One audit record per request with principal, policy decision, bytes scanned, latency.

## Run locally

```bash
cd data-answers-agent
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env   # edit as needed; API key optional for skeleton stubs

uvicorn app.main:app --reload --port 8000
```

### Example request

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What was total revenue last month?",
    "user_principal": {"user_id": "u1", "allowed_regions": ["US", "EU"]}
  }'
```

### Run tests

```bash
pytest tests/ -v
```

Tests mock the model router and BigQuery — no live API keys required in CI.

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Frontier model tier (optional in skeleton) | empty |
| `BQ_PROJECT_ID` | BigQuery project | `dev-project` |
| `BQ_DATASET` | BigQuery dataset | `analytics` |
| `MAX_BYTES_BILLED` | Bytes cap per query | `1000000000` |
| `AGENT_STEP_CAP` | Max orchestrator steps | `10` |
| `TOKEN_BUDGET` | Token/cost budget abort threshold | `8000` |
| `LOG_LEVEL` | Log level | `INFO` |

## Known limitations (skeleton)

- Single dev credential for BigQuery; principal enforced via stub `WHERE` row-filter, not real RLS.
- Flat YAML registry — not a real semantic layer (dbt/Cube).
- Keyword-based grounding retrieval — not embedding-based.
- Guardrails are pattern stubs — not Presidio or production injection detection.
- Typed Python tool functions — not real MCP transport.
- No auth provider; principal is passed in the request body.
- No artifacts/RAG server, multi-source joins, or UI.

## Before hardening — TODO seams

Search the codebase for `# TODO(harden)` and `# DECISION-NEEDED`. Key seams:

| Seam | Location | Action before production |
|------|----------|-------------------------|
| Identity → real RLS | `app/tools/warehouse.py` | Replace stub row-filter with BigQuery RLS via WIF/impersonation |
| Semantic layer | `app/grounding/grounding_service.py` | Back registry with dbt Semantic Layer or Cube |
| Model routing | `app/loop/model_router.py` | Swappable routing policy; embedding retrieval tier |
| MCP transport | `app/tools/warehouse.py` | Replace typed-function stub with MCP client |
| Policy engine | `app/policy/gate.py` | Replace skeleton allow with OPA/Rego or warehouse-native policy |
| Guardrails | `app/tools/guardrails.py` | Presidio PII detection; richer injection rules |
| Audit export | `app/audit/audit.py` | OpenTelemetry span export and durable audit store |

## Project layout

```
data-answers-agent/
  app/
    main.py              # FastAPI /ask route
    envelope.py          # ApiResponse envelope
    models.py            # Pydantic models
    config.py            # Env-driven settings
    loop/
      orchestrator.py    # Bounded agent loop
      model_router.py    # Two-tier classify/reason
    grounding/
      registry.yaml      # Metric + verified-query templates
      grounding_service.py
    policy/gate.py       # PEP→PDP authorize
    tools/
      warehouse.py       # Read-only BigQuery tool
      guardrails.py      # Input scan + output redaction
    audit/audit.py       # Structured audit logger
  tests/
  pyproject.toml
  .env.example
```
