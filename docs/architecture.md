# Architecture

The package is split so authorization decisions can be tested without FastAPI.

```
src/fastapi_route_guard/
  core/         models, policy, result, principal, resource
  evaluators/   roles, scopes, ownership, tenant, custom handlers, PolicyEvaluator
  registry/     resource and handler lookup
  testing/      evaluate_policy, test_principal
  fastapi/      RouteGuard, path-param extraction, HTTP 403
  exceptions.py configuration faults (500)
```

`PolicyEvaluator` never imports `Request`, `Depends`, FastAPI, or
`HTTPException`. The FastAPI layer extracts the resource id, loads the object
after claims pass, builds an `AuthorizationContext`, and asks the evaluator for
a decision.

The integration layer does not resolve dependencies itself. `protect_resource`
reads the resolver signatures at wiring time and exposes every parameter it does
not bind — anything other than the resource id, and the loaded resource for the
attributes mapper — as a real FastAPI dependency on the guard dependency it
returns. FastAPI therefore owns `Depends` resolution, `yield` teardown,
`dependency_overrides`, and the per-request cache, while the resolver call
itself stays behind the claims phase so a denied caller never triggers the
lookup.

Public entry point: `fastapi_route_guard` — core types, evaluator, `RouteGuard`,
testing helpers.

The HTTP pipeline expected by `0.1.x`:

```
host authentication dependency
        ↓
AuthorizationPrincipal
        ↓
RouteGuard dependency
        ↓
claims phase: principal, roles, scopes   (in memory, no I/O)
        ↓
resource resolver (only if the claims passed)
        ↓
resource phase: tenant, ownership, handlers
        ↓
ALLOW and return the resource, or AuthorizationDenied (403)
```

Simple requirement checks (roles, scopes, tenant, ownership) are synchronous.
Resource resolvers and custom handlers are async because they may hit a
database or another service.

FastAPI already supplies request context through dependencies. `0.1.x` does not
use `ContextVar`.
