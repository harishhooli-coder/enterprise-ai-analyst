---
name: opentelemetry-observability
description: >-
  OpenTelemetry tracing, metrics, and structured audit export for the
  Data-Answers Agent. Use when hardening audit.py, adding Prometheus metrics,
  or instrumenting the orchestrator loop for Phase 2–3 evaluation.
---

# OpenTelemetry & Observability (Phase 2–3)

## Skeleton default

Structlog JSON to stdout — sufficient for Phase 0 acceptance.

## Phase 2 packages

```toml
"opentelemetry-api>=1.28",
"opentelemetry-sdk>=1.28",
"opentelemetry-instrumentation-fastapi>=0.49",
"opentelemetry-exporter-gcp-trace>=1.6",  # if on GCP
"prometheus-client>=0.21",
```

## Span structure (one trace per /ask)

```
ask.request
├── guardrails.scan_input
├── model_router.classify
├── grounding.resolve
├── policy.authorize
├── warehouse.query
├── model_router.reason (optional)
├── guardrails.redact_output
└── audit.close
```

Attributes on spans: `request_id`, `user_id`, `metric_id`, `policy_decision`, `bytes_scanned`, `response_status`.

## Success metrics hooks (SPEC §9)

Instrument counters/histograms for later eval:

| Metric | Type | Purpose |
|--------|------|---------|
| `agent_requests_total` | counter by status | Deflection rate |
| `agent_latency_seconds` | histogram | Time-to-answer |
| `agent_clarifications_total` | counter | Clarification rate |
| `agent_declines_total` | counter by reason | Refusal vs hallucination proxy |
| `bq_bytes_scanned` | histogram | Cost control |

## Audit vs traces

- **Audit log** — reconstructable business record (who, what query, allow/deny)
- **Traces** — latency debugging across components
- Correlate via `request_id` on both

## FastAPI instrumentation

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
FastAPIInstrumentor.instrument_app(app)
```

```python
# TODO(harden): wire OTel exporter + Prometheus /metrics endpoint
```

## Evaluation harness (Phase 3)

Export audit records to parquet/JSONL for offline eval with pytest golden sets or promptfoo/Ragas — measure refusal-vs-hallucination on labeled question sets.
