from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, Field

TResource = TypeVar("TResource")
TResource_co = TypeVar("TResource_co", covariant=True)
TResource_contra = TypeVar("TResource_contra", contravariant=True)


class ResourceAttributes(BaseModel):
    owner_id: str | None = None
    tenant_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ResourceResolver(Protocol[TResource_co]):
    async def resolve(self, resource_id: str) -> TResource_co | None: ...


class ResourceAttributesResolver(Protocol[TResource_contra]):
    async def resolve(self, resource: TResource_contra) -> ResourceAttributes: ...
