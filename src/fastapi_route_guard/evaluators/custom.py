from typing import Protocol

from fastapi_route_guard.core.models import AuthorizationContext


class PolicyHandler(Protocol):
    name: str

    async def evaluate(self, context: AuthorizationContext) -> bool: ...
