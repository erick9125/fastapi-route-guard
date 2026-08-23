from fastapi_route_guard import (
    ResourceAttributes,
    RoutePolicy,
    ViolationCode,
    evaluate_policy,
    make_principal,
)
from fastapi_route_guard.core.models import AuthorizationContext
from fastapi_route_guard.evaluators.evaluator import PolicyEvaluator


class _Deny:
    name = "invoice.deny"

    async def evaluate(self, context: AuthorizationContext) -> bool:
        return False


async def test_collect_all_includes_resource_violations() -> None:
    result = await evaluate_policy(
        policy=RoutePolicy(
            resource="invoice",
            tenant=True,
            ownership=True,
            handlers=("invoice.deny",),
        ),
        principal=make_principal(id="user-1", tenant_id="tenant-a"),
        resource=object(),
        attributes=ResourceAttributes(owner_id="user-2", tenant_id="tenant-b"),
        handlers=[_Deny()],
        collect_all=True,
    )
    codes = {item.code for item in result.violations}
    assert codes == {
        ViolationCode.TENANT_MISMATCH,
        ViolationCode.OWNERSHIP_MISMATCH,
        ViolationCode.CUSTOM_POLICY_DENIED,
    }


async def test_collect_all_does_not_run_handlers_for_a_denied_caller() -> None:
    """Aggregating violations must never buy them with I/O.

    Custom handlers are documented as doing database work, so a caller already
    denied on claims must not reach them just because `collect_all` would like
    a fuller report.
    """
    invocations: list[str] = []

    class _Expensive:
        name = "invoice.expensive"

        async def evaluate(self, context: AuthorizationContext) -> bool:
            invocations.append("called")
            return True

    result = await evaluate_policy(
        policy=RoutePolicy(
            scopes=frozenset({"invoice:read"}),
            handlers=("invoice.expensive",),
        ),
        principal=make_principal(scopes=set()),
        handlers=[_Expensive()],
        collect_all=True,
    )

    assert result.allowed is False
    assert invocations == []


async def test_collect_all_reports_unauthenticated_once() -> None:
    result = await evaluate_policy(
        policy=RoutePolicy(resource="invoice", tenant=True),
        principal=None,
        collect_all=True,
    )

    codes = [item.code for item in result.violations]
    assert codes == [ViolationCode.UNAUTHENTICATED]


async def test_unauthenticated_resource_phase_is_denied() -> None:
    evaluator = PolicyEvaluator()
    result = await evaluator.evaluate_resource(
        RoutePolicy(resource="invoice", tenant=True),
        AuthorizationContext(
            principal=None,
            resource=object(),
            resource_type="invoice",
            action="read",
            attributes=ResourceAttributes(tenant_id="tenant-a"),
        ),
    )
    assert result.violations[0].code is ViolationCode.UNAUTHENTICATED
