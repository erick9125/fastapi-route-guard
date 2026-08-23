from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from tests.fixtures.invoices import INVOICE_A, USER_A
from tests.fixtures.invoices_app import InvoiceStore, create_invoices_app

from fastapi_route_guard import (
    AuthorizationPrincipal,
    DuplicateResource,
    InvalidPrincipal,
    ResourceNotRegistered,
    ResourceRegistry,
    RouteGuard,
)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_invoices_app(InvoiceStore())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as instance:
        yield instance


async def test_missing_resource_is_403_not_404(client: AsyncClient) -> None:
    response = await client.get("/invoices/does-not-exist", headers={"x-user": USER_A})
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


async def test_forbidden_body_does_not_leak_authorization_context(
    client: AsyncClient,
) -> None:
    response = await client.get("/invoices/invoice-b", headers={"x-user": USER_A})
    body = response.text.lower()
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}
    for leaked in (
        "tenant",
        "owner",
        "mismatch",
        "unauthenticated",
        "missing_role",
        "missing_scope",
        "resource_not_found",
        "invoice-b",
        "tenant-b",
        "user-b",
    ):
        assert leaked not in body


async def test_denied_claims_do_not_load_the_resource() -> None:
    store = InvoiceStore()
    app = create_invoices_app(store)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/invoices/{INVOICE_A.id}",
            headers={"x-user": "admin-a"},
            params={"amount": 1},
        )
    assert response.status_code == 403
    assert store.find_by_id_calls == 0


async def test_duplicate_resource_registration_fails_closed() -> None:
    registry = ResourceRegistry()

    async def resolver(resource_id: str) -> None:
        return None

    async def attributes(resource: object) -> None:
        return None

    registry.register("invoice", resolver=resolver, attributes=attributes)
    try:
        registry.register("invoice", resolver=resolver, attributes=attributes)
    except DuplicateResource as exc:
        assert exc.name == "invoice"
    else:
        raise AssertionError("duplicate resources must not overwrite silently")


async def test_unknown_resource_type_fails_closed_at_wiring_time() -> None:
    """An unregistered resource must not survive until the first request.

    The guard reads the resolver signatures when the route is declared, so a
    typo in a resource name breaks at import time instead of returning a 500
    the first time someone hits that endpoint.
    """

    async def principal() -> AuthorizationPrincipal:
        return AuthorizationPrincipal(id="user-1", scopes={"invoice:read"})

    guard = RouteGuard(principal=principal)

    with pytest.raises(ResourceNotRegistered) as exc_info:
        guard.protect_resource(
            "ghost",
            id_param="invoice_id",
            scopes={"invoice:read"},
            tenant=True,
        )
    assert exc_info.value.name == "ghost"


async def test_unmapped_principal_is_a_named_configuration_fault() -> None:
    """A principal dependency that forgets to map the user must say so.

    FastAPI does not validate what a dependency returns, so an application
    user object used to reach the evaluators and fail there with an anonymous
    `AttributeError`.
    """

    @dataclass
    class User:
        id: str

    async def current_principal() -> User:
        return User(id="user-1")

    guard = RouteGuard(principal=current_principal)
    app = FastAPI()

    @app.get("/ping")
    async def ping(
        _: None = Depends(guard.protect(scopes={"invoice:read"})),
    ) -> dict[str, str]:
        return {"status": "ok"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with pytest.raises(InvalidPrincipal) as exc_info:
            await client.get("/ping")

    assert exc_info.value.dependency == "current_principal"
    assert exc_info.value.received == "User"


async def test_unmapped_principal_is_reported_on_resource_routes_too() -> None:
    @dataclass
    class User:
        id: str

    async def current_principal() -> User:
        return User(id="user-a")

    async def resolve_invoice(invoice_id: str) -> object:
        raise AssertionError("the resolver must not run with an invalid principal")

    async def invoice_attributes(resource: object) -> object:
        raise AssertionError("attributes must not run with an invalid principal")

    guard = RouteGuard(principal=current_principal)
    guard.add_resource(
        "invoice",
        resolver=resolve_invoice,
        attributes=invoice_attributes,
    )
    app = FastAPI()

    @app.get("/invoices/{invoice_id}")
    async def read_invoice(
        invoice: object = Depends(
            guard.protect_resource(
                "invoice",
                id_param="invoice_id",
                scopes={"invoice:read"},
                tenant=True,
            )
        ),
    ) -> object:
        return invoice

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with pytest.raises(InvalidPrincipal):
            await client.get("/invoices/invoice-a")
