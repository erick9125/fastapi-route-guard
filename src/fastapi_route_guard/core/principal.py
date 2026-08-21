from typing import Any

from pydantic import BaseModel, Field


class AuthorizationPrincipal(BaseModel):
    id: str
    roles: set[str] = Field(default_factory=set)
    scopes: set[str] = Field(default_factory=set)
    tenant_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
