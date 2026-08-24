from importlib.metadata import PackageNotFoundError, version

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
from fastapi_route_guard.evaluators.custom import PolicyHandler
from fastapi_route_guard.evaluators.evaluator import PolicyEvaluator
from fastapi_route_guard.evaluators.ownership import OwnershipEvaluator
from fastapi_route_guard.evaluators.roles import RoleEvaluator
from fastapi_route_guard.evaluators.scopes import ScopeEvaluator
from fastapi_route_guard.evaluators.tenant import TenantEvaluator
from fastapi_route_guard.exceptions import (
    DuplicatePolicyHandler,
    DuplicateResource,
    IdParameterNotInPath,
    InvalidPrincipal,
    MissingObjectCheck,
    MissingResourceId,
    PolicyEvaluationError,
    PolicyHandlerNotFound,
    ResourceNotRegistered,
)
from fastapi_route_guard.integrations.fastapi.exceptions import AuthorizationDenied
from fastapi_route_guard.integrations.fastapi.guard import RouteGuard
from fastapi_route_guard.registry.policies import PolicyRegistry
from fastapi_route_guard.registry.resources import (
    ResourceRegistration,
    ResourceRegistry,
)
from fastapi_route_guard.testing.builders import evaluate_policy
from fastapi_route_guard.testing.principals import make_principal

try:
    __version__ = version("fastapi-route-guard")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0.dev0"

__all__ = [
    "AttributesResolverLike",
    "AuthorizationContext",
    "AuthorizationDenied",
    "AuthorizationPrincipal",
    "AuthorizationResult",
    "AuthorizationViolation",
    "DuplicatePolicyHandler",
    "DuplicateResource",
    "IdParameterNotInPath",
    "InvalidPrincipal",
    "MissingObjectCheck",
    "MissingResourceId",
    "OwnershipEvaluator",
    "PolicyEvaluationError",
    "PolicyEvaluator",
    "PolicyHandler",
    "PolicyHandlerNotFound",
    "PolicyRegistry",
    "ResolverLike",
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
    "TenantEvaluator",
    "ViolationCode",
    "__version__",
    "evaluate_policy",
    "make_principal",
]
