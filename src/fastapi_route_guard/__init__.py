from fastapi_route_guard.core.models import AuthorizationContext
from fastapi_route_guard.core.policy import RoutePolicy
from fastapi_route_guard.core.principal import AuthorizationPrincipal
from fastapi_route_guard.core.resource import (
    ResourceAttributes,
    ResourceAttributesResolver,
    ResourceResolver,
    TResource,
)
from fastapi_route_guard.core.result import AuthorizationResult, AuthorizationViolation
from fastapi_route_guard.core.violations import ViolationCode
from fastapi_route_guard.evaluators.custom import PolicyHandler
from fastapi_route_guard.evaluators.evaluator import PolicyEvaluator
from fastapi_route_guard.evaluators.ownership import OwnershipEvaluator
from fastapi_route_guard.evaluators.roles import RoleEvaluator
from fastapi_route_guard.evaluators.scopes import ScopeEvaluator
from fastapi_route_guard.evaluators.tenant import TenantEvaluator
from fastapi_route_guard.exceptions import (
    DuplicatePolicyHandler,
    DuplicateResource,
    InvalidPrincipal,
    MissingObjectCheck,
    MissingResourceId,
    PolicyEvaluationError,
    PolicyHandlerNotFound,
    ResourceNotRegistered,
)
from fastapi_route_guard.fastapi.exceptions import AuthorizationDenied
from fastapi_route_guard.fastapi.guard import RouteGuard
from fastapi_route_guard.registry.policies import PolicyRegistry
from fastapi_route_guard.registry.resources import (
    ResourceRegistration,
    ResourceRegistry,
)
from fastapi_route_guard.testing.builders import evaluate_policy
from fastapi_route_guard.testing.principals import make_principal

__all__ = [
    "AuthorizationContext",
    "AuthorizationDenied",
    "AuthorizationPrincipal",
    "AuthorizationResult",
    "AuthorizationViolation",
    "DuplicatePolicyHandler",
    "DuplicateResource",
    "InvalidPrincipal",
    "MissingObjectCheck",
    "MissingResourceId",
    "OwnershipEvaluator",
    "PolicyEvaluationError",
    "PolicyEvaluator",
    "PolicyHandler",
    "PolicyHandlerNotFound",
    "PolicyRegistry",
    "ResourceAttributes",
    "ResourceAttributesResolver",
    "ResourceNotRegistered",
    "ResourceRegistration",
    "ResourceRegistry",
    "ResourceResolver",
    "RoleEvaluator",
    "RouteGuard",
    "RoutePolicy",
    "ScopeEvaluator",
    "TResource",
    "TenantEvaluator",
    "ViolationCode",
    "evaluate_policy",
    "make_principal",
]
