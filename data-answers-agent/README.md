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
| `ANTHROPIC_API_KEY` | Anthropic fallback for answer formatting | empty |
| `FRONTIER_PROVIDER` | Primary frontier backend: `nim` or `anthropic` | `nim` |
| `FRONTIER_MODEL` | Anthropic model when provider is `anthropic` | `claude-sonnet-4-6` |
| `NIM_API_KEY` | NVIDIA NIM API key (`nvapi-...`) | empty |
| `NIM_BASE_URL` | NIM OpenAI-compatible endpoint | `https://integrate.api.nvidia.com/v1` |
| `NIM_MODEL` | NIM model id for answer formatting | `meta/llama-3.3-70b-instruct` |
| `BQ_PROJECT_ID` | BigQuery project | `dev-project` |
| `BQ_DATASET` | BigQuery dataset | `analytics` |
| `BQ_USE_MOCK` | Force seed-data mock warehouse (`1`/`true`) | auto when project is `dev-project` |
| `MAX_BYTES_BILLED` | Bytes cap per query | `1000000000` |
| `AGENT_STEP_CAP` | Max orchestrator steps | `10` |
| `TOKEN_BUDGET` | Token/cost budget abort threshold | `8000` |
| `GROUNDING_RETRIEVAL` | `auto`, `embedding`, or `keyword` | `auto` |
| `EMBEDDING_MATCH_THRESHOLD` | Min cosine score for a metric match | `0.25` |
| `EMBEDDING_AMBIGUITY_MARGIN` | Top-two score gap below which → clarify | `0.05` |
| `IDENTITY_MODE` | `stub` (row-filter) or `wif` (warehouse RLS) | `stub` |
| `BQ_DEV_SERVICE_ACCOUNT` | Executing identity logged in stub mode | empty |
| `BQ_IMPERSONATE_TARGET` | SA to impersonate per user (WIF mode) | empty |
| `WIF_PROVIDER_CONFIG` | Path to WIF provider config JSON (WIF mode) | empty |
| `CORS_ORIGINS` | Comma-separated browser origins for the test UI | `http://localhost:3000` |
| `LOG_LEVEL` | Log level | `INFO` |

## Known limitations (skeleton)

- **Stub identity mode is not production-safe** for multi-user real data — use `IDENTITY_MODE=wif` with BigQuery RLS before any pilot.
- Flat YAML registry — not a real semantic layer (dbt/Cube).
- Hash-embedding retrieval by default — install `[embeddings]` extra for sentence-transformers.
- Guardrails are pattern stubs — not Presidio or production injection detection.
- Typed Python tool functions — not real MCP transport.
- No auth provider; principal is passed in the request body.
- No artifacts/RAG server, multi-source joins, or UI.

## Phase 1 features (current)

- **Identity broker seam** — swappable `StubIdentityBroker` (default) and `WifIdentityBroker` skeleton; audit records both requesting principal and executing identity.
- **Embedding retrieval tier** — `GROUNDING_RETRIEVAL=auto|embedding|keyword` with hash-based embeddings by default; optional `pip install -e ".[embeddings]"` for sentence-transformers.
- **Expanded revenue domain registry** — `order_count`, `average_order_value` alongside existing revenue/customer metrics.
- **Eval metric hooks** — `GET /metrics` exposes deflection rate, clarification rate, latency and bytes averages for Phase 3 evaluation.
- **Golden-set eval harness** — `python -m app.eval` runs labeled trust cases offline; `pytest tests/test_eval_harness.py` gates CI.

### Identity modes

| Mode | Behavior | Production use |
|------|----------|----------------|
| `stub` (default) | Dev credential + app-side `{region_filter}` injection | Dev/CI only |
| `wif` | Skips row filter; expects BigQuery RLS + WIF/impersonation | Requires GCP setup |

Audit records include `executing_identity_id`, `executing_identity_type`, and `identity_mode` so every request answers *who asked* vs *who executed*.

**GCP activation checklist** (when you have a project): see [`docs/gcp-connectivity-checklist.md`](docs/gcp-connectivity-checklist.md) for the full list of what to provide.

1. Create a read-only service account and row access policies on `sales`, `orders`, `customers` — see [`docs/bigquery-rls-setup.sql`](docs/bigquery-rls-setup.sql)
2. Configure Workload Identity Federation or service account impersonation
3. Set `IDENTITY_MODE=wif`, `BQ_IMPERSONATE_TARGET`, and/or `WIF_PROVIDER_CONFIG`
4. Verify queries no longer inject app-side `region IN (...)` filters
5. Run an integration test against real BigQuery and confirm audit fields

### Retrieval modes

| Mode | Behavior |
|------|----------|
| `auto` (default) | Embedding retrieval with hash vectors; uses sentence-transformers when installed |
| `embedding` | Force embedding path |
| `keyword` | Phase 0 keyword/alias matching only |

### Metrics endpoint

```bash
curl http://localhost:8000/metrics
```

Returns counters keyed by response status plus `deflection_rate` and `clarification_rate`.

### Mock BigQuery (local dev, no GCP)

When `BQ_PROJECT_ID=dev-project` or `BQ_USE_MOCK=1`, queries run against seed JSON tables in [`mock_data/`](mock_data/):

| File | Contents |
|------|----------|
| `sales.json` | Row-level `amount` / `net_amount` by month and region |
| `orders.json` | Monthly rollups: `order_count`, `total_order_amount` |
| `customers.json` | Monthly rollups: `active_customers` |

Regions: **US**, **EU**, **APAC**. Months: **2026-05**, **2026-06**.

The mock executor applies month params and principal region filters like the real warehouse stub. Example (US+EU, 2026-06): total revenue **$1.25M**, order count **18,400**, AOV **$67.93**, active customers **42,500**.

### Evaluation harness (golden set)

Offline trust eval over labeled questions in [`eval/golden_set.yaml`](eval/golden_set.yaml):

```bash
python -m app.eval              # human-readable summary
python -m app.eval --json         # full JSON report
pytest tests/test_eval_harness.py # CI gate (all golden cases must pass)
```

Reports **deflection rate**, **clarification rate**, and **decline rate** plus per-case pass/fail against expected status, metric source, and audit fields. Uses mock BigQuery + stub identity — no live GCP or Anthropic API.

## Test UI (Next.js)

A developer harness lives in [`../data-answers-ui`](../data-answers-ui/). It is not a production business interface.

```bash
# Terminal 1 — API
cd data-answers-agent
uvicorn app.main:app --reload --port 8000

# Terminal 2 — UI
cd ../data-answers-ui
cp .env.local.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). CORS defaults to `http://localhost:3000` via `CORS_ORIGINS`.

## Before hardening — TODO seams

Search the codebase for `# TODO(harden)` and `# DECISION-NEEDED`. Key seams:

| Seam | Location | Action before production |
|------|----------|-------------------------|
| Identity → real RLS | `app/identity/wif_broker.py` | Implement WIF/impersonation credential minting |
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
    identity/
      broker.py          # IdentityBroker protocol + factory
      stub_broker.py     # Dev credential + row filter (default)
      wif_broker.py      # WIF/impersonation skeleton
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
    eval/
      harness.py         # Golden-set runner
      models.py          # EvalReport, GoldenCase
  eval/
    golden_set.yaml      # Labeled questions for offline eval
  docs/
    bigquery-rls-setup.sql
  mock_data/
    sales.json
    orders.json
    customers.json
  tests/
  pyproject.toml
  .env.example
```
