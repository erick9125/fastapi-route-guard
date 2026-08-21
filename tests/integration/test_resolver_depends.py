from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

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
