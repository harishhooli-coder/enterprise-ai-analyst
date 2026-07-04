---
name: grounding-verified-queries
description: >-
  Grounding registry and verified-query matching for the Data-Answers Agent.
  Use when creating registry.yaml, grounding_service.py, metric definitions,
  ambiguity detection, or embedding/cosine retrieval over the registry.
---

# Grounding & Verified Queries

## Purpose

Every answer traces to a defined metric or vetted query template. No free-form SQL on raw schemas.

## registry.yaml structure

```yaml
metrics:
  - id: total_revenue
    name: Total Revenue
    description: Sum of gross revenue for a calendar month
    aliases: [revenue, gross revenue, total sales]
    template: |
      SELECT SUM(amount) AS total_revenue
      FROM `{project}.{dataset}.sales`
      WHERE month = @month
        AND {region_filter}
    parameters:
      - name: month
        type: string
        description: Calendar month YYYY-MM
    ambiguity_group: revenue  # shared word → forces clarify tests

  - id: net_revenue
    name: Net Revenue
    description: Revenue after returns and discounts
    aliases: [net revenue, revenue after returns]
    template: |
      SELECT SUM(net_amount) AS net_revenue
      FROM `{project}.{dataset}.sales`
      WHERE month = @month
        AND {region_filter}
    parameters:
      - name: month
        type: string
    ambiguity_group: revenue
```

## Grounding service outcomes

```python
class GroundingResult(BaseModel):
    status: Literal["match", "ambiguous", "out_of_set"]
    metric_id: Optional[str] = None
    template: Optional[str] = None
    resolved_params: Optional[dict[str, str]] = None
    candidates: Optional[list[str]] = None  # metric ids when ambiguous
    clarify_prompt: Optional[str] = None
```

| Outcome | When | Agent response |
|---------|------|----------------|
| `match` | One clear metric + resolvable params | Proceed to policy → warehouse |
| `ambiguous` | >1 plausible metric (e.g. revenue vs net revenue) | `needs_clarification` |
| `out_of_set` | No registry match | `declined` — routed to human |

## Skeleton retrieval (simple → embeddings later)

Phase 0 options (pick one, keep interface stable):

1. **Keyword/alias match** — score aliases + description tokens
2. **Cosine over embeddings** — `sentence-transformers` + in-memory vectors at startup

```python
# Skeleton cosine (Phase 0)
from sklearn.metrics.pairwise import cosine_similarity
# Embed registry descriptions; embed question; threshold + top-k
```

## Parameter resolution

- Extract `{month}` from question via regex/heuristic or cheap model tier
- Never pass unresolved required params to warehouse — clarify instead
- `{region_filter}` is NOT from the question — injected from principal in warehouse tool

## Tests required

- Ambiguous question ("What was revenue last month?") → `ambiguous`
- Unknown question ("How many unicorns?") → `out_of_set`
- Clear question with month → `match` with resolved params

## Phase 1 seam

```python
# TODO(harden): back registry with dbt Semantic Layer or Cube; add join-path graph reasoning
```

See also: `semantic-layer-dbt-cube` skill for Phase 1.
