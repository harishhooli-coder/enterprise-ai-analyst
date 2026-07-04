# GCP Connectivity Checklist

What to provide when connecting the Data-Answers Agent to real Google Cloud Platform (BigQuery).

The app reads configuration from environment variables (see [`.env.example`](../.env.example)). **Do not paste secrets into chat or commit them to git** — use a local `.env`, Secret Manager, or your CI secret store.

---

## Two paths (pick one)

| Path | When to use | Security model |
|------|-------------|----------------|
| **A — Dev / single-user pilot** | First live BigQuery test | `IDENTITY_MODE=stub` + read-only service account + app-side region filter |
| **B — Enterprise / multi-user** | Real users, real data | `IDENTITY_MODE=wif` + BigQuery RLS + per-user credentials (WIF or impersonation) |

Path A is faster to validate connectivity. Path B is required before any real multi-user pilot.

See also: [Identity modes](../README.md#identity-modes) in the README and [`bigquery-rls-setup.sql`](bigquery-rls-setup.sql) for example RLS policies.

---

## 1. GCP project & BigQuery data

Provide (non-secret):

| Item | Example | Env var / notes |
|------|---------|-----------------|
| **GCP project ID** | `acme-analytics-prod` | `BQ_PROJECT_ID` |
| **Dataset name** | `analytics` | `BQ_DATASET` |
| **Region/location** | `US`, `EU`, `us-central1` | Where the dataset lives |
| **Table mapping** | `sales`, `orders`, `customers` | Must match or be mapped in `app/grounding/registry.yaml` |

### Expected schema (skeleton registry)

The verified-query templates in [`app/grounding/registry.yaml`](../app/grounding/registry.yaml) expect:

- **`sales`**: `month` (STRING `YYYY-MM`), `region`, `amount`, `net_amount`
- **`orders`**: `month`, `region`, plus row-level `order_amount` or aggregated columns used by templates
- **`customers`**: `month`, `region`, `active_customers` (or equivalent)

Mock seed data for reference: [`mock_data/`](../mock_data/).

If your warehouse uses different table or column names, provide a mapping — the registry is updated explicitly; the agent never improvises SQL against raw schemas.

Optional but useful:

- Sample row counts / which months have data
- Whether to load mock seed data into BigQuery or point at existing tables

---

## 2. Authentication (how the app talks to BigQuery)

Pick **one** runtime auth method:

### Option 1 — Service account key (dev only)

1. Create a **read-only** service account.
2. IAM: `roles/bigquery.jobUser` + `roles/bigquery.dataViewer` (dataset-scoped is better than project-wide).
3. Set `GOOGLE_APPLICATION_CREDENTIALS` to the JSON key path on the machine or container.
4. **Never** commit the key file or share it in chat.

### Option 2 — Application Default Credentials (preferred on GCP)

- App runs on Cloud Run, GKE, or GCE with an attached service account.
- No key file; provide the SA email and IAM bindings only.

### Option 3 — Local dev with `gcloud auth application-default login`

- Your user account must have BigQuery read access.
- Good for a quick smoke test.

Also configure:

| Item | Env var |
|------|---------|
| Read-only service account email (if used) | `BQ_DEV_SERVICE_ACCOUNT` |
| Max bytes per query (cost cap) | `MAX_BYTES_BILLED` (default `1000000000` = 1 GB) |
| Disable mock mode | `BQ_USE_MOCK=0` and a real `BQ_PROJECT_ID` (not `dev-project`) |

When `BQ_PROJECT_ID=dev-project` or `BQ_USE_MOCK=1`, queries run against local JSON mock data — not live BigQuery.

---

## 3. Identity & access control (enterprise / Path B)

For multi-user production, the agent must run **as the end user**, not one all-seeing service account. Provide:

| Item | Purpose |
|------|---------|
| **How users authenticate** to your app (OIDC/JWT from Okta, Azure AD, Google Workspace, etc.) | Drives `UserPrincipal` on `POST /ask` |
| **User identifier format** | Email (`user@company.com`) or stable `user_id` |
| **Region entitlements** | How you know `allowed_regions` per user (IdP claim, internal ACL, etc.) |
| **WIF vs SA impersonation** | Which pattern your security team allows |

### Environment variables (Path B)

| Env var | What to provide |
|---------|-----------------|
| `IDENTITY_MODE=wif` | Switches off app-side region filter; expects BigQuery RLS |
| `BQ_IMPERSONATE_TARGET` | Service account to impersonate per user (if using impersonation) |
| `WIF_PROVIDER_CONFIG` | Path or JSON for Workload Identity Federation provider |

### BigQuery RLS

Your GCP admin applies row access policies on `sales`, `orders`, and `customers`. Example SQL: [`bigquery-rls-setup.sql`](bigquery-rls-setup.sql).

Document:

- Which users or groups get which regions
- Whether RLS is already in place or needs to be created

After RLS is verified:

1. Set `IDENTITY_MODE=wif`
2. Configure `BQ_IMPERSONATE_TARGET` and/or `WIF_PROVIDER_CONFIG`
3. Confirm audit records show `executing_identity_id` distinct from the requesting principal
4. Confirm warehouse queries no longer inject app-side `region IN (...)` filters

---

## 4. App / API config (non-GCP but required for full E2E)

| Item | Env var |
|------|---------|
| Anthropic API key | `ANTHROPIC_API_KEY` |
| CORS (if using the UI) | `CORS_ORIGINS` |
| Agent limits | `AGENT_STEP_CAP`, `TOKEN_BUDGET`, `MAX_BYTES_BILLED` |
| Grounding retrieval | `GROUNDING_RETRIEVAL`, `EMBEDDING_MATCH_THRESHOLD`, `EMBEDDING_AMBIGUITY_MARGIN` |

---

## 5. Deployment context

So auth and networking are wired correctly:

- Where will the API run? (laptop, VM, Cloud Run, GKE, on-prem)
- Can it reach BigQuery APIs? (VPC-SC, Private Google Access, proxy?)
- Who calls `POST /ask`? (UI, internal portal, another service)
- Do you have a **staging** GCP project for the first live test?

---

## 6. What NOT to share in chat or docs

- Service account **private keys**
- Anthropic API keys
- WIF provider secrets

Use `.env` locally or Secret Manager. Share only **names, IDs, and architecture decisions**.

---

## Minimal starter pack (copy, fill in, send to your team)

```
Path: A (dev pilot) or B (enterprise)

GCP:
  project_id:
  dataset:
  location:
  tables: sales / orders / customers — same schema as skeleton? Y/N
  if N, column mapping:

Auth:
  method: SA key / ADC on Cloud Run / gcloud ADC
  readonly_sa_email:
  deployment: local / Cloud Run / other

Identity (Path B only):
  idp:
  user_id_format:
  region_entitlements_source:
  wif_or_impersonation:
  rls_status: not started / in progress / done

Limits:
  max_bytes_billed:
  staging_project_yes/no:

Anthropic: configured Y/N
```

---

## Activation steps (summary)

**Path A — dev pilot**

1. Create read-only SA with BigQuery job + data viewer on the target dataset.
2. Set `BQ_PROJECT_ID`, `BQ_DATASET`, `BQ_USE_MOCK=0`, and auth (`GOOGLE_APPLICATION_CREDENTIALS` or ADC).
3. Ensure tables match the registry schema (or update the registry).
4. Run the API and send a grounded question via `POST /ask`.
5. Confirm audit log shows bytes scanned and executing identity.

**Path B — enterprise**

1. Complete Path A smoke test.
2. Create BigQuery row access policies — see [`bigquery-rls-setup.sql`](bigquery-rls-setup.sql).
3. Configure Workload Identity Federation or service account impersonation.
4. Set `IDENTITY_MODE=wif`, `BQ_IMPERSONATE_TARGET`, and/or `WIF_PROVIDER_CONFIG`.
5. Run an integration test against real BigQuery and confirm audit fields (`executing_identity_id`, `identity_mode`).

---

## Related files

| File | Purpose |
|------|---------|
| [`.env.example`](../.env.example) | All supported environment variables |
| [`app/config.py`](../app/config.py) | Settings model |
| [`app/tools/warehouse.py`](../app/tools/warehouse.py) | Read-only BigQuery execution |
| [`app/identity/wif_broker.py`](../app/identity/wif_broker.py) | WIF / impersonation broker (hardening seam) |
| [`docs/bigquery-rls-setup.sql`](bigquery-rls-setup.sql) | Example RLS policies |
