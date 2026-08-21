from dataclasses import dataclass, field
from typing import Any

from fastapi_route_guard.core.principal import AuthorizationPrincipal
from fastapi_route_guard.core.resource import ResourceAttributes


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    principal: AuthorizationPrincipal | None
    resource: object | None
    resource_type: str | None
    action: str | None
    attributes: ResourceAttributes | None
    request_context: dict[str, Any] = field(default_factory=dict)
