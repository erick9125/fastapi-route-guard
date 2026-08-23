# FastAPI Route Guard

Declarative resource-level authorization for FastAPI.

FastAPI Route Guard helps applications enforce consistent access
control using roles, scopes, ownership, tenant boundaries, resource
context, and extensible async policies while keeping authorization
logic outside route handlers.

**`0.1.x` promise:** enforce consistent resource-level authorization in FastAPI
using reusable async dependencies for roles, scopes, ownership, tenant
boundaries, resource loading, and custom policy handlers.

|         |                         |
| ------- | ----------------------- |
| Package | `fastapi-route-guard`   |
| Runtime | FastAPI, Python 3.11+   |
| License | MIT                     |

A Spanish-language summary is available in [README.es.md](README.es.md); this file is the full reference.

---

## Table of contents

1. [The problem](#the-problem)
2. [Why authentication is not authorization](#why-authentication-is-not-authorization)
3. [What this library solves](#what-this-library-solves)
4. [What this is not](#what-this-is-not)
5. [Installation](#installation)
6. [Quick start](#quick-start)
7. [Principal mapping](#principal-mapping)
8. [Roles](#roles)
9. [Scopes](#scopes)
10. [Resource authorization](#resource-authorization)
11. [Ownership](#ownership)
12. [Multi-tenancy](#multi-tenancy)
13. [Custom policies](#custom-policies)
14. [Resource reuse](#resource-reuse)
15. [Failure behavior](#failure-behavior)
16. [Security model](#security-model)
17. [BOLA example](#bola-example)
18. [Testing](#testing)
19. [Limitations](#limitations)
20. [Architecture](#architecture)
21. [Roadmap](#roadmap)
22. [License](#license)

---

## The problem

FastAPI can authenticate a user and verify scopes. That does not mean the
caller may access **this** resource.

```python
@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    user: User = Depends(current_user),
):
    return await repository.find_by_id(invoice_id)
```

The user may have `invoice:read` while invoice `123` belongs to tenant B and
the user belongs to tenant A, or `invoice.owner_id != user.id`.

That is the class of bug OWASP describes as BOLA / IDOR: the endpoint is
authorized, the object is not.

---

## Why authentication is not authorization

```
authenticated principal
        +
requested action
        +
resource
        +
roles
        +
scopes
        +
tenant
        +
ownership
        +
custom rules
        ↓
      allow / deny
```

This package answers the second question. It does not answer the first.

FastAPI Route Guard does not authenticate users. Authentication must resolve a
trusted principal before authorization is evaluated.

---

## What this library solves

Version `0.1.x` covers:

- a `RouteGuard` instance and FastAPI `Depends` integration
- roles (ANY)
- scopes (ALL)
- ownership
- tenant matching
- async resource resolvers and attribute resolvers
- async custom policy handlers
- fail-closed evaluation
- structured internal results with generic HTTP 403 bodies
- returning the loaded resource from the guard so the endpoint does not load it again
- a FastAPI-free evaluator that can be unit-tested in isolation

It helps enforce consistent object-level authorization controls that can
mitigate BOLA/IDOR risks when correctly configured. It does not prevent every
BOLA vulnerability: a missing dependency or a wrong resolver can still leave a
hole.

---

## What this is not

This package is not an IAM.

It does not issue JWTs, log users in, talk to OAuth, hash passwords, store
roles in a database, compile a policy language, or replace your authentication
dependency.

`0.1.x` does not include GraphQL, WebSockets, Casbin, OPA, Zanzibar, Redis,
audit dashboards, API keys, sessions, rate limiting, or list-result filtering.

---

## Installation

```bash
pip install fastapi-route-guard
```

Requires Python 3.11+ and FastAPI (Pydantic 2).

---

## Quick start

```python
from fastapi import Depends, FastAPI
from fastapi_route_guard import (
    AuthorizationPrincipal,
    ResourceAttributes,
    RouteGuard,
)


async def current_principal() -> AuthorizationPrincipal: ...


async def resolve_invoice(invoice_id: str) -> Invoice | None:
    return await repository.find_by_id(invoice_id)


async def invoice_attributes(invoice: Invoice) -> ResourceAttributes:
    return ResourceAttributes(
        owner_id=invoice.owner_id,
        tenant_id=invoice.tenant_id,
    )


guard = RouteGuard(principal=current_principal)
guard.add_resource(
    "invoice",
    resolver=resolve_invoice,
    attributes=invoice_attributes,
)

app = FastAPI()


@app.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice: Invoice = Depends(
        guard.protect_resource(
            "invoice",
            id_param="invoice_id",
            action="read",
            scopes={"invoice:read"},
            tenant=True,
        )
    ),
):
    return invoice
```

For permissions that do not load a resource:

```python
@app.get("/invoices")
async def list_invoices(
    _: None = Depends(
        guard.protect(
            scopes={"invoice:list"},
            roles={"admin", "manager"},
        )
    ),
): ...
```

---

## Principal mapping

Do not change the application's user model. Map it:

```python
async def current_principal(
    user: User = Security(get_current_user),
) -> AuthorizationPrincipal:
    return AuthorizationPrincipal(
        id=str(user.id),
        roles=set(user.roles),
        scopes=set(user.permissions),
        tenant_id=str(user.organization_id),
    )
```

`AuthorizationPrincipal` uses `set[str]` for roles and scopes so membership
checks stay simple. The library never reads `request.user` on its own.

---

## Roles

```python
RoutePolicy(roles=frozenset({"admin", "manager"}))
```

means **admin OR manager**. Empty role requirements allow.

---

## Scopes

```python
RoutePolicy(scopes=frozenset({"invoice:read", "invoice:export"}))
```

means **invoice:read AND invoice:export**. Empty scope requirements allow.

---

## Resource authorization

Register a resource with a resolver and an attributes mapper. Resolvers are
async callables. They can also use FastAPI `Depends` for repositories, so you
do not construct infrastructure at import time.

```python
async def resolve_invoice(
    invoice_id: str,
    repository: InvoiceRepository = Depends(get_invoice_repository),
) -> Invoice | None:
    return await repository.find_by_id(invoice_id)
```

Everything except the resource id is resolved by FastAPI itself, so a resolver
gets the same dependency semantics as a route handler: `yield` dependencies are
entered and closed around the request, `app.dependency_overrides` apply, and a
dependency shared with the endpoint is resolved once per request. Because the
guard reads the resolver's signature when the route is declared, call
`add_resource()` before `protect_resource()` — an unregistered resource then
fails at import time instead of on the first request that reaches the endpoint.

The FastAPI layer extracts `id_param` from the path. The core evaluator never
reads `request.path_params`.

A `protect_resource()` policy must declare `tenant`, `ownership`, or a custom
handler. Loading a row is not, by itself, an authorization decision.
`unsafe_skip_object_check=True` opts out explicitly.

---

## Ownership

```python
@app.patch("/invoices/{invoice_id}")
async def update_invoice(
    invoice: Invoice = Depends(
        guard.protect_resource(
            "invoice",
            id_param="invoice_id",
            action="update",
            scopes={"invoice:update"},
            tenant=True,
            ownership=True,
        )
    ),
):
    return invoice
```

Tenant membership does not imply ownership. See [docs/ownership.md](docs/ownership.md).

---

## Multi-tenancy

`tenant=True` requires `principal.tenant_id == attributes.tenant_id`, and both
values must be present. This is a boundary check, not a query filter. See
[docs/multi-tenancy.md](docs/multi-tenancy.md).

---

## Custom policies

```python
class InvoiceCanApprove:
    name = "invoice.can_approve"

    async def evaluate(self, context: AuthorizationContext) -> bool:
        invoice = context.resource
        if not isinstance(invoice, Invoice):
            return False
        return invoice.status == "pending"


guard.policy(InvoiceCanApprove())
```

```python
Depends(
    guard.protect_resource(
        "invoice",
        id_param="invoice_id",
        action="approve",
        roles={"manager"},
        scopes={"invoice:approve"},
        tenant=True,
        handlers=("invoice.can_approve",),
    )
)
```

Every listed handler must allow. A missing handler is an error, not an allow.
See [docs/custom-policies.md](docs/custom-policies.md).

---

## Resource reuse

The guard loads the resource, authorizes it, and returns it. The endpoint
receives the same object. Do not load the invoice again inside the handler.

A repository `find_by_id` counter on `GET /invoices/123` should stay at `1`.

---

## Failure behavior

Requirements combine with AND:

```
role (ANY)
AND scopes (ALL)
AND tenant
AND ownership
AND handlers (ALL)
```

Evaluation order:

```
principal → roles → scopes → resource existence → tenant → ownership → handlers
```

Cheap claims run first so a denied caller does not pay for a resource lookup.

| Situation | Result |
| --------- | ------ |
| Authentication dependency rejects the caller | `401` (your app) |
| Authenticated but unauthorized | `403` `{"detail": "Forbidden"}` |
| Resource missing | `403` (default; resists id enumeration) |
| Handler not registered, resolver throws | error (never allow) |

The HTTP body does not include violation codes, tenant ids, or owner ids.

---

## Security model

FastAPI Route Guard does not authenticate users.

Authentication must resolve a trusted principal before authorization is
evaluated.

Resource-level authorization depends on correct resolver and policy
configuration.

Read [docs/security-model.md](docs/security-model.md) for fail-closed rules,
logging guidance, and what the `403` body must never contain.

---

## BOLA example

```
Tenant A
├── user-a
└── invoice-a

Tenant B
├── user-b
└── invoice-b
```

```bash
curl -H "X-User: user-a" /invoices/invoice-a   # 200
curl -H "X-User: user-a" /invoices/invoice-b   # 403
```

The second request is an ID-manipulation attempt. The caller is authenticated
and may even have `invoice:read`. They still do not get tenant B's invoice.

Same tenant, wrong owner:

```
Tenant A / user-a / invoice-c (owner = user-c)
PATCH /invoices/invoice-c  →  403
```

Tenant and ownership are different controls. See
[examples/invoices_api](examples/invoices_api).

---

## Testing

```python
from fastapi_route_guard import RoutePolicy, evaluate_policy, make_principal

principal = make_principal(
    id="user-1",
    roles={"manager"},
    scopes={"invoice:read"},
    tenant_id="tenant-a",
)

result = await evaluate_policy(
    policy=policy,
    principal=principal,
    resource=resource,
    attributes=attributes,
)
```

`evaluate_policy` exercises the same engine FastAPI uses, without `Request` or
a TestClient.

---

## Limitations

This library authorizes one requested resource at a time. It does not turn a
policy into `WHERE tenant_id = :tenant`. List filtering, ORM adapters, OPA,
and decision caching are out of scope for `0.1.x`.

See [docs/limitations.md](docs/limitations.md).

---

## Architecture

The authorization engine is Python, async, and framework-free. FastAPI is an
integration layer on top of it: `Depends`, path-param extraction, and HTTP
errors.

See [docs/architecture.md](docs/architecture.md).

---

## Roadmap

- **0.2.0** — observers, custom role/scope modes, configurable
  resource-not-found behavior
- **0.3.0** — policy presets, list filtering helpers
- **0.4.0** — external PDP / OPA only if there is real demand

---

## License

MIT. See [LICENSE](LICENSE).
