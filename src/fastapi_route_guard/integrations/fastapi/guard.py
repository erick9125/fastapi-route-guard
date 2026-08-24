import inspect
from collections.abc import Awaitable, Callable, Iterator
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, FastAPI
from starlette.requests import Request

from fastapi_route_guard.core.models import AuthorizationContext
from fastapi_route_guard.core.policy import RoutePolicy
from fastapi_route_guard.core.principal import AuthorizationPrincipal
from fastapi_route_guard.core.resource import (
    AttributesResolverLike,
    ResolverLike,
    ResourceAttributes,
)
from fastapi_route_guard.evaluators.custom import PolicyHandler
from fastapi_route_guard.evaluators.evaluator import PolicyEvaluator
from fastapi_route_guard.exceptions import (
    IdParameterNotInPath,
    InvalidPrincipal,
    MissingObjectCheck,
    MissingResourceId,
)
from fastapi_route_guard.integrations.fastapi.context import build_request_context
from fastapi_route_guard.integrations.fastapi.dependencies import (
    INVALID_ID,
    call_resolver,
    callable_from,
    coerce_resource_id,
    collector_for,
    id_parameter,
    parameter_annotation,
    resource_parameter,
)
from fastapi_route_guard.integrations.fastapi.exceptions import AuthorizationDenied
from fastapi_route_guard.registry.policies import PolicyRegistry
from fastapi_route_guard.registry.resources import ResourceRegistry

PrincipalDependency = Callable[..., Any]

_REQUEST_ARG = "_guard_request"
_PRINCIPAL_ARG = "_guard_principal"
_RESOLVER_ARGS = "_guard_resolver_args"
_ATTRIBUTE_ARGS = "_guard_attribute_args"


def _parameter(name: str, annotation: object) -> inspect.Parameter:
    return inspect.Parameter(
        name,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        annotation=annotation,
    )


def _dependency_calls(route: object) -> Iterator[Callable[..., Any]]:
    """Every callable FastAPI resolves for a route, sub-dependencies included."""
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return
    pending = [dependant]
    while pending:
        current = pending.pop()
        call = getattr(current, "call", None)
        if callable(call):
            yield call
        pending.extend(getattr(current, "dependencies", ()))


def _checked_principal(
    principal: object,
    dependency: PrincipalDependency,
) -> AuthorizationPrincipal | None:
    """FastAPI does not validate what a dependency returns, so the guard does.

    A principal dependency that forgets to map the application user would
    otherwise fail deep inside an evaluator with an anonymous ``AttributeError``.
    """
    if principal is None or isinstance(principal, AuthorizationPrincipal):
        return principal
    raise InvalidPrincipal(
        getattr(dependency, "__name__", repr(dependency)),
        type(principal).__name__,
    )


