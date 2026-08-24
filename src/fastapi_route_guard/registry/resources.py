from dataclasses import dataclass

from fastapi_route_guard.core.resource import AttributesResolverLike, ResolverLike
from fastapi_route_guard.exceptions import DuplicateResource, ResourceNotRegistered


@dataclass(frozen=True, slots=True)
class ResourceRegistration:
    name: str
    resolver: ResolverLike
    attributes: AttributesResolverLike


class ResourceRegistry:
    def __init__(self) -> None:
        self._resources: dict[str, ResourceRegistration] = {}

    def register(
        self,
        name: str,
        *,
        resolver: ResolverLike,
        attributes: AttributesResolverLike,
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
