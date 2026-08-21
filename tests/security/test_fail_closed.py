from collections.abc import AsyncIterator

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from tests.fixtures.invoices import INVOICE_A, USER_A
from tests.fixtures.invoices_app import InvoiceStore, create_invoices_app

from fastapi_route_guard import (
    AuthorizationPrincipal,
    DuplicateResource,
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


async def test_unknown_resource_type_fails_closed_on_request() -> None:
    async def principal() -> AuthorizationPrincipal:
        return AuthorizationPrincipal(id="user-1", scopes={"invoice:read"})

    guard = RouteGuard(principal=principal)
    app = FastAPI()

    @app.get("/ghost/{invoice_id}")
    async def ghost(
        item: object = Depends(
            guard.protect_resource(
                "ghost",
                id_param="invoice_id",
                scopes={"invoice:read"},
                tenant=True,
            )
        ),
    ) -> object:
        return item

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with pytest.raises(ResourceNotRegistered):
            await client.get("/ghost/invoice-a")
