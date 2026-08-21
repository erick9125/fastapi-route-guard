from fastapi_route_guard.core.principal import AuthorizationPrincipal
from fastapi_route_guard.core.resource import ResourceAttributes


class TenantEvaluator:
    def evaluate(
        self,
        principal: AuthorizationPrincipal,
        attributes: ResourceAttributes,
    ) -> bool:
        return (
            principal.tenant_id is not None
            and attributes.tenant_id is not None
            and principal.tenant_id == attributes.tenant_id
        )
