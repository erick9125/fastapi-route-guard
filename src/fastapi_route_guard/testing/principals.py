from typing import Any

from fastapi_route_guard.core.principal import AuthorizationPrincipal


def make_principal(
    *,
    id: str = "user-1",
    roles: set[str] | None = None,
    scopes: set[str] | None = None,
    tenant_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> AuthorizationPrincipal:
    return AuthorizationPrincipal(
        id=id,
        roles=roles or set(),
        scopes=scopes or set(),
        tenant_id=tenant_id,
        attributes=attributes or {},
    )
