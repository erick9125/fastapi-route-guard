from collections.abc import Sequence
from typing import Any

from fastapi_route_guard.core.models import AuthorizationContext
from fastapi_route_guard.core.policy import RoutePolicy
from fastapi_route_guard.core.principal import AuthorizationPrincipal
from fastapi_route_guard.core.resource import ResourceAttributes
from fastapi_route_guard.core.result import AuthorizationResult
from fastapi_route_guard.evaluators.custom import PolicyHandler
from fastapi_route_guard.evaluators.evaluator import PolicyEvaluator
from fastapi_route_guard.registry.policies import PolicyRegistry


async def evaluate_policy(
    *,
    policy: RoutePolicy,
    principal: AuthorizationPrincipal | None = None,
    resource: object | None = None,
    attributes: ResourceAttributes | None = None,
    handlers: Sequence[PolicyHandler] = (),
    collect_all: bool = False,
    request_context: dict[str, Any] | None = None,
) -> AuthorizationResult:
    registry = PolicyRegistry(list(handlers))
    evaluator = PolicyEvaluator(registry=registry, collect_all=collect_all)
    context = AuthorizationContext(
        principal=principal,
        resource=resource,
        resource_type=policy.resource,
        action=policy.action,
        attributes=attributes,
        request_context=request_context or {},
    )
    return await evaluator.evaluate(policy, context)
