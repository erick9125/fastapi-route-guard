from fastapi_route_guard import (
    OwnershipEvaluator,
    ResourceAttributes,
    TenantEvaluator,
    make_principal,
)


def test_matching_tenant_allows() -> None:
    evaluator = TenantEvaluator()
    principal = make_principal(tenant_id="tenant-a")
    attributes = ResourceAttributes(tenant_id="tenant-a")
    assert evaluator.evaluate(principal, attributes) is True


def test_mismatched_tenant_is_denied() -> None:
    evaluator = TenantEvaluator()
    principal = make_principal(tenant_id="tenant-a")
    attributes = ResourceAttributes(tenant_id="tenant-b")
    assert evaluator.evaluate(principal, attributes) is False


def test_missing_tenant_ids_are_denied() -> None:
    evaluator = TenantEvaluator()
    principal = make_principal(tenant_id=None)
    attributes = ResourceAttributes(tenant_id="tenant-a")
    assert evaluator.evaluate(principal, attributes) is False


def test_matching_owner_allows() -> None:
    evaluator = OwnershipEvaluator()
    principal = make_principal(id="user-1")
    attributes = ResourceAttributes(owner_id="user-1")
    assert evaluator.evaluate(principal, attributes) is True


def test_mismatched_owner_is_denied() -> None:
    evaluator = OwnershipEvaluator()
    principal = make_principal(id="user-1")
    attributes = ResourceAttributes(owner_id="user-2")
    assert evaluator.evaluate(principal, attributes) is False


def test_missing_owner_id_is_denied() -> None:
    evaluator = OwnershipEvaluator()
    principal = make_principal(id="user-1")
    attributes = ResourceAttributes(owner_id=None)
    assert evaluator.evaluate(principal, attributes) is False
