---
name: identity-bigquery-rls
description: >-
  Per-user BigQuery identity via Workload Identity Federation, service account
  impersonation, and RLS for the Data-Ansights Agent. Use when hardening the
  identity stub, replacing WHERE-clause row filters, or implementing Pattern A
  to production auth.
---

# Identity & BigQuery RLS (Hardening)

## Skeleton (Phase 0) — Pattern A stub

- Thread `UserPrincipal` through every layer
- Executor may use single dev credential BUT must:
  1. Accept and log principal
  2. Apply WHERE-clause row filter from `allowed_regions`
  3. Structure for one-module swap to real auth

```python
# TODO(harden): replace stub row-filter with BigQuery RLS via WIF/impersonation
```

## Target (Phase 1) — agent acts AS the user

No all-seeing service account. End-user principal → short-lived, downscoped credential.

## GCP packages

```toml
"google-auth>=2.0",
"google-auth-oauthlib>=1.0",
"google-cloud-bigquery>=3.0",
```

## Workload Identity Federation flow

1. Consuming system passes end-user principal (from their IdP) to `POST /ask`
2. Identity broker validates principal; rejects service-only tokens when human required
3. Mint short-lived credential scoped to user (impersonation or federated token)
4. BigQuery client uses **user credential** — RLS + column masking apply automatically

## BigQuery RLS (preferred over app filters)

Define row access policies on tables — enforcement in warehouse, not prompt:

```sql
CREATE ROW ACCESS POLICY region_policy
ON dataset.sales
GRANT TO ("user:{{end_user_email}}")
FILTER USING (region IN UNNEST(@allowed_regions));
```

Remove app-side `region_filter` injection once RLS is verified.

## Identity broker interface

```python
class IdentityBroker:
    def mint_credential(self, principal: UserPrincipal) -> Credentials:
        ...
```

Single module change at executor seam when swapping stub → production.

## Audit requirements

Log: requesting principal, executing identity, allow/deny, bytes scanned. Must reconstruct who saw what.

## Feasibility gate

Validate WIF/impersonation in your GCP setup **before** any real data or multi-user pilot. Everything in the security model depends on this.
