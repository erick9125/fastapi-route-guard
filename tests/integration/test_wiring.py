import pytest
from fastapi import Depends, FastAPI

from fastapi_route_guard import (
    AuthorizationContext,
    AuthorizationPrincipal,
    IdParameterNotInPath,
    PolicyHandlerNotFound,
    ResourceAttributes,
    RouteGuard,
)


async def _principal() -> AuthorizationPrincipal:
    return AuthorizationPrincipal(
        id="user-1", scopes={"doc:read"}, tenant_id="tenant-a"
    )


async def _resolve_doc(doc_id: str) -> dict[str, str]:
    return {"id": doc_id}


async def _doc_attributes(resource: dict[str, str]) -> ResourceAttributes:
    return ResourceAttributes(owner_id="user-1", tenant_id="tenant-a")


def _guard() -> RouteGuard:
    guard = RouteGuard(principal=_principal)
    guard.add_resource("doc", resolver=_resolve_doc, attributes=_doc_attributes)
    return guard


def test_unknown_handler_name_fails_at_wiring_time() -> None:
    """A handler name is resolved when the route is declared, not when it is hit."""
    guard = _guard()

    with pytest.raises(PolicyHandlerNotFound) as exc_info:
        guard.protect_resource(
            "doc",
            id_param="doc_id",
            handler_names=("doc.can_read",),
        )
    assert exc_info.value.name == "doc.can_read"


def test_unknown_handler_name_fails_on_claims_only_routes_too() -> None:
    guard = _guard()

    with pytest.raises(PolicyHandlerNotFound):
        guard.protect(handler_names=("doc.can_read",))


def test_registered_handler_name_wires_cleanly() -> None:
    class _CanRead:
        name = "doc.can_read"

        async def evaluate(self, context: AuthorizationContext) -> bool:
            return True

    guard = _guard()
    guard.add_policy_handler(_CanRead())

    assert guard.protect_resource(
        "doc",
        id_param="doc_id",
        handler_names=("doc.can_read",),
    )


def test_validate_rejects_an_id_param_the_route_does_not_declare() -> None:
    """A mistyped `id_param` must break at startup, not on the first request."""
    guard = _guard()
    app = FastAPI()

    @app.get("/docs/{doc_id}")
    async def read_doc(
        doc: dict[str, str] = Depends(
            guard.protect_resource(
                "doc",
                id_param="document_id",
                scopes={"doc:read"},
                tenant=True,
            )
        ),
    ) -> dict[str, str]:
        return doc

    with pytest.raises(IdParameterNotInPath) as exc_info:
        guard.validate(app)

    assert exc_info.value.resource == "doc"
    assert exc_info.value.id_param == "document_id"
    assert exc_info.value.path == "/docs/{doc_id}"


def test_validate_accepts_a_correctly_wired_app() -> None:
    guard = _guard()
    app = FastAPI()

    @app.get("/docs/{doc_id}")
    async def read_doc(
        doc: dict[str, str] = Depends(
            guard.protect_resource(
                "doc",
                id_param="doc_id",
                scopes={"doc:read"},
                tenant=True,
            )
        ),
    ) -> dict[str, str]:
        return doc

    guard.validate(app)


def test_validate_ignores_routes_that_do_not_use_the_guard() -> None:
    guard = _guard()
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    guard.validate(app)
