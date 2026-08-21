from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from tests.fixtures.invoices import ADMIN_A, INVOICE_A, MANAGER_A, USER_A
from tests.fixtures.invoices_app import InvoiceStore, create_invoices_app

from fastapi_route_guard import MissingObjectCheck, RouteGuard


@pytest.fixture
def store() -> InvoiceStore:
    return InvoiceStore()


@pytest.fixture
async def client(store: InvoiceStore) -> AsyncIterator[AsyncClient]:
    app = create_invoices_app(store)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as instance:
        yield instance


async def test_read_invoice_returns_the_guard_loaded_resource(
    client: AsyncClient,
) -> None:
    response = await client.get(f"/invoices/{INVOICE_A.id}", headers={"x-user": USER_A})
    assert response.status_code == 200
    assert response.json()["id"] == INVOICE_A.id


async def test_resource_is_loaded_once_per_request(store: InvoiceStore) -> None:
    app = create_invoices_app(store)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/invoices/{INVOICE_A.id}", headers={"x-user": USER_A}
        )
    assert response.status_code == 200
    assert store.find_by_id_calls == 1


async def test_list_requires_role_and_scope(client: AsyncClient) -> None:
    denied = await client.get("/invoices", headers={"x-user": USER_A})
    allowed = await client.get("/invoices", headers={"x-user": MANAGER_A})
    admin = await client.get("/invoices", headers={"x-user": ADMIN_A})
    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert admin.status_code == 200


async def test_update_requires_ownership(client: AsyncClient) -> None:
    response = await client.patch(
        f"/invoices/{INVOICE_A.id}",
        headers={"x-user": USER_A},
        params={"amount": 50},
    )
    assert response.status_code == 200
    assert response.json()["amount"] == 50


async def test_approve_and_delete_endpoints(client: AsyncClient) -> None:
    approved = await client.post(
        f"/invoices/{INVOICE_A.id}/approve",
        headers={"x-user": MANAGER_A},
    )
    deleted = await client.delete(
        "/invoices/invoice-c",
        headers={"x-user": ADMIN_A},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert deleted.status_code == 200


async def test_missing_user_is_401_from_authentication(client: AsyncClient) -> None:
    response = await client.get(f"/invoices/{INVOICE_A.id}")
    assert response.status_code == 401


async def test_protect_resource_requires_an_object_check() -> None:
    async def principal() -> None:
        return None

    guard = RouteGuard(principal=principal)
    try:
        guard.protect_resource(
            "invoice",
            id_param="invoice_id",
            scopes={"invoice:read"},
        )
    except MissingObjectCheck as exc:
        assert exc.resource == "invoice"
    else:
        raise AssertionError("resource policies without object checks must fail closed")
