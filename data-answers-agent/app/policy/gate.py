"""PEP→PDP policy gate — every tool call passes through authorize()."""

from __future__ import annotations

from typing import Any, Callable, Optional

from app.models import AllowDeny, UserPrincipal

# TODO(harden): replace with OPA/Rego or warehouse-native policy engine

AuditCallback = Callable[[str, UserPrincipal, str, dict[str, Any], AllowDeny], None]


def authorize(
    principal: UserPrincipal,
    resource: str,
    metadata: Optional[dict[str, Any]] = None,
    *,
    audit_callback: Optional[AuditCallback] = None,
) -> AllowDeny:
    """Allow if principal has at least one allowed region; otherwise deny."""
    meta = metadata or {}

    if not principal.allowed_regions:
        decision = AllowDeny(allowed=False, reason="no_allowed_regions")
    else:
        decision = AllowDeny(allowed=True, reason="skeleton_allow")

    if audit_callback is not None:
        audit_callback("policy_decision", principal, resource, meta, decision)

    return decision
