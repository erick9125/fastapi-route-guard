from uuid import UUID

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from fastapi_route_guard import (
    AuthorizationPrincipal,
    ResourceAttributes,
    RouteGuard,
)

DOC_UUID = UUID("11111111-1111-1111-1111-111111111111")


async def _principal() -> AuthorizationPrincipal:
    return AuthorizationPrincipal(
        id="user-1", scopes={"doc:read"}, tenant_id="tenant-a"
    )


async def _attributes(resource: dict[str, str]) -> ResourceAttributes:
    return ResourceAttributes(owner_id="user-1", tenant_id="tenant-a")


def _app(guard: RouteGuard, path: str = "/docs/{doc_id}") -> FastAPI:
    app = FastAPI()

    @app.get(path)
    async def read_doc(
        doc: dict[str, str] = Depends(
            guard.protect_resource(
                "doc",
                id_param=path.strip("/").split("{")[1].rstrip("}"),
                scopes={"doc:read"},
                tenant=True,
            )
        ),
    ) -> dict[str, str]:
        return doc

    return app


async def test_int_id_reaches_the_resolver_as_an_int() -> None:
    """Starlette hands path values over as strings; the resolver asked for an int."""
    seen: list[object] = []

    async def resolve_doc(doc_id: int) -> dict[str, str]:
        seen.append(doc_id)
        return {"id": str(doc_id)}

    guard = RouteGuard(principal=_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=_attributes)

    transport = ASGITransport(app=_app(guard))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/42")

    assert response.status_code == 200
    assert seen == [42]


async def test_uuid_id_reaches_the_resolver_as_a_uuid() -> None:
    seen: list[object] = []

    async def resolve_doc(doc_id: UUID) -> dict[str, str]:
        seen.append(doc_id)
        return {"id": str(doc_id)}

    guard = RouteGuard(principal=_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=_attributes)

    transport = ASGITransport(app=_app(guard))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/docs/{DOC_UUID}")

    assert response.status_code == 200
    assert seen == [DOC_UUID]


async def test_optional_annotation_is_unwrapped() -> None:
    seen: list[object] = []

    async def resolve_doc(doc_id: int | None) -> dict[str, str]:
        seen.append(doc_id)
        return {"id": str(doc_id)}

    guard = RouteGuard(principal=_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=_attributes)

    transport = ASGITransport(app=_app(guard))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/7")

    assert response.status_code == 200
    assert seen == [7]


async def test_unparsable_id_is_denied_without_calling_the_resolver() -> None:
    """An id that cannot be an int cannot name a resource: deny, do not raise."""
    calls: list[object] = []

    async def resolve_doc(doc_id: int) -> dict[str, str]:
        calls.append(doc_id)
        return {"id": str(doc_id)}

    guard = RouteGuard(principal=_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=_attributes)

    transport = ASGITransport(app=_app(guard))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/not-a-number")

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}
    assert calls == []


async def test_unannotated_id_stays_a_string() -> None:
    seen: list[object] = []

    async def resolve_doc(doc_id) -> dict[str, str]:  # type: ignore[no-untyped-def]
        seen.append(doc_id)
        return {"id": str(doc_id)}

    guard = RouteGuard(principal=_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=_attributes)

    transport = ASGITransport(app=_app(guard))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/abc")

    assert response.status_code == 200
    assert seen == ["abc"]


async def test_a_path_param_named_request_does_not_shadow_the_asgi_request() -> None:
    """The id binding must not steal the parameter that wants the request."""
    seen: list[object] = []

    async def resolve_doc(resource_id: str, request: Request) -> dict[str, str]:
        seen.append((resource_id, request.url.path))
        return {"id": resource_id}

    guard = RouteGuard(principal=_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=_attributes)

    transport = ASGITransport(app=_app(guard, "/docs/{request}"))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/doc-1")

    assert response.status_code == 200
    assert seen == [("doc-1", "/docs/doc-1")]


async def test_attributes_resolver_takes_the_resource_by_name_not_by_position() -> None:
    """A named `resource` parameter wins over its position in the signature."""

    async def resolve_doc(doc_id: str) -> dict[str, str]:
        return {"id": doc_id}

    async def attributes(doc_id: str, resource: dict[str, str]) -> ResourceAttributes:
        assert resource == {"id": doc_id}
        return ResourceAttributes(owner_id="user-1", tenant_id="tenant-a")

    guard = RouteGuard(principal=_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=attributes)

    transport = ASGITransport(app=_app(guard))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/doc-1")

    assert response.status_code == 200
    assert response.json() == {"id": "doc-1"}
