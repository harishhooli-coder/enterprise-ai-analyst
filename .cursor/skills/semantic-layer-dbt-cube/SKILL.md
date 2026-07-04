---
name: semantic-layer-dbt-cube
description: >-
  dbt Semantic Layer (MetricFlow) and Cube patterns for Phase 1 grounding.
  Use when replacing flat registry.yaml with a real semantic layer, defining
  metrics, lineage, or join-path resolution for the Data-Answers Agent.
---

# Semantic Layer — dbt / Cube (Phase 1)

## When to adopt

Replace flat `registry.yaml` when question variety outgrows a single YAML file. Skeleton stays YAML-only; this skill guides Phase 1.

## Option A: dbt + MetricFlow

- **dbt Core** (OSS) defines models in warehouse
- **MetricFlow** semantic layer exposes metrics with dimensions
- Agent grounding maps natural language → metric name + dimensions (not raw tables)

```yaml
# metrics/total_revenue.yml (dbt metric)
metrics:
  - name: total_revenue
    type: simple
    type_params:
      measure: revenue
    filter: |
      {{ Dimension('sales__region') }} IN ({{ allowed_regions }})
```

Grounding service calls MetricFlow API or compiled manifest — never raw `SELECT` from agent.

## Option B: Cube

- **Cube** (OSS) headless semantic layer with REST/GraphQL API
- Pre-aggregations for cost control
- Agent retrieves metric definitions via Cube meta API

## Join-path resolution (Phase 1)

Reason over metric lineage graph (not raw schema dump):

```python
# TODO(harden): structural/graph reasoning over semantic layer for join paths
# NetworkX or semantic-layer-native APIs
```

## Migration seam from skeleton

1. Keep `GroundingResult` interface unchanged
2. Swap YAML loader for semantic-layer client behind `GroundingService`
3. Verified-query templates become metric queries with bound dimensions
4. Audit logs `source` as metric id from semantic layer

## Rules (unchanged from skeleton)

- Agent never free-forms SQL on raw tables
- Out-of-set metrics → decline
- Identity enforced at warehouse (RLS), not in metric definitions as prompt text
