from fastapi_route_guard import evaluate_policy, make_principal
from fastapi_route_guard.core.policy import RoutePolicy
from fastapi_route_guard.core.resource import ResourceAttributes


async def test_evaluate_policy_helper_allows_matching_principal() -> None:
    result = await evaluate_policy(
        policy=RoutePolicy(
            resource="invoice",
            roles=frozenset({"manager"}),
            scopes=frozenset({"invoice:read"}),
            tenant=True,
            ownership=True,
        ),
        principal=make_principal(
            id="user-1",
            roles={"manager"},
            scopes={"invoice:read"},
            tenant_id="tenant-a",
        ),
        resource=object(),
        attributes=ResourceAttributes(owner_id="user-1", tenant_id="tenant-a"),
    )
    assert result.allowed is True
