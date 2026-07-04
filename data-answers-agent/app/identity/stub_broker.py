"""Stub identity broker — dev credential + app-side row filter (Pattern A)."""

from __future__ import annotations

from app.config import get_settings
from app.models import ExecutionContext, UserPrincipal


class StubIdentityBroker:
    """Mints a fixed dev-readonly identity; row filter injected at query time."""

    def mint(self, principal: UserPrincipal) -> ExecutionContext:
        settings = get_settings()
        if settings.bq_dev_service_account:
            executing_id = settings.bq_dev_service_account
        else:
            executing_id = f"dev-readonly@{settings.bq_project_id}.iam.gserviceaccount.com"

        return ExecutionContext(
            requesting_principal=principal,
            executing_identity_id=executing_id,
            executing_identity_type="stub_dev",
            uses_warehouse_rls=False,
        )
