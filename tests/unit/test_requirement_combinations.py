from fastapi_route_guard import (
    ResourceAttributes,
    RoutePolicy,
    ViolationCode,
    evaluate_policy,
    make_principal,
)


async def test_roles_scopes_tenant_and_handler_must_all_pass() -> None:
    class _Approve:
        name = "invoice.can_approve"

        async def evaluate(self, context: object) -> bool:
            return True

    policy = RoutePolicy(
        resource="invoice",
        roles=frozenset({"manager"}),
        scopes=frozenset({"invoice:approve"}),
        tenant=True,
        handlers=("invoice.can_approve",),
    )
    principal = make_principal(
        roles={"manager"},
        scopes={"invoice:approve"},
        tenant_id="tenant-a",
    )
    result = await evaluate_policy(
        policy=policy,
        principal=principal,
        resource=object(),
        attributes=ResourceAttributes(tenant_id="tenant-a"),
        handlers=[_Approve()],
    )
    assert result.allowed is True


async def test_tenant_failure_denies_even_when_other_requirements_pass() -> None:
    class _Approve:
        name = "invoice.can_approve"

        async def evaluate(self, context: object) -> bool:
            return True

    result = await evaluate_policy(
        policy=RoutePolicy(
            resource="invoice",
            roles=frozenset({"manager"}),
            scopes=frozenset({"invoice:approve"}),
            tenant=True,
            handlers=("invoice.can_approve",),
        ),
        principal=make_principal(
            roles={"manager"},
            scopes={"invoice:approve"},
            tenant_id="tenant-a",
        ),
        resource=object(),
        attributes=ResourceAttributes(tenant_id="tenant-b"),
        handlers=[_Approve()],
    )
    assert result.allowed is False
    assert result.violations[0].code is ViolationCode.TENANT_MISMATCH
