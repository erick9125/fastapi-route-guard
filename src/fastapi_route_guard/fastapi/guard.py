import inspect
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, cast

from fastapi import Depends
from starlette.requests import Request

from fastapi_route_guard.core.models import AuthorizationContext
from fastapi_route_guard.core.policy import RoutePolicy
from fastapi_route_guard.core.principal import AuthorizationPrincipal
from fastapi_route_guard.core.resource import ResourceAttributes
from fastapi_route_guard.evaluators.custom import PolicyHandler
from fastapi_route_guard.evaluators.evaluator import PolicyEvaluator
from fastapi_route_guard.exceptions import MissingObjectCheck, MissingResourceId
from fastapi_route_guard.fastapi.context import build_request_context
from fastapi_route_guard.fastapi.dependencies import (
    call_resolver,
    callable_from,
    collector_for,
    id_parameter,
    resource_parameter,
)
from fastapi_route_guard.fastapi.exceptions import AuthorizationDenied
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

    def add_resource(
        self,
        name: str,
        *,
        resolver: object,
        attributes: object,
    ) -> None:
        self._resources.register(name, resolver=resolver, attributes=attributes)

    def policy(self, handler: PolicyHandler) -> None:
        self._policies.register(handler)

    def protect(
        self,
        *,
        action: str | None = None,
        roles: set[str] | None = None,
        scopes: set[str] | None = None,
        handlers: tuple[str, ...] = (),
    ) -> Callable[..., Awaitable[None]]:
        policy = RoutePolicy(
            action=action,
            roles=frozenset(roles or ()),
            scopes=frozenset(scopes or ()),
            handlers=handlers,
        )

        async def dependency(
            request: Request,
            principal: AuthorizationPrincipal | None = Depends(self._principal),
        ) -> None:
            context = AuthorizationContext(
                principal=principal,
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
        handlers: tuple[str, ...] = (),
        unsafe_skip_object_check: bool = False,
    ) -> Callable[..., Awaitable[Any]]:
        policy = RoutePolicy(
            resource=resource,
            action=action,
            roles=frozenset(roles or ()),
            scopes=frozenset(scopes or ()),
            ownership=ownership,
            tenant=tenant,
            handlers=handlers,
        )
        if (
            not unsafe_skip_object_check
            and not policy.tenant
            and not policy.ownership
            and not policy.handlers
        ):
            raise MissingObjectCheck(resource)

        # Resolved at wiring time: the resolver signatures decide the shape of
        # the dependency FastAPI introspects when the route is registered.
        registration = self._resources.get(resource)
        resolver_call = callable_from(registration.resolver)
        attributes_call = callable_from(registration.attributes)
        resource_id_arg = id_parameter(resolver_call, id_param)
        resource_arg = resource_parameter(attributes_call)
        resolver_deps = collector_for(resolver_call, exclude={resource_id_arg})
        attribute_deps = collector_for(attributes_call, exclude={resource_arg})

        async def dependency(**guard_args: Any) -> Any:
            request = cast(Request, guard_args[_REQUEST_ARG])
            principal = cast(AuthorizationPrincipal | None, guard_args[_PRINCIPAL_ARG])
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

            loaded = await call_resolver(
                resolver_call,
                **{resource_id_arg: str(resource_id)},
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
