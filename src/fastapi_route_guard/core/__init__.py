from fastapi_route_guard.core.models import AuthorizationContext
from fastapi_route_guard.core.policy import RoutePolicy
from fastapi_route_guard.core.principal import AuthorizationPrincipal
from fastapi_route_guard.core.resource import (
    AttributesResolverLike,
    ResolverLike,
    ResourceAttributes,
    ResourceAttributesResolver,
    ResourceResolver,
)
from fastapi_route_guard.core.result import AuthorizationResult, AuthorizationViolation
from fastapi_route_guard.core.violations import ViolationCode

__all__ = [
    "AttributesResolverLike",
    "AuthorizationContext",
    "AuthorizationPrincipal",
    "AuthorizationResult",
    "AuthorizationViolation",
    "ResolverLike",
    "ResourceAttributes",
    "ResourceAttributesResolver",
    "ResourceResolver",
    "RoutePolicy",
    "ViolationCode",
]
