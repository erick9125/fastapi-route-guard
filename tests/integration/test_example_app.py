"""The example app is documentation, so it has to keep working.

It is referenced from the README and shipped in the sdist, and it duplicates the
shape of the test fixture app on purpose: one is a readable reference, the other
is a rig with call counters. These tests keep the reference honest and catch the
two drifting apart.
"""

from collections.abc import AsyncIterator

import pytest
from examples.invoices_api.app import app as example_app
from httpx import ASGITransport, AsyncClient
from tests.fixtures.invoices_app import InvoiceStore, create_invoices_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=example_app)
    async with AsyncClient(transport=transport, base_url="http://test") as instance:
        yield instance


async def test_the_example_denies_id_manipulation_across_tenants(
    client: AsyncClient,
) -> None:
    own = await client.get("/invoices/invoice-a", headers={"x-user": "user-a"})
    swapped = await client.get("/invoices/invoice-b", headers={"x-user": "user-a"})

    assert own.status_code == 200
    assert swapped.status_code == 403
    assert swapped.json() == {"detail": "Forbidden"}


async def test_the_example_denies_the_wrong_owner_in_the_same_tenant(
    client: AsyncClient,
) -> None:
    response = await client.patch(
        "/invoices/invoice-c",
        headers={"x-user": "user-a"},
        params={"amount": 9},
    )

    assert response.status_code == 403


async def test_the_example_leaves_authentication_to_the_application(
    client: AsyncClient,
) -> None:
    response = await client.get("/invoices/invoice-a")

    assert response.status_code == 401


def test_the_example_and_the_fixture_app_expose_the_same_routes() -> None:
    fixture_app = create_invoices_app(InvoiceStore())

    def paths(app: object) -> set[tuple[str, frozenset[str]]]:
        return {
            (route.path, frozenset(route.methods or ()))
            for route in getattr(app, "routes", ())
            if getattr(route, "path", "").startswith("/invoices")
        }

    assert paths(example_app) == paths(fixture_app)
