from collections.abc import Callable
from typing import Any, Protocol, TypeAlias, TypeVar

from pydantic import BaseModel, Field

TResource_co = TypeVar("TResource_co", covariant=True)
TResource_contra = TypeVar("TResource_contra", contravariant=True)


class ResourceAttributes(BaseModel):
    owner_id: str | None = None
    tenant_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ResourceResolver(Protocol[TResource_co]):
    """Class-based resource resolver: loads one object by its id."""

    async def resolve(self, resource_id: str) -> TResource_co | None: ...


class ResourceAttributesResolver(Protocol[TResource_contra]):
    """Class-based attributes resolver: maps a loaded object to its attributes."""

    async def resolve(self, resource: TResource_contra) -> ResourceAttributes: ...


# A resolver is either one of the protocols above or a function. Function
# signatures stay open because the integration layer lets FastAPI inject the
# parameters the guard does not bind, so they cannot be spelled out here.
ResolverLike: TypeAlias = ResourceResolver[Any] | Callable[..., Any]
AttributesResolverLike: TypeAlias = ResourceAttributesResolver[Any] | Callable[..., Any]
