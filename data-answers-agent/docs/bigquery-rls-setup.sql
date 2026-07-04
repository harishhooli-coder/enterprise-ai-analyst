# BigQuery RLS setup reference (documentation only — not executed by the agent)
#
# Use this checklist when activating IDENTITY_MODE=wif with real GCP.
# See README.md "Identity modes" section for the full activation steps.

-- Example row access policy for sales table (region-scoped)
-- Replace dataset/table names and grantee with your project values.

CREATE ROW ACCESS POLICY region_policy_sales
ON `YOUR_PROJECT.analytics.sales`
GRANT TO ("user:END_USER_EMAIL@YOUR_DOMAIN.com")
FILTER USING (region IN UNNEST(['US', 'EU']));

-- Repeat for orders and customers tables used by the registry templates:

CREATE ROW ACCESS POLICY region_policy_orders
ON `YOUR_PROJECT.analytics.orders`
GRANT TO ("user:END_USER_EMAIL@YOUR_DOMAIN.com")
FILTER USING (region IN UNNEST(['US', 'EU']));

CREATE ROW ACCESS POLICY region_policy_customers
ON `YOUR_PROJECT.analytics.customers`
GRANT TO ("user:END_USER_EMAIL@YOUR_DOMAIN.com")
FILTER USING (region IN UNNEST(['US', 'EU']));

-- After RLS is verified:
-- 1. Set IDENTITY_MODE=wif
-- 2. Configure BQ_IMPERSONATE_TARGET or WIF_PROVIDER_CONFIG
-- 3. Confirm audit records show executing_identity_id distinct from requesting principal
-- 4. Confirm warehouse queries no longer inject app-side region IN (...) filters
