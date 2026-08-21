from fastapi_route_guard import (
    ResourceAttributes,
    RoutePolicy,
    ViolationCode,
    evaluate_policy,
    test_principal,
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
        principal=test_principal(id="user-1", tenant_id="tenant-a"),
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
