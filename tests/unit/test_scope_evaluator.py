from fastapi_route_guard import ScopeEvaluator, test_principal


def test_all_required_scopes_allow() -> None:
    evaluator = ScopeEvaluator()
    principal = test_principal(scopes={"invoice:read", "invoice:export"})
    assert (
        evaluator.evaluate(frozenset({"invoice:read", "invoice:export"}), principal)
        is True
    )


def test_missing_scope_is_denied() -> None:
    evaluator = ScopeEvaluator()
    principal = test_principal(scopes={"invoice:read"})
    assert (
        evaluator.evaluate(frozenset({"invoice:read", "invoice:export"}), principal)
        is False
    )


def test_empty_required_scopes_allow() -> None:
    evaluator = ScopeEvaluator()
    principal = test_principal(scopes=set())
    assert evaluator.evaluate(frozenset(), principal) is True
