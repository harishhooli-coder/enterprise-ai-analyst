# Mock warehouse seed data
#
# Used when BQ_USE_MOCK=1 or BQ_PROJECT_ID=dev-project (default).
# Row-level sales; monthly rollups for orders and customers.
#
# Regions: US, EU, APAC
# Months: 2026-05, 2026-06
#
# Example (US+EU, 2026-06):
#   total_revenue      1,250,000
#   net_revenue          980,000
#   order_count           18,400
#   average_order_value     67.93
#   active_customers      42,500
