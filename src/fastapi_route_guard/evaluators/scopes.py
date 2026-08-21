from fastapi_route_guard.core.principal import AuthorizationPrincipal


class ScopeEvaluator:
    def evaluate(
        self,
        required: frozenset[str],
        principal: AuthorizationPrincipal,
    ) -> bool:
        return required.issubset(principal.scopes)
