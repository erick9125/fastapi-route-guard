from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from fastapi_route_guard.exceptions import DuplicateResource, ResourceNotRegistered

ResourceResolverFn = Callable[..., Awaitable[Any | None]]
AttributesResolverFn = Callable[..., Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class ResourceRegistration:
    name: str
    resolver: ResourceResolverFn | object
    attributes: AttributesResolverFn | object


class ResourceRegistry:
    def __init__(self) -> None:
        self._resources: dict[str, ResourceRegistration] = {}

    def register(
        self,
        name: str,
        *,
        resolver: ResourceResolverFn | object,
        attributes: AttributesResolverFn | object,
    ) -> None:
        if name in self._resources:
            raise DuplicateResource(name)
        self._resources[name] = ResourceRegistration(
            name=name,
            resolver=resolver,
            attributes=attributes,
        )

    def get(self, name: str) -> ResourceRegistration:
        try:
            return self._resources[name]
        except KeyError as exc:
            raise ResourceNotRegistered(name) from exc
