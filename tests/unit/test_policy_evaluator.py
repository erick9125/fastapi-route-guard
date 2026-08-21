from fastapi_route_guard import (
    DuplicatePolicyHandler,
    PolicyHandlerNotFound,
    PolicyRegistry,
    ResourceAttributes,
    RoutePolicy,
    ViolationCode,
    evaluate_policy,
    test_principal,
)
from fastapi_route_guard.core.models import AuthorizationContext


class _Named:
    def __init__(self, name: str) -> None:
        self.name = name

    async def evaluate(self, context: AuthorizationContext) -> bool:
        return True


async def test_unauthenticated_principal_is_denied() -> None:
    result = await evaluate_policy(
        policy=RoutePolicy(roles=frozenset({"admin"})),
        principal=None,
    )
    assert result.allowed is False
    assert result.violations[0].code is ViolationCode.UNAUTHENTICATED


async def test_empty_principal_id_is_denied() -> None:
    result = await evaluate_policy(
        policy=RoutePolicy(),
        principal=test_principal(id=""),
    )
    assert result.allowed is False
    assert result.violations[0].code is ViolationCode.UNAUTHENTICATED


async def test_fail_fast_stops_at_first_violation() -> None:
    result = await evaluate_policy(
        policy=RoutePolicy(
            roles=frozenset({"admin"}),
            scopes=frozenset({"invoice:read"}),
        ),
        principal=test_principal(roles={"user"}, scopes=set()),
    )
    assert result.allowed is False
    assert len(result.violations) == 1
    assert result.violations[0].code is ViolationCode.MISSING_ROLE


async def test_collect_all_gathers_claim_violations() -> None:
    result = await evaluate_policy(
        policy=RoutePolicy(
            roles=frozenset({"admin"}),
            scopes=frozenset({"invoice:read"}),
        ),
        principal=test_principal(roles={"user"}, scopes=set()),
        collect_all=True,
    )
    codes = {item.code for item in result.violations}
    assert codes == {ViolationCode.MISSING_ROLE, ViolationCode.MISSING_SCOPE}


async def test_missing_role_denies_before_resource_checks() -> None:
    result = await evaluate_policy(
        policy=RoutePolicy(
            resource="invoice",
            roles=frozenset({"admin"}),
            tenant=True,
        ),
        principal=test_principal(roles={"user"}, tenant_id="tenant-a"),
        resource=object(),
        attributes=ResourceAttributes(tenant_id="tenant-a"),
    )
    assert result.violations[0].code is ViolationCode.MISSING_ROLE


async def test_duplicate_handler_registration_fails_closed() -> None:
    registry = PolicyRegistry([_Named("dup")])
    try:
        registry.register(_Named("dup"))
    except DuplicatePolicyHandler as exc:
        assert exc.name == "dup"
    else:
        raise AssertionError("duplicate handlers must not overwrite silently")


async def test_registry_get_unknown_handler_fails_closed() -> None:
    registry = PolicyRegistry()
    try:
        registry.get("missing")
    except PolicyHandlerNotFound as exc:
        assert exc.name == "missing"
    else:
        raise AssertionError("unknown handlers must not allow")
