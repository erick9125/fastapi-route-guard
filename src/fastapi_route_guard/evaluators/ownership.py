from fastapi_route_guard.core.principal import AuthorizationPrincipal
from fastapi_route_guard.core.resource import ResourceAttributes


class OwnershipEvaluator:
    def evaluate(
        self,
        principal: AuthorizationPrincipal,
        attributes: ResourceAttributes,
    ) -> bool:
        return attributes.owner_id is not None and attributes.owner_id == principal.id
