from fastapi_route_guard.core.principal import AuthorizationPrincipal


class RoleEvaluator:
    def evaluate(
        self,
        required: frozenset[str],
        principal: AuthorizationPrincipal,
    ) -> bool:
        if not required:
            return True
        return bool(required.intersection(principal.roles))