class RouteGuard:
    def __init__(
        self,
        *,
        principal: PrincipalDependency,
        collect_all: bool = False,
    ) -> None:
        self._principal = principal
        self._resources = ResourceRegistry()
        self._policies = PolicyRegistry()
        self._evaluator = PolicyEvaluator(
            registry=self._policies,
            collect_all=collect_all,
        )
        self._wiring: dict[Callable[..., Any], tuple[str, str]] = {}

    def validate(self, app: FastAPI | APIRouter) -> None:
        """Check this guard's dependencies against the routes they are mounted on.

        The path a dependency ends up on is only known once the route is
        declared, so this cannot be checked while wiring. Call it at startup —
        or in a test — to turn a mistyped `id_param` into a boot failure instead
        of a 500 on the first request to that endpoint.
        """
        for route in app.routes:
            path_params = set(getattr(route, "param_convertors", {}) or {})
            for call in _dependency_calls(route):
                wiring = self._wiring.get(call)
                if wiring is None:
                    continue
                resource, id_param = wiring
                if id_param not in path_params:
                    raise IdParameterNotInPath(
                        resource,
                        id_param,
                        getattr(route, "path", "?"),
                    )

    def add_resource(
        self,
        name: str,
        *,
        resolver: ResolverLike,
        attributes: AttributesResolverLike,
    ) -> None:
        self._resources.register(name, resolver=resolver, attributes=attributes)

    def add_policy_handler(self, handler: PolicyHandler) -> None:
        self._policies.register(handler)

    def _require_handlers(self, handler_names: tuple[str, ...]) -> None:
        """Resolve every handler name now, so a typo fails at wiring time."""
        for name in handler_names:
            self._policies.get(name)

    def protect(
        self,
        *,
        action: str | None = None,
        roles: set[str] | None = None,
        scopes: set[str] | None = None,
        handler_names: tuple[str, ...] = (),
    ) -> Callable[..., Awaitable[None]]:
        policy = RoutePolicy(
            action=action,
            roles=frozenset(roles or ()),
            scopes=frozenset(scopes or ()),
            handler_names=handler_names,
        )
        self._require_handlers(handler_names)

        async def dependency(
            request: Request,
            principal: Annotated[Any, Depends(self._principal)] = None,
        ) -> None:
            context = AuthorizationContext(
                principal=_checked_principal(principal, self._principal),
                resource=None,
                resource_type=None,
                action=action,
                attributes=None,
                request_context=build_request_context(request),
            )
            result = await self._evaluator.evaluate(policy, context)
            if not result.allowed:
                raise AuthorizationDenied(result)

        dependency.__name__ = "protect"
        return dependency

    def protect_resource(
        self,
        resource: str,
        *,
        id_param: str,
        action: str | None = None,
        roles: set[str] | None = None,
        scopes: set[str] | None = None,
        ownership: bool = False,
        tenant: bool = False,
        handler_names: tuple[str, ...] = (),
        unsafe_skip_object_check: bool = False,
    ) -> Callable[..., Awaitable[Any]]:
        policy = RoutePolicy(
            resource=resource,
            action=action,
            roles=frozenset(roles or ()),
            scopes=frozenset(scopes or ()),
            ownership=ownership,
            tenant=tenant,
            handler_names=handler_names,
        )
        if (
            not unsafe_skip_object_check
            and not policy.tenant
            and not policy.ownership
            and not policy.handler_names
        ):
            raise MissingObjectCheck(resource)

        # Resolved at wiring time: the resolver signatures decide the shape of
        # the dependency FastAPI introspects when the route is registered.
        registration = self._resources.get(resource)
        resolver_call = callable_from(registration.resolver)
        attributes_call = callable_from(registration.attributes)
        resource_id_arg = id_parameter(resolver_call, id_param)
        resource_id_type = parameter_annotation(resolver_call, resource_id_arg)
        resource_arg = resource_parameter(attributes_call)
        resolver_deps = collector_for(resolver_call, exclude={resource_id_arg})
        attribute_deps = collector_for(attributes_call, exclude={resource_arg})
        self._require_handlers(handler_names)

        async def dependency(**guard_args: Any) -> Any:
            request = cast(Request, guard_args[_REQUEST_ARG])
            principal = _checked_principal(guard_args[_PRINCIPAL_ARG], self._principal)
            claims_context = AuthorizationContext(
                principal=principal,
                resource=None,
                resource_type=resource,
                action=action,
                attributes=None,
                request_context=build_request_context(request),
            )
            claims = self._evaluator.evaluate_claims(policy, claims_context)
            if not claims.allowed:
                raise AuthorizationDenied(claims)

            resource_id = request.path_params.get(id_param)
            if resource_id is None:
                raise MissingResourceId(id_param)

            coerced_id = coerce_resource_id(str(resource_id), resource_id_type)
            loaded = None
            if coerced_id is not INVALID_ID:
                loaded = await call_resolver(
                    resolver_call,
                    **{resource_id_arg: coerced_id},
                    **guard_args[_RESOLVER_ARGS],
                )
            attributes: ResourceAttributes | None = None
            if loaded is not None:
                resolved = await call_resolver(
                    attributes_call,
                    **{resource_arg: loaded},
                    **guard_args[_ATTRIBUTE_ARGS],
                )
                if not isinstance(resolved, ResourceAttributes):
                    raise TypeError(
                        "Resource attributes resolver must return ResourceAttributes."
                    )
                attributes = resolved

            context = AuthorizationContext(
                principal=principal,
                resource=loaded,
                resource_type=resource,
                action=action,
                attributes=attributes,
                request_context=build_request_context(request),
            )
            result = await self._evaluator.evaluate_resource(policy, context)
            if not result.allowed:
                raise AuthorizationDenied(result)
            return loaded

        dependency.__name__ = f"protect_{resource}"
        self._wiring[dependency] = (resource, id_param)
        dependency.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
            [
                _parameter(_REQUEST_ARG, Request),
                _parameter(
                    _PRINCIPAL_ARG,
                    Annotated[Any, Depends(self._principal)],
                ),
                _parameter(
                    _RESOLVER_ARGS,
                    Annotated[dict[str, Any], Depends(resolver_deps)],
                ),
                _parameter(
                    _ATTRIBUTE_ARGS,
                    Annotated[dict[str, Any], Depends(attribute_deps)],
                ),
            ]
        )
        return dependency
