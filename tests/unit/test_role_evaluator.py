from fastapi_route_guard import RoleEvaluator, make_principal


def test_admin_role_allows() -> None:
    evaluator = RoleEvaluator()
    principal = make_principal(roles={"admin"})
    assert evaluator.evaluate(frozenset({"admin"}), principal) is True


def test_user_without_role_is_denied() -> None:
    evaluator = RoleEvaluator()
    principal = make_principal(roles={"user"})
    assert evaluator.evaluate(frozenset({"admin"}), principal) is False


def test_roles_use_any_semantics() -> None:
    evaluator = RoleEvaluator()
    principal = make_principal(roles={"manager"})
    assert evaluator.evaluate(frozenset({"admin", "manager"}), principal) is True


def test_empty_required_roles_allow() -> None:
    evaluator = RoleEvaluator()
    principal = make_principal(roles=set())
    assert evaluator.evaluate(frozenset(), principal) is True
