from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from tests.fixtures.invoices import (
    ADMIN_A,
    INVOICE_A,
    INVOICE_B,
    INVOICE_C,
    MANAGER_A,
    USER_A,
    USER_B,
)
from tests.fixtures.invoices_app import InvoiceStore, create_invoices_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_invoices_app(InvoiceStore())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as instance:
        yield instance


async def test_user_can_read_invoice_in_own_tenant(client: AsyncClient) -> None:
    response = await client.get(f"/invoices/{INVOICE_A.id}", headers={"x-user": USER_A})
    assert response.status_code == 200


async def test_id_manipulation_across_tenants_is_denied(client: AsyncClient) -> None:
    allowed = await client.get(f"/invoices/{INVOICE_A.id}", headers={"x-user": USER_A})
    swapped = await client.get(f"/invoices/{INVOICE_B.id}", headers={"x-user": USER_A})
    assert allowed.status_code == 200
    assert swapped.status_code == 403
    assert swapped.json() == {"detail": "Forbidden"}


async def test_user_b_cannot_read_tenant_a_invoice(client: AsyncClient) -> None:
    response = await client.get(f"/invoices/{INVOICE_A.id}", headers={"x-user": USER_B})
    assert response.status_code == 403


async def test_same_tenant_wrong_owner_is_denied_on_update(
    client: AsyncClient,
) -> None:
    response = await client.patch(
        f"/invoices/{INVOICE_C.id}",
        headers={"x-user": USER_A},
        params={"amount": 9},
    )
    assert response.status_code == 403


async def test_owner_can_update_own_invoice(client: AsyncClient) -> None:
    response = await client.patch(
        f"/invoices/{INVOICE_A.id}",
        headers={"x-user": USER_A},
        params={"amount": 9},
    )
    assert response.status_code == 200


async def test_approve_denied_without_role_or_when_not_pending(
    client: AsyncClient,
) -> None:
    as_user = await client.post(
        f"/invoices/{INVOICE_A.id}/approve",
        headers={"x-user": USER_A},
    )
    as_manager_pending = await client.post(
        f"/invoices/{INVOICE_A.id}/approve",
        headers={"x-user": MANAGER_A},
    )
    as_manager_already_approved = await client.post(
        "/invoices/invoice-approved/approve",
        headers={"x-user": MANAGER_A},
    )
    assert as_user.status_code == 403
    assert as_manager_pending.status_code == 200
    assert as_manager_already_approved.status_code == 403


async def test_delete_requires_admin_and_tenant(client: AsyncClient) -> None:
    as_manager = await client.delete(
        f"/invoices/{INVOICE_A.id}",
        headers={"x-user": MANAGER_A},
    )
    as_admin_other_tenant = await client.delete(
        f"/invoices/{INVOICE_B.id}",
        headers={"x-user": ADMIN_A},
    )
    as_admin = await client.delete(
        f"/invoices/{INVOICE_C.id}",
        headers={"x-user": ADMIN_A},
    )
    assert as_manager.status_code == 403
    assert as_admin_other_tenant.status_code == 403
    assert as_admin.status_code == 200
