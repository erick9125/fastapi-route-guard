from fastapi_route_guard import (
    AuthorizationContext,
    PolicyHandlerNotFound,
    RoutePolicy,
    ViolationCode,
    evaluate_policy,
    make_principal,
)
from fastapi_route_guard.core.resource import ResourceAttributes


class _Allow:
    name = "always.allow"

    async def evaluate(self, context: AuthorizationContext) -> bool:
        return True


class _Deny:
    name = "always.deny"

    async def evaluate(self, context: AuthorizationContext) -> bool:
        return False


class _Boom:
    name = "always.boom"

    async def evaluate(self, context: AuthorizationContext) -> bool:
        raise RuntimeError("handler failed")


async def test_custom_handler_true_allows() -> None:
    result = await evaluate_policy(
        policy=RoutePolicy(handlers=("always.allow",)),
        principal=make_principal(),
        handlers=[_Allow()],
    )
    assert result.allowed is True


async def test_custom_handler_false_denies() -> None:
    result = await evaluate_policy(
        policy=RoutePolicy(handlers=("always.deny",)),
        principal=make_principal(),
        handlers=[_Deny()],
    )
    assert result.allowed is False
    assert result.violations[0].code is ViolationCode.CUSTOM_POLICY_DENIED


async def test_missing_handler_fails_closed() -> None:
    try:
        await evaluate_policy(
            policy=RoutePolicy(handlers=("invoice.can_approve",)),
            principal=make_principal(),
        )
    except PolicyHandlerNotFound as exc:
        assert exc.name == "invoice.can_approve"
    else:
        raise AssertionError("missing handlers must not be treated as allow")


async def test_handler_exception_is_not_rewritten_to_allow() -> None:
    try:
        await evaluate_policy(
            policy=RoutePolicy(handlers=("always.boom",)),
            principal=make_principal(),
            handlers=[_Boom()],
        )
    except RuntimeError as exc:
        assert str(exc) == "handler failed"
    else:
        raise AssertionError("handler exceptions must not become allow")


async def test_resource_none_is_denied() -> None:
    result = await evaluate_policy(
        policy=RoutePolicy(resource="invoice", tenant=True),
        principal=make_principal(tenant_id="tenant-a"),
        resource=None,
        attributes=ResourceAttributes(tenant_id="tenant-a"),
    )
    assert result.allowed is False
    assert result.violations[0].code is ViolationCode.RESOURCE_NOT_FOUND
