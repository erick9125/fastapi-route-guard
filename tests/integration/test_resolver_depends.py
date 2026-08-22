from collections.abc import AsyncIterator, Iterator

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from tests.fixtures.invoices import INVOICE_A
from tests.fixtures.invoices_app import InvoiceStore, create_invoices_app

from fastapi_route_guard import (
    AuthorizationPrincipal,
    ResourceAttributes,
    RouteGuard,
)


class _Repo:
    def __init__(self) -> None:
        self.calls = 0

    async def find_by_id(self, resource_id: str) -> dict[str, str] | None:
        self.calls += 1
        if resource_id != "doc-1":
            return None
        return {"id": "doc-1", "owner_id": "user-1", "tenant_id": "tenant-a"}


async def test_resolver_can_use_fastapi_depends() -> None:
    repo = _Repo()

    def get_repo() -> _Repo:
        return repo

    async def current_principal() -> AuthorizationPrincipal:
        return AuthorizationPrincipal(
            id="user-1",
            scopes={"doc:read"},
            tenant_id="tenant-a",
        )

    async def resolve_doc(
        doc_id: str,
        repository: _Repo = Depends(get_repo),
    ) -> dict[str, str] | None:
        return await repository.find_by_id(doc_id)

    async def doc_attributes(resource: dict[str, str]) -> ResourceAttributes:
        return ResourceAttributes(
            owner_id=resource["owner_id"],
            tenant_id=resource["tenant_id"],
        )

    guard = RouteGuard(principal=current_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=doc_attributes)

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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/doc-1")

    assert response.status_code == 200
    assert response.json()["id"] == "doc-1"
    assert repo.calls == 1


async def test_resolver_yield_dependency_is_entered_and_closed() -> None:
    """A `yield` dependency must reach the resolver as its value.

    This is the most common shape in FastAPI (a database session). Handing the
    resolver an un-started generator used to succeed silently with a 200, and
    the teardown never ran.
    """
    events: list[str] = []

    async def get_session() -> AsyncIterator[str]:
        events.append("open")
        yield "session"
        events.append("close")

    async def current_principal() -> AuthorizationPrincipal:
        return AuthorizationPrincipal(
            id="user-1",
            scopes={"doc:read"},
            tenant_id="tenant-a",
        )

    async def resolve_doc(
        doc_id: str,
        session: str = Depends(get_session),
    ) -> dict[str, str]:
        return {"id": doc_id, "session": session}

    async def doc_attributes(resource: dict[str, str]) -> ResourceAttributes:
        return ResourceAttributes(owner_id="user-1", tenant_id="tenant-a")

    guard = RouteGuard(principal=current_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=doc_attributes)
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/doc-1")

    assert response.status_code == 200
    assert response.json()["session"] == "session"
    assert events == ["open", "close"]


async def test_resolver_sync_yield_dependency_is_entered_and_closed() -> None:
    events: list[str] = []

    def get_session() -> Iterator[str]:
        events.append("open")
        yield "session"
        events.append("close")

    async def current_principal() -> AuthorizationPrincipal:
        return AuthorizationPrincipal(
            id="user-1",
            scopes={"doc:read"},
            tenant_id="tenant-a",
        )

    async def resolve_doc(
        doc_id: str,
        session: str = Depends(get_session),
    ) -> dict[str, str]:
        return {"id": doc_id, "session": session}

    async def doc_attributes(resource: dict[str, str]) -> ResourceAttributes:
        return ResourceAttributes(owner_id="user-1", tenant_id="tenant-a")

    guard = RouteGuard(principal=current_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=doc_attributes)
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/doc-1")

    assert response.status_code == 200
    assert response.json()["session"] == "session"
    assert events == ["open", "close"]


class _FakeRepo(_Repo):
    async def find_by_id(self, resource_id: str) -> dict[str, str] | None:
        self.calls += 1
        return {"id": resource_id, "owner_id": "user-1", "tenant_id": "tenant-a"}


async def test_resolver_honours_dependency_overrides() -> None:
    """dependency_overrides must reach the resolver the guard runs.

    Otherwise a test substitutes the repository for the route while the guard
    keeps authorizing against the real one.
    """

    def get_repo() -> _Repo:
        return _Repo()

    async def current_principal() -> AuthorizationPrincipal:
        return AuthorizationPrincipal(
            id="user-1",
            scopes={"doc:read"},
            tenant_id="tenant-a",
        )

    async def resolve_doc(
        doc_id: str,
        repository: _Repo = Depends(get_repo),
    ) -> dict[str, str] | None:
        return await repository.find_by_id(doc_id)

    async def doc_attributes(resource: dict[str, str]) -> ResourceAttributes:
        return ResourceAttributes(
            owner_id=resource["owner_id"],
            tenant_id=resource["tenant_id"],
        )

    guard = RouteGuard(principal=current_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=doc_attributes)
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

    fake = _FakeRepo()
    app.dependency_overrides[get_repo] = lambda: fake

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/anything")

    assert response.status_code == 200
    assert response.json()["id"] == "anything"
    assert fake.calls == 1


async def test_dependency_shared_with_the_route_is_resolved_once() -> None:
    """The per-request dependency cache must cover the guard's resolver.

    A repository shared by the route and the resolver used to be constructed
    twice per request: two sessions, two connections, duplicated side effects.
    """
    built: list[int] = []

    def get_repo() -> _Repo:
        built.append(1)
        return _FakeRepo()

    async def current_principal() -> AuthorizationPrincipal:
        return AuthorizationPrincipal(
            id="user-1",
            scopes={"doc:read"},
            tenant_id="tenant-a",
        )

    async def resolve_doc(
        doc_id: str,
        repository: _Repo = Depends(get_repo),
    ) -> dict[str, str] | None:
        return await repository.find_by_id(doc_id)

    async def doc_attributes(resource: dict[str, str]) -> ResourceAttributes:
        return ResourceAttributes(
            owner_id=resource["owner_id"],
            tenant_id=resource["tenant_id"],
        )

    guard = RouteGuard(principal=current_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=doc_attributes)
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
        repository: _Repo = Depends(get_repo),
    ) -> dict[str, str]:
        return doc

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/doc-1")

    assert response.status_code == 200
    assert built == [1]


async def test_denied_claims_still_skip_the_resolver_body() -> None:
    """The claims-first guarantee survives delegating injection to FastAPI."""
    queried: list[str] = []

    async def get_session() -> AsyncIterator[str]:
        yield "session"

    async def current_principal() -> AuthorizationPrincipal:
        return AuthorizationPrincipal(id="user-1", scopes=set(), tenant_id="tenant-a")

    async def resolve_doc(
        doc_id: str,
        session: str = Depends(get_session),
    ) -> dict[str, str]:
        queried.append(doc_id)
        return {"id": doc_id}

    async def doc_attributes(resource: dict[str, str]) -> ResourceAttributes:
        return ResourceAttributes(owner_id="user-1", tenant_id="tenant-a")

    guard = RouteGuard(principal=current_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=doc_attributes)
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/doc-1")

    assert response.status_code == 403
    assert queried == []


async def test_resource_is_still_loaded_once_per_request() -> None:
    store = InvoiceStore()
    app = create_invoices_app(store)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/invoices/{INVOICE_A.id}", headers={"x-user": "user-a"}
        )

    assert response.status_code == 200
    assert store.find_by_id_calls == 1
