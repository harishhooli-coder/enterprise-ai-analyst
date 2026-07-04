"""Identity broker protocol and factory."""

from __future__ import annotations

from typing import Optional, Protocol

from app.config import get_settings
from app.models import ExecutionContext, UserPrincipal

_broker_override: Optional["IdentityBroker"] = None


class IdentityConfigurationError(Exception):
    """Raised when WIF/impersonation mode is enabled but not configured."""


class IdentityBroker(Protocol):
    """Mint a short-lived execution context for warehouse queries."""

    def mint(self, principal: UserPrincipal) -> ExecutionContext:
        ...


def get_identity_broker() -> IdentityBroker:
    if _broker_override is not None:
        return _broker_override

    settings = get_settings()
    if settings.identity_mode == "wif":
        from app.identity.wif_broker import WifIdentityBroker

        return WifIdentityBroker()

    from app.identity.stub_broker import StubIdentityBroker

    return StubIdentityBroker()


def set_identity_broker(broker: Optional[IdentityBroker]) -> None:
    """Test hook: inject a fake identity broker."""
    global _broker_override
    _broker_override = broker
