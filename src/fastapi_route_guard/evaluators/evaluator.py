from fastapi_route_guard.core.models import AuthorizationContext
from fastapi_route_guard.core.policy import RoutePolicy
from fastapi_route_guard.core.principal import AuthorizationPrincipal
from fastapi_route_guard.core.result import AuthorizationResult, AuthorizationViolation
from fastapi_route_guard.core.violations import ViolationCode
from fastapi_route_guard.evaluators.custom import PolicyHandler
from fastapi_route_guard.evaluators.ownership import OwnershipEvaluator
from fastapi_route_guard.evaluators.roles import RoleEvaluator
from fastapi_route_guard.evaluators.scopes import ScopeEvaluator
from fastapi_route_guard.evaluators.tenant import TenantEvaluator
from fastapi_route_guard.registry.policies import PolicyRegistry


def _violation(code: ViolationCode, message: str) -> AuthorizationViolation:
    return AuthorizationViolation(code=code, message=message)


def _denied(*violations: AuthorizationViolation) -> AuthorizationResult:
    return AuthorizationResult(allowed=False, violations=violations)


def _allowed(
    violations: tuple[AuthorizationViolation, ...] = (),
) -> AuthorizationResult:
    if violations:
        return AuthorizationResult(allowed=False, violations=violations)
    return AuthorizationResult(allowed=True)


def _usable_principal(
    principal: AuthorizationPrincipal | None,
) -> AuthorizationPrincipal | None:
    if principal is None or not principal.id:
        return None
    return principal


class PolicyEvaluator:
    def __init__(
        self,
        role_evaluator: RoleEvaluator | None = None,
        scope_evaluator: ScopeEvaluator | None = None,
        ownership_evaluator: OwnershipEvaluator | None = None,
        tenant_evaluator: TenantEvaluator | None = None,
        registry: PolicyRegistry | None = None,
        *,
        collect_all: bool = False,
    ) -> None:
        self._role_evaluator = role_evaluator or RoleEvaluator()
        self._scope_evaluator = scope_evaluator or ScopeEvaluator()
        self._ownership_evaluator = ownership_evaluator or OwnershipEvaluator()
        self._tenant_evaluator = tenant_evaluator or TenantEvaluator()
        self._registry = registry or PolicyRegistry()
        self._collect_all = collect_all

    async def evaluate(
        self,
        policy: RoutePolicy,
        context: AuthorizationContext,
    ) -> AuthorizationResult:
        claims = self.evaluate_claims(policy, context)
        if not claims.allowed:
            # `collect_all` aggregates the violations of one phase, never at the
            # cost of running the next one: the resource phase reaches handlers
            # that hit a database, and a denied caller must not trigger them.
            return claims
        return await self.evaluate_resource(policy, context)

    def evaluate_claims(
        self,
        policy: RoutePolicy,
        context: AuthorizationContext,
    ) -> AuthorizationResult:
        principal = _usable_principal(context.principal)
        if principal is None:
            return _denied(
                _violation(
                    ViolationCode.UNAUTHENTICATED,
                    "An authenticated principal is required.",
                )
            )

        violations: list[AuthorizationViolation] = []

        if not self._role_evaluator.evaluate(policy.roles, principal):
            violation = _violation(
                ViolationCode.MISSING_ROLE,
                "Principal does not satisfy the required roles.",
            )
            if not self._collect_all:
                return _denied(violation)
            violations.append(violation)

        if not self._scope_evaluator.evaluate(policy.scopes, principal):
            violation = _violation(
                ViolationCode.MISSING_SCOPE,
                "Principal does not satisfy the required scopes.",
            )
            if not self._collect_all:
                return _denied(violation)
            violations.append(violation)

        return _allowed(tuple(violations))

    async def evaluate_resource(
        self,
        policy: RoutePolicy,
        context: AuthorizationContext,
    ) -> AuthorizationResult:
        principal = _usable_principal(context.principal)
        if principal is None:
            return _denied(
                _violation(
                    ViolationCode.UNAUTHENTICATED,
                    "An authenticated principal is required.",
                )
            )

        if policy.resource is not None and context.resource is None:
            return _denied(
                _violation(
                    ViolationCode.RESOURCE_NOT_FOUND,
                    "The requested resource is not available.",
                )
            )

        violations: list[AuthorizationViolation] = []

        if policy.tenant:
            attributes = context.attributes
            tenant_ok = attributes is not None and self._tenant_evaluator.evaluate(
                principal, attributes
            )
            if not tenant_ok:
                violation = _violation(
                    ViolationCode.TENANT_MISMATCH,
                    "Principal tenant does not match the resource tenant.",
                )
                if not self._collect_all:
                    return _denied(violation)
                violations.append(violation)

        if policy.ownership:
            attributes = context.attributes
            owner_ok = attributes is not None and self._ownership_evaluator.evaluate(
                principal, attributes
            )
            if not owner_ok:
                violation = _violation(
                    ViolationCode.OWNERSHIP_MISMATCH,
                    "Principal does not own the requested resource.",
                )
                if not self._collect_all:
                    return _denied(violation)
                violations.append(violation)

        for name in policy.handlers:
            handler: PolicyHandler = self._registry.get(name)
            allowed = await handler.evaluate(context)
            if not allowed:
                violation = _violation(
                    ViolationCode.CUSTOM_POLICY_DENIED,
                    f'Custom policy handler "{name}" denied the request.',
                )
                if not self._collect_all:
                    return _denied(violation)
                violations.append(violation)

        return _allowed(tuple(violations))
