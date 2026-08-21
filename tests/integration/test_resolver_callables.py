from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from fastapi_route_guard import (
    AuthorizationPrincipal,
    MissingResourceId,
    ResourceAttributes,
    RouteGuard,
)
from fastapi_route_guard.fastapi.dependencies import callable_from, invoke_callable


class _Doc:
    def __init__(self, doc_id: str) -> None:
        self.id = doc_id
        self.owner_id = "user-1"
        self.tenant_id = "tenant-a"


class _Resolver:
    async def resolve(self, resource_id: str) -> _Doc | None:
        if resource_id != "doc-1":
            return None
        return _Doc(resource_id)


class _Attributes:
    async def resolve(self, resource: _Doc) -> ResourceAttributes:
        return ResourceAttributes(
            owner_id=resource.owner_id,
            tenant_id=resource.tenant_id,
        )


async def test_class_resolver_and_request_injection() -> None:
    async def current_principal() -> AuthorizationPrincipal:
        return AuthorizationPrincipal(
            id="user-1",
            scopes={"doc:read"},
            tenant_id="tenant-a",
        )

    guard = RouteGuard(principal=current_principal)
    guard.add_resource("doc", resolver=_Resolver(), attributes=_Attributes())
    app = FastAPI()

    @app.get("/docs/{doc_id}")
    async def read_doc(
        doc: _Doc = Depends(
            guard.protect_resource(
                "doc",
                id_param="doc_id",
                scopes={"doc:read"},
                tenant=True,
            )
        ),
    ) -> dict[str, str]:
        return {"id": doc.id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs/doc-1")
    assert response.status_code == 200
    assert response.json() == {"id": "doc-1"}


async def test_missing_path_param_fails_closed() -> None:
    async def current_principal() -> AuthorizationPrincipal:
        return AuthorizationPrincipal(id="user-1", scopes={"doc:read"})

    async def resolve_doc(doc_id: str) -> _Doc | None:
        return _Doc(doc_id)

    async def attributes(resource: _Doc) -> ResourceAttributes:
        return ResourceAttributes(owner_id="user-1", tenant_id="tenant-a")

    guard = RouteGuard(principal=current_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=attributes)
    app = FastAPI()

    @app.get("/docs/{doc_id}")
    async def read_doc(
        doc: _Doc = Depends(
            guard.protect_resource(
                "doc",
                id_param="invoice_id",
                scopes={"doc:read"},
                tenant=True,
            )
        ),
    ) -> dict[str, str]:
        return {"id": doc.id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with pytest.raises(MissingResourceId):
            await client.get("/docs/doc-1")


async def test_attributes_must_return_resource_attributes() -> None:
    async def current_principal() -> AuthorizationPrincipal:
        return AuthorizationPrincipal(
            id="user-1",
            scopes={"doc:read"},
            tenant_id="tenant-a",
        )

    async def resolve_doc(doc_id: str) -> _Doc | None:
        return _Doc(doc_id)

    async def attributes(resource: _Doc) -> str:
        return "nope"

    guard = RouteGuard(principal=current_principal)
    guard.add_resource("doc", resolver=resolve_doc, attributes=attributes)
    app = FastAPI()

    @app.get("/docs/{doc_id}")
    async def read_doc(
        doc: _Doc = Depends(
            guard.protect_resource(
                "doc",
                id_param="doc_id",
                scopes={"doc:read"},
                tenant=True,
            )
        ),
    ) -> dict[str, str]:
        return {"id": doc.id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with pytest.raises(TypeError, match="ResourceAttributes"):
            await client.get("/docs/doc-1")


def test_callable_from_rejects_plain_objects() -> None:
    with pytest.raises(TypeError):
        callable_from(object())


async def test_invoke_callable_supports_annotated_depends_and_sync() -> None:
    def get_flag() -> str:
        return "ok"

    def resolve(
        resource_id: str,
        flag: Annotated[str, Depends(get_flag)],
        request: Request,
    ) -> str:
        return f"{resource_id}:{flag}:{request.url.path}"

    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/docs/doc-1",
            "raw_path": b"/docs/doc-1",
            "query_string": b"",
            "headers": [],
            "client": ("test", 80),
            "server": ("test", 80),
            "path_params": {"doc_id": "doc-1"},
        }
    )
    result = await invoke_callable(
        resolve,
        request=request,
        bound={"resource_id": "doc-1"},
    )
    assert result == "doc-1:ok:/docs/doc-1"
