"""WIF / impersonation identity broker skeleton — requires GCP configuration."""

from __future__ import annotations

from app.config import get_settings
from app.identity.broker import IdentityConfigurationError
from app.models import ExecutionContext, UserPrincipal

# TODO(harden): replace stub row-filter with BigQuery RLS via WIF/impersonation
_ACTIVATION_CHECKLIST = (
    "WIF identity mode requires GCP configuration. Before enabling IDENTITY_MODE=wif:\n"
    "  1. Create read-only service account and BigQuery row access policies\n"
    "  2. Configure Workload Identity Federation or SA impersonation\n"
    "  3. Set BQ_IMPERSONATE_TARGET and/or WIF_PROVIDER_CONFIG env vars\n"
    "  4. Verify RLS enforces region access without app-side row filters\n"
    "See docs/bigquery-rls-setup.sql for example RLS policies."
)


class WifIdentityBroker:
    """Skeleton broker for per-user BigQuery credentials via WIF/impersonation."""

    def mint(self, principal: UserPrincipal) -> ExecutionContext:
        settings = get_settings()
        has_impersonation = bool(settings.bq_impersonate_target.strip())
        has_wif = bool(settings.wif_provider_config.strip())

        if not has_impersonation and not has_wif:
            raise IdentityConfigurationError(_ACTIVATION_CHECKLIST)

        # TODO(harden): mint real federated or impersonated credentials here
        executing_id = principal.email or f"user:{principal.user_id}"
        if has_impersonation:
            executing_id = settings.bq_impersonate_target

        return ExecutionContext(
            requesting_principal=principal,
            executing_identity_id=executing_id,
            executing_identity_type="impersonated_sa" if has_impersonation else "federated_user",
            uses_warehouse_rls=True,
        )
